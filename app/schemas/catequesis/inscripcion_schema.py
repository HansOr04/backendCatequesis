"""
Schemas de inscripción para el sistema de catequesis.
Maneja validaciones para inscripciones de catequizandos en niveles y grupos.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('inscripcion_create')
class InscripcionCreateSchema(BaseSchema):
    """Schema para creación de inscripciones."""
    
    # Referencias principales
    catequizando_id = PositiveInteger(required=True)
    nivel_id = PositiveInteger(required=True)
    grupo_id = PositiveInteger(allow_none=True)
    parroquia_id = PositiveInteger(required=True)
    
    # Fechas de la inscripción
    fecha_inscripcion = fields.Date(required=True, missing=date.today)
    fecha_inicio_clases = fields.Date(allow_none=True)
    fecha_fin_estimada = fields.Date(allow_none=True)
    
    # Estado de la inscripción
    estado_inscripcion = TrimmedString(
        required=True,
        missing='pendiente',
        validate=validate.OneOf([
            'pendiente', 'pre_inscrita', 'confirmada', 'activa',
            'suspendida', 'retirada', 'completada', 'transferida', 'cancelada'
        ])
    )
    
    # Información del proceso de inscripción
    forma_inscripcion = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'virtual', 'telefonica', 'terceros'])
    )
    
    inscrito_por = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    relacion_inscriptor = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'padre', 'madre', 'tutor_legal', 'abuelo', 'abuela',
            'hermano_mayor', 'tio', 'tia', 'representante', 'autoregistro', 'otro'
        ])
    )
    
    # Motivación para la inscripción
    motivo_inscripcion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'preparacion_sacramento', 'formacion_religiosa', 'tradicion_familiar',
            'crecimiento_espiritual', 'valores_cristianos', 'comunidad_fe',
            'requisito_sacramental', 'recomendacion_terceros', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Expectativas y objetivos
    expectativas_catequesis = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    objetivos_personales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Experiencia religiosa previa
    ha_recibido_catequesis_antes = fields.Boolean(missing=False)
    lugar_catequesis_anterior = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    nivel_catequesis_anterior = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    año_catequesis_anterior = PositiveInteger(allow_none=True)
    motivo_no_continuidad = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Preferencias de horario y grupo
    preferencia_horario = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mañana', 'tarde', 'noche', 'cualquiera'])
    )
    
    preferencia_dia = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo', 'cualquiera'
        ])
    )
    
    requiere_atencion_especial = fields.Boolean(missing=False)
    tipo_atencion_especial = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'discapacidad_fisica', 'discapacidad_cognitiva', 'discapacidad_sensorial',
            'dificultades_aprendizaje', 'problemas_conducta', 'situacion_familiar_especial',
            'timidez_extrema', 'hiperactividad', 'otro'
        ])
    )
    
    descripcion_atencion_especial = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Información financiera
    costo_total_inscripcion = NonNegativeDecimal(required=True, places=2)
    costo_materiales = NonNegativeDecimal(missing=0, places=2)
    otros_costos = NonNegativeDecimal(missing=0, places=2)
    descuento_aplicado = NonNegativeDecimal(missing=0, places=2)
    monto_total_pagar = NonNegativeDecimal(dump_only=True, places=2)
    
    # Becas y ayudas
    solicita_beca = fields.Boolean(missing=False)
    tipo_beca_solicitada = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'beca_completa', 'beca_parcial', 'exencion_materiales',
            'plan_pagos', 'ayuda_social', 'descuento_hermanos'
        ])
    )
    
    justificacion_beca = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    beca_aprobada = fields.Boolean(allow_none=True)
    porcentaje_beca = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    # Documentación requerida
    documentos_entregados = fields.List(
        fields.String(validate=validate.OneOf([
            'fotocopia_documento', 'foto_reciente', 'certificado_bautismo',
            'certificado_primera_comunion', 'certificado_confirmacion',
            'certificado_nacimiento', 'certificado_estudios', 'carta_parroco',
            'autorizacion_padres', 'comprobante_pago', 'examen_medico', 'otro'
        ])),
        missing=[]
    )
    
    documentos_pendientes = fields.List(
        fields.String(),
        missing=[]
    )
    
    documentacion_completa = fields.Boolean(dump_only=True)
    
    # Compromisos y autorizaciones
    acepta_reglamento = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe aceptar el reglamento interno')
    )
    
    autoriza_fotos_videos = fields.Boolean(missing=True)
    autoriza_salidas_pedagogicas = fields.Boolean(missing=True)
    autoriza_comunicaciones = fields.Boolean(missing=True)
    acepta_responsabilidad_civil = fields.Boolean(missing=True)
    
    # Contacto de emergencia
    contacto_emergencia_nombre = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    contacto_emergencia_telefono = TrimmedString(
        required=True,
        validate=validate.Length(min=7, max=15)
    )
    
    contacto_emergencia_relacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'padre', 'madre', 'hermano', 'hermana', 'abuelo', 'abuela',
            'tio', 'tia', 'primo', 'vecino', 'amigo_familia', 'otro'
        ])
    )
    
    # Información adicional para menores
    autorizacion_recoger = fields.List(
        fields.Dict(keys=fields.String(), values=fields.String()),
        missing=[]
    )
    
    restricciones_entrega = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Evaluación inicial
    evaluacion_conocimientos_previos = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'basico', 'nulo'])
    )
    
    observaciones_evaluacion_inicial = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    requiere_nivelacion = fields.Boolean(missing=False)
    temas_nivelacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Seguimiento y observaciones
    observaciones_inscripcion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    recomendaciones_catequista = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Control administrativo
    numero_inscripcion = TrimmedString(
        allow_none=True,  # Se genera automáticamente
        validate=validate.Length(min=5, max=20)
    )
    
    @validates_schema
    def validate_inscripcion(self, data, **kwargs):
        """Validaciones específicas de inscripción."""
        # Validar fechas
        fecha_inscripcion = data.get('fecha_inscripcion')
        fecha_inicio = data.get('fecha_inicio_clases')
        fecha_fin = data.get('fecha_fin_estimada')
        
        if fecha_inicio and fecha_inscripcion and fecha_inicio < fecha_inscripcion:
            raise ValidationError({'fecha_inicio_clases': 'La fecha de inicio no puede ser anterior a la inscripción'})
        
        if fecha_fin and fecha_inicio and fecha_fin <= fecha_inicio:
            raise ValidationError({'fecha_fin_estimada': 'La fecha de fin debe ser posterior al inicio'})
        
        # Validar beca
        solicita_beca = data.get('solicita_beca', False)
        justificacion_beca = data.get('justificacion_beca')
        
        if solicita_beca and not justificacion_beca:
            raise ValidationError({'justificacion_beca': 'Debe justificar la solicitud de beca'})
        
        # Validar atención especial
        requiere_atencion = data.get('requiere_atencion_especial', False)
        descripcion_atencion = data.get('descripcion_atencion_especial')
        
        if requiere_atencion and not descripcion_atencion:
            raise ValidationError({'descripcion_atencion_especial': 'Debe describir el tipo de atención especial'})
        
        # Calcular monto total
        costo_total = data.get('costo_total_inscripcion', 0)
        costo_materiales = data.get('costo_materiales', 0)
        otros_costos = data.get('otros_costos', 0)
        descuento = data.get('descuento_aplicado', 0)
        
        data['monto_total_pagar'] = costo_total + costo_materiales + otros_costos - descuento


@register_schema('inscripcion_update')
class InscripcionUpdateSchema(BaseSchema):
    """Schema para actualización de inscripciones."""
    
    # No se puede cambiar catequizando_id, nivel_id, ni parroquia_id
    grupo_id = PositiveInteger(allow_none=True)
    
    # Fechas
    fecha_inicio_clases = fields.Date(allow_none=True)
    fecha_fin_estimada = fields.Date(allow_none=True)
    
    # Estado
    estado_inscripcion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'pendiente', 'pre_inscrita', 'confirmada', 'activa',
            'suspendida', 'retirada', 'completada', 'transferida', 'cancelada'
        ])
    )
    
    # Preferencias
    preferencia_horario = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mañana', 'tarde', 'noche', 'cualquiera'])
    )
    preferencia_dia = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo', 'cualquiera'
        ])
    )
    
    # Atención especial
    requiere_atencion_especial = fields.Boolean(allow_none=True)
    tipo_atencion_especial = TrimmedString(allow_none=True)
    descripcion_atencion_especial = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Financiero
    descuento_aplicado = NonNegativeDecimal(allow_none=True, places=2)
    beca_aprobada = fields.Boolean(allow_none=True)
    porcentaje_beca = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    # Documentación
    documentos_entregados = fields.List(fields.String(), allow_none=True)
    documentos_pendientes = fields.List(fields.String(), allow_none=True)
    
    # Autorizaciones
    autoriza_fotos_videos = fields.Boolean(allow_none=True)
    autoriza_salidas_pedagogicas = fields.Boolean(allow_none=True)
    autoriza_comunicaciones = fields.Boolean(allow_none=True)
    acepta_responsabilidad_civil = fields.Boolean(allow_none=True)
    
    # Contacto emergencia
    contacto_emergencia_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    contacto_emergencia_telefono = TrimmedString(allow_none=True, validate=validate.Length(min=7, max=15))
    contacto_emergencia_relacion = TrimmedString(allow_none=True)
    
    # Evaluación
    evaluacion_conocimientos_previos = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'basico', 'nulo'])
    )
    observaciones_evaluacion_inicial = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    requiere_nivelacion = fields.Boolean(allow_none=True)
    temas_nivelacion = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Observaciones
    observaciones_inscripcion = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    recomendaciones_catequista = TrimmedString(allow_none=True, validate=validate.Length(max=500))


@register_schema('inscripcion_response')
class InscripcionResponseSchema(BaseSchema):
    """Schema para respuesta de inscripción."""
    
    # Información básica
    id = PositiveInteger(required=True)
    numero_inscripcion = TrimmedString(required=True)
    
    # Referencias
    catequizando_id = PositiveInteger(required=True)
    catequizando_nombre = TrimmedString(dump_only=True, required=True)
    nivel_id = PositiveInteger(required=True)
    nivel_nombre = TrimmedString(dump_only=True, required=True)
    grupo_id = PositiveInteger(allow_none=True)
    grupo_nombre = TrimmedString(dump_only=True, allow_none=True)
    parroquia_id = PositiveInteger(required=True)
    parroquia_nombre = TrimmedString(dump_only=True, required=True)
    
    # Fechas
    fecha_inscripcion = fields.Date(required=True)
    fecha_inicio_clases = fields.Date(allow_none=True)
    fecha_fin_estimada = fields.Date(allow_none=True)
    duracion_estimada_semanas = PositiveInteger(dump_only=True, allow_none=True)
    
    # Estado
    estado_inscripcion = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    
    # Proceso de inscripción
    forma_inscripcion = TrimmedString(required=True)
    inscrito_por = TrimmedString(required=True)
    relacion_inscriptor = TrimmedString(required=True)
    relacion_inscriptor_display = TrimmedString(dump_only=True)
    
    # Motivación
    motivo_inscripcion = TrimmedString(required=True)
    motivo_inscripcion_display = TrimmedString(dump_only=True)
    descripcion_motivo = TrimmedString(allow_none=True)
    expectativas_catequesis = TrimmedString(allow_none=True)
    objetivos_personales = TrimmedString(allow_none=True)
    
    # Experiencia previa
    ha_recibido_catequesis_antes = fields.Boolean(required=True)
    lugar_catequesis_anterior = TrimmedString(allow_none=True)
    nivel_catequesis_anterior = TrimmedString(allow_none=True)
    año_catequesis_anterior = PositiveInteger(allow_none=True)
    motivo_no_continuidad = TrimmedString(allow_none=True)
    
    # Preferencias
    preferencia_horario = TrimmedString(allow_none=True)
    preferencia_dia = TrimmedString(allow_none=True)
    
    # Atención especial
    requiere_atencion_especial = fields.Boolean(required=True)
    tipo_atencion_especial = TrimmedString(allow_none=True)
    descripcion_atencion_especial = TrimmedString(allow_none=True)
    
    # Información financiera
    costo_total_inscripcion = NonNegativeDecimal(required=True, places=2)
    costo_materiales = NonNegativeDecimal(required=True, places=2)
    otros_costos = NonNegativeDecimal(required=True, places=2)
    descuento_aplicado = NonNegativeDecimal(required=True, places=2)
    monto_total_pagar = NonNegativeDecimal(required=True, places=2)
    
    # Becas
    solicita_beca = fields.Boolean(required=True)
    tipo_beca_solicitada = TrimmedString(allow_none=True)
    justificacion_beca = TrimmedString(allow_none=True)
    beca_aprobada = fields.Boolean(allow_none=True)
    porcentaje_beca = NonNegativeDecimal(allow_none=True, places=1)
    monto_beca = NonNegativeDecimal(dump_only=True, places=2, allow_none=True)
    
    # Documentación
    documentos_entregados = fields.List(fields.String(), missing=[])
    documentos_pendientes = fields.List(fields.String(), missing=[])
    documentacion_completa = fields.Boolean(dump_only=True)
    porcentaje_documentacion = NonNegativeDecimal(dump_only=True, places=1)
    
    # Compromisos
    acepta_reglamento = fields.Boolean(required=True)
    autoriza_fotos_videos = fields.Boolean(required=True)
    autoriza_salidas_pedagogicas = fields.Boolean(required=True)
    autoriza_comunicaciones = fields.Boolean(required=True)
    acepta_responsabilidad_civil = fields.Boolean(required=True)
    
    # Contacto emergencia
    contacto_emergencia_nombre = TrimmedString(required=True)
    contacto_emergencia_telefono = TrimmedString(required=True)
    contacto_emergencia_relacion = TrimmedString(required=True)
    
    # Evaluación inicial
    evaluacion_conocimientos_previos = TrimmedString(allow_none=True)
    observaciones_evaluacion_inicial = TrimmedString(allow_none=True)
    requiere_nivelacion = fields.Boolean(required=True)
    temas_nivelacion = TrimmedString(allow_none=True)
    
    # Estado académico
    porcentaje_avance = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    sesiones_asistidas = NonNegativeInteger(dump_only=True, allow_none=True)
    total_sesiones = NonNegativeInteger(dump_only=True, allow_none=True)
    porcentaje_asistencia = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    calificacion_promedio = NonNegativeDecimal(dump_only=True, places=2, allow_none=True)
    
    # Observaciones
    observaciones_inscripcion = TrimmedString(allow_none=True)
    recomendaciones_catequista = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('cambio_estado_inscripcion')
class CambioEstadoInscripcionSchema(BaseSchema):
    """Schema para cambios de estado de inscripción."""
    
    inscripcion_id = PositiveInteger(required=True)
    nuevo_estado = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'confirmada', 'activa', 'suspendida', 'retirada',
            'completada', 'transferida', 'cancelada'
        ])
    )
    
    motivo_cambio = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    fecha_efectiva = fields.Date(required=True, missing=date.today)
    autorizado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    # Información específica según el cambio
    fecha_retorno_estimada = fields.Date(allow_none=True)  # Para suspensiones
    parroquia_destino_id = PositiveInteger(allow_none=True)  # Para transferencias
    calificacion_final = NonNegativeDecimal(
        allow_none=True,
        places=2,
        validate=validate.Range(min=0, max=5)
    )  # Para completadas
    
    @validates_schema
    def validate_cambio_estado(self, data, **kwargs):
        """Validaciones específicas del cambio de estado."""
        nuevo_estado = data.get('nuevo_estado')
        
        if nuevo_estado == 'suspendida':
            fecha_retorno = data.get('fecha_retorno_estimada')
            if not fecha_retorno:
                raise ValidationError({'fecha_retorno_estimada': 'Fecha de retorno requerida para suspensiones'})
        
        if nuevo_estado == 'transferida':
            parroquia_destino = data.get('parroquia_destino_id')
            if not parroquia_destino:
                raise ValidationError({'parroquia_destino_id': 'Parroquia destino requerida para transferencias'})
        
        if nuevo_estado == 'completada':
            calificacion = data.get('calificacion_final')
            if not calificacion:
                raise ValidationError({'calificacion_final': 'Calificación final requerida para completar'})


@register_schema('inscripcion_search')
class InscripcionSearchSchema(BaseSchema):
    """Schema para búsqueda de inscripciones."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    numero_inscripcion = TrimmedString(allow_none=True)
    catequizando_id = PositiveInteger(allow_none=True)
    nivel_id = PositiveInteger(allow_none=True)
    grupo_id = PositiveInteger(allow_none=True)
    parroquia_id = PositiveInteger(allow_none=True)
    
    # Filtros de estado
    estado_inscripcion = TrimmedString(allow_none=True)
    estados_incluir = fields.List(fields.String(), allow_none=True)
    
    # Filtros de fecha
    fecha_inscripcion_desde = fields.Date(allow_none=True)
    fecha_inscripcion_hasta = fields.Date(allow_none=True)
    año_inscripcion = PositiveInteger(allow_none=True)
    
    # Filtros académicos
    requiere_nivelacion = fields.Boolean(allow_none=True)
    documentacion_completa = fields.Boolean(allow_none=True)
    ha_recibido_catequesis_antes = fields.Boolean(allow_none=True)
    
    # Filtros especiales
    requiere_atencion_especial = fields.Boolean(allow_none=True)
    tipo_atencion_especial = TrimmedString(allow_none=True)
    
    # Filtros financieros
    solicita_beca = fields.Boolean(allow_none=True)
    beca_aprobada = fields.Boolean(allow_none=True)
    monto_pendiente_pago = fields.Boolean(allow_none=True)
    
    # Filtros de proceso
    forma_inscripcion = TrimmedString(allow_none=True)
    inscrito_por_terceros = fields.Boolean(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_inscripcion',
        validate=validate.OneOf([
            'fecha_inscripcion', 'numero_inscripcion', 'catequizando_nombre',
            'nivel_nombre', 'estado_inscripcion', 'monto_total_pagar'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('inscripcion_stats')
class InscripcionStatsSchema(BaseSchema):
    """Schema para estadísticas de inscripciones."""
    
    total_inscripciones = NonNegativeInteger(required=True)
    inscripciones_activas = NonNegativeInteger(required=True)
    nuevas_este_mes = NonNegativeInteger(required=True)
    nuevas_este_año = NonNegativeInteger(required=True)
    
    # Por estado
    por_estado = fields.Dict(required=True)
    
    # Tendencias
    por_mes_año_actual = fields.List(fields.Dict())
    por_año = fields.List(fields.Dict())
    
    # Por nivel y programa
    por_nivel = fields.List(fields.Dict())
    por_tipo_programa = fields.Dict(required=True)
    
    # Por parroquia
    por_parroquia = fields.List(fields.Dict())
    
    # Financiero
    ingresos_totales = NonNegativeDecimal(required=True, places=2)
    ingresos_este_mes = NonNegativeDecimal(required=True, places=2)
    becas_otorgadas = NonNegativeInteger(required=True)
    monto_becas = NonNegativeDecimal(required=True, places=2)
    pendientes_pago = NonNegativeInteger(required=True)
    
    # Documentación
    documentacion_completa = NonNegativeInteger(required=True)
    documentacion_pendiente = NonNegativeInteger(required=True)
    
    # Atención especial
    requieren_atencion_especial = NonNegativeInteger(required=True)
    por_tipo_atencion = fields.List(fields.Dict())
    
    # Experiencia previa
    con_experiencia_previa = NonNegativeInteger(required=True)
    sin_experiencia = NonNegativeInteger(required=True)
    
    # Completación
    tasa_completacion = NonNegativeDecimal(required=True, places=1)
    promedio_duracion_dias = NonNegativeDecimal(required=True, places=1)
    
    # Top inscripciones
    niveles_mas_demandados = fields.List(fields.Dict())
    parroquias_mas_inscripciones = fields.List(fields.Dict())


@register_schema('inscripcion_masiva')
class InscripcionMasivaSchema(BaseSchema):
    """Schema para inscripciones masivas."""
    
    nivel_id = PositiveInteger(required=True)
    parroquia_id = PositiveInteger(required=True)
    grupo_id = PositiveInteger(allow_none=True)
    
    catequizandos_ids = fields.List(
        PositiveInteger(),
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    
    fecha_inscripcion = fields.Date(required=True, missing=date.today)
    fecha_inicio_clases = fields.Date(allow_none=True)
    
    # Configuraciones comunes
    costo_total_inscripcion = NonNegativeDecimal(required=True, places=2)
    costo_materiales = NonNegativeDecimal(missing=0, places=2)
    
    forma_inscripcion = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'virtual', 'telefonica', 'masiva'])
    )
    
    inscrito_por = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    # Configuraciones por defecto
    motivo_inscripcion_defecto = TrimmedString(
        missing='formacion_religiosa',
        validate=validate.OneOf([
            'preparacion_sacramento', 'formacion_religiosa', 'tradicion_familiar',
            'crecimiento_espiritual', 'valores_cristianos', 'comunidad_fe'
        ])
    )
    
    autoriza_fotos_videos_defecto = fields.Boolean(missing=True)
    autoriza_salidas_pedagogicas_defecto = fields.Boolean(missing=True)
    autoriza_comunicaciones_defecto = fields.Boolean(missing=True)
    
    observaciones_generales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_inscripcion_masiva(self, data, **kwargs):
        """Validaciones para inscripción masiva."""
        catequizandos = data.get('catequizandos_ids', [])
        if len(set(catequizandos)) != len(catequizandos):
            raise ValidationError({'catequizandos_ids': 'No se pueden repetir catequizandos en la lista'})