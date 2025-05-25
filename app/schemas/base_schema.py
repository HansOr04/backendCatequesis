"""
Schema base para el sistema de catequesis.
Proporciona clases base y utilidades comunes para todos los schemas.
"""

from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime, date
from decimal import Decimal
from marshmallow import Schema, fields, validate, ValidationError, post_load, pre_dump
from marshmallow.decorators import validates_schema
import logging

logger = logging.getLogger(__name__)


class BaseField(fields.Field):
    """Campo base personalizado con validaciones comunes."""
    
    def __init__(self, *args, **kwargs):
        # Configuraciones por defecto
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        self.convert_empty_to_none = kwargs.pop('convert_empty_to_none', True)
        super().__init__(*args, **kwargs)
    
    def _deserialize(self, value, attr, data, **kwargs):
        """Deserialización con procesamiento común."""
        if value is None:
            return None
        
        # Convertir strings vacíos a None si está habilitado
        if self.convert_empty_to_none and isinstance(value, str) and not value.strip():
            return None
        
        # Limpiar espacios en blanco si está habilitado
        if self.trim_whitespace and isinstance(value, str):
            value = value.strip()
        
        return super()._deserialize(value, attr, data, **kwargs)


class TrimmedString(BaseField, fields.String):
    """Campo String que automáticamente limpia espacios en blanco."""
    pass


class PositiveInteger(BaseField, fields.Integer):
    """Campo Integer que solo acepta valores positivos."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validate', validate.Range(min=1))
        super().__init__(*args, **kwargs)


class NonNegativeInteger(BaseField, fields.Integer):
    """Campo Integer que acepta valores no negativos (>= 0)."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validate', validate.Range(min=0))
        super().__init__(*args, **kwargs)


class PositiveDecimal(BaseField, fields.Decimal):
    """Campo Decimal que solo acepta valores positivos."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validate', validate.Range(min=0.01))
        super().__init__(*args, **kwargs)


class NonNegativeDecimal(BaseField, fields.Decimal):
    """Campo Decimal que acepta valores no negativos (>= 0)."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validate', validate.Range(min=0))
        super().__init__(*args, **kwargs)


class DocumentoIdentidad(TrimmedString):
    """Campo para documentos de identidad con validaciones específicas."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validate', [
            validate.Length(min=5, max=20),
            validate.Regexp(r'^[0-9A-Za-z\-]+$', error="Formato de documento inválido")
        ])
        super().__init__(*args, **kwargs)


class Telefono(TrimmedString):
    """Campo para números telefónicos."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validate', [
            validate.Length(min=7, max=15),
            validate.Regexp(r'^[\+]?[0-9\-\s\(\)]+$', error="Formato de teléfono inválido")
        ])
        super().__init__(*args, **kwargs)


class Email(fields.Email):
    """Campo Email mejorado."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validate', validate.Length(max=254))
        super().__init__(*args, **kwargs)
    
    def _deserialize(self, value, attr, data, **kwargs):
        """Normaliza el email a minúsculas."""
        if isinstance(value, str):
            value = value.strip().lower()
        return super()._deserialize(value, attr, data, **kwargs)


class FechaNacimiento(fields.Date):
    """Campo para fechas de nacimiento con validaciones."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def _deserialize(self, value, attr, data, **kwargs):
        """Valida que la fecha de nacimiento sea válida."""
        fecha = super()._deserialize(value, attr, data, **kwargs)
        
        if fecha:
            hoy = date.today()
            # No puede ser fecha futura
            if fecha > hoy:
                raise ValidationError("La fecha de nacimiento no puede ser futura")
            
            # No puede ser muy antigua (más de 150 años)
            años = (hoy - fecha).days / 365.25
            if años > 150:
                raise ValidationError("La fecha de nacimiento no puede ser mayor a 150 años")
        
        return fecha


class EnumField(BaseField, fields.String):
    """Campo para enumeraciones."""
    
    def __init__(self, enum_class, *args, **kwargs):
        self.enum_class = enum_class
        valid_values = [e.value for e in enum_class]
        kwargs.setdefault('validate', validate.OneOf(valid_values))
        super().__init__(*args, **kwargs)
    
    def _deserialize(self, value, attr, data, **kwargs):
        """Convierte string a enum."""
        value = super()._deserialize(value, attr, data, **kwargs)
        if value is not None:
            try:
                return self.enum_class(value)
            except ValueError:
                raise ValidationError(f"Valor '{value}' no válido para {self.enum_class.__name__}")
        return value
    
    def _serialize(self, value, attr, obj, **kwargs):
        """Convierte enum a string."""
        if value is not None:
            return value.value if hasattr(value, 'value') else str(value)
        return value


class BaseSchema(Schema):
    """
    Schema base para todos los schemas del sistema.
    Proporciona funcionalidad común y validaciones base.
    """
    
    class Meta:
        """Configuración base del schema."""
        # Incluir campos desconocidos pero no fallar
        unknown = 'INCLUDE'
        # Ordenar campos por nombre
        ordered = True
        # Formato de fecha por defecto
        dateformat = '%Y-%m-%d'
        # Formato de datetime por defecto
        datetimeformat = '%Y-%m-%d %H:%M:%S'
    
    # Campos de auditoría comunes
    id = NonNegativeInteger(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True, allow_none=True)
    updated_at = fields.DateTime(dump_only=True, allow_none=True)
    created_by = TrimmedString(dump_only=True, allow_none=True)
    updated_by = TrimmedString(dump_only=True, allow_none=True)
    version = NonNegativeInteger(dump_only=True, allow_none=True, missing=0)
    is_active = fields.Boolean(dump_only=True, allow_none=True, missing=True)
    
    def __init__(self, *args, **kwargs):
        """Inicializa el schema con configuraciones adicionales."""
        # Opciones de serialización
        self.exclude_null = kwargs.pop('exclude_null', False)
        self.exclude_audit = kwargs.pop('exclude_audit', False)
        self.include_metadata = kwargs.pop('include_metadata', False)
        
        super().__init__(*args, **kwargs)
        
        # Excluir campos de auditoría si se solicita
        if self.exclude_audit:
            audit_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'version']
            for field in audit_fields:
                if field in self.fields:
                    self.fields.pop(field)
    
    @post_load
    def make_object(self, data, **kwargs):
        """Post-procesamiento después de la carga."""
        # Limpiar valores None si se solicita
        if hasattr(self, 'exclude_null') and self.exclude_null:
            data = {k: v for k, v in data.items() if v is not None}
        
        return data
    
    @pre_dump
    def prepare_dump(self, obj, **kwargs):
        """Pre-procesamiento antes del dump."""
        # Si es un modelo, convertir a dict
        if hasattr(obj, 'to_dict'):
            return obj.to_dict(include_audit=not self.exclude_audit)
        return obj
    
    def validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Valida que los campos requeridos estén presentes."""
        missing_fields = []
        
        for field_name, field_obj in self.fields.items():
            if field_obj.required and field_name not in data:
                missing_fields.append(field_name)
        
        if missing_fields:
            raise ValidationError(f"Campos requeridos faltantes: {', '.join(missing_fields)}")
    
    def dump_json(self, obj, *args, **kwargs) -> str:
        """Serializa objeto a JSON string."""
        import json
        from datetime import datetime, date
        
        def json_serializer(o):
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            elif isinstance(o, Decimal):
                return float(o)
            raise TypeError(f"Object of type {type(o)} is not JSON serializable")
        
        data = self.dump(obj, *args, **kwargs)
        return json.dumps(data, default=json_serializer, ensure_ascii=False, indent=2)
    
    def load_json(self, json_str: str, *args, **kwargs):
        """Deserializa desde JSON string."""
        import json
        data = json.loads(json_str)
        return self.load(data, *args, **kwargs)
    
    def validate_business_rules(self, data: Dict[str, Any]) -> None:
        """Método para validaciones de reglas de negocio específicas."""
        pass
    
    @validates_schema
    def validate_schema(self, data, **kwargs):
        """Validación general del schema."""
        # Ejecutar validaciones de reglas de negocio
        self.validate_business_rules(data)


class PaginationSchema(BaseSchema):
    """Schema para parámetros de paginación."""
    
    page = PositiveInteger(missing=1, validate=validate.Range(min=1))
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(allow_none=True)
    sort_order = TrimmedString(
        allow_none=True, 
        validate=validate.OneOf(['asc', 'desc']),
        missing='asc'
    )


class SearchSchema(BaseSchema):
    """Schema para parámetros de búsqueda."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=255))
    filters = fields.Dict(allow_none=True)
    date_from = fields.Date(allow_none=True)
    date_to = fields.Date(allow_none=True)
    
    @validates_schema
    def validate_dates(self, data, **kwargs):
        """Valida que las fechas sean coherentes."""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("La fecha inicial no puede ser mayor a la fecha final")


class ResponseSchema(BaseSchema):
    """Schema para respuestas de API."""
    
    success = fields.Boolean(required=True)
    message = TrimmedString(allow_none=True)
    data = fields.Raw(allow_none=True)
    errors = fields.List(fields.String(), allow_none=True)
    metadata = fields.Dict(allow_none=True)
    pagination = fields.Nested('PaginationResponseSchema', allow_none=True)


class PaginationResponseSchema(BaseSchema):
    """Schema para respuestas paginadas."""
    
    page = PositiveInteger(required=True)
    pages = NonNegativeInteger(required=True)
    per_page = PositiveInteger(required=True)
    total = NonNegativeInteger(required=True)
    has_prev = fields.Boolean(required=True)
    prev_num = NonNegativeInteger(allow_none=True)
    has_next = fields.Boolean(required=True)
    next_num = NonNegativeInteger(allow_none=True)


class ErrorSchema(BaseSchema):
    """Schema para errores."""
    
    error_code = TrimmedString(required=True)
    message = TrimmedString(required=True)
    details = fields.Dict(allow_none=True)
    timestamp = fields.DateTime(required=True, missing=datetime.utcnow)


class ValidationErrorSchema(ErrorSchema):
    """Schema para errores de validación."""
    
    field_errors = fields.Dict(
        keys=fields.String(),
        values=fields.List(fields.String()),
        allow_none=True
    )


# Registro de schemas para facilitar el acceso
class SchemaRegistry:
    """Registro centralizado de schemas."""
    
    _schemas: Dict[str, Type[BaseSchema]] = {}
    
    @classmethod
    def register(cls, name: str, schema_class: Type[BaseSchema]) -> None:
        """Registra un schema."""
        cls._schemas[name] = schema_class
        logger.debug(f"Schema '{name}' registrado: {schema_class}")
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseSchema]]:
        """Obtiene un schema registrado."""
        return cls._schemas.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, Type[BaseSchema]]:
        """Obtiene todos los schemas registrados."""
        return cls._schemas.copy()
    
    @classmethod
    def create_instance(cls, name: str, **kwargs) -> Optional[BaseSchema]:
        """Crea una instancia de un schema registrado."""
        schema_class = cls.get(name)
        if schema_class:
            return schema_class(**kwargs)
        return None


# Decorador para registrar schemas automáticamente
def register_schema(name: str):
    """Decorador para registrar schemas."""
    def decorator(schema_class):
        SchemaRegistry.register(name, schema_class)
        return schema_class
    return decorator


# Funciones auxiliares para validaciones comunes
def validate_phone_number(phone: str) -> bool:
    """Valida formato de número telefónico."""
    import re
    pattern = r'^[\+]?[0-9\-\s\(\)]+$'
    return bool(re.match(pattern, phone.strip())) if phone else False


def validate_document_id(document: str, doc_type: str = 'CC') -> bool:
    """Valida documento de identidad según el tipo."""
    if not document:
        return False
    
    document = document.strip()
    
    if doc_type == 'CC':  # Cédula de ciudadanía
        return document.isdigit() and 5 <= len(document) <= 12
    elif doc_type == 'TI':  # Tarjeta de identidad
        return document.isdigit() and 8 <= len(document) <= 11
    elif doc_type == 'CE':  # Cédula de extranjería
        return len(document) >= 6 and len(document) <= 10
    elif doc_type == 'PA':  # Pasaporte
        return len(document) >= 6 and len(document) <= 20
    
    return True  # Para otros tipos, validación básica


def validate_email_format(email: str) -> bool:
    """Valida formato de email."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip().lower())) if email else False


def sanitize_string(value: str, max_length: int = None) -> str:
    """Sanitiza y limpia string."""
    if not value:
        return ""
    
    # Limpiar espacios y caracteres especiales
    cleaned = value.strip()
    
    # Truncar si es necesario
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned


# Registrar schemas base
SchemaRegistry.register('base', BaseSchema)
SchemaRegistry.register('pagination', PaginationSchema)
SchemaRegistry.register('search', SearchSchema)
SchemaRegistry.register('response', ResponseSchema)
SchemaRegistry.register('error', ErrorSchema)
SchemaRegistry.register('validation_error', ValidationErrorSchema)