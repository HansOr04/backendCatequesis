"""
Middleware de autenticación y autorización.
Maneja JWT tokens, sesiones y control de acceso basado en roles.
"""

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict, Any, List, Optional, Set, Callable
import logging
import jwt
import time
from datetime import datetime, timedelta
from functools import wraps

from app.core.config import get_settings
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.services.seguridad.auth_service import AuthService
from app.services.seguridad.session_service import SessionService

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware principal de autenticación."""
    
    def __init__(
        self,
        app,
        secret_key: str = None,
        algorithm: str = "HS256",
        auto_error: bool = True,
        public_paths: List[str] = None,
        optional_auth_paths: List[str] = None
    ):
        super().__init__(app)
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm
        self.auto_error = auto_error
        self.auth_service = AuthService()
        self.session_service = SessionService()
        
        # Rutas públicas (sin autenticación)
        self.public_paths = set(public_paths or [
            "/",
            "/health",
            "/healthz",
            "/ping",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/forgot-password",
            "/auth/reset-password",
            "/static"
        ])
        
        # Rutas con autenticación opcional
        self.optional_auth_paths = set(optional_auth_paths or [])
        
        self.bearer = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        """Procesa autenticación en cada request."""
        try:
            # Verificar si la ruta requiere autenticación
            if self._is_public_path(request.url.path):
                return await call_next(request)
            
            # Extraer y validar token
            auth_result = await self._authenticate_request(request)
            
            # Manejar autenticación opcional
            if not auth_result and self._is_optional_auth_path(request.url.path):
                return await call_next(request)
            
            # Verificar autenticación requerida
            if not auth_result:
                if self.auto_error:
                    raise AuthenticationException("Token de autenticación requerido")
                else:
                    return await call_next(request)
            
            # Agregar información del usuario al request
            request.state.current_user = auth_result["user"]
            request.state.session_id = auth_result.get("session_id")
            request.state.token_payload = auth_result.get("payload")
            
            # Continuar con el request
            response = await call_next(request)
            
            # Actualizar última actividad de sesión
            if hasattr(request.state, 'session_id') and request.state.session_id:
                await self._update_session_activity(request.state.session_id)
            
            return response
            
        except (AuthenticationException, AuthorizationException) as e:
            logger.warning(f"Authentication error: {str(e)} for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "AUTHENTICATION_ERROR",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Unexpected auth error: {str(e)}")
            if self.auto_error:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "code": "INTERNAL_AUTH_ERROR",
                            "message": "Error interno de autenticación",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
            return await call_next(request)
    
    async def _authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Autentica el request actual.
        
        Args:
            request: Request HTTP
            
        Returns:
            Dict con información del usuario autenticado o None
        """
        # Intentar autenticación por token JWT
        jwt_result = await self._authenticate_jwt(request)
        if jwt_result:
            return jwt_result
        
        # Intentar autenticación por sesión
        session_result = await self._authenticate_session(request)
        if session_result:
            return session_result
        
        # Intentar autenticación por API key
        api_key_result = await self._authenticate_api_key(request)
        if api_key_result:
            return api_key_result
        
        return None
    
    async def _authenticate_jwt(self, request: Request) -> Optional[Dict[str, Any]]:
        """Autentica usando JWT token."""
        try:
            # Extraer token del header Authorization
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None
            
            token = authorization.split(" ")[1]
            
            # Decodificar y validar token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verificar expiración
            if payload.get("exp", 0) < time.time():
                raise AuthenticationException("Token expirado")
            
            # Obtener información del usuario
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationException("Token inválido: falta user_id")
            
            user = await self.auth_service.get_user_by_id(user_id)
            if not user:
                raise AuthenticationException("Usuario no encontrado")
            
            if not user.get("activo"):
                raise AuthenticationException("Usuario inactivo")
            
            # Verificar blacklist de tokens
            jti = payload.get("jti")
            if jti and await self.auth_service.is_token_blacklisted(jti):
                raise AuthenticationException("Token revocado")
            
            return {
                "user": user,
                "payload": payload,
                "auth_method": "jwt"
            }
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationException("Token expirado")
        except jwt.InvalidTokenError:
            raise AuthenticationException("Token inválido")
        except Exception as e:
            logger.error(f"JWT authentication error: {str(e)}")
            return None
    
    async def _authenticate_session(self, request: Request) -> Optional[Dict[str, Any]]:
        """Autentica usando sesión de cookies."""
        try:
            # Extraer session ID de cookies
            session_id = request.cookies.get("session_id")
            if not session_id:
                return None
            
            # Validar sesión
            session = await self.session_service.get_session(session_id)
            if not session:
                return None
            
            if session.get("expired_at") and session["expired_at"] < datetime.utcnow():
                await self.session_service.delete_session(session_id)
                return None
            
            # Obtener usuario de la sesión
            user_id = session.get("user_id")
            if not user_id:
                return None
            
            user = await self.auth_service.get_user_by_id(user_id)
            if not user or not user.get("activo"):
                await self.session_service.delete_session(session_id)
                return None
            
            return {
                "user": user,
                "session_id": session_id,
                "auth_method": "session"
            }
            
        except Exception as e:
            logger.error(f"Session authentication error: {str(e)}")
            return None
    
    async def _authenticate_api_key(self, request: Request) -> Optional[Dict[str, Any]]:
        """Autentica usando API key."""
        try:
            # Extraer API key del header
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                return None
            
            # Validar API key
            api_key_info = await self.auth_service.validate_api_key(api_key)
            if not api_key_info:
                return None
            
            # Obtener usuario asociado
            user_id = api_key_info.get("user_id")
            if not user_id:
                return None
            
            user = await self.auth_service.get_user_by_id(user_id)
            if not user or not user.get("activo"):
                return None
            
            # Registrar uso de API key
            await self.auth_service.log_api_key_usage(
                api_key_info["id"],
                request.client.host if request.client else None
            )
            
            return {
                "user": user,
                "api_key_id": api_key_info["id"],
                "auth_method": "api_key"
            }
            
        except Exception as e:
            logger.error(f"API key authentication error: {str(e)}")
            return None
    
    async def _update_session_activity(self, session_id: str):
        """Actualiza la última actividad de la sesión."""
        try:
            await self.session_service.update_last_activity(session_id)
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")
    
    def _is_public_path(self, path: str) -> bool:
        """Verifica si la ruta es pública."""
        # Verificación exacta
        if path in self.public_paths:
            return True
        
        # Verificación de prefijos
        return any(
            path.startswith(public_path.rstrip("/") + "/")
            for public_path in self.public_paths
            if public_path.endswith("/") or public_path in ["/static", "/docs"]
        )
    
    def _is_optional_auth_path(self, path: str) -> bool:
        """Verifica si la ruta tiene autenticación opcional."""
        return any(
            path.startswith(optional_path.rstrip("/"))
            for optional_path in self.optional_auth_paths
        )


class RoleBasedAccessMiddleware(BaseHTTPMiddleware):
    """Middleware para control de acceso basado en roles."""
    
    def __init__(
        self,
        app,
        role_permissions: Dict[str, List[str]] = None,
        path_permissions: Dict[str, List[str]] = None
    ):
        super().__init__(app)
        self.role_permissions = role_permissions or {}
        self.path_permissions = path_permissions or {}
    
    async def dispatch(self, request: Request, call_next):
        """Verifica permisos basados en roles."""
        try:
            # Verificar si hay usuario autenticado
            if not hasattr(request.state, 'current_user'):
                return await call_next(request)
            
            user = request.state.current_user
            path = request.url.path
            method = request.method
            
            # Verificar permisos para la ruta
            if not await self._check_permissions(user, path, method):
                raise AuthorizationException(
                    "No tiene permisos para acceder a este recurso"
                )
            
            return await call_next(request)
            
        except AuthorizationException as e:
            logger.warning(
                f"Authorization denied for user {user.get('id')} "
                f"on {method} {path}: {str(e)}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "AUTHORIZATION_ERROR",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
    
    async def _check_permissions(
        self, 
        user: Dict[str, Any], 
        path: str, 
        method: str
    ) -> bool:
        """
        Verifica permisos del usuario para la ruta.
        
        Args:
            user: Usuario autenticado
            path: Ruta del request
            method: Método HTTP
            
        Returns:
            True si tiene permisos
        """
        # Superadmin siempre tiene acceso
        if self._is_superadmin(user):
            return True
        
        # Verificar permisos específicos de ruta
        required_permissions = self._get_required_permissions(path, method)
        if not required_permissions:
            return True  # Ruta sin restricciones específicas
        
        # Obtener permisos del usuario
        user_permissions = self._get_user_permissions(user)
        
        # Verificar si tiene alguno de los permisos requeridos
        return any(perm in user_permissions for perm in required_permissions)
    
    def _is_superadmin(self, user: Dict[str, Any]) -> bool:
        """Verifica si el usuario es superadministrador."""
        roles = user.get("roles", [])
        return any(
            role.get("nombre") == "superadmin" 
            for role in roles
        )
    
    def _get_required_permissions(self, path: str, method: str) -> List[str]:
        """Obtiene permisos requeridos para una ruta."""
        # Buscar coincidencias exactas primero
        path_key = f"{method.upper()} {path}"
        if path_key in self.path_permissions:
            return self.path_permissions[path_key]
        
        # Buscar patrones
        for pattern, permissions in self.path_permissions.items():
            if self._match_path_pattern(pattern, f"{method.upper()} {path}"):
                return permissions
        
        return []
    
    def _get_user_permissions(self, user: Dict[str, Any]) -> Set[str]:
        """Obtiene todos los permisos del usuario."""
        permissions = set()
        
        # Permisos directos del usuario
        user_permissions = user.get("permisos", [])
        permissions.update(perm.get("codigo") for perm in user_permissions)
        
        # Permisos de roles
        roles = user.get("roles", [])
        for role in roles:
            role_name = role.get("nombre")
            if role_name in self.role_permissions:
                permissions.update(self.role_permissions[role_name])
            
            # Permisos del rol
            role_permissions = role.get("permisos", [])
            permissions.update(perm.get("codigo") for perm in role_permissions)
        
        return permissions
    
    def _match_path_pattern(self, pattern: str, path: str) -> bool:
        """Verifica si un path coincide con un patrón."""
        import re
        
        # Convertir patrón a regex
        # Ejemplo: "GET /users/{id}" -> "GET /users/[^/]+"
        regex_pattern = pattern.replace("{id}", r"[^/]+")
        regex_pattern = regex_pattern.replace("{", r"[^/]+")  # Para otros parámetros
        regex_pattern = f"^{regex_pattern}$"
        
        return bool(re.match(regex_pattern, path))


class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware para manejo de timeout de sesiones."""
    
    def __init__(
        self,
        app,
        session_timeout: int = 3600,  # 1 hora en segundos
        warning_threshold: int = 300   # 5 minutos antes de expirar
    ):
        super().__init__(app)
        self.session_timeout = session_timeout
        self.warning_threshold = warning_threshold
        self.session_service = SessionService()
    
    async def dispatch(self, request: Request, call_next):
        """Verifica timeout de sesión."""
        # Procesar request
        response = await call_next(request)
        
        # Verificar sesión si existe
        if hasattr(request.state, 'session_id') and request.state.session_id:
            await self._check_session_timeout(request, response)
        
        return response
    
    async def _check_session_timeout(self, request: Request, response):
        """Verifica y maneja timeout de sesión."""
        try:
            session_id = request.state.session_id
            session = await self.session_service.get_session(session_id)
            
            if not session:
                return
            
            last_activity = session.get("last_activity")
            if not last_activity:
                return
            
            # Calcular tiempo desde última actividad
            time_since_activity = (datetime.utcnow() - last_activity).total_seconds()
            
            # Verificar timeout
            if time_since_activity > self.session_timeout:
                await self.session_service.delete_session(session_id)
                response.headers["X-Session-Expired"] = "true"
                return
            
            # Verificar si está cerca del timeout
            time_remaining = self.session_timeout - time_since_activity
            if time_remaining <= self.warning_threshold:
                response.headers["X-Session-Warning"] = str(int(time_remaining))
                
        except Exception as e:
            logger.error(f"Session timeout check error: {str(e)}")


def require_roles(*required_roles):
    """
    Decorator para requerir roles específicos.
    
    Args:
        required_roles: Roles requeridos
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, 'current_user'):
                raise AuthorizationException("Autenticación requerida")
            
            user = request.state.current_user
            user_roles = {role.get("nombre") for role in user.get("roles", [])}
            
            if not any(role in user_roles for role in required_roles):
                raise AuthorizationException(
                    f"Se requiere uno de estos roles: {', '.join(required_roles)}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_permissions(*required_permissions):
    """
    Decorator para requerir permisos específicos.
    
    Args:
        required_permissions: Permisos requeridos
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, 'current_user'):
                raise AuthorizationException("Autenticación requerida")
            
            user = request.state.current_user
            
            # Obtener permisos del usuario
            user_permissions = set()
            
            # Permisos directos
            for perm in user.get("permisos", []):
                user_permissions.add(perm.get("codigo"))
            
            # Permisos de roles
            for role in user.get("roles", []):
                for perm in role.get("permisos", []):
                    user_permissions.add(perm.get("codigo"))
            
            # Verificar si tiene alguno de los permisos requeridos
            if not any(perm in user_permissions for perm in required_permissions):
                raise AuthorizationException(
                    f"Se requiere uno de estos permisos: {', '.join(required_permissions)}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Obtiene el usuario actual del request.
    
    Args:
        request: Request HTTP
        
    Returns:
        Dict con información del usuario
        
    Raises:
        AuthenticationException: Si no hay usuario autenticado
    """
    if not hasattr(request.state, 'current_user') or not request.state.current_user:
        raise AuthenticationException("Usuario no autenticado")
    
    return request.state.current_user


def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """
    Obtiene el usuario actual del request (opcional).
    
    Args:
        request: Request HTTP
        
    Returns:
        Dict con información del usuario o None
    """
    if hasattr(request.state, 'current_user'):
        return request.state.current_user
    return None


def require_superadmin(func):
    """
    Decorator para requerir rol de superadministrador.
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not hasattr(request.state, 'current_user'):
            raise AuthorizationException("Autenticación requerida")
        
        user = request.state.current_user
        user_roles = {role.get("nombre") for role in user.get("roles", [])}
        
        if "superadmin" not in user_roles:
            raise AuthorizationException("Se requiere rol de superadministrador")
        
        return await func(request, *args, **kwargs)
    return wrapper


def require_parish_access(parish_id_param: str = "parroquia_id"):
    """
    Decorator para requerir acceso a una parroquia específica.
    
    Args:
        parish_id_param: Nombre del parámetro que contiene el ID de parroquia
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, 'current_user'):
                raise AuthorizationException("Autenticación requerida")
            
            user = request.state.current_user
            
            # Superadmin tiene acceso a todo
            user_roles = {role.get("nombre") for role in user.get("roles", [])}
            if "superadmin" in user_roles:
                return await func(request, *args, **kwargs)
            
            # Obtener ID de parroquia del request
            parish_id = None
            
            # Buscar en path params
            if hasattr(request, 'path_params') and parish_id_param in request.path_params:
                parish_id = request.path_params[parish_id_param]
            
            # Buscar en query params
            elif parish_id_param in request.query_params:
                parish_id = request.query_params[parish_id_param]
            
            # Buscar en body (para POST/PUT)
            elif request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                    parish_id = body.get(parish_id_param)
                except:
                    pass
            
            if not parish_id:
                raise AuthorizationException("ID de parroquia no especificado")
            
            # Verificar acceso del usuario a la parroquia
            user_parish_id = user.get("parroquia_id")
            if user_parish_id != int(parish_id):
                raise AuthorizationException("No tiene acceso a esta parroquia")
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_active_user(func):
    """
    Decorator para requerir que el usuario esté activo.
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not hasattr(request.state, 'current_user'):
            raise AuthorizationException("Autenticación requerida")
        
        user = request.state.current_user
        
        if not user.get("activo", False):
            raise AuthorizationException("Usuario inactivo")
        
        return await func(request, *args, **kwargs)
    return wrapper


def require_email_verified(func):
    """
    Decorator para requerir email verificado.
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not hasattr(request.state, 'current_user'):
            raise AuthorizationException("Autenticación requerida")
        
        user = request.state.current_user
        
        if not user.get("email_verificado", False):
            raise AuthorizationException("Email no verificado")
        
        return await func(request, *args, **kwargs)
    return wrapper


def rate_limit(requests: int, window: int, scope: str = "user"):
    """
    Decorator para aplicar rate limiting a endpoints específicos.
    
    Args:
        requests: Número de requests permitidos
        window: Ventana de tiempo en segundos
        scope: Ámbito del rate limit ('user', 'ip', 'global')
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Generar clave para rate limiting
            if scope == "user":
                if hasattr(request.state, 'current_user') and request.state.current_user:
                    key = f"rate_limit:user:{request.state.current_user.get('id')}"
                else:
                    key = f"rate_limit:ip:{request.client.host if request.client else 'unknown'}"
            elif scope == "ip":
                key = f"rate_limit:ip:{request.client.host if request.client else 'unknown'}"
            else:
                key = f"rate_limit:global:{func.__name__}"
            
            # Aquí se implementaría la lógica de rate limiting
            # Por simplicidad, asumimos que pasa la validación
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def audit_log(action: str, resource_type: str = None):
    """
    Decorator para logging de auditoría.
    
    Args:
        action: Acción realizada
        resource_type: Tipo de recurso afectado
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            start_time = time.time()
            user_id = None
            
            if hasattr(request.state, 'current_user') and request.state.current_user:
                user_id = request.state.current_user.get("id")
            
            try:
                # Ejecutar función
                result = await func(request, *args, **kwargs)
                
                # Log de auditoría exitosa
                audit_data = {
                    "user_id": user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "endpoint": f"{request.method} {request.url.path}",
                    "ip_address": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "status": "success",
                    "duration": round((time.time() - start_time) * 1000, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.info(f"AUDIT: {json.dumps(audit_data)}")
                
                return result
                
            except Exception as e:
                # Log de auditoría de error
                audit_data = {
                    "user_id": user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "endpoint": f"{request.method} {request.url.path}",
                    "ip_address": request.client.host if request.client else None,
                    "status": "error",
                    "error": str(e),
                    "duration": round((time.time() - start_time) * 1000, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.warning(f"AUDIT ERROR: {json.dumps(audit_data)}")
                raise
                
        return wrapper
    return decorator


def require_mfa_verified(func):
    """
    Decorator para requerir MFA verificado.
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not hasattr(request.state, 'current_user'):
            raise AuthorizationException("Autenticación requerida")
        
        # Verificar token MFA en headers
        mfa_token = request.headers.get("X-MFA-Token")
        if not mfa_token:
            raise AuthorizationException("Token MFA requerido")
        
        # Aquí se validaría el token MFA
        # Por simplicidad, asumimos validación exitosa
        
        return await func(request, *args, **kwargs)
    return wrapper


def require_ip_whitelist(allowed_ips: List[str]):
    """
    Decorator para requerir IPs específicas.
    
    Args:
        allowed_ips: Lista de IPs permitidas
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else None
            
            if client_ip not in allowed_ips:
                raise AuthorizationException(f"IP {client_ip} no autorizada")
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_time_window(start_hour: int, end_hour: int, timezone: str = "UTC"):
    """
    Decorator para requerir ventana de tiempo específica.
    
    Args:
        start_hour: Hora de inicio (0-23)
        end_hour: Hora de fin (0-23)
        timezone: Zona horaria
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            from datetime import datetime
            import pytz
            
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            current_hour = current_time.hour
            
            if not (start_hour <= current_hour <= end_hour):
                raise AuthorizationException(
                    f"Acceso permitido solo entre {start_hour}:00 y {end_hour}:00 {timezone}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def cache_result(ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Decorator para cachear resultados de endpoints.
    
    Args:
        ttl: Tiempo de vida en segundos
        key_func: Función para generar clave de cache
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Generar clave de cache
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                cache_key = f"cache:{func.__name__}:{hash(str(request.url))}"
            
            # Aquí se implementaría la lógica de cache
            # Por simplicidad, ejecutamos la función directamente
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


class MultiFactorAuthMiddleware(BaseHTTPMiddleware):
    """Middleware para autenticación de múltiples factores."""
    
    def __init__(
        self,
        app,
        mfa_required_paths: List[str] = None,
        mfa_bypass_roles: List[str] = None
    ):
        super().__init__(app)
        self.mfa_required_paths = set(mfa_required_paths or [
            "/admin",
            "/api/admin",
            "/api/usuarios",
            "/api/configuracion"
        ])
        self.mfa_bypass_roles = set(mfa_bypass_roles or ["system"])
        self.auth_service = AuthService()
    
    async def dispatch(self, request: Request, call_next):
        """Verifica MFA cuando es requerido."""
        try:
            # Verificar si la ruta requiere MFA
            if not self._requires_mfa(request.url.path):
                return await call_next(request)
            
            # Verificar si hay usuario autenticado
            if not hasattr(request.state, 'current_user'):
                return await call_next(request)
            
            user = request.state.current_user
            
            # Verificar si el usuario puede bypass MFA
            if self._can_bypass_mfa(user):
                return await call_next(request)
            
            # Verificar MFA
            if not await self._verify_mfa(request, user):
                raise AuthorizationException(
                    "Autenticación de múltiples factores requerida"
                )
            
            return await call_next(request)
            
        except AuthorizationException as e:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "MFA_REQUIRED",
                        "message": str(e),
                        "mfa_required": True,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
    
    def _requires_mfa(self, path: str) -> bool:
        """Verifica si la ruta requiere MFA."""
        return any(
            path.startswith(mfa_path.rstrip("/"))
            for mfa_path in self.mfa_required_paths
        )
    
    def _can_bypass_mfa(self, user: Dict[str, Any]) -> bool:
        """Verifica si el usuario puede bypass MFA."""
        user_roles = {role.get("nombre") for role in user.get("roles", [])}
        return bool(user_roles.intersection(self.mfa_bypass_roles))
    
    async def _verify_mfa(self, request: Request, user: Dict[str, Any]) -> bool:
        """Verifica la autenticación MFA."""
        # Verificar token MFA en headers
        mfa_token = request.headers.get("X-MFA-Token")
        if not mfa_token:
            return False
        
        # Validar token MFA
        return await self.auth_service.verify_mfa_token(
            user.get("id"),
            mfa_token
        )


class DeviceTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware para tracking de dispositivos."""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()
    
    async def dispatch(self, request: Request, call_next):
        """Rastrea información del dispositivo."""
        # Procesar request
        response = await call_next(request)
        
        # Registrar información del dispositivo si hay usuario
        if hasattr(request.state, 'current_user') and request.state.current_user:
            await self._track_device(request)
        
        return response
    
    async def _track_device(self, request: Request):
        """Registra información del dispositivo."""
        try:
            user_id = request.state.current_user.get("id")
            device_info = {
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "accept_language": request.headers.get("accept-language"),
                "timestamp": datetime.utcnow()
            }
            
            await self.auth_service.track_device_login(user_id, device_info)
            
        except Exception as e:
            logger.error(f"Device tracking error: {str(e)}")


def setup_auth_middleware(
    app,
    config: Dict[str, Any] = None
):
    """
    Configura todos los middleware de autenticación.
    
    Args:
        app: Aplicación FastAPI
        config: Configuración personalizada
    """
    default_config = {
        "secret_key": settings.SECRET_KEY,
        "public_paths": [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/forgot-password",
            "/static"
        ],
        "session_timeout": 3600,
        "mfa_required_paths": ["/admin", "/api/admin"],
        "enable_device_tracking": True
    }
    
    # Combinar configuración
    auth_config = {**default_config, **(config or {})}
    
    # Middleware de autenticación principal
    app.add_middleware(
        AuthenticationMiddleware,
        secret_key=auth_config["secret_key"],
        public_paths=auth_config["public_paths"]
    )
    
    # Middleware de control de acceso
    app.add_middleware(RoleBasedAccessMiddleware)
    
    # Middleware de timeout de sesión
    app.add_middleware(
        SessionTimeoutMiddleware,
        session_timeout=auth_config["session_timeout"]
    )
    
    # Middleware MFA (si está habilitado)
    if auth_config.get("mfa_required_paths"):
        app.add_middleware(
            MultiFactorAuthMiddleware,
            mfa_required_paths=auth_config["mfa_required_paths"]
        )
    
    # Middleware de tracking de dispositivos
    if auth_config.get("enable_device_tracking"):
        app.add_middleware(DeviceTrackingMiddleware)
    
    logger.info("Authentication middleware configured successfully")