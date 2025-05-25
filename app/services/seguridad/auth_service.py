"""
Servicio de autenticación para el sistema de catequesis.
Maneja login, logout, registro, recuperación de contraseñas y sesiones.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import uuid
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from app.services.base_service import BaseService
from app.models.seguridad.usuario_model import Usuario
from app.models.seguridad.sesion_model import Sesion
from app.models.seguridad.token_recuperacion_model import TokenRecuperacion
from app.schemas.seguridad.auth_schema import (
    LoginSchema, LoginResponseSchema, RegisterSchema, 
    PasswordResetRequestSchema, PasswordResetSchema,
    RefreshTokenSchema, LogoutSchema
)
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.core.exceptions import (
    AuthenticationException, ValidationException, 
    NotFoundException, BusinessLogicException
)
from app.utils.email import send_email
from app.utils.rate_limit import RateLimiter
from app.utils.device_detection import get_device_info
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio de autenticación y gestión de sesiones."""
    
    def __init__(self, db: Session):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.rate_limiter = RateLimiter()
        
    # ==========================================
    # AUTENTICACIÓN PRINCIPAL
    # ==========================================
    
    def login(self, login_data: Dict[str, Any], request_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Autentica un usuario y crea una nueva sesión.
        
        Args:
            login_data: Datos de login (email/username y password)
            request_info: Información de la petición (IP, user agent, etc.)
            
        Returns:
            Dict con tokens de acceso y información del usuario
            
        Raises:
            AuthenticationException: Si las credenciales son inválidas
            ValidationException: Si los datos son inválidos
        """
        try:
            # Validar datos de entrada
            schema = LoginSchema()
            validated_data = schema.load(login_data)
            
            identifier = validated_data['identifier']  # email o username
            password = validated_data['password']
            remember_me = validated_data.get('remember_me', False)
            
            # Rate limiting
            client_ip = request_info.get('client_ip', 'unknown') if request_info else 'unknown'
            if not self.rate_limiter.allow_request(f"login:{client_ip}", max_requests=5, window_minutes=15):
                raise AuthenticationException("Demasiados intentos de login. Intente más tarde.")
            
            # Buscar usuario por email o username
            user = self._find_user_by_identifier(identifier)
            
            if not user:
                self._log_failed_login(identifier, "Usuario no encontrado", request_info)
                raise AuthenticationException("Credenciales inválidas")
            
            # Verificar que el usuario esté activo
            if not user.activo:
                self._log_failed_login(identifier, "Usuario inactivo", request_info)
                raise AuthenticationException("Usuario inactivo. Contacte al administrador.")
            
            # Verificar contraseña
            if not self._verify_password(password, user.password_hash):
                self._log_failed_login(identifier, "Contraseña incorrecta", request_info, user.id)
                self._increment_failed_attempts(user)
                raise AuthenticationException("Credenciales inválidas")
            
            # Verificar si la cuenta está bloqueada por intentos fallidos
            if self._is_account_locked(user):
                raise AuthenticationException("Cuenta bloqueada por múltiples intentos fallidos")
            
            # Verificar si requiere verificación adicional
            if user.requiere_2fa and not validated_data.get('totp_code'):
                return {
                    'requires_2fa': True,
                    'temp_token': self._create_temp_token(user.id),
                    'message': 'Se requiere código de verificación'
                }
            
            # Verificar código 2FA si está presente
            if user.requiere_2fa and validated_data.get('totp_code'):
                if not self._verify_2fa_code(user, validated_data['totp_code']):
                    raise AuthenticationException("Código de verificación inválido")
            
            # Login exitoso - crear sesión
            session = self._create_session(user, request_info, remember_me)
            
            # Generar tokens
            access_token = create_access_token(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                    "roles": [role.nombre for role in user.roles],
                    "session_id": str(session.id)
                }
            )
            
            refresh_token = create_refresh_token(
                data={"sub": str(user.id), "session_id": str(session.id)}
            )
            
            # Actualizar información del usuario
            user.ultimo_login = datetime.utcnow()
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
            
            self.db.commit()
            
            # Log de login exitoso
            self._log_successful_login(user, request_info, session.id)
            
            # Serializar respuesta
            response_schema = LoginResponseSchema()
            return response_schema.dump({
                'user': user,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'bearer',
                'expires_in': settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                'session_id': str(session.id)
            })
            
        except ValidationException:
            raise
        except AuthenticationException:
            raise
        except Exception as e:
            logger.error(f"Error inesperado en login: {str(e)}")
            raise AuthenticationException("Error interno del servidor")
    
    def logout(self, logout_data: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cierra la sesión del usuario.
        
        Args:
            logout_data: Datos de logout
            current_user: Usuario actual
            
        Returns:
            Dict con confirmación del logout
        """
        try:
            schema = LogoutSchema()
            validated_data = schema.load(logout_data)
            
            user_id = current_user['id']
            session_id = current_user.get('session_id')
            logout_all = validated_data.get('logout_all', False)
            
            if logout_all:
                # Cerrar todas las sesiones del usuario
                self.db.query(Sesion).filter(
                    and_(
                        Sesion.usuario_id == user_id,
                        Sesion.activa == True
                    )
                ).update({
                    'activa': False,
                    'fecha_cierre': datetime.utcnow(),
                    'razon_cierre': 'logout_all'
                })
                
                sessions_closed = self.db.query(Sesion).filter(
                    Sesion.usuario_id == user_id,
                    Sesion.activa == False,
                    Sesion.razon_cierre == 'logout_all'
                ).count()
                
                message = f"Se cerraron {sessions_closed} sesiones"
                
            else:
                # Cerrar solo la sesión actual
                if session_id:
                    session = self.db.query(Sesion).filter(
                        and_(
                            Sesion.id == session_id,
                            Sesion.usuario_id == user_id,
                            Sesion.activa == True
                        )
                    ).first()
                    
                    if session:
                        session.activa = False
                        session.fecha_cierre = datetime.utcnow()
                        session.razon_cierre = 'logout'
                
                message = "Sesión cerrada exitosamente"
            
            self.db.commit()
            
            # Log del logout
            logger.info(f"Usuario {user_id} cerró sesión. Logout all: {logout_all}")
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error en logout: {str(e)}")
            self.db.rollback()
            raise BusinessLogicException("Error cerrando sesión")
    
    def refresh_token(self, refresh_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Renueva el token de acceso usando el refresh token.
        
        Args:
            refresh_data: Datos con refresh token
            
        Returns:
            Dict con nuevo access token
        """
        try:
            schema = RefreshTokenSchema()
            validated_data = schema.load(refresh_data)
            
            refresh_token = validated_data['refresh_token']
            
            # Verificar refresh token
            try:
                payload = verify_token(refresh_token)
                user_id = int(payload.get("sub"))
                session_id = payload.get("session_id")
                
            except JWTError:
                raise AuthenticationException("Refresh token inválido")
            
            # Verificar que el usuario existe y está activo
            user = self.db.query(Usuario).filter(
                and_(Usuario.id == user_id, Usuario.activo == True)
            ).first()
            
            if not user:
                raise AuthenticationException("Usuario no encontrado o inactivo")
            
            # Verificar que la sesión existe y está activa
            session = self.db.query(Sesion).filter(
                and_(
                    Sesion.id == session_id,
                    Sesion.usuario_id == user_id,
                    Sesion.activa == True
                )
            ).first()
            
            if not session:
                raise AuthenticationException("Sesión inválida o expirada")
            
            # Actualizar última actividad de la sesión
            session.ultima_actividad = datetime.utcnow()
            
            # Generar nuevo access token
            access_token = create_access_token(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                    "roles": [role.nombre for role in user.roles],
                    "session_id": str(session.id)
                }
            )
            
            self.db.commit()
            
            return {
                'access_token': access_token,
                'token_type': 'bearer',
                'expires_in': settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
            
        except ValidationException:
            raise
        except AuthenticationException:
            raise
        except Exception as e:
            logger.error(f"Error renovando token: {str(e)}")
            raise AuthenticationException("Error renovando token")
    
    # ==========================================
    # REGISTRO DE USUARIOS
    # ==========================================
    
    def register(self, register_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra un nuevo usuario en el sistema.
        
        Args:
            register_data: Datos de registro
            
        Returns:
            Dict con información del usuario creado
        """
        try:
            schema = RegisterSchema()
            validated_data = schema.load(register_data)
            
            # Verificar que el email no existe
            existing_user = self.db.query(Usuario).filter(
                Usuario.email == validated_data['email']
            ).first()
            
            if existing_user:
                raise ValidationException("El email ya está registrado")
            
            # Verificar que el username no existe (si se proporciona)
            if validated_data.get('username'):
                existing_username = self.db.query(Usuario).filter(
                    Usuario.username == validated_data['username']
                ).first()
                
                if existing_username:
                    raise ValidationException("El nombre de usuario ya está en uso")
            
            # Crear hash de la contraseña
            password_hash = self._hash_password(validated_data['password'])
            
            # Crear usuario
            user_data = {
                'email': validated_data['email'],
                'username': validated_data.get('username'),
                'nombres': validated_data['nombres'],
                'apellidos': validated_data['apellidos'],
                'password_hash': password_hash,
                'activo': False,  # Requiere verificación por email
                'email_verificado': False,
                'requiere_cambio_password': False,
                'created_at': datetime.utcnow()
            }
            
            user = Usuario(**user_data)
            self.db.add(user)
            self.db.flush()
            
            # Asignar rol por defecto
            self._assign_default_role(user)
            
            # Generar token de verificación
            verification_token = self._create_verification_token(user)
            
            # Enviar email de verificación
            self._send_verification_email(user, verification_token)
            
            self.db.commit()
            
            logger.info(f"Usuario registrado: {user.email}")
            
            return {
                'success': True,
                'message': 'Usuario registrado. Revise su email para verificar la cuenta.',
                'user_id': user.id,
                'email': user.email
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en registro: {str(e)}")
            raise BusinessLogicException("Error registrando usuario")
    
    # ==========================================
    # RECUPERACIÓN DE CONTRASEÑAS
    # ==========================================
    
    def request_password_reset(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solicita recuperación de contraseña.
        
        Args:
            request_data: Datos con email del usuario
            
        Returns:
            Dict con confirmación
        """
        try:
            schema = PasswordResetRequestSchema()
            validated_data = schema.load(request_data)
            
            email = validated_data['email']
            
            # Buscar usuario
            user = self.db.query(Usuario).filter(Usuario.email == email).first()
            
            if not user:
                # Por seguridad, siempre retornamos éxito
                return {
                    'success': True,
                    'message': 'Si el email existe, recibirá instrucciones de recuperación'
                }
            
            # Verificar rate limiting
            if not self.rate_limiter.allow_request(f"password_reset:{email}", max_requests=3, window_minutes=60):
                raise BusinessLogicException("Demasiadas solicitudes. Intente más tarde.")
            
            # Invalidar tokens anteriores
            self.db.query(TokenRecuperacion).filter(
                and_(
                    TokenRecuperacion.usuario_id == user.id,
                    TokenRecuperacion.usado == False,
                    TokenRecuperacion.fecha_expiracion > datetime.utcnow()
                )
            ).update({'usado': True})
            
            # Crear nuevo token
            reset_token = TokenRecuperacion(
                usuario_id=user.id,
                token=secrets.token_urlsafe(32),
                fecha_expiracion=datetime.utcnow() + timedelta(hours=1),
                usado=False,
                created_at=datetime.utcnow()
            )
            
            self.db.add(reset_token)
            
            # Enviar email
            self._send_password_reset_email(user, reset_token.token)
            
            self.db.commit()
            
            logger.info(f"Solicitud de recuperación de contraseña para: {email}")
            
            return {
                'success': True,
                'message': 'Si el email existe, recibirá instrucciones de recuperación'
            }
            
        except ValidationException:
            raise
        except BusinessLogicException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en solicitud de recuperación: {str(e)}")
            raise BusinessLogicException("Error procesando solicitud")
    
    def reset_password(self, reset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restablece la contraseña usando un token.
        
        Args:
            reset_data: Datos con token y nueva contraseña
            
        Returns:
            Dict con confirmación
        """
        try:
            schema = PasswordResetSchema()
            validated_data = schema.load(reset_data)
            
            token = validated_data['token']
            new_password = validated_data['new_password']
            
            # Buscar token válido
            reset_token = self.db.query(TokenRecuperacion).filter(
                and_(
                    TokenRecuperacion.token == token,
                    TokenRecuperacion.usado == False,
                    TokenRecuperacion.fecha_expiracion > datetime.utcnow()
                )
            ).first()
            
            if not reset_token:
                raise AuthenticationException("Token inválido o expirado")
            
            # Obtener usuario
            user = self.db.query(Usuario).filter(Usuario.id == reset_token.usuario_id).first()
            
            if not user:
                raise NotFoundException("Usuario no encontrado")
            
            # Actualizar contraseña
            user.password_hash = self._hash_password(new_password)
            user.requiere_cambio_password = False
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
            user.updated_at = datetime.utcnow()
            
            # Marcar token como usado
            reset_token.usado = True
            reset_token.fecha_uso = datetime.utcnow()
            
            # Cerrar todas las sesiones del usuario
            self.db.query(Sesion).filter(
                and_(
                    Sesion.usuario_id == user.id,
                    Sesion.activa == True
                )
            ).update({
                'activa': False,
                'fecha_cierre': datetime.utcnow(),
                'razon_cierre': 'password_reset'
            })
            
            self.db.commit()
            
            logger.info(f"Contraseña restablecida para usuario: {user.email}")
            
            return {
                'success': True,
                'message': 'Contraseña restablecida exitosamente'
            }
            
        except ValidationException:
            raise
        except (AuthenticationException, NotFoundException):
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error restableciendo contraseña: {str(e)}")
            raise BusinessLogicException("Error restableciendo contraseña")
    
    # ==========================================
    # GESTIÓN DE SESIONES
    # ==========================================
    
    def get_active_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Obtiene las sesiones activas de un usuario."""
        try:
            sessions = self.db.query(Sesion).filter(
                and_(
                    Sesion.usuario_id == user_id,
                    Sesion.activa == True
                )
            ).order_by(Sesion.ultima_actividad.desc()).all()
            
            return [
                {
                    'id': str(session.id),
                    'dispositivo': session.dispositivo,
                    'navegador': session.navegador,
                    'ip_address': session.ip_address,
                    'ubicacion': session.ubicacion,
                    'fecha_inicio': session.fecha_inicio.isoformat(),
                    'ultima_actividad': session.ultima_actividad.isoformat(),
                    'es_sesion_actual': session.id == user_id  # Esto se debe ajustar según el contexto
                }
                for session in sessions
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo sesiones activas: {str(e)}")
            raise BusinessLogicException("Error obteniendo sesiones")
    
    def revoke_session(self, session_id: str, user_id: int) -> Dict[str, Any]:
        """Revoca una sesión específica."""
        try:
            session = self.db.query(Sesion).filter(
                and_(
                    Sesion.id == session_id,
                    Sesion.usuario_id == user_id,
                    Sesion.activa == True
                )
            ).first()
            
            if not session:
                raise NotFoundException("Sesión no encontrada")
            
            session.activa = False
            session.fecha_cierre = datetime.utcnow()
            session.razon_cierre = 'revoked_by_user'
            
            self.db.commit()
            
            return {
                'success': True,
                'message': 'Sesión revocada exitosamente'
            }
            
        except NotFoundException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revocando sesión: {str(e)}")
            raise BusinessLogicException("Error revocando sesión")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _find_user_by_identifier(self, identifier: str) -> Optional[Usuario]:
        """Busca usuario por email o username."""
        return self.db.query(Usuario).filter(
            or_(
                Usuario.email == identifier,
                Usuario.username == identifier
            )
        ).first()
    
    def _hash_password(self, password: str) -> str:
        """Genera hash de contraseña."""
        return self.pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica contraseña contra hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def _create_session(self, user: Usuario, request_info: Dict[str, Any], remember_me: bool) -> Sesion:
        """Crea nueva sesión de usuario."""
        device_info = get_device_info(request_info.get('user_agent', '')) if request_info else {}
        
        session = Sesion(
            id=str(uuid.uuid4()),
            usuario_id=user.id,
            ip_address=request_info.get('client_ip', 'unknown') if request_info else 'unknown',
            user_agent=request_info.get('user_agent', 'unknown') if request_info else 'unknown',
            dispositivo=device_info.get('device', 'unknown'),
            navegador=device_info.get('browser', 'unknown'),
            ubicacion=request_info.get('location', 'unknown') if request_info else 'unknown',
            fecha_inicio=datetime.utcnow(),
            ultima_actividad=datetime.utcnow(),
            activa=True,
            recordar_sesion=remember_me
        )
        
        self.db.add(session)
        return session
    
    def _is_account_locked(self, user: Usuario) -> bool:
        """Verifica si la cuenta está bloqueada."""
        if user.bloqueado_hasta and user.bloqueado_hasta > datetime.utcnow():
            return True
        return False
    
    def _increment_failed_attempts(self, user: Usuario):
        """Incrementa intentos fallidos y bloquea si es necesario."""
        user.intentos_fallidos = (user.intentos_fallidos or 0) + 1
        
        if user.intentos_fallidos >= 5:
            user.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=30)
    
    def _verify_2fa_code(self, user: Usuario, code: str) -> bool:
        """Verifica código 2FA/TOTP."""
        # Implementar verificación TOTP
        # Esta es una implementación placeholder
        return True  # Implementar lógica real
    
    def _create_temp_token(self, user_id: int) -> str:
        """Crea token temporal para 2FA."""
        return create_access_token(
            data={"sub": str(user_id), "temp": True},
            expires_delta=timedelta(minutes=5)
        )
    
    def _assign_default_role(self, user: Usuario):
        """Asigna rol por defecto al usuario."""
        # Implementar asignación de rol por defecto
        pass
    
    def _create_verification_token(self, user: Usuario) -> str:
        """Crea token de verificación de email."""
        return secrets.token_urlsafe(32)
    
    def _send_verification_email(self, user: Usuario, token: str):
        """Envía email de verificación."""
        # Implementar envío de email
        pass
    
    def _send_password_reset_email(self, user: Usuario, token: str):
        """Envía email de recuperación de contraseña."""
        # Implementar envío de email
        pass
    
    def _log_failed_login(self, identifier: str, reason: str, request_info: Dict[str, Any], user_id: int = None):
        """Registra intento de login fallido."""
        logger.warning(f"Login fallido - Identifier: {identifier}, Razón: {reason}, IP: {request_info.get('client_ip') if request_info else 'unknown'}")
    
    def _log_successful_login(self, user: Usuario, request_info: Dict[str, Any], session_id: str):
        """Registra login exitoso."""
        logger.info(f"Login exitoso - Usuario: {user.email}, IP: {request_info.get('client_ip') if request_info else 'unknown'}, Sesión: {session_id}")