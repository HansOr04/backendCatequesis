"""
Servicio de gestión de inscripciones a catequesis.
Maneja CRUD de inscripciones, validaciones y flujo de estados.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.inscripcion_model import Inscripcion
from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.grupo_model import Grupo
from app.models.catequesis.nivel_model import Nivel
from app.schemas.catequesis.inscripcion_schema import (
    InscripcionCreateSchema, InscripcionUpdateSchema, InscripcionResponseSchema,
    InscripcionSearchSchema, CambioEstadoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class InscripcionService(BaseService):
    """Servicio para gestión completa de inscripciones."""
    
    @property
    def model(self) -> Type[Inscripcion]:
        return Inscripcion
    
    @property
    def create_schema(self) -> Type[InscripcionCreateSchema]:
        return InscripcionCreateSchema
    
    @property
    def update_schema(self) -> Type[InscripcionUpdateSchema]:
        return InscripcionUpdateSchema
    
    @property
    def response_schema(self) -> Type[InscripcionResponseSchema]:
        return InscripcionResponseSchema
    
    @property
    def search_schema(self) -> Type[InscripcionSearchSchema]:
        return InscripcionSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Inscripcion.catequizando),
            joinedload(Inscripcion.grupo),
            joinedload(Inscripcion.nivel),
            joinedload(Inscripcion.sacramento_objetivo),
            joinedload(Inscripcion.created_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para inscripciones."""
        query = self._build_base_query(**kwargs)
        
        # Filtros básicos
        if search_data.get('catequizando_id'):
            query = query.filter(Inscripcion.catequizando_id == search_data['catequizando_id'])
        
        if search_data.get('grupo_id'):
            query = query.filter(Inscripcion.grupo_id == search_data['grupo_id'])
        
        if search_data.get('nivel_id'):
            query = query.filter(Inscripcion.nivel_id == search_data['nivel_id'])
        
        if search_data.get('estado'):
            query = query.filter(Inscripcion.estado == search_data['estado'])
        
        if search_data.get('estados_incluir'):
            query = query.filter(Inscripcion.estado.in_(search_data['estados_incluir']))
        
        # Filtros de fecha
        if search_data.get('fecha_desde'):
            query = query.filter(Inscripcion.fecha_inscripcion >= search_data['fecha_desde'])
        
        if search_data.get('fecha_hasta'):
            query = query.filter(Inscripcion.fecha_inscripcion <= search_data['fecha_hasta'])
        
        return query
    
    @require_permission('inscripciones', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que el catequizando existe y está activo
        catequizando = self.db.query(Catequizando).filter(
            Catequizando.id == data['catequizando_id']
        ).first()
        
        if not catequizando or not catequizando.activo:
            raise ValidationException("Catequizando no encontrado o inactivo")
        
        # Verificar que no tenga inscripción activa en el mismo nivel
        inscripcion_activa = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.catequizando_id == data['catequizando_id'],
                Inscripcion.nivel_id == data['nivel_id'],
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).first()
        
        if inscripcion_activa:
            raise ValidationException("Ya tiene una inscripción activa en este nivel")
        
        # Validar prerequisitos del nivel
        self._validate_nivel_prerequisites(catequizando, data['nivel_id'])
        
        # Verificar cupos en el grupo (si se especifica)
        if data.get('grupo_id'):
            self._validate_group_capacity(data['grupo_id'])
        
        # Configuraciones por defecto
        data.setdefault('fecha_inscripcion', date.today())
        data.setdefault('estado', 'activa')
        
        return data
    
    def _after_create(self, instance, data: Dict[str, Any], **kwargs):
        """Hook post-creación."""
        # Actualizar cupos del grupo si se asignó
        if instance.grupo_id:
            self._update_group_capacity(instance.grupo_id, 1)
        
        return instance
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS
    # ==========================================
    
    @require_permission('inscripciones', 'administrar')
    def cambiar_estado(self, inscripcion_id: int, cambio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cambia el estado de una inscripción."""
        try:
            schema = CambioEstadoSchema()
            validated_data = schema.load(cambio_data)
            
            inscripcion = self._get_instance_by_id(inscripcion_id)
            
            nuevo_estado = validated_data['nuevo_estado']
            observaciones = validated_data.get('observaciones')
            
            # Validar transición
            self._validate_state_transition(inscripcion.estado, nuevo_estado)
            
            estado_anterior = inscripcion.estado
            inscripcion.estado = nuevo_estado
            inscripcion.updated_at = datetime.utcnow()
            
            # Manejar consecuencias del cambio
            self._handle_state_change(inscripcion, estado_anterior, nuevo_estado)
            
            self.db.commit()
            
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
            raise BusinessLogicException("Error cambiando estado de inscripción")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de inscripciones."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas por estado
            estado_distribution = self.db.query(
                Inscripcion.estado, func.count(Inscripcion.id)
            ).group_by(Inscripcion.estado).all()
            
            # Inscripciones por mes
            inscripciones_mes = self.db.query(
                func.extract('month', Inscripcion.fecha_inscripcion).label('mes'),
                func.count(Inscripcion.id).label('total')
            ).filter(
                func.extract('year', Inscripcion.fecha_inscripcion) == datetime.now().year
            ).group_by('mes').all()
            
            base_stats.update({
                'distribucion_estados': {estado: count for estado, count in estado_distribution},
                'inscripciones_por_mes': {int(mes): total for mes, total in inscripciones_mes}
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================
    
    def _validate_nivel_prerequisites(self, catequizando: Catequizando, nivel_id: int):
        """Valida prerequisitos del nivel."""
        nivel = self.db.query(Nivel).filter(Nivel.id == nivel_id).first()
        if not nivel:
            raise NotFoundException("Nivel no encontrado")
        
        # Verificar edad
        if nivel.edad_minima:
            edad = self._calculate_age(catequizando.fecha_nacimiento)
            if edad < nivel.edad_minima:
                raise ValidationException(f"Edad mínima requerida: {nivel.edad_minima} años")
        
        # Verificar prerequisito
        if nivel.prerequisito_nivel_id:
            prerequisito_completado = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.catequizando_id == catequizando.id,
                    Inscripcion.nivel_id == nivel.prerequisito_nivel_id,
                    Inscripcion.estado == 'completado'
                )
            ).first()
            
            if not prerequisito_completado:
                raise ValidationException("Debe completar el nivel prerequisito")
    
    def _validate_group_capacity(self, grupo_id: int):
        """Valida capacidad del grupo."""
        grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
        if not grupo:
            raise NotFoundException("Grupo no encontrado")
        
        if grupo.cupos_ocupados >= grupo.capacidad_maxima:
            raise ValidationException("El grupo no tiene cupos disponibles")
    
    def _update_group_capacity(self, grupo_id: int, increment: int):
        """Actualiza la capacidad del grupo."""
        grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
        if grupo:
            grupo.cupos_ocupados += increment
            grupo.updated_at = datetime.utcnow()
    
    def _validate_state_transition(self, estado_actual: str, nuevo_estado: str):
        """Valida transiciones de estado."""
        transitions = {
            'activa': ['en_progreso', 'suspendida', 'cancelada'],
            'en_progreso': ['completado', 'suspendida', 'cancelada'],
            'suspendida': ['activa', 'en_progreso', 'cancelada'],
            'completado': [],  # Estado final
            'cancelada': []    # Estado final
        }
        
        if nuevo_estado not in transitions.get(estado_actual, []):
            raise ValidationException(f"No se puede cambiar de '{estado_actual}' a '{nuevo_estado}'")
    
    def _handle_state_change(self, inscripcion: Inscripcion, estado_anterior: str, nuevo_estado: str):
        """Maneja consecuencias del cambio de estado."""
        if nuevo_estado == 'completado':
            inscripcion.fecha_finalizacion = datetime.utcnow()
        elif nuevo_estado == 'cancelada':
            inscripcion.fecha_cancelacion = datetime.utcnow()
            # Liberar cupo del grupo
            if inscripcion.grupo_id:
                self._update_group_capacity(inscripcion.grupo_id, -1)
        elif nuevo_estado == 'suspendida':
            inscripcion.fecha_suspension = datetime.utcnow()
    
    def _calculate_age(self, fecha_nacimiento: date) -> int:
        """Calcula edad en años."""
        if not fecha_nacimiento:
            return 0
        
        today = date.today()
        return today.year - fecha_nacimiento.year - (
            (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )