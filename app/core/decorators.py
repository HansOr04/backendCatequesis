"""
Decoradores para el Sistema de Catequesis.
Incluye decoradores para autenticación, autorización, logging, cache y más.
"""

import time
import functools
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from flask import request, g, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from marshmallow import ValidationError

from app.core.exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    InsufficientPermissionsError,
    RateLimitExceededError,
    ValidationError as CatequesisValidationError
)
from app.core.response_handler import ResponseHandler
from app.utils.constants import UserProfileType, HTTPStatus


logger = logging.getLogger(__name__)


def authenticate_required(f: Callable) -> Callable:
    """
    Decorador que requiere autenticación JWT.
    
    Args:
        f: Función a decorar
        
    Returns:
        Callable: Función decorada
    """
    @functools.wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            # Obtener identidad del token
            current_user_id = get_jwt_identity()
            if not current_user_id:
                raise AuthenticationError("Token de autenticación inválido")
            
            # Almacenar en el contexto global
            g.current_user_id = current_user_id
            
            return f(*args, **kwargs)
            
        except AuthenticationError as e:
            return ResponseHandler.from_exception(e)
        except Exception as e:
            logger.error(f"Error en autenticación: {str(e)}")
            return ResponseHandler.unauthorized("Error de autenticación")
    
    return decorated_function


def authorize_profiles(*allowed_profiles: str):
    """
    Decorador que autoriza solo ciertos perfiles de usuario.
    
    Args:
        allowed_profiles: Perfiles permitidos
        
    Returns:
        Callable: Decorador
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        @authenticate_required
        def decorated_function(*args, **kwargs):
            try:
                # Obtener perfil del usuario desde el token JWT
                claims = get_jwt()
                user_profile = claims.get('profile')
                
                if not user_profile:
                    raise AuthorizationError("Perfil de usuario no encontrado")
                
                if user_profile not in allowed_profiles:
                    raise InsufficientPermissionsError(f"Perfil requerido: {', '.join(allowed_profiles)}")
                
                # Almacenar perfil en contexto
                g.current_user_profile = user_profile
                
                return f(*args, **kwargs)
                
            except (AuthorizationError, InsufficientPermissionsError) as e:
                return ResponseHandler.from_exception(e)
            except Exception as e:
                logger.error(f"Error en autorización: {str(e)}")
                return ResponseHandler.forbidden("Sin permisos suficientes")
        
        return decorated_function
    return decorator


def admin_required(f: Callable) -> Callable:
    """
    Decorador que requiere perfil de administrador.
    
    Args:
        f: Función a decorar
        
    Returns:
        Callable: Función decorada
    """
    return authorize_profiles(UserProfileType.ADMIN.value)(f)


def parroco_or_admin_required(f: Callable) -> Callable:
    """
    Decorador que requiere perfil de párroco o administrador.
    
    Args:
        f: Función a decorar
        
    Returns:
        Callable: Función decorada
    """
    return authorize_profiles(
        UserProfileType.ADMIN.value, 
        UserProfileType.PARROCO.value
    )(f)


def secretaria_or_higher_required(f: Callable) -> Callable:
    """
    Decorador que requiere perfil de secretaria o superior.
    
    Args:
        f: Función a decorar
        
    Returns:
        Callable: Función decorada
    """
    return authorize_profiles(
        UserProfileType.ADMIN.value,
        UserProfileType.PARROCO.value,
        UserProfileType.SECRETARIA.value
    )(f)


def validate_parroquia_access(f: Callable) -> Callable:
    """
    Decorador que valida acceso a datos de parroquia específica.
    
    Args:
        f: Función a decorar
        
    Returns:
        Callable: Función decorada
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Obtener ID de parroquia del token JWT
            claims = get_jwt()
            user_parroquia_id = claims.get('parroquia_id')
            user_profile = claims.get('profile')
            
            # Los admins pueden acceder a cualquier parroquia
            if user_profile == UserProfileType.ADMIN.value:
                return f(*args, **kwargs)
            
            # Obtener ID de parroquia de los parámetros
            parroquia_id = kwargs.get('parroquia_id') or request.view_args.get('parroquia_id')
            
            if parroquia_id and user_parroquia_id:
                if int(parroquia_id) != int(user_parroquia_id):
                    raise AuthorizationError("No tiene acceso a datos de esta parroquia")
            
            return f(*args, **kwargs)
            
        except AuthorizationError as e:
            return ResponseHandler.from_exception(e)
        except Exception as e:
            logger.error(f"Error en validación de parroquia: {str(e)}")
            return ResponseHandler.forbidden("Acceso denegado a esta parroquia")
    
    return decorated_function


def log_activity(activity_type: str, entity: str = None):
    """
    Decorador para logging de actividades del usuario.
    
    Args:
        activity_type: Tipo de actividad (CREATE, UPDATE, DELETE, etc.)
        entity: Entidad afectada
        
    Returns:
        Callable: Decorador
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Ejecutar función
                result = f(*args, **kwargs)
                
                # Log de actividad exitosa
                duration = time.time() - start_time
                user_id = getattr(g, 'current_user_id', 'unknown')
                
                logger.info(
                    f"Activity: {activity_type} | "
                    f"Entity: {entity or 'unknown'} | "
                    f"User: {user_id} | "
                    f"Duration: {duration:.3f}s | "
                    f"Status: SUCCESS"
                )
                
                return result
                
            except Exception as e:
                # Log de error
                duration = time.time() - start_time
                user_id = getattr(g, 'current_user_id', 'unknown')