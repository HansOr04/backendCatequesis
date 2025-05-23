"""
Modelo base para el sistema de catequesis.
Proporciona funcionalidad común para todos los modelos de datos.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Type, TypeVar
from dataclasses import dataclass, field, asdict
from enum import Enum

from app.database.stored_procedures import get_sp_manager
from app.core.exceptions import ValidationError, ModelError
from app.utils.validators import DataValidator
from app.utils.constants import SystemConstants

logger = logging.getLogger(__name__)

# Type variable para métodos genéricos
T = TypeVar('T', bound='BaseModel')


class ModelStatus(Enum):
    """Estados posibles de los modelos."""
    ACTIVE = "activo"
    INACTIVE = "inactivo"
    DELETED = "eliminado"
    PENDING = "pendiente"


@dataclass
class AuditInfo:
    """Información de auditoría para los modelos."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la información de auditoría a diccionario."""
        return {
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'version': self.version
        }


class BaseModel(ABC):
    """
    Clase base abstracta para todos los modelos del sistema.
    Proporciona funcionalidad común de CRUD y validación.
    """
    
    # Configuración del modelo
    _table_schema: str = ""
    _primary_key: str = "id"
    _required_fields: List[str] = []
    _unique_fields: List[str] = []
    _searchable_fields: List[str] = []
    
    def __init__(self, **kwargs):
        """
        Inicializa el modelo base.
        
        Args:
            **kwargs: Atributos del modelo
        """
        self._sp_manager = get_sp_manager()
        self._validator = DataValidator()
        self._original_data = {}
        self._changed_fields = set()
        
        # Información de auditoría
        self.audit_info = AuditInfo()
        
        # Estado del modelo
        self.status = ModelStatus.ACTIVE
        
        # Cargar datos iniciales
        self._load_data(kwargs)
    
    def _load_data(self, data: Dict[str, Any]) -> None:
        """
        Carga datos en el modelo.
        
        Args:
            data: Diccionario con los datos
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
                self._original_data[key] = value
    
    @property
    def primary_key_value(self) -> Any:
        """Obtiene el valor de la clave primaria."""
        return getattr(self, self._primary_key, None)
    
    @property
    def is_new(self) -> bool:
        """Verifica si el modelo es nuevo (no guardado)."""
        return self.primary_key_value is None
    
    @property
    def has_changes(self) -> bool:
        """Verifica si el modelo tiene cambios pendientes."""
        return len(self._changed_fields) > 0
    
    @property
    def changed_fields(self) -> set:
        """Obtiene los campos que han cambiado."""
        return self._changed_fields.copy()
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Intercepta la asignación de atributos para detectar cambios.
        
        Args:
            name: Nombre del atributo
            value: Valor del atributo
        """
        # Permitir atributos privados sin control de cambios
        if name.startswith('_') or name in ['audit_info', 'status']:
            super().__setattr__(name, value)
            return
        
        # Detectar cambios solo si el objeto ya está inicializado
        if hasattr(self, '_original_data'):
            old_value = getattr(self, name, None)
            if old_value != value:
                self._changed_fields.add(name)
        
        super().__setattr__(name, value)
    
    def validate(self) -> bool:
        """
        Valida el modelo según las reglas definidas.
        
        Returns:
            bool: True si es válido
            
        Raises:
            ValidationError: Si la validación falla
        """
        try:
            # Validar campos requeridos
            self._validate_required_fields()
            
            # Validar campos únicos
            self._validate_unique_fields()
            
            # Validación específica del modelo
            self._validate_model_specific()
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando modelo {self.__class__.__name__}: {str(e)}")
            raise ValidationError(f"Validación fallida: {str(e)}")
    
    def _validate_required_fields(self) -> None:
        """Valida que los campos requeridos tengan valor."""
        for field in self._required_fields:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValidationError(f"El campo '{field}' es requerido")
    
    def _validate_unique_fields(self) -> None:
        """Valida que los campos únicos no estén duplicados."""
        if not self._unique_fields:
            return
        
        for field in self._unique_fields:
            value = getattr(self, field, None)
            if value is not None:
                # Solo validar si es un modelo nuevo o si el campo cambió
                if self.is_new or field in self._changed_fields:
                    if self._field_exists(field, value):
                        raise ValidationError(f"Ya existe un registro con {field} = '{value}'")
    
    @abstractmethod
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo. Debe ser implementada por cada modelo."""
        pass
    
    def _field_exists(self, field: str, value: Any) -> bool:
        """
        Verifica si un valor de campo ya existe en la base de datos.
        
        Args:
            field: Nombre del campo
            value: Valor a verificar
            
        Returns:
            bool: True si existe
        """
        try:
            # Implementar según el schema del modelo
            result = self._sp_manager.executor.execute(
                self._table_schema,
                'existe_campo',
                {
                    'campo': field,
                    'valor': value,
                    'excluir_id': self.primary_key_value
                }
            )
            return result.get('existe', False)
        except Exception:
            # Si no existe el SP, asumir que no existe
            return False
    
    def save(self, usuario: str = None) -> 'BaseModel':
        """
        Guarda el modelo en la base de datos.
        
        Args:
            usuario: Usuario que realiza la operación
            
        Returns:
            BaseModel: El modelo guardado
            
        Raises:
            ValidationError: Si la validación falla
            ModelError: Si hay error al guardar
        """
        try:
            # Validar antes de guardar
            self.validate()
            
            # Actualizar información de auditoría
            now = datetime.now()
            if self.is_new:
                self.audit_info.created_at = now
                self.audit_info.created_by = usuario
                operation = 'crear'
            else:
                self.audit_info.updated_at = now
                self.audit_info.updated_by = usuario
                self.audit_info.version += 1
                operation = 'actualizar'
            
            # Preparar datos para guardar
            data = self.to_dict()
            
            # Ejecutar stored procedure
            result = self._sp_manager.executor.execute(
                self._table_schema,
                operation,
                data
            )
            
            # Actualizar con datos devueltos por la BD
            if result.get('success'):
                returned_data = result.get('data', {})
                if returned_data:
                    self._load_data(returned_data)
                
                # Limpiar campos cambiados
                self._changed_fields.clear()
                self._original_data = self.to_dict()
                
                logger.info(f"Modelo {self.__class__.__name__} guardado exitosamente")
                return self
            else:
                raise ModelError(f"Error guardando modelo: {result.get('message', 'Error desconocido')}")
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error guardando modelo {self.__class__.__name__}: {str(e)}")
            raise ModelError(f"Error al guardar: {str(e)}")
    
    def delete(self, usuario: str = None, soft_delete: bool = True) -> bool:
        """
        Elimina el modelo.
        
        Args:
            usuario: Usuario que realiza la operación
            soft_delete: Si usar eliminación lógica
            
        Returns:
            bool: True si se eliminó exitosamente
            
        Raises:
            ModelError: Si hay error al eliminar
        """
        try:
            if self.is_new:
                raise ModelError("No se puede eliminar un modelo que no ha sido guardado")
            
            if soft_delete:
                # Eliminación lógica
                self.status = ModelStatus.DELETED
                self.audit_info.updated_at = datetime.now()
                self.audit_info.updated_by = usuario
                operation = 'eliminar_logico'
            else:
                # Eliminación física
                operation = 'eliminar'
            
            result = self._sp_manager.executor.execute(
                self._table_schema,
                operation,
                {self._primary_key: self.primary_key_value}
            )
            
            if result.get('success'):
                logger.info(f"Modelo {self.__class__.__name__} eliminado exitosamente")
                return True
            else:
                raise ModelError(f"Error eliminando modelo: {result.get('message', 'Error desconocido')}")
                
        except Exception as e:
            logger.error(f"Error eliminando modelo {self.__class__.__name__}: {str(e)}")
            raise ModelError(f"Error al eliminar: {str(e)}")
    
    def refresh(self) -> 'BaseModel':
        """
        Recarga el modelo desde la base de datos.
        
        Returns:
            BaseModel: El modelo actualizado
            
        Raises:
            ModelError: Si hay error al recargar
        """
        try:
            if self.is_new:
                raise ModelError("No se puede recargar un modelo que no ha sido guardado")
            
            result = self._sp_manager.executor.execute(
                self._table_schema,
                'obtener',
                {self._primary_key: self.primary_key_value}
            )
            
            if result.get('success') and result.get('data'):
                self._load_data(result['data'])
                self._changed_fields.clear()
                logger.debug(f"Modelo {self.__class__.__name__} recargado exitosamente")
                return self
            else:
                raise ModelError("Modelo no encontrado en la base de datos")
                
        except Exception as e:
            logger.error(f"Error recargando modelo {self.__class__.__name__}: {str(e)}")
            raise ModelError(f"Error al recargar: {str(e)}")
    
    def to_dict(self, include_audit: bool = False) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario.
        
        Args:
            include_audit: Si incluir información de auditoría
            
        Returns:
            dict: Datos del modelo
        """
        data = {}
        
        # Obtener todos los atributos públicos
        for key, value in self.__dict__.items():
            if not key.startswith('_') and key not in ['audit_info', 'status']:
                # Convertir fechas a string
                if isinstance(value, (datetime, date)):
                    data[key] = value.isoformat()
                elif isinstance(value, Enum):
                    data[key] = value.value
                else:
                    data[key] = value
        
        # Incluir estado
        data['status'] = self.status.value
        
        # Incluir auditoría si se solicita
        if include_audit:
            data['audit_info'] = self.audit_info.to_dict()
        
        return data
    
    @classmethod
    def find_by_id(cls: Type[T], id_value: Any) -> Optional[T]:
        """
        Busca un modelo por su ID.
        
        Args:
            id_value: Valor del ID
            
        Returns:
            Model: El modelo encontrado o None
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                cls._table_schema,
                'obtener',
                {cls._primary_key: id_value}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando {cls.__name__} por ID {id_value}: {str(e)}")
            return None
    
    @classmethod
    def find_all(cls: Type[T], filters: Dict[str, Any] = None) -> List[T]:
        """
        Busca todos los modelos que coincidan con los filtros.
        
        Args:
            filters: Filtros de búsqueda
            
        Returns:
            List: Lista de modelos encontrados
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                cls._table_schema,
                'obtener_todos',
                filters or {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando todos los {cls.__name__}: {str(e)}")
            return []
    
    @classmethod
    def search(cls: Type[T], term: str, fields: List[str] = None) -> List[T]:
        """
        Busca modelos por término de búsqueda.
        
        Args:
            term: Término de búsqueda
            fields: Campos donde buscar (usa _searchable_fields si no se especifica)
            
        Returns:
            List: Lista de modelos encontrados
        """
        try:
            search_fields = fields or cls._searchable_fields
            if not search_fields:
                return []
            
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                cls._table_schema,
                'buscar',
                {
                    'termino': term,
                    'campos': search_fields
                }
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando {cls.__name__} con término '{term}': {str(e)}")
            return []
    
    def __str__(self) -> str:
        """Representación en string del modelo."""
        return f"{self.__class__.__name__}(id={self.primary_key_value})"
    
    def __repr__(self) -> str:
        """Representación detallada del modelo."""
        return f"{self.__class__.__name__}({self.to_dict()})"


class ModelFactory:
    """Factory para crear instancias de modelos."""
    
    _models: Dict[str, Type[BaseModel]] = {}
    
    @classmethod
    def register(cls, name: str, model_class: Type[BaseModel]) -> None:
        """
        Registra un modelo en la factory.
        
        Args:
            name: Nombre del modelo
            model_class: Clase del modelo
        """
        cls._models[name.lower()] = model_class
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseModel:
        """
        Crea una instancia de modelo.
        
        Args:
            name: Nombre del modelo
            **kwargs: Datos del modelo
            
        Returns:
            BaseModel: Instancia del modelo
            
        Raises:
            ModelError: Si el modelo no está registrado
        """
        model_class = cls._models.get(name.lower())
        if not model_class:
            raise ModelError(f"Modelo '{name}' no registrado")
        
        return model_class(**kwargs)
    @classmethod
    def get_registered_models(cls) -> List[str]:
        """Obtiene la lista de modelos registrados."""
        return list(cls._models.keys())


# Funciones de utilidad para trabajar con modelos
def get_model_by_name(name: str) -> Optional[Type[BaseModel]]:
    """
    Obtiene una clase de modelo por nombre.
    
    Args:
        name: Nombre del modelo
        
    Returns:
        Type[BaseModel]: Clase del modelo o None si no existe
    """
    return ModelFactory._models.get(name.lower())


def create_model_instance(name: str, **kwargs) -> Optional[BaseModel]:
    """
    Crea una instancia de modelo por nombre.
    
    Args:
        name: Nombre del modelo
        **kwargs: Datos del modelo
        
    Returns:
        BaseModel: Instancia del modelo o None si no existe
    """
    try:
        return ModelFactory.create(name, **kwargs)
    except ModelError:
        return None


def validate_model_data(model_class: Type[BaseModel], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida datos para un modelo específico sin crear la instancia.
    
    Args:
        model_class: Clase del modelo
        data: Datos a validar
        
    Returns:
        dict: Resultado de la validación
    """
    try:
        # Crear instancia temporal para validar
        temp_instance = model_class(**data)
        temp_instance.validate()
        
        return {
            'valid': True,
            'errors': [],
            'cleaned_data': temp_instance.to_dict()
        }
        
    except ValidationError as e:
        return {
            'valid': False,
            'errors': [str(e)],
            'cleaned_data': None
        }
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Error inesperado: {str(e)}"],
            'cleaned_data': None
        }


class ModelMetrics:
    """Clase para obtener métricas de los modelos."""
    
    @staticmethod
    def get_model_statistics() -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de los modelos registrados.
        
        Returns:
            dict: Estadísticas de los modelos
        """
        registered_models = ModelFactory.get_registered_models()
        
        stats = {
            'total_models': len(registered_models),
            'models': {},
            'total_instances_created': 0,
            'validation_errors': 0
        }
        
        for model_name in registered_models:
            model_class = ModelFactory._models[model_name]
            
            # Información básica del modelo
            model_info = {
                'class_name': model_class.__name__,
                'table_schema': getattr(model_class, '_table_schema', ''),
                'primary_key': getattr(model_class, '_primary_key', ''),
                'required_fields': getattr(model_class, '_required_fields', []),
                'unique_fields': getattr(model_class, '_unique_fields', []),
                'searchable_fields': getattr(model_class, '_searchable_fields', [])
            }
            
            stats['models'][model_name] = model_info
        
        return stats
    
    @staticmethod
    def validate_model_integrity() -> Dict[str, Any]:
        """
        Valida la integridad de todos los modelos registrados.
        
        Returns:
            dict: Resultado de la validación de integridad
        """
        registered_models = ModelFactory.get_registered_models()
        integrity_report = {
            'valid_models': [],
            'invalid_models': [],
            'total_checked': len(registered_models),
            'errors': []
        }
        
        for model_name in registered_models:
            try:
                model_class = ModelFactory._models[model_name]
                
                # Verificar que tenga los atributos requeridos
                required_attrs = ['_table_schema', '_primary_key', '_required_fields']
                missing_attrs = []
                
                for attr in required_attrs:
                    if not hasattr(model_class, attr):
                        missing_attrs.append(attr)
                
                if missing_attrs:
                    integrity_report['invalid_models'].append({
                        'model': model_name,
                        'error': f"Faltan atributos: {missing_attrs}"
                    })
                else:
                    # Intentar crear una instancia vacía para verificar inicialización
                    try:
                        temp_instance = model_class()
                        integrity_report['valid_models'].append(model_name)
                    except Exception as e:
                        integrity_report['invalid_models'].append({
                            'model': model_name,
                            'error': f"Error en inicialización: {str(e)}"
                        })
                        
            except Exception as e:
                integrity_report['errors'].append(f"Error procesando {model_name}: {str(e)}")
        
        return integrity_report


class ModelQueryBuilder:
    """Constructor de consultas para modelos."""
    
    def __init__(self, model_class: Type[BaseModel]):
        """
        Inicializa el constructor de consultas.
        
        Args:
            model_class: Clase del modelo
        """
        self.model_class = model_class
        self.filters = {}
        self.order_by = []
        self.limit_value = None
        self.offset_value = None
    
    def filter(self, **kwargs) -> 'ModelQueryBuilder':
        """
        Agrega filtros a la consulta.
        
        Args:
            **kwargs: Filtros clave-valor
            
        Returns:
            ModelQueryBuilder: Instancia para encadenamiento
        """
        self.filters.update(kwargs)
        return self
    
    def order_by_field(self, field: str, ascending: bool = True) -> 'ModelQueryBuilder':
        """
        Agrega ordenamiento por campo.
        
        Args:
            field: Campo para ordenar
            ascending: Si es ascendente
            
        Returns:
            ModelQueryBuilder: Instancia para encadenamiento
        """
        direction = 'ASC' if ascending else 'DESC'
        self.order_by.append(f"{field} {direction}")
        return self
    
    def limit(self, count: int) -> 'ModelQueryBuilder':
        """
        Establece límite de resultados.
        
        Args:
            count: Número máximo de resultados
            
        Returns:
            ModelQueryBuilder: Instancia para encadenamiento
        """
        self.limit_value = count
        return self
    
    def offset(self, count: int) -> 'ModelQueryBuilder':
        """
        Establece offset de resultados.
        
        Args:
            count: Número de registros a saltar
            
        Returns:
            ModelQueryBuilder: Instancia para encadenamiento
        """
        self.offset_value = count
        return self
    
    def execute(self) -> List[BaseModel]:
        """
        Ejecuta la consulta construida.
        
        Returns:
            List[BaseModel]: Lista de modelos encontrados
        """
        try:
            sp_manager = get_sp_manager()
            
            # Construir parámetros de consulta
            query_params = self.filters.copy()
            
            if self.order_by:
                query_params['order_by'] = ', '.join(self.order_by)
            
            if self.limit_value:
                query_params['limit'] = self.limit_value
            
            if self.offset_value:
                query_params['offset'] = self.offset_value
            
            # Ejecutar consulta
            result = sp_manager.executor.execute(
                self.model_class._table_schema,
                'buscar_avanzado',
                query_params
            )
            
            if result.get('success') and result.get('data'):
                return [self.model_class(**item) for item in result['data']]
            
            return []
            
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {str(e)}")
            return []
    
    def count(self) -> int:
        """
        Cuenta los resultados sin obtenerlos.
        
        Returns:
            int: Número de resultados
        """
        try:
            sp_manager = get_sp_manager()
            
            result = sp_manager.executor.execute(
                self.model_class._table_schema,
                'contar',
                self.filters
            )
            
            if result.get('success') and result.get('data'):
                return result['data'].get('count', 0)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error contando resultados: {str(e)}")
            return 0
    
    def exists(self) -> bool:
        """
        Verifica si existen resultados.
        
        Returns:
            bool: True si existen resultados
        """
        return self.count() > 0


class ModelCache:
    """Cache simple para modelos."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Inicializa el cache.
        
        Args:
            max_size: Tamaño máximo del cache
            ttl_seconds: Tiempo de vida en segundos
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
    
    def get(self, key: str) -> Optional[BaseModel]:
        """
        Obtiene un modelo del cache.
        
        Args:
            key: Clave del cache
            
        Returns:
            BaseModel: Modelo cacheado o None
        """
        if key not in self.cache:
            return None
        
        # Verificar TTL
        if self._is_expired(key):
            self.remove(key)
            return None
        
        # Actualizar tiempo de acceso
        self.access_times[key] = datetime.now()
        return self.cache[key]
    
    def set(self, key: str, model: BaseModel) -> None:
        """
        Guarda un modelo en el cache.
        
        Args:
            key: Clave del cache
            model: Modelo a cachear
        """
        # Limpiar cache si está lleno
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = model
        self.access_times[key] = datetime.now()
    
    def remove(self, key: str) -> None:
        """
        Remueve un modelo del cache.
        
        Args:
            key: Clave del cache
        """
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
    
    def clear(self) -> None:
        """Limpia todo el cache."""
        self.cache.clear()
        self.access_times.clear()
    
    def _is_expired(self, key: str) -> bool:
        """Verifica si una entrada está expirada."""
        if key not in self.access_times:
            return True
        
        age = datetime.now() - self.access_times[key]
        return age.total_seconds() > self.ttl_seconds
    
    def _evict_oldest(self) -> None:
        """Remueve la entrada más antigua."""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.remove(oldest_key)


# Cache global para modelos
model_cache = ModelCache()


class ModelRepository:
    """Repositorio base para operaciones comunes de modelos."""
    
    def __init__(self, model_class: Type[BaseModel], use_cache: bool = True):
        """
        Inicializa el repositorio.
        
        Args:
            model_class: Clase del modelo
            use_cache: Si usar cache
        """
        self.model_class = model_class
        self.use_cache = use_cache
        self.query_builder = ModelQueryBuilder(model_class)
    
    def find_by_id(self, id_value: Any, use_cache: bool = None) -> Optional[BaseModel]:
        """
        Busca un modelo por ID con cache opcional.
        
        Args:
            id_value: Valor del ID
            use_cache: Si usar cache (usa configuración por defecto si es None)
            
        Returns:
            BaseModel: Modelo encontrado o None
        """
        should_cache = use_cache if use_cache is not None else self.use_cache
        cache_key = f"{self.model_class.__name__}:{id_value}"
        
        # Intentar obtener del cache
        if should_cache:
            cached_model = model_cache.get(cache_key)
            if cached_model:
                return cached_model
        
        # Buscar en base de datos
        model = self.model_class.find_by_id(id_value)
        
        # Guardar en cache
        if model and should_cache:
            model_cache.set(cache_key, model)
        
        return model
    
    def find_all(self, filters: Dict[str, Any] = None) -> List[BaseModel]:
        """
        Busca todos los modelos con filtros opcionales.
        
        Args:
            filters: Filtros de búsqueda
            
        Returns:
            List[BaseModel]: Lista de modelos
        """
        return self.model_class.find_all(filters)
    
    def search(self, term: str, fields: List[str] = None) -> List[BaseModel]:
        """
        Busca modelos por término.
        
        Args:
            term: Término de búsqueda
            fields: Campos donde buscar
            
        Returns:
            List[BaseModel]: Lista de modelos encontrados
        """
        return self.model_class.search(term, fields)
    
    def query(self) -> ModelQueryBuilder:
        """
        Obtiene un constructor de consultas.
        
        Returns:
            ModelQueryBuilder: Constructor de consultas
        """
        return ModelQueryBuilder(self.model_class)
    
    def save(self, model: BaseModel, usuario: str = None) -> BaseModel:
        """
        Guarda un modelo y actualiza el cache.
        
        Args:
            model: Modelo a guardar
            usuario: Usuario que realiza la operación
            
        Returns:
            BaseModel: Modelo guardado
        """
        saved_model = model.save(usuario)
        
        # Actualizar cache
        if self.use_cache and saved_model.primary_key_value:
            cache_key = f"{self.model_class.__name__}:{saved_model.primary_key_value}"
            model_cache.set(cache_key, saved_model)
        
        return saved_model
    
    def delete(self, model: BaseModel, usuario: str = None, soft_delete: bool = True) -> bool:
        """
        Elimina un modelo y actualiza el cache.
        
        Args:
            model: Modelo a eliminar
            usuario: Usuario que realiza la operación
            soft_delete: Si usar eliminación lógica
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        success = model.delete(usuario, soft_delete)
        
        # Remover del cache
        if success and self.use_cache and model.primary_key_value:
            cache_key = f"{self.model_class.__name__}:{model.primary_key_value}"
            model_cache.remove(cache_key)
        
        return success


# Funciones de conveniencia para crear repositorios
def get_repository(model_class: Type[BaseModel], use_cache: bool = True) -> ModelRepository:
    """
    Crea un repositorio para una clase de modelo.
    
    Args:
        model_class: Clase del modelo
        use_cache: Si usar cache
        
    Returns:
        ModelRepository: Repositorio configurado
    """
    return ModelRepository(model_class, use_cache)


def get_repository_by_name(model_name: str, use_cache: bool = True) -> Optional[ModelRepository]:
    """
    Crea un repositorio por nombre de modelo.
    
    Args:
        model_name: Nombre del modelo
        use_cache: Si usar cache
        
    Returns:
        ModelRepository: Repositorio configurado o None
    """
    model_class = get_model_by_name(model_name)
    if model_class:
        return ModelRepository(model_class, use_cache)
    return None


# Decorador para transacciones (placeholder para implementación futura)
def transactional(func):
    """
    Decorador para operaciones transaccionales.
    
    Args:
        func: Función a decorar
        
    Returns:
        function: Función decorada
    """
    def wrapper(*args, **kwargs):
        # TODO: Implementar lógica transaccional
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # TODO: Rollback de transacción
            logger.error(f"Error en transacción: {str(e)}")
            raise
    
    return wrapper