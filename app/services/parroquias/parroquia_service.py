"""
Servicio de gestión de parroquias para el sistema de catequesis.
Maneja CRUD de parroquias, programas, horarios y configuraciones.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from app.services.base_service import BaseService
from app.models.parroquias.parroquia_model import Parroquia
from app.models.parroquias.programa_catequesis_model import ProgramaCatequesis
from app.models.parroquias.horario_model import Horario
from app.models.seguridad.usuario_model import Usuario
from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.grupo_model import Grupo
from app.schemas.parroquias.parroquia_schema import (
    ParroquiaCreateSchema, ParroquiaUpdateSchema, ParroquiaResponseSchema,
    ParroquiaSearchSchema, ConfiguracionParroquiaSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.utils.image_processor import process_parroquia_image
from app.utils.geocoding import get_coordinates, validate_address
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class ParroquiaService(BaseService):
    """Servicio para gestión completa de parroquias."""
    
    @property
    def model(self) -> Type[Parroquia]:
        return Parroquia
    
    @property
    def create_schema(self) -> Type[ParroquiaCreateSchema]:
        return ParroquiaCreateSchema
    
    @property
    def update_schema(self) -> Type[ParroquiaUpdateSchema]:
        return ParroquiaUpdateSchema
    
    @property
    def response_schema(self) -> Type[ParroquiaResponseSchema]:
        return ParroquiaResponseSchema
    
    @property
    def search_schema(self) -> Type[ParroquiaSearchSchema]:
        return ParroquiaSearchSchema
    
    def __init__(self, db: Session = None, current_user: Dict = None):
        super().__init__(db, current_user)
        self.geocoder = Nominatim(user_agent="catequesis_system")
    
    # ==========================================
    # OPERACIONES CRUD EXTENDIDAS
    # ==========================================
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Parroquia.diocesis),
            joinedload(Parroquia.parroco),
            joinedload(Parroquia.programas_catequesis),
            joinedload(Parroquia.horarios),
            joinedload(Parroquia.created_by_user),
            joinedload(Parroquia.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para parroquias."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Parroquia.nombre.ilike(search_term),
                    Parroquia.direccion.ilike(search_term),
                    Parroquia.municipio.ilike(search_term),
                    Parroquia.departamento.ilike(search_term),
                    Parroquia.telefono.ilike(search_term),
                    Parroquia.email.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('activa') is not None:
            query = query.filter(Parroquia.activa == search_data['activa'])
        
        if search_data.get('diocesis_id'):
            query = query.filter(Parroquia.diocesis_id == search_data['diocesis_id'])
        
        if search_data.get('departamento'):
            query = query.filter(Parroquia.departamento.ilike(f"%{search_data['departamento']}%"))
        
        if search_data.get('municipio'):
            query = query.filter(Parroquia.municipio.ilike(f"%{search_data['municipio']}%"))
        
        if search_data.get('parroco_id'):
            query = query.filter(Parroquia.parroco_id == search_data['parroco_id'])
        
        # Filtros de ubicación
        if search_data.get('cerca_de_coordenadas'):
            coords = search_data['cerca_de_coordenadas']
            radio_km = search_data.get('radio_km', 10)
            
            # Usar fórmula de distancia en SQL para filtro aproximado
            query = query.filter(
                text(f"""
                    (6371 * acos(cos(radians({coords['lat']})) * cos(radians(latitud)) 
                    * cos(radians(longitud) - radians({coords['lng']})) 
                    + sin(radians({coords['lat']})) * sin(radians(latitud)))) <= {radio_km}
                """)
            )
        
        # Filtros de capacidad
        if search_data.get('capacidad_minima'):
            query = query.filter(Parroquia.capacidad_maxima >= search_data['capacidad_minima'])
        
        # Filtros por programas
        if search_data.get('con_programa'):
            programa_nombre = search_data['con_programa']
            query = query.join(ProgramaCatequesis).filter(
                ProgramaCatequesis.nombre.ilike(f"%{programa_nombre}%")
            )
        
        return query
    
    @require_permission('parroquias', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar nombre único
        if self.exists(nombre=data['nombre']):
            raise ValidationException("Ya existe una parroquia con ese nombre")
        
        # Validar y geocodificar dirección
        if data.get('direccion'):
            address_data = self._geocode_address(data)
            data.update(address_data)
        
        # Configuraciones por defecto
        data.setdefault('activa', True)
        data.setdefault('capacidad_maxima', 100)
        data.setdefault('configuracion', self._get_default_configuration())
        
        return data
    
    def _after_create(self, instance, data: Dict[str, Any], **kwargs):
        """Hook post-creación para configuraciones adicionales."""
        # Crear programas de catequesis por defecto
        if kwargs.get('create_default_programs', True):
            self._create_default_programs(instance)
        
        # Crear horarios por defecto
        if kwargs.get('create_default_schedules', True):
            self._create_default_schedules(instance)
        
        return instance
    
    @require_permission('parroquias', 'actualizar')
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-actualización para validaciones."""
        # Verificar nombre único (si cambió)
        if 'nombre' in data and data['nombre'] != instance.nombre:
            if self.exists(nombre=data['nombre']):
                raise ValidationException("Ya existe una parroquia con ese nombre")
        
        # Regecodificar si cambió la dirección
        if 'direccion' in data and data['direccion'] != instance.direccion:
            address_data = self._geocode_address(data)
            data.update(address_data)
        
        return data
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar la parroquia."""
        # Verificar dependencias
        dependencies = self._check_parroquia_dependencies(instance.id)
        if dependencies:
            raise BusinessLogicException(f"No se puede eliminar. Tiene dependencias: {', '.join(dependencies)}")
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE PARROQUIAS
    # ==========================================
    
    def get_parroquia_details(self, parroquia_id: int) -> Dict[str, Any]:
        """
        Obtiene detalles completos de una parroquia.
        
        Args:
            parroquia_id: ID de la parroquia
            
        Returns:
            Dict con detalles completos
        """
        try:
            parroquia = self._get_instance_by_id(parroquia_id)
            
            # Estadísticas básicas
            stats = self._get_parroquia_statistics(parroquia_id)
            
            # Programas activos
            programas = self.db.query(ProgramaCatequesis).filter(
                and_(
                    ProgramaCatequesis.parroquia_id == parroquia_id,
                    ProgramaCatequesis.activo == True
                )
            ).all()
            
            # Horarios vigentes
            horarios = self.db.query(Horario).filter(
                and_(
                    Horario.parroquia_id == parroquia_id,
                    Horario.activo == True
                )
            ).all()
            
            # Serializar respuesta
            result = self._serialize_response(parroquia)
            result.update({
                'estadisticas': stats,
                'programas_activos': [self._serialize_programa(p) for p in programas],
                'horarios_vigentes': [self._serialize_horario(h) for h in horarios],
                'configuracion_completa': parroquia.configuracion
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles de parroquia: {str(e)}")
            raise BusinessLogicException("Error obteniendo detalles de la parroquia")
    
    @require_permission('parroquias', 'actualizar')
    def update_configuration(self, parroquia_id: int, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza la configuración de una parroquia.
        
        Args:
            parroquia_id: ID de la parroquia
            config_data: Nueva configuración
            
        Returns:
            Dict con la configuración actualizada
        """
        try:
            parroquia = self._get_instance_by_id(parroquia_id)
            
            # Validar configuración
            schema = ConfiguracionParroquiaSchema()
            validated_config = schema.load(config_data)
            
            # Actualizar configuración
            current_config = parroquia.configuracion or {}
            current_config.update(validated_config)
            parroquia.configuracion = current_config
            parroquia.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Configuración actualizada para parroquia {parroquia.nombre}")
            
            return {
                'success': True,
                'configuracion': current_config,
                'message': 'Configuración actualizada exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error actualizando configuración: {str(e)}")
            raise BusinessLogicException("Error actualizando configuración")
    
    def find_nearby_parroquias(self, coordinates: Dict[str, float], radius_km: float = 10) -> List[Dict[str, Any]]:
        """
        Encuentra parroquias cercanas a unas coordenadas.
        
        Args:
            coordinates: Dict con 'lat' y 'lng'
            radius_km: Radio de búsqueda en kilómetros
            
        Returns:
            Lista de parroquias cercanas con distancia
        """
        try:
            # Obtener parroquias con coordenadas válidas
            parroquias = self.db.query(Parroquia).filter(
                and_(
                    Parroquia.activa == True,
                    Parroquia.latitud.isnot(None),
                    Parroquia.longitud.isnot(None)
                )
            ).all()
            
            # Calcular distancias
            nearby_parroquias = []
            origin = (coordinates['lat'], coordinates['lng'])
            
            for parroquia in parroquias:
                destination = (parroquia.latitud, parroquia.longitud)
                distance = geodesic(origin, destination).kilometers
                
                if distance <= radius_km:
                    parroquia_data = self._serialize_response(parroquia)
                    parroquia_data['distancia_km'] = round(distance, 2)
                    nearby_parroquias.append(parroquia_data)
            
            # Ordenar por distancia
            nearby_parroquias.sort(key=lambda x: x['distancia_km'])
            
            return nearby_parroquias
            
        except Exception as e:
            logger.error(f"Error buscando parroquias cercanas: {str(e)}")
            raise BusinessLogicException("Error buscando parroquias cercanas")
    
    def get_parroquias_by_diocesis(self, diocesis_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todas las parroquias de una diócesis.
        
        Args:
            diocesis_id: ID de la diócesis
            
        Returns:
            Lista de parroquias
        """
        try:
            parroquias = self.db.query(Parroquia).filter(
                Parroquia.diocesis_id == diocesis_id
            ).order_by(Parroquia.nombre).all()
            
            return [self._serialize_response(p) for p in parroquias]
            
        except Exception as e:
            logger.error(f"Error obteniendo parroquias por diócesis: {str(e)}")
            raise BusinessLogicException("Error obteniendo parroquias")
    
    @require_permission('parroquias', 'administrar')
    def toggle_activation(self, parroquia_id: int) -> Dict[str, Any]:
        """
        Activa o desactiva una parroquia.
        
        Args:
            parroquia_id: ID de la parroquia
            
        Returns:
            Dict con el nuevo estado
        """
        try:
            parroquia = self._get_instance_by_id(parroquia_id)
            
            # Cambiar estado
            new_state = not parroquia.activa
            parroquia.activa = new_state
            parroquia.updated_at = datetime.utcnow()
            
            # Si se desactiva, manejar consecuencias
            if not new_state:
                self._handle_parroquia_deactivation(parroquia_id)
            
            self.db.commit()
            
            action = "activada" if new_state else "desactivada"
            logger.info(f"Parroquia {parroquia.nombre} {action}")
            
            return {
                'success': True,
                'activa': new_state,
                'message': f'Parroquia {action} exitosamente'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando estado de parroquia: {str(e)}")
            raise BusinessLogicException("Error cambiando estado de la parroquia")
    
    def assign_parroco(self, parroquia_id: int, parroco_id: int) -> Dict[str, Any]:
        """
        Asigna un párroco a una parroquia.
        
        Args:
            parroquia_id: ID de la parroquia
            parroco_id: ID del párroco (usuario)
            
        Returns:
            Dict con confirmación
        """
        try:
            parroquia = self._get_instance_by_id(parroquia_id)
            
            # Verificar que el usuario existe y es párroco
            parroco = self.db.query(Usuario).filter(Usuario.id == parroco_id).first()
            if not parroco:
                raise NotFoundException("Párroco no encontrado")
            
            # Verificar rol de párroco
            user_roles = [role.nombre for role in parroco.roles]
            if 'parroco' not in user_roles and 'admin' not in user_roles:
                raise ValidationException("El usuario debe tener rol de párroco")
            
            # Asignar párroco
            old_parroco_id = parroquia.parroco_id
            parroquia.parroco_id = parroco_id
            parroquia.fecha_asignacion_parroco = datetime.utcnow()
            parroquia.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Párroco {parroco.email} asignado a parroquia {parroquia.nombre}")
            
            return {
                'success': True,
                'parroco_anterior_id': old_parroco_id,
                'parroco_nuevo_id': parroco_id,
                'message': f'Párroco asignado exitosamente'
            }
            
        except (NotFoundException, ValidationException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error asignando párroco: {str(e)}")
            raise BusinessLogicException("Error asignando párroco")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de parroquias."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de parroquias
            total_parroquias = self.db.query(Parroquia).count()
            active_parroquias = self.db.query(Parroquia).filter(Parroquia.activa == True).count()
            
            # Distribución por departamento
            departamento_distribution = self.db.query(
                Parroquia.departamento, func.count(Parroquia.id)
            ).filter(
                Parroquia.activa == True
            ).group_by(Parroquia.departamento).all()
            
            # Capacidad total
            capacidad_total = self.db.query(
                func.sum(Parroquia.capacidad_maxima)
            ).filter(Parroquia.activa == True).scalar() or 0
            
            # Parroquias con programas activos
            with_programs = self.db.query(Parroquia).join(ProgramaCatequesis).filter(
                and_(
                    Parroquia.activa == True,
                    ProgramaCatequesis.activo == True
                )
            ).distinct().count()
            
            # Estadísticas de catequizandos por parroquia
            catequizandos_stats = self.db.query(
                func.count(Catequizando.id).label('total_catequizandos'),
                func.avg(func.count(Catequizando.id)).over().label('promedio_por_parroquia')
            ).join(Parroquia).filter(
                and_(
                    Parroquia.activa == True,
                    Catequizando.activo == True
                )
            ).group_by(Parroquia.id).first()
            
            base_stats.update({
                'total_parroquias': total_parroquias,
                'parroquias_activas': active_parroquias,
                'parroquias_inactivas': total_parroquias - active_parroquias,
                'capacidad_total_sistema': capacidad_total,
                'promedio_capacidad': round(capacidad_total / active_parroquias, 1) if active_parroquias > 0 else 0,
                'parroquias_con_programas': with_programs,
                'cobertura_programas_pct': round((with_programs / active_parroquias) * 100, 1) if active_parroquias > 0 else 0,
                'distribucion_departamentos': {dept: count for dept, count in departamento_distribution},
                'total_catequizandos': catequizandos_stats.total_catequizandos if catequizandos_stats else 0,
                'promedio_catequizandos_por_parroquia': round(catequizandos_stats.promedio_por_parroquia, 1) if catequizandos_stats else 0
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de parroquias: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # GESTIÓN DE PROGRAMAS DE CATEQUESIS
    # ==========================================
    
    @require_permission('parroquias', 'administrar')
    def create_programa_catequesis(self, parroquia_id: int, programa_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un programa de catequesis para una parroquia.
        
        Args:
            parroquia_id: ID de la parroquia
            programa_data: Datos del programa
            
        Returns:
            Dict con el programa creado
        """
        try:
            parroquia = self._get_instance_by_id(parroquia_id)
            
            # Verificar que no existe un programa con el mismo nombre
            existing = self.db.query(ProgramaCatequesis).filter(
                and_(
                    ProgramaCatequesis.parroquia_id == parroquia_id,
                    ProgramaCatequesis.nombre == programa_data['nombre']
                )
            ).first()
            
            if existing:
                raise ValidationException("Ya existe un programa con ese nombre en la parroquia")
            
            # Crear programa
            programa_data['parroquia_id'] = parroquia_id
            programa = ProgramaCatequesis(**programa_data)
            programa.created_at = datetime.utcnow()
            programa.created_by = self.current_user.get('id') if self.current_user else None
            
            self.db.add(programa)
            self.db.commit()
            
            logger.info(f"Programa {programa.nombre} creado para parroquia {parroquia.nombre}")
            
            return self._serialize_programa(programa)
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando programa: {str(e)}")
            raise BusinessLogicException("Error creando programa de catequesis")
    
    def get_programas_parroquia(self, parroquia_id: int, solo_activos: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene los programas de catequesis de una parroquia.
        
        Args:
            parroquia_id: ID de la parroquia
            solo_activos: Si solo incluir programas activos
            
        Returns:
            Lista de programas
        """
        try:
            query = self.db.query(ProgramaCatequesis).filter(
                ProgramaCatequesis.parroquia_id == parroquia_id
            )
            
            if solo_activos:
                query = query.filter(ProgramaCatequesis.activo == True)
            
            programas = query.order_by(ProgramaCatequesis.orden, ProgramaCatequesis.nombre).all()
            
            return [self._serialize_programa(p) for p in programas]
            
        except Exception as e:
            logger.error(f"Error obteniendo programas: {str(e)}")
            raise BusinessLogicException("Error obteniendo programas")
    
    # ==========================================
    # GESTIÓN DE HORARIOS
    # ==========================================
    
    @require_permission('parroquias', 'administrar')
    def create_horario(self, parroquia_id: int, horario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un horario para una parroquia.
        
        Args:
            parroquia_id: ID de la parroquia
            horario_data: Datos del horario
            
        Returns:
            Dict con el horario creado
        """
        try:
            parroquia = self._get_instance_by_id(parroquia_id)
            
            # Validar que no hay conflictos de horario
            conflicts = self._check_schedule_conflicts(parroquia_id, horario_data)
            if conflicts:
                raise ValidationException(f"Conflicto de horario con: {', '.join(conflicts)}")
            
            # Crear horario
            horario_data['parroquia_id'] = parroquia_id
            horario = Horario(**horario_data)
            horario.created_at = datetime.utcnow()
            horario.created_by = self.current_user.get('id') if self.current_user else None
            
            self.db.add(horario)
            self.db.commit()
            
            logger.info(f"Horario creado para parroquia {parroquia.nombre}")
            
            return self._serialize_horario(horario)
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando horario: {str(e)}")
            raise BusinessLogicException("Error creando horario")
    
    def get_horarios_parroquia(self, parroquia_id: int, fecha: date = None) -> List[Dict[str, Any]]:
        """
        Obtiene los horarios de una parroquia para una fecha específica.
        
        Args:
            parroquia_id: ID de la parroquia
            fecha: Fecha específica (opcional, default hoy)
            
        Returns:
            Lista de horarios
        """
        try:
            if not fecha:
                fecha = date.today()
            
            day_of_week = fecha.weekday()  # 0=Monday, 6=Sunday
            
            horarios = self.db.query(Horario).filter(
                and_(
                    Horario.parroquia_id == parroquia_id,
                    Horario.activo == True,
                    Horario.dia_semana == day_of_week
                )
            ).order_by(Horario.hora_inicio).all()
            
            return [self._serialize_horario(h) for h in horarios]
            
        except Exception as e:
            logger.error(f"Error obteniendo horarios: {str(e)}")
            raise BusinessLogicException("Error obteniendo horarios")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _geocode_address(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Geocodifica una dirección y obtiene coordenadas."""
        try:
            full_address = f"{data['direccion']}, {data.get('municipio', '')}, {data.get('departamento', '')}, Colombia"
            location = self.geocoder.geocode(full_address, timeout=10)
            
            if location:
                return {
                    'latitud': location.latitude,
                    'longitud': location.longitude,
                    'direccion_completa': location.address
                }
            else:
                logger.warning(f"No se pudo geocodificar la dirección: {full_address}")
                return {}
                
        except Exception as e:
            logger.warning(f"Error en geocodificación: {str(e)}")
            return {}
    
    def _get_default_configuration(self) -> Dict[str, Any]:
        """Obtiene la configuración por defecto para nuevas parroquias."""
        return {
            'notificaciones': {
                'email_enabled': True,
                'sms_enabled': False,
                'recordatorios_automaticos': True
            },
            'inscripciones': {
                'auto_approval': False,
                'require_documents': True,
                'max_per_group': 25,
                'edad_minima': 6,
                'edad_maxima': 99
            },
            'certificados': {
                'auto_generate': False,
                'require_approval': True,
                'template_default': 'basico'
            },
            'pagos': {
                'enabled': True,
                'methods': ['efectivo', 'transferencia'],
                'currency': 'COP'
            },
            'horarios': {
                'timezone': 'America/Bogota',
                'duracion_default_minutos': 60
            }
        }
    
    def _create_default_programs(self, parroquia: Parroquia):
        """Crea programas de catequesis por defecto."""
        default_programs = [
            {
                'nombre': 'Primera Comunión',
                'descripcion': 'Preparación para el Sacramento de la Primera Comunión',
                'edad_minima': 8,
                'edad_maxima': 12,
                'duracion_meses': 12,
                'orden': 1,
                'activo': True
            },
            {
                'nombre': 'Confirmación',
                'descripcion': 'Preparación para el Sacramento de la Confirmación',
                'edad_minima': 13,
                'edad_maxima': 18,
                'duracion_meses': 24,
                'orden': 2,
                'activo': True
            },
            {
                'nombre': 'Catequesis Familiar',
                'descripcion': 'Catequesis para toda la familia',
                'edad_minima': 0,
                'edad_maxima': 99,
                'duracion_meses': 6,
                'orden': 3,
                'activo': True
            }
        ]
        
        for program_data in default_programs:
            program_data['parroquia_id'] = parroquia.id
            program_data['created_at'] = datetime.utcnow()
            programa = ProgramaCatequesis(**program_data)
            self.db.add(programa)
    
    def _create_default_schedules(self, parroquia: Parroquia):
        """Crea horarios por defecto."""
        from datetime import time
        
        default_schedules = [
            {
                'nombre': 'Catequesis Dominical Mañana',
                'dia_semana': 6,  # Domingo
                'hora_inicio': time(9, 0),
                'hora_fin': time(10, 30),
                'capacidad_maxima': 30,
                'activo': True
            },
            {
                'nombre': 'Catequesis Dominical Tarde',
                'dia_semana': 6,  # Domingo
                'hora_inicio': time(15, 0),
                'hora_fin': time(16, 30),
                'capacidad_maxima': 30,
                'activo': True
            },
            {
                'nombre': 'Catequesis Sábado',
                'dia_semana': 5,  # Sábado
                'hora_inicio': time(16, 0),
                'hora_fin': time(17, 30),
                'capacidad_maxima': 25,
                'activo': True
            }
        ]
        
        for schedule_data in default_schedules:
            schedule_data['parroquia_id'] = parroquia.id
            schedule_data['created_at'] = datetime.utcnow()
            horario = Horario(**schedule_data)
            self.db.add(horario)
    
    def _get_parroquia_statistics(self, parroquia_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de una parroquia."""
        try:
            # Catequizandos activos
            total_catequizandos = self.db.query(Catequizando).filter(
                and_(
                    Catequizando.parroquia_id == parroquia_id,
                    Catequizando.activo == True
                )
            ).count()
            
            # Grupos activos
            total_grupos = self.db.query(Grupo).filter(
                and_(
                    Grupo.parroquia_id == parroquia_id,
                    Grupo.activo == True
                )
            ).count()
            
            # Programas activos
            total_programas = self.db.query(ProgramaCatequesis).filter(
                and_(
                    ProgramaCatequesis.parroquia_id == parroquia_id,
                    ProgramaCatequesis.activo == True
                )
            ).count()
            
            # Catequistas
            total_catequistas = self.db.query(Usuario).join(UsuarioRol).join(Rol).filter(
                and_(
                    Usuario.parroquia_id == parroquia_id,
                    Usuario.activo == True,
                    Rol.nombre == 'catequista'
                )
            ).count()
            
            return {
                'total_catequizandos': total_catequizandos,
                'total_grupos': total_grupos,
                'total_programas': total_programas,
                'total_catequistas': total_catequistas,
                'utilizacion_capacidad_pct': 0  # Calcular según capacidad vs catequizandos
            }
            
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de parroquia: {str(e)}")
            return {}
    
    def _check_parroquia_dependencies(self, parroquia_id: int) -> List[str]:
        """Verifica dependencias de la parroquia antes de eliminar."""
        dependencies = []
        
        # Verificar catequizandos
        catequizandos_count = self.db.query(Catequizando).filter(
            Catequizando.parroquia_id == parroquia_id
        ).count()
        if catequizandos_count > 0:
            dependencies.append(f'{catequizandos_count} catequizandos')
        
        # Verificar usuarios
        usuarios_count = self.db.query(Usuario).filter(
            Usuario.parroquia_id == parroquia_id
        ).count()
        if usuarios_count > 0:
            dependencies.append(f'{usuarios_count} usuarios')
        
        # Verificar grupos
        grupos_count = self.db.query(Grupo).filter(
            Grupo.parroquia_id == parroquia_id
        ).count()
        if grupos_count > 0:
            dependencies.append(f'{grupos_count} grupos')
        
        return dependencies
    
    def _handle_parroquia_deactivation(self, parroquia_id: int):
        """Maneja las consecuencias de desactivar una parroquia."""
        # Desactivar grupos activos
        self.db.query(Grupo).filter(
            and_(
                Grupo.parroquia_id == parroquia_id,
                Grupo.activo == True
            )
        ).update({'activo': False, 'updated_at': datetime.utcnow()})
        
        # Marcar catequizandos como inactivos
        self.db.query(Catequizando).filter(
            and_(
                Catequizando.parroquia_id == parroquia_id,
                Catequizando.activo == True
            )
        ).update({'activo': False, 'updated_at': datetime.utcnow()})
    
    def _check_schedule_conflicts(self, parroquia_id: int, horario_data: Dict[str, Any]) -> List[str]:
        """Verifica conflictos de horario en la parroquia."""
        conflicts = []
        
        dia_semana = horario_data['dia_semana']
        hora_inicio = horario_data['hora_inicio']
        hora_fin = horario_data['hora_fin']
        
        # Buscar horarios existentes en el mismo día
        existing_schedules = self.db.query(Horario).filter(
            and_(
                Horario.parroquia_id == parroquia_id,
                Horario.dia_semana == dia_semana,
                Horario.activo == True
            )
        ).all()
        
        for schedule in existing_schedules:
            # Verificar solapamiento de horarios
            if (hora_inicio < schedule.hora_fin and hora_fin > schedule.hora_inicio):
                conflicts.append(f"{schedule.nombre} ({schedule.hora_inicio}-{schedule.hora_fin})")
        
        return conflicts
    
    def _serialize_programa(self, programa: ProgramaCatequesis) -> Dict[str, Any]:
        """Serializa un programa de catequesis."""
        return {
            'id': programa.id,
            'nombre': programa.nombre,
            'descripcion': programa.descripcion,
            'edad_minima': programa.edad_minima,
            'edad_maxima': programa.edad_maxima,
            'duracion_meses': programa.duracion_meses,
            'orden': programa.orden,
            'activo': programa.activo,
            'created_at': programa.created_at.isoformat() if programa.created_at else None
        }
    
    def _serialize_horario(self, horario: Horario) -> Dict[str, Any]:
        """Serializa un horario."""
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        return {
            'id': horario.id,
            'nombre': horario.nombre,
            'dia_semana': horario.dia_semana,
            'dia_semana_nombre': dias_semana[horario.dia_semana],
            'hora_inicio': horario.hora_inicio.strftime('%H:%M'),
            'hora_fin': horario.hora_fin.strftime('%H:%M'),
            'capacidad_maxima': horario.capacidad_maxima,
            'activo': horario.activo,
            'created_at': horario.created_at.isoformat() if horario.created_at else None
        }