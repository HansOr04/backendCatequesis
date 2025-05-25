"""
Schemas de parroquia para el sistema de catequesis.
Maneja validaciones para gestión de parroquias, sedes y estructuras administrativas.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date, time
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, Telefono, EnumField,
    register_schema, PositiveInteger, NonNegativeInteger,
    NonNegativeDecimal
)


@register_schema('parroquia_create')
class ParroquiaCreateSchema(BaseSchema):
    """Schema para creación de parroquias."""
    
    # Información básica
    nombre = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=200)
    )
    
    nombre_completo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    codigo_parroquia = TrimmedString(
        required=True,
        validate=[
            validate.Length(min=3, max=20),
            validate.Regexp(r'^[A-Z0-9\-]+$', error='Código debe contener solo letras mayúsculas, números y guiones')
        ]
    )
    
    # Información religiosa
    santo_patron = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    fecha_fundacion = fields.Date(allow_none=True)
    fecha_consagracion = fields.Date(allow_none=True)
    
    # Jerarquía eclesiástica
    diocesis = TrimmedString(required=True, validate=validate.Length(min=3, max=100))
    archidiocesis = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    vicaria = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    decanato = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Ubicación principal
    pais = TrimmedString(required=True, missing='Colombia')
    departamento = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    municipio = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    direccion_principal = TrimmedString(required=True, validate=validate.Length(min=10, max=300))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Coordenadas geográficas
    latitud = fields.Decimal(allow_none=True, places=6)
    longitud = fields.Decimal(allow_none=True, places=6)
    
    # Información de contacto
    telefono_principal = Telefono(required=True)
    telefono_alternativo = Telefono(allow_none=True)
    email_principal = Email(required=True)
    email_alternativo = Email(allow_none=True)
    sitio_web = fields.Url(allow_none=True)
    
    # Redes sociales
    facebook = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    instagram = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    youtube = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    twitter = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Información administrativa
    nit = TrimmedString(
        allow_none=True,
        validate=validate.Regexp(r'^\d{9}-\d$', error='NIT debe tener formato 123456789-0')
    )
    representante_legal = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Configuraciones
    capacidad_maxima = PositiveInteger(allow_none=True)
    numero_sedes = NonNegativeInteger(missing=1)
    tiene_columbario = fields.Boolean(missing=False)
    tiene_salon_social = fields.Boolean(missing=False)
    tiene_estacionamiento = fields.Boolean(missing=False)
    
    # Estado
    is_active = fields.Boolean(missing=True)
    acepta_inscripciones = fields.Boolean(missing=True)
    
    # Observaciones
    descripcion = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    @validates_schema
    def validate_parroquia(self, data, **kwargs):
        """Validaciones específicas de parroquia."""
        # Validar fechas
        fundacion = data.get('fecha_fundacion')
        consagracion = data.get('fecha_consagracion')
        
        if fundacion and fundacion > date.today():
            raise ValidationError({'fecha_fundacion': 'La fecha de fundación no puede ser futura'})
        
        if consagracion and consagracion > date.today():
            raise ValidationError({'fecha_consagracion': 'La fecha de consagración no puede ser futura'})
        
        if fundacion and consagracion and consagracion < fundacion:
            raise ValidationError({'fecha_consagracion': 'La consagración no puede ser anterior a la fundación'})
        
        # Validar coordenadas
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if latitud is not None and not (-90 <= float(latitud) <= 90):
            raise ValidationError({'latitud': 'La latitud debe estar entre -90 y 90'})
        
        if longitud is not None and not (-180 <= float(longitud) <= 180):
            raise ValidationError({'longitud': 'La longitud debe estar entre -180 y 180'})


@register_schema('parroquia_update')
class ParroquiaUpdateSchema(BaseSchema):
    """Schema para actualización de parroquias."""
    
    # Información básica (no se puede cambiar código)
    nombre = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=200))
    nombre_completo = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    santo_patron = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Jerarquía eclesiástica
    diocesis = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=100))
    archidiocesis = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    vicaria = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    decanato = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Ubicación
    departamento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    municipio = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    direccion_principal = TrimmedString(allow_none=True, validate=validate.Length(min=10, max=300))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Coordenadas
    latitud = fields.Decimal(allow_none=True, places=6)
    longitud = fields.Decimal(allow_none=True, places=6)
    
    # Contacto
    telefono_principal = Telefono(allow_none=True)
    telefono_alternativo = Telefono(allow_none=True)
    email_principal = Email(allow_none=True)
    email_alternativo = Email(allow_none=True)
    sitio_web = fields.Url(allow_none=True)
    
    # Redes sociales
    facebook = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    instagram = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    youtube = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    twitter = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Información administrativa
    representante_legal = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Configuraciones
    capacidad_maxima = PositiveInteger(allow_none=True)
    numero_sedes = NonNegativeInteger(allow_none=True)
    tiene_columbario = fields.Boolean(allow_none=True)
    tiene_salon_social = fields.Boolean(allow_none=True)
    tiene_estacionamiento = fields.Boolean(allow_none=True)
    
    # Estado
    acepta_inscripciones = fields.Boolean(allow_none=True)
    
    # Observaciones
    descripcion = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('parroquia_response')
class ParroquiaResponseSchema(BaseSchema):
    """Schema para respuesta de parroquia."""
    
    # Información básica
    id = PositiveInteger(required=True)
    nombre = TrimmedString(required=True)
    nombre_completo = TrimmedString(allow_none=True)
    codigo_parroquia = TrimmedString(required=True)
    
    # Información religiosa
    santo_patron = TrimmedString(allow_none=True)
    fecha_fundacion = fields.Date(allow_none=True)
    fecha_consagracion = fields.Date(allow_none=True)
    años_funcionamiento = PositiveInteger(dump_only=True, allow_none=True)
    
    # Jerarquía eclesiástica
    diocesis = TrimmedString(required=True)
    archidiocesis = TrimmedString(allow_none=True)
    vicaria = TrimmedString(allow_none=True)
    decanato = TrimmedString(allow_none=True)
    
    # Ubicación
    pais = TrimmedString(required=True)
    departamento = TrimmedString(required=True)
    municipio = TrimmedString(required=True)
    direccion_principal = TrimmedString(required=True)
    direccion_completa = TrimmedString(dump_only=True)
    codigo_postal = TrimmedString(allow_none=True)
    barrio = TrimmedString(allow_none=True)
    
    # Coordenadas
    latitud = fields.Decimal(allow_none=True, places=6)
    longitud = fields.Decimal(allow_none=True, places=6)
    
    # Contacto
    telefono_principal = TrimmedString(required=True)
    telefono_alternativo = TrimmedString(allow_none=True)
    email_principal = Email(required=True)
    email_alternativo = Email(allow_none=True)
    sitio_web = fields.Url(allow_none=True)
    
    # Redes sociales
    facebook = TrimmedString(allow_none=True)
    instagram = TrimmedString(allow_none=True)
    youtube = TrimmedString(allow_none=True)
    twitter = TrimmedString(allow_none=True)
    
    # Información administrativa
    nit = TrimmedString(allow_none=True)
    representante_legal = TrimmedString(allow_none=True)
    
    # Configuraciones
    capacidad_maxima = PositiveInteger(allow_none=True)
    numero_sedes = NonNegativeInteger(required=True)
    tiene_columbario = fields.Boolean(required=True)
    tiene_salon_social = fields.Boolean(required=True)
    tiene_estacionamiento = fields.Boolean(required=True)
    
    # Estado
    is_active = fields.Boolean(required=True)
    acepta_inscripciones = fields.Boolean(required=True)
    
    # Estadísticas
    total_catequizandos = NonNegativeInteger(dump_only=True)
    total_catequistas = NonNegativeInteger(dump_only=True)
    total_grupos = NonNegativeInteger(dump_only=True)
    total_programas = NonNegativeInteger(dump_only=True)
    
    # Descripción
    descripcion = TrimmedString(allow_none=True)
    observaciones = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('sede_parroquia')
class SedeParroquiaSchema(BaseSchema):
    """Schema para sedes de parroquia."""
    
    id = PositiveInteger(dump_only=True)
    parroquia_id = PositiveInteger(required=True)
    
    nombre = TrimmedString(required=True, validate=validate.Length(min=3, max=150))
    tipo_sede = TrimmedString(
        required=True,
        validate=validate.OneOf(['principal', 'capilla', 'salon_pastoral', 'centro_catequesis'])
    )
    
    # Ubicación
    direccion = TrimmedString(required=True, validate=validate.Length(min=10, max=300))
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    telefono = Telefono(allow_none=True)
    
    # Coordenadas
    latitud = fields.Decimal(allow_none=True, places=6)
    longitud = fields.Decimal(allow_none=True, places=6)
    
    # Capacidad y facilidades
    capacidad_personas = PositiveInteger(allow_none=True)
    numero_salones = NonNegativeInteger(missing=1)
    tiene_audiovisuales = fields.Boolean(missing=False)
    tiene_cocina = fields.Boolean(missing=False)
    tiene_baños = fields.Boolean(missing=True)
    accesible_discapacitados = fields.Boolean(missing=False)
    
    # Horarios
    horario_funcionamiento = fields.Dict(allow_none=True)
    
    # Estado
    is_active = fields.Boolean(missing=True)
    disponible_catequesis = fields.Boolean(missing=True)
    
    descripcion = TrimmedString(allow_none=True, validate=validate.Length(max=500))


@register_schema('horario_misa')
class HorarioMisaSchema(BaseSchema):
    """Schema para horarios de misa."""
    
    id = PositiveInteger(dump_only=True)
    parroquia_id = PositiveInteger(required=True)
    sede_id = PositiveInteger(allow_none=True)
    
    dia_semana = TrimmedString(
        required=True,
        validate=validate.OneOf(['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'])
    )
    
    hora = fields.Time(required=True)
    tipo_celebracion = TrimmedString(
        required=True,
        validate=validate.OneOf(['misa', 'adoracion', 'rosario', 'novena', 'via_crucis', 'especial'])
    )
    
    nombre_celebracion = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    celebrante = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Características especiales
    es_bilingue = fields.Boolean(missing=False)
    para_niños = fields.Boolean(missing=False)
    con_musica = fields.Boolean(missing=False)
    transmision_online = fields.Boolean(missing=False)
    
    # Temporalidad
    fecha_inicio = fields.Date(allow_none=True)
    fecha_fin = fields.Date(allow_none=True)
    es_temporal = fields.Boolean(missing=False)
    
    # Estado
    is_active = fields.Boolean(missing=True)
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=300))


@register_schema('personal_parroquia')
class PersonalParroquiaSchema(BaseSchema):
    """Schema para personal de la parroquia."""
    
    id = PositiveInteger(dump_only=True)
    parroquia_id = PositiveInteger(required=True)
    user_id = PositiveInteger(allow_none=True)
    
    # Información personal
    nombres = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    apellidos = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    documento_identidad = TrimmedString(required=True, validate=validate.Length(min=5, max=20))
    telefono = Telefono(required=True)
    email = Email(allow_none=True)
    
    # Información del cargo
    cargo = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'parroco', 'vicario', 'diacono', 'coordinador_catequesis',
            'catequista', 'secretaria', 'tesorero', 'sacristan',
            'coro', 'acolitomonaguillo', 'voluntario', 'otro'
        ])
    )
    
    cargo_descripcion = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    nivel_responsabilidad = TrimmedString(
        missing='basico',
        validate=validate.OneOf(['basico', 'intermedio', 'alto', 'directivo'])
    )
    
    # Fechas
    fecha_ingreso = fields.Date(required=True)
    fecha_salida = fields.Date(allow_none=True)
    
    # Estado
    is_active = fields.Boolean(missing=True)
    disponible_catequesis = fields.Boolean(missing=False)
    
    # Información adicional
    formacion_religiosa = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    experiencia_años = NonNegativeInteger(allow_none=True)
    especialidades = fields.List(fields.String(), missing=[])
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))


@register_schema('parroquia_search')
class ParroquiaSearchSchema(BaseSchema):
    """Schema para búsqueda de parroquias."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros geográficos
    pais = TrimmedString(allow_none=True)
    departamento = TrimmedString(allow_none=True)
    municipio = TrimmedString(allow_none=True)
    diocesis = TrimmedString(allow_none=True)
    
    # Filtros de estado
    is_active = fields.Boolean(allow_none=True)
    acepta_inscripciones = fields.Boolean(allow_none=True)
    
    # Filtros de capacidad
    capacidad_minima = PositiveInteger(allow_none=True)
    tiene_estacionamiento = fields.Boolean(allow_none=True)
    tiene_salon_social = fields.Boolean(allow_none=True)
    
    # Búsqueda por proximidad
    latitud_centro = fields.Decimal(allow_none=True, places=6)
    longitud_centro = fields.Decimal(allow_none=True, places=6)
    radio_km = PositiveInteger(allow_none=True, validate=validate.Range(min=1, max=100))
    
    # Paginación y ordenamiento
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='nombre',
        validate=validate.OneOf(['nombre', 'municipio', 'diocesis', 'fecha_fundacion', 'total_catequizandos'])
    )
    sort_order = TrimmedString(missing='asc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('parroquia_stats')
class ParroquiaStatsSchema(BaseSchema):
    """Schema para estadísticas de parroquias."""
    
    total_parroquias = NonNegativeInteger(required=True)
    parroquias_activas = NonNegativeInteger(required=True)
    parroquias_con_catequesis = NonNegativeInteger(required=True)
    
    # Por región
    por_departamento = fields.List(fields.Dict())
    por_diocesis = fields.List(fields.Dict())
    
    # Capacidades
    capacidad_total = NonNegativeInteger(required=True)
    capacidad_promedio = NonNegativeDecimal(required=True)
    
    # Catequesis
    total_catequizandos = NonNegativeInteger(required=True)
    total_catequistas = NonNegativeInteger(required=True)
    total_grupos = NonNegativeInteger(required=True)
    
    # Crecimiento
    nuevas_parroquias_año = NonNegativeInteger(required=True)
    crecimiento_catequizandos = fields.Decimal(allow_none=True)
    
    # Top parroquias
    mas_catequizandos = fields.List(fields.Nested(ParroquiaResponseSchema))
    mas_catequistas = fields.List(fields.Nested(ParroquiaResponseSchema))


@register_schema('parroquia_contact_info')
class ParroquiaContactInfoSchema(BaseSchema):
    """Schema simplificado para información de contacto."""
    
    id = PositiveInteger(required=True)
    nombre = TrimmedString(required=True)
    codigo_parroquia = TrimmedString(required=True)
    
    telefono_principal = TrimmedString(required=True)
    email_principal = Email(required=True)
    direccion_principal = TrimmedString(required=True)
    
    municipio = TrimmedString(required=True)
    departamento = TrimmedString(required=True)
    
    is_active = fields.Boolean(required=True)
    acepta_inscripciones = fields.Boolean(required=True)