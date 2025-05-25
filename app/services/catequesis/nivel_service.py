"""
Servicio de gestión de niveles de catequesis.
Maneja CRUD de niveles, prerequisitos, progresión y configuraciones.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.nivel_model import Nivel
from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.grupo_model import Grupo
from app.schemas.catequesis.nivel_schema import (
    NivelCreateSchema, NivelUpdateSchema, NivelResponseSchema,
    NivelSearchSchema, ProgresionNivelSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class NivelService(BaseService):
    """Servicio para gestión completa de niveles de catequesis."""
    
    @property
    def model(self) -> Type[Nivel]:
        return Nivel
    
    @property
    def create_schema(self) -> Type[NivelCreateSchema]:
        return NivelCreateSchema
    
    @property
    def update_schema(self) -> Type[NivelUpdateSchema]:
        return NivelUpdateSchema
    
    @property
    def response_schema(self) -> Type[NivelResponseSchema]:
        return NivelResponseSchema
    
    @property
    def search_schema(self) -> Type[NivelSearchSchema]:
        return NivelSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Nivel.programa_catequesis),
            joinedload(Nivel.nivel_prerequisito),
            joinedload(Nivel.created_by_user),
            joinedload(Nivel.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para niveles."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Nivel.nombre.ilike(search_term),
                    Nivel.descripcion.ilike(search_term),
                    Nivel.objetivos.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('activo') is not None:
            query = query.filter(Nivel.activo == search_data['activo'])
        
        if search_data.get('programa_id'):
            query = query.filter(Nivel.programa_catequesis_id == search_data['programa_id'])
        
        if search_data.get('edad_minima'):
            query = query.filter(Nivel.edad_minima >= search_data['edad_minima'])
        
        if search_data.get('edad_maxima'):
            query = query.filter(Nivel.edad_maxima <= search_data['edad_maxima'])
        
        if search_data.get('duracion_minima_meses'):
            query = query.filter(Nivel.duracion_meses >= search_data['duracion_minima_meses'])
        
        if search_data.get('tipo_nivel'):
            query = query.filter(Nivel.tipo_nivel == search_data['tipo_nivel'])
        
        if search_data.get('requiere_sacramento'):
            query = query.filter(Nivel.requiere_sacramento == search_data['requiere_sacramento'])
        
        if search_data.get('sin_prerequisitos'):
            query = query.filter(Nivel.prerequisito_nivel_id.is_(None))
        
        return query
    
    @require_permission('niveles', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar nombre único dentro del programa
        if self._exists_name_in_program(data['nombre'], data['programa_catequesis_id']):
            raise ValidationException("Ya existe un nivel con ese nombre en el programa")
        
        # Validar edades
        if data.get('edad_minima') and data.get('edad_maxima'):
            if data['edad_minima'] > data['edad_maxima']:
                raise ValidationException("La edad mínima no puede ser mayor que la máxima")
        
        # Validar prerequisito
        if data.get('prerequisito_nivel_id'):
            self._validate_prerequisite(data['prerequisito_nivel_id'], data['programa_catequesis_id'])
        
        # Asignar orden automático si no se especifica
        if not data.get('orden'):
            data['orden'] = self._get_next_order(data['programa_catequesis_id'])
        
        # Configuraciones por defecto
        data.setdefault('activo', True)
        data.setdefault('tipo_nivel', 'regular')
        data.setdefault('requiere_examen', False)
        data.setdefault('requiere_proyecto', False)
        
        return data
    
    @require_permission('niveles', 'actualizar')
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-actualización para validaciones."""
        # Verificar nombre único (si cambió)
        if 'nombre' in data and data['nombre'] != instance.nombre:
            if self._exists_name_in_program(data['nombre'], instance.programa_catequesis_id):
                raise ValidationException("Ya existe un nivel con ese nombre en el programa")
        
        # Validar edades
        edad_min = data.get('edad_minima', instance.edad_minima)
        edad_max = data.get('edad_maxima', instance.edad_maxima)
        if edad_min and edad_max and edad_min > edad_max:
            raise ValidationException("La edad mínima no puede ser mayor que la máxima")
        
        # Validar prerequisito (si cambió)
        if 'prerequisito_nivel_id' in data:
            if data['prerequisito_nivel_id']:
                self._validate_prerequisite(data['prerequisito_nivel_id'], instance.programa_catequesis_id, instance.id)
        
        return data
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar el nivel."""
        # Verificar dependencias
        dependencies = self._check_nivel_dependencies(instance.id)
        if dependencies:
            raise BusinessLogicException(f"No se puede eliminar. Tiene dependencias: {', '.join(dependencies)}")
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE NIVELES
    # ==========================================
    
    def get_niveles_programa(self, programa_id: int, solo_activos: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene todos los niveles de un programa ordenados.
        
        Args:
            programa_id: ID del programa
            solo_activos: Si solo incluir niveles activos
            
        Returns:
            Lista de niveles ordenados
        """
        try:
            query = self.db.query(Nivel).filter(Nivel.programa_catequesis_id == programa_id)
            
            if solo_activos:
                query = query.filter(Nivel.activo == True)
            
            niveles = query.order_by(Nivel.orden, Nivel.nombre).all()
            
            return [self._serialize_response(nivel) for nivel in niveles]
            
        except Exception as e:
            logger.error(f"Error obteniendo niveles de programa: {str(e)}")
            raise BusinessLogicException("Error obteniendo niveles del programa")
    
    def get_ruta_progresion(self, programa_id: int) -> Dict[str, Any]:
        """
        Obtiene la ruta completa de progresión de un programa.
        
        Args:
            programa_id: ID del programa
            
        Returns:
            Dict con la ruta de progresión
        """
        try:
            niveles = self.db.query(Nivel).filter(
                and_(
                    Nivel.programa_catequesis_id == programa_id,
                    Nivel.activo == True
                )
            ).order_by(Nivel.orden).all()
            
            # Construir árbol de progresión
            ruta = []
            niveles_map = {nivel.id: nivel for nivel in niveles}
            
            for nivel in niveles:
                nivel_data = self._serialize_response(nivel)
                
                # Agregar información de progresión
                if nivel.prerequisito_nivel_id:
                    prerequisito = niveles_map.get(nivel.prerequisito_nivel_id)
                    if prerequisito:
                        nivel_data['prerequisito'] = {
                            'id': prerequisito.id,
                            'nombre': prerequisito.nombre
                        }
                
                # Buscar niveles siguientes
                siguientes = [n for n in niveles if n.prerequisito_nivel_id == nivel.id]
                nivel_data['niveles_siguientes'] = [
                    {'id': n.id, 'nombre': n.nombre} for n in siguientes
                ]
                
                ruta.append(nivel_data)
            
            return {
                'programa_id': programa_id,
                'total_niveles': len(niveles),
                'duracion_total_meses': sum(n.duracion_meses or 0 for n in niveles),
                'ruta_progresion': ruta
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ruta de progresión: {str(e)}")
            raise BusinessLogicException("Error obteniendo ruta de progresión")
    
    @require_permission('niveles', 'administrar')
    def reordenar_niveles(self, programa_id: int, orden_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reordena los niveles de un programa.
        
        Args:
            programa_id: ID del programa
            orden_data: Lista con {nivel_id, nuevo_orden}
            
        Returns:
            Dict con confirmación
        """
        try:
            # Validar que todos los niveles pertenecen al programa
            nivel_ids = [item['nivel_id'] for item in orden_data]
            niveles = self.db.query(Nivel).filter(
                and_(
                    Nivel.id.in_(nivel_ids),
                    Nivel.programa_catequesis_id == programa_id
                )
            ).all()
            
            if len(niveles) != len(nivel_ids):
                raise ValidationException("Algunos niveles no pertenecen al programa")
            
            # Aplicar nuevo orden
            for item in orden_data:
                nivel = next(n for n in niveles if n.id == item['nivel_id'])
                nivel.orden = item['nuevo_orden']
                nivel.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Niveles reordenados en programa {programa_id}")
            
            return {
                'success': True,
                'message': 'Niveles reordenados exitosamente',
                'total_reordenados': len(orden_data)
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error reordenando niveles: {str(e)}")
            raise BusinessLogicException("Error reordenando niveles")
    
    def get_nivel_disponible_para_catequizando(self, catequizando_id: int, programa_id: int) -> Optional[Dict[str, Any]]:
        """
        Determina el siguiente nivel disponible para un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            programa_id: ID del programa
            
        Returns:
            Dict con el nivel recomendado o None
        """
        try:
            from app.models.catequesis.catequizando_model import Catequizando
            from app.models.catequesis.inscripcion_model import Inscripcion
            
            # Obtener catequizando
            catequizando = self.db.query(Catequizando).filter(Catequizando.id == catequizando_id).first()
            if not catequizando:
                raise NotFoundException("Catequizando no encontrado")
            
            # Obtener niveles completados
            inscripciones_completadas = self.db.query(Inscripcion).join(Nivel).filter(
                and_(
                    Inscripcion.catequizando_id == catequizando_id,
                    Nivel.programa_catequesis_id == programa_id,
                    Inscripcion.estado == 'completado'
                )
            ).all()
            
            niveles_completados = {insc.nivel_id for insc in inscripciones_completadas}
            
            # Obtener todos los niveles del programa
            niveles = self.db.query(Nivel).filter(
                and_(
                    Nivel.programa_catequesis_id == programa_id,
                    Nivel.activo == True
                )
            ).order_by(Nivel.orden).all()
            
            # Encontrar el siguiente nivel disponible
            for nivel in niveles:
                # Si ya completó este nivel, continuar
                if nivel.id in niveles_completados:
                    continue
                
                # Verificar edad
                edad = self._calculate_age(catequizando.fecha_nacimiento)
                if nivel.edad_minima and edad < nivel.edad_minima:
                    continue
                if nivel.edad_maxima and edad > nivel.edad_maxima:
                    continue
                
                # Verificar prerequisito
                if nivel.prerequisito_nivel_id and nivel.prerequisito_nivel_id not in niveles_completados:
                    continue
                
                # Este nivel está disponible
                nivel_data = self._serialize_response(nivel)
                nivel_data['razon_disponible'] = self._get_availability_reason(nivel, catequizando, niveles_completados)
                return nivel_data
            
            return None
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error determinando nivel disponible: {str(e)}")
            raise BusinessLogicException("Error determinando nivel disponible")
    
    @require_permission('niveles', 'administrar')
    def toggle_activation(self, nivel_id: int) -> Dict[str, Any]:
        """
        Activa o desactiva un nivel.
        
        Args:
            nivel_id: ID del nivel
            
        Returns:
            Dict con el nuevo estado
        """
        try:
            nivel = self._get_instance_by_id(nivel_id)
            
            # Validaciones antes de desactivar
            if nivel.activo and not self._can_deactivate_nivel(nivel_id):
                raise BusinessLogicException("No se puede desactivar. Hay inscripciones activas en este nivel")
            
            # Cambiar estado
            new_state = not nivel.activo
            nivel.activo = new_state
            nivel.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            action = "activado" if new_state else "desactivado"
            logger.info(f"Nivel {nivel.nombre} {action}")
            
            return {
                'success': True,
                'activo': new_state,
                'message': f'Nivel {action} exitosamente'
            }
            
        except BusinessLogicException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando estado de nivel: {str(e)}")
            raise BusinessLogicException("Error cambiando estado del nivel")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de niveles."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de niveles
            total_niveles = self.db.query(Nivel).count()
            niveles_activos = self.db.query(Nivel).filter(Nivel.activo == True).count()
            
            # Distribución por tipo
            tipos_distribution = self.db.query(
                Nivel.tipo_nivel, func.count(Nivel.id)
            ).group_by(Nivel.tipo_nivel).all()
            
            # Distribución por duración
            duracion_stats = self.db.query(
                func.avg(Nivel.duracion_meses).label('promedio'),
                func.min(Nivel.duracion_meses).label('minimo'),
                func.max(Nivel.duracion_meses).label('maximo')
            ).filter(Nivel.duracion_meses.isnot(None)).first()
            
            # Niveles con más inscripciones
            from app.models.catequesis.inscripcion_model import Inscripcion
            niveles_populares = self.db.query(
                Nivel.nombre, func.count(Inscripcion.id).label('total_inscripciones')
            ).join(Inscripcion).group_by(Nivel.id, Nivel.nombre).order_by(
                func.count(Inscripcion.id).desc()
            ).limit(5).all()
            
            base_stats.update({
                'total_niveles': total_niveles,
                'niveles_activos': niveles_activos,
                'niveles_inactivos': total_niveles - niveles_activos,
                'distribucion_tipos': {tipo: count for tipo, count in tipos_distribution},
                'duracion_promedio_meses': round(duracion_stats.promedio, 1) if duracion_stats and duracion_stats.promedio else 0,
                'duracion_minima_meses': duracion_stats.minimo if duracion_stats else 0,
                'duracion_maxima_meses': duracion_stats.maximo if duracion_stats else 0,
                'niveles_mas_populares': [
                    {'nombre': nombre, 'inscripciones': count} 
                    for nombre, count in niveles_populares
                ]
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de niveles: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _exists_name_in_program(self, nombre: str, programa_id: int, exclude_id: int = None) -> bool:
        """Verifica si existe un nivel con el mismo nombre en el programa."""
        query = self.db.query(Nivel).filter(
            and_(
                Nivel.nombre == nombre,
                Nivel.programa_catequesis_id == programa_id
            )
        )
        
        if exclude_id:
            query = query.filter(Nivel.id != exclude_id)
        
        return query.first() is not None
    
    def _validate_prerequisite(self, prerequisito_id: int, programa_id: int, exclude_id: int = None):
        """Valida que el prerequisito sea válido."""
        # Verificar que el prerequisito existe y pertenece al mismo programa
        prerequisito = self.db.query(Nivel).filter(
            and_(
                Nivel.id == prerequisito_id,
                Nivel.programa_catequesis_id == programa_id
            )
        ).first()
        
        if not prerequisito:
            raise ValidationException("El prerequisito debe pertenecer al mismo programa")
        
        # Verificar que no se cree un ciclo
        if exclude_id and self._creates_cycle(prerequisito_id, exclude_id):
            raise ValidationException("La relación de prerequisito crearía un ciclo")
    
    def _creates_cycle(self, prerequisito_id: int, nivel_id: int) -> bool:
        """Verifica si la relación de prerequisito crearía un ciclo."""
        visited = set()
        current = prerequisito_id
        
        while current and current not in visited:
            if current == nivel_id:
                return True
            
            visited.add(current)
            nivel = self.db.query(Nivel).filter(Nivel.id == current).first()
            current = nivel.prerequisito_nivel_id if nivel else None
        
        return False
    
    def _get_next_order(self, programa_id: int) -> int:
        """Obtiene el siguiente número de orden para un programa."""
        max_order = self.db.query(func.max(Nivel.orden)).filter(
            Nivel.programa_catequesis_id == programa_id
        ).scalar()
        
        return (max_order or 0) + 1
    
    def _check_nivel_dependencies(self, nivel_id: int) -> List[str]:
        """Verifica dependencias del nivel antes de eliminar."""
        dependencies = []
        
        # Verificar inscripciones
        from app.models.catequesis.inscripcion_model import Inscripcion
        inscripciones_count = self.db.query(Inscripcion).filter(
            Inscripcion.nivel_id == nivel_id
        ).count()
        if inscripciones_count > 0:
            dependencies.append(f'{inscripciones_count} inscripciones')
        
        # Verificar si es prerequisito de otros niveles
        dependientes_count = self.db.query(Nivel).filter(
            Nivel.prerequisito_nivel_id == nivel_id
        ).count()
        if dependientes_count > 0:
            dependencies.append(f'{dependientes_count} niveles dependientes')
        
        return dependencies
    
    def _can_deactivate_nivel(self, nivel_id: int) -> bool:
        """Verifica si se puede desactivar un nivel."""
        from app.models.catequesis.inscripcion_model import Inscripcion
        
        # Verificar inscripciones activas
        active_inscriptions = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.nivel_id == nivel_id,
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).count()
        
        return active_inscriptions == 0
    
    def _calculate_age(self, fecha_nacimiento: date) -> int:
        """Calcula la edad en años."""
        if not fecha_nacimiento:
            return 0
        
        today = date.today()
        return today.year - fecha_nacimiento.year - (
            (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
    
    def _get_availability_reason(self, nivel: Nivel, catequizando, niveles_completados: set) -> str:
        """Obtiene la razón por la cual un nivel está disponible."""
        if not nivel.prerequisito_nivel_id:
            return "Nivel inicial - no requiere prerequisitos"
        
        if nivel.prerequisito_nivel_id in niveles_completados:
            return "Prerequisito completado satisfactoriamente"
        
        return "Disponible según progresión normal"