"""
Schemas de pago de inscripción para el sistema de catequesis.
Maneja validaciones para pagos, transacciones y gestión financiera.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, Telefono, register_schema,
    PositiveInteger, NonNegativeInteger, NonNegativeDecimal
)


@register_schema('pago_inscripcion_create')
class PagoInscripcionCreateSchema(BaseSchema):
    """Schema para creación de pagos de inscripción."""
    
    # Referencias principales
    inscripcion_id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(allow_none=True)
    
    # Información del pago
    concepto = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'inscripcion', 'materiales', 'certificado', 'mora',
            'actividades', 'uniforme', 'retiro', 'otro'
        ])
    )
    
    descripcion_concepto = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Montos
    monto = NonNegativeDecimal(
        required=True,
        places=2,
        validate=validate.Range(min=0.01)
    )
    
    monto_descuento = NonNegativeDecimal(missing=0, places=2)
    monto_recargo = NonNegativeDecimal(missing=0, places=2)
    
    # Método de pago
    tipo_pago = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'efectivo', 'transferencia', 'tarjeta_credito', 'tarjeta_debito',
            'cheque', 'consignacion', 'pse', 'nequi', 'daviplata'
        ])
    )
    
    # Fechas
    fecha_pago = fields.Date(required=True, missing=date.today)
    fecha_vencimiento = fields.Date(allow_none=True)
    
    # Información del pagador
    nombre_pagador = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_pagador = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    telefono_pagador = Telefono(allow_none=True)
    email_pagador = Email(allow_none=True)
    
    # Referencias bancarias/financieras
    referencia_pago = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    numero_cheque = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    banco_origen = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    cuenta_origen = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    
    banco_destino = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    cuenta_destino = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=20)
    )
    
    # Información de tarjeta (últimos 4 dígitos)
    ultimos_digitos_tarjeta = TrimmedString(
        allow_none=True,
        validate=[
            validate.Length(equal=4),
            validate.Regexp(r'^\d{4}$', error='Deben ser 4 dígitos')
        ]
    )
    
    tipo_tarjeta = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['credito', 'debito'])
    )
    
    franquicia = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['visa', 'mastercard', 'american_express', 'diners', 'otra'])
    )
    
    # Control administrativo
    recibido_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    numero_recibo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    comprobante_fisico = fields.Boolean(missing=False)
    
    # Estado inicial
    estado = TrimmedString(
        required=True,
        missing='pendiente',
        validate=validate.OneOf([
            'pendiente', 'procesando', 'aprobado', 'rechazado',
            'reversado', 'anulado'
        ])
    )
    
    # Observaciones
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_pago(self, data, **kwargs):
        """Validaciones específicas del pago."""
        # Validar fechas
        fecha_pago = data.get('fecha_pago')
        fecha_vencimiento = data.get('fecha_vencimiento')
        
        if fecha_vencimiento and fecha_pago and fecha_vencimiento < fecha_pago:
            raise ValidationError({'fecha_vencimiento': 'La fecha de vencimiento no puede ser anterior al pago'})
        
        # Validar información específica por tipo de pago
        tipo_pago = data.get('tipo_pago')
        
        if tipo_pago == 'cheque':
            numero_cheque = data.get('numero_cheque')
            if not numero_cheque:
                raise ValidationError({'numero_cheque': 'Número de cheque requerido'})
        
        if tipo_pago in ['transferencia', 'consignacion']:
            referencia = data.get('referencia_pago')
            if not referencia:
                raise ValidationError({'referencia_pago': 'Referencia requerida para transferencias/consignaciones'})
        
        if tipo_pago in ['tarjeta_credito', 'tarjeta_debito']:
            ultimos_digitos = data.get('ultimos_digitos_tarjeta')
            if not ultimos_digitos:
                raise ValidationError({'ultimos_digitos_tarjeta': 'Últimos 4 dígitos requeridos para tarjetas'})
        
        # Calcular monto total
        monto = data.get('monto', 0)
        descuento = data.get('monto_descuento', 0)
        recargo = data.get('monto_recargo', 0)
        
        if descuento > monto:
            raise ValidationError({'monto_descuento': 'El descuento no puede ser mayor al monto'})


@register_schema('pago_inscripcion_update')
class PagoInscripcionUpdateSchema(BaseSchema):
    """Schema para actualización de pagos."""
    
    # No se pueden cambiar referencias principales ni montos base
    
    # Información complementaria
    descripcion_concepto = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Fechas
    fecha_vencimiento = fields.Date(allow_none=True)
    
    # Información del pagador
    telefono_pagador = Telefono(allow_none=True)
    email_pagador = Email(allow_none=True)
    
    # Referencias adicionales
    numero_recibo = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    comprobante_fisico = fields.Boolean(allow_none=True)
    
    # Estado
    estado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'pendiente', 'procesando', 'aprobado', 'rechazado',
            'reversado', 'anulado'
        ])
    )
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('pago_inscripcion_response')
class PagoInscripcionResponseSchema(BaseSchema):
    """Schema para respuesta de pago."""
    
    # Información básica
    id = PositiveInteger(required=True)
    numero_transaccion = TrimmedString(allow_none=True)
    
    # Referencias
    inscripcion_id = PositiveInteger(required=True)
    inscripcion_numero = TrimmedString(dump_only=True, allow_none=True)
    catequizando_id = PositiveInteger(allow_none=True)
    catequizando_nombre = TrimmedString(dump_only=True, allow_none=True)
    
    # Información del pago
    concepto = TrimmedString(required=True)
    concepto_display = TrimmedString(dump_only=True)
    descripcion_concepto = TrimmedString(allow_none=True)
    
    # Montos
    monto = NonNegativeDecimal(required=True, places=2)
    monto_descuento = NonNegativeDecimal(required=True, places=2)
    monto_recargo = NonNegativeDecimal(required=True, places=2)
    monto_total = NonNegativeDecimal(dump_only=True, places=2)
    
    # Método de pago
    tipo_pago = TrimmedString(required=True)
    tipo_pago_display = TrimmedString(dump_only=True)
    
    # Fechas
    fecha_pago = fields.Date(required=True)
    fecha_vencimiento = fields.Date(allow_none=True)
    dias_hasta_vencimiento = PositiveInteger(dump_only=True, allow_none=True)
    esta_vencido = fields.Boolean(dump_only=True)
    
    # Información del pagador
    nombre_pagador = TrimmedString(required=True)
    documento_pagador = TrimmedString(allow_none=True)
    telefono_pagador = TrimmedString(allow_none=True)
    email_pagador = Email(allow_none=True)
    
    # Referencias bancarias/financieras
    referencia_pago = TrimmedString(allow_none=True)
    numero_cheque = TrimmedString(allow_none=True)
    banco_origen = TrimmedString(allow_none=True)
    banco_destino = TrimmedString(allow_none=True)
    
    # Información de tarjeta (enmascarada)
    ultimos_digitos_tarjeta = TrimmedString(allow_none=True)
    tipo_tarjeta = TrimmedString(allow_none=True)
    franquicia = TrimmedString(allow_none=True)
    info_tarjeta_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Control administrativo
    recibido_por = TrimmedString(required=True)
    autorizado_por = TrimmedString(allow_none=True)
    fecha_autorizacion = fields.Date(allow_none=True)
    numero_recibo = TrimmedString(allow_none=True)
    comprobante_fisico = fields.Boolean(required=True)
    
    # Estado del pago
    estado = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    esta_aprobado = fields.Boolean(dump_only=True)
    esta_pendiente = fields.Boolean(dump_only=True)
    puede_reversar = fields.Boolean(dump_only=True)
    
    # Reversión/Anulación
    fecha_reverso = fields.Date(allow_none=True)
    motivo_reverso = TrimmedString(allow_none=True)
    reversado_por = TrimmedString(allow_none=True)
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True)
    notas_internas = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('aprobacion_pago')
class AprobacionPagoSchema(BaseSchema):
    """Schema para aprobación de pagos."""
    
    pago_id = PositiveInteger(required=True)
    autorizado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    fecha_autorizacion = fields.Date(required=True, missing=date.today)
    
    observaciones_aprobacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )


@register_schema('rechazo_pago')
class RechazoPagoSchema(BaseSchema):
    """Schema para rechazo de pagos."""
    
    pago_id = PositiveInteger(required=True)
    rechazado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    motivo_rechazo = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'documentos_insuficientes', 'monto_incorrecto', 'datos_incorrectos',
            'cheque_sin_fondos', 'transaccion_duplicada', 'fraude_sospechoso',
            'politica_institucional', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    fecha_rechazo = fields.Date(required=True, missing=date.today)


@register_schema('reverso_pago')
class ReversoPagoSchema(BaseSchema):
    """Schema para reversión de pagos."""
    
    pago_id = PositiveInteger(required=True)
    reversado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    motivo_reverso = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'error_administrativo', 'solicitud_cliente', 'duplicacion',
            'fraude_confirmado', 'orden_judicial', 'politica_reembolso', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    fecha_reverso = fields.Date(required=True, missing=date.today)
    
    # Información del reembolso
    metodo_reembolso = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'efectivo', 'transferencia', 'cheque', 'nota_credito',
            'descuento_futuro', 'mismo_metodo_pago'
        ])
    )
    
    cuenta_reembolso = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    banco_reembolso = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )


@register_schema('plan_pagos')
class PlanPagosSchema(BaseSchema):
    """Schema para planes de pago."""
    
    inscripcion_id = PositiveInteger(required=True)
    monto_total = NonNegativeDecimal(
        required=True,
        places=2,
        validate=validate.Range(min=0.01)
    )
    
    numero_cuotas = PositiveInteger(
        required=True,
        validate=validate.Range(min=2, max=12)
    )
    
    valor_cuota = NonNegativeDecimal(
        required=True,
        places=2,
        validate=validate.Range(min=0.01)
    )
    
    fecha_primera_cuota = fields.Date(required=True)
    periodicidad = TrimmedString(
        required=True,
        validate=validate.OneOf(['semanal', 'quincenal', 'mensual'])
    )
    
    # Intereses y recargos
    tasa_interes = NonNegativeDecimal(
        missing=0,
        places=2,
        validate=validate.Range(min=0, max=50)
    )
    
    valor_mora_dia = NonNegativeDecimal(
        missing=0,
        places=2
    )
    
    dias_gracia = NonNegativeInteger(missing=5, validate=validate.Range(max=30))
    
    # Configuraciones
    pago_anticipado_permitido = fields.Boolean(missing=True)
    descuento_pago_total = NonNegativeDecimal(
        missing=0,
        places=1,
        validate=validate.Range(min=0, max=20)
    )
    
    observaciones_plan = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_plan_pagos(self, data, **kwargs):
        """Validaciones del plan de pagos."""
        monto_total = data.get('monto_total', 0)
        numero_cuotas = data.get('numero_cuotas', 1)
        valor_cuota = data.get('valor_cuota', 0)
        
        # Verificar coherencia entre monto total y cuotas
        total_cuotas = valor_cuota * numero_cuotas
        diferencia_permitida = monto_total * 0.01  # 1% de diferencia
        
        if abs(total_cuotas - monto_total) > diferencia_permitida:
            raise ValidationError('El valor de las cuotas no coincide con el monto total')


@register_schema('cuota_pago')
class CuotaPagoSchema(BaseSchema):
    """Schema para cuotas de plan de pagos."""
    
    plan_pagos_id = PositiveInteger(required=True)
    numero_cuota = PositiveInteger(required=True)
    
    valor_cuota = NonNegativeDecimal(required=True, places=2)
    fecha_vencimiento = fields.Date(required=True)
    
    # Estado de la cuota
    estado_cuota = TrimmedString(
        required=True,
        missing='pendiente',
        validate=validate.OneOf(['pendiente', 'pagada', 'vencida', 'condonada'])
    )
    
    # Información del pago
    pago_id = PositiveInteger(allow_none=True)
    fecha_pago = fields.Date(allow_none=True)
    monto_pagado = NonNegativeDecimal(allow_none=True, places=2)
    
    # Mora
    dias_mora = NonNegativeInteger(allow_none=True)
    valor_mora = NonNegativeDecimal(missing=0, places=2)
    
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )


@register_schema('pago_search')
class PagoSearchSchema(BaseSchema):
    """Schema para búsqueda de pagos."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    numero_transaccion = TrimmedString(allow_none=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    catequizando_id = PositiveInteger(allow_none=True)
    
    # Filtros de concepto y tipo
    concepto = TrimmedString(allow_none=True)
    tipo_pago = TrimmedString(allow_none=True)
    
    # Filtros de estado
    estado = TrimmedString(allow_none=True)
    estados_incluir = fields.List(fields.String(), allow_none=True)
    
    # Filtros de fecha
    fecha_pago_desde = fields.Date(allow_none=True)
    fecha_pago_hasta = fields.Date(allow_none=True)
    
    # Filtros de monto
    monto_minimo = NonNegativeDecimal(allow_none=True, places=2)
    monto_maximo = NonNegativeDecimal(allow_none=True, places=2)
    
    # Filtros administrativos
    recibido_por = TrimmedString(allow_none=True)
    autorizado_por = TrimmedString(allow_none=True)
    
    # Filtros especiales
    tiene_recibo = fields.Boolean(allow_none=True)
    esta_vencido = fields.Boolean(allow_none=True)
    requiere_seguimiento = fields.Boolean(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_pago',
        validate=validate.OneOf([
            'fecha_pago', 'numero_transaccion', 'monto_total',
            'nombre_pagador', 'estado', 'created_at'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('pago_stats')
class PagoStatsSchema(BaseSchema):
    """Schema para estadísticas de pagos."""
    
    total_pagos = NonNegativeInteger(required=True)
    pagos_aprobados = NonNegativeInteger(required=True)
    pagos_pendientes = NonNegativeInteger(required=True)
    pagos_rechazados = NonNegativeInteger(required=True)
    
    # Montos
    monto_total_recaudado = NonNegativeDecimal(required=True, places=2)
    monto_pendiente = NonNegativeDecimal(required=True, places=2)
    monto_promedio_pago = NonNegativeDecimal(required=True, places=2)
    
    # Por concepto
    por_concepto = fields.Dict(required=True)
    ingresos_por_concepto = fields.List(fields.Dict())
    
    # Por método de pago
    por_tipo_pago = fields.Dict(required=True)
    efectivo_vs_digital = fields.Dict(required=True)
    
    # Tendencias temporales
    ingresos_este_mes = NonNegativeDecimal(required=True, places=2)
    ingresos_mes_anterior = NonNegativeDecimal(required=True, places=2)
    crecimiento_mensual = fields.Decimal(required=True, places=1)
    por_mes_año_actual = fields.List(fields.Dict())
    
    # Morosidad
    pagos_vencidos = NonNegativeInteger(required=True)
    monto_vencido = NonNegativeDecimal(required=True, places=2)
    tasa_morosidad = NonNegativeDecimal(required=True, places=1)
    
    # Eficiencia
    tiempo_promedio_aprobacion = NonNegativeDecimal(required=True, places=1)
    pagos_primer_intento = NonNegativeInteger(required=True)
    tasa_aprobacion = NonNegativeDecimal(required=True, places=1)
    
    # Por responsable
    por_recibido_por = fields.List(fields.Dict())
    por_autorizado_por = fields.List(fields.Dict())
    
    # Reversiones y devoluciones
    total_reversiones = NonNegativeInteger(required=True)
    monto_reversiones = NonNegativeDecimal(required=True, places=2)
    principales_motivos_reverso = fields.List(fields.Dict())


@register_schema('conciliacion_pagos')
class ConciliacionPagosSchema(BaseSchema):
    """Schema para conciliación de pagos."""
    
    fecha_conciliacion = fields.Date(required=True, missing=date.today)
    fecha_inicio_periodo = fields.Date(required=True)
    fecha_fin_periodo = fields.Date(required=True)
    
    tipo_conciliacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['diaria', 'semanal', 'mensual', 'especial'])
    )
    
    # Totales del sistema
    total_sistema = NonNegativeDecimal(required=True, places=2)
    cantidad_transacciones_sistema = NonNegativeInteger(required=True)
    
    # Totales bancarios/externos
    total_bancario = NonNegativeDecimal(required=True, places=2)
    cantidad_transacciones_bancarias = NonNegativeInteger(required=True)
    
    # Diferencias
    diferencia_monto = fields.Decimal(dump_only=True, places=2)
    diferencia_cantidad = fields.Integer(dump_only=True)
    
    # Estado de conciliación
    conciliado = fields.Boolean(dump_only=True)
    
    # Observaciones y ajustes
    observaciones_conciliacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    ajustes_realizados = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    responsable_conciliacion = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    @validates_schema
    def validate_conciliacion(self, data, **kwargs):
        """Validaciones para conciliación."""
        fecha_inicio = data.get('fecha_inicio_periodo')
        fecha_fin = data.get('fecha_fin_periodo')
        fecha_conciliacion = data.get('fecha_conciliacion')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError({'fecha_fin_periodo': 'La fecha fin debe ser posterior al inicio'})
        
        if fecha_conciliacion and fecha_fin and fecha_conciliacion < fecha_fin:
            raise ValidationError({'fecha_conciliacion': 'La conciliación debe ser posterior al período'})
        
        # Calcular diferencias
        total_sistema = data.get('total_sistema', 0)
        total_bancario = data.get('total_bancario', 0)
        data['diferencia_monto'] = total_sistema - total_bancario
        
        cantidad_sistema = data.get('cantidad_transacciones_sistema', 0)
        cantidad_bancaria = data.get('cantidad_transacciones_bancarias', 0)
        data['diferencia_cantidad'] = cantidad_sistema - cantidad_bancaria
        
        # Determinar si está conciliado
        data['conciliado'] = (
            abs(data['diferencia_monto']) < 0.01 and
            data['diferencia_cantidad'] == 0
        )