"""
Schemas de usuario para el sistema de catequesis.
Maneja validaciones para gestión de usuarios, perfiles y configuraciones.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, date
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, DocumentoIdentidad, Telefono,
    FechaNacimiento, EnumField, register_schema, PositiveInteger,
    NonNegativeInteger, NonNegativeDecimal
)


@register_schema('usuario_create')
class UsuarioCreateSchema(BaseSchema):
    """Schema para creación de usuarios."""
    
    # Información de acceso
    username = TrimmedString(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(
                r'^[a-zA-Z0-9_.-]+$',
                error='El username solo puede contener letras, números, puntos, guiones y guiones bajos'
            )
        ]
    )
    
    email = Email(required=True)
    
    password = TrimmedString(
        required=True,
        validate=validate.Length(min=8, max=128),
        load_only=True
    )
    
    # Información personal
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
        validate=validate.OneOf(['CC', 'TI', 'CE', 'PA', 'NIT'])
    )
    
    fecha_nacimiento = FechaNacimiento(allow_none=True)
    
    genero = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['M', 'F', 'O'])
    )
    
    # Información de contacto
    telefono = Telefono(allow_none=True)
    telefono_alternativo = Telefono(allow_none=True)
    direccion = TrimmedString(allow_none=True, validate=validate.Length(max=255))
    
    # Ubicación
    pais = TrimmedString(allow_none=True, missing='Colombia')
    departamento = TrimmedString(allow_none=True)
    ciudad = TrimmedString(allow_none=True)
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Configuraciones
    timezone = TrimmedString(missing='America/Bogota')
    language = TrimmedString(missing='es', validate=validate.OneOf(['es', 'en']))
    
    # Estado y roles
    is_active = fields.Boolean(missing=True)
    is_staff = fields.Boolean(missing=False)
    roles = fields.List(fields.Integer(), missing=[])
    
    # Información específica del sistema de catequesis
    parroquia_id = PositiveInteger(allow_none=True)
    codigo_empleado = TrimmedString(allow_none=True, validate=validate.Length(max=20))
    cargo = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    nivel_acceso = TrimmedString(
        missing='basico',
        validate=validate.OneOf(['basico', 'intermedio', 'avanzado', 'administrador'])
    )
    
    # Configuraciones de notificación
    notificaciones_email = fields.Boolean(missing=True)
    notificaciones_sms = fields.Boolean(missing=False)
    notificaciones_push = fields.Boolean(missing=True)
    
    # Información de emergencia
    contacto_emergencia_nombre = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    contacto_emergencia_telefono = Telefono(allow_none=True)
    contacto_emergencia_relacion = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))
    
    @validates_schema
    def validate_user_data(self, data, **kwargs):
        """Validaciones específicas del usuario."""
        # Validar coherencia de fechas
        fecha_nacimiento = data.get('fecha_nacimiento')
        if fecha_nacimiento:
            edad = (date.today() - fecha_nacimiento).days / 365.25
            if edad < 16:
                raise ValidationError({'fecha_nacimiento': 'El usuario debe ser mayor de 16 años'})
        
        # Validar documento según tipo
        documento = data.get('documento_identidad', '').strip()
        tipo_doc = data.get('tipo_documento')
        
        if documento and tipo_doc:
            if tipo_doc in ['CC', 'TI'] and not documento.isdigit():
                raise ValidationError({'documento_identidad': f'{tipo_doc} debe contener solo números'})
            
            if tipo_doc == 'NIT' and not re.match(r'^\d{9}-\d$', documento):
                raise ValidationError({'documento_identidad': 'NIT debe tener formato 123456789-0'})


@register_schema('usuario_update')
class UsuarioUpdateSchema(BaseSchema):
    """Schema para actualización de usuarios."""
    
    # Información personal (no se puede cambiar username ni email aquí)
    nombres = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    apellidos = TrimmedString(allow_none=True, validate=validate.Length(min=2, max=100))
    fecha_nacimiento = FechaNacimiento(allow_none=True)
    genero = TrimmedString(allow_none=True, validate=validate.OneOf(['M', 'F', 'O']))
    
    # Información de contacto
    telefono = Telefono(allow_none=True)
    telefono_alternativo = Telefono(allow_none=True)
    direccion = TrimmedString(allow_none=True, validate=validate.Length(max=255))
    
    # Ubicación
    departamento = TrimmedString(allow_none=True)
    ciudad = TrimmedString(allow_none=True)
    codigo_postal = TrimmedString(allow_none=True, validate=validate.Length(max=10))
    
    # Configuraciones
    timezone = TrimmedString(allow_none=True)
    language = TrimmedString(allow_none=True, validate=validate.OneOf(['es', 'en']))
    
    # Información específica del sistema
    cargo = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    
    # Configuraciones de notificación
    notificaciones_email = fields.Boolean(allow_none=True)
    notificaciones_sms = fields.Boolean(allow_none=True)
    notificaciones_push = fields.Boolean(allow_none=True)
    
    # Información de emergencia
    contacto_emergencia_nombre = TrimmedString(allow_none=True, validate=validate.Length(max=100))
    contacto_emergencia_telefono = Telefono(allow_none=True)
    contacto_emergencia_relacion = TrimmedString(allow_none=True, validate=validate.Length(max=50))
    
    # Observaciones
    observaciones = TrimmedString(allow_none=True, validate=validate.Length(max=1000))


@register_schema('usuario_response')
class UsuarioResponseSchema(BaseSchema):
    """Schema para respuesta de usuario."""
    
    # Información básica
    id = PositiveInteger(required=True)
    username = TrimmedString(required=True)
    email = Email(required=True)
    
    # Información personal
    nombres = TrimmedString(required=True)
    apellidos = TrimmedString(required=True)
    nombre_completo = TrimmedString(dump_only=True)
    documento_identidad = TrimmedString(allow_none=True)
    tipo_documento = TrimmedString(allow_none=True)
    fecha_nacimiento = fields.Date(allow_none=True)
    edad = PositiveInteger(dump_only=True, allow_none=True)
    genero = TrimmedString(allow_none=True)
    
    # Información de contacto
    telefono = TrimmedString(allow_none=True)
    telefono_alternativo = TrimmedString(allow_none=True)
    direccion = TrimmedString(allow_none=True)
    
    # Ubicación
    pais = TrimmedString(allow_none=True)
    departamento = TrimmedString(allow_none=True)
    ciudad = TrimmedString(allow_none=True)
    codigo_postal = TrimmedString(allow_none=True)
    
    # Configuraciones
    timezone = TrimmedString()
    language = TrimmedString()
    
    # Estado
    is_active = fields.Boolean(required=True)
    is_staff = fields.Boolean(required=True)
    is_verified = fields.Boolean(required=True)
    
    # Información del sistema
    parroquia_id = PositiveInteger(allow_none=True)
    parroquia_nombre = TrimmedString(dump_only=True, allow_none=True)
    codigo_empleado = TrimmedString(allow_none=True)
    cargo = TrimmedString(allow_none=True)
    nivel_acceso = TrimmedString()
    
    # Roles y permisos
    roles = fields.List(fields.Nested('RoleSchema'), dump_only=True)
    permissions = fields.List(fields.String(), dump_only=True)
    
    # Configuraciones de notificación
    notificaciones_email = fields.Boolean()
    notificaciones_sms = fields.Boolean()
    notificaciones_push = fields.Boolean()
    
    # Información de emergencia
    contacto_emergencia_nombre = TrimmedString(allow_none=True)
    contacto_emergencia_telefono = TrimmedString(allow_none=True)
    contacto_emergencia_relacion = TrimmedString(allow_none=True)
    
    # Fechas importantes
    date_joined = fields.DateTime(required=True)
    last_login = fields.DateTime(allow_none=True)
    last_activity = fields.DateTime(allow_none=True)
    
    # Avatar
    avatar_url = fields.Url(allow_none=True)
    
    # Estadísticas
    login_count = NonNegativeInteger(dump_only=True)
    failed_login_attempts = NonNegativeInteger(dump_only=True)
    
    # Observaciones (solo para staff)
    observaciones = TrimmedString(allow_none=True)


@register_schema('usuario_profile')
class UsuarioProfileSchema(BaseSchema):
    """Schema para perfil público de usuario."""
    
    id = PositiveInteger(required=True)
    username = TrimmedString(required=True)
    nombres = TrimmedString(required=True)
    apellidos = TrimmedString(required=True)
    nombre_completo = TrimmedString(dump_only=True)
    cargo = TrimmedString(allow_none=True)
    avatar_url = fields.Url(allow_none=True)
    is_active = fields.Boolean(required=True)
    date_joined = fields.DateTime(required=True)


@register_schema('usuario_admin_update')
class UsuarioAdminUpdateSchema(UsuarioUpdateSchema):
    """Schema para actualización de usuarios por administradores."""
    
    # Campos adicionales que solo admin puede cambiar
    email = Email(allow_none=True)
    is_active = fields.Boolean(allow_none=True)
    is_staff = fields.Boolean(allow_none=True)
    is_verified = fields.Boolean(allow_none=True)
    
    parroquia_id = PositiveInteger(allow_none=True)
    codigo_empleado = TrimmedString(allow_none=True, validate=validate.Length(max=20))
    nivel_acceso = TrimmedString(
        allow_none=True,
        validate=validate.OneOf(['basico', 'intermedio', 'avanzado', 'administrador'])
    )
    
    roles = fields.List(fields.Integer(), allow_none=True)
    
    # Forzar cambio de contraseña
    force_password_change = fields.Boolean(allow_none=True)


@register_schema('usuario_search')
class UsuarioSearchSchema(BaseSchema):
    """Schema para búsqueda de usuarios."""
    
    query = TrimmedString(allow_none=True, validate=validate.Length(min=1, max=100))
    
    # Filtros específicos
    is_active = fields.Boolean(allow_none=True)
    is_staff = fields.Boolean(allow_none=True)
    is_verified = fields.Boolean(allow_none=True)
    parroquia_id = PositiveInteger(allow_none=True)
    role_id = PositiveInteger(allow_none=True)
    nivel_acceso = TrimmedString(allow_none=True)
    
    # Filtros de fecha
    date_joined_from = fields.Date(allow_none=True)
    date_joined_to = fields.Date(allow_none=True)
    last_login_from = fields.Date(allow_none=True)
    last_login_to = fields.Date(allow_none=True)
    
    # Paginación
    page = PositiveInteger(missing=1)
    per_page = PositiveInteger(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = TrimmedString(
        missing='nombre_completo',
        validate=validate.OneOf([
            'nombre_completo', 'username', 'email', 'date_joined',
            'last_login', 'cargo'
        ])
    )
    sort_order = TrimmedString(
        missing='asc',
        validate=validate.OneOf(['asc', 'desc'])
    )


@register_schema('usuario_stats')
class UsuarioStatsSchema(BaseSchema):
    """Schema para estadísticas de usuario."""
    
    total_usuarios = NonNegativeInteger(required=True)
    usuarios_activos = NonNegativeInteger(required=True)
    usuarios_staff = NonNegativeInteger(required=True)
    usuarios_verificados = NonNegativeInteger(required=True)
    
    nuevos_hoy = NonNegativeInteger(required=True)
    nuevos_semana = NonNegativeInteger(required=True)
    nuevos_mes = NonNegativeInteger(required=True)
    
    logins_hoy = NonNegativeInteger(required=True)
    logins_semana = NonNegativeInteger(required=True)
    
    por_nivel_acceso = fields.Dict(
        keys=fields.String(),
        values=fields.Integer()
    )
    
    por_parroquia = fields.List(fields.Dict())
    
    usuarios_recientes = fields.List(fields.Nested(UsuarioProfileSchema))


@register_schema('usuario_activity')
class UsuarioActivitySchema(BaseSchema):
    """Schema para actividad de usuario."""
    
    id = PositiveInteger(required=True)
    user_id = PositiveInteger(required=True)
    action = TrimmedString(required=True)
    description = TrimmedString(allow_none=True)
    ip_address = TrimmedString(allow_none=True)
    user_agent = TrimmedString(allow_none=True)
    timestamp = fields.DateTime(required=True)
    
    # Información adicional
    module = TrimmedString(allow_none=True)
    object_type = TrimmedString(allow_none=True)
    object_id = PositiveInteger(allow_none=True)
    changes = fields.Dict(allow_none=True)


@register_schema('usuario_preferences')
class UsuarioPreferencesSchema(BaseSchema):
    """Schema para preferencias de usuario."""
    
    # Preferencias de interfaz
    theme = TrimmedString(
        missing='light',
        validate=validate.OneOf(['light', 'dark', 'auto'])
    )
    sidebar_collapsed = fields.Boolean(missing=False)
    items_per_page = PositiveInteger(
        missing=20,
        validate=validate.Range(min=10, max=100)
    )
    
    # Preferencias de notificación
    email_notifications = fields.Dict(missing={
        'login_alerts': True,
        'system_updates': True,
        'weekly_summary': False
    })
    
    push_notifications = fields.Dict(missing={
        'new_messages': True,
        'reminders': True,
        'urgent_alerts': True
    })
    
    # Preferencias de privacidad
    show_email = fields.Boolean(missing=False)
    show_phone = fields.Boolean(missing=False)
    allow_contact = fields.Boolean(missing=True)
    
    # Configuración regional
    date_format = TrimmedString(
        missing='DD/MM/YYYY',
        validate=validate.OneOf(['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD'])
    )
    time_format = TrimmedString(
        missing='24h',
        validate=validate.OneOf(['12h', '24h'])
    )
    first_day_week = TrimmedString(
        missing='monday',
        validate=validate.OneOf(['sunday', 'monday'])
    )


@register_schema('usuario_bulk_action')
class UsuarioBulkActionSchema(BaseSchema):
    """Schema para acciones en lote sobre usuarios."""
    
    user_ids = fields.List(
        PositiveInteger(),
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    
    action = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'activate', 'deactivate', 'verify', 'unverify',
            'force_password_change', 'assign_role', 'remove_role',
            'send_notification', 'export'
        ])
    )
    
    # Parámetros adicionales según la acción
    role_id = PositiveInteger(allow_none=True)
    notification_message = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    reason = TrimmedString(allow_none=True, validate=validate.Length(max=255))
    
    @validates_schema
    def validate_action_requirements(self, data, **kwargs):
        """Valida requisitos según la acción."""
        action = data.get('action')
        
        if action in ['assign_role', 'remove_role'] and not data.get('role_id'):
            raise ValidationError({'role_id': 'ID de rol requerido para esta acción'})
        
        if action == 'send_notification' and not data.get('notification_message'):
            raise ValidationError({'notification_message': 'Mensaje requerido para enviar notificación'})


@register_schema('usuario_import')
class UsuarioImportSchema(BaseSchema):
    """Schema para importación masiva de usuarios."""
    
    file_format = TrimmedString(
        required=True,
        validate=validate.OneOf(['csv', 'xlsx', 'json'])
    )
    
    # Configuración de importación
    skip_header = fields.Boolean(missing=True)
    delimiter = TrimmedString(missing=',', validate=validate.Length(max=1))
    encoding = TrimmedString(missing='utf-8')
    
    # Mapeo de columnas
    column_mapping = fields.Dict(
        keys=fields.String(),
        values=fields.String(),
        required=True
    )
    
    # Opciones de procesamiento
    update_existing = fields.Boolean(missing=False)
    send_welcome_email = fields.Boolean(missing=True)
    default_password = TrimmedString(allow_none=True)
    force_password_change = fields.Boolean(missing=True)
    default_role_id = PositiveInteger(allow_none=True)
    
    # Validaciones
    validate_emails = fields.Boolean(missing=True)
    validate_documents = fields.Boolean(missing=True)
    skip_invalid_rows = fields.Boolean(missing=True)
    
    @validates_schema
    def validate_import_config(self, data, **kwargs):
        """Valida configuración de importación."""
        mapping = data.get('column_mapping', {})
        
        # Verificar campos obligatorios en el mapeo
        required_fields = ['username', 'email', 'nombres', 'apellidos']
        missing_fields = [field for field in required_fields if field not in mapping.values()]
        
        if missing_fields:
            raise ValidationError({
                'column_mapping': f'Mapeo faltante para campos obligatorios: {", ".join(missing_fields)}'
            })


@register_schema('usuario_export')
class UsuarioExportSchema(BaseSchema):
    """Schema para exportación de usuarios."""
    
    format = TrimmedString(
        required=True,
        validate=validate.OneOf(['csv', 'xlsx', 'json', 'pdf'])
    )
    
    # Filtros de exportación
    user_ids = fields.List(PositiveInteger(), allow_none=True)
    filters = fields.Dict(allow_none=True)
    
    # Campos a incluir
    include_fields = fields.List(
        fields.String(),
        missing=[
            'username', 'email', 'nombres', 'apellidos',
            'documento_identidad', 'telefono', 'fecha_nacimiento',
            'is_active', 'date_joined'
        ]
    )
    
    # Opciones de formato
    include_headers = fields.Boolean(missing=True)
    date_format = TrimmedString(missing='YYYY-MM-DD')
    delimiter = TrimmedString(missing=',', validate=validate.OneOf([',', ';', '\t']))
    encoding = TrimmedString(missing='utf-8')
    
    # Configuraciones de privacidad
    anonymize_sensitive = fields.Boolean(missing=False)
    mask_documents = fields.Boolean(missing=True)
    mask_phones = fields.Boolean(missing=True)


@register_schema('usuario_role_assignment')
class UsuarioRoleAssignmentSchema(BaseSchema):
    """Schema para asignación de roles a usuarios."""
    
    user_id = PositiveInteger(required=True)
    role_ids = fields.List(
        PositiveInteger(),
        required=True,
        validate=validate.Length(min=1)
    )
    reason = TrimmedString(allow_none=True, validate=validate.Length(max=255))
    effective_date = fields.Date(allow_none=True)
    expiry_date = fields.Date(allow_none=True)
    
    @validates_schema
    def validate_dates(self, data, **kwargs):
        """Valida fechas de vigencia."""
        effective = data.get('effective_date')
        expiry = data.get('expiry_date')
        
        if effective and expiry and effective >= expiry:
            raise ValidationError({'expiry_date': 'La fecha de expiración debe ser posterior a la efectiva'})


@register_schema('usuario_permission_check')
class UsuarioPermissionCheckSchema(BaseSchema):
    """Schema para verificación de permisos."""
    
    user_id = PositiveInteger(required=True)
    permission = TrimmedString(required=True)
    object_type = TrimmedString(allow_none=True)
    object_id = PositiveInteger(allow_none=True)


@register_schema('usuario_session_management')
class UsuarioSessionManagementSchema(BaseSchema):
    """Schema para gestión de sesiones de usuario."""
    
    user_id = PositiveInteger(required=True)
    action = TrimmedString(
        required=True,
        validate=validate.OneOf(['list', 'terminate', 'terminate_all', 'terminate_others'])
    )
    session_id = TrimmedString(allow_none=True)
    reason = TrimmedString(allow_none=True, validate=validate.Length(max=255))
    
    @validates_schema
    def validate_session_action(self, data, **kwargs):
        """Valida acciones de sesión."""
        action = data.get('action')
        session_id = data.get('session_id')
        
        if action == 'terminate' and not session_id:
            raise ValidationError({'session_id': 'ID de sesión requerido para terminar sesión específica'})


@register_schema('usuario_security_log')
class UsuarioSecurityLogSchema(BaseSchema):
    """Schema para logs de seguridad de usuario."""
    
    user_id = PositiveInteger(required=True)
    event_type = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'login_success', 'login_failure', 'logout', 'password_change',
            'password_reset', 'email_change', 'profile_update', 'permission_change',
            'role_assignment', 'account_lock', 'account_unlock', 'suspicious_activity'
        ])
    )
    description = TrimmedString(required=True)
    ip_address = TrimmedString(allow_none=True)
    user_agent = TrimmedString(allow_none=True)
    location = TrimmedString(allow_none=True)
    risk_level = TrimmedString(
        missing='low',
        validate=validate.OneOf(['low', 'medium', 'high', 'critical'])
    )
    metadata = fields.Dict(allow_none=True)
    timestamp = fields.DateTime(required=True, missing=datetime.utcnow)


@register_schema('usuario_notification_settings')
class UsuarioNotificationSettingsSchema(BaseSchema):
    """Schema para configuración de notificaciones de usuario."""
    
    # Notificaciones por email
    email_enabled = fields.Boolean(missing=True)
    email_login_alerts = fields.Boolean(missing=True)
    email_security_alerts = fields.Boolean(missing=True)
    email_system_updates = fields.Boolean(missing=False)
    email_marketing = fields.Boolean(missing=False)
    email_weekly_digest = fields.Boolean(missing=False)
    
    # Notificaciones por SMS
    sms_enabled = fields.Boolean(missing=False)
    sms_security_alerts = fields.Boolean(missing=False)
    sms_urgent_only = fields.Boolean(missing=True)
    
    # Notificaciones push
    push_enabled = fields.Boolean(missing=True)
    push_new_messages = fields.Boolean(missing=True)
    push_reminders = fields.Boolean(missing=True)
    push_updates = fields.Boolean(missing=False)
    
    # Horarios de notificación
    quiet_hours_enabled = fields.Boolean(missing=False)
    quiet_hours_start = fields.Time(allow_none=True)
    quiet_hours_end = fields.Time(allow_none=True)
    
    # Frecuencia de resúmenes
    digest_frequency = TrimmedString(
        missing='weekly',
        validate=validate.OneOf(['daily', 'weekly', 'monthly', 'never'])
    )
    
    @validates_schema
    def validate_quiet_hours(self, data, **kwargs):
        """Valida horarios de silencio."""
        enabled = data.get('quiet_hours_enabled')
        start = data.get('quiet_hours_start')
        end = data.get('quiet_hours_end')
        
        if enabled and (not start or not end):
            raise ValidationError('Horarios de inicio y fin son requeridos cuando las horas de silencio están habilitadas')


@register_schema('usuario_password_policy')
class UsuarioPasswordPolicySchema(BaseSchema):
    """Schema para política de contraseñas."""
    
    min_length = PositiveInteger(missing=8, validate=validate.Range(min=6, max=128))
    max_length = PositiveInteger(missing=128, validate=validate.Range(min=8, max=256))
    
    require_uppercase = fields.Boolean(missing=True)
    require_lowercase = fields.Boolean(missing=True)
    require_numbers = fields.Boolean(missing=True)
    require_special = fields.Boolean(missing=True)
    
    min_uppercase = NonNegativeInteger(missing=1)
    min_lowercase = NonNegativeInteger(missing=1)
    min_numbers = NonNegativeInteger(missing=1)
    min_special = NonNegativeInteger(missing=1)
    
    max_age_days = PositiveInteger(allow_none=True, validate=validate.Range(min=30, max=365))
    history_count = NonNegativeInteger(missing=5, validate=validate.Range(max=24))
    
    lockout_attempts = PositiveInteger(missing=5, validate=validate.Range(min=3, max=10))
    lockout_duration_minutes = PositiveInteger(missing=30, validate=validate.Range(min=5, max=1440))
    
    @validates_schema
    def validate_policy(self, data, **kwargs):
        """Valida coherencia de la política."""
        min_len = data.get('min_length', 8)
        max_len = data.get('max_length', 128)
        
        if min_len >= max_len:
            raise ValidationError('La longitud mínima debe ser menor que la máxima')
        
        # Verificar que los requisitos mínimos no excedan la longitud mínima
        total_required = sum([
            data.get('min_uppercase', 0),
            data.get('min_lowercase', 0),
            data.get('min_numbers', 0),
            data.get('min_special', 0)
        ])
        
        if total_required > min_len:
            raise ValidationError('La suma de requisitos mínimos excede la longitud mínima de contraseña')


# Schemas específicos para diferentes tipos de usuario en el sistema de catequesis

@register_schema('catequista_profile')
class CatequistaProfileSchema(UsuarioResponseSchema):
    """Schema extendido para perfil de catequista."""
    
    codigo_catequista = TrimmedString(allow_none=True)
    fecha_ingreso = fields.Date(allow_none=True)
    especialidad = TrimmedString(allow_none=True)
    nivel_catequesis = TrimmedString(allow_none=True)
    años_experiencia = NonNegativeInteger(allow_none=True)
    certificaciones = fields.List(fields.String(), missing=[])
    grupos_asignados = fields.List(fields.Dict(), dump_only=True)
    horario_disponible = fields.Dict(allow_none=True)
    calificacion_promedio = NonNegativeDecimal(dump_only=True, allow_none=True)


@register_schema('coordinador_profile')
class CoordinadorProfileSchema(UsuarioResponseSchema):
    """Schema extendido para perfil de coordinador."""
    
    codigo_coordinador = TrimmedString(allow_none=True)
    area_responsabilidad = TrimmedString(allow_none=True)
    catequistas_supervisados = PositiveInteger(dump_only=True, allow_none=True)
    programas_coordinados = fields.List(fields.String(), missing=[])
    nivel_autoridad = TrimmedString(
        missing='local',
        validate=validate.OneOf(['local', 'zonal', 'diocesano', 'nacional'])
    )


@register_schema('administrador_profile')
class AdministradorProfileSchema(UsuarioResponseSchema):
    """Schema extendido para perfil de administrador."""
    
    permisos_especiales = fields.List(fields.String(), dump_only=True)
    modulos_acceso = fields.List(fields.String(), dump_only=True)
    nivel_administracion = TrimmedString(
        missing='basico',
        validate=validate.OneOf(['basico', 'avanzado', 'super_admin'])
    )
    ultimo_backup = fields.DateTime(dump_only=True, allow_none=True)
    configuraciones_sistema = fields.Dict(dump_only=True, allow_none=True)