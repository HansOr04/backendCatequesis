"""
Schemas de catequista para el sistema de catequesis.
Maneja validaciones para catequistas, formación y asignaciones.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date, time
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, DocumentoIdentidad, Telefono,
    FechaNacimiento, register_schema, PositiveInteger, NonNegativeInteger,
    NonNegativeDecimal
)


@register_schema('catequista_create')
class CatequistaCreateSchema(BaseSchema):
    """Schema para creación de catequistas."""
    
    # Información personal básica (heredada del usuario)
    user_id = PositiveInteger(required=True)
    
    # Código único del catequista
    codigo_catequista = TrimmedString(
        allow_none=True,  # Se puede generar automáticamente
        validate=[
            validate.Length(min=3, max=15),
            validate.Regexp(r'^CAT-[A-Z0-9\-]+$', error='Código debe tener formato CAT-XXXX')
        ]
    )
    
    # Información específica del catequista
    fecha_ingreso = fields.Date(required=True, missing=date.today)
    
    estado_catequista = TrimmedString(
        required=True,
        missing='activo',
        validate=validate.OneOf(['candidato', 'activo', 'inactivo', 'suspendido', 'retirado'])
    )
    
    # Formación y experiencia
    nivel_formacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'basico', 'intermedio', 'avanzado', 'especializado',
            'coordinador', 'formador', 'maestro'
        ])
    )
    
    años_experiencia = NonNegativeInteger(missing=0)
    
    experiencia_previa = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    # Especialidades y competencias
    especialidades = fields.List(
        fields.String(validate=validate.OneOf([
            'primera_comunion', 'confirmacion', 'bautismo', 'matrimonio',
            'catequesis_familiar', 'catequesis_adultos', 'necesidades_especiales',
            'pastoral_juvenil', 'liturgia', 'musica_liturgica', 'arte_sacro',
            'dinamicas_grupo', 'psicologia_infantil', 'otro'
        ])),
        missing=[]
    )
    
    habilidades_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Niveles que puede enseñar
    niveles_autorizados = fields.List(
        PositiveInteger(),
        missing=[]
    )
    
    # Disponibilidad
    disponibilidad_dias = fields.List(
        fields.String(validate=validate.OneOf([
            'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'
        ])),
        missing=[]
    )
    
    disponibilidad_horarios = fields.List(
        fields.String(validate=validate.OneOf([
            'mañana', 'tarde', 'noche'
        ])),
        missing=[]
    )
    
    disponibilidad_flexible = fields.Boolean(missing=False)
    
    # Límites de carga
    max_grupos_simultaneos = PositiveInteger(
        missing=2,
        validate=validate.Range(min=1, max=8)
    )
    
    max_catequizandos_total = PositiveInteger(
        missing=50,
        validate=validate.Range(min=5, max=200)
    )
    
    # Información académica/profesional
    profesion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    nivel_educativo = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'secundaria_completa', 'tecnico', 'tecnologo',
            'universitario_incompleto', 'universitario_completo',
            'especializacion', 'maestria', 'doctorado'
        ])
    )
    
    titulo_profesional = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    # Formación religiosa
    formacion_catequistica = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=1000)
    )
    
    cursos_realizados = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    certificaciones = fields.List(fields.String(), missing=[])
    
    # Referencias
    referencias_personales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    referencias_religiosas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Motivación y compromiso
    motivo_servicio = TrimmedString(
        required=True,
        validate=validate.Length(min=20, max=1000)
    )
    
    expectativas_ministerio = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    tiempo_compromiso_anos = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=20)
    )
    
    # Evaluación inicial
    evaluacion_inicial = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    recomendaciones_formacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Autorizaciones
    autoriza_verificacion_antecedentes = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe autorizar verificación de antecedentes')
    )
    
    acepta_codigo_conducta = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe aceptar el código de conducta')
    )
    
    # Observaciones
    observaciones_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_catequista(self, data, **kwargs):
        """Validaciones específicas del catequista."""
        # Validar coherencia de nivel de formación con experiencia
        nivel_formacion = data.get('nivel_formacion')
        años_experiencia = data.get('años_experiencia', 0)
        
        if nivel_formacion in ['avanzado', 'especializado'] and años_experiencia < 2:
            raise ValidationError({'años_experiencia': 'Se requiere al menos 2 años de experiencia para nivel avanzado'})
        
        if nivel_formacion in ['coordinador', 'formador', 'maestro'] and años_experiencia < 5:
            raise ValidationError({'años_experiencia': 'Se requiere al menos 5 años de experiencia para estos niveles'})
        
        # Validar disponibilidad
        dias = data.get('disponibilidad_dias', [])
        horarios = data.get('disponibilidad_horarios', [])
        
        if not dias and not data.get('disponibilidad_flexible', False):
            raise ValidationError({'disponibilidad_dias': 'Debe especificar disponibilidad de días o marcar como flexible'})
        
        if not horarios and not data.get('disponibilidad_flexible', False):
            raise ValidationError({'disponibilidad_horarios': 'Debe especificar disponibilidad de horarios o marcar como flexible'})


@register_schema('catequista_update')
class CatequistaUpdateSchema(BaseSchema):
    """Schema para actualización de catequistas."""
    
    # Estado (no se puede cambiar user_id ni código)
    estado_catequista = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['candidato', 'activo', 'inactivo', 'suspendido', 'retirado'])
    )
    
    # Formación y experiencia
    nivel_formacion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'basico', 'intermedio', 'avanzado', 'especializado',
            'coordinador', 'formador', 'maestro'
        ])
    )
    
    años_experiencia = NonNegativeInteger(allow_none=True)
    experiencia_previa = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    # Especialidades
    especialidades = fields.List(fields.String(), allow_none=True)
    habilidades_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    niveles_autorizados = fields.List(PositiveInteger(), allow_none=True)
    
    # Disponibilidad
    disponibilidad_dias = fields.List(fields.String(), allow_none=True)
    disponibilidad_horarios = fields.List(fields.String(), allow_none=True)
    disponibilidad_flexible = fields.Boolean(allow_none=True)
    
    # Límites
    max_grupos_simultaneos = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=8)
    )
    max_catequizandos_total = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=5, max=200)
    )
    
    # Información profesional
    profesion = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    titulo_profesional = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    
    # Formación religiosa
    formacion_catequistica = TrimmedString(allow_none=True, validate=validate.Length(min=10, max=1000))
    cursos_realizados = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    certificaciones = fields.List(fields.String(), allow_none=True)
    
    # Referencias
    referencias_personales = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    referencias_religiosas = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Compromiso
    tiempo_compromiso_anos = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=20)
    )
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('catequista_response')
class CatequistaResponseSchema(BaseSchema):
    """Schema para respuesta de catequista."""
    
    # Información básica
    id = PositiveInteger(required=True)
    user_id = PositiveInteger(required=True)
    codigo_catequista = TrimmedString(required=True)
    
    # Información del usuario relacionado
    nombres = TrimmedString(dump_only=True, required=True)
    apellidos = TrimmedString(dump_only=True, required=True)
    nombre_completo = TrimmedString(dump_only=True, required=True)
    email = Email(dump_only=True, required=True)
    telefono = TrimmedString(dump_only=True, allow_none=True)
    
    # Fechas importantes
    fecha_ingreso = fields.Date(required=True)
    años_servicio = NonNegativeDecimal(dump_only=True, places=1)
    
    # Estado y formación
    estado_catequista = TrimmedString(required=True)
    estado_display = TrimmedString(dump_only=True)
    nivel_formacion = TrimmedString(required=True)
    nivel_formacion_display = TrimmedString(dump_only=True)
    años_experiencia = NonNegativeInteger(required=True)
    
    # Especialidades y competencias
    especialidades = fields.List(fields.String(), missing=[])
    especialidades_display = fields.List(fields.String(), dump_only=True)
    habilidades_especiales = TrimmedString(allow_none=True)
    niveles_autorizados = fields.List(PositiveInteger(), missing=[])
    niveles_autorizados_nombres = fields.List(fields.String(), dump_only=True)
    
    # Disponibilidad
    disponibilidad_dias = fields.List(fields.String(), missing=[])
    disponibilidad_horarios = fields.List(fields.String(), missing=[])
    disponibilidad_flexible = fields.Boolean(required=True)
    disponibilidad_display = TrimmedString(dump_only=True)
    
    # Límites y capacidad
    max_grupos_simultaneos = PositiveInteger(required=True)
    max_catequizandos_total = PositiveInteger(required=True)
    grupos_actuales = NonNegativeInteger(dump_only=True)
    catequizandos_actuales = NonNegativeInteger(dump_only=True)
    carga_actual_porcentaje = NonNegativeDecimal(dump_only=True, places=1)
    
    # Información académica/profesional
    profesion = TrimmedString(allow_none=True)
    nivel_educativo = TrimmedString(required=True)
    titulo_profesional = TrimmedString(allow_none=True)
    
    # Formación religiosa
    formacion_catequistica = TrimmedString(required=True)
    cursos_realizados = TrimmedString(allow_none=True)
    certificaciones = fields.List(fields.String(), missing=[])
    
    # Evaluaciones y desempeño
    calificacion_promedio = NonNegativeDecimal(dump_only=True, places=2, allow_none=True)
    evaluaciones_realizadas = NonNegativeInteger(dump_only=True)
    ultima_evaluacion = fields.Date(dump_only=True, allow_none=True)
    
    # Estadísticas de servicio
    total_grupos_historicos = NonNegativeInteger(dump_only=True)
    total_catequizandos_historicos = NonNegativeInteger(dump_only=True)
    sesiones_impartidas = NonNegativeInteger(dump_only=True)
    porcentaje_asistencia = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    
    # Motivación y compromiso
    motivo_servicio = TrimmedString(required=True)
    expectativas_ministerio = TrimmedString(allow_none=True)
    tiempo_compromiso_anos = PositiveInteger(allow_none=True)
    
    # Referencias
    referencias_personales = TrimmedString(allow_none=True)
    referencias_religiosas = TrimmedString(allow_none=True)
    
    # Autorizaciones
    autoriza_verificacion_antecedentes = fields.Boolean(required=True)
    acepta_codigo_conducta = fields.Boolean(required=True)
    antecedentes_verificados = fields.Boolean(dump_only=True, missing=False)
    fecha_verificacion_antecedentes = fields.Date(dump_only=True, allow_none=True)
    
    # Estado
    is_active = fields.Boolean(required=True)
    puede_enseñar = fields.Boolean(dump_only=True)
    requiere_formacion_adicional = fields.Boolean(dump_only=True)
    
    # Observaciones
    evaluacion_inicial = TrimmedString(allow_none=True)
    recomendaciones_formacion = TrimmedString(allow_none=True)
    observaciones_especiales = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('asignacion_grupo')
class AsignacionGrupoSchema(BaseSchema):
    """Schema para asignación de catequista a grupo."""
    
    id = PositiveInteger(dump_only=True)
    catequista_id = PositiveInteger(required=True)
    grupo_id = PositiveInteger(required=True)
    
    # Tipo de asignación
    tipo_asignacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['principal', 'auxiliar', 'suplente', 'apoyo'])
    )
    
    # Fechas de vigencia
    fecha_inicio = fields.Date(required=True, missing=date.today)
    fecha_fin = fields.Date(allow_none=True)
    
    # Responsabilidades específicas
    responsabilidades = fields.List(
        fields.String(validate=validate.OneOf([
            'planificacion', 'enseñanza', 'evaluacion', 'seguimiento',
            'comunicacion_padres', 'disciplina', 'actividades_especiales',
            'materiales', 'asistencia', 'liturgia'
        ])),
        missing=['enseñanza']
    )
    
    # Porcentaje de participación (para auxiliares)
    porcentaje_participacion = NonNegativeDecimal(
        missing=100,
        places=1,
        validate=validate.Range(min=10, max=100)
    )
    
    # Estado de la asignación
    estado_asignacion = TrimmedString(
        required=True,
        missing='activa',
        validate=validate.OneOf(['propuesta', 'activa', 'suspendida', 'finalizada'])
    )
    
    # Motivos de cambio
    motivo_asignacion = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    motivo_finalizacion = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Autorizaciones
    autorizado_por = TrimmedString(allow_none=True)
    fecha_autorizacion = fields.Date(allow_none=True)
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    @validates_schema
    def validate_asignacion(self, data, **kwargs):
        """Validaciones específicas de asignación."""
        # Validar fechas
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_fin and fecha_inicio and fecha_fin <= fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de fin debe ser posterior al inicio'})
        
        # Validar porcentaje para auxiliares
        tipo = data.get('tipo_asignacion')
        porcentaje = data.get('porcentaje_participacion', 100)
        
        if tipo == 'principal' and porcentaje != 100:
            raise ValidationError({'porcentaje_participacion': 'El catequista principal debe tener 100% de participación'})


@register_schema('evaluacion_catequista')
class EvaluacionCatequistaSchema(BaseSchema):
    """Schema para evaluación de catequistas."""
    
    id = PositiveInteger(dump_only=True)
    catequista_id = PositiveInteger(required=True)
    evaluador_id = PositiveInteger(required=True)
    
    # Información de la evaluación
    periodo_evaluacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['trimestral', 'semestral', 'anual', 'especial'])
    )
    
    fecha_evaluacion = fields.Date(required=True, missing=date.today)
    fecha_periodo_inicio = fields.Date(required=True)
    fecha_periodo_fin = fields.Date(required=True)
    
    # Criterios de evaluación (escala 1-5)
    conocimiento_contenido = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    metodologia_enseñanza = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    manejo_grupo = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    comunicacion_efectiva = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    puntualidad_asistencia = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    relacion_catequizandos = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    comunicacion_padres = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    trabajo_equipo = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    compromiso_ministerio = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    crecimiento_espiritual = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=1, max=5)
    )
    
    # Calificación general (calculada)
    calificacion_general = NonNegativeDecimal(
        dump_only=True,
        places=2,
        validate=validate.Range(min=1, max=5)
    )
    
    # Observaciones detalladas
    fortalezas_destacadas = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=1000)
    )
    
    areas_mejora = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=1000)
    )
    
    recomendaciones_formacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    # Plan de mejoramiento
    requiere_plan_mejoramiento = fields.Boolean(missing=False)
    objetivos_mejoramiento = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    fecha_seguimiento = fields.Date(allow_none=True)
    
    # Reconocimientos
    merece_reconocimiento = fields.Boolean(missing=False)
    tipo_reconocimiento = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'felicitacion', 'mencion_honor', 'certificado_excelencia',
            'promocion', 'beca_formacion', 'delegacion_especial'
        ])
    )
    
    # Estado de la evaluación
    estado_evaluacion = TrimmedString(
        required=True,
        missing='borrador',
        validate=validate.OneOf(['borrador', 'finalizada', 'revisada', 'apelada'])
    )
    
    # Firmas y aprobaciones
    firma_evaluador = fields.Boolean(missing=False)
    firma_catequista = fields.Boolean(missing=False)
    fecha_firma_catequista = fields.Date(allow_none=True)
    
    observaciones_catequista = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    observaciones_generales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_evaluacion(self, data, **kwargs):
        """Validaciones específicas de evaluación."""
        # Validar periodo
        fecha_inicio = data.get('fecha_periodo_inicio')
        fecha_fin = data.get('fecha_periodo_fin')
        fecha_eval = data.get('fecha_evaluacion')
        
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError({'fecha_periodo_fin': 'La fecha de fin debe ser posterior al inicio'})
        
        if fecha_eval and fecha_fin and fecha_eval < fecha_fin:
            raise ValidationError({'fecha_evaluacion': 'La evaluación debe realizarse después del periodo evaluado'})
        
        # Validar plan de mejoramiento
        requiere_plan = data.get('requiere_plan_mejoramiento', False)
        objetivos = data.get('objetivos_mejoramiento')
        
        if requiere_plan and not objetivos:
            raise ValidationError({'objetivos_mejoramiento': 'Debe especificar objetivos si requiere plan de mejoramiento'})


@register_schema('formacion_catequista')
class FormacionCatequistaSchema(BaseSchema):
    """Schema para formación de catequistas."""
    
    id = PositiveInteger(dump_only=True)
    catequista_id = PositiveInteger(required=True)
    
    # Información del curso/formación
    nombre_curso = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    
    tipo_formacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'curso_basico', 'curso_avanzado', 'especializacion',
            'taller', 'seminario', 'congreso', 'retiro',
            'diplomado', 'certificacion', 'otro'
        ])
    )
    
    institucion_formadora = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=200)
    )
    
    # Fechas y duración
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    duracion_horas = PositiveInteger(required=True)
    
    modalidad = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'virtual', 'mixta'])
    )
    
    # Evaluación y certificación
    fue_aprobado = fields.Boolean(allow_none=True)
    calificacion_obtenida = NonNegativeDecimal(
        allow_none=True,
        places=2,
        validate=validate.Range(min=0, max=5)
    )
    
    calificacion_minima = NonNegativeDecimal(
        missing=3.0,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    
    certificado_obtenido = fields.Boolean(missing=False)
    numero_certificado = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    
    # Competencias desarrolladas
    competencias_desarrolladas = fields.List(fields.String(), missing=[])
    
    # Aplicabilidad
    aplicable_niveles = fields.List(PositiveInteger(), missing=[])
    
    # Observaciones
    descripcion_contenido = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    observaciones_catequista = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Financiamiento
    costo_formacion = NonNegativeDecimal(missing=0, places=2)
    financiado_por = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['catequista', 'parroquia', 'diocesis', 'beca', 'otro'])
    )
    
    @validates_schema
    def validate_formacion(self, data, **kwargs):
        """Validaciones específicas de formación."""
        # Validar fechas
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de fin debe ser posterior al inicio'})
        
        # Validar aprobación
        fue_aprobado = data.get('fue_aprobado')
        calificacion = data.get('calificacion_obtenida')
        minima = data.get('calificacion_minima', 3.0)
        
        if fue_aprobado is True and calificacion and calificacion < minima:
            raise ValidationError({'calificacion_obtenida': 'La calificación es menor a la mínima para aprobar'})


@register_schema('catequista_search')
class CatequistaSearchSchema(BaseSchema):
    """Schema para búsqueda de catequistas."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    codigo_catequista = TrimmedString(allow_none=True)
    estado_catequista = TrimmedString(allow_none=True)
    nivel_formacion = TrimmedString(allow_none=True)
    
    # Filtros de capacidad
    especialidad = TrimmedString(allow_none=True)
    nivel_autorizado_id = PositiveInteger(allow_none=True)
    disponible_asignacion = fields.Boolean(allow_none=True)
    
    # Filtros de experiencia
    años_experiencia_min = NonNegativeInteger(allow_none=True)
    años_experiencia_max = NonNegativeInteger(allow_none=True)
    
    # Filtros de disponibilidad
    disponible_dia = TrimmedString(allow_none=True)
    disponible_horario = TrimmedString(allow_none=True)
    disponibilidad_flexible = fields.Boolean(allow_none=True)
    
    # Filtros de desempeño
    calificacion_minima = NonNegativeDecimal(allow_none=True, places=1)
    requiere_formacion = fields.Boolean(allow_none=True)
    
    # Filtros de carga
    con_grupos_activos = fields.Boolean(allow_none=True)
    carga_maxima_porcentaje = NonNegativeDecimal(allow_none=True, places=1)
    
    # Filtros geográficos
    parroquia_id = PositiveInteger(allow_none=True)
    municipio = TrimmedString(allow_none=True)
    
    # Filtros de fechas
    ingreso_desde = fields.Date(allow_none=True)
    ingreso_hasta = fields.Date(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='nombre_completo',
        validate=validate.OneOf([
            'nombre_completo', 'codigo_catequista', 'fecha_ingreso',
            'nivel_formacion', 'años_experiencia', 'calificacion_promedio',
            'grupos_actuales', 'catequizandos_actuales'
        ])
    )
    sort_order = TrimmedString(missing='asc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('catequista_stats')
class CatequistaStatsSchema(BaseSchema):
    """Schema para estadísticas de catequistas."""
    
    total_catequistas = NonNegativeInteger(required=True)
    catequistas_activos = NonNegativeInteger(required=True)
    nuevos_este_año = NonNegativeInteger(required=True)
    
    # Por estado y nivel
    por_estado = fields.Dict(required=True)
    por_nivel_formacion = fields.Dict(required=True)
    por_especialidad = fields.List(fields.Dict())
    
    # Experiencia
    años_experiencia_promedio = NonNegativeDecimal(required=True, places=1)
    por_rango_experiencia = fields.List(fields.Dict())
    
    # Carga de trabajo
    promedio_grupos_por_catequista = NonNegativeDecimal(required=True, places=1)
    promedio_catequizandos_por_catequista = NonNegativeDecimal(required=True, places=1)
    catequistas_sobrecargados = NonNegativeInteger(required=True)
    catequistas_disponibles = NonNegativeInteger(required=True)
    
    # Desempeño
    calificacion_promedio_general = NonNegativeDecimal(required=True, places=2)
    catequistas_excelente_desempeño = NonNegativeInteger(required=True)
    catequistas_requieren_formacion = NonNegativeInteger(required=True)
    
    # Formación
    total_formaciones_año = NonNegativeInteger(required=True)
    promedio_horas_formacion = NonNegativeDecimal(required=True, places=1)
    catequistas_certificados = NonNegativeInteger(required=True)
    
    # Geográfico
    por_parroquia = fields.List(fields.Dict())
    por_municipio = fields.List(fields.Dict())
    
    # Top catequistas
    mejor_evaluados = fields.List(fields.Nested('CatequistaResponseSchema'))
    mas_experiencia = fields.List(fields.Nested('CatequistaResponseSchema'))
    mas_formacion = fields.List(fields.Nested('CatequistaResponseSchema'))