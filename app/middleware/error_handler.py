"""
Middleware para manejo centralizado de errores y excepciones.
Proporciona respuestas consistentes y logging detallado.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import Dict, Any
import logging
import traceback
import json
from datetime import datetime

from app.core.exceptions import (
    BusinessLogicException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException
)

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware para manejo centralizado de errores."""
    
    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next):
        """Procesa request y maneja errores."""
        try:
            response = await call_next(request)
            return response
            
        except Exception as exc:
            return await self._handle_exception(request, exc)
    
    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """
        Maneja diferentes tipos de excepciones.
        
        Args:
            request: Request HTTP
            exc: Excepción capturada
            
        Returns:
            JSONResponse con error formateado
        """
        error_id = self._generate_error_id()
        
        # Log del error
        await self._log_error(request, exc, error_id)
        
        # Manejo por tipo de excepción
        if isinstance(exc, HTTPException):
            return await self._handle_http_exception(exc, error_id)
        
        elif isinstance(exc, RequestValidationError):
            return await self._handle_validation_exception(exc, error_id)
        
        elif isinstance(exc, BusinessLogicException):
            return await self._handle_business_exception(exc, error_id)
        
        elif isinstance(exc, ValidationException):
            return await self._handle_custom_validation_exception(exc, error_id)
        
        elif isinstance(exc, AuthenticationException):
            return await self._handle_auth_exception(exc, error_id)
        
        elif isinstance(exc, AuthorizationException):
            return await self._handle_authorization_exception(exc, error_id)
        
        elif isinstance(exc, ResourceNotFoundException):
            return await self._handle_not_found_exception(exc, error_id)
        
        elif isinstance(exc, IntegrityError):
            return await self._handle_integrity_exception(exc, error_id)
        
        elif isinstance(exc, OperationalError):
            return await self._handle_database_exception(exc, error_id)
        
        else:
            return await self._handle_generic_exception(exc, error_id)
    
    async def _handle_http_exception(self, exc: HTTPException, error_id: str) -> JSONResponse:
        """Maneja excepciones HTTP estándar."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_validation_exception(self, exc: RequestValidationError, error_id: str) -> JSONResponse:
        """Maneja errores de validación de request."""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Error en validación de datos",
                    "details": errors,
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_business_exception(self, exc: BusinessLogicException, error_id: str) -> JSONResponse:
        """Maneja excepciones de lógica de negocio."""
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "BUSINESS_LOGIC_ERROR",
                    "message": str(exc),
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_custom_validation_exception(self, exc: ValidationException, error_id: str) -> JSONResponse:
        """Maneja excepciones de validación personalizada."""
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "CUSTOM_VALIDATION_ERROR",
                    "message": str(exc),
                    "details": getattr(exc, 'details', None),
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_auth_exception(self, exc: AuthenticationException, error_id: str) -> JSONResponse:
        """Maneja excepciones de autenticación."""
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "AUTHENTICATION_ERROR",
                    "message": str(exc),
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_authorization_exception(self, exc: AuthorizationException, error_id: str) -> JSONResponse:
        """Maneja excepciones de autorización."""
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "AUTHORIZATION_ERROR",
                    "message": str(exc),
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_not_found_exception(self, exc: ResourceNotFoundException, error_id: str) -> JSONResponse:
        """Maneja excepciones de recurso no encontrado."""
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": str(exc),
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_integrity_exception(self, exc: IntegrityError, error_id: str) -> JSONResponse:
        """Maneja errores de integridad de base de datos."""
        message = "Error de integridad de datos"
        
        # Parsear mensaje específico
        if "UNIQUE constraint failed" in str(exc):
            message = "Ya existe un registro con estos datos únicos"
        elif "FOREIGN KEY constraint failed" in str(exc):
            message = "Error de referencia: el recurso relacionado no existe"
        elif "NOT NULL constraint failed" in str(exc):
            message = "Falta información requerida"
        
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "DATA_INTEGRITY_ERROR",
                    "message": message,
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_database_exception(self, exc: OperationalError, error_id: str) -> JSONResponse:
        """Maneja errores operacionales de base de datos."""
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Error temporal de base de datos. Intente nuevamente.",
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _handle_generic_exception(self, exc: Exception, error_id: str) -> JSONResponse:
        """Maneja excepciones no categorizadas."""
        message = "Error interno del servidor"
        
        if self.debug:
            message = str(exc)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": message,
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    async def _log_error(self, request: Request, exc: Exception, error_id: str):
        """
        Registra error en logs.
        
        Args:
            request: Request HTTP
            exc: Excepción
            error_id: ID único del error
        """
        # Información de contexto
        context = {
            "error_id": error_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
        
        # Headers (sin datos sensibles)
        safe_headers = {}
        for key, value in request.headers.items():
            if key.lower() not in ['authorization', 'cookie', 'x-api-key']:
                safe_headers[key] = value
        context["headers"] = safe_headers
        
        # Query params
        if request.query_params:
            context["query_params"] = dict(request.query_params)
        
        # Traceback para errores críticos
        if not isinstance(exc, (HTTPException, BusinessLogicException, ValidationException)):
            context["traceback"] = traceback.format_exc()
            logger.error(f"Error crítico: {json.dumps(context, indent=2)}")
        else:
            logger.warning(f"Error manejado: {json.dumps(context, indent=2)}")
    
    def _generate_error_id(self) -> str:
        """Genera ID único para el error."""
        import uuid
        return f"ERR_{datetime.utcnow().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Middleware para health checks que evita logging innecesario."""
    
    async def dispatch(self, request: Request, call_next):
        """Procesa health checks sin logging detallado."""
        if request.url.path in ["/health", "/healthz", "/ping"]:
            try:
                response = await call_next(request)
                return response
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy"}
                )
        
        return await call_next(request)


def get_error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    Crea respuesta de error estandarizada.
    
    Args:
        error_code: Código de error
        message: Mensaje descriptivo
        status_code: Código HTTP
        details: Detalles adicionales
        
    Returns:
        JSONResponse formateada
    """
    content = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    if details:
        content["error"]["details"] = details
    
    return JSONResponse(status_code=status_code, content=content)