"""
Schemas de certificado para el sistema de catequesis.
Maneja validaciones para emisión y gestión de certificados.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('certificado_create')
class CertificadoCreateSchema(BaseSchema):
    """Schema para creación de certificados."""
    
    # Referencias principales
    catequizando_id = PositiveInteger(required=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    nivel_id = PositiveInteger(required=True)
    
    # Tipo de certificado
    tipo_certificado = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'primera_comunion', 'confirmacion', 'bautismo', 'matrimonio',
            'catequesis_completa', 'asistencia', 'participacion',
            'aprovechamiento', 'especializacion', 'otro'
        ])
    )
    
    # Información del certificado
    titulo_certificado = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=200)
    )
    
    descripcion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    motivo_emision = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'completacion_nivel', 'completacion_programa', 'sacramento_recibido',
            'participacion_especial', 'merito_academico', 'solicitud_terceros',
            'tramite_legal', 'otro'
        ])
    )
    
    # Fechas
    fecha_solicitud = fields.Date(required=True, missing=date.today)
    fecha_emision = fields.Date(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    fecha_vencimiento = fields.Date(allow_none=True)
    
    # Información académica
    calificacion_final = NonNegativeDecimal(
        allow_none=True,
        places=2,
        validate=validate.Range(min=0, max=5)
    )
    
    porcentaje_asistencia = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    numero_sesiones_asistidas = NonNegativeInteger(allow_none=True)
    total_sesiones_programadas = NonNegativeInteger(allow_none=True)
    
    # Información sacramental (si aplica)
    fecha_sacramento = fields.Date(allow_none=True)
    lugar_sacramento = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    celebrante = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    padrinos = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Autoridades que certifican
    autoridad_certificadora = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    cargo_autoridad = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'parroco', 'vicario', 'coordinador_catequesis', 'catequista',
            'obispo', 'director_diocesano', 'otro'
        ])
    )
    
    # Validaciones y requisitos
    cumple_requisitos_academicos = fields.Boolean(missing=True)
    cumple_requisitos_asistencia = fields.Boolean(missing=True)
    cumple_requisitos_sacramentales = fields.Boolean(missing=True)
    
    requisitos_pendientes = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Configuración del certificado
    formato = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'fisico', 'digital_firmado'])
    )
    
    template_certificado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    incluir_sello_oficial = fields.Boolean(missing=True)
    incluir_firma_digital = fields.Boolean(missing=False)
    
    # Estado inicial
    estado = TrimmedString(
        required=True,
        missing='pendiente',
        validate=validate.OneOf([
            'pendiente', 'en_proceso', 'generado', 'firmado',
            'entregado', 'anulado'
        ])
    )
    
    # Costos
    costo_emision = NonNegativeDecimal(missing=0, places=2)
    pagado = fields.Boolean(missing=False)
    
    # Observaciones
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_certificado(self, data, **kwargs):
        """Validaciones específicas del certificado."""
        # Validar fechas
        fecha_solicitud = data.get('fecha_solicitud')
        fecha_emision = data.get('fecha_emision')
        fecha_entrega = data.get('fecha_entrega')
        fecha_vencimiento = data.get('fecha_vencimiento')
        
        if fecha_emision and fecha_solicitud and fecha_emision < fecha_solicitud:
            raise ValidationError({'fecha_emision': 'La fecha de emisión no puede ser anterior a la solicitud'})
        
        if fecha_entrega and fecha_emision and fecha_entrega < fecha_emision:
            raise ValidationError({'fecha_entrega': 'La fecha de entrega no puede ser anterior a la emisión'})
        
        if fecha_vencimiento and fecha_emision and fecha_vencimiento <= fecha_emision:
            raise ValidationError({'fecha_vencimiento': 'La fecha de vencimiento debe ser posterior a la emisión'})
        
        # Validar asistencia
        sesiones_asistidas = data.get('numero_sesiones_asistidas')
        total_sesiones = data.get('total_sesiones_programadas')
        
        if sesiones_asistidas is not None and total_sesiones is not None:
            if sesiones_asistidas > total_sesiones:
                raise ValidationError({'numero_sesiones_asistidas': 'No puede ser mayor al total de sesiones'})
        
        # Validar requisitos para ciertos tipos de certificado
        tipo = data.get('tipo_certificado')
        if tipo in ['primera_comunion', 'confirmacion', 'bautismo']:
            fecha_sacramento = data.get('fecha_sacramento')
            lugar_sacramento = data.get('lugar_sacramento')
            
            if not fecha_sacramento:
                raise ValidationError({'fecha_sacramento': 'Fecha del sacramento requerida para este tipo'})
            
            if not lugar_sacramento:
                raise ValidationError({'lugar_sacramento': 'Lugar del sacramento requerido para este tipo'})


@register_schema('certificado_update')
class CertificadoUpdateSchema(BaseSchema):
    """Schema para actualización de certificados."""
    
    # No se pueden cambiar referencias principales
    
    # Información básica
    titulo_certificado = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=200))
    descripcion = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    # Fechas
    fecha_emision = fields.Date(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    fecha_vencimiento = fields.Date(allow_none=True)
    
    # Información académica
    calificacion_final = NonNegativeDecimal(
        allow_none=True,
        places=2,
        validate=validate.Range(min=0, max=5)
    )
    porcentaje_asistencia = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    # Información sacramental
    fecha_sacramento = fields.Date(allow_none=True)
    lugar_sacramento = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    celebrante = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    padrinos = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Autoridades
    autoridad_certificadora = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    cargo_autoridad = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'parroco', 'vicario', 'coordinador_catequesis', 'catequista',
            'obispo', 'director_diocesano', 'otro'
        ])
    )
    
    # Validaciones
    cumple_requisitos_academicos = fields.Boolean(allow_none=True)
    cumple_requisitos_asistencia = fields.Boolean(allow_none=True)
    cumple_requisitos_sacramentales = fields.Boolean(allow_none=True)
    requisitos_pendientes = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Configuración
    template_certificado = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    incluir_sello_oficial = fields.Boolean(allow_none=True)
    incluir_firma_digital = fields.Boolean(allow_none=True)
    
    # Estado
    estado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'pendiente', 'en_proceso', 'generado', 'firmado',
            'entregado', 'anulado'
        ])
    )
    
    # Costos
    pagado = fields.Boolean(allow_none=True)
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('certificado_response')
class CertificadoResponseSchema(BaseSchema):
    """Schema para respuesta de certificado."""
    
    # Información básica
    id = PositiveInteger(required=True)
    numero_certificado = TrimmedString(allow_none=True)
    codigo_verificacion = TrimmedString(allow_none=True)
    
    # Referencias
    catequizando_id = PositiveInteger(required=True)
    catequizando_nombre = TrimmedString(dump_only=True, required=True)
    inscripcion_id = PositiveInteger(allow_none=True)
    nivel_id = PositiveInteger(required=True)
    nivel_nombre = TrimmedString(dump_only=True, required=True)
    
    # Tipo y contenido
    tipo_certificado = TrimmedString(required=True)
    tipo_certificado_display = TrimmedString(dump_only=True)
    titulo_certificado = TrimmedString(allow_none=True)
    descripcion = TrimmedString(allow_none=True)
    motivo_emision = TrimmedString(required=True)
    motivo_emision_display = TrimmedString(dump_only=True)
    
    # Fechas
    fecha_solicitud = fields.Date(required=True)
    fecha_emision = fields.Date(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    fecha_vencimiento = fields.Date(allow_none=True)
    dias_vigencia = PositiveInteger(dump_only=True, allow_none=True)
    esta_vencido = fields.Boolean(dump_only=True)
    
    # Información académica
    calificacion_final = NonNegativeDecimal(allow_none=True, places=2)
    porcentaje_asistencia = NonNegativeDecimal(allow_none=True, places=1)
    numero_sesiones_asistidas = NonNegativeInteger(allow_none=True)
    total_sesiones_programadas = NonNegativeInteger(allow_none=True)
    resultado_academico = TrimmedString(dump_only=True, allow_none=True)
    
    # Información sacramental
    fecha_sacramento = fields.Date(allow_none=True)
    lugar_sacramento = TrimmedString(allow_none=True)
    celebrante = TrimmedString(allow_none=True)
    padrinos = TrimmedString(allow_none=True)
    
    # Autoridades
    autoridad_certificadora = TrimmedString(required=True)
    cargo_autoridad = TrimmedString(required=True)
    cargo_autoridad_display = TrimmedString(dump_only=True)
    
    # Validaciones
    cumple_requisitos_academicos = fields.Boolean(required=True)
    cumple_requisitos_asistencia = fields.Boolean(required=True)
    cumple_requisitos_sacramentales = fields.Boolean(required=True)
    cumple_todos_requisitos = fields.Boolean(dump_only=True)
    requisitos_pendientes = TrimmedString(allow_none=True)
    
    # Configuración
    formato = TrimmedString(required=True)
    formato_display = TrimmedString(dump_only=True)
    template_certificado = TrimmedString(allow_none=True)
    incluir_sello_oficial = fields.Boolean(required=True)
    incluir_firma_digital = fields.Boolean(required=True)
    
    # Archivo generado
    ruta_archivo = TrimmedString(allow_none=True)
    nombre_archivo = TrimmedString(allow_none=True)
    tamaño_archivo = NonNegativeInteger(allow_none=True)
    hash_archivo = TrimmedString(allow_none=True)
    
    # Estado
    estado = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    puede_generar = fields.Boolean(dump_only=True)
    puede_firmar = fields.Boolean(dump_only=True)
    puede_entregar = fields.Boolean(dump_only=True)
    
    # Costos
    costo_emision = NonNegativeDecimal(required=True, places=2)
    pagado = fields.Boolean(required=True)
    
    # Entrega
    entregado_por = TrimmedString(allow_none=True)
    recibido_por = TrimmedString(allow_none=True)
    medio_entrega = TrimmedString(allow_none=True)
    
    # Verificación
    verificaciones_realizadas = NonNegativeInteger(dump_only=True)
    ultima_verificacion = fields.DateTime(dump_only=True, allow_none=True)
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('emision_certificado')
class EmisionCertificadoSchema(BaseSchema):
    """Schema para emisión de certificado."""
    
    certificado_id = PositiveInteger(required=True)
    emitido_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    fecha_emision = fields.Date(required=True, missing=date.today)
    
    # Configuraciones de emisión
    template_usar = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    incluir_sello = fields.Boolean(missing=True)
    incluir_firma_digital = fields.Boolean(missing=False)
    
    # Observaciones de la emisión
    observaciones_emision = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_emision(self, data, **kwargs):
        """Validaciones para emisión."""
        fecha_emision = data.get('fecha_emision')
        
        if fecha_emision and fecha_emision > date.today():
            raise ValidationError({'fecha_emision': 'La fecha de emisión no puede ser futura'})


@register_schema('firma_certificado')
class FirmaCertificadoSchema(BaseSchema):
    """Schema para firma de certificado."""
    
    certificado_id = PositiveInteger(required=True)
    firmado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    cargo_firmante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'parroco', 'vicario', 'obispo', 'coordinador',
            'director_diocesano', 'otro'
        ])
    )
    
    fecha_firma = fields.Date(required=True, missing=date.today)
    
    # Información del firmante
    numero_registro_firmante = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    entidad_registro = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    # Configuraciones de firma
    aplicar_sello_oficial = fields.Boolean(missing=True)
    tipo_firma = TrimmedString(
        required=True,
        validate=validate.OneOf(['fisica', 'digital', 'mixta'])
    )
    
    observaciones_firma = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )


@register_schema('entrega_certificado')
class EntregaCertificadoSchema(BaseSchema):
    """Schema para entrega de certificado."""
    
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
        required=True,
        validate=validate.Length(min=5, max=20)
    )
    
    parentesco_receptor = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'titular', 'padre', 'madre', 'tutor_legal', 'hermano',
            'abuelo', 'tio', 'representante', 'otro'
        ])
    )
    
    fecha_entrega = fields.Date(required=True, missing=date.today)
    hora_entrega = fields.Time(allow_none=True)
    
    medio_entrega = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'correo', 'mensajeria', 'terceros'])
    )
    
    # Para entrega por terceros
    autorizado_por = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    documento_autorizacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    observaciones_entrega = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_entrega(self, data, **kwargs):
        """Validaciones para entrega."""
        medio = data.get('medio_entrega')
        autorizado_por = data.get('autorizado_por')
        
        if medio == 'terceros' and not autorizado_por:
            raise ValidationError({'autorizado_por': 'Requerido para entrega por terceros'})


@register_schema('verificacion_certificado')
class VerificacionCertificadoSchema(BaseSchema):
    """Schema para verificación de certificado."""
    
    numero_certificado = TrimmedString(allow_none=True)
    codigo_verificacion = TrimmedString(allow_none=True)
    certificado_id = PositiveInteger(allow_none=True)
    
    verificado_por = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    @validates_schema
    def validate_verificacion(self, data, **kwargs):
        """Validaciones para verificación."""
        numero = data.get('numero_certificado')
        codigo = data.get('codigo_verificacion')
        cert_id = data.get('certificado_id')
        
        if not numero and not codigo and not cert_id:
            raise ValidationError('Debe proporcionar al menos un método de identificación')


@register_schema('certificado_search')
class CertificadoSearchSchema(BaseSchema):
    """Schema para búsqueda de certificados."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    numero_certificado = TrimmedString(allow_none=True)
    catequizando_id = PositiveInteger(allow_none=True)
    nivel_id = PositiveInteger(allow_none=True)
    tipo_certificado = TrimmedString(allow_none=True)
    
    # Filtros de estado
    estado = TrimmedString(allow_none=True)
    estados_incluir = fields.List(fields.String(), allow_none=True)
    
    # Filtros de fecha
    fecha_solicitud_desde = fields.Date(allow_none=True)
    fecha_solicitud_hasta = fields.Date(allow_none=True)
    fecha_emision_desde = fields.Date(allow_none=True)
    fecha_emision_hasta = fields.Date(allow_none=True)
    
    # Filtros de autoridad
    autoridad_certificadora = TrimmedString(allow_none=True)
    cargo_autoridad = TrimmedString(allow_none=True)
    
    # Filtros de validación
    cumple_todos_requisitos = fields.Boolean(allow_none=True)
    pagado = fields.Boolean(allow_none=True)
    esta_vencido = fields.Boolean(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_solicitud',
        validate=validate.OneOf([
            'fecha_solicitud', 'fecha_emision', 'numero_certificado',
            'catequizando_nombre', 'tipo_certificado', 'estado'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('certificado_stats')
class CertificadoStatsSchema(BaseSchema):
    """Schema para estadísticas de certificados."""
    
    total_certificados = NonNegativeInteger(required=True)
    certificados_emitidos = NonNegativeInteger(required=True)
    certificados_entregados = NonNegativeInteger(required=True)
    pendientes_emision = NonNegativeInteger(required=True)
    
    # Por tipo
    por_tipo_certificado = fields.Dict(required=True)
    
    # Por estado
    por_estado = fields.Dict(required=True)
    
    # Tendencias temporales
    emitidos_este_mes = NonNegativeInteger(required=True)
    emitidos_este_año = NonNegativeInteger(required=True)
    por_mes_año_actual = fields.List(fields.Dict())
    
    # Por autoridad
    por_autoridad_certificadora = fields.List(fields.Dict())
    por_cargo_autoridad = fields.Dict(required=True)
    
    # Financiero
    ingresos_certificados = NonNegativeDecimal(required=True, places=2)
    certificados_gratuitos = NonNegativeInteger(required=True)
    certificados_pagados = NonNegativeInteger(required=True)
    
    # Calidad y validez
    con_todos_requisitos = NonNegativeInteger(required=True)
    certificados_validos = NonNegativeInteger(required=True)
    certificados_vencidos = NonNegativeInteger(required=True)
    
    # Verificaciones
    total_verificaciones = NonNegativeInteger(required=True)
    verificaciones_exitosas = NonNegativeInteger(required=True)
    
    # Por nivel y programa
    por_nivel = fields.List(fields.Dict())
    por_programa = fields.List(fields.Dict())
    
    # Tiempo promedio de procesamiento
    dias_promedio_emision = NonNegativeDecimal(required=True, places=1)
    dias_promedio_entrega = NonNegativeDecimal(required=True, places=1)