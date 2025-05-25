"""
Schemas de autenticación para el sistema de catequesis.
Maneja validaciones de login, registro, tokens y recuperación de contraseñas.
"""

from marshmallow import fields, validate, validates_schema, ValidationError, post_load
from datetime import datetime, timedelta
import re

from app.schemas.base_schema import (
    BaseSchema, TrimmedString, Email, register_schema,
    PositiveInteger, NonNegativeInteger
)


@register_schema('login_request')
class LoginRequestSchema(BaseSchema):
    """Schema para solicitudes de login."""
    
    # Puede ser username, email o documento
    identifier = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100),
        error_messages={
            'required': 'El identificador es requerido',
            'validator_failed': 'El identificador debe tener entre 3 y 100 caracteres'
        }
    )
    
    password = TrimmedString(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={
            'required': 'La contraseña es requerida'
        }
    )
    
    remember_me = fields.Boolean(missing=False)
    captcha_token = TrimmedString(allow_none=True)
    
    @validates_schema
    def validate_identifier(self, data, **kwargs):
        """Valida el formato del identificador."""
        identifier = data.get('identifier', '').strip()
        
        if not identifier:
            raise ValidationError('El identificador no puede estar vacío')
        
        # Verificar si es email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if '@' in identifier and not re.match(email_pattern, identifier):
            raise ValidationError('Formato de email inválido')


@register_schema('login_response')
class LoginResponseSchema(BaseSchema):
    """Schema para respuestas de login exitoso."""
    
    access_token = TrimmedString(required=True)
    refresh_token = TrimmedString(allow_none=True)
    token_type = TrimmedString(required=True, missing='Bearer')
    expires_in = PositiveInteger(required=True)
    expires_at = fields.DateTime(required=True)
    
    user = fields.Nested('UserProfileSchema', required=True)
    permissions = fields.List(fields.String(), missing=[])
    roles = fields.List(fields.String(), missing=[])
    
    # Información adicional de sesión
    session_id = TrimmedString(allow_none=True)
    last_login = fields.DateTime(allow_none=True)
    login_count = NonNegativeInteger(missing=0)
    
    @post_load
    def calculate_expiration(self, data, **kwargs):
        """Calcula la fecha de expiración si no está presente."""
        if 'expires_at' not in data and 'expires_in' in data:
            data['expires_at'] = datetime.utcnow() + timedelta(seconds=data['expires_in'])
        return data


@register_schema('logout_request')
class LogoutRequestSchema(BaseSchema):
    """Schema para solicitudes de logout."""
    
    token = TrimmedString(required=True)
    logout_all_devices = fields.Boolean(missing=False)


@register_schema('register_request')
class RegisterRequestSchema(BaseSchema):
    """Schema para registro de nuevos usuarios."""
    
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
        validate=validate.Length(min=8, max=128)
    )
    
    password_confirmation = TrimmedString(required=True)
    
    # Información personal básica
    nombres = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    apellidos = TrimmedString(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    
    documento_identidad = TrimmedString(
        required=True,
        validate=validate.Length(min=5, max=20)
    )
    
    tipo_documento = TrimmedString(
        required=True,
        validate=validate.OneOf(['CC', 'TI', 'CE', 'PA'])
    )
    
    telefono = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=7, max=15)
    )
    
    # Términos y condiciones
    accept_terms = fields.Boolean(
        required=True,
        validate=validate.Equal(True, error='Debe aceptar los términos y condiciones')
    )
    
    # Captcha para prevenir spam
    captcha_token = TrimmedString(allow_none=True)
    
    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """Valida que las contraseñas coincidan y cumplan requisitos."""
        password = data.get('password')
        password_confirmation = data.get('password_confirmation')
        
        if password != password_confirmation:
            raise ValidationError('Las contraseñas no coinciden')
        
        # Validar fortaleza de contraseña
        if password:
            errors = []
            
            if len(password) < 8:
                errors.append('La contraseña debe tener al menos 8 caracteres')
            
            if not re.search(r'[A-Z]', password):
                errors.append('La contraseña debe contener al menos una letra mayúscula')
            
            if not re.search(r'[a-z]', password):
                errors.append('La contraseña debe contener al menos una letra minúscula')
            
            if not re.search(r'\d', password):
                errors.append('La contraseña debe contener al menos un número')
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                errors.append('La contraseña debe contener al menos un carácter especial')
            
            if errors:
                raise ValidationError({'password': errors})
    
    @validates_schema
    def validate_document(self, data, **kwargs):
        """Valida el documento de identidad según el tipo."""
        documento = data.get('documento_identidad', '').strip()
        tipo_doc = data.get('tipo_documento')
        
        if documento and tipo_doc:
            if tipo_doc == 'CC' and not documento.isdigit():
                raise ValidationError({'documento_identidad': 'La cédula debe contener solo números'})
            
            if tipo_doc == 'TI' and not documento.isdigit():
                raise ValidationError({'documento_identidad': 'La tarjeta de identidad debe contener solo números'})


@register_schema('password_reset_request')
class PasswordResetRequestSchema(BaseSchema):
    """Schema para solicitudes de recuperación de contraseña."""
    
    email = Email(required=True)
    captcha_token = TrimmedString(allow_none=True)


@register_schema('password_reset_confirm')
class PasswordResetConfirmSchema(BaseSchema):
    """Schema para confirmación de nueva contraseña."""
    
    token = TrimmedString(required=True)
    
    new_password = TrimmedString(
        required=True,
        validate=validate.Length(min=8, max=128)
    )
    
    new_password_confirmation = TrimmedString(required=True)
    
    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """Valida que las contraseñas coincidan y cumplan requisitos."""
        password = data.get('new_password')
        password_confirmation = data.get('new_password_confirmation')
        
        if password != password_confirmation:
            raise ValidationError('Las contraseñas no coinciden')
        
        # Reutilizar validación de fortaleza
        if password:
            errors = []
            
            if len(password) < 8:
                errors.append('La contraseña debe tener al menos 8 caracteres')
            
            if not re.search(r'[A-Z]', password):
                errors.append('La contraseña debe contener al menos una letra mayúscula')
            
            if not re.search(r'[a-z]', password):
                errors.append('La contraseña debe contener al menos una letra minúscula')
            
            if not re.search(r'\d', password):
                errors.append('La contraseña debe contener al menos un número')
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                errors.append('La contraseña debe contener al menos un carácter especial')
            
            if errors:
                raise ValidationError({'new_password': errors})


@register_schema('change_password')
class ChangePasswordSchema(BaseSchema):
    """Schema para cambio de contraseña (usuario autenticado)."""
    
    current_password = TrimmedString(required=True)
    
    new_password = TrimmedString(
        required=True,
        validate=validate.Length(min=8, max=128)
    )
    
    new_password_confirmation = TrimmedString(required=True)
    
    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """Valida las contraseñas."""
        current = data.get('current_password')
        new_password = data.get('new_password')
        confirmation = data.get('new_password_confirmation')
        
        # Verificar que la nueva contraseña sea diferente
        if current == new_password:
            raise ValidationError({'new_password': 'La nueva contraseña debe ser diferente a la actual'})
        
        # Verificar confirmación
        if new_password != confirmation:
            raise ValidationError('Las contraseñas no coinciden')
        
        # Validar fortaleza
        if new_password:
            errors = []
            
            if len(new_password) < 8:
                errors.append('La contraseña debe tener al menos 8 caracteres')
            
            if not re.search(r'[A-Z]', new_password):
                errors.append('La contraseña debe contener al menos una letra mayúscula')
            
            if not re.search(r'[a-z]', new_password):
                errors.append('La contraseña debe contener al menos una letra minúscula')
            
            if not re.search(r'\d', new_password):
                errors.append('La contraseña debe contener al menos un número')
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
                errors.append('La contraseña debe contener al menos un carácter especial')
            
            if errors:
                raise ValidationError({'new_password': errors})


@register_schema('refresh_token')
class RefreshTokenSchema(BaseSchema):
    """Schema para renovación de tokens."""
    
    refresh_token = TrimmedString(required=True)


@register_schema('token_validation')
class TokenValidationSchema(BaseSchema):
    """Schema para validación de tokens."""
    
    token = TrimmedString(required=True)
    token_type = TrimmedString(missing='access', validate=validate.OneOf(['access', 'refresh']))


@register_schema('user_profile')
class UserProfileSchema(BaseSchema):
    """Schema para perfil de usuario en respuestas de auth."""
    
    id = PositiveInteger(required=True)
    username = TrimmedString(required=True)
    email = Email(required=True)
    
    nombres = TrimmedString(required=True)
    apellidos = TrimmedString(required=True)
    nombre_completo = TrimmedString(dump_only=True)
    
    documento_identidad = TrimmedString(allow_none=True)
    tipo_documento = TrimmedString(allow_none=True)
    telefono = TrimmedString(allow_none=True)
    
    # Estado del usuario
    is_active = fields.Boolean(required=True)
    is_verified = fields.Boolean(required=True)
    is_staff = fields.Boolean(missing=False)
    
    # Fechas importantes
    last_login = fields.DateTime(allow_none=True)
    date_joined = fields.DateTime(required=True)
    
    # Configuraciones del usuario
    timezone = TrimmedString(missing='America/Bogota')
    language = TrimmedString(missing='es')
    
    # Avatar/foto
    avatar_url = fields.Url(allow_none=True)


@register_schema('two_factor_setup')
class TwoFactorSetupSchema(BaseSchema):
    """Schema para configuración de autenticación de dos factores."""
    
    method = TrimmedString(
        required=True,
        validate=validate.OneOf(['totp', 'sms', 'email'])
    )
    phone_number = TrimmedString(
        allow_none=True,
        validate=validate.Length(min=10, max=15)
    )
    
    @validates_schema
    def validate_method_requirements(self, data, **kwargs):
        """Valida requisitos según el método de 2FA."""
        method = data.get('method')
        phone = data.get('phone_number')
        
        if method == 'sms' and not phone:
            raise ValidationError({'phone_number': 'El número de teléfono es requerido para SMS'})


@register_schema('two_factor_verify')
class TwoFactorVerifySchema(BaseSchema):
    """Schema para verificación de código de dos factores."""
    
    code = TrimmedString(
        required=True,
        validate=[
            validate.Length(min=6, max=8),
            validate.Regexp(r'^\d+$', error='El código debe contener solo números')
        ]
    )
    remember_device = fields.Boolean(missing=False)


@register_schema('account_verification')
class AccountVerificationSchema(BaseSchema):
    """Schema para verificación de cuenta."""
    
    verification_token = TrimmedString(required=True)


@register_schema('resend_verification')
class ResendVerificationSchema(BaseSchema):
    """Schema para reenvío de verificación."""
    
    email = Email(required=True)
    captcha_token = TrimmedString(allow_none=True)


@register_schema('session_info')
class SessionInfoSchema(BaseSchema):
    """Schema para información de sesión activa."""
    
    session_id = TrimmedString(required=True)
    user_agent = TrimmedString(allow_none=True)
    ip_address = TrimmedString(allow_none=True)
    location = TrimmedString(allow_none=True)
    device_info = TrimmedString(allow_none=True)
    created_at = fields.DateTime(required=True)
    last_activity = fields.DateTime(required=True)
    is_current = fields.Boolean(required=True)


@register_schema('security_settings')
class SecuritySettingsSchema(BaseSchema):
    """Schema para configuraciones de seguridad del usuario."""
    
    two_factor_enabled = fields.Boolean(required=True)
    two_factor_method = TrimmedString(allow_none=True)
    login_notifications = fields.Boolean(missing=True)
    suspicious_activity_alerts = fields.Boolean(missing=True)
    session_timeout = PositiveInteger(missing=3600)  # segundos
    require_password_change = fields.Boolean(missing=False)
    password_last_changed = fields.DateTime(allow_none=True)


@register_schema('login_attempt')
class LoginAttemptSchema(BaseSchema):
    """Schema para registro de intentos de login."""
    
    identifier = TrimmedString(required=True)
    ip_address = TrimmedString(required=True)
    user_agent = TrimmedString(allow_none=True)
    success = fields.Boolean(required=True)
    failure_reason = TrimmedString(allow_none=True)
    timestamp = fields.DateTime(required=True)
    location = TrimmedString(allow_none=True)
    blocked = fields.Boolean(missing=False)


@register_schema('account_lockout')
class AccountLockoutSchema(BaseSchema):
    """Schema para bloqueo de cuenta."""
    
    reason = TrimmedString(
        required=True,
        validate=validate.OneOf([
            'too_many_failed_attempts',
            'suspicious_activity',
            'admin_lock',
            'security_violation'
        ])
    )
    duration_minutes = PositiveInteger(allow_none=True)
    unlock_token = TrimmedString(allow_none=True)


@register_schema('unlock_account')
class UnlockAccountSchema(BaseSchema):
    """Schema para desbloqueo de cuenta."""
    
    unlock_token = TrimmedString(required=True)
    new_password = TrimmedString(allow_none=True)
    new_password_confirmation = TrimmedString(allow_none=True)
    
    @validates_schema
    def validate_password_if_provided(self, data, **kwargs):
        """Valida contraseña si se proporciona."""
        password = data.get('new_password')
        confirmation = data.get('new_password_confirmation')
        
        if password or confirmation:
            if password != confirmation:
                raise ValidationError('Las contraseñas no coinciden')
            
            if password and len(password) < 8:
                raise ValidationError({'new_password': 'La contraseña debe tener al menos 8 caracteres'})


@register_schema('oauth_authorize')
class OAuthAuthorizeSchema(BaseSchema):
    """Schema para autorización OAuth."""
    
    client_id = TrimmedString(required=True)
    response_type = TrimmedString(
        required=True,
        validate=validate.OneOf(['code', 'token'])
    )
    redirect_uri = fields.Url(required=True)
    scope = TrimmedString(allow_none=True)
    state = TrimmedString(allow_none=True)


@register_schema('oauth_token')
class OAuthTokenSchema(BaseSchema):
    """Schema para intercambio de token OAuth."""
    
    grant_type = TrimmedString(
        required=True,
        validate=validate.OneOf(['authorization_code', 'refresh_token'])
    )
    code = TrimmedString(allow_none=True)
    redirect_uri = fields.Url(allow_none=True)
    client_id = TrimmedString(required=True)
    client_secret = TrimmedString(required=True)
    refresh_token = TrimmedString(allow_none=True)
    
    @validates_schema
    def validate_grant_type_requirements(self, data, **kwargs):
        """Valida requisitos según el tipo de grant."""
        grant_type = data.get('grant_type')
        
        if grant_type == 'authorization_code':
            if not data.get('code'):
                raise ValidationError({'code': 'El código de autorización es requerido'})
            if not data.get('redirect_uri'):
                raise ValidationError({'redirect_uri': 'La URI de redirección es requerida'})
        
        elif grant_type == 'refresh_token':
            if not data.get('refresh_token'):
                raise ValidationError({'refresh_token': 'El refresh token es requerido'})


@register_schema('api_key_create')
class ApiKeyCreateSchema(BaseSchema):
    """Schema para creación de API keys."""
    
    name = TrimmedString(
        required=True,
        validate=validate.Length(min=3, max=100)
    )
    description = TrimmedString(allow_none=True, validate=validate.Length(max=500))
    scopes = fields.List(fields.String(), missing=[])
    expires_at = fields.DateTime(allow_none=True)
    ip_restrictions = fields.List(fields.String(), missing=[])
    
    @validates_schema
    def validate_expiration(self, data, **kwargs):
        """Valida que la fecha de expiración sea futura."""
        expires_at = data.get('expires_at')
        if expires_at and expires_at <= datetime.utcnow():
            raise ValidationError({'expires_at': 'La fecha de expiración debe ser futura'})


@register_schema('api_key_response')
class ApiKeyResponseSchema(BaseSchema):
    """Schema para respuesta de API key."""
    
    id = PositiveInteger(required=True)
    name = TrimmedString(required=True)
    description = TrimmedString(allow_none=True)
    key = TrimmedString(required=True, dump_only=True)  # Solo en creación
    key_preview = TrimmedString(dump_only=True)  # Últimos 4 caracteres
    scopes = fields.List(fields.String(), missing=[])
    created_at = fields.DateTime(required=True)
    expires_at = fields.DateTime(allow_none=True)
    last_used = fields.DateTime(allow_none=True)
    is_active = fields.Boolean(required=True)
    ip_restrictions = fields.List(fields.String(), missing=[])


@register_schema('permission')
class PermissionSchema(BaseSchema):
    """Schema para permisos."""
    
    id = PositiveInteger(dump_only=True)
    name = TrimmedString(required=True)
    codename = TrimmedString(required=True)
    description = TrimmedString(allow_none=True)
    module = TrimmedString(required=True)
    is_active = fields.Boolean(missing=True)


@register_schema('role')
class RoleSchema(BaseSchema):
    """Schema para roles."""
    
    id = PositiveInteger(dump_only=True)
    name = TrimmedString(required=True)
    description = TrimmedString(allow_none=True)
    permissions = fields.List(fields.Nested(PermissionSchema), missing=[])
    is_active = fields.Boolean(missing=True)
    is_system = fields.Boolean(dump_only=True, missing=False)


@register_schema('auth_error')
class AuthErrorSchema(BaseSchema):
    """Schema para errores de autenticación."""
    
    error = TrimmedString(required=True)
    error_description = TrimmedString(allow_none=True)
    error_code = TrimmedString(allow_none=True)
    details = fields.Dict(allow_none=True)
    
    # Información adicional para ciertos errores
    lockout_duration = PositiveInteger(allow_none=True)
    remaining_attempts = NonNegativeInteger(allow_none=True)
    unlock_token = TrimmedString(allow_none=True)
    next_attempt_at = fields.DateTime(allow_none=True)


# Schemas para validaciones específicas del sistema de catequesis
@register_schema('catequesis_user_register')
class CatequesisUserRegisterSchema(RegisterRequestSchema):
    """Schema extendido para registro en el sistema de catequesis."""
    
    # Información adicional específica del sistema
    parroquia_preferida = TrimmedString(allow_none=True)
    como_se_entero = TrimmedString(
        allow_none=True,
        validate=validate.OneOf([
            'redes_sociales', 'amigos_familia', 'parroquia',
            'sitio_web', 'publicidad', 'otro'
        ])
    )
    
    # Información de contacto de emergencia
    contacto_emergencia_nombre = TrimmedString(allow_none=True)
    contacto_emergencia_telefono = TrimmedString(allow_none=True)
    contacto_emergencia_relacion = TrimmedString(allow_none=True)
    
    # Notificaciones preferidas
    notificaciones_email = fields.Boolean(missing=True)
    notificaciones_sms = fields.Boolean(missing=False)
    notificaciones_whatsapp = fields.Boolean(missing=False)


@register_schema('catequista_login')
class CatequistaLoginSchema(LoginRequestSchema):
    """Schema especializado para login de catequistas."""
    
    codigo_catequista = TrimmedString(allow_none=True)
    
    @validates_schema
    def validate_catequista_info(self, data, **kwargs):
        """Validaciones adicionales para catequistas."""
        identifier = data.get('identifier', '')
        codigo = data.get('codigo_catequista')
        
        # Si proporciona código de catequista, debe ser válido
        if codigo and len(codigo) < 3:
            raise ValidationError({'codigo_catequista': 'Código de catequista inválido'})