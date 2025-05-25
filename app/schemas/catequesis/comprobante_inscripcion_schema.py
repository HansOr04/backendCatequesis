"""
Schemas de comprobante de inscripción para el sistema de catequesis.
Maneja validaciones para comprobantes, recibos y documentos oficiales.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('comprobante_inscripcion_create')
class ComprobanteInscripcionCreateSchema(BaseSchema):
    """Schema para creación de comprobantes de inscripción."""
    
    # Referencias principales
    inscripcion_id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(allow_none=True)
    pago_id = PositiveInteger(allow_none=True)
    
    # Tipo de comprobante
    tipo_comprobante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'recibo_pago', 'comprobante_inscripcion', 'factura',
            'certificado_pago', 'constancia', 'otro'
        ])
    )
    
    # Formato y configuración
    formato = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'html', 'fisico'])
    )
    
    # Fechas
    fecha_emision = fields.Date(required=True, missing=date.today)
    fecha_vencimiento = fields.Date(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    
    # Información del destinatario
    nombre_completo = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_identidad = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=20)
    )
    
    telefono = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=7, max=15)
    )
    
    email = Email(allow_none=True)
    
    direccion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Información del curso/programa
    programa_catequesis = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    nivel_catequesis = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    año_catequesis = PositiveInteger(
        required=True,
        missing=datetime.now().year
    )
    
    periodo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    # Información financiera
    monto_inscripcion = NonNegativeDecimal(missing=0, places=2)
    monto_materiales = NonNegativeDecimal(missing=0, places=2)
    monto_certificado = NonNegativeDecimal(missing=0, places=2)
    descuentos = NonNegativeDecimal(missing=0, places=2)
    recargos = NonNegativeDecimal(missing=0, places=2)
    
    # Detalles del pago (si aplica)
    forma_pago = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'efectivo', 'transferencia', 'tarjeta_credito', 'tarjeta_debito',
            'cheque', 'consignacion', 'pse', 'otro'
        ])
    )
    
    referencia_pago = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    fecha_pago = fields.Date(allow_none=True)
    estado_pago = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['pendiente', 'aprobado', 'rechazado', 'parcial'])
    )
    
    # Control documental
    template_usado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    # Estado inicial
    estado = TrimmedString(
        required=True,
        missing='borrador',
        validate=validate.OneOf(['borrador', 'generado', 'enviado', 'entregado', 'anulado'])
    )
    
    # Control de entrega
    medio_entrega = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['email', 'presencial', 'correo', 'mensajeria'])
    )
    
    # Observaciones
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_comprobante(self, data, **kwargs):
        """Validaciones específicas del comprobante."""
        # Validar fechas
        fecha_emision = data.get('fecha_emision')
        fecha_vencimiento = data.get('fecha_vencimiento')
        fecha_entrega = data.get('fecha_entrega')
        
        if fecha_vencimiento and fecha_emision and fecha_vencimiento < fecha_emision:
            raise ValidationError({'fecha_vencimiento': 'La fecha de vencimiento no puede ser anterior a la emisión'})
        
        if fecha_entrega and fecha_emision and fecha_entrega < fecha_emision:
            raise ValidationError({'fecha_entrega': 'La fecha de entrega no puede ser anterior a la emisión'})
        
        # Validar montos
        monto_inscripcion = data.get('monto_inscripcion', 0)
        monto_materiales = data.get('monto_materiales', 0)
        monto_certificado = data.get('monto_certificado', 0)
        descuentos = data.get('descuentos', 0)
        recargos = data.get('recargos', 0)
        
        subtotal = monto_inscripcion + monto_materiales + monto_certificado
        
        if descuentos > subtotal:
            raise ValidationError({'descuentos': 'Los descuentos no pueden ser mayores al subtotal'})
        
        # Calcular monto total
        data['monto_total'] = subtotal - descuentos + recargos
        
        # Validar información de pago si se proporciona
        forma_pago = data.get('forma_pago')
        referencia_pago = data.get('referencia_pago')
        
        if forma_pago in ['transferencia', 'consignacion'] and not referencia_pago:
            raise ValidationError({'referencia_pago': 'Referencia requerida para transferencias'})


@register_schema('comprobante_inscripcion_update')
class ComprobanteInscripcionUpdateSchema(BaseSchema):
    """Schema para actualización de comprobantes."""
    
    # No se pueden cambiar referencias principales
    
    # Fechas
    fecha_vencimiento = fields.Date(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    
    # Información del destinatario
    telefono = TrimmedString(allow_none=True, validate=validate.Length(min=7, max=15))
    email = Email(allow_none=True)
    direccion = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Información del programa
    periodo = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    
    # Detalles del pago
    referencia_pago = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    fecha_pago = fields.Date(allow_none=True)
    estado_pago = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['pendiente', 'aprobado', 'rechazado', 'parcial'])
    )
    
    # Control documental
    template_usado = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    
    # Estado
    estado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['borrador', 'generado', 'enviado', 'entregado', 'anulado'])
    )
    
    # Entrega
    medio_entrega = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['email', 'presencial', 'correo', 'mensajeria'])
    )
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('comprobante_inscripcion_response')
class ComprobanteInscripcionResponseSchema(BaseSchema):
    """Schema para respuesta de comprobante."""
    
    # Información básica
    id = PositiveInteger(required=True)
    numero_comprobante = TrimmedString(allow_none=True)
    
    # Referencias
    inscripcion_id = PositiveInteger(required=True)
    inscripcion_numero = TrimmedString(dump_only=True, allow_none=True)
    catequizando_id = PositiveInteger(allow_none=True)
    catequizando_nombre = TrimmedString(dump_only=True, allow_none=True)
    pago_id = PositiveInteger(allow_none=True)
    
    # Tipo y formato
    tipo_comprobante = TrimmedString(required=True)
    tipo_comprobante_display = TrimmedString(dump_only=True)
    formato = TrimmedString(required=True)
    formato_display = TrimmedString(dump_only=True)
    
    # Fechas
    fecha_emision = fields.Date(required=True)
    fecha_vencimiento = fields.Date(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    dias_vigencia = PositiveInteger(dump_only=True, allow_none=True)
    esta_vencido = fields.Boolean(dump_only=True)
    
    # Información del destinatario
    nombre_completo = TrimmedString(required=True)
    documento_identidad = TrimmedString(required=True)
    telefono = TrimmedString(allow_none=True)
    email = Email(allow_none=True)
    direccion = TrimmedString(allow_none=True)
    
    # Información del curso/programa
    programa_catequesis = TrimmedString(allow_none=True)
    nivel_catequesis = TrimmedString(allow_none=True)
    año_catequesis = PositiveInteger(required=True)
    periodo = TrimmedString(allow_none=True)
    
    # Información financiera
    monto_inscripcion = NonNegativeDecimal(required=True, places=2)
    monto_materiales = NonNegativeDecimal(required=True, places=2)
    monto_certificado = NonNegativeDecimal(required=True, places=2)
    descuentos = NonNegativeDecimal(required=True, places=2)
    recargos = NonNegativeDecimal(required=True, places=2)
    monto_total = NonNegativeDecimal(dump_only=True, places=2)
    
    # Detalles del pago
    forma_pago = TrimmedString(allow_none=True)
    forma_pago_display = TrimmedString(dump_only=True, allow_none=True)
    referencia_pago = TrimmedString(allow_none=True)
    fecha_pago = fields.Date(allow_none=True)
    estado_pago = TrimmedString(allow_none=True)
    estado_pago_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Control documental
    template_usado = TrimmedString(allow_none=True)
    ruta_archivo = TrimmedString(allow_none=True)
    nombre_archivo = TrimmedString(allow_none=True)
    tamaño_archivo = NonNegativeInteger(allow_none=True)
    hash_archivo = TrimmedString(allow_none=True)
    
    # Estado
    estado = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    esta_generado = fields.Boolean(dump_only=True)
    esta_entregado = fields.Boolean(dump_only=True)
    puede_anular = fields.Boolean(dump_only=True)
    
    # Control de entrega
    entregado_por = TrimmedString(allow_none=True)
    recibido_por = TrimmedString(allow_none=True)
    medio_entrega = TrimmedString(allow_none=True)
    medio_entrega_display = TrimmedString(dump_only=True, allow_none=True)
    acuse_recibo = fields.Boolean(dump_only=True, missing=False)
    
    # Anulación
    fecha_anulacion = fields.Date(allow_none=True)
    motivo_anulacion = TrimmedString(allow_none=True)
    anulado_por = TrimmedString(allow_none=True)
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True)
    notas_internas = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('generacion_comprobante')
class GeneracionComprobanteSchema(BaseSchema):
    """Schema para generación de comprobantes."""
    
    comprobante_id = PositiveInteger(required=True)
    generado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    template = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    fecha_generacion = fields.Date(required=True, missing=date.today)
    
    observaciones_generacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )


@register_schema('envio_comprobante')
class EnvioComprobanteSchema(BaseSchema):
    """Schema para envío de comprobantes."""
    
    comprobante_id = PositiveInteger(required=True)
    enviado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    email_destino = Email(allow_none=True)
    mensaje = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    fecha_envio = fields.DateTime(required=True, missing=datetime.utcnow)
    
    @validates_schema
    def validate_envio(self, data, **kwargs):
        """Validaciones para envío."""
        email_destino = data.get('email_destino')
        if not email_destino:
            raise ValidationError({'email_destino': 'Email de destino requerido para envío'})


@register_schema('entrega_comprobante')
class EntregaComprobanteSchema(BaseSchema):
    """Schema para entrega de comprobantes."""
    
    comprobante_id = PositiveInteger(required=True)
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
            'representante', 'otro'
        ])
    )
    
    medio_entrega = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'correo', 'mensajeria', 'terceros'])
    )
    
    fecha_entrega = fields.Date(required=True, missing=date.today)
    hora_entrega = fields.Time(allow_none=True)
    
    observaciones_entrega = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )


@register_schema('anulacion_comprobante')
class AnulacionComprobanteSchema(BaseSchema):
    """Schema para anulación de comprobantes."""
    
    comprobante_id = PositiveInteger(required=True)
    anulado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    motivo_anulacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'error_datos', 'duplicado', 'solicitud_cliente', 'error_sistema',
            'cambio_informacion', 'orden_superior', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    fecha_anulacion = fields.Date(required=True, missing=date.today)
    
    comprobante_reemplazo_id = PositiveInteger(allow_none=True)


@register_schema('comprobante_search')
class ComprobanteSearchSchema(BaseSchema):
    """Schema para búsqueda de comprobantes."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    numero_comprobante = TrimmedString(allow_none=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    catequizando_id = PositiveInteger(allow_none=True)
    pago_id = PositiveInteger(allow_none=True)
    
    # Filtros de tipo
    tipo_comprobante = TrimmedString(allow_none=True)
    formato = TrimmedString(allow_none=True)
    
    # Filtros de estado
    estado = TrimmedString(allow_none=True)
    estados_incluir = fields.List(fields.String(), allow_none=True)
    
    # Filtros de fecha
    fecha_emision_desde = fields.Date(allow_none=True)
    fecha_emision_hasta = fields.Date(allow_none=True)
    fecha_entrega_desde = fields.Date(allow_none=True)
    fecha_entrega_hasta = fields.Date(allow_none=True)
    
    # Filtros de entrega
    esta_entregado = fields.Boolean(allow_none=True)
    medio_entrega = TrimmedString(allow_none=True)
    pendiente_entrega = fields.Boolean(allow_none=True)
    
    # Filtros de programa
    programa_catequesis = TrimmedString(allow_none=True)
    nivel_catequesis = TrimmedString(allow_none=True)
    año_catequesis = PositiveInteger(allow_none=True)
    
    # Filtros administrativos
    entregado_por = TrimmedString(allow_none=True)
    template_usado = TrimmedString(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_emision',
        validate=validate.OneOf([
            'fecha_emision', 'numero_comprobante', 'nombre_completo',
            'tipo_comprobante', 'estado', 'monto_total'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('comprobante_stats')
class ComprobanteStatsSchema(BaseSchema):
    """Schema para estadísticas de comprobantes."""
    
    total_comprobantes = NonNegativeInteger(required=True)
    comprobantes_generados = NonNegativeInteger(required=True)
    comprobantes_entregados = NonNegativeInteger(required=True)
    comprobantes_pendientes = NonNegativeInteger(required=True)
    
    # Por tipo
    por_tipo_comprobante = fields.Dict(required=True)
    
    # Por estado
    por_estado = fields.Dict(required=True)
    
    # Por formato
    por_formato = fields.Dict(required=True)
    digitales_vs_fisicos = fields.Dict(required=True)
    
    # Tendencias temporales
    generados_este_mes = NonNegativeInteger(required=True)
    entregados_este_mes = NonNegativeInteger(required=True)
    por_mes_año_actual = fields.List(fields.Dict())
    
    # Entrega
    por_medio_entrega = fields.Dict(required=True)
    tasa_entrega = NonNegativeDecimal(required=True, places=1)
    tiempo_promedio_entrega = NonNegativeDecimal(required=True, places=1)
    
    # Por programa
    por_programa_catequesis = fields.List(fields.Dict())
    por_nivel_catequesis = fields.List(fields.Dict())
    por_año_catequesis = fields.List(fields.Dict())
    
    # Eficiencia
    comprobantes_primer_intento = NonNegativeInteger(required=True)
    tasa_generacion_exitosa = NonNegativeDecimal(required=True, places=1)
    
    # Anulaciones
    total_anulaciones = NonNegativeInteger(required=True)
    tasa_anulacion = NonNegativeDecimal(required=True, places=1)
    principales_motivos_anulacion = fields.List(fields.Dict())
    
    # Por responsable
    por_generado_por = fields.List(fields.Dict())
    por_entregado_por = fields.List(fields.Dict())


@register_schema('reporte_comprobantes')
class ReporteComprobantesSchema(BaseSchema):
    """Schema para reportes de comprobantes."""
    
    tipo_reporte = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'emitidos', 'entregados', 'pendientes', 'anulados',
            'por_periodo', 'por_programa', 'estadistico'
        ])
    )
    
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    
    # Filtros del reporte
    filtros = fields.Dict(allow_none=True)
    
    # Configuraciones
    incluir_detalles_financieros = fields.Boolean(missing=True)
    incluir_informacion_entrega = fields.Boolean(missing=True)
    incluir_graficos = fields.Boolean(missing=True)
    incluir_estadisticas = fields.Boolean(missing=True)
    
    # Agrupación
    agrupar_por = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mes', 'trimestre', 'programa', 'tipo', 'estado'])
    )
    
    # Formato de salida
    formato_salida = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'excel', 'csv'])
    )
    
    # Campos a incluir
    campos_incluir = fields.List(
        fields.String(),
        missing=[
            'numero_comprobante', 'fecha_emision', 'nombre_completo',
            'tipo_comprobante', 'monto_total', 'estado'
        ]
    )
    
    @validates_schema
    def validate_reporte(self, data, **kwargs):
        """Validaciones para reporte."""
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError({'fecha_fin': 'La fecha fin debe ser posterior al inicio'})


@register_schema('comprobante_masivo')
class ComprobanteMasivoSchema(BaseSchema):
    """Schema para generación masiva de comprobantes."""
    
    inscripciones_ids = fields.List(
        PositiveInteger(),
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    
    tipo_comprobante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'recibo_pago', 'comprobante_inscripcion', 'constancia'
        ])
    )
    
    formato = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'html'])
    )
    
    generado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    # Configuraciones comunes
    template_usar = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    fecha_emision = fields.Date(required=True, missing=date.today)
    
    observaciones_generales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Configuraciones de entrega
    enviar_automaticamente = fields.Boolean(missing=False)
    medio_entrega_defecto = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['email', 'presencial'])
    )
    
    @validates_schema
    def validate_masivo(self, data, **kwargs):
        """Validaciones para generación masiva."""
        inscripciones = data.get('inscripciones_ids', [])
        if len(set(inscripciones)) != len(inscripciones):
            raise ValidationError({'inscripciones_ids': 'No se pueden repetir inscripciones'})
        
        enviar_auto = data.get('enviar_automaticamente', False)
        medio_entrega = data.get('medio_entrega_defecto')
        
        if enviar_auto and not medio_entrega:
            raise ValidationError({'medio_entrega_defecto': 'Requerido para envío automático'})