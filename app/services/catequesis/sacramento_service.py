"""
Servicio de gestión de sacramentos.
Maneja CRUD de sacramentos, prerequisitos y configuraciones litúrgicas.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.sacramento_model import Sacramento
from app.models.catequesis.inscripcion_model import Inscripcion
from app.models.catequesis.padrino_model import Padrino
from app.schemas.catequesis.sacramento_schema import (
    SacramentoCreateSchema, SacramentoUpdateSchema, SacramentoResponseSchema,
    SacramentoSearchSchema, ConfiguracionLiturgicaSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class SacramentoService(BaseService):
    """Servicio para gestión completa de sacramentos."""
    
    @property
    def model(self) -> Type[Sacramento]:
        return Sacramento
    
    @property
    def create_schema(self) -> Type[SacramentoCreateSchema]:
        return SacramentoCreateSchema
    
    @property
    def update_schema(self) -> Type[SacramentoUpdateSchema]:
        return SacramentoUpdateSchema
    
    @property
    def response_schema(self) -> Type[SacramentoResponseSchema]:
        return SacramentoResponseSchema
    
    @property
    def search_schema(self) -> Type[SacramentoSearchSchema]:
        return SacramentoSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Sacramento.sacramento_prerequisito),
            joinedload(Sacramento.sacramentos_dependientes),
            joinedload(Sacramento.created_by_user),
            joinedload(Sacramento.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para sacramentos."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Sacramento.nombre.ilike(search_term),
                    Sacramento.descripcion.ilike(search_term),
                    Sacramento.nombre_liturgico.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('activo') is not None:
            query = query.filter(Sacramento.activo == search_data['activo'])
        
        if search_data.get('categoria'):
            query = query.filter(Sacramento.categoria == search_data['categoria'])
        
        if search_data.get('es_iniciacion') is not None:
            query = query.filter(Sacramento.es_iniciacion == search_data['es_iniciacion'])
        
        if search_data.get('requiere_padrinos') is not None:
            query = query.filter(Sacramento.requiere_padrinos == search_data['requiere_padrinos'])
        
        if search_data.get('edad_minima'):
            query = query.filter(Sacramento.edad_minima_recomendada >= search_data['edad_minima'])
        
        if search_data.get('edad_maxima'):
            query = query.filter(Sacramento.edad_maxima_recomendada <= search_data['edad_maxima'])
        
        if search_data.get('sin_prerequisitos'):
            query = query.filter(Sacramento.prerequisito_sacramento_id.is_(None))
        
        if search_data.get('con_dependientes'):
            query = query.join(Sacramento.sacramentos_dependientes).filter(
                Sacramento.sacramentos_dependientes.any()
            )
        
        return query
    
    @require_permission('sacramentos', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar nombre único
        if self.exists(nombre=data['nombre']):
            raise ValidationException("Ya existe un sacramento con ese nombre")
        
        # Validar prerequisito
        if data.get('prerequisito_sacramento_id'):
            self._validate_prerequisite(data['prerequisito_sacramento_id'])
        
        # Validar edades
        if data.get('edad_minima_recomendada') and data.get('edad_maxima_recomendada'):
            if data['edad_minima_recomendada'] > data['edad_maxima_recomendada']:
                raise ValidationException("La edad mínima no puede ser mayor que la máxima")
        
        # Asignar orden automático si no se especifica
        if not data.get('orden_liturgico'):
            data['orden_liturgico'] = self._get_next_liturgical_order()
        
        # Configuraciones por defecto
        data.setdefault('activo', True)
        data.setdefault('es_iniciacion', False)
        data.setdefault('requiere_padrinos', False)
        data.setdefault('requiere_preparacion', True)
        data.setdefault('configuracion_liturgica', self._get_default_liturgical_config())
        
        return data
    
    @require_permission('sacramentos', 'actualizar')
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-actualización para validaciones."""
        # Verificar nombre único (si cambió)
        if 'nombre' in data and data['nombre'] != instance.nombre:
            if self.exists(nombre=data['nombre']):
                raise ValidationException("Ya existe un sacramento con ese nombre")
        
        # Validar prerequisito (si cambió)
        if 'prerequisito_sacramento_id' in data:
            if data['prerequisito_sacramento_id']:
                self._validate_prerequisite(data['prerequisito_sacramento_id'], instance.id)
        
        # Validar edades
        edad_min = data.get('edad_minima_recomendada', instance.edad_minima_recomendada)
        edad_max = data.get('edad_maxima_recomendada', instance.edad_maxima_recomendada)
        if edad_min and edad_max and edad_min > edad_max:
            raise ValidationException("La edad mínima no puede ser mayor que la máxima")
        
        return data
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar el sacramento."""
        # Verificar dependencias
        dependencies = self._check_sacramento_dependencies(instance.id)
        if dependencies:
            raise BusinessLogicException(f"No se puede eliminar. Tiene dependencias: {', '.join(dependencies)}")
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE SACRAMENTOS
    # ==========================================
    
    def get_sacramentos_iniciacion(self) -> List[Dict[str, Any]]:
        """
        Obtiene los sacramentos de iniciación cristiana.
        
        Returns:
            Lista de sacramentos de iniciación ordenados
        """
        try:
            sacramentos = self.db.query(Sacramento).filter(
                and_(
                    Sacramento.es_iniciacion == True,
                    Sacramento.activo == True
                )
            ).order_by(Sacramento.orden_liturgico).all()
            
            return [self._serialize_response(s) for s in sacramentos]
            
        except Exception as e:
            logger.error(f"Error obteniendo sacramentos de iniciación: {str(e)}")
            raise BusinessLogicException("Error obteniendo sacramentos de iniciación")
    
    def get_ruta_sacramental(self, sacramento_final_id: int) -> Dict[str, Any]:
        """
        Obtiene la ruta sacramental completa hasta un sacramento específico.
        
        Args:
            sacramento_final_id: ID del sacramento final
            
        Returns:
            Dict con la ruta sacramental
        """
        try:
            sacramento_final = self._get_instance_by_id(sacramento_final_id)
            
            ruta = []
            current_sacramento = sacramento_final
            
            # Construir ruta hacia atrás siguiendo prerequisitos
            while current_sacramento:
                sacramento_data = self._serialize_response(current_sacramento)
                ruta.insert(0, sacramento_data)  # Insertar al inicio para orden correcto
                
                # Obtener prerequisito
                if current_sacramento.prerequisito_sacramento_id:
                    current_sacramento = self.db.query(Sacramento).filter(
                        Sacramento.id == current_sacramento.prerequisito_sacramento_id
                    ).first()
                else:
                    current_sacramento = None
            
            # Calcular información adicional
            total_duracion = sum(s.get('duracion_preparacion_meses', 0) for s in ruta if s.get('duracion_preparacion_meses'))
            edad_minima_total = min(s.get('edad_minima_recomendada', 0) for s in ruta if s.get('edad_minima_recomendada'))
            
            return {
                'sacramento_final': sacramento_final.nombre,
                'total_sacramentos': len(ruta),
                'duracion_total_meses': total_duracion,
                'edad_minima_inicio': edad_minima_total,
                'ruta_sacramental': ruta
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ruta sacramental: {str(e)}")
            raise BusinessLogicException("Error obteniendo ruta sacramental")
    
    def get_sacramentos_disponibles_para_catequizando(self, catequizando_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene sacramentos disponibles para un catequizando específico.
        
        Args:
            catequizando_id: ID del catequizando
            
        Returns:
            Lista de sacramentos disponibles
        """
        try:
            from app.models.catequesis.catequizando_model import Catequizando
            
            # Obtener catequizando
            catequizando = self.db.query(Catequizando).filter(
                Catequizando.id == catequizando_id
            ).first()
            
            if not catequizando:
                raise NotFoundException("Catequizando no encontrado")
            
            # Obtener sacramentos ya recibidos/en proceso
            sacramentos_en_proceso = set()
            inscripciones = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.catequizando_id == catequizando_id,
                    Inscripcion.estado.in_(['activa', 'en_progreso', 'completado'])
                )
            ).all()
            
            for inscripcion in inscripciones:
                if inscripcion.sacramento_objetivo_id:
                    sacramentos_en_proceso.add(inscripcion.sacramento_objetivo_id)
            
            # Obtener todos los sacramentos activos
            sacramentos = self.db.query(Sacramento).filter(
                Sacramento.activo == True
            ).order_by(Sacramento.orden_liturgico).all()
            
            # Filtrar sacramentos disponibles
            sacramentos_disponibles = []
            edad_catequizando = self._calculate_age(catequizando.fecha_nacimiento)
            
            for sacramento in sacramentos:
                # Saltar si ya está en proceso o completado
                if sacramento.id in sacramentos_en_proceso:
                    continue
                
                # Verificar edad
                if sacramento.edad_minima_recomendada and edad_catequizando < sacramento.edad_minima_recomendada:
                    continue
                
                if sacramento.edad_maxima_recomendada and edad_catequizando > sacramento.edad_maxima_recomendada:
                    continue
                
                # Verificar prerequisito
                if sacramento.prerequisito_sacramento_id:
                    prerequisito_completado = any(
                        insc.sacramento_objetivo_id == sacramento.prerequisito_sacramento_id and insc.estado == 'completado'
                        for insc in inscripciones
                    )
                    
                    if not prerequisito_completado:
                        continue
                
                sacramento_data = self._serialize_response(sacramento)
                sacramento_data['razon_disponible'] = self._get_availability_reason(sacramento, catequizando, sacramentos_en_proceso)
                sacramentos_disponibles.append(sacramento_data)
            
            return sacramentos_disponibles
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo sacramentos disponibles: {str(e)}")
            raise BusinessLogicException("Error obteniendo sacramentos disponibles")
    
    @require_permission('sacramentos', 'administrar')
    def configurar_liturgia(self, sacramento_id: int, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configura aspectos litúrgicos de un sacramento.
        
        Args:
            sacramento_id: ID del sacramento
            config_data: Configuración litúrgica
            
        Returns:
            Dict con la configuración actualizada
        """
        try:
            sacramento = self._get_instance_by_id(sacramento_id)
            
            # Validar configuración
            schema = ConfiguracionLiturgicaSchema()
            validated_config = schema.load(config_data)
            
            # Actualizar configuración
            current_config = sacramento.configuracion_liturgica or {}
            current_config.update(validated_config)
            sacramento.configuracion_liturgica = current_config
            sacramento.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Configuración litúrgica actualizada para sacramento {sacramento.nombre}")
            
            return {
                'success': True,
                'configuracion': current_config,
                'mensaje': 'Configuración litúrgica actualizada exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error configurando liturgia: {str(e)}")
            raise BusinessLogicException("Error configurando liturgia")
    
    @require_permission('sacramentos', 'administrar')
    def reordenar_sacramentos(self, orden_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reordena los sacramentos según el orden litúrgico.
        
        Args:
            orden_data: Lista con {sacramento_id, nuevo_orden}
            
        Returns:
            Dict con confirmación
        """
        try:
            # Validar que todos los sacramentos existen
            sacramento_ids = [item['sacramento_id'] for item in orden_data]
            sacramentos = self.db.query(Sacramento).filter(
                Sacramento.id.in_(sacramento_ids)
            ).all()
            
            if len(sacramentos) != len(sacramento_ids):
                raise ValidationException("Algunos sacramentos no fueron encontrados")
            
            # Aplicar nuevo orden
            for item in orden_data:
                sacramento = next(s for s in sacramentos if s.id == item['sacramento_id'])
                sacramento.orden_liturgico = item['nuevo_orden']
                sacramento.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Sacramentos reordenados: {len(orden_data)} items")
            
            return {
                'success': True,
                'message': 'Sacramentos reordenados exitosamente',
                'total_reordenados': len(orden_data)
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error reordenando sacramentos: {str(e)}")
            raise BusinessLogicException("Error reordenando sacramentos")
    
    def get_estadisticas_sacramento(self, sacramento_id: int) -> Dict[str, Any]:
        """
        Obtiene estadísticas específicas de un sacramento.
        
        Args:
            sacramento_id: ID del sacramento
            
        Returns:
            Dict con estadísticas del sacramento
        """
        try:
            sacramento = self._get_instance_by_id(sacramento_id)
            
            # Inscripciones por estado
            inscripciones_stats = self.db.query(
                Inscripcion.estado, func.count(Inscripcion.id)
            ).filter(
                Inscripcion.sacramento_objetivo_id == sacramento_id
            ).group_by(Inscripcion.estado).all()
            
            # Padrinos asignados
            total_padrinos = self.db.query(Padrino).filter(
                and_(
                    Padrino.sacramento_id == sacramento_id,
                    Padrino.activo == True
                )
            ).count()
            
            # Distribución por edad de catequizandos
            from app.models.catequesis.catequizando_model import Catequizando
            
            edad_distribution = self.db.query(
                func.extract('year', func.age(func.current_date(), Catequizando.fecha_nacimiento)).label('edad'),
                func.count(Catequizando.id).label('count')
            ).join(Inscripcion).filter(
                and_(
                    Inscripcion.sacramento_objetivo_id == sacramento_id,
                    Inscripcion.estado.in_(['activa', 'en_progreso', 'completado'])
                )
            ).group_by('edad').all()
            
            # Tiempo promedio de preparación
            tiempo_promedio = self.db.query(
                func.avg(func.extract('day', func.age(Inscripcion.fecha_finalizacion, Inscripcion.fecha_inscripcion)))
            ).filter(
                and_(
                    Inscripcion.sacramento_objetivo_id == sacramento_id,
                    Inscripcion.estado == 'completado',
                    Inscripcion.fecha_finalizacion.isnot(None)
                )
            ).scalar() or 0
            
            return {
                'sacramento_nombre': sacramento.nombre,
                'total_inscripciones': sum(count for _, count in inscripciones_stats),
                'inscripciones_por_estado': {estado: count for estado, count in inscripciones_stats},
                'total_padrinos_asignados': total_padrinos,
                'distribucion_edades': {int(edad): count for edad, count in edad_distribution if edad},
                'tiempo_promedio_preparacion_dias': round(tiempo_promedio, 1),
                'requiere_padrinos': sacramento.requiere_padrinos,
                'edad_recomendada': {
                    'minima': sacramento.edad_minima_recomendada,
                    'maxima': sacramento.edad_maxima_recomendada
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de sacramento: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas del sacramento")
    
    def inicializar_sacramentos_basicos(self) -> Dict[str, Any]:
        """
        Inicializa los sacramentos básicos del sistema.
        
        Returns:
            Dict con estadísticas de inicialización
        """
        try:
            sacramentos_basicos = [
                {
                    'nombre': 'Bautismo',
                    'nombre_liturgico': 'Sacramento del Bautismo',
                    'descripcion': 'Primer sacramento de iniciación cristiana',
                    'categoria': 'iniciacion',
                    'es_iniciacion': True,
                    'requiere_padrinos': True,
                    'requiere_preparacion': True,
                    'edad_minima_recomendada': 0,
                    'edad_maxima_recomendada': None,
                    'duracion_preparacion_meses': 3,
                    'orden_liturgico': 1,
                    'activo': True
                },
                {
                    'nombre': 'Primera Comunión',
                    'nombre_liturgico': 'Primera Comunión Eucarística',
                    'descripcion': 'Segundo sacramento de iniciación cristiana',
                    'categoria': 'iniciacion',
                    'es_iniciacion': True,
                    'requiere_padrinos': False,
                    'requiere_preparacion': True,
                    'edad_minima_recomendada': 8,
                    'edad_maxima_recomendada': 12,
                    'duracion_preparacion_meses': 12,
                    'orden_liturgico': 2,
                    'activo': True
                },
                {
                    'nombre': 'Confirmación',
                    'nombre_liturgico': 'Sacramento de la Confirmación',
                    'descripcion': 'Tercer sacramento de iniciación cristiana',
                    'categoria': 'iniciacion',
                    'es_iniciacion': True,
                    'requiere_padrinos': True,
                    'requiere_preparacion': True,
                    'edad_minima_recomendada': 14,
                    'edad_maxima_recomendada': None,
                    'duracion_preparacion_meses': 24,
                    'orden_liturgico': 3,
                    'activo': True
                },
                {
                    'nombre': 'Matrimonio',
                    'nombre_liturgico': 'Sacramento del Matrimonio',
                    'descripcion': 'Sacramento del amor conyugal',
                    'categoria': 'servicio',
                    'es_iniciacion': False,
                    'requiere_padrinos': True,
                    'requiere_preparacion': True,
                    'edad_minima_recomendada': 18,
                    'edad_maxima_recomendada': None,
                    'duracion_preparacion_meses': 6,
                    'orden_liturgico': 4,
                    'activo': True
                }
            ]
            
            sacramentos_creados = 0
            
            for sacramento_data in sacramentos_basicos:
                # Verificar si ya existe
                existing = self.db.query(Sacramento).filter(
                    Sacramento.nombre == sacramento_data['nombre']
                ).first()
                
                if not existing:
                    sacramento_data['configuracion_liturgica'] = self._get_default_liturgical_config()
                    sacramento_data['created_at'] = datetime.utcnow()
                    
                    sacramento = Sacramento(**sacramento_data)
                    self.db.add(sacramento)
                    sacramentos_creados += 1
            
            # Establecer prerequisitos
            if sacramentos_creados > 0:
                self.db.flush()  # Para obtener los IDs
                
                # Bautismo como prerequisito de Primera Comunión
                bautismo = self.db.query(Sacramento).filter(Sacramento.nombre == 'Bautismo').first()
                primera_comunion = self.db.query(Sacramento).filter(Sacramento.nombre == 'Primera Comunión').first()
                confirmacion = self.db.query(Sacramento).filter(Sacramento.nombre == 'Confirmación').first()
                
                if bautismo and primera_comunion:
                    primera_comunion.prerequisito_sacramento_id = bautismo.id
                
                if primera_comunion and confirmacion:
                    confirmacion.prerequisito_sacramento_id = primera_comunion.id
            
            self.db.commit()
            
            logger.info(f"Sacramentos básicos inicializados: {sacramentos_creados} creados")
            
            return {
                'success': True,
                'sacramentos_creados': sacramentos_creados,
                'total_sacramentos': len(sacramentos_basicos),
                'mensaje': 'Sacramentos básicos inicializados exitosamente'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inicializando sacramentos: {str(e)}")
            raise BusinessLogicException("Error inicializando sacramentos básicos")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de sacramentos."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de sacramentos
            total_sacramentos = self.db.query(Sacramento).count()
            sacramentos_activos = self.db.query(Sacramento).filter(Sacramento.activo == True).count()
            
            # Distribución por categoría
            categoria_distribution = self.db.query(
                Sacramento.categoria, func.count(Sacramento.id)
            ).filter(
                Sacramento.activo == True
            ).group_by(Sacramento.categoria).all()
            
            # Sacramentos de iniciación
            iniciacion_count = self.db.query(Sacramento).filter(
                and_(
                    Sacramento.es_iniciacion == True,
                    Sacramento.activo == True
                )
            ).count()
            
            # Sacramentos que requieren padrinos
            con_padrinos = self.db.query(Sacramento).filter(
                and_(
                    Sacramento.requiere_padrinos == True,
                    Sacramento.activo == True
                )
            ).count()
            
            # Promedio de duración de preparación
            duracion_promedio = self.db.query(
                func.avg(Sacramento.duracion_preparacion_meses)
            ).filter(
                and_(
                    Sacramento.activo == True,
                    Sacramento.duracion_preparacion_meses.isnot(None)
                )
            ).scalar() or 0
            
            # Sacramento más popular (más inscripciones)
            sacramento_popular = self.db.query(
                Sacramento.nombre, func.count(Inscripcion.id).label('total_inscripciones')
            ).join(Inscripcion).filter(
                Sacramento.activo == True
            ).group_by(Sacramento.id, Sacramento.nombre).order_by(
                func.count(Inscripcion.id).desc()
            ).first()
            
            base_stats.update({
                'total_sacramentos': total_sacramentos,
                'sacramentos_activos': sacramentos_activos,
                'sacramentos_inactivos': total_sacramentos - sacramentos_activos,
                'distribucion_categorias': {cat: count for cat, count in categoria_distribution},
                'sacramentos_iniciacion': iniciacion_count,
                'sacramentos_con_padrinos': con_padrinos,
                'duracion_promedio_preparacion': round(duracion_promedio, 1),
                'sacramento_mas_popular': {
                    'nombre': sacramento_popular[0] if sacramento_popular else None,
                    'inscripciones': sacramento_popular[1] if sacramento_popular else 0
                }
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de sacramentos: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _validate_prerequisite(self, prerequisito_id: int, exclude_id: int = None):
        """Valida que el prerequisito sea válido."""
        # Verificar que el prerequisito existe
        prerequisito = self.db.query(Sacramento).filter(
            Sacramento.id == prerequisito_id
        ).first()
        
        if not prerequisito:
            raise ValidationException("El sacramento prerequisito no existe")
        
        # Verificar que no se cree un ciclo
        if exclude_id and self._creates_cycle(prerequisito_id, exclude_id):
            raise ValidationException("La relación de prerequisito crearía un ciclo")
    
    def _creates_cycle(self, prerequisito_id: int, sacramento_id: int) -> bool:
        """Verifica si la relación de prerequisito crearía un ciclo."""
        visited = set()
        current = prerequisito_id
        
        while current and current not in visited:
            if current == sacramento_id:
                return True
            
            visited.add(current)
            sacramento = self.db.query(Sacramento).filter(Sacramento.id == current).first()
            current = sacramento.prerequisito_sacramento_id if sacramento else None
        
        return False
    
    def _get_next_liturgical_order(self) -> int:
        """Obtiene el siguiente número de orden litúrgico."""
        max_order = self.db.query(func.max(Sacramento.orden_liturgico)).scalar()
        return (max_order or 0) + 1
    
    def _get_default_liturgical_config(self) -> Dict[str, Any]:
        """Obtiene la configuración litúrgica por defecto."""
        return {
            'color_liturgico': 'blanco',
            'textos_especiales': [],
            'cantos_recomendados': [],
            'duracion_estimada_minutos': 60,
            'elementos_necesarios': [],
            'observaciones_liturgicas': ''
        }
    
    def _check_sacramento_dependencies(self, sacramento_id: int) -> List[str]:
        """Verifica dependencias del sacramento antes de eliminar."""
        dependencies = []
        
        # Verificar inscripciones
        inscripciones_count = self.db.query(Inscripcion).filter(
            Inscripcion.sacramento_objetivo_id == sacramento_id
        ).count()
        if inscripciones_count > 0:
            dependencies.append(f'{inscripciones_count} inscripciones')
        
        # Verificar padrinos
        padrinos_count = self.db.query(Padrino).filter(
            Padrino.sacramento_id == sacramento_id
        ).count()
        if padrinos_count > 0:
            dependencies.append(f'{padrinos_count} padrinos')
        
        # Verificar si es prerequisito de otros sacramentos
        dependientes_count = self.db.query(Sacramento).filter(
            Sacramento.prerequisito_sacramento_id == sacramento_id
        ).count()
        if dependientes_count > 0:
            dependencies.append(f'{dependientes_count} sacramentos dependientes')
        
        return dependencies
    
    def _calculate_age(self, fecha_nacimiento: date) -> int:
        """Calcula la edad en años."""
        if not fecha_nacimiento:
            return 0
        
        today = date.today()
        return today.year - fecha_nacimiento.year - (
            (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
    
    def _get_availability_reason(self, sacramento: Sacramento, catequizando, sacramentos_en_proceso: set) -> str:
       """Obtiene la razón por la cual un sacramento está disponible."""
       if not sacramento.prerequisito_sacramento_id:
           return "Sacramento inicial - no requiere prerequisitos"
       
       return "Prerequisitos cumplidos satisfactoriamente"