"""
Schemas de notificaciones para el sistema de catequesis.
Maneja validaciones para notificaciones, mensajes y comunicaciones.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date, time
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('notificacion_create')
class NotificacionCreateSchema(BaseSchema):
    """Schema para creación de notificaciones."""
    
    # Referencias principales
    catequizando_id = PositiveInteger(allow_none=True)
    catequista_id = PositiveInteger(allow_none=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    pago_id = PositiveInteger(allow_none=True)
    
    # Tipo y configuración
    tipo_notificacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'recordatorio_pago', 'confirmacion_inscripcion', 'cambio_horario',
            'suspension_clases', 'evento_especial', 'comunicado_general',
            'alerta_comportamiento', 'felicitacion', 'convocatoria',
            'recordatorio_documentos', 'otro'
        ])
    )
    
    prioridad = TrimmedString(
        required=True,
        missing='normal',
        validate=validate.OneOf(['baja', 'normal', 'alta', 'urgente'])
    )
    
    # Contenido
    titulo = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    
    mensaje = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=2000)
    )
    
    mensaje_corto = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=160)
    )
    
    # Destinatarios
    destinatario_nombre = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=150)
    )
    
    destinatario_email = Email(allow_none=True)
    destinatario_telefono = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=7, max=15)
    )
    
    # Canales de entrega
    enviar_email = fields.Boolean(missing=True)
    enviar_sms = fields.Boolean(missing=False)
    enviar_whatsapp = fields.Boolean(missing=False)
    mostrar_sistema = fields.Boolean(missing=True)
    
    # Programación
    enviar_inmediatamente = fields.Boolean(missing=True)
    fecha_programada = fields.DateTime(allow_none=True)
    repetir_notificacion = fields.Boolean(missing=False)
    
    frecuencia_repeticion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['diaria', 'semanal', 'mensual'])
    )
    
    hasta_fecha = fields.Date(allow_none=True)
    
    # Configuraciones adicionales
    requiere_confirmacion = fields.Boolean(missing=False)
    fecha_expiracion = fields.DateTime(allow_none=True)
    
    # Plantilla y formato
    template_id = PositiveInteger(allow_none=True)
    variables_template = fields.Dict(allow_none=True)
    
    # Estado inicial
    estado = TrimmedString(
        required=True,
        missing='borrador',
        validate=validate.OneOf(['borrador', 'programada', 'enviada', 'entregada', 'fallida', 'expirada'])
    )
    
    # Categorización
    categoria = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'academica', 'administrativa', 'pastoral', 'disciplinaria',
            'financiera', 'evento', 'emergencia'
        ])
    )
    
    tags = fields.List(fields.String(), allow_none=True)
    
    # Observaciones
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_notificacion(self, data, **kwargs):
        """Validaciones específicas de la notificación."""
        # Validar canales de entrega
        enviar_email = data.get('enviar_email', False)
        enviar_sms = data.get('enviar_sms', False)
        enviar_whatsapp = data.get('enviar_whatsapp', False)
        mostrar_sistema = data.get('mostrar_sistema', False)
        
        if not any([enviar_email, enviar_sms, enviar_whatsapp, mostrar_sistema]):
            raise ValidationError({'canales': 'Debe seleccionar al menos un canal de entrega'})
        
        # Validar contacto para canales específicos
        email = data.get('destinatario_email')
        telefono = data.get('destinatario_telefono')
        
        if enviar_email and not email:
            raise ValidationError({'destinatario_email': 'Email requerido para envío por correo'})
        
        if (enviar_sms or enviar_whatsapp) and not telefono:
            raise ValidationError({'destinatario_telefono': 'Teléfono requerido para SMS/WhatsApp'})
        
        # Validar programación
        enviar_inmediatamente = data.get('enviar_inmediatamente', True)
        fecha_programada = data.get('fecha_programada')
        
        if not enviar_inmediatamente and not fecha_programada:
            raise ValidationError({'fecha_programada': 'Fecha requerida si no se envía inmediatamente'})
        
        if fecha_programada and fecha_programada < datetime.now():
            raise ValidationError({'fecha_programada': 'La fecha programada debe ser futura'})
        
        # Validar repetición
        repetir = data.get('repetir_notificacion', False)
        frecuencia = data.get('frecuencia_repeticion')
        hasta_fecha = data.get('hasta_fecha')
        
        if repetir and not frecuencia:
            raise ValidationError({'frecuencia_repeticion': 'Frecuencia requerida para repetición'})
        
        if repetir and hasta_fecha and hasta_fecha < date.today():
            raise ValidationError({'hasta_fecha': 'La fecha límite debe ser futura'})
        
        # Validar mensaje corto para SMS
        if enviar_sms and not data.get('mensaje_corto'):
            # Generar mensaje corto automáticamente si no se proporciona
            mensaje = data.get('mensaje', '')
            if len(mensaje) > 160:
                data['mensaje_corto'] = mensaje[:157] + '...'
            else:
                data['mensaje_corto'] = mensaje


@register_schema('notificacion_update')
class NotificacionUpdateSchema(BaseSchema):
    """Schema para actualización de notificaciones."""
    
    # Solo campos modificables después de creación
    titulo = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=200))
    mensaje = TrimmedString(allow_none=True, validate=validate.Length(min=10, max=2000))
    mensaje_corto = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=160))
    
    # Contacto
    destinatario_email = Email(allow_none=True)
    destinatario_telefono = TrimmedString(allow_none=True, validate=validate.Length(min=7, max=15))
    
    # Programación (solo si no se ha enviado)
    fecha_programada = fields.DateTime(allow_none=True)
    repetir_notificacion = fields.Boolean(allow_none=True)
    frecuencia_repeticion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['diaria', 'semanal', 'mensual'])
    )
    hasta_fecha = fields.Date(allow_none=True)
    
    # Estado
    estado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['borrador', 'programada', 'enviada', 'entregada', 'fallida', 'expirada'])
    )
    
    # Configuraciones
    requiere_confirmacion = fields.Boolean(allow_none=True)
    fecha_expiracion = fields.DateTime(allow_none=True)
    
    # Categorización
    categoria = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'academica', 'administrativa', 'pastoral', 'disciplinaria',
            'financiera', 'evento', 'emergencia'
        ])
    )
    
    tags = fields.List(fields.String(), allow_none=True)
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))


@register_schema('notificacion_response')
class NotificacionResponseSchema(BaseSchema):
    """Schema para respuesta de notificación."""
    
    # Información básica
    id = PositiveInteger(required=True)
    numero_notificacion = TrimmedString(allow_none=True)
    
    # Referencias
    catequizando_id = PositiveInteger(allow_none=True)
    catequizando_nombre = TrimmedString(dump_only=True, allow_none=True)
    catequista_id = PositiveInteger(allow_none=True)
    catequista_nombre = TrimmedString(dump_only=True, allow_none=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    pago_id = PositiveInteger(allow_none=True)
    
    # Tipo y configuración
    tipo_notificacion = TrimmedString(required=True)
    tipo_notificacion_display = TrimmedString(dump_only=True)
    prioridad = TrimmedString(required=True)
    prioridad_display = TrimmedString(dump_only=True)
    
    # Contenido
    titulo = TrimmedString(required=True)
    mensaje = TrimmedString(required=True)
    mensaje_corto = TrimmedString(allow_none=True)
    
    # Destinatario
    destinatario_nombre = TrimmedString(required=True)
    destinatario_email = Email(allow_none=True)
    destinatario_telefono = TrimmedString(allow_none=True)
    
    # Canales configurados
    enviar_email = fields.Boolean(required=True)
    enviar_sms = fields.Boolean(required=True)
    enviar_whatsapp = fields.Boolean(required=True)
    mostrar_sistema = fields.Boolean(required=True)
    canales_activos = fields.List(fields.String(), dump_only=True)
    
    # Fechas y programación
    fecha_creacion = fields.DateTime(required=True)
    fecha_programada = fields.DateTime(allow_none=True)
    fecha_envio = fields.DateTime(allow_none=True)
    fecha_entrega = fields.DateTime(allow_none=True)
    fecha_leida = fields.DateTime(allow_none=True)
    
    # Repetición
    repetir_notificacion = fields.Boolean(required=True)
    frecuencia_repeticion = TrimmedString(allow_none=True)
    hasta_fecha = fields.Date(allow_none=True)
    
    # Estado y control
    estado = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    esta_enviada = fields.Boolean(dump_only=True)
    esta_entregada = fields.Boolean(dump_only=True)
    esta_leida = fields.Boolean(dump_only=True)
    esta_expirada = fields.Boolean(dump_only=True)
    puede_reenviar = fields.Boolean(dump_only=True)
    
    # Confirmación
    requiere_confirmacion = fields.Boolean(required=True)
    fecha_confirmacion = fields.DateTime(allow_none=True)
    confirmada = fields.Boolean(dump_only=True)
    
    # Entrega por canal
    estado_email = TrimmedString(allow_none=True)
    estado_sms = TrimmedString(allow_none=True)
    estado_whatsapp = TrimmedString(allow_none=True)
    estado_sistema = TrimmedString(allow_none=True)
    
    fecha_entrega_email = fields.DateTime(allow_none=True)
    fecha_entrega_sms = fields.DateTime(allow_none=True)
    fecha_entrega_whatsapp = fields.DateTime(allow_none=True)
    
    # Plantilla
    template_id = PositiveInteger(allow_none=True)
    template_nombre = TrimmedString(dump_only=True, allow_none=True)
    variables_template = fields.Dict(allow_none=True)
    
    # Categorización
    categoria = TrimmedString(allow_none=True)
    categoria_display = TrimmedString(dump_only=True, allow_none=True)
    tags = fields.List(fields.String(), allow_none=True)
    
    # Métricas
    intentos_envio = NonNegativeInteger(dump_only=True, missing=0)
    tiempo_entrega_promedio = NonNegativeInteger(dump_only=True, allow_none=True)
    
    # Control de errores
    ultimo_error = TrimmedString(allow_none=True)
    fecha_ultimo_error = fields.DateTime(allow_none=True)
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True)
    notas_internas = TrimmedString(allow_none=True)
    
    # Auditoría
    creado_por = TrimmedString(allow_none=True)
    enviado_por = TrimmedString(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('envio_notificacion')
class EnvioNotificacionSchema(BaseSchema):
    """Schema para envío de notificaciones."""
    
    notificacion_id = PositiveInteger(required=True)
    enviado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    # Canales específicos (opcional, si no se usan los configurados)
    canales_envio = fields.List(
        fields.String(validate=validate.OneOf(['email', 'sms', 'whatsapp', 'sistema'])),
        allow_none=True
    )
    
    fecha_envio = fields.DateTime(required=True, missing=datetime.utcnow)
    forzar_reenvio = fields.Boolean(missing=False)
    
    observaciones_envio = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )


@register_schema('confirmacion_notificacion')
class ConfirmacionNotificacionSchema(BaseSchema):
    """Schema para confirmación de notificaciones."""
    
    notificacion_id = PositiveInteger(required=True)
    confirmado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    fecha_confirmacion = fields.DateTime(required=True, missing=datetime.utcnow)
    
    respuesta = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    canal_confirmacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['email', 'sms', 'whatsapp', 'sistema', 'presencial'])
    )


@register_schema('notificacion_masiva')
class NotificacionMasivaSchema(BaseSchema):
    """Schema para envío masivo de notificaciones."""
    
    # Destinatarios
    catequizandos_ids = fields.List(PositiveInteger(), allow_none=True)
    catequistas_ids = fields.List(PositiveInteger(), allow_none=True)
    grupos_ids = fields.List(PositiveInteger(), allow_none=True)
    
    # Criterios de selección automática
    filtro_programa = TrimmedString(allow_none=True)
    filtro_nivel = TrimmedString(allow_none=True)
    filtro_año = PositiveInteger(allow_none=True)
    solo_activos = fields.Boolean(missing=True)
    
    # Contenido de la notificación
    tipo_notificacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'comunicado_general', 'evento_especial', 'suspension_clases',
            'cambio_horario', 'convocatoria', 'recordatorio_documentos'
        ])
    )
    
    titulo = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    
    mensaje = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=2000)
    )
    
    # Canales
    enviar_email = fields.Boolean(missing=True)
    enviar_sms = fields.Boolean(missing=False)
    mostrar_sistema = fields.Boolean(missing=True)
    
    # Programación
    enviar_inmediatamente = fields.Boolean(missing=True)
    fecha_programada = fields.DateTime(allow_none=True)
    
    # Configuraciones
    prioridad = TrimmedString(
        missing='normal',
        validate=validate.OneOf(['baja', 'normal', 'alta', 'urgente'])
    )
    
    personalizar_por_destinatario = fields.Boolean(missing=False)
    
    enviado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    @validates_schema
    def validate_masiva(self, data, **kwargs):
        """Validaciones para envío masivo."""
        # Al menos un tipo de destinatario
        catequizandos = data.get('catequizandos_ids', [])
        catequistas = data.get('catequistas_ids', [])
        grupos = data.get('grupos_ids', [])
        
        tiene_filtros = any([
            data.get('filtro_programa'),
            data.get('filtro_nivel'),
            data.get('filtro_año')
        ])
        
        if not any([catequizandos, catequistas, grupos]) and not tiene_filtros:
            raise ValidationError({'destinatarios': 'Debe especificar destinatarios o filtros'})
        
        # Al menos un canal
        canales = [
            data.get('enviar_email', False),
            data.get('enviar_sms', False),
            data.get('mostrar_sistema', False)
        ]
        
        if not any(canales):
            raise ValidationError({'canales': 'Debe seleccionar al menos un canal'})


@register_schema('notificacion_search')
class NotificacionSearchSchema(BaseSchema):
    """Schema para búsqueda de notificaciones."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    catequizando_id = PositiveInteger(allow_none=True)
    catequista_id = PositiveInteger(allow_none=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    
    # Filtros de tipo
    tipo_notificacion = TrimmedString(allow_none=True)
    tipos_incluir = fields.List(fields.String(), allow_none=True)
    prioridad = TrimmedString(allow_none=True)
    categoria = TrimmedString(allow_none=True)
    
    # Filtros de estado
    estado = TrimmedString(allow_none=True)
    estados_incluir = fields.List(fields.String(), allow_none=True)
    
    # Filtros de fecha
    fecha_desde = fields.DateTime(allow_none=True)
    fecha_hasta = fields.DateTime(allow_none=True)
    fecha_envio_desde = fields.DateTime(allow_none=True)
    fecha_envio_hasta = fields.DateTime(allow_none=True)
    
    # Filtros de entrega
    solo_enviadas = fields.Boolean(allow_none=True)
    solo_entregadas = fields.Boolean(allow_none=True)
    solo_leidas = fields.Boolean(allow_none=True)
    solo_pendientes = fields.Boolean(allow_none=True)
    
    # Filtros de canal
    canal_email = fields.Boolean(allow_none=True)
    canal_sms = fields.Boolean(allow_none=True)
    canal_sistema = fields.Boolean(allow_none=True)
    
    # Filtros administrativos
    creado_por = TrimmedString(allow_none=True)
    enviado_por = TrimmedString(allow_none=True)
    requiere_confirmacion = fields.Boolean(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_creacion',
        validate=validate.OneOf([
            'fecha_creacion', 'fecha_envio', 'titulo', 'prioridad',
            'tipo_notificacion', 'estado', 'destinatario_nombre'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('notificacion_stats')
class NotificacionStatsSchema(BaseSchema):
    """Schema para estadísticas de notificaciones."""
    
    total_notificaciones = NonNegativeInteger(required=True)
    notificaciones_enviadas = NonNegativeInteger(required=True)
    notificaciones_entregadas = NonNegativeInteger(required=True)
    notificaciones_leidas = NonNegativeInteger(required=True)
    notificaciones_pendientes = NonNegativeInteger(required=True)
    
    # Tasas
    tasa_entrega = NonNegativeDecimal(required=True, places=1)
    tasa_lectura = NonNegativeDecimal(required=True, places=1)
    tasa_confirmacion = NonNegativeDecimal(required=True, places=1)
    
    # Por tipo
    por_tipo_notificacion = fields.Dict(required=True)
    por_prioridad = fields.Dict(required=True)
    por_categoria = fields.Dict(required=True)
    
    # Por canal
    por_canal = fields.Dict(required=True)
    eficiencia_por_canal = fields.Dict(required=True)
    
    # Temporal
    enviadas_hoy = NonNegativeInteger(required=True)
    enviadas_esta_semana = NonNegativeInteger(required=True)
    enviadas_este_mes = NonNegativeInteger(required=True)
    por_mes_año_actual = fields.List(fields.Dict())
    
    # Tiempo de respuesta
    tiempo_promedio_entrega = NonNegativeDecimal(required=True, places=1)
    tiempo_promedio_lectura = NonNegativeDecimal(required=True, places=1)
    
    # Errores
    total_errores = NonNegativeInteger(required=True)
    tasa_error = NonNegativeDecimal(required=True, places=1)
    principales_errores = fields.List(fields.Dict())
    
    # Por responsable
    por_creado_por = fields.List(fields.Dict())
    por_enviado_por = fields.List(fields.Dict())


@register_schema('template_notificacion')
class TemplateNotificacionSchema(BaseSchema):
    """Schema para plantillas de notificación."""
    
    nombre = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    descripcion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    tipo_notificacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'recordatorio_pago', 'confirmacion_inscripcion', 'cambio_horario',
            'suspension_clases', 'evento_especial', 'comunicado_general',
            'alerta_comportamiento', 'felicitacion', 'convocatoria',
            'recordatorio_documentos', 'otro'
        ])
    )
    
    titulo_plantilla = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    
    mensaje_plantilla = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=2000)
    )
    
    mensaje_corto_plantilla = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=160)
    )
    
    variables_disponibles = fields.List(fields.String(), allow_none=True)
    variables_requeridas = fields.List(fields.String(), allow_none=True)
    
    activa = fields.Boolean(missing=True)
    
    canales_recomendados = fields.List(
        fields.String(validate=validate.OneOf(['email', 'sms', 'whatsapp', 'sistema'])),
        allow_none=True
    )