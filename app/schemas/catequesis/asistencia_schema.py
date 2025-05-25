"""
Schemas de asistencia para el sistema de catequesis.
Maneja validaciones para registro de asistencia y seguimiento académico.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date, time
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('asistencia_create')
class AsistenciaCreateSchema(BaseSchema):
    """Schema para registro de asistencia."""
    
    # Referencias principales
    catequizando_id = PositiveInteger(required=True)
    sesion_id = PositiveInteger(required=True)
    grupo_id = PositiveInteger(required=True)
    fecha_sesion = fields.Date(required=True)
    
    # Asistencia básica
    asistio = fields.Boolean(required=True)
    llego_tarde = fields.Boolean(missing=False)
    minutos_retraso = NonNegativeInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=120)
    )
    
    se_retiro_temprano = fields.Boolean(missing=False)
    minutos_antes_salida = NonNegativeInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=120)
    )
    
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
    
    # Participación en clase
    nivel_participacion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'bajo', 'no_participó'])
    )
    
    aportes_destacados = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Comportamiento
    comportamiento = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'inadecuado'])
    )
    
    incidentes_comportamiento = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Tareas y materiales
    trajo_tarea = fields.Boolean(allow_none=True)
    calidad_tarea = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'buena', 'regular', 'deficiente', 'no_trajo'])
    )
    
    trajo_materiales = fields.Boolean(allow_none=True)
    materiales_faltantes = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Evaluación de la sesión
    calificacion_sesion = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    
    temas_dominados = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    temas_reforzar = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Necesidades especiales
    requirio_atencion_especial = fields.Boolean(missing=False)
    tipo_atencion_requerida = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'academica', 'comportamental', 'medica', 'emocional',
            'familiar', 'adaptacion_curricular', 'otro'
        ])
    )
    
    descripcion_atencion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Observaciones del catequista
    observaciones_catequista = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    recomendaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    # Seguimiento
    requiere_seguimiento = fields.Boolean(missing=False)
    tipo_seguimiento = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'academico', 'comportamental', 'familiar', 'medico', 'emocional', 'otro'
        ])
    )
    
    # Comunicación con padres
    comunicar_a_padres = fields.Boolean(missing=False)
    mensaje_padres = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
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
            data['nivel_participacion'] = None
            data['comportamiento'] = None
            data['trajo_tarea'] = None
            data['trajo_materiales'] = None
            data['calificacion_sesion'] = None
        else:
            # Si asistió, limpiar campos de inasistencia
            data['inasistencia_justificada'] = None
            data['motivo_inasistencia'] = None
            data['descripcion_motivo'] = None
        
        # Validar retraso
        llego_tarde = data.get('llego_tarde', False)
        minutos_retraso = data.get('minutos_retraso')
        
        if llego_tarde and not minutos_retraso:
            raise ValidationError({'minutos_retraso': 'Debe especificar minutos de retraso'})
        
        if not llego_tarde and minutos_retraso:
            data['minutos_retraso'] = None
        
        # Validar salida temprana
        retiro_temprano = data.get('se_retiro_temprano', False)
        minutos_antes = data.get('minutos_antes_salida')
        
        if retiro_temprano and not minutos_antes:
            raise ValidationError({'minutos_antes_salida': 'Debe especificar minutos antes de la salida'})
        
        if not retiro_temprano and minutos_antes:
            data['minutos_antes_salida'] = None


@register_schema('asistencia_update')
class AsistenciaUpdateSchema(BaseSchema):
    """Schema para actualización de asistencia."""
    
    # No se pueden cambiar referencias principales
    
    # Asistencia
    asistio = fields.Boolean(allow_none=True)
    llego_tarde = fields.Boolean(allow_none=True)
    minutos_retraso = NonNegativeInteger(allow_none=True, validate=validate.Range(min=1, max=120))
    se_retiro_temprano = fields.Boolean(allow_none=True)
    minutos_antes_salida = NonNegativeInteger(allow_none=True, validate=validate.Range(min=1, max=120))
    
    # Justificación
    inasistencia_justificada = fields.Boolean(allow_none=True)
    motivo_inasistencia = TrimmedString(allow_none=True)
    descripcion_motivo = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Participación
    nivel_participacion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'bajo', 'no_participó'])
    )
    aportes_destacados = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Comportamiento
    comportamiento = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'inadecuado'])
    )
    incidentes_comportamiento = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Tareas
    trajo_tarea = fields.Boolean(allow_none=True)
    calidad_tarea = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'buena', 'regular', 'deficiente', 'no_trajo'])
    )
    trajo_materiales = fields.Boolean(allow_none=True)
    materiales_faltantes = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Evaluación
    calificacion_sesion = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    temas_dominados = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    temas_reforzar = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Atención especial
    requirio_atencion_especial = fields.Boolean(allow_none=True)
    tipo_atencion_requerida = TrimmedString(allow_none=True)
    descripcion_atencion = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Observaciones
    observaciones_catequista = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    recomendaciones = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Seguimiento
    requiere_seguimiento = fields.Boolean(allow_none=True)
    tipo_seguimiento = TrimmedString(allow_none=True)
    
    # Comunicación
    comunicar_a_padres = fields.Boolean(allow_none=True)
    mensaje_padres = TrimmedString(allow_none=True, validate=validate.Length(max=300))


@register_schema('asistencia_response')
class AsistenciaResponseSchema(BaseSchema):
    """Schema para respuesta de asistencia."""
    
    # Información básica
    id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(required=True)
    catequizando_nombre = TrimmedString(dump_only=True, required=True)
    sesion_id = PositiveInteger(required=True)
    sesion_tema = TrimmedString(dump_only=True, allow_none=True)
    grupo_id = PositiveInteger(required=True)
    grupo_nombre = TrimmedString(dump_only=True, required=True)
    fecha_sesion = fields.Date(required=True)
    
    # Asistencia
    asistio = fields.Boolean(required=True)
    llego_tarde = fields.Boolean(required=True)
    minutos_retraso = NonNegativeInteger(allow_none=True)
    se_retiro_temprano = fields.Boolean(required=True)
    minutos_antes_salida = NonNegativeInteger(allow_none=True)
    tiempo_presencia_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Justificación
    inasistencia_justificada = fields.Boolean(allow_none=True)
    motivo_inasistencia = TrimmedString(allow_none=True)
    motivo_inasistencia_display = TrimmedString(dump_only=True, allow_none=True)
    descripcion_motivo = TrimmedString(allow_none=True)
    
    # Participación
    nivel_participacion = TrimmedString(allow_none=True)
    nivel_participacion_display = TrimmedString(dump_only=True, allow_none=True)
    aportes_destacados = TrimmedString(allow_none=True)
    
    # Comportamiento
    comportamiento = TrimmedString(allow_none=True)
    comportamiento_display = TrimmedString(dump_only=True, allow_none=True)
    incidentes_comportamiento = TrimmedString(allow_none=True)
    
    # Tareas y materiales
    trajo_tarea = fields.Boolean(allow_none=True)
    calidad_tarea = TrimmedString(allow_none=True)
    calidad_tarea_display = TrimmedString(dump_only=True, allow_none=True)
    trajo_materiales = fields.Boolean(allow_none=True)
    materiales_faltantes = TrimmedString(allow_none=True)
    
    # Evaluación
    calificacion_sesion = NonNegativeDecimal(allow_none=True, places=1)
    temas_dominados = TrimmedString(allow_none=True)
    temas_reforzar = TrimmedString(allow_none=True)
    
    # Atención especial
    requirio_atencion_especial = fields.Boolean(required=True)
    tipo_atencion_requerida = TrimmedString(allow_none=True)
    descripcion_atencion = TrimmedString(allow_none=True)
    
    # Observaciones
    observaciones_catequista = TrimmedString(allow_none=True)
    recomendaciones = TrimmedString(allow_none=True)
    
    # Seguimiento
    requiere_seguimiento = fields.Boolean(required=True)
    tipo_seguimiento = TrimmedString(allow_none=True)
    
    # Comunicación
    comunicar_a_padres = fields.Boolean(required=True)
    mensaje_padres = TrimmedString(allow_none=True)
    comunicacion_enviada = fields.Boolean(dump_only=True, missing=False)
    
    # Registrado por
    registrado_por = TrimmedString(dump_only=True, allow_none=True)
    
    # Fechas
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('asistencia_masiva')
class AsistenciaMasivaSchema(BaseSchema):
    """Schema para registro masivo de asistencia."""
    
    sesion_id = PositiveInteger(required=True)
    grupo_id = PositiveInteger(required=True)
    fecha_sesion = fields.Date(required=True)
    
    # Lista de asistencias
    asistencias = fields.List(
        fields.Dict(keys=fields.String(), values=fields.Raw()),
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    
    # Configuraciones por defecto
    registrado_por = TrimmedString(required=True, validate=validate.Length(min=3, max=100))
    
    # Observaciones generales para toda la sesión
    observaciones_sesion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    metodologia_usada = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'explicativa', 'participativa', 'ludica', 'narrativa',
            'experiencial', 'reflexiva', 'grupal', 'mixta'
        ])
    )
    
    recursos_utilizados = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    @validates_schema
    def validate_asistencia_masiva(self, data, **kwargs):
        """Validaciones para asistencia masiva."""
        asistencias = data.get('asistencias', [])
        
        # Verificar que no se repitan catequizandos
        catequizandos_ids = [a.get('catequizando_id') for a in asistencias]
        if len(set(catequizandos_ids)) != len(catequizandos_ids):
            raise ValidationError({'asistencias': 'No se pueden repetir catequizandos'})
        
        # Validar estructura de cada asistencia
        for i, asistencia in enumerate(asistencias):
            if 'catequizando_id' not in asistencia:
                raise ValidationError({f'asistencias.{i}': 'catequizando_id es requerido'})
            
            if 'asistio' not in asistencia:
                raise ValidationError({f'asistencias.{i}': 'asistio es requerido'})


@register_schema('reporte_asistencia')
class ReporteAsistenciaSchema(BaseSchema):
    """Schema para reportes de asistencia."""
    
    tipo_reporte = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'individual', 'grupo', 'nivel', 'parroquia',
            'catequista', 'periodo', 'comparativo'
        ])
    )
    
    # Filtros de tiempo
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    
    # Filtros de entidades
    catequizando_id = PositiveInteger(allow_none=True)
    grupo_id = PositiveInteger(allow_none=True)
    nivel_id = PositiveInteger(allow_none=True)
    parroquia_id = PositiveInteger(allow_none=True)
    catequista_id = PositiveInteger(allow_none=True)
    
    # Configuraciones del reporte
    incluir_estadisticas = fields.Boolean(missing=True)
    incluir_graficos = fields.Boolean(missing=True)
    incluir_observaciones = fields.Boolean(missing=False)
    incluir_recomendaciones = fields.Boolean(missing=False)
    
    # Agrupación y ordenamiento
    agrupar_por = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mes', 'semana', 'catequizando', 'grupo', 'nivel'])
    )
    
    ordenar_por = TrimmedString(
        missing='fecha_sesion',
        validate=validate.OneOf([
            'fecha_sesion', 'catequizando_nombre', 'porcentaje_asistencia',
            'calificacion_promedio'
        ])
    )
    
    formato_salida = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'excel', 'csv'])
    )
    
    @validates_schema
    def validate_reporte(self, data, **kwargs):
        """Validaciones para reporte de asistencia."""
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError({'fecha_fin': 'La fecha fin debe ser posterior a la inicio'})


@register_schema('asistencia_search')
class AsistenciaSearchSchema(BaseSchema):
    """Schema para búsqueda de asistencias."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    catequizando_id = PositiveInteger(allow_none=True)
    grupo_id = PositiveInteger(allow_none=True)
    sesion_id = PositiveInteger(allow_none=True)
    
    # Filtros de fecha
    fecha_desde = fields.Date(allow_none=True)
    fecha_hasta = fields.Date(allow_none=True)
    
    # Filtros de asistencia
    asistio = fields.Boolean(allow_none=True)
    llego_tarde = fields.Boolean(allow_none=True)
    inasistencia_justificada = fields.Boolean(allow_none=True)
    motivo_inasistencia = TrimmedString(allow_none=True)
    
    # Filtros de desempeño
    nivel_participacion = TrimmedString(allow_none=True)
    comportamiento = TrimmedString(allow_none=True)
    calificacion_minima = NonNegativeDecimal(allow_none=True, places=1)
    calificacion_maxima = NonNegativeDecimal(allow_none=True, places=1)
    
    # Filtros especiales
    requiere_seguimiento = fields.Boolean(allow_none=True)
    requirio_atencion_especial = fields.Boolean(allow_none=True)
    comunicar_a_padres = fields.Boolean(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_sesion',
        validate=validate.OneOf([
            'fecha_sesion', 'catequizando_nombre', 'calificacion_sesion',
            'nivel_participacion', 'comportamiento'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('asistencia_stats')
class AsistenciaStatsSchema(BaseSchema):
    """Schema para estadísticas de asistencia."""
    
    total_registros = NonNegativeInteger(required=True)
    total_asistencias = NonNegativeInteger(required=True)
    total_inasistencias = NonNegativeInteger(required=True)
    porcentaje_asistencia_general = NonNegativeDecimal(required=True, places=1)
    
    # Por motivos de inasistencia
    por_motivo_inasistencia = fields.Dict(required=True)
    inasistencias_justificadas = NonNegativeInteger(required=True)
    inasistencias_injustificadas = NonNegativeInteger(required=True)
    
    # Puntualidad
    llegadas_tarde = NonNegativeInteger(required=True)
    salidas_tempranas = NonNegativeInteger(required=True)
    porcentaje_puntualidad = NonNegativeDecimal(required=True, places=1)
    
    # Participación
    por_nivel_participacion = fields.Dict(required=True)
    participacion_promedio = TrimmedString(required=True)
    
    # Comportamiento
    por_comportamiento = fields.Dict(required=True)
    comportamiento_promedio = TrimmedString(required=True)
    
    # Evaluaciones
    calificacion_promedio_general = NonNegativeDecimal(required=True, places=2)
    por_rango_calificacion = fields.List(fields.Dict())
    
    # Seguimiento especial
    requieren_seguimiento = NonNegativeInteger(required=True)
    con_atencion_especial = NonNegativeInteger(required=True)
    comunicaciones_enviadas = NonNegativeInteger(required=True)
    
    # Tendencias temporales
    por_mes = fields.List(fields.Dict())
    por_dia_semana = fields.Dict(required=True)
    
    # Por grupos y niveles
    por_grupo = fields.List(fields.Dict())
    por_nivel = fields.List(fields.Dict())
    
    # Catequizandos destacados
    mejor_asistencia = fields.List(fields.Dict())
    mayor_participacion = fields.List(fields.Dict())
    requieren_atencion = fields.List(fields.Dict())