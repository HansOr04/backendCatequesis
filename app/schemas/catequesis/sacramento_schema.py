"""
Schemas de sacramento para el sistema de catequesis.
Maneja validaciones para registro de sacramentos recibidos por catequizandos.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('sacramento_create')
class SacramentoCreateSchema(BaseSchema):
    """Schema para registro de sacramentos."""
    
    # Información básica
    catequizando_id = PositiveInteger(required=True)
    
    tipo_sacramento = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'bautismo', 'primera_comunion', 'confirmacion', 'matrimonio',
            'orden_sacerdotal', 'uncion_enfermos', 'penitencia'
        ])
    )
    
    # Fechas del sacramento
    fecha_sacramento = fields.Date(required=True)
    hora_sacramento = fields.Time(allow_none=True)
    
    # Lugar de celebración
    parroquia_sacramento = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=200)
    )
    
    ciudad_sacramento = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    departamento_sacramento = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    pais_sacramento = TrimmedString(
        required=True,
        missing='Colombia',
        validate=validate.Length(min=2, max=100)
    )
    
    # Información del celebrante
    celebrante_principal = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    cargo_celebrante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'parroco', 'vicario', 'sacerdote', 'diacono', 'obispo',
            'arzobispo', 'cardenal', 'papa', 'otro'
        ])
    )
    
    celebrantes_concelebrantes = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Padrinos/Testigos (según el sacramento)
    padrino_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    padrino_documento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    madrina_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    madrina_documento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    # Testigos (para matrimonio principalmente)
    testigo1_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    testigo1_documento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    testigo2_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    testigo2_documento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    # Información específica del sacramento
    numero_acta = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=50)
    )
    
    folio = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=20)
    )
    
    libro = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=20)
    )
    
    numero_partida = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=50)
    )
    
    # Información adicional específica por sacramento
    # Para bautismo
    edad_al_bautismo = NonNegativeInteger(allow_none=True)
    motivo_bautismo_tardio = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Para matrimonio
    tipo_matrimonio = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['religioso', 'civil_religioso', 'convalidacion'])
    )
    
    conyuge_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    conyuge_documento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    # Para confirmación
    nombre_confirmacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=2, max=100)
    )
    
    santo_patron_confirmacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=2, max=100)
    )
    
    # Preparación sacramental
    recibio_preparacion = fields.Boolean(missing=True)
    lugar_preparacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    duracion_preparacion_meses = NonNegativeInteger(allow_none=True)
    catequista_preparacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    # Documentos y certificaciones
    numero_certificado = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=50)
    )
    
    fecha_expedicion_certificado = fields.Date(allow_none=True)
    entidad_expide_certificado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Validaciones canónicas
    cumple_requisitos_canonicos = fields.Boolean(missing=True)
    dispensas_otorgadas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    observaciones_canonicas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    # Estado y verificación
    sacramento_valido = fields.Boolean(missing=True)
    verificado_por = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    fecha_verificacion = fields.Date(allow_none=True)
    
    # Observaciones generales
    observaciones_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_sacramento(self, data, **kwargs):
        """Validaciones específicas del sacramento."""
        tipo_sacramento = data.get('tipo_sacramento')
        fecha_sacramento = data.get('fecha_sacramento')
        
        # Validar fecha no sea futura
        if fecha_sacramento and fecha_sacramento > date.today():
            raise ValidationError({'fecha_sacramento': 'La fecha del sacramento no puede ser futura'})
        
        # Validaciones específicas por tipo de sacramento
        if tipo_sacramento == 'matrimonio':
            conyuge_nombre = data.get('conyuge_nombre')
            if not conyuge_nombre:
                raise ValidationError({'conyuge_nombre': 'El nombre del cónyuge es requerido para matrimonio'})
        
        if tipo_sacramento in ['bautismo', 'primera_comunion', 'confirmacion']:
            padrino = data.get('padrino_nombre')
            madrina = data.get('madrina_nombre')
            if not padrino and not madrina:
                raise ValidationError('Debe especificar al menos un padrino o madrina')
        
        if tipo_sacramento == 'confirmacion':
            nombre_confirmacion = data.get('nombre_confirmacion')
            if not nombre_confirmacion:
                raise ValidationError({'nombre_confirmacion': 'El nombre de confirmación es requerido'})


@register_schema('sacramento_update')
class SacramentoUpdateSchema(BaseSchema):
    """Schema para actualización de sacramentos."""
    
    # No se puede cambiar catequizando_id ni tipo_sacramento
    
    # Fechas
    fecha_sacramento = fields.Date(allow_none=True)
    hora_sacramento = fields.Time(allow_none=True)
    
    # Lugar
    parroquia_sacramento = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=200))
    ciudad_sacramento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    departamento_sacramento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    pais_sacramento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    
    # Celebrante
    celebrante_principal = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    cargo_celebrante = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'parroco', 'vicario', 'sacerdote', 'diacono', 'obispo',
            'arzobispo', 'cardenal', 'papa', 'otro'
        ])
    )
    celebrantes_concelebrantes = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Padrinos/Testigos
    padrino_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    padrino_documento = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    madrina_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    madrina_documento = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    
    testigo1_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    testigo1_documento = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    testigo2_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    testigo2_documento = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    
    # Registro
    numero_acta = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=50))
    folio = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=20))
    libro = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=20))
    numero_partida = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=50))
    
    # Información específica
    nombre_confirmacion = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    santo_patron_confirmacion = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    conyuge_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    conyuge_documento = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    
    # Preparación
    recibio_preparacion = fields.Boolean(allow_none=True)
    lugar_preparacion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    duracion_preparacion_meses = NonNegativeInteger(allow_none=True)
    catequista_preparacion = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    
    # Certificación
    numero_certificado = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=50))
    fecha_expedicion_certificado = fields.Date(allow_none=True)
    entidad_expide_certificado = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Validaciones
    cumple_requisitos_canonicos = fields.Boolean(allow_none=True)
    dispensas_otorgadas = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    observaciones_canonicas = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    # Verificación
    sacramento_valido = fields.Boolean(allow_none=True)
    verificado_por = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    fecha_verificacion = fields.Date(allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('sacramento_response')
class SacramentoResponseSchema(BaseSchema):
    """Schema para respuesta de sacramento."""
    
    # Información básica
    id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(required=True)
    catequizando_nombre = TrimmedString(dump_only=True, required=True)
    
    tipo_sacramento = TrimmedString(required=True)
    tipo_sacramento_display = TrimmedString(dump_only=True)
    
    # Fechas
    fecha_sacramento = fields.Date(required=True)
    hora_sacramento = fields.Time(allow_none=True)
    fecha_hora_display = TrimmedString(dump_only=True)
    
    # Lugar
    parroquia_sacramento = TrimmedString(required=True)
    ciudad_sacramento = TrimmedString(required=True)
    departamento_sacramento = TrimmedString(required=True)
    pais_sacramento = TrimmedString(required=True)
    lugar_completo = TrimmedString(dump_only=True)
    
    # Celebrante
    celebrante_principal = TrimmedString(required=True)
    cargo_celebrante = TrimmedString(required=True)
    cargo_celebrante_display = TrimmedString(dump_only=True)
    celebrantes_concelebrantes = TrimmedString(allow_none=True)
    
    # Padrinos y testigos
    padrino_nombre = TrimmedString(allow_none=True)
    padrino_documento = TrimmedString(allow_none=True)
    madrina_nombre = TrimmedString(allow_none=True)
    madrina_documento = TrimmedString(allow_none=True)
    padrinos_display = TrimmedString(dump_only=True, allow_none=True)
    
    testigo1_nombre = TrimmedString(allow_none=True)
    testigo1_documento = TrimmedString(allow_none=True)
    testigo2_nombre = TrimmedString(allow_none=True)
    testigo2_documento = TrimmedString(allow_none=True)
    testigos_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Registro parroquial
    numero_acta = TrimmedString(allow_none=True)
    folio = TrimmedString(allow_none=True)
    libro = TrimmedString(allow_none=True)
    numero_partida = TrimmedString(allow_none=True)
    referencia_registro = TrimmedString(dump_only=True, allow_none=True)
    
    # Información específica
    edad_al_bautismo = NonNegativeInteger(allow_none=True)
    motivo_bautismo_tardio = TrimmedString(allow_none=True)
    tipo_matrimonio = TrimmedString(allow_none=True)
    conyuge_nombre = TrimmedString(allow_none=True)
    conyuge_documento = TrimmedString(allow_none=True)
    nombre_confirmacion = TrimmedString(allow_none=True)
    santo_patron_confirmacion = TrimmedString(allow_none=True)
    
    # Preparación sacramental
    recibio_preparacion = fields.Boolean(required=True)
    lugar_preparacion = TrimmedString(allow_none=True)
    duracion_preparacion_meses = NonNegativeInteger(allow_none=True)
    catequista_preparacion = TrimmedString(allow_none=True)
    
    # Certificación
    numero_certificado = TrimmedString(allow_none=True)
    fecha_expedicion_certificado = fields.Date(allow_none=True)
    entidad_expide_certificado = TrimmedString(allow_none=True)
    tiene_certificado = fields.Boolean(dump_only=True)
    
    # Validez canónica
    cumple_requisitos_canonicos = fields.Boolean(required=True)
    dispensas_otorgadas = TrimmedString(allow_none=True)
    observaciones_canonicas = TrimmedString(allow_none=True)
    sacramento_valido = fields.Boolean(required=True)
    
    # Verificación
    verificado_por = TrimmedString(allow_none=True)
    fecha_verificacion = fields.Date(allow_none=True)
    esta_verificado = fields.Boolean(dump_only=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('sacramento_search')
class SacramentoSearchSchema(BaseSchema):
    """Schema para búsqueda de sacramentos."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    catequizando_id = PositiveInteger(allow_none=True)
    tipo_sacramento = TrimmedString(allow_none=True)
    
    # Filtros de fecha
    fecha_desde = fields.Date(allow_none=True)
    fecha_hasta = fields.Date(allow_none=True)
    año_sacramento = PositiveInteger(allow_none=True)
    
    # Filtros de lugar
    parroquia_sacramento = TrimmedString(allow_none=True)
    ciudad_sacramento = TrimmedString(allow_none=True)
    departamento_sacramento = TrimmedString(allow_none=True)
    
    # Filtros de celebrante
    celebrante_principal = TrimmedString(allow_none=True)
    cargo_celebrante = TrimmedString(allow_none=True)
    
    # Filtros de padrinos
    padrino_nombre = TrimmedString(allow_none=True)
    madrina_nombre = TrimmedString(allow_none=True)
    
    # Filtros de validez
    sacramento_valido = fields.Boolean(allow_none=True)
    esta_verificado = fields.Boolean(allow_none=True)
    cumple_requisitos_canonicos = fields.Boolean(allow_none=True)
    
    # Filtros de certificación
    tiene_certificado = fields.Boolean(allow_none=True)
    numero_certificado = TrimmedString(allow_none=True)
    
    # Filtros de preparación
    recibio_preparacion = fields.Boolean(allow_none=True)
    lugar_preparacion = TrimmedString(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_sacramento',
        validate=validate.OneOf([
            'fecha_sacramento', 'tipo_sacramento', 'catequizando_nombre',
            'parroquia_sacramento', 'created_at'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('sacramento_stats')
class SacramentoStatsSchema(BaseSchema):
    """Schema para estadísticas de sacramentos."""
    
    total_sacramentos = NonNegativeInteger(required=True)
    sacramentos_este_año = NonNegativeInteger(required=True)
    sacramentos_este_mes = NonNegativeInteger(required=True)
    
    # Por tipo de sacramento
    por_tipo_sacramento = fields.Dict(required=True)
    
    # Tendencias mensuales
    por_mes_año_actual = fields.List(fields.Dict())
    por_año = fields.List(fields.Dict())
    
    # Por lugar
    por_parroquia = fields.List(fields.Dict())
    por_ciudad = fields.List(fields.Dict())
    por_departamento = fields.List(fields.Dict())
    
    # Por celebrante
    por_celebrante = fields.List(fields.Dict())
    por_cargo_celebrante = fields.Dict(required=True)
    
    # Validez y verificación
    sacramentos_validos = NonNegativeInteger(required=True)
    sacramentos_verificados = NonNegativeInteger(required=True)
    con_dispensas = NonNegativeInteger(required=True)
    
    # Preparación
    con_preparacion = NonNegativeInteger(required=True)
    sin_preparacion = NonNegativeInteger(required=True)
    duracion_promedio_preparacion = NonNegativeDecimal(required=True, places=1)
    
    # Certificación
    con_certificado = NonNegativeInteger(required=True)
    sin_certificado = NonNegativeInteger(required=True)
    
    # Edades (para bautismo principalmente)
    edad_promedio_bautismo = NonNegativeDecimal(allow_none=True, places=1)
    bautismos_adultos = NonNegativeInteger(required=True)
    bautismos_infantes = NonNegativeInteger(required=True)


@register_schema('verificacion_sacramento')
class VerificacionSacramentoSchema(BaseSchema):
    """Schema para verificación de sacramentos."""
    
    sacramento_id = PositiveInteger(required=True)
    verificado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    fecha_verificacion = fields.Date(required=True, missing=date.today)
    
    resultado_verificacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['verificado', 'rechazado', 'pendiente_documentos'])
    )
    
    observaciones_verificacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    documentos_solicitados = fields.List(
        fields.String(validate=validate.OneOf([
            'acta_bautismo', 'acta_matrimonio', 'certificado_confirmacion',
            'carta_parroco', 'documento_identidad', 'acta_defuncion',
            'dispensa_canonical', 'otro'
        ])),
        missing=[]
    )
    
    @validates_schema
    def validate_verificacion(self, data, **kwargs):
        """Validaciones específicas de verificación."""
        resultado = data.get('resultado_verificacion')
        observaciones = data.get('observaciones_verificacion')
        documentos = data.get('documentos_solicitados', [])
        
        if resultado == 'rechazado' and not observaciones:
            raise ValidationError({'observaciones_verificacion': 'Debe especificar motivo del rechazo'})
        
        if resultado == 'pendiente_documentos' and not documentos:
            raise ValidationError({'documentos_solicitados': 'Debe especificar documentos pendientes'})


@register_schema('constancia_sacramento')
class ConstanciaSacramentoSchema(BaseSchema):
    """Schema para emisión de constancias de sacramento."""
    
    sacramento_id = PositiveInteger(required=True)
    tipo_constancia = TrimmedString(
        required=True,
        validate=validate.OneOf(['constancia', 'certificado', 'copia_acta'])
    )
    
    solicitado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_solicitante = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=20)
    )
    
    parentesco_solicitante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'titular', 'padre', 'madre', 'conyuge', 'hijo', 'hermano',
            'abuelo', 'nieto', 'representante_legal', 'otro'
        ])
    )
    
    motivo_solicitud = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'tramite_matrimonio', 'tramite_confirmacion', 'tramite_laboral',
            'tramite_educativo', 'tramite_migratorio', 'archivo_personal',
            'tramite_legal', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    fecha_solicitud = fields.Date(required=True, missing=date.today)
    fecha_entrega = fields.Date(allow_none=True)
    
    costo_constancia = NonNegativeDecimal(missing=0, places=2)
    
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )