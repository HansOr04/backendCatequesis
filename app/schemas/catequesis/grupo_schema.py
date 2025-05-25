"""
Schemas de grupo para el sistema de catequesis.
Maneja validaciones para grupos, horarios, asistencia y actividades.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date, time
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('grupo_create')
class GrupoCreateSchema(BaseSchema):
    """Schema para creación de grupos."""
    
    # Información básica
    nombre = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=150)
    )
    
    codigo_grupo = TrimmedString(
        allow_none=True,  # Se puede generar automáticamente
        validate=[
            validate.Length(min=3, max=15),
            validate.Regexp(r'^GRP-[A-Z0-9\-]+$', error='Código debe tener formato GRP-XXXX')
        ]
    )
    
    descripcion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Asociaciones
    nivel_id = PositiveInteger(required=True)
    parroquia_id = PositiveInteger(required=True)
    sede_id = PositiveInteger(allow_none=True)
    salon_id = PositiveInteger(allow_none=True)
    
    # Catequista principal (requerido)
    catequista_principal_id = PositiveInteger(required=True)
    
    # Fechas del periodo
    fecha_inicio = fields.Date(required=True)
    fecha_fin_estimada = fields.Date(required=True)
    fecha_fin_real = fields.Date(allow_none=True)
    
    # Horarios
    dia_semana = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'
        ])
    )
    
    hora_inicio = fields.Time(required=True)
    hora_fin = fields.Time(required=True)
    
    # Configuración del grupo
    capacidad_maxima = PositiveInteger(
        required=True,
        validate=validate.Range(min=5, max=50)
    )
    
    edad_minima = PositiveInteger(
        required=True,
        validate=validate.Range(min=3, max=100)
    )
    
    edad_maxima = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=3, max=100)
    )
    
    # Modalidad y metodología
    modalidad = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'virtual', 'mixta'])
    )
    
    metodologia_principal = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'tradicional', 'montessori', 'waldorf', 'participativa',
            'experiencial', 'narrativa', 'ludica', 'mixta'
        ])
    )
    
    # Requisitos de inscripción
    requiere_entrevista = fields.Boolean(missing=False)
    requiere_documentos_especiales = fields.Boolean(missing=False)
    permite_inscripciones_tardias = fields.Boolean(missing=True)
    fecha_limite_inscripciones = fields.Date(allow_none=True)
    
    # Costo
    costo_inscripcion = NonNegativeDecimal(missing=0, places=2)
    costo_materiales = NonNegativeDecimal(missing=0, places=2)
    incluye_refrigerio = fields.Boolean(missing=False)
    costo_refrigerio = NonNegativeDecimal(missing=0, places=2)
    
    # Configuraciones especiales
    atiende_necesidades_especiales = fields.Boolean(missing=False)
    tipos_necesidades_especiales = fields.List(
        fields.String(validate=validate.OneOf([
            'discapacidad_fisica', 'discapacidad_cognitiva', 'discapacidad_sensorial',
            'trastornos_aprendizaje', 'trastornos_conducta', 'autismo', 'otra'
        ])),
        missing=[]
    )
    
    # Estado
    estado_grupo = TrimmedString(
        required=True,
        missing='planificado',
        validate=validate.OneOf([
            'planificado', 'abierto_inscripciones', 'en_curso',
            'suspendido', 'finalizado', 'cancelado'
        ])
    )
    
    acepta_inscripciones = fields.Boolean(missing=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_grupo(self, data, **kwargs):
        """Validaciones específicas del grupo."""
        # Validar fechas
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin_est = data.get('fecha_fin_estimada')
        fecha_limite_insc = data.get('fecha_limite_inscripciones')
        
        if fecha_inicio and fecha_fin_est and fecha_fin_est <= fecha_inicio:
            raise ValidationError({'fecha_fin_estimada': 'La fecha de fin debe ser posterior al inicio'})
        
        if fecha_limite_insc and fecha_inicio and fecha_limite_insc > fecha_inicio:
            raise ValidationError({'fecha_limite_inscripciones': 'El límite de inscripciones debe ser antes del inicio'})
        
        # Validar horarios
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        
        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise ValidationError({'hora_fin': 'La hora de fin debe ser posterior al inicio'})
        
        # Validar edades
        edad_min = data.get('edad_minima')
        edad_max = data.get('edad_maxima')
        
        if edad_max and edad_min and edad_max <= edad_min:
            raise ValidationError({'edad_maxima': 'La edad máxima debe ser mayor a la mínima'})
        
        # Validar necesidades especiales
        atiende_especiales = data.get('atiende_necesidades_especiales', False)
        tipos_especiales = data.get('tipos_necesidades_especiales', [])
        
        if atiende_especiales and not tipos_especiales:
            raise ValidationError({'tipos_necesidades_especiales': 'Debe especificar los tipos de necesidades que atiende'})


@register_schema('grupo_update')
class GrupoUpdateSchema(BaseSchema):
    """Schema para actualización de grupos."""
    
    # Información básica (no se puede cambiar código ni nivel)
    nombre = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=150))
    descripcion = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Asociaciones (sede y salón se pueden cambiar)
    sede_id = PositiveInteger(allow_none=True)
    salon_id = PositiveInteger(allow_none=True)
    
    # Fechas (solo algunas modificables)
    fecha_fin_estimada = fields.Date(allow_none=True)
    fecha_fin_real = fields.Date(allow_none=True)
    fecha_limite_inscripciones = fields.Date(allow_none=True)
    
    # Horarios
    dia_semana = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'
        ])
    )
    hora_inicio = fields.Time(allow_none=True)
    hora_fin = fields.Time(allow_none=True)
    
    # Configuración
    capacidad_maxima = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=5, max=50)
    )
    
    # Modalidad
    modalidad = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['presencial', 'virtual', 'mixta'])
    )
    metodologia_principal = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'tradicional', 'montessori', 'waldorf', 'participativa',
            'experiencial', 'narrativa', 'ludica', 'mixta'
        ])
    )
    
    # Requisitos
    requiere_entrevista = fields.Boolean(allow_none=True)
    requiere_documentos_especiales = fields.Boolean(allow_none=True)
    permite_inscripciones_tardias = fields.Boolean(allow_none=True)
    
    # Costos
    costo_inscripcion = NonNegativeDecimal(allow_none=True, places=2)
    costo_materiales = NonNegativeDecimal(allow_none=True, places=2)
    incluye_refrigerio = fields.Boolean(allow_none=True)
    costo_refrigerio = NonNegativeDecimal(allow_none=True, places=2)
    
    # Necesidades especiales
    atiende_necesidades_especiales = fields.Boolean(allow_none=True)
    tipos_necesidades_especiales = fields.List(fields.String(), allow_none=True)
    
    # Estado
    estado_grupo = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'planificado', 'abierto_inscripciones', 'en_curso',
            'suspendido', 'finalizado', 'cancelado'
        ])
    )
    acepta_inscripciones = fields.Boolean(allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('grupo_response')
class GrupoResponseSchema(BaseSchema):
    """Schema para respuesta de grupo."""
    
    # Información básica
    id = PositiveInteger(required=True)
    nombre = TrimmedString(required=True)
    codigo_grupo = TrimmedString(required=True)
    descripcion = TrimmedString(allow_none=True)
    
    # Asociaciones
    nivel_id = PositiveInteger(required=True)
    nivel_nombre = TrimmedString(dump_only=True, required=True)
    parroquia_id = PositiveInteger(required=True)
    parroquia_nombre = TrimmedString(dump_only=True, required=True)
    sede_id = PositiveInteger(allow_none=True)
    sede_nombre = TrimmedString(dump_only=True, allow_none=True)
    salon_id = PositiveInteger(allow_none=True)
    salon_nombre = TrimmedString(dump_only=True, allow_none=True)
    
    # Catequistas
    catequista_principal_id = PositiveInteger(required=True)
    catequista_principal_nombre = TrimmedString(dump_only=True, required=True)
    catequistas_auxiliares = fields.List(fields.Dict(), dump_only=True)
    total_catequistas = NonNegativeInteger(dump_only=True)
    
    # Fechas
    fecha_inicio = fields.Date(required=True)
    fecha_fin_estimada = fields.Date(required=True)
    fecha_fin_real = fields.Date(allow_none=True)
    duracion_semanas = PositiveInteger(dump_only=True)
    semanas_transcurridas = NonNegativeInteger(dump_only=True)
    porcentaje_avance = NonNegativeDecimal(dump_only=True, places=1)
    
    # Horarios
    dia_semana = TrimmedString(required=True)
    dia_semana_display = TrimmedString(dump_only=True)
    hora_inicio = fields.Time(required=True)
    hora_fin = fields.Time(required=True)
    horario_display = TrimmedString(dump_only=True)
    duracion_sesion_minutos = PositiveInteger(dump_only=True)
    
    # Configuración
    capacidad_maxima = PositiveInteger(required=True)
    edad_minima = PositiveInteger(required=True)
    edad_maxima = PositiveInteger(allow_none=True)
    rango_edad_display = TrimmedString(dump_only=True)
    
    # Modalidad
    modalidad = TrimmedString(required=True)
    modalidad_display = TrimmedString(dump_only=True)
    metodologia_principal = TrimmedString(required=True)
    metodologia_display = TrimmedString(dump_only=True)
    
    # Inscripciones
    total_inscritos = NonNegativeInteger(dump_only=True)
    inscritos_activos = NonNegativeInteger(dump_only=True)
    lista_espera = NonNegativeInteger(dump_only=True)
    cupos_disponibles = NonNegativeInteger(dump_only=True)
    porcentaje_ocupacion = NonNegativeDecimal(dump_only=True, places=1)
    
    # Requisitos
    requiere_entrevista = fields.Boolean(required=True)
    requiere_documentos_especiales = fields.Boolean(required=True)
    permite_inscripciones_tardias = fields.Boolean(required=True)
    fecha_limite_inscripciones = fields.Date(allow_none=True)
    
    # Costos
    costo_inscripcion = NonNegativeDecimal(required=True, places=2)
    costo_materiales = NonNegativeDecimal(required=True, places=2)
    incluye_refrigerio = fields.Boolean(required=True)
    costo_refrigerio = NonNegativeDecimal(required=True, places=2)
    costo_total = NonNegativeDecimal(dump_only=True, places=2)
    
    # Necesidades especiales
    atiende_necesidades_especiales = fields.Boolean(required=True)
    tipos_necesidades_especiales = fields.List(fields.String(), missing=[])
    catequizandos_necesidades_especiales = NonNegativeInteger(dump_only=True)
    
    # Estado
    estado_grupo = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    acepta_inscripciones = fields.Boolean(required=True)
    is_active = fields.Boolean(required=True)
    
    # Estadísticas académicas
    sesiones_programadas = NonNegativeInteger(dump_only=True)
    sesiones_realizadas = NonNegativeInteger(dump_only=True)
    porcentaje_asistencia_promedio = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    calificacion_promedio = NonNegativeDecimal(dump_only=True, places=2, allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('sesion_grupo')
class SesionGrupoSchema(BaseSchema):
    """Schema para sesiones de grupo."""
    
    id = PositiveInteger(dump_only=True)
    grupo_id = PositiveInteger(required=True)
    
    # Información de la sesión
    numero_sesion = PositiveInteger(required=True)
    fecha_sesion = fields.Date(required=True)
    hora_inicio_real = fields.Time(allow_none=True)
    hora_fin_real = fields.Time(allow_none=True)
    
    # Tema y contenido
    tema_sesion = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    objetivo_sesion = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    contenido_desarrollado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=2000)
    )
    
    # Metodología aplicada
    metodologia_usada = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'explicativa', 'participativa', 'ludica', 'narrativa',
            'experiencial', 'reflexiva', 'grupal', 'individual', 'mixta'
        ])
    )
    actividades_realizadas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    recursos_utilizados = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Asistencia
    catequizandos_programados = NonNegativeInteger(required=True)
    catequizandos_asistieron = NonNegativeInteger(required=True)
    catequizandos_justificaron = NonNegativeInteger(missing=0)
    porcentaje_asistencia = NonNegativeDecimal(dump_only=True, places=1)
    
    # Evaluación de la sesión
    cumplimiento_objetivo = TrimmedString(
        required=True,
        validate=validate.OneOf(['completo', 'parcial', 'minimo', 'no_cumplido'])
    )
    nivel_participacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'bajo'])
    )
    
    # Catequista(s)
    catequista_principal = PositiveInteger(required=True)
    catequistas_auxiliares = fields.List(PositiveInteger(), missing=[])
    
    # Estado de la sesión
    estado_sesion = TrimmedString(
        required=True,
        missing='programada',
        validate=validate.OneOf(['programada', 'realizada', 'suspendida', 'cancelada', 'reprogramada'])
    )
    
    # Observaciones y seguimiento
    observaciones_generales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    dificultades_encontradas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    recomendaciones_proxima = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Tareas asignadas
    tarea_asignada = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    fecha_entrega_tarea = fields.Date(allow_none=True)
    
    @validates_schema
    def validate_sesion(self, data, **kwargs):
        """Validaciones específicas de sesión."""
        # Validar horarios reales
        hora_inicio = data.get('hora_inicio_real')
        hora_fin = data.get('hora_fin_real')
        
        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise ValidationError({'hora_fin_real': 'La hora de fin debe ser posterior al inicio'})
        
        # Validar asistencia
        programados = data.get('catequizandos_programados', 0)
        asistieron = data.get('catequizandos_asistieron', 0)
        justificaron = data.get('catequizandos_justificaron', 0)
        
        if asistieron > programados:
            raise ValidationError({'catequizandos_asistieron': 'No pueden asistir más de los programados'})
        
        if justificaron > (programados - asistieron):
            raise ValidationError({'catequizandos_justificaron': 'Justificaciones exceden inasistencias'})


@register_schema('asistencia_catequizando')
class AsistenciaCatequizandoSchema(BaseSchema):
    """Schema para asistencia individual de catequizandos."""
    
    id = PositiveInteger(dump_only=True)
    sesion_id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(required=True)
    
    # Asistencia
    asistio = fields.Boolean(required=True)
    llego_tarde = fields.Boolean(missing=False)
    minutos_retraso = NonNegativeInteger(allow_none=True)
    se_retiro_temprano = fields.Boolean(missing=False)
    minutos_antes_salida = NonNegativeInteger(allow_none=True)
    
    # Justificación de inasistencia
    inasistencia_justificada = fields.Boolean(allow_none=True)
    motivo_inasistencia = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'enfermedad', 'viaje_familiar', 'compromiso_escolar',
            'emergencia_familiar', 'clima_adverso', 'transporte',
            'otro_compromiso', 'sin_justificar', 'otro'
        ])
    )
    descripcion_motivo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Participación y comportamiento
    nivel_participacion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'bajo', 'no_participó'])
    )
    comportamiento = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'inadecuado'])
    )
    
    # Tareas y materiales
    trajo_tarea = fields.Boolean(allow_none=True)
    calidad_tarea = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'buena', 'regular', 'deficiente', 'no_trajo'])
    )
    trajo_materiales = fields.Boolean(allow_none=True)
    
    # Observaciones específicas
    observaciones_catequista = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    requiere_seguimiento = fields.Boolean(missing=False)
    tipo_seguimiento = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'academico', 'comportamental', 'familiar', 'medico', 'emocional', 'otro'
        ])
    )
    
    @validates_schema
    def validate_asistencia(self, data, **kwargs):
        """Validaciones específicas de asistencia."""
        asistio = data.get('asistio', False)
        
        # Si no asistió, limpiar campos de participación
        if not asistio:
            data['llego_tarde'] = False
            data['minutos_retraso'] = None
            data['se_retiro_temprano'] = False
            data['minutos_antes_salida'] = None
            
            # Debe tener motivo si no está justificada
            justificada = data.get('inasistencia_justificada', False)
            motivo = data.get('motivo_inasistencia')
            
            if not justificada and not motivo:
                data['motivo_inasistencia'] = 'sin_justificar'
        else:
            # Si asistió, limpiar campos de inasistencia
            data['inasistencia_justificada'] = None
            data['motivo_inasistencia'] = None
            data['descripcion_motivo'] = None


@register_schema('actividad_grupo')
class ActividadGrupoSchema(BaseSchema):
    """Schema para actividades especiales del grupo."""
    
    id = PositiveInteger(dump_only=True)
    grupo_id = PositiveInteger(required=True)
    
    # Información de la actividad
    nombre_actividad = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    tipo_actividad = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'salida_pedagogica', 'retiro', 'convivencia', 'celebracion',
            'servicio_social', 'liturgia_especial', 'taller_padres',
            'proyecto_comunitario', 'actividad_recreativa', 'evaluacion', 'otro'
        ])
    )
    descripcion = TrimmedString(
        required=True,
        validate=validate.Length(min=20, max=1000)
    )
    
    # Fechas y horarios
    fecha_actividad = fields.Date(required=True)
    hora_inicio = fields.Time(required=True)
    hora_fin_estimada = fields.Time(required=True)
    hora_fin_real = fields.Time(allow_none=True)
    
    # Lugar
    lugar_actividad = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=300)
    )
    direccion_lugar = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    requiere_transporte = fields.Boolean(missing=False)
    
    # Responsables
    responsable_principal = PositiveInteger(required=True)
    responsables_apoyo = fields.List(PositiveInteger(), missing=[])
    
    # Participación
    dirigida_a = TrimmedString(
        required=True,
        validate=validate.OneOf(['catequizandos', 'padres', 'familias', 'catequistas', 'todos'])
    )
    participacion_obligatoria = fields.Boolean(missing=False)
    requiere_autorizacion_padres = fields.Boolean(missing=True)
    
    # Costos
    tiene_costo = fields.Boolean(missing=False)
    costo_actividad = NonNegativeDecimal(missing=0, places=2)
    incluye_alimentacion = fields.Boolean(missing=False)
    incluye_transporte = fields.Boolean(missing=False)
    incluye_materiales = fields.Boolean(missing=True)
    
    # Requisitos
    edad_minima_participacion = PositiveInteger(allow_none=True)
    requisitos_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    materiales_necesarios = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Estado
    estado_actividad = TrimmedString(
        required=True,
        missing='planificada',
        validate=validate.OneOf(['planificada', 'confirmada', 'realizada', 'suspendida', 'cancelada'])
    )
    
    # Resultados
    participantes_confirmados = NonNegativeInteger(allow_none=True)
    participantes_reales = NonNegativeInteger(allow_none=True)
    
    # Evaluación
    evaluacion_actividad = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'buena', 'regular', 'deficiente'])
    )
    objetivos_cumplidos = fields.Boolean(allow_none=True)
    
    # Observaciones
    observaciones_planificacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    observaciones_realizacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    recomendaciones_futuras = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_actividad(self, data, **kwargs):
        """Validaciones específicas de actividad."""
        # Validar fechas y horarios
        fecha_actividad = data.get('fecha_actividad')
        if fecha_actividad and fecha_actividad < date.today():
            # Solo permitir fechas pasadas si es para registro histórico
            pass
        
        hora_inicio = data.get('hora_inicio')
        hora_fin_est = data.get('hora_fin_estimada')
        hora_fin_real = data.get('hora_fin_real')
        
        if hora_inicio and hora_fin_est and hora_fin_est <= hora_inicio:
            raise ValidationError({'hora_fin_estimada': 'La hora de fin debe ser posterior al inicio'})
        
        if hora_fin_real and hora_inicio and hora_fin_real <= hora_inicio:
            raise ValidationError({'hora_fin_real': 'La hora de fin real debe ser posterior al inicio'})
        
        # Validar costos
        tiene_costo = data.get('tiene_costo', False)
        costo = data.get('costo_actividad', 0)
        
        if tiene_costo and costo <= 0:
            raise ValidationError({'costo_actividad': 'Debe especificar un costo mayor a 0'})
        
        if not tiene_costo and costo > 0:
            raise ValidationError({'tiene_costo': 'Debe marcar que tiene costo si especifica un valor'})


@register_schema('grupo_search')
class GrupoSearchSchema(BaseSchema):
    """Schema para búsqueda de grupos."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    codigo_grupo = TrimmedString(allow_none=True)
    nivel_id = PositiveInteger(allow_none=True)
    parroquia_id = PositiveInteger(allow_none=True)
    catequista_id = PositiveInteger(allow_none=True)
    
    # Filtros de estado
    estado_grupo = TrimmedString(allow_none=True)
    acepta_inscripciones = fields.Boolean(allow_none=True)
    is_active = fields.Boolean(allow_none=True)
    
    # Filtros de horario
    dia_semana = TrimmedString(allow_none=True)
    modalidad = TrimmedString(allow_none=True)
    
    # Filtros de edad
    edad_objetivo = PositiveInteger(allow_none=True)
    edad_minima_filtro = PositiveInteger(allow_none=True)
    edad_maxima_filtro = PositiveInteger(allow_none=True)
    
    # Filtros de capacidad
    tiene_cupos_disponibles = fields.Boolean(allow_none=True)
    capacidad_minima = PositiveInteger(allow_none=True)
    porcentaje_ocupacion_max = NonNegativeDecimal(allow_none=True, places=1)
    
    # Filtros especiales
    atiende_necesidades_especiales = fields.Boolean(allow_none=True)
    permite_inscripciones_tardias = fields.Boolean(allow_none=True)
    
    # Filtros de costo
    costo_maximo = NonNegativeDecimal(allow_none=True, places=2)
    incluye_refrigerio = fields.Boolean(allow_none=True)
    
    # Filtros de fechas
    fecha_inicio_desde = fields.Date(allow_none=True)
    fecha_inicio_hasta = fields.Date(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='nombre',
        validate=validate.OneOf([
            'nombre', 'codigo_grupo', 'fecha_inicio', 'total_inscritos',
            'porcentaje_ocupacion', 'dia_semana', 'hora_inicio'
        ])
    )
    sort_order = TrimmedString(missing='asc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('grupo_stats')
class GrupoStatsSchema(BaseSchema):
    """Schema para estadísticas de grupos."""
    
    total_grupos = NonNegativeInteger(required=True)
    grupos_activos = NonNegativeInteger(required=True)
    grupos_en_curso = NonNegativeInteger(required=True)
    nuevos_grupos_año = NonNegativeInteger(required=True)
    
    # Por estado
    por_estado = fields.Dict(required=True)
    por_modalidad = fields.Dict(required=True)
    por_nivel = fields.List(fields.Dict())
    
    # Ocupación
    promedio_inscritos_por_grupo = NonNegativeDecimal(required=True, places=1)
    porcentaje_ocupacion_promedio = NonNegativeDecimal(required=True, places=1)
    grupos_con_cupos = NonNegativeInteger(required=True)
    grupos_llenos = NonNegativeInteger(required=True)
    
    # Por horarios
    por_dia_semana = fields.Dict(required=True)
    por_jornada = fields.Dict(required=True)
    
    # Geográfico
    por_parroquia = fields.List(fields.Dict())
    por_municipio = fields.List(fields.Dict())
    
    # Necesidades especiales
    grupos_necesidades_especiales = NonNegativeInteger(required=True)
    catequizandos_necesidades_especiales = NonNegativeInteger(required=True)
    
    # Rendimiento
    porcentaje_asistencia_promedio = NonNegativeDecimal(required=True, places=1)
    grupos_excelente_asistencia = NonNegativeInteger(required=True)
    sesiones_promedio_realizadas = NonNegativeDecimal(required=True, places=1)
    
    # Top grupos
    mayor_asistencia = fields.List(fields.Nested(GrupoResponseSchema))
    mas_inscritos = fields.List(fields.Nested(GrupoResponseSchema))
    mejor_evaluados = fields.List(fields.Nested(GrupoResponseSchema))