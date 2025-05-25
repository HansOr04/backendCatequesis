"""
Servicio de gestión de grupos de catequesis.
Maneja CRUD de grupos, asignaciones, horarios y seguimiento.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.grupo_model import Grupo
from app.models.catequesis.inscripcion_model import Inscripcion
from app.models.catequesis.asistencia_model import Asistencia
from app.models.seguridad.usuario_model import Usuario
from app.models.catequesis.nivel_model import Nivel
from app.schemas.catequesis.grupo_schema import (
    GrupoCreateSchema, GrupoUpdateSchema, GrupoResponseSchema,
    GrupoSearchSchema, HorarioGrupoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class GrupoService(BaseService):
    """Servicio para gestión completa de grupos de catequesis."""
    
    @property
    def model(self) -> Type[Grupo]:
        return Grupo
    
    @property
    def create_schema(self) -> Type[GrupoCreateSchema]:
        return GrupoCreateSchema
    
    @property
    def update_schema(self) -> Type[GrupoUpdateSchema]:
        return GrupoUpdateSchema
    
    @property
    def response_schema(self) -> Type[GrupoResponseSchema]:
        return GrupoResponseSchema
    
    @property
    def search_schema(self) -> Type[GrupoSearchSchema]:
        return GrupoSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Grupo.parroquia),
            joinedload(Grupo.nivel),
            joinedload(Grupo.catequista_principal),
            joinedload(Grupo.catequista_auxiliar),
            joinedload(Grupo.inscripciones),
            joinedload(Grupo.horarios),
            joinedload(Grupo.created_by_user),
            joinedload(Grupo.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para grupos."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Grupo.nombre.ilike(search_term),
                    Grupo.descripcion.ilike(search_term),
                    Grupo.codigo_grupo.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('activo') is not None:
            query = query.filter(Grupo.activo == search_data['activo'])
        
        if search_data.get('parroquia_id'):
            query = query.filter(Grupo.parroquia_id == search_data['parroquia_id'])
        
        if search_data.get('nivel_id'):
            query = query.filter(Grupo.nivel_id == search_data['nivel_id'])
        
        if search_data.get('catequista_id'):
            query = query.filter(
                or_(
                    Grupo.catequista_principal_id == search_data['catequista_id'],
                    Grupo.catequista_auxiliar_id == search_data['catequista_id']
                )
            )
        
        if search_data.get('año'):
            query = query.filter(Grupo.año == search_data['año'])
        
        if search_data.get('periodo'):
            query = query.filter(Grupo.periodo == search_data['periodo'])
        
        # Filtros de capacidad
        if search_data.get('con_cupos_disponibles'):
            query = query.filter(Grupo.cupos_ocupados < Grupo.capacidad_maxima)
        
        if search_data.get('capacidad_minima'):
            query = query.filter(Grupo.capacidad_maxima >= search_data['capacidad_minima'])
        
        # Filtros de estado
        if search_data.get('solo_con_catequista'):
            query = query.filter(Grupo.catequista_principal_id.isnot(None))
        
        if search_data.get('sin_catequista'):
            query = query.filter(Grupo.catequista_principal_id.is_(None))
        
        # Filtros de horario
        if search_data.get('dia_semana'):
            from app.models.catequesis.horario_grupo_model import HorarioGrupo
            query = query.join(HorarioGrupo).filter(
                HorarioGrupo.dia_semana == search_data['dia_semana']
            )
        
        return query
    
    @require_permission('grupos', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que el nivel existe y está activo
        if data.get('nivel_id'):
            nivel = self.db.query(Nivel).filter(Nivel.id == data['nivel_id']).first()
            if not nivel:
                raise NotFoundException("Nivel no encontrado")
            if not nivel.activo:
                raise ValidationException("El nivel no está activo")
        
        # Verificar catequistas si se asignan
        if data.get('catequista_principal_id'):
            self._validate_catequista(data['catequista_principal_id'], data['parroquia_id'])
        
        if data.get('catequista_auxiliar_id'):
            self._validate_catequista(data['catequista_auxiliar_id'], data['parroquia_id'])
            
            # No puede ser el mismo catequista
            if data['catequista_auxiliar_id'] == data.get('catequista_principal_id'):
                raise ValidationException("El catequista principal y auxiliar no pueden ser la misma persona")
        
        # Generar código único si no se proporciona
        if not data.get('codigo_grupo'):
            data['codigo_grupo'] = self._generate_group_code(data['parroquia_id'], data.get('nivel_id'))
        
        # Configuraciones por defecto
        data.setdefault('activo', True)
        data.setdefault('año', datetime.now().year)
        data.setdefault('capacidad_maxima', 25)
        data.setdefault('cupos_ocupados', 0)
        data.setdefault('estado', 'planificado')
        
        return data
    
    @require_permission('grupos', 'actualizar')
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-actualización para validaciones."""
        # Verificar catequistas si se cambian
        if 'catequista_principal_id' in data and data['catequista_principal_id']:
            self._validate_catequista(data['catequista_principal_id'], instance.parroquia_id)
        
        if 'catequista_auxiliar_id' in data and data['catequista_auxiliar_id']:
            self._validate_catequista(data['catequista_auxiliar_id'], instance.parroquia_id)
            
            principal_id = data.get('catequista_principal_id', instance.catequista_principal_id)
            if data['catequista_auxiliar_id'] == principal_id:
                raise ValidationException("El catequista principal y auxiliar no pueden ser la misma persona")
        
        # Validar capacidad
        if 'capacidad_maxima' in data:
            if data['capacidad_maxima'] < instance.cupos_ocupados:
                raise ValidationException("La nueva capacidad no puede ser menor a los cupos ocupados actuales")
        
        return data
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar el grupo."""
        # Verificar inscripciones activas
        inscripciones_activas = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.grupo_id == instance.id,
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).count()
        
        if inscripciones_activas > 0:
            raise BusinessLogicException(f"No se puede eliminar. Tiene {inscripciones_activas} inscripciones activas")
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE GRUPOS
    # ==========================================
    
    def get_grupo_completo(self, grupo_id: int) -> Dict[str, Any]:
        """
        Obtiene información completa de un grupo.
        
        Args:
            grupo_id: ID del grupo
            
        Returns:
            Dict con información completa
        """
        try:
            grupo = self._get_instance_by_id(grupo_id)
            
            # Información básica
            result = self._serialize_response(grupo)
            
            # Inscripciones del grupo
            result['inscripciones'] = self._get_inscripciones_grupo(grupo_id)
            
            # Horarios del grupo
            result['horarios'] = self._get_horarios_grupo(grupo_id)
            
            # Estadísticas del grupo
            result['estadisticas'] = self._get_estadisticas_grupo(grupo_id)
            
            # Progreso del grupo
            result['progreso'] = self._get_progreso_grupo(grupo_id)
            
            # Próximas clases
            result['proximas_clases'] = self._get_proximas_clases(grupo_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo grupo completo: {str(e)}")
            raise BusinessLogicException("Error obteniendo información del grupo")
    
    @require_permission('grupos', 'administrar')
    def asignar_catequista(self, grupo_id: int, catequista_id: int, es_principal: bool = True) -> Dict[str, Any]:
        """
        Asigna un catequista a un grupo.
        
        Args:
            grupo_id: ID del grupo
            catequista_id: ID del catequista
            es_principal: Si es catequista principal o auxiliar
            
        Returns:
            Dict con confirmación
        """
        try:
            grupo = self._get_instance_by_id(grupo_id)
            
            # Validar catequista
            self._validate_catequista(catequista_id, grupo.parroquia_id)
            
            # Realizar asignación
            if es_principal:
                # Mover principal actual a auxiliar si no hay auxiliar
                if grupo.catequista_principal_id and not grupo.catequista_auxiliar_id:
                    grupo.catequista_auxiliar_id = grupo.catequista_principal_id
                
                grupo.catequista_principal_id = catequista_id
            else:
                if grupo.catequista_auxiliar_id:
                    raise ValidationException("El grupo ya tiene un catequista auxiliar")
                
                grupo.catequista_auxiliar_id = catequista_id
            
            grupo.fecha_ultima_asignacion = datetime.utcnow()
            grupo.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            tipo = "principal" if es_principal else "auxiliar"
            logger.info(f"Catequista {catequista_id} asignado como {tipo} al grupo {grupo_id}")
            
            return {
                'success': True,
                'tipo_asignacion': tipo,
                'mensaje': f'Catequista asignado como {tipo} exitosamente'
            }
            
        except (ValidationException, NotFoundException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error asignando catequista: {str(e)}")
            raise BusinessLogicException("Error asignando catequista al grupo")
    
    @require_permission('grupos', 'administrar')
    def remover_catequista(self, grupo_id: int, catequista_id: int) -> Dict[str, Any]:
        """
        Remueve un catequista de un grupo.
        
        Args:
            grupo_id: ID del grupo
            catequista_id: ID del catequista
            
        Returns:
            Dict con confirmación
        """
        try:
            grupo = self._get_instance_by_id(grupo_id)
            
            tipo_remocion = None
            if grupo.catequista_principal_id == catequista_id:
                grupo.catequista_principal_id = None
                tipo_remocion = "principal"
                
                # Promover auxiliar a principal si existe
                if grupo.catequista_auxiliar_id:
                    grupo.catequista_principal_id = grupo.catequista_auxiliar_id
                    grupo.catequista_auxiliar_id = None
                    tipo_remocion += " (auxiliar promovido)"
                    
            elif grupo.catequista_auxiliar_id == catequista_id:
                grupo.catequista_auxiliar_id = None
                tipo_remocion = "auxiliar"
            else:
                raise ValidationException("El catequista no está asignado a este grupo")
            
            grupo.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Catequista {catequista_id} removido del grupo {grupo_id}")
            
            return {
                'success': True,
                'tipo_remocion': tipo_remocion,
                'mensaje': f'Catequista removido como {tipo_remocion} exitosamente'
            }
            
        except (ValidationException, NotFoundException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removiendo catequista: {str(e)}")
            raise BusinessLogicException("Error removiendo catequista del grupo")
    
    def crear_horario(self, grupo_id: int, horario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un horario para un grupo.
        
        Args:
            grupo_id: ID del grupo
            horario_data: Datos del horario
            
        Returns:
            Dict con el horario creado
        """
        try:
            grupo = self._get_instance_by_id(grupo_id)
            
            schema = HorarioGrupoSchema()
            validated_data = schema.load(horario_data)
            
            # Verificar conflictos de horario
            conflicts = self._check_schedule_conflicts(grupo_id, validated_data)
            if conflicts:
                raise ValidationException(f"Conflicto de horario: {', '.join(conflicts)}")
            
            # Crear horario
            from app.models.catequesis.horario_grupo_model import HorarioGrupo
            
            horario = HorarioGrupo(
                grupo_id=grupo_id,
                dia_semana=validated_data['dia_semana'],
                hora_inicio=validated_data['hora_inicio'],
                hora_fin=validated_data['hora_fin'],
                aula=validated_data.get('aula'),
                observaciones=validated_data.get('observaciones'),
                activo=True,
                created_at=datetime.utcnow(),
                created_by=self.current_user.get('id') if self.current_user else None
            )
            
            self.db.add(horario)
            self.db.commit()
            
            logger.info(f"Horario creado para grupo {grupo_id}")
            
            return self._serialize_horario(horario)
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando horario: {str(e)}")
            raise BusinessLogicException("Error creando horario del grupo")
    
    @require_permission('grupos', 'administrar')
    def cambiar_estado(self, grupo_id: int, nuevo_estado: str, observaciones: str = None) -> Dict[str, Any]:
        """
        Cambia el estado de un grupo.
        
        Args:
            grupo_id: ID del grupo
            nuevo_estado: Nuevo estado
            observaciones: Observaciones del cambio
            
        Returns:
            Dict con confirmación
        """
        try:
            grupo = self._get_instance_by_id(grupo_id)
            
            estados_validos = ['planificado', 'activo', 'suspendido', 'finalizado', 'cancelado']
            if nuevo_estado not in estados_validos:
                raise ValidationException(f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}")
            
            # Validar transiciones de estado
            self._validate_state_transition(grupo.estado, nuevo_estado)
            
            estado_anterior = grupo.estado
            grupo.estado = nuevo_estado
            grupo.updated_at = datetime.utcnow()
            
            # Registrar cambio de estado
            self._register_state_change(grupo_id, estado_anterior, nuevo_estado, observaciones)
            
            # Manejar consecuencias del cambio de estado
            self._handle_state_change_consequences(grupo, nuevo_estado)
            
            self.db.commit()
            
            logger.info(f"Estado del grupo {grupo_id} cambiado de {estado_anterior} a {nuevo_estado}")
            
            return {
                'success': True,
                'estado_anterior': estado_anterior,
                'estado_nuevo': nuevo_estado,
                'mensaje': f'Estado cambiado a {nuevo_estado} exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando estado: {str(e)}")
            raise BusinessLogicException("Error cambiando estado del grupo")
    
    def inscribir_catequizando(self, grupo_id: int, catequizando_id: int) -> Dict[str, Any]:
        """
        Inscribe un catequizando en un grupo.
        
        Args:
            grupo_id: ID del grupo
            catequizando_id: ID del catequizando
            
        Returns:
            Dict con la inscripción creada
        """
        try:
            grupo = self._get_instance_by_id(grupo_id)
            
            # Verificar capacidad
            if grupo.cupos_ocupados >= grupo.capacidad_maxima:
                raise ValidationException("El grupo no tiene cupos disponibles")
            
            # Verificar que el grupo esté activo
            if grupo.estado not in ['planificado', 'activo']:
                raise ValidationException("Solo se puede inscribir en grupos planificados o activos")
            
            # Crear inscripción
            from app.services.catequesis.inscripcion_service import InscripcionService
            inscripcion_service = InscripcionService(self.db, self.current_user)
            
            inscripcion_data = {
                'catequizando_id': catequizando_id,
                'grupo_id': grupo_id,
                'nivel_id': grupo.nivel_id,
                'fecha_inscripcion': date.today(),
                'estado': 'activa'
            }
            
            inscripcion = inscripcion_service.create(inscripcion_data)
            
            # Actualizar cupos del grupo
            grupo.cupos_ocupados += 1
            if grupo.cupos_ocupados == grupo.capacidad_maxima:
                grupo.estado = 'completo'
            
            grupo.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Catequizando {catequizando_id} inscrito en grupo {grupo_id}")
            
            return inscripcion
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inscribiendo catequizando: {str(e)}")
            raise BusinessLogicException("Error inscribiendo catequizando en el grupo")
    
    def get_grupos_disponibles_para_inscripcion(self, filtros: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Obtiene grupos disponibles para inscripción.
        
        Args:
            filtros: Filtros adicionales
            
        Returns:
            Lista de grupos disponibles
        """
        try:
            filtros = filtros or {}
            
            query = self._build_base_query().filter(
                and_(
                    Grupo.activo == True,
                    Grupo.estado.in_(['planificado', 'activo']),
                    Grupo.cupos_ocupados < Grupo.capacidad_maxima
                )
            )
            
            # Aplicar filtros
            if filtros.get('parroquia_id'):
                query = query.filter(Grupo.parroquia_id == filtros['parroquia_id'])
            
            if filtros.get('nivel_id'):
                query = query.filter(Grupo.nivel_id == filtros['nivel_id'])
            
            if filtros.get('dia_semana'):
                from app.models.catequesis.horario_grupo_model import HorarioGrupo
                query = query.join(HorarioGrupo).filter(
                    HorarioGrupo.dia_semana == filtros['dia_semana']
                )
            
            grupos = query.order_by(Grupo.nombre).all()
            
            # Agregar información de disponibilidad
            result = []
            for grupo in grupos:
                grupo_data = self._serialize_response(grupo)
                grupo_data['cupos_disponibles'] = grupo.capacidad_maxima - grupo.cupos_ocupados
                grupo_data['porcentaje_ocupacion'] = round((grupo.cupos_ocupados / grupo.capacidad_maxima) * 100, 1)
                grupo_data['horarios'] = self._get_horarios_grupo(grupo.id)
                result.append(grupo_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo grupos disponibles: {str(e)}")
            raise BusinessLogicException("Error obteniendo grupos disponibles")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de grupos."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de grupos
            total_grupos = self.db.query(Grupo).count()
            grupos_activos = self.db.query(Grupo).filter(Grupo.activo == True).count()
            
            # Distribución por estado
            estado_distribution = self.db.query(
                Grupo.estado, func.count(Grupo.id)
            ).group_by(Grupo.estado).all()
            
            # Distribución por parroquia
            parroquia_distribution = self.db.query(
                Grupo.parroquia_id, func.count(Grupo.id)
            ).filter(
                Grupo.activo == True
            ).group_by(Grupo.parroquia_id).all()
            
            # Estadísticas de ocupación
            ocupacion_stats = self.db.query(
                func.avg(Grupo.cupos_ocupados).label('promedio_ocupados'),
                func.avg(Grupo.capacidad_maxima).label('promedio_capacidad'),
                func.sum(Grupo.cupos_ocupados).label('total_ocupados'),
                func.sum(Grupo.capacidad_maxima).label('total_capacidad')
            ).filter(Grupo.activo == True).first()
            
            # Grupos sin catequista
            sin_catequista = self.db.query(Grupo).filter(
                and_(
                    Grupo.activo == True,
                    Grupo.catequista_principal_id.is_(None)
                )
            ).count()
            
            # Grupos por nivel
            nivel_distribution = self.db.query(
                Nivel.nombre, func.count(Grupo.id)
            ).join(Grupo).filter(
                Grupo.activo == True
            ).group_by(Nivel.id, Nivel.nombre).all()
            
            tasa_ocupacion = 0
            if ocupacion_stats and ocupacion_stats.total_capacidad:
                tasa_ocupacion = round((ocupacion_stats.total_ocupados / ocupacion_stats.total_capacidad) * 100, 1)
            
            base_stats.update({
                'total_grupos': total_grupos,
                'grupos_activos': grupos_activos,
                'grupos_inactivos': total_grupos - grupos_activos,
                'distribucion_estados': {estado: count for estado, count in estado_distribution},
                'distribucion_parroquias': {str(pid): count for pid, count in parroquia_distribution},
                'distribucion_niveles': {nivel: count for nivel, count in nivel_distribution},
                'sin_catequista_principal': sin_catequista,
                'promedio_ocupados_por_grupo': round(ocupacion_stats.promedio_ocupados, 1) if ocupacion_stats and ocupacion_stats.promedio_ocupados else 0,
                'promedio_capacidad_por_grupo': round(ocupacion_stats.promedio_capacidad, 1) if ocupacion_stats and ocupacion_stats.promedio_capacidad else 0,
                'tasa_ocupacion_global': tasa_ocupacion,
                'total_cupos_disponibles': (ocupacion_stats.total_capacidad - ocupacion_stats.total_ocupados) if ocupacion_stats else 0
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de grupos: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _validate_catequista(self, catequista_id: int, parroquia_id: int):
        """Valida que el catequista existe y puede ser asignado."""
        catequista = self.db.query(Usuario).filter(Usuario.id == catequista_id).first()
        
        if not catequista:
            raise NotFoundException("Catequista no encontrado")
        
        if not catequista.activo:
            raise ValidationException("El catequista no está activo")
        
        # Verificar que tiene rol de catequista
        from app.models.seguridad.rol_model import Rol
        from app.models.seguridad.usuario_rol_model import UsuarioRol
        
        has_catequista_role = self.db.query(UsuarioRol).join(Rol).filter(
            and_(
                UsuarioRol.usuario_id == catequista_id,
                Rol.nombre == 'catequista'
            )
        ).first()
        
        if not has_catequista_role:
            raise ValidationException("El usuario debe tener rol de catequista")
        
        # Verificar que pertenece a la misma parroquia
        if catequista.parroquia_id != parroquia_id:
            raise ValidationException("El catequista debe pertenecer a la misma parroquia que el grupo")
    
    def _generate_group_code(self, parroquia_id: int, nivel_id: int = None) -> str:
        """Genera un código único para el grupo."""
        import random
        import string
        
        # Prefijo basado en parroquia y nivel
        prefix = f"P{parroquia_id:03d}"
        if nivel_id:
            prefix += f"N{nivel_id:02d}"
        
        # Número secuencial
        year = datetime.now().year
        existing_count = self.db.query(Grupo).filter(
            and_(
                Grupo.parroquia_id == parroquia_id,
                Grupo.año == year
            )
        ).count()
        
        sequence = f"{existing_count + 1:03d}"
        
        return f"{prefix}-{year}-{sequence}"
    
    def _check_schedule_conflicts(self, grupo_id: int, horario_data: Dict[str, Any]) -> List[str]:
        """Verifica conflictos de horario."""
        from app.models.catequesis.horario_grupo_model import HorarioGrupo
        
        conflicts = []
        dia_semana = horario_data['dia_semana']
        hora_inicio = horario_data['hora_inicio']
        hora_fin = horario_data['hora_fin']
        aula = horario_data.get('aula')
        
        # Verificar conflictos con otros grupos en la misma parroquia
        grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
        
        conflicting_schedules = self.db.query(HorarioGrupo).join(Grupo).filter(
            and_(
                Grupo.parroquia_id == grupo.parroquia_id,
                HorarioGrupo.dia_semana == dia_semana,
                HorarioGrupo.activo == True,
                HorarioGrupo.grupo_id != grupo_id
            )
        ).all()
        
        for schedule in conflicting_schedules:
            # Verificar solapamiento de horarios
            if (hora_inicio < schedule.hora_fin and hora_fin > schedule.hora_inicio):
                # Verificar si es el mismo aula
                if aula and schedule.aula and aula.lower() == schedule.aula.lower():
                    conflicts.append(f"Aula {aula} ocupada por {schedule.grupo.nombre}")
                
                # Verificar si es el mismo catequista
                if (grupo.catequista_principal_id and 
                    (grupo.catequista_principal_id == schedule.grupo.catequista_principal_id or
                     grupo.catequista_principal_id == schedule.grupo.catequista_auxiliar_id)):
                    conflicts.append(f"Catequista principal ocupado con {schedule.grupo.nombre}")
                
                if (grupo.catequista_auxiliar_id and 
                    (grupo.catequista_auxiliar_id == schedule.grupo.catequista_principal_id or
                     grupo.catequista_auxiliar_id == schedule.grupo.catequista_auxiliar_id)):
                    conflicts.append(f"Catequista auxiliar ocupado con {schedule.grupo.nombre}")
        
        return conflicts
    
    def _validate_state_transition(self, estado_actual: str, nuevo_estado: str):
        """Valida que la transición de estado sea válida."""
        transitions = {
            'planificado': ['activo', 'cancelado'],
            'activo': ['suspendido', 'finalizado', 'cancelado'],
            'suspendido': ['activo', 'cancelado', 'finalizado'],
            'finalizado': [],  # Estado final
            'cancelado': []    # Estado final
        }
        
        if nuevo_estado not in transitions.get(estado_actual, []):
            raise ValidationException(f"No se puede cambiar de '{estado_actual}' a '{nuevo_estado}'")
    
    def _register_state_change(self, grupo_id: int, estado_anterior: str, estado_nuevo: str, observaciones: str):
        """Registra un cambio de estado en el historial."""
        # Implementar registro en tabla de historial si existe
        logger.info(f"Cambio de estado grupo {grupo_id}: {estado_anterior} -> {estado_nuevo}. Obs: {observaciones}")
    
    def _handle_state_change_consequences(self, grupo: Grupo, nuevo_estado: str):
        """Maneja las consecuencias del cambio de estado."""
        if nuevo_estado == 'suspendido':
            # Suspender inscripciones activas
            self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo.id,
                    Inscripcion.estado == 'activa'
                )
            ).update({
                'estado': 'suspendida',
                'fecha_suspension': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        elif nuevo_estado == 'finalizado':
            # Completar inscripciones activas
            self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo.id,
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).update({
                'estado': 'completado',
                'fecha_finalizacion': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        elif nuevo_estado == 'cancelado':
            # Cancelar inscripciones
            self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo.id,
                    Inscripcion.estado.in_(['activa', 'en_progreso', 'suspendida'])
                )
            ).update({
                'estado': 'cancelada',
                'fecha_cancelacion': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
    
    def _get_inscripciones_grupo(self, grupo_id: int) -> List[Dict[str, Any]]:
        """Obtiene las inscripciones del grupo."""
        inscripciones = self.db.query(Inscripcion).filter(
            Inscripcion.grupo_id == grupo_id
        ).options(
            joinedload(Inscripcion.catequizando)
        ).order_by(Inscripcion.created_at).all()
        
        return [self._serialize_inscripcion(insc) for insc in inscripciones]
    
    def _get_horarios_grupo(self, grupo_id: int) -> List[Dict[str, Any]]:
        """Obtiene los horarios del grupo."""
        from app.models.catequesis.horario_grupo_model import HorarioGrupo
        
        horarios = self.db.query(HorarioGrupo).filter(
            and_(
                HorarioGrupo.grupo_id == grupo_id,
                HorarioGrupo.activo == True
            )
        ).order_by(HorarioGrupo.dia_semana, HorarioGrupo.hora_inicio).all()
        
        return [self._serialize_horario(h) for h in horarios]
    
    def _get_estadisticas_grupo(self, grupo_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas específicas del grupo."""
        # Inscripciones por estado
        inscripciones_stats = self.db.query(
            Inscripcion.estado, func.count(Inscripcion.id)
        ).filter(
            Inscripcion.grupo_id == grupo_id
        ).group_by(Inscripcion.estado).all()
        
        # Asistencia promedio
        asistencia_promedio = self.db.query(
            func.avg(func.case([(Asistencia.presente == True, 1)], else_=0) * 100)
        ).join(Inscripcion).filter(
            Inscripcion.grupo_id == grupo_id
        ).scalar() or 0
        
        # Total de clases realizadas
        total_clases = self.db.query(func.count(func.distinct(Asistencia.fecha_clase))).join(Inscripcion).filter(
            Inscripcion.grupo_id == grupo_id
        ).scalar() or 0
        
        return {
            'inscripciones_por_estado': {estado: count for estado, count in inscripciones_stats},
            'asistencia_promedio': round(asistencia_promedio, 1),
            'total_clases_realizadas': total_clases,
            'tasa_ocupacion': round((len(inscripciones_stats) / self.db.query(Grupo).filter(Grupo.id == grupo_id).first().capacidad_maxima) * 100, 1) if inscripciones_stats else 0
        }
    
    def _get_progreso_grupo(self, grupo_id: int) -> Dict[str, Any]:
        """Obtiene el progreso del grupo."""
        grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
        if not grupo or not grupo.nivel:
            return {}
        
        # Calcular progreso basado en duración del nivel
        duracion_nivel = grupo.nivel.duracion_meses or 12
        fecha_inicio = grupo.fecha_inicio
        
        if not fecha_inicio:
            return {'progreso_temporal': 0, 'meses_transcurridos': 0}
        
        meses_transcurridos = (datetime.now().date() - fecha_inicio).days / 30
        progreso_temporal = min((meses_transcurridos / duracion_nivel) * 100, 100)
        
        return {
            'progreso_temporal': round(progreso_temporal, 1),
            'meses_transcurridos': round(meses_transcurridos, 1),
            'duracion_total_meses': duracion_nivel,
            'fecha_estimada_fin': (fecha_inicio + timedelta(days=duracion_nivel * 30)).isoformat() if fecha_inicio else None
        }
    
    def _get_proximas_clases(self, grupo_id: int, dias_adelante: int = 7) -> List[Dict[str, Any]]:
        """Obtiene las próximas clases del grupo."""
        from app.models.catequesis.horario_grupo_model import HorarioGrupo
        
        horarios = self.db.query(HorarioGrupo).filter(
            and_(
                HorarioGrupo.grupo_id == grupo_id,
                HorarioGrupo.activo == True
            )
        ).all()
        
        proximas_clases = []
        hoy = date.today()
        
        for i in range(dias_adelante):
            fecha = hoy + timedelta(days=i)
            dia_semana = fecha.weekday()  # 0=Monday, 6=Sunday
            
            for horario in horarios:
                if horario.dia_semana == dia_semana:
                    proximas_clases.append({
                        'fecha': fecha.isoformat(),
                        'dia_semana': dia_semana,
                        'hora_inicio': horario.hora_inicio.strftime('%H:%M'),
                        'hora_fin': horario.hora_fin.strftime('%H:%M'),
                        'aula': horario.aula,
                        'observaciones': horario.observaciones
                    })
        
        return sorted(proximas_clases, key=lambda x: x['fecha'])
    
    def _serialize_inscripcion(self, inscripcion: Inscripcion) -> Dict[str, Any]:
        """Serializa una inscripción."""
        return {
            'id': inscripcion.id,
            'catequizando_id': inscripcion.catequizando_id,
            'catequizando_nombre': f"{inscripcion.catequizando.nombres} {inscripcion.catequizando.apellidos}" if inscripcion.catequizando else None,
            'fecha_inscripcion': inscripcion.fecha_inscripcion.isoformat() if inscripcion.fecha_inscripcion else None,
            'estado': inscripcion.estado,
            'created_at': inscripcion.created_at.isoformat() if inscripcion.created_at else None
        }
    
    def _serialize_horario(self, horario) -> Dict[str, Any]:
        """Serializa un horario de grupo."""
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        return {
            'id': horario.id,
            'dia_semana': horario.dia_semana,
            'dia_semana_nombre': dias_semana[horario.dia_semana],
            'hora_inicio': horario.hora_inicio.strftime('%H:%M'),
            'hora_fin': horario.hora_fin.strftime('%H:%M'),
            'aula': horario.aula,
            'observaciones': horario.observaciones,
            'activo': horario.activo,
            'created_at': horario.created_at.isoformat() if horario.created_at else None
        }