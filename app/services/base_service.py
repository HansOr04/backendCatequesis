"""
Servicio base para el sistema de catequesis.
Proporciona funcionalidades comunes para todos los servicios de negocio.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_, or_, func, desc, asc
from marshmallow import Schema, ValidationError
import logging

from app.core.database import get_db
from app.core.exceptions import (
    ValidationException, NotFoundException, DuplicateException,
    BusinessLogicException, DatabaseException
)
from app.core.security import get_current_user
from app.utils.pagination import paginate_query
from app.utils.audit import log_activity
from app.utils.cache import cache_manager
from app.schemas.base_schema import BaseSchema


logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Servicio base que proporciona operaciones CRUD estándar y funcionalidades comunes.
    Todos los servicios del sistema deben heredar de esta clase.
    """
    
    def __init__(self, db: Session = None, current_user: Dict = None):
        """
        Inicializa el servicio base.
        
        Args:
            db: Sesión de base de datos
            current_user: Usuario actual del contexto
        """
        self.db = db or next(get_db())
        self.current_user = current_user or get_current_user()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @property
    @abstractmethod
    def model(self) -> Type:
        """Modelo SQLAlchemy asociado al servicio."""
        pass
    
    @property
    @abstractmethod
    def create_schema(self) -> Type[Schema]:
        """Schema para creación de registros."""
        pass
    
    @property
    @abstractmethod
    def update_schema(self) -> Type[Schema]:
        """Schema para actualización de registros."""
        pass
    
    @property
    @abstractmethod
    def response_schema(self) -> Type[Schema]:
        """Schema para respuesta de registros."""
        pass
    
    @property
    def search_schema(self) -> Optional[Type[Schema]]:
        """Schema para búsqueda (opcional)."""
        return None
    
    @property
    def entity_name(self) -> str:
        """Nombre de la entidad para logs y mensajes."""
        return self.model.__name__.lower()
    
    # ==========================================
    # OPERACIONES CRUD BÁSICAS
    # ==========================================
    
    def create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Crea un nuevo registro.
        
        Args:
            data: Datos para crear el registro
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict con el registro creado serializado
            
        Raises:
            ValidationException: Si los datos no son válidos
            DuplicateException: Si el registro ya existe
            DatabaseException: Si hay error en la base de datos
        """
        try:
            # Validar datos de entrada
            validated_data = self._validate_create_data(data)
            
            # Hook pre-creación
            validated_data = self._before_create(validated_data, **kwargs)
            
            # Crear instancia del modelo
            instance = self.model(**validated_data)
            
            # Agregar información de auditoría
            self._add_audit_fields(instance, action='create')
            
            # Guardar en base de datos
            self.db.add(instance)
            self.db.flush()  # Para obtener el ID sin commit
            
            # Hook post-creación
            instance = self._after_create(instance, validated_data, **kwargs)
            
            # Confirmar transacción
            self.db.commit()
            
            # Log de actividad
            self._log_activity('create', instance.id, validated_data)
            
            # Limpiar caché relacionado
            self._invalidate_cache('create', instance)
            
            # Serializar respuesta
            return self._serialize_response(instance)
            
        except ValidationError as e:
            self.db.rollback()
            raise ValidationException(f"Error de validación en {self.entity_name}", e.messages)
        except IntegrityError as e:
            self.db.rollback()
            raise DuplicateException(f"El {self.entity_name} ya existe")
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error de base de datos creando {self.entity_name}: {str(e)}")
            raise DatabaseException(f"Error creando {self.entity_name}")
    
    def get_by_id(self, id: int, **kwargs) -> Dict[str, Any]:
        """
        Obtiene un registro por ID.
        
        Args:
            id: ID del registro
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict con el registro serializado
            
        Raises:
            NotFoundException: Si el registro no existe
        """
        try:
            # Intentar obtener desde caché
            cache_key = self._get_cache_key('get', id)
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Construir query base
            query = self._build_base_query(**kwargs)
            
            # Buscar por ID
            instance = query.filter(self.model.id == id).first()
            
            if not instance:
                raise NotFoundException(f"{self.entity_name.title()} con ID {id} no encontrado")
            
            # Hook post-obtención
            instance = self._after_get(instance, **kwargs)
            
            # Serializar respuesta
            result = self._serialize_response(instance)
            
            # Guardar en caché
            cache_manager.set(cache_key, result, timeout=300)  # 5 minutos
            
            return result
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error obteniendo {self.entity_name} {id}: {str(e)}")
            raise DatabaseException(f"Error obteniendo {self.entity_name}")
    
    def get_all(self, filters: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Obtiene todos los registros con filtros opcionales.
        
        Args:
            filters: Filtros para aplicar
            **kwargs: Argumentos adicionales (page, per_page, sort_by, etc.)
            
        Returns:
            Dict con registros paginados y metadatos
        """
        try:
            # Construir query base
            query = self._build_base_query(**kwargs)
            
            # Aplicar filtros
            if filters:
                query = self._apply_filters(query, filters)
            
            # Hook pre-listado
            query = self._before_list(query, filters, **kwargs)
            
            # Aplicar ordenamiento
            query = self._apply_sorting(query, **kwargs)
            
            # Paginar resultados
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            
            paginated_result = paginate_query(
                query=query,
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            # Serializar elementos
            items = [self._serialize_response(item) for item in paginated_result.items]
            
            # Hook post-listado
            items = self._after_list(items, filters, **kwargs)
            
            return {
                'items': items,
                'pagination': {
                    'page': paginated_result.page,
                    'per_page': paginated_result.per_page,
                    'total': paginated_result.total,
                    'pages': paginated_result.pages,
                    'has_prev': paginated_result.has_prev,
                    'has_next': paginated_result.has_next,
                    'prev_num': paginated_result.prev_num,
                    'next_num': paginated_result.next_num
                }
            }
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error listando {self.entity_name}: {str(e)}")
            raise DatabaseException(f"Error listando {self.entity_name}")
    
    def update(self, id: int, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Actualiza un registro existente.
        
        Args:
            id: ID del registro a actualizar
            data: Datos para actualizar
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict con el registro actualizado serializado
            
        Raises:
            NotFoundException: Si el registro no existe
            ValidationException: Si los datos no son válidos
        """
        try:
            # Obtener registro existente
            instance = self._get_instance_by_id(id)
            
            # Validar datos de actualización
            validated_data = self._validate_update_data(data, instance)
            
            # Hook pre-actualización
            validated_data = self._before_update(instance, validated_data, **kwargs)
            
            # Aplicar cambios
            for key, value in validated_data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            # Actualizar información de auditoría
            self._add_audit_fields(instance, action='update')
            
            # Hook post-actualización
            instance = self._after_update(instance, validated_data, **kwargs)
            
            # Confirmar transacción
            self.db.commit()
            
            # Log de actividad
            self._log_activity('update', instance.id, validated_data)
            
            # Limpiar caché
            self._invalidate_cache('update', instance)
            
            # Serializar respuesta
            return self._serialize_response(instance)
            
        except ValidationError as e:
            self.db.rollback()
            raise ValidationException(f"Error de validación actualizando {self.entity_name}", e.messages)
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error actualizando {self.entity_name} {id}: {str(e)}")
            raise DatabaseException(f"Error actualizando {self.entity_name}")
    
    def delete(self, id: int, **kwargs) -> bool:
        """
        Elimina un registro.
        
        Args:
            id: ID del registro a eliminar
            **kwargs: Argumentos adicionales
            
        Returns:
            True si se eliminó correctamente
            
        Raises:
            NotFoundException: Si el registro no existe
            BusinessLogicException: Si no se puede eliminar
        """
        try:
            # Obtener registro existente
            instance = self._get_instance_by_id(id)
            
            # Validar que se puede eliminar
            self._validate_delete(instance, **kwargs)
            
            # Hook pre-eliminación
            self._before_delete(instance, **kwargs)
            
            # Realizar eliminación (física o lógica)
            if self._use_soft_delete():
                self._soft_delete(instance)
            else:
                self.db.delete(instance)
            
            # Hook post-eliminación
            self._after_delete(instance, **kwargs)
            
            # Confirmar transacción
            self.db.commit()
            
            # Log de actividad
            self._log_activity('delete', instance.id, {})
            
            # Limpiar caché
            self._invalidate_cache('delete', instance)
            
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error eliminando {self.entity_name} {id}: {str(e)}")
            raise DatabaseException(f"Error eliminando {self.entity_name}")
    
    # ==========================================
    # MÉTODOS DE BÚSQUEDA Y FILTRADO
    # ==========================================
    
    def search(self, search_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Realiza búsqueda avanzada con múltiples criterios.
        
        Args:
            search_data: Criterios de búsqueda
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict con resultados paginados
        """
        try:
            # Validar criterios de búsqueda
            if self.search_schema:
                schema = self.search_schema()
                validated_data = schema.load(search_data)
            else:
                validated_data = search_data
            
            # Construir query de búsqueda
            query = self._build_search_query(validated_data, **kwargs)
            
            # Aplicar ordenamiento
            query = self._apply_sorting(query, **validated_data)
            
            # Paginar
            page = validated_data.get('page', 1)
            per_page = validated_data.get('per_page', 20)
            
            paginated_result = paginate_query(query, page, per_page)
            
            # Serializar resultados
            items = [self._serialize_response(item) for item in paginated_result.items]
            
            return {
                'items': items,
                'pagination': {
                    'page': paginated_result.page,
                    'per_page': paginated_result.per_page,
                    'total': paginated_result.total,
                    'pages': paginated_result.pages,
                    'has_prev': paginated_result.has_prev,
                    'has_next': paginated_result.has_next
                },
                'search_criteria': validated_data
            }
            
        except ValidationError as e:
            raise ValidationException("Error en criterios de búsqueda", e.messages)
        except SQLAlchemyError as e:
            self.logger.error(f"Error en búsqueda de {self.entity_name}: {str(e)}")
            raise DatabaseException(f"Error en búsqueda de {self.entity_name}")
    
    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        Cuenta registros que coinciden con los filtros.
        
        Args:
            filters: Filtros para aplicar
            
        Returns:
            Número de registros
        """
        try:
            query = self._build_base_query()
            
            if filters:
                query = self._apply_filters(query, filters)
            
            return query.count()
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error contando {self.entity_name}: {str(e)}")
            raise DatabaseException(f"Error contando {self.entity_name}")
    
    def exists(self, **filters) -> bool:
        """
        Verifica si existe al menos un registro con los filtros dados.
        
        Args:
            **filters: Filtros como argumentos nombrados
            
        Returns:
            True si existe al menos un registro
        """
        try:
            query = self._build_base_query()
            
            # Aplicar filtros
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
            
            return query.first() is not None
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error verificando existencia en {self.entity_name}: {str(e)}")
            raise DatabaseException(f"Error verificando existencia en {self.entity_name}")
    
    # ==========================================
    # MÉTODOS AUXILIARES Y HOOKS
    # ==========================================
    
    def _validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para creación usando el schema correspondiente."""
        schema = self.create_schema()
        return schema.load(data)
    
    def _validate_update_data(self, data: Dict[str, Any], instance=None) -> Dict[str, Any]:
        """Valida datos para actualización usando el schema correspondiente."""
        schema = self.update_schema()
        return schema.load(data)
    
    def _serialize_response(self, instance) -> Dict[str, Any]:
        """Serializa una instancia usando el schema de respuesta."""
        schema = self.response_schema()
        return schema.dump(instance)
    
    def _get_instance_by_id(self, id: int):
        """Obtiene una instancia por ID o lanza excepción si no existe."""
        instance = self.db.query(self.model).filter(self.model.id == id).first()
        if not instance:
            raise NotFoundException(f"{self.entity_name.title()} con ID {id} no encontrado")
        return instance
    
    def _build_base_query(self, **kwargs):
        """Construye la query base para el modelo."""
        query = self.db.query(self.model)
        
        # Aplicar filtro de soft delete si aplica
        if self._use_soft_delete() and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at.is_(None))
        
        return query
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda. Debe ser implementado por subclases."""
        return self._build_base_query(**kwargs)
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Aplica filtros básicos a la query."""
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                if isinstance(value, list):
                    query = query.filter(getattr(self.model, key).in_(value))
                else:
                    query = query.filter(getattr(self.model, key) == value)
        return query
    
    def _apply_sorting(self, query, **kwargs):
        """Aplica ordenamiento a la query."""
        sort_by = kwargs.get('sort_by', 'id')
        sort_order = kwargs.get('sort_order', 'desc')
        
        if hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == 'asc':
                query = query.order_by(asc(column))
            else:
                query = query.order_by(desc(column))
        
        return query
    
    def _add_audit_fields(self, instance, action: str):
        """Agrega campos de auditoría a la instancia."""
        now = datetime.utcnow()
        user_id = self.current_user.get('id') if self.current_user else None
        
        if action == 'create':
            if hasattr(instance, 'created_at'):
                instance.created_at = now
            if hasattr(instance, 'created_by') and user_id:
                instance.created_by = user_id
        
        if hasattr(instance, 'updated_at'):
            instance.updated_at = now
        if hasattr(instance, 'updated_by') and user_id:
            instance.updated_by = user_id
    
    def _use_soft_delete(self) -> bool:
        """Indica si el modelo usa eliminación lógica."""
        return hasattr(self.model, 'deleted_at')
    
    def _soft_delete(self, instance):
        """Realiza eliminación lógica."""
        if hasattr(instance, 'deleted_at'):
            instance.deleted_at = datetime.utcnow()
        if hasattr(instance, 'deleted_by') and self.current_user:
            instance.deleted_by = self.current_user.get('id')
    
    def _validate_delete(self, instance, **kwargs):
        """Valida que se puede eliminar la instancia. Sobrescribir en subclases."""
        pass
    
    def _log_activity(self, action: str, entity_id: int, data: Dict[str, Any]):
        """Registra actividad en el log de auditoría."""
        try:
            log_activity(
                user_id=self.current_user.get('id') if self.current_user else None,
                action=action,
                entity_type=self.entity_name,
                entity_id=entity_id,
                details=data
            )
        except Exception as e:
            self.logger.warning(f"No se pudo registrar actividad: {str(e)}")
    
    def _get_cache_key(self, operation: str, *args) -> str:
        """Genera clave de caché."""
        return f"{self.entity_name}:{operation}:{':'.join(map(str, args))}"
    
    def _invalidate_cache(self, operation: str, instance):
        """Invalida caché relacionado."""
        try:
            # Invalidar caché específico
            cache_key = self._get_cache_key('get', instance.id)
            cache_manager.delete(cache_key)
            
            # Invalidar caché de listados
            cache_manager.delete_pattern(f"{self.entity_name}:list:*")
            cache_manager.delete_pattern(f"{self.entity_name}:search:*")
            
        except Exception as e:
            self.logger.warning(f"Error invalidando caché: {str(e)}")
    
    # ==========================================
    # HOOKS PARA PERSONALIZACIÓN EN SUBCLASES
    # ==========================================
    
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook ejecutado antes de crear. Retorna datos modificados."""
        return data
    
    def _after_create(self, instance, data: Dict[str, Any], **kwargs):
        """Hook ejecutado después de crear. Retorna instancia modificada."""
        return instance
    
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook ejecutado antes de actualizar. Retorna datos modificados."""
        return data
    
    def _after_update(self, instance, data: Dict[str, Any], **kwargs):
        """Hook ejecutado después de actualizar. Retorna instancia modificada."""
        return instance
    
    def _before_delete(self, instance, **kwargs):
        """Hook ejecutado antes de eliminar."""
        pass
    
    def _after_delete(self, instance, **kwargs):
        """Hook ejecutado después de eliminar."""
        pass
    
    def _after_get(self, instance, **kwargs):
        """Hook ejecutado después de obtener. Retorna instancia modificada."""
        return instance
    
    def _before_list(self, query, filters: Dict[str, Any], **kwargs):
        """Hook ejecutado antes de listar. Retorna query modificada."""
        return query
    
    def _after_list(self, items: List[Dict[str, Any]], filters: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Hook ejecutado después de listar. Retorna items modificados."""
        return items
    
    # ==========================================
    # MÉTODOS DE UTILIDAD
    # ==========================================
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """
        Obtiene estadísticas básicas del modelo.
        Puede ser sobrescrito en subclases para estadísticas específicas.
        """
        try:
            query = self._build_base_query()
            
            total = query.count()
            
            # Estadísticas básicas
            stats = {
                'total': total,
                'created_today': 0,
                'created_this_week': 0,
                'created_this_month': 0
            }
            
            # Si el modelo tiene fecha de creación
            if hasattr(self.model, 'created_at'):
                today = date.today()
                stats['created_today'] = query.filter(
                    func.date(self.model.created_at) == today
                ).count()
                
                # Más estadísticas temporales pueden agregarse aquí
            
            return stats
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error obteniendo estadísticas de {self.entity_name}: {str(e)}")
            raise DatabaseException(f"Error obteniendo estadísticas de {self.entity_name}")
    
    def bulk_create(self, data_list: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Crea múltiples registros en una sola transacción.
        
        Args:
            data_list: Lista de datos para crear
            **kwargs: Argumentos adicionales
            
        Returns:
            Lista de registros creados serializados
        """
        try:
            instances = []
            
            for data in data_list:
                # Validar cada elemento
                validated_data = self._validate_create_data(data)
                validated_data = self._before_create(validated_data, **kwargs)
                
                # Crear instancia
                instance = self.model(**validated_data)
                self._add_audit_fields(instance, action='create')
                instances.append(instance)
            
            # Agregar todas las instancias
            self.db.add_all(instances)
            self.db.commit()
            
            # Serializar respuestas
            results = []
            for instance in instances:
                instance = self._after_create(instance, {}, **kwargs)
                results.append(self._serialize_response(instance))
                
                # Log individual
                self._log_activity('bulk_create', instance.id, {})
            
            # Limpiar caché
            cache_manager.delete_pattern(f"{self.entity_name}:*")
            
            return results
            
        except (ValidationError, SQLAlchemyError) as e:
            self.db.rollback()
            if isinstance(e, ValidationError):
                raise ValidationException(f"Error de validación en creación masiva", e.messages)
            else:
                self.logger.error(f"Error en creación masiva de {self.entity_name}: {str(e)}")
                raise DatabaseException(f"Error en creación masiva de {self.entity_name}")
    
    def bulk_update(self, updates: List[Tuple[int, Dict[str, Any]]], **kwargs) -> List[Dict[str, Any]]:
        """
        Actualiza múltiples registros en una sola transacción.
        
        Args:
            updates: Lista de tuplas (id, data) para actualizar
            **kwargs: Argumentos adicionales
            
        Returns:
            Lista de registros actualizados serializados
        """
        try:
            results = []
            
            for id, data in updates:
                # Obtener y actualizar cada instancia
                instance = self._get_instance_by_id(id)
                validated_data = self._validate_update_data(data, instance)
                validated_data = self._before_update(instance, validated_data, **kwargs)
                
                # Aplicar cambios
                for key, value in validated_data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                
                self._add_audit_fields(instance, action='update')
                instance = self._after_update(instance, validated_data, **kwargs)
                results.append(self._serialize_response(instance))
                
                # Log individual
                self._log_activity('bulk_update', instance.id, validated_data)
            
            self.db.commit()
            
            # Limpiar caché
            cache_manager.delete_pattern(f"{self.entity_name}:*")
            
            return results
            
        except (ValidationError, SQLAlchemyError) as e:
            self.db.rollback()
            if isinstance(e, ValidationError):
                raise ValidationException(f"Error de validación en actualización masiva", e.messages)
            else:
                self.logger.error(f"Error en actualización masiva de {self.entity_name}: {str(e)}")
                raise DatabaseException(f"Error en actualización masiva de {self.entity_name}")


class ReadOnlyService(BaseService):
    """
    Servicio de solo lectura que deshabilita operaciones de escritura.
    Útil para vistas o entidades que no deben modificarse directamente.
    """
    
    def create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        raise BusinessLogicException(f"No se permite crear {self.entity_name}")
    
    def update(self, id: int, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        raise BusinessLogicException(f"No se permite actualizar {self.entity_name}")
    
    def delete(self, id: int, **kwargs) -> bool:
        raise BusinessLogicException(f"No se permite eliminar {self.entity_name}")
    
    def bulk_create(self, data_list: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        raise BusinessLogicException(f"No se permite crear {self.entity_name} masivamente")
    
    def bulk_update(self, updates: List[Tuple[int, Dict[str, Any]]], **kwargs) -> List[Dict[str, Any]]:
        raise BusinessLogicException(f"No se permite actualizar {self.entity_name} masivamente")