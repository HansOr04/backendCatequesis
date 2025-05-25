"""
Schemas de padrino para el sistema de catequesis.
Maneja validaciones para padrinos, madrinas y testigos de sacramentos.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, DocumentoIdentidad, Telefono,
    FechaNacimiento, register_schema, PositiveInteger, NonNegativeInteger
)


@register_schema('padrino_create')
class PadrinoCreateSchema(BaseSchema):
    """Schema para creación de padrinos."""
    
    # Información personal básica
    nombres = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    apellidos = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    documento_identidad = DocumentoIdentidad(required=True)
    tipo_documento = TrimmedString(
        required=True,
        validate=validate.OneOf(['CC', 'CE', 'PA'])
    )
    
    fecha_nacimiento = FechaNacimiento(required=True)
    lugar_nacimiento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=3, max=150)
    )
    
    genero = TrimmedString(
        required=True,
        validate=validate.OneOf(['M', 'F'])
    )
    
    # Información de contacto
    telefono_principal = Telefono(required=True)
    telefono_alternativo = Telefono(allow_none=True)
    email = Email(allow_none=True)
    
    # Dirección
    direccion_residencia = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=300)
    )
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    municipio = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    departamento = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Estado civil y familiar
    estado_civil = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'soltero', 'casado_iglesia', 'casado_civil', 'union_libre',
            'separado', 'divorciado', 'viudo'
        ])
    )
    
    # Información del cónyuge (si aplica)
    nombre_conyuge = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    casado_por_iglesia = fields.Boolean(allow_none=True)
    fecha_matrimonio_iglesia = fields.Date(allow_none=True)
    parroquia_matrimonio = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Información religiosa (requisitos para ser padrino/madrina)
    es_catolico_bautizado = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe ser católico bautizado para ser padrino/madrina')
    )
    
    lugar_bautismo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    fecha_bautismo = fields.Date(allow_none=True)
    
    recibio_confirmacion = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe estar confirmado para ser padrino/madrina')
    )
    
    lugar_confirmacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    fecha_confirmacion = fields.Date(allow_none=True)
    
    recibio_primera_comunion = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe haber recibido la primera comunión')
    )
    
    lugar_primera_comunion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    fecha_primera_comunion = fields.Date(allow_none=True)
    
    # Vida religiosa activa
    practica_religion_activamente = fields.Boolean(missing=True)
    parroquia_donde_practica = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    frecuencia_misa = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'diaria', 'semanal', 'quincenal', 'mensual', 'ocasional', 'rara_vez'
        ])
    )
    
    participa_ministerios = fields.Boolean(missing=False)
    ministerios_participa = fields.List(
        fields.String(validate=validate.OneOf([
            'catequesis', 'coro', 'lector', 'ministro_extraordinario',
            'acolitado', 'pastoral_social', 'pastoral_juvenil',
            'pastoral_familiar', 'otro'
        ])),
        missing=[]
    )
    
    # Información laboral/profesional
    ocupacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    nivel_educativo = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'primaria_incompleta', 'primaria_completa',
            'secundaria_incompleta', 'secundaria_completa',
            'tecnico', 'tecnologo', 'universitario_incompleto',
            'universitario_completo', 'posgrado'
        ])
    )
    
    # Relación con el ahijado/a
    parentesco_ahijado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'tio', 'tia', 'abuelo', 'abuela', 'primo', 'prima',
            'hermano', 'hermana', 'cuñado', 'cuñada', 'amigo_familia',
            'conocido', 'ninguno', 'otro'
        ])
    )
    
    como_conocio_familia = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    tiempo_conoce_familia = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'menos_1_año', '1_2_años', '2_5_años', '5_10_años', 'mas_10_años'
        ])
    )
    
    # Compromiso y motivación
    motivo_aceptar_padrinazgo = TrimmedString(
        required=True,
        validate=validate.Length(min=20, max=1000)
    )
    
    comprende_responsabilidades = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe comprender las responsabilidades del padrinazgo')
    )
    
    compromete_acompañamiento = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe comprometerse al acompañamiento espiritual')
    )
    
    # Referencias
    referencia_parroco = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    referencia_personal = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Documentación
    presenta_certificado_bautismo = fields.Boolean(missing=False)
    presenta_certificado_confirmacion = fields.Boolean(missing=False)
    presenta_certificado_matrimonio = fields.Boolean(allow_none=True)
    presenta_carta_parroco = fields.Boolean(missing=False)
    
    # Observaciones
    observaciones_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_padrino(self, data, **kwargs):
        """Validaciones específicas del padrino."""
        # Validar edad mínima (debe ser mayor de edad)
        fecha_nac = data.get('fecha_nacimiento')
        if fecha_nac:
            edad = (date.today() - fecha_nac).days / 365.25
            if edad < 16:
                raise ValidationError({'fecha_nacimiento': 'Debe ser mayor de 16 años para ser padrino/madrina'})
        
        # Validar información matrimonial
        estado_civil = data.get('estado_civil')
        casado_iglesia = data.get('casado_por_iglesia')
        nombre_conyuge = data.get('nombre_conyuge')
        
        if estado_civil in ['casado_iglesia', 'casado_civil', 'union_libre']:
            if not nombre_conyuge:
                raise ValidationError({'nombre_conyuge': 'Debe especificar el nombre del cónyuge'})
            
            if estado_civil == 'casado_iglesia' and not casado_iglesia:
                data['casado_por_iglesia'] = True
        
        # Validar fechas sacramentales
        fecha_bautismo = data.get('fecha_bautismo')
        fecha_comunion = data.get('fecha_primera_comunion')
        fecha_confirmacion = data.get('fecha_confirmacion')
        
        if fecha_bautismo and fecha_nac and fecha_bautismo < fecha_nac:
            raise ValidationError({'fecha_bautismo': 'La fecha de bautismo no puede ser anterior al nacimiento'})
        
        if fecha_comunion and fecha_bautismo and fecha_comunion < fecha_bautismo:
            raise ValidationError({'fecha_primera_comunion': 'La primera comunión debe ser posterior al bautismo'})
        
        if fecha_confirmacion and fecha_comunion and fecha_confirmacion < fecha_comunion:
            raise ValidationError({'fecha_confirmacion': 'La confirmación debe ser posterior a la primera comunión'})


@register_schema('padrino_update')
class PadrinoUpdateSchema(BaseSchema):
    """Schema para actualización de padrinos."""
    
    # Información personal (documento no se puede cambiar)
    nombres = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    apellidos = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    lugar_nacimiento = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=150))
    
    # Contacto
    telefono_principal = Telefono(allow_none=True)
    telefono_alternativo = Telefono(allow_none=True)
    email = Email(allow_none=True)
    
    # Dirección
    direccion_residencia = TrimmedString(allow_none=True, validate=validate.Length(min=10, max=300))
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    municipio = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    departamento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Estado civil
    estado_civil = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'soltero', 'casado_iglesia', 'casado_civil', 'union_libre',
            'separado', 'divorciado', 'viudo'
        ])
    )
    nombre_conyuge = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    
    # Información religiosa
    lugar_bautismo = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    lugar_confirmacion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    lugar_primera_comunion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Vida religiosa
    practica_religion_activamente = fields.Boolean(allow_none=True)
    parroquia_donde_practica = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    frecuencia_misa = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'diaria', 'semanal', 'quincenal', 'mensual', 'ocasional', 'rara_vez'
        ])
    )
    participa_ministerios = fields.Boolean(allow_none=True)
    ministerios_participa = fields.List(fields.String(), allow_none=True)
    
    # Información laboral
    ocupacion = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    nivel_educativo = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'primaria_incompleta', 'primaria_completa',
            'secundaria_incompleta', 'secundaria_completa',
            'tecnico', 'tecnologo', 'universitario_incompleto',
            'universitario_completo', 'posgrado'
        ])
    )
    
    # Referencias
    referencia_parroco = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    referencia_personal = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Documentación
    presenta_certificado_bautismo = fields.Boolean(allow_none=True)
    presenta_certificado_confirmacion = fields.Boolean(allow_none=True)
    presenta_certificado_matrimonio = fields.Boolean(allow_none=True)
    presenta_carta_parroco = fields.Boolean(allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('padrino_response')
class PadrinoResponseSchema(BaseSchema):
    """Schema para respuesta de padrino."""
    
    # Información básica
    id = PositiveInteger(required=True)
    nombres = TrimmedString(required=True)
    apellidos = TrimmedString(required=True)
    nombre_completo = TrimmedString(dump_only=True)
    documento_identidad = TrimmedString(required=True)
    tipo_documento = TrimmedString(required=True)
    fecha_nacimiento = fields.Date(required=True)
    edad = PositiveInteger(dump_only=True)
    lugar_nacimiento = TrimmedString(allow_none=True)
    genero = TrimmedString(required=True)
    
    # Contacto
    telefono_principal = TrimmedString(required=True)
    telefono_alternativo = TrimmedString(allow_none=True)
    email = Email(allow_none=True)
    
    # Dirección
    direccion_residencia = TrimmedString(required=True)
    direccion_completa = TrimmedString(dump_only=True)
    barrio = TrimmedString(allow_none=True)
    municipio = TrimmedString(required=True)
    departamento = TrimmedString(required=True)
    codigo_postal = TrimmedString(allow_none=True)
    
    # Estado civil
    estado_civil = TrimmedString(required=True)
    estado_civil_display = TrimmedString(dump_only=True)
    nombre_conyuge = TrimmedString(allow_none=True)
    casado_por_iglesia = fields.Boolean(allow_none=True)
    fecha_matrimonio_iglesia = fields.Date(allow_none=True)
    parroquia_matrimonio = TrimmedString(allow_none=True)
    
    # Información religiosa
    es_catolico_bautizado = fields.Boolean(required=True)
    lugar_bautismo = TrimmedString(allow_none=True)
    fecha_bautismo = fields.Date(allow_none=True)
    
    recibio_confirmacion = fields.Boolean(required=True)
    lugar_confirmacion = TrimmedString(allow_none=True)
    fecha_confirmacion = fields.Date(allow_none=True)
    
    recibio_primera_comunion = fields.Boolean(required=True)
    lugar_primera_comunion = TrimmedString(allow_none=True)
    fecha_primera_comunion = fields.Date(allow_none=True)
    
    # Vida religiosa activa
    practica_religion_activamente = fields.Boolean(required=True)
    parroquia_donde_practica = TrimmedString(allow_none=True)
    frecuencia_misa = TrimmedString(allow_none=True)
    participa_ministerios = fields.Boolean(required=True)
    ministerios_participa = fields.List(fields.String(), missing=[])
    ministerios_display = fields.List(fields.String(), dump_only=True)
    
    # Información laboral
    ocupacion = TrimmedString(allow_none=True)
    nivel_educativo = TrimmedString(allow_none=True)
    nivel_educativo_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Compromiso y motivación
    motivo_aceptar_padrinazgo = TrimmedString(required=True)
    comprende_responsabilidades = fields.Boolean(required=True)
    compromete_acompañamiento = fields.Boolean(required=True)
    
    # Referencias
    referencia_parroco = TrimmedString(allow_none=True)
    referencia_personal = TrimmedString(allow_none=True)
    
    # Documentación
    presenta_certificado_bautismo = fields.Boolean(required=True)
    presenta_certificado_confirmacion = fields.Boolean(required=True)
    presenta_certificado_matrimonio = fields.Boolean(allow_none=True)
    presenta_carta_parroco = fields.Boolean(required=True)
    documentacion_completa = fields.Boolean(dump_only=True)
    
    # Estadísticas
    total_ahijados = NonNegativeInteger(dump_only=True)
    ahijados_activos = NonNegativeInteger(dump_only=True)
    años_como_padrino = NonNegativeInteger(dump_only=True, allow_none=True)
    
    # Estado
    is_active = fields.Boolean(required=True)
    apto_padrinazgo = fields.Boolean(dump_only=True)
    observaciones_aptitud = TrimmedString(dump_only=True, allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True)
    
    # Fechas
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('asignacion_padrino')
class AsignacionPadrinoSchema(BaseSchema):
    """Schema para asignación de padrino a catequizando."""
    
    id = PositiveInteger(dump_only=True)
    catequizando_id = PositiveInteger(required=True)
    padrino_id = PositiveInteger(allow_none=True)
    madrina_id = PositiveInteger(allow_none=True)
    
    # Tipo de padrinazgo
    tipo_padrinazgo = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'bautismo', 'primera_comunion', 'confirmacion', 'matrimonio'
        ])
    )
    
    # Fechas
    fecha_asignacion = fields.Date(required=True, missing=date.today)
    fecha_sacramento = fields.Date(allow_none=True)
    
    # Estado de la asignación
    estado_asignacion = TrimmedString(
        required=True,
        missing='asignado',
        validate=validate.OneOf(['propuesto', 'asignado', 'confirmado', 'realizado', 'cancelado'])
    )
    
    # Aprobaciones
    aprobado_por_parroco = fields.Boolean(missing=False)
    fecha_aprobacion_parroco = fields.Date(allow_none=True)
    parroco_aprobador = TrimmedString(allow_none=True)
    
    aprobado_por_familia = fields.Boolean(missing=False)
    fecha_aprobacion_familia = fields.Date(allow_none=True)
    
    # Preparación
    asistio_charla_padrinos = fields.Boolean(missing=False)
    fecha_charla_padrinos = fields.Date(allow_none=True)
    certificado_charla = fields.Boolean(missing=False)
    
    # Observaciones
    observaciones_asignacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    motivo_cancelacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    @validates_schema
    def validate_asignacion(self, data, **kwargs):
        """Validaciones específicas de asignación."""
        padrino_id = data.get('padrino_id')
        madrina_id = data.get('madrina_id')
        
        # Debe tener al menos un padrino o madrina
        if not padrino_id and not madrina_id:
            raise ValidationError('Debe asignar al menos un padrino o madrina')
        
        # No puede ser la misma persona como padrino y madrina
        if padrino_id and madrina_id and padrino_id == madrina_id:
            raise ValidationError('El padrino y la madrina deben ser personas diferentes')
        
        # Validar fechas
        fecha_asignacion = data.get('fecha_asignacion')
        fecha_sacramento = data.get('fecha_sacramento')
        
        if fecha_sacramento and fecha_asignacion and fecha_sacramento < fecha_asignacion:
            raise ValidationError({'fecha_sacramento': 'La fecha del sacramento debe ser posterior a la asignación'})


@register_schema('padrino_search')
class PadrinoSearchSchema(BaseSchema):
    """Schema para búsqueda de padrinos."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    documento_identidad = TrimmedString(allow_none=True)
    genero = TrimmedString(allow_none=True, validate=validate.OneOf(['M', 'F']))
    is_active = fields.Boolean(allow_none=True)
    
    # Filtros de estado civil
    estado_civil = TrimmedString(allow_none=True)
    casado_por_iglesia = fields.Boolean(allow_none=True)
    
    # Filtros religiosos
    practica_religion_activamente = fields.Boolean(allow_none=True)
    participa_ministerios = fields.Boolean(allow_none=True)
    frecuencia_misa = TrimmedString(allow_none=True)
    
    # Filtros geográficos
    municipio = TrimmedString(allow_none=True)
    departamento = TrimmedString(allow_none=True)
    
    # Filtros de edad
    edad_minima = PositiveInteger(allow_none=True)
    edad_maxima = PositiveInteger(allow_none=True)
    
    # Filtros de documentación
    documentacion_completa = fields.Boolean(allow_none=True)
    presenta_carta_parroco = fields.Boolean(allow_none=True)
    
    # Filtros de experiencia
    tiene_ahijados = fields.Boolean(allow_none=True)
    ahijados_activos = fields.Boolean(allow_none=True)
    
    # Disponibilidad
    disponible_padrinazgo = fields.Boolean(allow_none=True)
    tipo_padrinazgo_disponible = TrimmedString(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='nombre_completo',
        validate=validate.OneOf([
            'nombre_completo', 'documento_identidad', 'edad',
            'municipio', 'total_ahijados', 'created_at'
        ])
    )
    sort_order = TrimmedString(missing='asc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('padrino_stats')
class PadrinoStatsSchema(BaseSchema):
    """Schema para estadísticas de padrinos."""
    
    total_padrinos = NonNegativeInteger(required=True)
    padrinos_activos = NonNegativeInteger(required=True)
    madrinas_activas = NonNegativeInteger(required=True)
    nuevos_este_año = NonNegativeInteger(required=True)
    
    # Por género
    por_genero = fields.Dict(required=True)
    
    # Por estado civil
    por_estado_civil = fields.Dict(required=True)
    casados_por_iglesia = NonNegativeInteger(required=True)
    
    # Por edad
    por_rango_edad = fields.List(fields.Dict())
    edad_promedio = NonNegativeDecimal(required=True, places=1)
    
    # Vida religiosa
    practican_activamente = NonNegativeInteger(required=True)
    participan_ministerios = NonNegativeInteger(required=True)
    por_frecuencia_misa = fields.Dict(required=True)
    
    # Geográfico
    por_municipio = fields.List(fields.Dict())
    por_departamento = fields.List(fields.Dict())
    
    # Experiencia
    promedio_ahijados = NonNegativeDecimal(required=True, places=1)
    con_ahijados_activos = NonNegativeInteger(required=True)
    años_promedio_experiencia = NonNegativeDecimal(required=True, places=1)
    
    # Documentación
    documentacion_completa = NonNegativeInteger(required=True)
    necesitan_actualizar_documentos = NonNegativeInteger(required=True)
    
    # Por tipo de padrinazgo
    por_tipo_padrinazgo = fields.List(fields.Dict())
    
    # Top padrinos
    mas_ahijados = fields.List(fields.Nested(PadrinoResponseSchema))
    mas_experiencia = fields.List(fields.Nested(PadrinoResponseSchema))