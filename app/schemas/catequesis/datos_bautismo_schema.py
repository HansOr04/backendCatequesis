"""
Schemas de datos de bautismo para el sistema de catequesis.
Maneja validaciones específicas para información bautismal detallada.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, register_schema, PositiveInteger,
    NonNegativeInteger, FechaNacimiento
)


@register_schema('datos_bautismo_create')
class DatosBautismoCreateSchema(BaseSchema):
    """Schema para creación de datos detallados de bautismo."""
    
    # Referencia al catequizando
    catequizando_id = PositiveInteger(required=True)
    
    # Información básica del bautismo
    fecha_bautismo = fields.Date(required=True)
    hora_bautismo = fields.Time(allow_none=True)
    
    # Lugar del bautismo
    parroquia_bautismo = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=200)
    )
    
    direccion_parroquia = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    ciudad_bautismo = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    departamento_bautismo = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    pais_bautismo = TrimmedString(
        required=True,
        missing='Colombia',
        validate=validate.Length(min=2, max=100)
    )
    
    # Información del celebrante
    sacerdote_celebrante = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    cargo_celebrante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'parroco', 'vicario', 'sacerdote', 'diacono', 'obispo', 'otro'
        ])
    )
    
    numero_licencia_celebrante = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    # Información de los padres al momento del bautismo
    nombre_padre_bautismo = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_padre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    lugar_nacimiento_padre = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    nombre_madre_bautismo = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_madre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    lugar_nacimiento_madre = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    # Estado civil de los padres al momento del bautismo
    padres_casados_iglesia = fields.Boolean(allow_none=True)
    fecha_matrimonio_padres = fields.Date(allow_none=True)
    lugar_matrimonio_padres = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Información de los padrinos
    nombre_padrino = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_padrino = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    lugar_nacimiento_padrino = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    nombre_madrina = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_madrina = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    documento_madrina = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    lugar_nacimiento_madrina = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    # Relación de padrinos con el bautizado
    parentesco_padrino = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'tio', 'abuelo', 'hermano', 'primo', 'cuñado',
            'amigo_familia', 'conocido', 'ninguno', 'otro'
        ])
    )
    
    parentesco_madrina = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'tia', 'abuela', 'hermana', 'prima', 'cuñada',
            'amiga_familia', 'conocida', 'ninguno', 'otro'
        ])
    )
    
    # Información del registro parroquial
    numero_acta_bautismo = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=50)
    )
    
    folio_bautismo = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=20)
    )
    
    libro_bautismo = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=20)
    )
    
    numero_partida_bautismo = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=1, max=50)
    )
    
    año_libro = PositiveInteger(allow_none=True)
    
    # Circunstancias especiales del bautismo
    tipo_bautismo = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'ordinario', 'urgencia', 'condicionado', 'privado',
            'publico', 'solemne', 'otro'
        ])
    )
    
    edad_al_bautismo = NonNegativeInteger(allow_none=True)  # En días
    fue_bautismo_emergencia = fields.Boolean(missing=False)
    motivo_emergencia = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    lugar_emergencia = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Información ritual y litúrgica
    rito_utilizado = TrimmedString(
        missing='romano',
        validate=validate.OneOf(['romano', 'ambrosiano', 'mozarabe', 'otro'])
    )
    
    idioma_ceremonia = TrimmedString(
        missing='español',
        validate=validate.Length(max=50)
    )
    
    hubo_musica = fields.Boolean(missing=True)
    tipo_musica = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['gregoriana', 'tradicional', 'contemporanea', 'mixta'])
    )
    
    # Testigos adicionales
    testigo1_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    testigo1_documento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    testigo2_nombre = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=150)
    )
    
    testigo2_documento = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=5, max=20)
    )
    
    # Información complementaria
    nombre_bautismal_completo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    santos_patron = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    # Preparación pre-bautismal
    recibio_preparacion_prebautismal = fields.Boolean(missing=False)
    lugar_preparacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    duracion_preparacion_horas = NonNegativeInteger(allow_none=True)
    catequista_preparacion = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=150)
    )
    
    # Confirmación posterior
    fue_confirmado_posteriormente = fields.Boolean(allow_none=True)
    fecha_confirmacion_posterior = fields.Date(allow_none=True)
    lugar_confirmacion_posterior = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=200)
    )
    
    # Validaciones canónicas
    cumple_requisitos_canonicos = fields.Boolean(missing=True)
    canon_aplicable = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    dispensas_aplicadas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    observaciones_canonicas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    # Anotaciones marginales
    anotaciones_marginales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    rectificaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    # Estado del registro
    registro_valido = fields.Boolean(missing=True)
    verificado_por = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    fecha_verificacion = fields.Date(allow_none=True)
    
    # Observaciones generales
    observaciones_especiales = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    @validates_schema
    def validate_bautismo(self, data, **kwargs):
        """Validaciones específicas de datos de bautismo."""
        # Validar que tenga al menos un padrino o madrina
        padrino = data.get('nombre_padrino')
        madrina = data.get('nombre_madrina')
        
        if not padrino and not madrina:
            raise ValidationError('Debe especificar al menos un padrino o madrina')
        
        # Validar fechas
        fecha_bautismo = data.get('fecha_bautismo')
        fecha_matrimonio = data.get('fecha_matrimonio_padres')
        
        if fecha_matrimonio and fecha_bautismo and fecha_matrimonio > fecha_bautismo:
            raise ValidationError({'fecha_matrimonio_padres': 'El matrimonio no puede ser posterior al bautismo'})
        
        # Validar bautismo de emergencia
        emergencia = data.get('fue_bautismo_emergencia', False)
        motivo_emergencia = data.get('motivo_emergencia')
        
        if emergencia and not motivo_emergencia:
            raise ValidationError({'motivo_emergencia': 'Debe especificar motivo del bautismo de emergencia'})
        
        # Validar edad al bautismo
        edad_bautismo = data.get('edad_al_bautismo')
        if edad_bautismo is not None and edad_bautismo > 36500:  # 100 años
            raise ValidationError({'edad_al_bautismo': 'La edad al bautismo parece incorrecta'})


@register_schema('datos_bautismo_update')
class DatosBautismoUpdateSchema(BaseSchema):
    """Schema para actualización de datos de bautismo."""
    
    # No se puede cambiar catequizando_id
    
    # Fechas
    fecha_bautismo = fields.Date(allow_none=True)
    hora_bautismo = fields.Time(allow_none=True)
    
    # Lugar
    parroquia_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=3, max=200))
    direccion_parroquia = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    ciudad_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    departamento_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    pais_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    
    # Celebrante
    sacerdote_celebrante = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    cargo_celebrante = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['parroco', 'vicario', 'sacerdote', 'diacono', 'obispo', 'otro'])
    )
    numero_licencia_celebrante = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    
    # Padres
    nombre_padre_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    documento_padre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    lugar_nacimiento_padre = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    nombre_madre_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    documento_madre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    lugar_nacimiento_madre = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    
    # Matrimonio de padres
    padres_casados_iglesia = fields.Boolean(allow_none=True)
    fecha_matrimonio_padres = fields.Date(allow_none=True)
    lugar_matrimonio_padres = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Padrinos
    nombre_padrino = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    documento_padrino = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    lugar_nacimiento_padrino = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    nombre_madrina = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    documento_madrina = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    lugar_nacimiento_madrina = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    
    # Parentesco
    parentesco_padrino = TrimmedString(allow_none=True)
    parentesco_madrina = TrimmedString(allow_none=True)
    
    # Registro
    numero_acta_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=50))
    folio_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=20))
    libro_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=20))
    numero_partida_bautismo = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=50))
    año_libro = PositiveInteger(allow_none=True)
    
    # Circunstancias
    tipo_bautismo = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['ordinario', 'urgencia', 'condicionado', 'privado', 'publico', 'solemne', 'otro'])
    )
    edad_al_bautismo = NonNegativeInteger(allow_none=True)
    fue_bautismo_emergencia = fields.Boolean(allow_none=True)
    motivo_emergencia = TrimmedString(allow_none=True, validate=validate.Length(max=300))
    lugar_emergencia = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Información litúrgica
    rito_utilizado = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['romano', 'ambrosiano', 'mozarabe', 'otro'])
    )
    idioma_ceremonia = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    hubo_musica = fields.Boolean(allow_none=True)
    tipo_musica = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['gregoriana', 'tradicional', 'contemporanea', 'mixta'])
    )
    
    # Testigos
    testigo1_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    testigo1_documento = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    testigo2_nombre = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=150))
    testigo2_documento = TrimmedString(allow_none=True, validate=validate.Length(min=5, max=20))
    
    # Información complementaria
    nombre_bautismal_completo = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    santos_patron = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Preparación
    recibio_preparacion_prebautismal = fields.Boolean(allow_none=True)
    lugar_preparacion = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    duracion_preparacion_horas = NonNegativeInteger(allow_none=True)
    catequista_preparacion = TrimmedString(allow_none=True, validate=validate.Length(max=150))
    
    # Confirmación posterior
    fue_confirmado_posteriormente = fields.Boolean(allow_none=True)
    fecha_confirmacion_posterior = fields.Date(allow_none=True)
    lugar_confirmacion_posterior = TrimmedString(allow_none=True, validate=validate.Length(max=200))
    
    # Validez canónica
    cumple_requisitos_canonicos = fields.Boolean(allow_none=True)
    canon_aplicable = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    dispensas_aplicadas = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    observaciones_canonicas = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    # Anotaciones
    anotaciones_marginales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    rectificaciones = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    
    # Verificación
    registro_valido = fields.Boolean(allow_none=True)
    verificado_por = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    fecha_verificacion = fields.Date(allow_none=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('datos_bautismo_response')
class DatosBautismoResponseSchema(BaseSchema):
    """Schema para respuesta de datos de bautismo."""
    
    # Información básica
    id = PositiveInteger(required=True)
    catequizando_id = PositiveInteger(required=True)
    catequizando_nombre = TrimmedString(dump_only=True, required=True)
    
    # Fechas del bautismo
    fecha_bautismo = fields.Date(required=True)
    hora_bautismo = fields.Time(allow_none=True)
    fecha_hora_display = TrimmedString(dump_only=True)
    
    # Lugar
    parroquia_bautismo = TrimmedString(required=True)
    direccion_parroquia = TrimmedString(allow_none=True)
    ciudad_bautismo = TrimmedString(required=True)
    departamento_bautismo = TrimmedString(required=True)
    pais_bautismo = TrimmedString(required=True)
    lugar_completo = TrimmedString(dump_only=True)
    
    # Celebrante
    sacerdote_celebrante = TrimmedString(required=True)
    cargo_celebrante = TrimmedString(required=True)
    cargo_celebrante_display = TrimmedString(dump_only=True)
    numero_licencia_celebrante = TrimmedString(allow_none=True)
    
    # Padres
    nombre_padre_bautismo = TrimmedString(required=True)
    documento_padre = TrimmedString(allow_none=True)
    lugar_nacimiento_padre = TrimmedString(allow_none=True)
    nombre_madre_bautismo = TrimmedString(required=True)
    documento_madre = TrimmedString(allow_none=True)
    lugar_nacimiento_madre = TrimmedString(allow_none=True)
    padres_display = TrimmedString(dump_only=True)
    
    # Matrimonio de padres
    padres_casados_iglesia = fields.Boolean(allow_none=True)
    fecha_matrimonio_padres = fields.Date(allow_none=True)
    lugar_matrimonio_padres = TrimmedString(allow_none=True)
    
    # Padrinos
    nombre_padrino = TrimmedString(allow_none=True)
    documento_padrino = TrimmedString(allow_none=True)
    lugar_nacimiento_padrino = TrimmedString(allow_none=True)
    parentesco_padrino = TrimmedString(allow_none=True)
    nombre_madrina = TrimmedString(allow_none=True)
    documento_madrina = TrimmedString(allow_none=True)
    lugar_nacimiento_madrina = TrimmedString(allow_none=True)
    parentesco_madrina = TrimmedString(allow_none=True)
    padrinos_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Registro parroquial
    numero_acta_bautismo = TrimmedString(allow_none=True)
    folio_bautismo = TrimmedString(allow_none=True)
    libro_bautismo = TrimmedString(allow_none=True)
    numero_partida_bautismo = TrimmedString(allow_none=True)
    año_libro = PositiveInteger(allow_none=True)
    referencia_registro = TrimmedString(dump_only=True, allow_none=True)
    
    # Circunstancias del bautismo
    tipo_bautismo = TrimmedString(required=True)
    tipo_bautismo_display = TrimmedString(dump_only=True)
    edad_al_bautismo = NonNegativeInteger(allow_none=True)
    edad_al_bautismo_display = TrimmedString(dump_only=True, allow_none=True)
    fue_bautismo_emergencia = fields.Boolean(required=True)
    motivo_emergencia = TrimmedString(allow_none=True)
    lugar_emergencia = TrimmedString(allow_none=True)
    
    # Información litúrgica
    rito_utilizado = TrimmedString(required=True)
    idioma_ceremonia = TrimmedString(required=True)
    hubo_musica = fields.Boolean(required=True)
    tipo_musica = TrimmedString(allow_none=True)
    
    # Testigos adicionales
    testigo1_nombre = TrimmedString(allow_none=True)
    testigo1_documento = TrimmedString(allow_none=True)
    testigo2_nombre = TrimmedString(allow_none=True)
    testigo2_documento = TrimmedString(allow_none=True)
    testigos_display = TrimmedString(dump_only=True, allow_none=True)
    
    # Información complementaria
    nombre_bautismal_completo = TrimmedString(allow_none=True)
    santos_patron = TrimmedString(allow_none=True)
    
    # Preparación prebautismal
    recibio_preparacion_prebautismal = fields.Boolean(required=True)
    lugar_preparacion = TrimmedString(allow_none=True)
    duracion_preparacion_horas = NonNegativeInteger(allow_none=True)
    catequista_preparacion = TrimmedString(allow_none=True)
    
    # Confirmación posterior
    fue_confirmado_posteriormente = fields.Boolean(allow_none=True)
    fecha_confirmacion_posterior = fields.Date(allow_none=True)
    lugar_confirmacion_posterior = TrimmedString(allow_none=True)
    
    # Validez canónica
    cumple_requisitos_canonicos = fields.Boolean(required=True)
    canon_aplicable = TrimmedString(allow_none=True)
    dispensas_aplicadas = TrimmedString(allow_none=True)
    observaciones_canonicas = TrimmedString(allow_none=True)
    
    # Anotaciones marginales
    anotaciones_marginales = TrimmedString(allow_none=True)
    rectificaciones = TrimmedString(allow_none=True)
    tiene_anotaciones = fields.Boolean(dump_only=True)
    
    # Estado del registro
    registro_valido = fields.Boolean(required=True)
    verificado_por = TrimmedString(allow_none=True)
    fecha_verificacion = fields.Date(allow_none=True)
    esta_verificado = fields.Boolean(dump_only=True)
    
    # Observaciones
    observaciones_especiales = TrimmedString(allow_none=True)
    
    # Fechas de auditoría
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


@register_schema('datos_bautismo_search')
class DatosBautismoSearchSchema(BaseSchema):
    """Schema para búsqueda de datos de bautismo."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros básicos
    catequizando_id = PositiveInteger(allow_none=True)
    
    # Filtros de fecha
    fecha_bautismo_desde = fields.Date(allow_none=True)
    fecha_bautismo_hasta = fields.Date(allow_none=True)
    año_bautismo = PositiveInteger(allow_none=True)
    
    # Filtros de lugar
    parroquia_bautismo = TrimmedString(allow_none=True)
    ciudad_bautismo = TrimmedString(allow_none=True)
    departamento_bautismo = TrimmedString(allow_none=True)
    
    # Filtros de celebrante
    sacerdote_celebrante = TrimmedString(allow_none=True)
    cargo_celebrante = TrimmedString(allow_none=True)
    
    # Filtros de padrinos
    nombre_padrino = TrimmedString(allow_none=True)
    nombre_madrina = TrimmedString(allow_none=True)
    documento_padrino = TrimmedString(allow_none=True)
    documento_madrina = TrimmedString(allow_none=True)
    
    # Filtros de padres
    nombre_padre_bautismo = TrimmedString(allow_none=True)
    nombre_madre_bautismo = TrimmedString(allow_none=True)
    padres_casados_iglesia = fields.Boolean(allow_none=True)
    
    # Filtros de tipo
    tipo_bautismo = TrimmedString(allow_none=True)
    fue_bautismo_emergencia = fields.Boolean(allow_none=True)
    rito_utilizado = TrimmedString(allow_none=True)
    
    # Filtros de edad
    edad_minima_bautismo = NonNegativeInteger(allow_none=True)
    edad_maxima_bautismo = NonNegativeInteger(allow_none=True)
    
    # Filtros de validez
    registro_valido = fields.Boolean(allow_none=True)
    esta_verificado = fields.Boolean(allow_none=True)
    cumple_requisitos_canonicos = fields.Boolean(allow_none=True)
    
    # Filtros de preparación
    recibio_preparacion_prebautismal = fields.Boolean(allow_none=True)
    lugar_preparacion = TrimmedString(allow_none=True)
    
    # Filtros de registro
    numero_acta_bautismo = TrimmedString(allow_none=True)
    libro_bautismo = TrimmedString(allow_none=True)
    año_libro = PositiveInteger(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='fecha_bautismo',
        validate=validate.OneOf([
            'fecha_bautismo', 'catequizando_nombre', 'parroquia_bautismo',
            'sacerdote_celebrante', 'created_at'
        ])
    )
    sort_order = TrimmedString(missing='desc', validate=validate.OneOf(['asc', 'desc']))


@register_schema('datos_bautismo_stats')
class DatosBautismoStatsSchema(BaseSchema):
    """Schema para estadísticas de datos de bautismo."""
    
    total_bautismos = NonNegativeInteger(required=True)
    bautismos_este_año = NonNegativeInteger(required=True)
    bautismos_este_mes = NonNegativeInteger(required=True)
    
    # Por tipo de bautismo
    por_tipo_bautismo = fields.Dict(required=True)
    bautismos_emergencia = NonNegativeInteger(required=True)
    
    # Por edad al bautismo
    por_rango_edad_bautismo = fields.List(fields.Dict())
    edad_promedio_bautismo = NonNegativeDecimal(required=True, places=1)
    bautismos_adultos = NonNegativeInteger(required=True)
    bautismos_infantes = NonNegativeInteger(required=True)
    
    # Por lugar
    por_parroquia = fields.List(fields.Dict())
    por_ciudad = fields.List(fields.Dict())
    por_departamento = fields.List(fields.Dict())
    
    # Por celebrante
    por_celebrante = fields.List(fields.Dict())
    por_cargo_celebrante = fields.Dict(required=True)
    
    # Padres y matrimonio
    padres_casados_iglesia = NonNegativeInteger(required=True)
    padres_no_casados_iglesia = NonNegativeInteger(required=True)
    porcentaje_padres_casados = NonNegativeDecimal(required=True, places=1)
    
    # Padrinos
    con_padrino_y_madrina = NonNegativeInteger(required=True)
    solo_padrino = NonNegativeInteger(required=True)
    solo_madrina = NonNegativeInteger(required=True)
    
    # Preparación
    con_preparacion_prebautismal = NonNegativeInteger(required=True)
    sin_preparacion = NonNegativeInteger(required=True)
    horas_promedio_preparacion = NonNegativeDecimal(required=True, places=1)
    
    # Validez y verificación
    registros_validos = NonNegativeInteger(required=True)
    registros_verificados = NonNegativeInteger(required=True)
    con_requisitos_canonicos = NonNegativeInteger(required=True)
    con_dispensas = NonNegativeInteger(required=True)
    
    # Tendencias temporales
    por_mes_año_actual = fields.List(fields.Dict())
    por_año = fields.List(fields.Dict())
    
    # Rito y liturgia
    por_rito = fields.Dict(required=True)
    por_idioma_ceremonia = fields.Dict(required=True)
    con_musica = NonNegativeInteger(required=True)
    
    # Confirmación posterior
    confirmados_posteriormente = NonNegativeInteger(required=True)
    pendientes_confirmacion = NonNegativeInteger(required=True)


@register_schema('certificado_bautismo')
class CertificadoBautismoSchema(BaseSchema):
    """Schema para emisión de certificados de bautismo."""
    
    datos_bautismo_id = PositiveInteger(required=True)
    
    tipo_certificado = TrimmedString(
        required=True,
        validate=validate.OneOf(['certificado', 'constancia', 'copia_literal'])
    )
    
    solicitado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=150)
    )
    
    documento_solicitante = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=20)
    )
    
    parentesco_solicitante = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'titular', 'padre', 'madre', 'hijo', 'hermano', 'abuelo',
            'nieto', 'representante_legal', 'autoridad_eclesiastica', 'otro'
        ])
    )
    
    motivo_solicitud = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'primera_comunion', 'confirmacion', 'matrimonio', 'ordenacion',
            'tramite_migratorio', 'tramite_legal', 'archivo_personal', 'otro'
        ])
    )
    
    descripcion_motivo = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=300)
    )
    
    fecha_solicitud = fields.Date(required=True, missing=date.today)
    fecha_expedicion = fields.Date(allow_none=True)
    fecha_entrega = fields.Date(allow_none=True)
    
    incluir_anotaciones_marginales = fields.Boolean(missing=True)
    incluir_sello_parroquial = fields.Boolean(missing=True)
    
    numero_certificado = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=50)
    )
    
    expedido_por = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=100)
    )
    
    costo_certificado = NonNegativeDecimal(missing=0, places=2)
    
    observaciones = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates_schema
    def validate_certificado(self, data, **kwargs):
        """Validaciones para certificado de bautismo."""
        parentesco = data.get('parentesco_solicitante')
        motivo = data.get('motivo_solicitud')
        
        # Para ciertos motivos, validar parentesco apropiado
        if motivo in ['primera_comunion', 'confirmacion'] and parentesco not in ['titular', 'padre', 'madre', 'representante_legal']:
            raise ValidationError({'parentesco_solicitante': 'Parentesco no válido para este tipo de trámite'})
        
        # Validar fechas
        fecha_solicitud = data.get('fecha_solicitud')
        fecha_expedicion = data.get('fecha_expedicion')
        fecha_entrega = data.get('fecha_entrega')
        
        if fecha_expedicion and fecha_solicitud and fecha_expedicion < fecha_solicitud:
            raise ValidationError({'fecha_expedicion': 'La fecha de expedición no puede ser anterior a la solicitud'})
        
        if fecha_entrega and fecha_expedicion and fecha_entrega < fecha_expedicion:
            raise ValidationError({'fecha_entrega': 'La fecha de entrega no puede ser anterior a la expedición'})


@register_schema('validacion_bautismo')
class ValidacionBautismoSchema(BaseSchema):
    """Schema para validación canónica de bautismo."""
    
    datos_bautismo_id = PositiveInteger(required=True)
    
    validado_por = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    
    cargo_validador = TrimmedString(
        required=True,
        validate=validate.OneOf(['parroco', 'vicario', 'canciller', 'obispo', 'otro'])
    )
    
    fecha_validacion = fields.Date(required=True, missing=date.today)
    
    resultado_validacion = TrimmedString(
        required=True,
        validate=validate.OneOf(['valido', 'invalido', 'dudoso', 'pendiente_documentos'])
    )
    
    cumple_requisitos_forma = fields.Boolean(required=True)
    cumple_requisitos_materia = fields.Boolean(required=True)
    cumple_requisitos_intencion = fields.Boolean(required=True)
    
    defectos_encontrados = fields.List(
        fields.String(validate=validate.OneOf([
            'falta_intencion', 'materia_invalida', 'forma_incorrecta',
            'celebrante_no_autorizado', 'documentacion_incompleta',
            'datos_inconsistentes', 'otro'
        ])),
        missing=[]
    )
    
    observaciones_validacion = TrimmedString(
        required=True,
        validate=validate.Length(min=10, max=1000)
    )
    
    acciones_correctivas = TrimmedString(
        allow_none=True,
        validate=validate.Length(max=1000)
    )
    
    requiere_convalidacion = fields.Boolean(missing=False)
    fecha_convalidacion = fields.Date(allow_none=True)
    
    documentos_adicionales_requeridos = fields.List(
        fields.String(validate=validate.OneOf([
            'acta_matrimonio_padres', 'certificado_celebrante', 'testimonios',
            'dispensas_canonicas', 'autorizacion_ordinario', 'otro'
        ])),
        missing=[]
    )
    
    @validates_schema
    def validate_validacion(self, data, **kwargs):
        """Validaciones específicas de validación canónica."""
        resultado = data.get('resultado_validacion')
        defectos = data.get('defectos_encontrados', [])
        acciones = data.get('acciones_correctivas')
        
        if resultado == 'invalido' and not defectos:
            raise ValidationError({'defectos_encontrados': 'Debe especificar defectos si el bautismo es inválido'})
        
        if resultado in ['invalido', 'dudoso'] and not acciones:
            raise ValidationError({'acciones_correctivas': 'Debe especificar acciones correctivas'})
        
        # Validar convalidación
        requiere_conval = data.get('requiere_convalidacion', False)
        fecha_conval = data.get('fecha_convalidacion')
        
        if requiere_conval and not fecha_conval:
            raise ValidationError({'fecha_convalidacion': 'Debe especificar fecha de convalidación'})


@register_schema('reporte_bautismo')
class ReporteBautismoSchema(BaseSchema):
    """Schema para reportes de bautismo."""
    
    tipo_reporte = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'mensual', 'anual', 'por_periodo', 'por_parroquia',
            'por_celebrante', 'estadistico', 'personalizado'
        ])
    )
    
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    
    filtros = fields.Dict(allow_none=True)
    
    incluir_estadisticas = fields.Boolean(missing=True)
    incluir_graficos = fields.Boolean(missing=True)
    incluir_detalles = fields.Boolean(missing=False)
    
    formato_salida = TrimmedString(
        required=True,
        validate=validate.OneOf(['pdf', 'excel', 'csv', 'json'])
    )
    
    agrupacion = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['mes', 'trimestre', 'año', 'parroquia', 'celebrante'])
    )
    
    campos_incluir = fields.List(
        fields.String(),
        missing=[
            'fecha_bautismo', 'catequizando_nombre', 'parroquia_bautismo',
            'sacerdote_celebrante', 'padrinos', 'tipo_bautismo'
        ]
    )
    
    ordenamiento = TrimmedString(
        missing='fecha_bautismo',
        validate=validate.OneOf([
            'fecha_bautismo', 'catequizando_nombre', 'parroquia_bautismo',
            'sacerdote_celebrante'
        ])
    )
    
    orden_direccion = TrimmedString(
        missing='asc',
        validate=validate.OneOf(['asc', 'desc'])
    )
    
    @validates_schema
    def validate_reporte(self, data, **kwargs):
        """Validaciones para reporte de bautismo."""
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError({'fecha_fin': 'La fecha fin debe ser posterior a la fecha inicio'})
        
        # Validar que el período no sea muy extenso para ciertos reportes
        if fecha_inicio and fecha_fin:
            diferencia_dias = (fecha_fin - fecha_inicio).days
            tipo_reporte = data.get('tipo_reporte')
            
            if tipo_reporte == 'mensual' and diferencia_dias > 31:
                raise ValidationError({'fecha_fin': 'Para reporte mensual el período no puede exceder 31 días'})
            
            if diferencia_dias > 3650:  # 10 años
                raise ValidationError({'fecha_fin': 'El período del reporte no puede exceder 10 años'})