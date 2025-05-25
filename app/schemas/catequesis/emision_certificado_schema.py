"""
Schemas de emisión de certificados para el sistema de catequesis.
Maneja validaciones para certificados, diplomas y constancias oficiales.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('certificado_create')
class CertificadoCreateSchema(BaseSchema):
    """Schema para creación de certificados."""
    
    # Referencias principales
    catequizando_id = PositiveInteger(required=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    programa_id = PositiveInteger(allow_none=True)
    
    # Tipo de certificado
    tipo_certificado = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'bautismo', 'primera_comunion', 'confirmacion', 'matrimonio',
            'asistencia', 'participacion', 'aprovechamiento', 'merito',
            'constancia', 'diploma', 'reconocimiento', 'otro'
        ])
    )
    
    subtipo_certificado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    # Información del beneficiario
    nombres_beneficiario = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    apellidos_beneficiario = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    documento_beneficiario = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=20)
    )
    
    fecha_nacimiento = fields.Date(allow_none=True)
    lugar_nacimiento = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Información de los padres (para certificados sacramentales)
    nombre_padre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=2, max=150)
    )
    
    nombre_madre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=2, max=150)
    )
    
    nombres_padrinos = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=2, max=300)
    )
    
    # Información del sacramento/evento
    fecha_evento = fields.Date(required=True)
    lugar_evento = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    
    parroquia = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    diocesis = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    celebrante_principal = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=3, max=150)
    )
    
    # Información del programa/curso
    programa_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    nivel_completado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    año_completion = PositiveInteger(
        required=True,
        missing=datetime.now().year
    )
    
    periodo_academico = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    duracion_programa = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    calificacion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'excelente', 'muy_bueno', 'bueno', 'regular', 'aprobado', 'sobresaliente'
        ])
    )
    
    calificacion_numerica = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=10)
    )
    
    observaciones_calificacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Control de registro
    numero_registro = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    tomo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    
    folio = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    
    partida = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    
    libro_registro = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    # Formato y diseño
    formato_certificado = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'fisico', 'digital_firmado'])
    )
    
    template_certificado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    orientacion = TrimmedString(
        missing='vertical',
        validate=validate.OneOf(['vertical', 'horizontal'])
    )
    
    tamaño_papel = TrimmedString(
        missing='carta',
        validate=validate.OneOf(['carta', 'oficio', 'a4', 'legal'])
    )
    
    # Autoridades firmantes
    firmante_principal = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=3, max=150)
    )
    
    cargo_firmante_principal = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    firmante_secundario = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=3, max=150)
    )
    
    cargo_firmante_secundario = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    # Validaciones y autenticidad
    incluir_codigo_verificacion = fields.Boolean(missing=True)
    incluir_qr_code = fields.Boolean(missing=True)
    incluir_sello_oficial = fields.Boolean(missing=True)
    
    # Fechas
    fecha_emision = fields.Date(required=True, missing=date.today)
    fecha_vencimiento = fields.Date(allow_none=True)
    
    # Estado inicial
    estado = TrimmedString(
        required=True,
        missing='borrador',
        validate=validate.OneOf(['borrador', 'generado', 'firmado', 'entregado', 'anulado'])
    )
    
    # Observaciones y notas
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    notas_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_certificado(self, data, **kwargs):
        """Validaciones específicas del certificado."""
        # Validar fechas
        fecha_evento = data.get('fecha_evento')
        fecha_emision = data.get('fecha_emision')
        fecha_nacimiento = data.get('fecha_nacimiento')
        
        if fecha_evento and fecha_emision and fecha_evento > fecha_emision:
            raise ValidationError({'fecha_evento': 'La fecha del evento no puede ser posterior a la emisión'})
        
        if fecha_nacimiento and fecha_evento and fecha_nacimiento > fecha_evento:
            raise ValidationError({'fecha_evento': 'La fecha del evento no puede ser anterior al nacimiento'})
        
        # Validar información requerida según tipo
        tipo = data.get('tipo_certificado')
        
        if tipo in ['bautismo', 'primera_comunion', 'confirmacion']:
            if not data.get('nombre_padre') and not data.get('nombre_madre'):
                raise ValidationError({'padres': 'Se requiere al menos el nombre de un padre'})
        
        if tipo == 'matrimonio':
            if not data.get('nombres_padrinos'):
                raise ValidationError({'nombres_padrinos': 'Se requieren testigos para certificado de matrimonio'})
        
        # Validar información de registro para certificados sacramentales
        if tipo in ['bautismo', 'primera_comunion', 'confirmacion', 'matrimonio']:
            if not any([data.get('numero_registro'), data.get('libro_registro')]):
                raise ValidationError({'registro': 'Se requiere información de registro para certificados sacramentales'})
        
        # Validar calificaciones para certificados académicos
        if tipo in ['aprovechamiento', 'merito', 'diploma']:
            if not data.get('calificacion') and not data.get('calificacion_numerica'):
                raise ValidationError({'calificacion': 'Se requiere calificación para certificados académicos'})


@register_schema('certificado_update')
class CertificadoUpdateSchema(BaseSchema):
    """Schema para actualización de certificados."""
    
    # No se pueden cambiar datos principales del beneficiario ni del evento
    
    # Información adicional
    lugar_nacimiento = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    nombres_padrinos = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=300))
    
    # Programa
    observaciones_calificacion = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Registro
    numero_registro = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    tomo = TrimmedString(allow_none=True, validate=validate.Length(max=20))
    folio = TrimmedString(allow_none=True, validate=validate.Length(max=20))
    partida = TrimmedString(allow_none=True, validate=validate.Length(max=20))
    libro_registro = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    
    # Formato
    template_certificado = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    orientacion = TrimmedString(allow_none=True, validate=validate.OneOf(['vertical', 'horizontal']))
    tamaño_papel = TrimmedString(allow_none=True, validate=validate.OneOf(['carta', 'oficio', 'a4', 'legal']))
    
    # Firmantes
    firmante_principal = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=150))
    cargo_firmante_principal = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    firmante_secundario = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=150))
    cargo_firmante_secundario = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Configuraciones
    incluir_codigo_verificacion = fields.Boolean(allow_none=True)
    incluir_qr_code = fields.Boolean(allow_none=True)
    incluir_sello_oficial = fields.Boolean(allow_none=True)
    
    # Fechas
    fecha_vencimiento = fields.Date(allow_none=True)
    
    # Estado
    estado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['borrador', 'generado', 'firmado', 'entregado', 'anulado'])
    )
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    notas_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=500))


@register_schema('certificado_response')
class CertificadoResponseSchema(BaseSchema):
    """Schema para respuesta de certificado."""
    
    # Información básica
    id = PositiveInteger(required=True)
    numero_certificado = TrimmedString(allow_none=True)
    codigo_verificacion = TrimmedString(allow_none=True)
    
    # Referencias
    catequizando_id = PositiveInteger(required=True)
    catequizando_nombre_completo = TrimmedString(dump_only=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    programa_id = PositiveInteger(allow_none=True)
    programa_nombre = TrimmedString(allow_none=True)
    
    # Tipo
    tipo_certificado = TrimmedString(required=True)
    tipo_certificado_display = TrimmedString(dump_only=True)
    subtipo_certificado = TrimmedString(allow_none=True)
    
    # Beneficiario
    nombres_beneficiario = TrimmedString(required=True)
    apellidos_beneficiario = TrimmedString(required=True)
    nombre_completo_beneficiario = TrimmedString(dump_only=True)
    documento_beneficiario = TrimmedString(required=True)
    fecha_nacimiento = fields.Date(allow_none=True)
    lugar_nacimiento = TrimmedString(allow_none=True)
    edad_evento = PositiveInteger(dump_only=True, allow_none=True)
    
    # Padres y padrinos
    nombre_padre = TrimmedString(allow_none=True)
    nombre_madre = TrimmedString(allow_none=True)
    nombres_padrinos = TrimmedString(allow_none=True)
    
    # Evento/Sacramento
    fecha_evento = fields.Date(required=True)
    lugar_evento = TrimmedString(required=True)
    parroquia = TrimmedString(allow_none=True)
    diocesis = TrimmedString(allow_none=True)
    celebrante_principal = TrimmedString(allow_none=True)
    
    # Programa académico
    nivel_completado = TrimmedString(allow_none=True)
    año_completion = PositiveInteger(required=True)
    periodo_academico = TrimmedString(allow_none=True)
    duracion_programa = TrimmedString(allow_none=True)
    
    # Calificaciones
    calificacion = TrimmedString(allow_none=True)
    calificacion_display = TrimmedString(dump_only=True, allow_none=True)
    calificacion_numerica = NonNegativeDecimal(allow_none=True, places=1)
    observaciones_calificacion = TrimmedString(allow_none=True)
    
    # Registro
    numero_registro = TrimmedString(allow_none=True)
    tomo = TrimmedString(allow_none=True)
    folio = TrimmedString(allow_none=True)
    partida = TrimmedString(allow_none=True)
    libro_registro = TrimmedString(allow_none=True)
    referencia_completa = TrimmedString(dump_only=True, allow_none=True)
    
    # Formato
    formato_certificado = TrimmedString(required=True)
    formato_display = TrimmedString(dump_only=True)
    template_certificado = TrimmedString(allow_none=True)
    orientacion = TrimmedString(required=True)
    tamaño_papel = TrimmedString(required=True)
    
    # Firmantes
    firmante_principal = TrimmedString(allow_none=True)
    cargo_firmante_principal = TrimmedString(allow_none=True)
    firmante_secundario = TrimmedString(allow_none=True)
    cargo_firmante_secundario = TrimmedString(allow_none=True)
    
    # Características de seguridad
    incluir_codigo_verificacion = fields.Boolean(required=True)
    incluir_qr_code = fields.Boolean(required=True)
    incluir_sello_oficial = fields.Boolean(required=True)
    url_verificacion = TrimmedString(dump_only=True, allow_none=True)
    
    # Fechas
    fecha_emision = fields.Date(required=True)
    fecha_vencimiento = fields.Date(allow_none=True)
    fecha_generacion = fields.DateTime(allow_none=True)
    fecha_firma = fields.DateTime(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    
    # Control de validez
    esta_vigente = fields.Boolean(dump_only=True)
    dias_vigencia = PositiveInteger(dump_only=True, allow_none=True)
    esta_vencido = fields.Boolean(dump_only=True)
    
    # Estado
    estado = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    esta_generado = fields.Boolean(dump_only=True)
    esta_firmado = fields.Boolean(dump_only=True)
    esta_entregado = fields.Boolean(dump_only=True)
    puede_anular = fields.Boolean(dump_only=True)
    puede_regenerar = fields.Boolean(dump_only=True)
    
    # Archivos
    ruta_archivo = TrimmedString(allow_none=True)
    nombre_archivo = TrimmedString(allow_none=True)
    tamaño_archivo = NonNegativeInteger(allow_none=True)
    hash_archivo = TrimmedString(allow_none=True)
    
    # Entrega
    entregado_por = TrimmedString(allow_none=True)
    recibido_por = TrimmedString(allow_none=True)
    medio_entrega = TrimmedString(allow_none=True)
    acuse_recibo = fields.Boolean(dump_only=True, missing=False)
    
    # Anulación
    fecha_anulacion = fields.Date(allow_none=True)
    motivo_anulacion = TrimmedString(allow_none=True)
    anulado_por = TrimmedString(allow_none=True)
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True)
    notas_especiales = TrimmedString(allow_none=True)
    notas_internas = TrimmedString(allow_none=True)
    
    # Auditoría
    creado_por = TrimmedString(allow_none=True)
    generado_por = TrimmedString(allow_none=True)
    firmado_por = TrimmedString(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('generacion_certificado')
class GeneracionCertificadoSchema(BaseSchema):
    """Schema para generación de certificados."""
    
    certificado_id = PositiveInteger(required=True)
    generado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    template_usar = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    incluir_marca_agua = fields.Boolean(missing=True)
    resolucion_imagen = PositiveInteger(
        missing=300,
        validate=validate.Range(min=150, max=600)
    )
    
    fecha_generacion = fields.DateTime(required=True, missing=datetime.utcnow)
    
    observaciones_generacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )


@register_schema('firma_certificado')
class FirmaCertificadoSchema(BaseSchema):
    """Schema para firma de certificados."""
    
    certificado_id = PositiveInteger(required=True)
    firmado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    tipo_firma = TrimmedString(
        required=True,
        validate=validate.OneOf(['digital', 'fisica', 'electronica'])
    )
    
    certificado_digital_id = TrimmedString(allow_none=True)
    huella_firma = TrimmedString(allow_none=True)
    
    fecha_firma = fields.DateTime(required=True, missing=datetime.utcnow)
    
    observaciones_firma = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )


@register_schema('entrega_certificado')
class EntregaCertificadoSchema(BaseSchema):
    """Schema para entrega de certificados."""
    
    certificado_id = PositiveInteger(required=True)
    entregado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    recibido_por = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_receptor = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    parentesco_receptor = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'titular', 'padre', 'madre', 'tutor_legal', 'hermano',
            'conyuge', 'representante', 'otro'
        ])
    )
    
    medio_entrega = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'correo', 'mensajeria', 'digital'])
    )
    
    fecha_entrega = fields.Date(required=True, missing=date.today)
    hora_entrega = fields.Time(allow_none=True)
    
    requiere_apostille = fields.Boolean(missing=False)
    legalizado = fields.Boolean(missing=False)
    
    observaciones_entrega = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )


@register_schema('certificado_search')
class CertificadoSearchSchema(BaseSchema):
    """Schema para búsqueda de certificados."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    numero_certificado = TrimmedString(allow_none=True)
    codigo_verificacion = TrimmedString(allow_none=True)
    catequizando_id = PositiveInteger(allow_none=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    
    # Filtros de tipo
    tipo_certificado = TrimmedString(allow_none=True)
    tipos_incluir = fields.List(fields.String(), allow_none=True)
    formato_certificado = TrimmedString(allow_none=True)
    
    # Filtros de beneficiario
    documento_beneficiario = TrimmedString(allow_none=True)
    nombres_beneficiario = TrimmedString(allow_none=True)
    apellidos_beneficiario = TrimmedString(allow_none=True)
    
    # Filtros de fecha
    fecha_evento_desde = fields.Date(allow_none=True)
    fecha_evento_hasta = fields.Date(allow_none=True)
    fecha_emision_desde = fields.Date(allow_none=True)
    fecha_emision_hasta = fields.Date(allow_none=True)
    año_completion = PositiveInteger(allow_none=True)
    
    # Filtros de estado
    estado = TrimmedString(allow_none=True)
    estados_incluir = fields.List(fields.String(), allow_none=True)
    solo_vigentes = fields.Boolean(allow_none=True)
    solo_vencidos = fields.Boolean(allow_none=True)
    
    # Filtros de registro
    numero_registro = TrimmedString(allow_none=True)
    libro_registro = TrimmedString(allow_none=True)
    
    # Filtros de programa
    programa_nombre = TrimmedString(allow_none=True)
    nivel_completado = TrimmedString(allow_none=True)
    
    # Filtros administrativos
    generado_por = TrimmedString(allow_none=True)
    firmado_por = TrimmedString(allow_none=True)
    entregado_por = TrimmedString(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_emision',
        validate=validate.OneOf([
            'fecha_emision', 'fecha_evento', 'numero_certificado',
            'nombres_beneficiario', 'tipo_certificado', 'estado'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('verificacion_certificado')
class VerificacionCertificadoSchema(BaseSchema):
    """Schema para verificación de certificados."""
    
    codigo_verificacion = TrimmedString(
        required=True,
        validate=validate.Length(min=6, max=50)
    )
    
    numero_certificado = TrimmedString(allow_none=True)
    documento_beneficiario = TrimmedString(allow_none=True)
    
    # Información adicional para verificación
    fecha_evento = fields.Date(allow_none=True)
    tipo_certificado = TrimmedString(allow_none=True)


@register_schema('certificado_stats')
class CertificadoStatsSchema(BaseSchema):
    """Schema para estadísticas de certificados."""
    
    total_certificados = NonNegativeInteger(required=True)
    certificados_generados = NonNegativeInteger(required=True)
    certificados_firmados = NonNegativeInteger(required=True)
    certificados_entregados = NonNegativeInteger(required=True)
    certificados_vigentes = NonNegativeInteger(required=True)
    
    # Por tipo
    por_tipo_certificado = fields.Dict(required=True)
    sacramentales_vs_academicos = fields.Dict(required=True)
    
    # Por estado
    por_estado = fields.Dict(required=True)
    
    # Por formato
    por_formato = fields.Dict(required=True)
    digitales_vs_fisicos = fields.Dict(required=True)
    
    # Tendencias temporales
    emitidos_este_mes = NonNegativeInteger(required=True)
    entregados_este_mes = NonNegativeInteger(required=True)
    por_mes_año_actual = fields.List(fields.Dict())
    
    # Por programa
    por_programa = fields.List(fields.Dict())
    por_nivel = fields.List(fields.Dict())
    por_año_completion = fields.List(fields.Dict())
    
    # Eficiencia
    tiempo_promedio_generacion = NonNegativeDecimal(required=True, places=1)
    tiempo_promedio_entrega = NonNegativeDecimal(required=True, places=1)
    tasa_entrega = NonNegativeDecimal(required=True, places=1)
    
    # Verificaciones
    total_verificaciones = NonNegativeInteger(required=True)
    verificaciones_exitosas = NonNegativeInteger(required=True)
    tasa_verificacion_exitosa = NonNegativeDecimal(required=True, places=1)
    
    # Por responsable
    por_generado_por = fields.List(fields.Dict())
    por_firmado_por = fields.List(fields.Dict())
    por_entregado_por = fields.List(fields.Dict())


@register_schema('reporte_certificados')
class ReporteCertificadosSchema(BaseSchema):
    """Schema para reportes de certificados."""
    
    tipo_reporte = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'emitidos', 'entregados', 'por_tipo', 'por_programa',
            'verificaciones', 'estadistico', 'registro_sacramental'
        ])
    )
    
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    
    # Filtros específicos
    tipos_certificado = fields.List(fields.String(), allow_none=True)
    programas_incluir = fields.List(fields.String(), allow_none=True)
    estados_incluir = fields.List(fields.String(), allow_none=True)
    
    # Configuraciones
    incluir_datos_beneficiario = fields.Boolean(missing=True)
    incluir_datos_registro = fields.Boolean(missing=True)
    incluir_firmantes = fields.Boolean(missing=True)
    incluir_graficos = fields.Boolean(missing=True)
    
    # Agrupación
    agrupar_por = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mes', 'tipo', 'programa', 'estado', 'firmante'])
    )
    
    # Formato
    formato_salida = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'excel', 'csv'])
    )
    
    @validates_schema
    def validate_reporte(self, data, **kwargs):
        """Validaciones para reporte."""
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError({'fecha_fin': 'La fecha fin debe ser posterior al inicio'})


@register_schema('anulacion_certificado')
class AnulacionCertificadoSchema(BaseSchema):
    """Schema para anulación de certificados."""
    
    certificado_id = PositiveInteger(required=True)
    anulado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    motivo_anulacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'error_datos', 'duplicado', 'solicitud_beneficiario',
            'error_registro', 'cambio_informacion', 'orden_superior',
            'documento_perdido', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    fecha_anulacion = fields.Date(required=True, missing=date.today)
    
    certificado_reemplazo_id = PositiveInteger(allow_none=True)
    requiere_nuevo_registro = fields.Boolean(missing=False)