"""
Schemas de nivel de catequesis para el sistema.
Maneja validaciones para niveles, programas y estructuras curriculares.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, EnumField, register_schema,
    PositiveInteger, NonNegativeInteger, NonNegativeDecimal
)


@register_schema('nivel_create')
class NivelCreateSchema(BaseSchema):
    """Schema para creación de niveles de catequesis."""
    
    # Información básica
    nombre = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    codigo_nivel = TrimmedString(
        required=True,
        validate=[
            validate.Length(min=2, max=10),
            validate.Regexp(r'^[A-Z0-9\-]+$', error='Código debe contener solo letras mayúsculas, números y guiones')
        ]
    )
    
    descripcion = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    # Clasificación
    tipo_programa = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'primera_comunion', 'confirmacion', 'bautismo', 'matrimonio',
            'catequesis_familiar', 'catequesis_adultos', 'formacion_catequistas',
            'preparacion_sacramental', 'otro'
        ])
    )
    
    modalidad = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'virtual', 'mixta', 'autodirigida'])
    )
    
    # Estructura del programa
    orden_secuencial = PositiveInteger(required=True)
    es_obligatorio = fields.Boolean(missing=True)
    es_prerequisito = fields.Boolean(missing=False)
    nivel_prerequisito_id = PositiveInteger(allow_none=True)
    
    # Duración y temporalidad
    duracion_semanas = PositiveInteger(
        required=True,
        validate=validate.Range(min=1, max=104)  # máximo 2 años
    )
    sesiones_por_semana = PositiveInteger(
        required=True,
        validate=validate.Range(min=1, max=7)
    )
    duracion_sesion_minutos = PositiveInteger(
        required=True,
        validate=validate.Range(min=30, max=180)
    )
    
    # Edades objetivo
    edad_minima = PositiveInteger(
        required=True,
        validate=validate.Range(min=3, max=100)
    )
    edad_maxima = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=3, max=100)
    )
    
    # Capacidades
    tamaño_grupo_minimo = PositiveInteger(
        missing=5,
        validate=validate.Range(min=1, max=50)
    )
    tamaño_grupo_maximo = PositiveInteger(
        missing=25,
        validate=validate.Range(min=1, max=100)
    )
    
    # Requisitos
    requiere_padrinos = fields.Boolean(missing=False)
    requiere_documentos_especiales = fields.Boolean(missing=False)
    requiere_entrevista_previa = fields.Boolean(missing=False)
    requiere_retiro = fields.Boolean(missing=False)
    
    # Costo
    costo_inscripcion = NonNegativeDecimal(missing=0, places=2)
    costo_materiales = NonNegativeDecimal(missing=0, places=2)
    costo_certificado = NonNegativeDecimal(missing=0, places=2)
    
    # Certificación
    otorga_certificado = fields.Boolean(missing=True)
    tipo_certificado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'participacion', 'aprovechamiento', 'sacramento', 'formacion', 'especializacion'
        ])
    )
    
    # Estado
    is_active = fields.Boolean(missing=True)
    acepta_inscripciones = fields.Boolean(missing=True)
    
    # Información adicional
    objetivos_generales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    metodologia = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    recursos_necesarios = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    @validates_schema
    def validate_nivel(self, data, **kwargs):
        """Validaciones específicas del nivel."""
        # Validar edades
        edad_min = data.get('edad_minima')
        edad_max = data.get('edad_maxima')
        
        if edad_max and edad_min and edad_max <= edad_min:
            raise ValidationError({'edad_maxima': 'La edad máxima debe ser mayor a la mínima'})
        
        # Validar tamaños de grupo
        min_grupo = data.get('tamaño_grupo_minimo', 5)
        max_grupo = data.get('tamaño_grupo_maximo', 25)
        
        if max_grupo <= min_grupo:
            raise ValidationError({'tamaño_grupo_maximo': 'El tamaño máximo debe ser mayor al mínimo'})
        
        # Validar prerequisito
        prerequisito_id = data.get('nivel_prerequisito_id')
        es_prerequisito = data.get('es_prerequisito', False)
        
        if es_prerequisito and prerequisito_id:
            raise ValidationError({'nivel_prerequisito_id': 'Un nivel no puede tener prerequisito y ser prerequisito al mismo tiempo'})


@register_schema('nivel_update')
class NivelUpdateSchema(BaseSchema):
    """Schema para actualización de niveles."""
    
    # Información básica (no se puede cambiar código)
    nombre = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=100))
    descripcion = TrimmedString(allow_none=True, validate=validate.Length(min=10, max=500))
    
    # Clasificación
    modalidad = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['presencial', 'virtual', 'mixta', 'autodirigida'])
    )
    
    # Estructura
    es_obligatorio = fields.Boolean(allow_none=True)
    nivel_prerequisito_id = PositiveInteger(allow_none=True)
    
    # Duración
    duracion_semanas = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=104)
    )
    sesiones_por_semana = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=7)
    )
    duracion_sesion_minutos = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=30, max=180)
    )
    
    # Edades
    edad_minima = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=3, max=100)
    )
    edad_maxima = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=3, max=100)
    )
    
    # Capacidades
    tamaño_grupo_minimo = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=50)
    )
    tamaño_grupo_maximo = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=100)
    )
    
    # Requisitos
    requiere_padrinos = fields.Boolean(allow_none=True)
    requiere_documentos_especiales = fields.Boolean(allow_none=True)
    requiere_entrevista_previa = fields.Boolean(allow_none=True)
    requiere_retiro = fields.Boolean(allow_none=True)
    
    # Costos
    costo_inscripcion = NonNegativeDecimal(allow_none=True, places=2)
    costo_materiales = NonNegativeDecimal(allow_none=True, places=2)
    costo_certificado = NonNegativeDecimal(allow_none=True, places=2)
    
    # Certificación
    otorga_certificado = fields.Boolean(allow_none=True)
    tipo_certificado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'participacion', 'aprovechamiento', 'sacramento', 'formacion', 'especializacion'
        ])
    )
    
    # Estado
    acepta_inscripciones = fields.Boolean(allow_none=True)
    
    # Información adicional
    objetivos_generales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    metodologia = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    recursos_necesarios = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))


@register_schema('nivel_response')
class NivelResponseSchema(BaseSchema):
    """Schema para respuesta de nivel."""
    
    # Información básica
    id = PositiveInteger(required=True)
    nombre = TrimmedString(required=True)
    codigo_nivel = TrimmedString(required=True)
    descripcion = TrimmedString(required=True)
    
    # Clasificación
    tipo_programa = TrimmedString(required=True)
    tipo_programa_display = TrimmedString(dump_only=True)
    modalidad = TrimmedString(required=True)
    modalidad_display = TrimmedString(dump_only=True)
    
    # Estructura
    orden_secuencial = PositiveInteger(required=True)
    es_obligatorio = fields.Boolean(required=True)
    es_prerequisito = fields.Boolean(required=True)
    nivel_prerequisito_id = PositiveInteger(allow_none=True)
    nivel_prerequisito_nombre = TrimmedString(dump_only=True, allow_none=True)
    
    # Duración
    duracion_semanas = PositiveInteger(required=True)
    sesiones_por_semana = PositiveInteger(required=True)
    duracion_sesion_minutos = PositiveInteger(required=True)
    total_sesiones = PositiveInteger(dump_only=True)
    total_horas = NonNegativeDecimal(dump_only=True, places=1)
    
    # Edades
    edad_minima = PositiveInteger(required=True)
    edad_maxima = PositiveInteger(allow_none=True)
    rango_edad_display = TrimmedString(dump_only=True)
    
    # Capacidades
    tamaño_grupo_minimo = PositiveInteger(required=True)
    tamaño_grupo_maximo = PositiveInteger(required=True)
    
    # Requisitos
    requiere_padrinos = fields.Boolean(required=True)
    requiere_documentos_especiales = fields.Boolean(required=True)
    requiere_entrevista_previa = fields.Boolean(required=True)
    requiere_retiro = fields.Boolean(required=True)
    
    # Costos
    costo_inscripcion = NonNegativeDecimal(required=True, places=2)
    costo_materiales = NonNegativeDecimal(required=True, places=2)
    costo_certificado = NonNegativeDecimal(required=True, places=2)
    costo_total = NonNegativeDecimal(dump_only=True, places=2)
    
    # Certificación
    otorga_certificado = fields.Boolean(required=True)
    tipo_certificado = TrimmedString(allow_none=True)
    tipo_certificado_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Estado
    is_active = fields.Boolean(required=True)
    acepta_inscripciones = fields.Boolean(required=True)
    
    # Estadísticas
    total_inscritos = NonNegativeInteger(dump_only=True)
    total_grupos_activos = NonNegativeInteger(dump_only=True)
    total_catequistas = NonNegativeInteger(dump_only=True)
    porcentaje_completacion = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    
    # Información adicional
    objetivos_generales = TrimmedString(allow_none=True)
    metodologia = TrimmedString(allow_none=True)
    recursos_necesarios = TrimmedString(allow_none=True)
    observaciones = TrimmedString(allow_none=True)
    
    # Fechas
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('contenido_nivel')
class ContenidoNivelSchema(BaseSchema):
    """Schema para contenidos de un nivel."""
    
    id = PositiveInteger(dump_only=True)
    nivel_id = PositiveInteger(required=True)
    
    # Información del contenido
    numero_sesion = PositiveInteger(required=True)
    titulo_sesion = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=200)
    )
    
    objetivo_sesion = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    contenido_teorico = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=2000)
    )
    
    actividades_sugeridas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    recursos_necesarios = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Evaluación
    criterios_evaluacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    actividades_casa = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Referencias
    citas_biblicas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    referencias_catecismo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    material_complementario = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Estado
    is_obligatorio = fields.Boolean(missing=True)
    is_active = fields.Boolean(missing=True)
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=300))


@register_schema('evaluacion_nivel')
class EvaluacionNivelSchema(BaseSchema):
    """Schema para evaluaciones de nivel."""
    
    id = PositiveInteger(dump_only=True)
    nivel_id = PositiveInteger(required=True)
    
    nombre_evaluacion = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    tipo_evaluacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'diagnostica', 'formativa', 'sumativa', 'final',
            'practica', 'oral', 'escrita', 'proyecto'
        ])
    )
    
    momento_aplicacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['inicio', 'proceso', 'intermedia', 'final'])
    )
    
    # Configuración
    es_obligatoria = fields.Boolean(missing=True)
    valor_porcentual = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    nota_minima_aprobacion = NonNegativeDecimal(
        missing=3.0,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    
    # Contenido
    competencias_evaluar = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=1000)
    )
    
    descripcion_actividad = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1500)
    )
    
    criterios_calificacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    # Tiempo
    duracion_minutos = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=15, max=180)
    )
    
    # Estado
    is_active = fields.Boolean(missing=True)
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=300))


@register_schema('nivel_search')
class NivelSearchSchema(BaseSchema):
    """Schema para búsqueda de niveles."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros
    tipo_programa = TrimmedString(allow_none=True)
    modalidad = TrimmedString(allow_none=True)
    is_active = fields.Boolean(allow_none=True)
    acepta_inscripciones = fields.Boolean(allow_none=True)
    
    # Filtros de edad
    edad_objetivo = PositiveInteger(allow_none=True)
    edad_minima_filtro = PositiveInteger(allow_none=True)
    edad_maxima_filtro = PositiveInteger(allow_none=True)
    
    # Filtros de duración
    duracion_minima_semanas = PositiveInteger(allow_none=True)
    duracion_maxima_semanas = PositiveInteger(allow_none=True)
    
    # Filtros de costo
    costo_maximo = NonNegativeDecimal(allow_none=True, places=2)
    
    # Filtros de requisitos
    requiere_padrinos = fields.Boolean(allow_none=True)
    requiere_retiro = fields.Boolean(allow_none=True)
    otorga_certificado = fields.Boolean(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='orden_secuencial',
        validate=validate.OneOf([
            'nombre', 'orden_secuencial', 'duracion_semanas',
            'edad_minima', 'costo_total', 'total_inscritos'
        ])
    )
    sort_order = TrimmedString(missing='asc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('nivel_stats')
class NivelStatsSchema(BaseSchema):
    """Schema para estadísticas de niveles."""
    
    total_niveles = NonNegativeInteger(required=True)
    niveles_activos = NonNegativeInteger(required=True)
    niveles_con_inscripciones = NonNegativeInteger(required=True)
    
    # Por tipo de programa
    por_tipo_programa = fields.List(fields.Dict())
    por_modalidad = fields.List(fields.Dict())
    
    # Inscripciones
    total_inscritos_todos_niveles = NonNegativeInteger(required=True)
    promedio_inscritos_por_nivel = NonNegativeDecimal(required=True, places=1)
    
    # Completación
    porcentaje_completacion_promedio = NonNegativeDecimal(required=True, places=1)
    
    # Costos
    costo_promedio_inscripcion = NonNegativeDecimal(required=True, places=2)
    costo_promedio_total = NonNegativeDecimal(required=True, places=2)
    
    # Duración
    duracion_promedio_semanas = NonNegativeDecimal(required=True, places=1)
    
    # Más populares
    niveles_mas_demandados = fields.List(fields.Nested(NivelResponseSchema))
    niveles_mejor_completacion = fields.List(fields.Nested(NivelResponseSchema))


@register_schema('nivel_prerequisito')
class NivelPrerequisitoSchema(BaseSchema):
    """Schema para gestión de prerequisitos entre niveles."""
    
    nivel_id = PositiveInteger(required=True)
    prerequisito_id = PositiveInteger(required=True)
    
    # Tipo de prerequisito
    tipo_prerequisito = TrimmedString(
        required=True,
        validate=validate.OneOf(['obligatorio', 'recomendado', 'equivalente'])
    )
    
    # Validación de prerequisito
    requiere_aprobacion = fields.Boolean(missing=True)
    nota_minima_requerida = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    
    porcentaje_asistencia_requerido = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    # Flexibilidad
    permite_convalidacion = fields.Boolean(missing=False)
    permite_examen_suficiencia = fields.Boolean(missing=False)
    
    # Estado
    is_active = fields.Boolean(missing=True)
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    @validates_schema
    def validate_prerequisito(self, data, **kwargs):
        """Valida que un nivel no sea prerequisito de sí mismo."""
        nivel_id = data.get('nivel_id')
        prerequisito_id = data.get('prerequisito_id')
        
        if nivel_id == prerequisito_id:
            raise ValidationError('Un nivel no puede ser prerequisito de sí mismo')


@register_schema('nivel_programa_completo')
class NivelProgramaCompletoSchema(BaseSchema):
    """Schema para programas completos de catequesis."""
    
    id = PositiveInteger(dump_only=True)
    nombre_programa = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    descripcion_programa = TrimmedString(
        required=True,
        validate=validate.Length(min=20, max=1000)
    )
    
    tipo_programa = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'primera_comunion', 'confirmacion', 'bautismo', 'matrimonio',
            'catequesis_familiar', 'catequesis_adultos', 'formacion_catequistas'
        ])
    )
    
    # Configuración del programa
    niveles_incluidos = fields.List(PositiveInteger(), required=True)
    orden_niveles = fields.List(PositiveInteger(), required=True)
    
    # Duración total
    duracion_total_semanas = PositiveInteger(dump_only=True)
    costo_total_programa = NonNegativeDecimal(dump_only=True, places=2)
    
    # Requisitos del programa completo
    edad_minima_ingreso = PositiveInteger(required=True)
    edad_maxima_ingreso = PositiveInteger(allow_none=True)
    
    documentos_requeridos = fields.List(fields.String(), missing=[])
    requisitos_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    # Certificación final
    certificado_final = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=100)
    )
    
    autoridad_certificadora = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=100)
    )
    
    # Estado
    is_active = fields.Boolean(missing=True)
    acepta_inscripciones = fields.Boolean(missing=True)
    
    # Estadísticas
    total_inscritos_programa = NonNegativeInteger(dump_only=True)
    porcentaje_completacion_programa = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))