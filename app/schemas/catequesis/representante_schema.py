"""
Schemas de representante para el sistema de catequesis.
Maneja validaciones para padres, tutores y representantes legales de catequizandos.
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from datetime import datetime, date

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, DocumentoIdentidad, Telefono,
    FechaNacimiento, register_schema, PositiveInteger, NonNegativeInteger
)


@register_schema('representante_create')
class RepresentanteCreateSchema(BaseSchema):
    """Schema para creación de representantes."""
    
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
        validate=validate.OneOf(['CC', 'CE', 'PA', 'NIT'])
    )
    
    fecha_nacimiento = FechaNacimiento(allow_none=True)
    lugar_nacimiento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=3, max=150)
    )
    
    genero = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['M', 'F'])
    )
    
    # Relación con el catequizando
    tipo_representante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'padre', 'madre', 'abuelo', 'abuela', 'tio', 'tia',
            'hermano', 'hermana', 'tutor_legal', 'acudiente',
            'padrino', 'madrina', 'otro_familiar', 'otro'
        ])
    )
    
    es_representante_legal = fields.Boolean(missing=False)
    es_contacto_principal = fields.Boolean(missing=False)
    es_contacto_emergencia = fields.Boolean(missing=False)
    
    # Información de contacto
    telefono_principal = Telefono(required=True)
    telefono_alternativo = Telefono(allow_none=True)
    email_principal = Email(allow_none=True)
    email_alternativo = Email(allow_none=True)
    
    # Dirección (puede ser diferente a la del catequizando)
    direccion_residencia = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=10, max=300)
    )
    misma_direccion_catequizando = fields.Boolean(missing=True)
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    municipio = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    departamento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Información laboral/profesional
    ocupacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    empresa_trabajo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    telefono_trabajo = Telefono(allow_none=True)
    
    # Información educativa
    nivel_educativo = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'primaria_incompleta', 'primaria_completa',
            'secundaria_incompleta', 'secundaria_completa',
            'tecnico', 'tecnologo', 'universitario_incompleto',
            'universitario_completo', 'posgrado'
        ])
    )
    
    # Estado civil y familiar
    estado_civil = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'soltero', 'casado_iglesia', 'casado_civil', 'union_libre',
            'separado', 'divorciado', 'viudo'
        ])
    )
    
    # Información religiosa
    religion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    bautizado_catolico = fields.Boolean(allow_none=True)
    practica_religion = fields.Boolean(allow_none=True)
    parroquia_pertenece = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Participación en la catequesis
    puede_colaborar = fields.Boolean(missing=False)
    areas_colaboracion = fields.List(
        fields.String(validate=validate.OneOf([
            'transporte', 'eventos', 'materiales', 'apoyo_academico',
            'actividades_recreativas', 'pastoral_familiar', 'otro'
        ])),
        missing=[]
    )
    
    disponibilidad_horaria = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mañana', 'tarde', 'noche', 'fines_semana', 'flexible'])
    )
    
    # Información socioeconómica
    estrato_socioeconomico = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=6)
    )
    
    situacion_laboral = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'empleado_formal', 'empleado_informal', 'independiente',
            'desempleado', 'pensionado', 'estudiante', 'hogar'
        ])
    )
    
    # Autorizaciones y permisos
    autoriza_fotos = fields.Boolean(missing=True)
    autoriza_datos_personales = fields.Boolean(missing=True)
    autoriza_comunicaciones = fields.Boolean(missing=True)
    acepta_responsabilidades = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe aceptar las responsabilidades como representante')
    )
    
    # Observaciones
    observaciones_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_representante(self, data, **kwargs):
        """Validaciones específicas del representante."""
        # Validar edad si se proporciona fecha de nacimiento
        fecha_nac = data.get('fecha_nacimiento')
        if fecha_nac:
            edad = (date.today() - fecha_nac).days / 365.25
            if edad < 18:
                raise ValidationError({'fecha_nacimiento': 'El representante debe ser mayor de edad'})
        
        # Validar dirección si no es la misma del catequizando
        misma_direccion = data.get('misma_direccion_catequizando', True)
        direccion = data.get('direccion_residencia')
        
        if not misma_direccion and not direccion:
            raise ValidationError({'direccion_residencia': 'Debe proporcionar dirección si es diferente a la del catequizando'})
        
        # Validar información laboral
        ocupacion = data.get('ocupacion')
        situacion_laboral = data.get('situacion_laboral')
        
        if situacion_laboral in ['empleado_formal', 'empleado_informal', 'independiente'] and not ocupacion:
            raise ValidationError({'ocupacion': 'Debe especificar ocupación según su situación laboral'})


@register_schema('representante_update')
class RepresentanteUpdateSchema(BaseSchema):
    """Schema para actualización de representantes."""
    
    # Información personal (documento no se puede cambiar)
    nombres = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    apellidos = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    lugar_nacimiento = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=150))
    
    # Relación (tipo no se cambia, pero sí otros aspectos)
    es_representante_legal = fields.Boolean(allow_none=True)
    es_contacto_principal = fields.Boolean(allow_none=True)
    es_contacto_emergencia = fields.Boolean(allow_none=True)
    
    # Contacto
    telefono_principal = Telefono(allow_none=True)
    telefono_alternativo = Telefono(allow_none=True)
    email_principal = Email(allow_none=True)
    email_alternativo = Email(allow_none=True)
    
    # Dirección
    direccion_residencia = TrimmedString(allow_none=True, validate=validate.Length(min=10, max=300))
    misma_direccion_catequizando = fields.Boolean(allow_none=True)
    barrio = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    municipio = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    departamento = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Información laboral
    ocupacion = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    empresa_trabajo = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    telefono_trabajo = Telefono(allow_none=True)
    
    # Información educativa
    nivel_educativo = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'primaria_incompleta', 'primaria_completa',
            'secundaria_incompleta', 'secundaria_completa',
            'tecnico', 'tecnologo', 'universitario_incompleto',
            'universitario_completo', 'posgrado'
        ])
    )
    
    # Estado civil
    estado_civil = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'soltero', 'casado_iglesia', 'casado_civil', 'union_libre',
            'separado', 'divorciado', 'viudo'
        ])
    )
    
    # Información religiosa
    religion = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    bautizado_catolico = fields.Boolean(allow_none=True)
    practica_religion = fields.Boolean(allow_none=True)
    parroquia_pertenece = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Participación
    puede_colaborar = fields.Boolean(allow_none=True)
    areas_colaboracion = fields.List(fields.String(), allow_none=True)
    disponibilidad_horaria = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mañana', 'tarde', 'noche', 'fines_semana', 'flexible'])
    )
    
    # Información socioeconómica
    estrato_socioeconomico = PositiveInteger(
        allow_none=True,
        validate=validate.Range(min=1, max=6)
    )
    situacion_laboral = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'empleado_formal', 'empleado_informal', 'independiente',
            'desempleado', 'pensionado', 'estudiante', 'hogar'
        ])
    )
    
    # Autorizaciones
    autoriza_fotos = fields.Boolean(allow_none=True)
    autoriza_datos_personales = fields.Boolean(allow_none=True)
    autoriza_comunicaciones = fields.Boolean(allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('representante_response')
class RepresentanteResponseSchema(BaseSchema):
    """Schema para respuesta de representante."""
    
    # Información básica
    id = PositiveInteger(required=True)
    nombres = TrimmedString(required=True)
    apellidos = TrimmedString(required=True)
    nombre_completo = TrimmedString(dump_only=True)
    documento_identidad = TrimmedString(required=True)
    tipo_documento = TrimmedString(required=True)
    fecha_nacimiento = fields.Date(allow_none=True)
    edad = PositiveInteger(dump_only=True, allow_none=True)
    lugar_nacimiento = TrimmedString(allow_none=True)
    genero = TrimmedString(allow_none=True)
    
    # Relación con catequizando
    tipo_representante = TrimmedString(required=True)
    tipo_representante_display = TrimmedString(dump_only=True)
    es_representante_legal = fields.Boolean(required=True)
    es_contacto_principal = fields.Boolean(required=True)
    es_contacto_emergencia = fields.Boolean(required=True)
    
    # Contacto
    telefono_principal = TrimmedString(required=True)
    telefono_alternativo = TrimmedString(allow_none=True)
    email_principal = Email(allow_none=True)
    email_alternativo = Email(allow_none=True)
    
    # Dirección
    direccion_residencia = TrimmedString(allow_none=True)
    direccion_completa = TrimmedString(dump_only=True, allow_none=True)
    misma_direccion_catequizando = fields.Boolean(required=True)
    barrio = TrimmedString(allow_none=True)
    municipio = TrimmedString(allow_none=True)
    departamento = TrimmedString(allow_none=True)
    codigo_postal = TrimmedString(allow_none=True)
    
    # Información laboral
    ocupacion = TrimmedString(allow_none=True)
    empresa_trabajo = TrimmedString(allow_none=True)
    telefono_trabajo = TrimmedString(allow_none=True)
    nivel_educativo = TrimmedString(allow_none=True)
    situacion_laboral = TrimmedString(allow_none=True)
    estrato_socioeconomico = PositiveInteger(allow_none=True)
    
    # Estado civil y religioso
    estado_civil = TrimmedString(allow_none=True)
    religion = TrimmedString(allow_none=True)
    bautizado_catolico = fields.Boolean(allow_none=True)
    practica_religion = fields.Boolean(allow_none=True)
    parroquia_pertenece = TrimmedString(allow_none=True)
    
    # Participación en catequesis
    puede_colaborar = fields.Boolean(required=True)
    areas_colaboracion = fields.List(fields.String(), missing=[])
    disponibilidad_horaria = TrimmedString(allow_none=True)
    
    # Estadísticas de participación
    catequizandos_representados = NonNegativeInteger(dump_only=True)
    eventos_participados = NonNegativeInteger(dump_only=True)
    colaboraciones_realizadas = NonNegativeInteger(dump_only=True)
    
    # Autorizaciones
    autoriza_fotos = fields.Boolean(required=True)
    autoriza_datos_personales = fields.Boolean(required=True)
    autoriza_comunicaciones = fields.Boolean(required=True)
    acepta_responsabilidades = fields.Boolean(required=True)
    
    # Estado
    is_active = fields.Boolean(required=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True)
    
    # Fechas
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('relacion_catequizando_representante')
class RelacionCatequizandoRepresentanteSchema(BaseSchema):
    """Schema para relación entre catequizando y representante."""
    
    id = PositiveInteger(dump_only=True)
    catequizando_id = PositiveInteger(required=True)
    representante_id = PositiveInteger(required=True)
    
    # Tipo de relación específica
    parentesco = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'padre', 'madre', 'abuelo_paterno', 'abuela_paterna',
            'abuelo_materno', 'abuela_materna', 'tio_paterno', 'tia_paterna',
            'tio_materno', 'tia_materna', 'hermano_mayor', 'hermana_mayor',
            'padrino_bautismo', 'madrina_bautismo', 'tutor_legal',
            'acudiente_autorizado', 'otro_familiar', 'no_familiar'
        ])
    )
    
    # Responsabilidades
    puede_recoger = fields.Boolean(missing=True)
    puede_autorizar_salidas = fields.Boolean(missing=False)
    recibe_informes = fields.Boolean(missing=True)
    recibe_citaciones = fields.Boolean(missing=True)
    puede_tomar_decisiones = fields.Boolean(missing=False)
    
    # Contacto de emergencia
    prioridad_contacto = PositiveInteger(
        missing=1,
        validate=validate.Range(min=1, max=5)
    )
    
    # Vigencia de la relación
    fecha_inicio_relacion = fields.Date(required=True, missing=date.today)
    fecha_fin_relacion = fields.Date(allow_none=True)
    motivo_fin_relacion = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Estado
    is_active = fields.Boolean(missing=True)
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    @validates_schema
    def validate_relacion(self, data, **kwargs):
        """Validaciones específicas de la relación."""
        # Validar fechas
        fecha_inicio = data.get('fecha_inicio_relacion')
        fecha_fin = data.get('fecha_fin_relacion')
        
        if fecha_fin and fecha_inicio and fecha_fin <= fecha_inicio:
            raise ValidationError({'fecha_fin_relacion': 'La fecha de fin debe ser posterior al inicio'})
        
        # Validar coherencia del parentesco con responsabilidades
        parentesco = data.get('parentesco')
        puede_tomar_decisiones = data.get('puede_tomar_decisiones', False)
        
        if parentesco in ['padre', 'madre', 'tutor_legal'] and not puede_tomar_decisiones:
            data['puede_tomar_decisiones'] = True  # Forzar para padres y tutores


@register_schema('representante_search')
class RepresentanteSearchSchema(BaseSchema):
    """Schema para búsqueda de representantes."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    documento_identidad = TrimmedString(allow_none=True)
    tipo_representante = TrimmedString(allow_none=True)
    genero = TrimmedString(allow_none=True, validate=validate.OneOf(['M', 'F']))
    is_active = fields.Boolean(allow_none=True)
    
    # Filtros de relación
    es_representante_legal = fields.Boolean(allow_none=True)
    es_contacto_principal = fields.Boolean(allow_none=True)
    es_contacto_emergencia = fields.Boolean(allow_none=True)
    
    # Filtros geográficos
    municipio = TrimmedString(allow_none=True)
    departamento = TrimmedString(allow_none=True)
    barrio = TrimmedString(allow_none=True)
    
    # Filtros socioeconómicos
    nivel_educativo = TrimmedString(allow_none=True)
    situacion_laboral = TrimmedString(allow_none=True)
    estrato_socioeconomico = PositiveInteger(allow_none=True)
    
    # Filtros religiosos
    bautizado_catolico = fields.Boolean(allow_none=True)
    practica_religion = fields.Boolean(allow_none=True)
    
    # Filtros de participación
    puede_colaborar = fields.Boolean(allow_none=True)
    disponibilidad_horaria = TrimmedString(allow_none=True)
    
    # Filtros por catequizando
    catequizando_id = PositiveInteger(allow_none=True)
    tiene_catequizandos_activos = fields.Boolean(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='nombre_completo',
        validate=validate.OneOf([
            'nombre_completo', 'documento_identidad', 'tipo_representante',
            'municipio', 'created_at', 'catequizandos_representados'
        ])
    )
    sort_order = TrimmedString(missing='asc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('comunicacion_representante')
class ComunicacionRepresentanteSchema(BaseSchema):
    """Schema para comunicaciones con representantes."""
    
    id = PositiveInteger(dump_only=True)
    representante_id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(allow_none=True)
    
    # Tipo y medio de comunicación
    tipo_comunicacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'citacion', 'informe_academico', 'informe_comportamiento',
            'notificacion_evento', 'solicitud_documentos', 'felicitacion',
            'llamada_atencion', 'invitacion_reunion', 'recordatorio',
            'emergencia', 'otro'
        ])
    )
    
    medio_comunicacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['presencial', 'telefonica', 'whatsapp', 'email', 'carta', 'mensaje'])
    )
    
    # Contenido
    asunto = TrimmedString(required=True, validate=validate.Length(min=5, max=200))
    mensaje = TrimmedString(required=True, validate=validate.Length(min=10, max=2000))
    
    # Fechas y seguimiento
    fecha_envio = fields.DateTime(required=True, missing=datetime.utcnow)
    fecha_lectura = fields.DateTime(allow_none=True)
    fecha_respuesta = fields.DateTime(allow_none=True)
    requiere_respuesta = fields.Boolean(missing=False)
    fecha_limite_respuesta = fields.Date(allow_none=True)
    
    # Estado
    estado_comunicacion = TrimmedString(
        required=True,
        missing='enviada',
        validate=validate.OneOf(['borrador', 'enviada', 'entregada', 'leida', 'respondida', 'vencida'])
    )
    
    # Respuesta
    respuesta_representante = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    satisfaccion_respuesta = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['muy_satisfactoria', 'satisfactoria', 'regular', 'insatisfactoria'])
    )
    
    # Personal
    enviado_por = TrimmedString(required=True)
    respondido_por = TrimmedString(allow_none=True)
    
    # Observaciones
    observaciones_internas = TrimmedString(allow_none=True, validate=validate.Length(max=500))


@register_schema('autorizacion_representante')
class AutorizacionRepresentanteSchema(BaseSchema):
    """Schema para autorizaciones específicas."""
    
    id = PositiveInteger(dump_only=True)
    representante_id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(required=True)
    
    # Tipo de autorización
    tipo_autorizacion = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'salida_pedagogica', 'retiro_espiritual', 'evento_especial',
            'actividad_recreativa', 'servicio_medico', 'transporte_especial',
            'uso_imagen', 'participacion_liturgica', 'otro'
        ])
    )
    
    descripcion_actividad = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    
    # Fechas y horarios
    fecha_actividad = fields.Date(required=True)
    hora_inicio = fields.Time(required=True)
    hora_fin = fields.Time(required=True)
    lugar_actividad = TrimmedString(required=True, validate=validate.Length(min=5, max=200))
    
    # Responsables
    responsable_actividad = TrimmedString(required=True, validate=validate.Length(min=5, max=100))
    telefono_responsable = Telefono(required=True)
    
    # Costo y requisitos
    costo_actividad = NonNegativeInteger(missing=0)
    requiere_transporte = fields.Boolean(missing=False)
    requiere_alimentacion = fields.Boolean(missing=False)
    requiere_materiales = fields.Boolean(missing=False)
    lista_materiales = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Autorización
    fecha_autorizacion = fields.DateTime(allow_none=True)
    autorizado = fields.Boolean(allow_none=True)
    motivo_negacion = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    
    # Condiciones especiales
    condiciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    requiere_acompañante = fields.Boolean(missing=False)
    acompañante_designado = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Estado
    estado_autorizacion = TrimmedString(
        required=True,
        missing='pendiente',
        validate=validate.OneOf(['pendiente', 'autorizada', 'denegada', 'vencida', 'utilizada'])
    )
    
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    @validates_schema
    def validate_autorizacion(self, data, **kwargs):
        """Validaciones específicas de autorización."""
        # Validar fecha no sea pasada
        fecha_actividad = data.get('fecha_actividad')
        if fecha_actividad and fecha_actividad < date.today():
            raise ValidationError({'fecha_actividad': 'La fecha de la actividad no puede ser pasada'})
        
        # Validar horarios
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        
        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise ValidationError({'hora_fin': 'La hora de fin debe ser posterior al inicio'})


@register_schema('representante_stats')
class RepresentanteStatsSchema(BaseSchema):
    """Schema para estadísticas de representantes."""
    
    total_representantes = NonNegativeInteger(required=True)
    representantes_activos = NonNegativeInteger(required=True)
    nuevos_este_año = NonNegativeInteger(required=True)
    
    # Por tipo de representante
    por_tipo_representante = fields.Dict(required=True)
    por_genero = fields.Dict(required=True)
    
    # Por nivel educativo
    por_nivel_educativo = fields.List(fields.Dict())
    por_situacion_laboral = fields.List(fields.Dict())
    por_estrato = fields.List(fields.Dict())
    
    # Geográficos
    por_municipio = fields.List(fields.Dict())
    por_departamento = fields.List(fields.Dict())
    
    # Religiosos
    bautizados_catolicos = NonNegativeInteger(required=True)
    practicantes_activos = NonNegativeInteger(required=True)
    
    # Participación
    pueden_colaborar = NonNegativeInteger(required=True)
    colaboradores_activos = NonNegativeInteger(required=True)
    promedio_catequizandos_por_representante = fields.Decimal(required=True, places=1)
    
    # Comunicaciones
    comunicaciones_enviadas_mes = NonNegativeInteger(required=True)
    tasa_respuesta_comunicaciones = fields.Decimal(required=True, places=1)
    autorizaciones_pendientes = NonNegativeInteger(required=True)


@register_schema('representante_export')
class RepresentanteExportSchema(BaseSchema):
    """Schema para exportación de representantes."""
    
    formato = TrimmedString(
        required=True,
        validate=validate.OneOf(['csv', 'xlsx', 'pdf'])
    )
    
    # Filtros de exportación
    representante_ids = fields.List(PositiveInteger(), allow_none=True)
    filtros = fields.Dict(allow_none=True)
    
    # Campos a incluir
    incluir_campos = fields.List(
        fields.String(),
        missing=[
            'nombre_completo', 'documento_identidad', 'tipo_representante',
            'telefono_principal', 'email_principal', 'municipio',
            'ocupacion', 'nivel_educativo'
        ]
    )
    
    # Información adicional
    incluir_catequizandos = fields.Boolean(missing=True)
    incluir_comunicaciones = fields.Boolean(missing=False)
    incluir_autorizaciones = fields.Boolean(missing=False)
    
    # Configuraciones de privacidad
    anonimizar_datos_sensibles = fields.Boolean(missing=False)
    ocultar_documentos = fields.Boolean(missing=True)
    ocultar_telefonos = fields.Boolean(missing=False)