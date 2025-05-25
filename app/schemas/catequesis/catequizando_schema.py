"""
Schemas de catequizando para el sistema de catequesis.
Maneja validaciones para catequizandos, inscripciones y seguimiento académico.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, DocumentoIdentidad, Telefono,
    FechaNacimiento, register_schema, PositiveInteger, NonNegativeInteger,
    NonNegativeDecimal
)


@register_schema('catequizando_create')
class CatequizandoCreateSchema(BaseSchema):
    """Schema para creación de catequizandos."""
    
    # Información personal básica
    nombres = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    apellidos = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    documento_identidad = DocumentoIdentidad(required=True)
    tipo_documento = TrimmedString(
        required=True,
        validate=validate.OneOf(['RC', 'TI', 'CC', 'CE', 'PA'])
    )
    
    fecha_nacimiento = FechaNacimiento(required=True)
    lugar_nacimiento = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=150)
    )
    
    genero = TrimmedString(
        required=True,
        validate=validate.OneOf(['M', 'F'])
    )
    
    # Información familiar
    nombre_padre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=2, max=100)
    )
    
    nombre_madre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=2, max=100)
    )
    
    estado_civil_padres = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'casados_iglesia', 'casados_civil', 'union_libre',
            'separados', 'divorciados', 'viudo_viuda', 'soltero'
        ])
    )
    
    # Información de contacto
    telefono_contacto = Telefono(required=True)
    telefono_alternativo = Telefono(allow_none=True)
    email_contacto = Email(allow_none=True)
    
    # Dirección de residencia
    direccion_residencia = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=300)
    )
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    municipio = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    departamento = TrimmedString(required=True, validate=validate.Length(min=2, max=100))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Información académica/laboral
    institucion_educativa = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    grado_escolar = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    ocupacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    # Información religiosa
    fue_bautizado = fields.Boolean(allow_none=True)
    lugar_bautismo = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    fecha_bautismo = fields.Date(allow_none=True)
    
    hizo_primera_comunion = fields.Boolean(allow_none=True)
    lugar_primera_comunion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    fecha_primera_comunion = fields.Date(allow_none=True)
    
    fue_confirmado = fields.Boolean(allow_none=True)
    lugar_confirmacion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    fecha_confirmacion = fields.Date(allow_none=True)
    
    # Padrinos
    nombre_padrino = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    nombre_madrina = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    telefono_padrinos = Telefono(allow_none=True)
    
    # Información médica básica
    tiene_discapacidad = fields.Boolean(missing=False)
    tipo_discapacidad = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    requiere_atencion_especial = fields.Boolean(missing=False)
    medicamentos_regulares = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    alergias_conocidas = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    contacto_emergencia_medica = Telefono(allow_none=True)
    
    # Motivación y compromiso
    motivo_inscripcion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    experiencia_religiosa_previa = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Configuraciones
    autoriza_fotos = fields.Boolean(missing=True)
    autoriza_datos_personales = fields.Boolean(missing=True)
    acepta_reglamento = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe aceptar el reglamento')
    )
    
    # Observaciones
    observaciones_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_catequizando(self, data, **kwargs):
        """Validaciones específicas del catequizando."""
        # Validar edad mínima
        fecha_nac = data.get('fecha_nacimiento')
        if fecha_nac:
            edad = (date.today() - fecha_nac).days / 365.25
            if edad < 3:
                raise ValidationError({'fecha_nacimiento': 'El catequizando debe tener al menos 3 años'})
        
        # Validar fechas sacramentales
        fecha_bautismo = data.get('fecha_bautismo')
        fecha_comunion = data.get('fecha_primera_comunion')
        fecha_confirmacion = data.get('fecha_confirmacion')
        
        if fecha_bautismo and fecha_nac and fecha_bautismo < fecha_nac:
            raise ValidationError({'fecha_bautismo': 'La fecha de bautismo no puede ser anterior al nacimiento'})
        
        if fecha_comunion and fecha_bautismo and fecha_comunion < fecha_bautismo:
            raise ValidationError({'fecha_primera_comunion': 'La primera comunión debe ser posterior al bautismo'})
        
        if fecha_confirmacion and fecha_comunion and fecha_confirmacion < fecha_comunion:
            raise ValidationError({'fecha_confirmacion': 'La confirmación debe ser posterior a la primera comunión'})
        
        # Validar información de discapacidad
        tiene_discapacidad = data.get('tiene_discapacidad', False)
        tipo_discapacidad = data.get('tipo_discapacidad')
        
        if tiene_discapacidad and not tipo_discapacidad:
            raise ValidationError({'tipo_discapacidad': 'Debe especificar el tipo de discapacidad'})


@register_schema('catequizando_update')
class CatequizandoUpdateSchema(BaseSchema):
    """Schema para actualización de catequizandos."""
    
    # Información personal (documento e identidad no se pueden cambiar)
    nombres = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    apellidos = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    lugar_nacimiento = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=150))
    
    # Información familiar
    nombre_padre = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    nombre_madre = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    estado_civil_padres = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'casados_iglesia', 'casados_civil', 'union_libre',
            'separados', 'divorciados', 'viudo_viuda', 'soltero'
        ])
    )
    
    # Contacto
    telefono_contacto = Telefono(allow_none=True)
    telefono_alternativo = Telefono(allow_none=True)
    email_contacto = Email(allow_none=True)
    
    # Dirección
    direccion_residencia = TrimmedString(allow_none=True, validate=validate.Length(min=10, max=300))
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    municipio = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    departamento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Información académica/laboral
    institucion_educativa = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    grado_escolar = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    ocupacion = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Información religiosa (solo si no están registrados previamente)
    lugar_bautismo = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    lugar_primera_comunion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    lugar_confirmacion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Padrinos
    nombre_padrino = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    nombre_madrina = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    telefono_padrinos = Telefono(allow_none=True)
    
    # Información médica
    tipo_discapacidad = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    requiere_atencion_especial = fields.Boolean(allow_none=True)
    medicamentos_regulares = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    alergias_conocidas = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    contacto_emergencia_medica = Telefono(allow_none=True)
    
    # Configuraciones
    autoriza_fotos = fields.Boolean(allow_none=True)
    autoriza_datos_personales = fields.Boolean(allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('catequizando_response')
class CatequizandoResponseSchema(BaseSchema):
    """Schema para respuesta de catequizando."""
    
    # Información básica
    id = PositiveInteger(required=True)
    nombres = TrimmedString(required=True)
    apellidos = TrimmedString(required=True)
    nombre_completo = TrimmedString(dump_only=True)
    documento_identidad = TrimmedString(required=True)
    tipo_documento = TrimmedString(required=True)
    fecha_nacimiento = fields.Date(required=True)
    edad = PositiveInteger(dump_only=True)
    lugar_nacimiento = TrimmedString(required=True)
    genero = TrimmedString(required=True)
    
    # Información familiar
    nombre_padre = TrimmedString(allow_none=True)
    nombre_madre = TrimmedString(allow_none=True)
    estado_civil_padres = TrimmedString(allow_none=True)
    
    # Contacto
    telefono_contacto = TrimmedString(required=True)
    telefono_alternativo = TrimmedString(allow_none=True)
    email_contacto = Email(allow_none=True)
    
    # Dirección
    direccion_residencia = TrimmedString(required=True)
    direccion_completa = TrimmedString(dump_only=True)
    barrio = TrimmedString(allow_none=True)
    municipio = TrimmedString(required=True)
    departamento = TrimmedString(required=True)
    codigo_postal = TrimmedString(allow_none=True)
    
    # Información académica/laboral
    institucion_educativa = TrimmedString(allow_none=True)
    grado_escolar = TrimmedString(allow_none=True)
    ocupacion = TrimmedString(allow_none=True)
    
    # Información religiosa
    fue_bautizado = fields.Boolean(allow_none=True)
    lugar_bautismo = TrimmedString(allow_none=True)
    fecha_bautismo = fields.Date(allow_none=True)
    
    hizo_primera_comunion = fields.Boolean(allow_none=True)
    lugar_primera_comunion = TrimmedString(allow_none=True)
    fecha_primera_comunion = fields.Date(allow_none=True)
    
    fue_confirmado = fields.Boolean(allow_none=True)
    lugar_confirmacion = TrimmedString(allow_none=True)
    fecha_confirmacion = fields.Date(allow_none=True)
    
    # Padrinos
    nombre_padrino = TrimmedString(allow_none=True)
    nombre_madrina = TrimmedString(allow_none=True)
    telefono_padrinos = TrimmedString(allow_none=True)
    
    # Información médica
    tiene_discapacidad = fields.Boolean(required=True)
    tipo_discapacidad = TrimmedString(allow_none=True)
    requiere_atencion_especial = fields.Boolean(required=True)
    medicamentos_regulares = TrimmedString(allow_none=True)
    alergias_conocidas = TrimmedString(allow_none=True)
    contacto_emergencia_medica = TrimmedString(allow_none=True)
    
    # Estado académico
    estado_catequesis = TrimmedString(dump_only=True)
    nivel_actual = TrimmedString(dump_only=True, allow_none=True)
    grupo_actual = TrimmedString(dump_only=True, allow_none=True)
    porcentaje_avance = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    
    # Configuraciones
    autoriza_fotos = fields.Boolean(required=True)
    autoriza_datos_personales = fields.Boolean(required=True)
    acepta_reglamento = fields.Boolean(required=True)
    
    # Estado
    is_active = fields.Boolean(required=True)
    
    # Estadísticas
    total_inscripciones = NonNegativeInteger(dump_only=True)
    niveles_completados = NonNegativeInteger(dump_only=True)
    certificados_obtenidos = NonNegativeInteger(dump_only=True)
    
    # Observaciones
    motivo_inscripcion = TrimmedString(allow_none=True)
    experiencia_religiosa_previa = TrimmedString(allow_none=True)
    observaciones_especiales = TrimmedString(allow_none=True)
    
    # Fechas
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('catequizando_search')
class CatequizandoSearchSchema(BaseSchema):
    """Schema para búsqueda de catequizandos."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    documento_identidad = TrimmedString(allow_none=True)
    genero = TrimmedString(allow_none=True, validate=validate.OneOf(['M', 'F']))
    is_active = fields.Boolean(allow_none=True)
    
    # Filtros de edad
    edad_minima = PositiveInteger(allow_none=True, validate=validate.Range(min=3, max=100))
    edad_maxima = PositiveInteger(allow_none=True, validate=validate.Range(min=3, max=100))
    
    # Filtros geográficos
    municipio = TrimmedString(allow_none=True)
    departamento = TrimmedString(allow_none=True)
    barrio = TrimmedString(allow_none=True)
    
    # Filtros religiosos
    fue_bautizado = fields.Boolean(allow_none=True)
    hizo_primera_comunion = fields.Boolean(allow_none=True)
    fue_confirmado = fields.Boolean(allow_none=True)
    
    # Filtros de estado académico
    tiene_inscripcion_activa = fields.Boolean(allow_none=True)
    nivel_actual_id = PositiveInteger(allow_none=True)
    grupo_actual_id = PositiveInteger(allow_none=True)
    
    # Filtros especiales
    tiene_discapacidad = fields.Boolean(allow_none=True)
    requiere_atencion_especial = fields.Boolean(allow_none=True)
    
    # Fechas
    fecha_nacimiento_desde = fields.Date(allow_none=True)
    fecha_nacimiento_hasta = fields.Date(allow_none=True)
    inscrito_desde = fields.Date(allow_none=True)
    inscrito_hasta = fields.Date(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='nombre_completo',
        validate=validate.OneOf([
            'nombre_completo', 'documento_identidad', 'edad',
            'fecha_nacimiento', 'municipio', 'created_at'
        ])
    )
    sort_order = TrimmedString(missing='asc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('inscripcion_catequizando')
class InscripcionCatequizandoSchema(BaseSchema):
    """Schema para inscripción de catequizando."""
    
    id = PositiveInteger(dump_only=True)
    catequizando_id = PositiveInteger(required=True)
    nivel_id = PositiveInteger(required=True)
    grupo_id = PositiveInteger(allow_none=True)
    parroquia_id = PositiveInteger(required=True)
    
    # Fechas
    fecha_inscripcion = fields.Date(required=True, missing=date.today)
    fecha_inicio_clases = fields.Date(allow_none=True)
    fecha_fin_estimada = fields.Date(allow_none=True)
    fecha_fin_real = fields.Date(allow_none=True)
    
    # Estado de la inscripción
    estado_inscripcion = TrimmedString(
        required=True,
        missing='activa',
        validate=validate.OneOf([
            'pendiente', 'activa', 'suspendida', 'retirada',
            'completada', 'aplazada', 'transferida'
        ])
    )
    
    # Información académica
    calificacion_final = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    
    porcentaje_asistencia = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    sesiones_asistidas = NonNegativeInteger(allow_none=True)
    sesiones_programadas = NonNegativeInteger(allow_none=True)
    
    # Observaciones académicas
    fortalezas_observadas = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    areas_mejora = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    comportamiento_general = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'necesita_apoyo'])
    )
    
    # Información financiera
    costo_total = NonNegativeDecimal(required=True, places=2)
    monto_pagado = NonNegativeDecimal(missing=0, places=2)
    saldo_pendiente = NonNegativeDecimal(dump_only=True, places=2)
    tiene_beca = fields.Boolean(missing=False)
    porcentaje_beca = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    # Certificación
    certificado_emitido = fields.Boolean(missing=False)
    fecha_emision_certificado = fields.Date(allow_none=True)
    numero_certificado = TrimmedString(allow_none=True)
    
    # Motivos de cambio de estado
    motivo_suspension = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    motivo_retiro = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Observaciones generales
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    @validates_schema
    def validate_inscripcion(self, data, **kwargs):
        """Validaciones específicas de inscripción."""
        # Validar fechas
        fecha_inscripcion = data.get('fecha_inscripcion')
        fecha_inicio = data.get('fecha_inicio_clases')
        fecha_fin_est = data.get('fecha_fin_estimada')
        fecha_fin_real = data.get('fecha_fin_real')
        
        if fecha_inicio and fecha_inscripcion and fecha_inicio < fecha_inscripcion:
            raise ValidationError({'fecha_inicio_clases': 'La fecha de inicio no puede ser anterior a la inscripción'})
        
        if fecha_fin_est and fecha_inicio and fecha_fin_est <= fecha_inicio:
            raise ValidationError({'fecha_fin_estimada': 'La fecha de fin debe ser posterior al inicio'})
        
        if fecha_fin_real and fecha_inicio and fecha_fin_real < fecha_inicio:
            raise ValidationError({'fecha_fin_real': 'La fecha de fin real no puede ser anterior al inicio'})
        
        # Validar beca
        tiene_beca = data.get('tiene_beca', False)
        porcentaje_beca = data.get('porcentaje_beca')
        
        if tiene_beca and not porcentaje_beca:
            raise ValidationError({'porcentaje_beca': 'Debe especificar el porcentaje de beca'})
        
        if not tiene_beca and porcentaje_beca:
            raise ValidationError({'tiene_beca': 'Debe marcar que tiene beca si especifica porcentaje'})


@register_schema('seguimiento_academico')
class SeguimientoAcademicoSchema(BaseSchema):
    """Schema para seguimiento académico del catequizando."""
    
    id = PositiveInteger(dump_only=True)
    inscripcion_id = PositiveInteger(required=True)
    sesion_numero = PositiveInteger(required=True)
    fecha_sesion = fields.Date(required=True)
    
    # Asistencia
    asistio = fields.Boolean(required=True)
    llego_tarde = fields.Boolean(missing=False)
    minutos_retraso = NonNegativeInteger(allow_none=True)
    
    # Participación
    nivel_participacion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'bajo', 'no_participó'])
    )
    
    aportes_destacados = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Evaluación
    calificacion_sesion = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    
    cumplió_tareas = fields.Boolean(allow_none=True)
    trajo_materiales = fields.Boolean(allow_none=True)
    
    # Comportamiento
    comportamiento = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['excelente', 'bueno', 'regular', 'inadecuado'])
    )
    
    requirio_atencion_especial = fields.Boolean(missing=False)
    tipo_atencion_requerida = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Observaciones del catequista
    observaciones_catequista = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    recomendaciones = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Seguimiento a observaciones anteriores
    seguimiento_observaciones_previas = TrimmedString(allow_none=True, validate=validate.Length(max=300))


@register_schema('historial_academico')
class HistorialAcademicoSchema(BaseSchema):
    """Schema para historial académico completo."""
    
    catequizando_id = PositiveInteger(required=True)
    
    # Resumen general
    total_inscripciones = NonNegativeInteger(dump_only=True)
    niveles_completados = NonNegativeInteger(dump_only=True)
    niveles_en_progreso = NonNegativeInteger(dump_only=True)
    promedio_general = NonNegativeDecimal(dump_only=True, places=2, allow_none=True)
    porcentaje_asistencia_general = NonNegativeDecimal(dump_only=True, places=1, allow_none=True)
    
    # Sacramentos recibidos durante la catequesis
    sacramentos_recibidos = fields.List(fields.Dict(), dump_only=True)
    certificados_obtenidos = fields.List(fields.Dict(), dump_only=True)
    
    # Historial de inscripciones
    inscripciones = fields.List(fields.Nested(InscripcionCatequizandoSchema), dump_only=True)
    
    # Reconocimientos y logros
    reconocimientos = fields.List(fields.Dict(), dump_only=True)
    participacion_eventos = fields.List(fields.Dict(), dump_only=True)
    
    # Observaciones importantes
    observaciones_relevantes = TrimmedString(allow_none=True)
    recomendaciones_futuras = TrimmedString(allow_none=True)


@register_schema('catequizando_stats')
class CatequizandoStatsSchema(BaseSchema):
    """Schema para estadísticas de catequizandos."""
    
    total_catequizandos = NonNegativeInteger(required=True)
    catequizandos_activos = NonNegativeInteger(required=True)
    nuevos_este_año = NonNegativeInteger(required=True)
    
    # Por género
    por_genero = fields.Dict(required=True)
    
    # Por edad
    por_rango_edad = fields.List(fields.Dict())
    edad_promedio = NonNegativeDecimal(required=True, places=1)
    
    # Por estado académico
    por_estado_inscripcion = fields.Dict(required=True)
    por_nivel_actual = fields.List(fields.Dict())
    
    # Geográficos
    por_municipio = fields.List(fields.Dict())
    por_departamento = fields.List(fields.Dict())
    
    # Sacramentales
    bautizados = NonNegativeInteger(required=True)
    con_primera_comunion = NonNegativeInteger(required=True)
    confirmados = NonNegativeInteger(required=True)
    
    # Especiales
    con_discapacidad = NonNegativeInteger(required=True)
    requieren_atencion_especial = NonNegativeInteger(required=True)
    con_beca = NonNegativeInteger(required=True)
    
    # Rendimiento académico
    promedio_general_todos = NonNegativeDecimal(required=True, places=2)
    porcentaje_asistencia_promedio = NonNegativeDecimal(required=True, places=1)
    tasa_completacion = NonNegativeDecimal(required=True, places=1)


@register_schema('catequizando_transfer')
class CatequizandoTransferSchema(BaseSchema):
    """Schema para transferencia de catequizando."""
    
    catequizando_id = PositiveInteger(required=True)
    parroquia_origen_id = PositiveInteger(required=True)
    parroquia_destino_id = PositiveInteger(required=True)
    
    # Información de la transferencia
    motivo_transferencia = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'cambio_residencia', 'cambio_horario', 'problema_personal',
            'solicitud_familia', 'recomendacion_catequista', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Estado en origen y destino
    nivel_actual_id = PositiveInteger(required=True)
    nivel_destino_id = PositiveInteger(allow_none=True)
    
    # Información académica para transferir
    calificacion_parcial = NonNegativeDecimal(
        allow_none=True,
        places=1,
        validate=validate.Range(min=0, max=5)
    )
    
    sesiones_completadas = NonNegativeInteger(required=True)
    porcentaje_avance = NonNegativeDecimal(
        required=True,
        places=1,
        validate=validate.Range(min=0, max=100)
    )
    
    # Fechas
    fecha_solicitud = fields.Date(required=True, missing=date.today)
    fecha_autorizacion = fields.Date(allow_none=True)
    fecha_efectiva = fields.Date(allow_none=True)
    
    # Autorizaciones
    autorizado_por_origen = TrimmedString(allow_none=True)
    autorizado_por_destino = TrimmedString(allow_none=True)
    
    # Observaciones y recomendaciones
    observaciones_origen = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    recomendaciones_destino = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Estado de la transferencia
    estado_transferencia = TrimmedString(
        required=True,
        missing='pendiente',
        validate=validate.OneOf(['pendiente', 'aprobada', 'rechazada', 'completada'])
    )
    
    @validates_schema
    def validate_transfer(self, data, **kwargs):
        """Validaciones específicas de transferencia."""
        origen = data.get('parroquia_origen_id')
        destino = data.get('parroquia_destino_id')
        
        if origen == destino:
            raise ValidationError('La parroquia de origen no puede ser igual a la de destino')
        
        # Validar fechas
        fecha_solicitud = data.get('fecha_solicitud')
        fecha_autorizacion = data.get('fecha_autorizacion')
        fecha_efectiva = data.get('fecha_efectiva')
        
        if fecha_autorizacion and fecha_solicitud and fecha_autorizacion < fecha_solicitud:
            raise ValidationError({'fecha_autorizacion': 'La autorización no puede ser anterior a la solicitud'})
        
        if fecha_efectiva and fecha_autorizacion and fecha_efectiva < fecha_autorizacion:
            raise ValidationError({'fecha_efectiva': 'La fecha efectiva no puede ser anterior a la autorización'})