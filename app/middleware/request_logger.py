"""
Middleware para logging detallado de requests HTTP.
Registra información de entrada, salida y métricas de performance.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
import logging
import time
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware para logging completo de requests."""
    
    def __init__(
        self,
        app,
        log_level: str = "INFO",
        include_request_body: bool = False,
        include_response_body: bool = False,
        exclude_paths: List[str] = None,
        sensitive_headers: List[str] = None,
        max_body_size: int = 1024 * 10  # 10KB
    ):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.exclude_paths = exclude_paths or ["/health", "/healthz", "/ping", "/metrics"]
        self.sensitive_headers = sensitive_headers or [
            "authorization", "cookie", "x-api-key", "x-auth-token"
        ]
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next):
        """Procesa request con logging completo."""
        # Generar ID único para el request
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Verificar si debe excluir este path
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Timestamp de inicio
        start_time = time.time()
        
        # Capturar información del request
        request_info = await self._capture_request_info(request, request_id)
        
        # Log del request entrante
        logger.log(self.log_level, f"REQUEST IN: {json.dumps(request_info, indent=2)}")
        
        # Procesar request
        try:
            response = await call_next(request)
            
            # Calcular tiempo de procesamiento
            process_time = time.time() - start_time
            
            # Capturar información del response
            response_info = await self._capture_response_info(
                response, request_id, process_time
            )
            
            # Log del response
            logger.log(self.log_level, f"REQUEST OUT: {json.dumps(response_info, indent=2)}")
            
            # Agregar headers de tracking
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            # Log de error
            process_time = time.time() - start_time
            error_info = {
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "process_time": process_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.error(f"REQUEST ERROR: {json.dumps(error_info, indent=2)}")
            raise
    
    async def _capture_request_info(self, request: Request, request_id: str) -> Dict[str, Any]:
        """
        Captura información detallada del request.
        
        Args:
            request: Objeto Request
            request_id: ID único del request
            
        Returns:
            Dict con información del request
        """
        info = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client": {
                "host": request.client.host if request.client else None,
                "port": request.client.port if request.client else None
            },
            "headers": self._filter_headers(dict(request.headers)),
            "query_params": dict(request.query_params) if request.query_params else None,
            "path_params": dict(request.path_params) if request.path_params else None
        }
        
        # Agregar información del usuario si está disponible
        if hasattr(request.state, 'current_user') and request.state.current_user:
            info["user"] = {
                "id": request.state.current_user.get("id"),
                "email": request.state.current_user.get("email"),
                "roles": request.state.current_user.get("roles", [])
            }
        
        # Capturar body del request si está habilitado
        if self.include_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await self._read_request_body(request)
                if body:
                    info["body"] = body
            except Exception as e:
                info["body_error"] = str(e)
        
        return info
    
    async def _capture_response_info(
        self, 
        response: Response, 
        request_id: str, 
        process_time: float
    ) -> Dict[str, Any]:
        """
        Captura información del response.
        
        Args:
            response: Objeto Response
            request_id: ID del request
            process_time: Tiempo de procesamiento
            
        Returns:
            Dict con información del response
        """
        info = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": response.status_code,
            "headers": self._filter_headers(dict(response.headers)),
            "process_time": round(process_time * 1000, 2),  # en milisegundos
            "content_length": response.headers.get("content-length")
        }
        
        # Capturar body del response si está habilitado
        if self.include_response_body:
            try:
                body = await self._read_response_body(response)
                if body:
                    info["body"] = body
            except Exception as e:
                info["body_error"] = str(e)
        
        return info
    
    async def _read_request_body(self, request: Request) -> Optional[Dict]:
        """Lee y parsea el body del request."""
        try:
            # Leer body raw
            body_bytes = await request.body()
            
            if not body_bytes or len(body_bytes) > self.max_body_size:
                return None
            
            # Intentar parsear como JSON
            try:
                body_str = body_bytes.decode('utf-8')
                return json.loads(body_str)
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Si no es JSON válido, truncar y devolver como string
                body_str = body_bytes.decode('utf-8', errors='ignore')
                if len(body_str) > 500:
                    body_str = body_str[:500] + "... [truncated]"
                return {"raw": body_str}
                
        except Exception:
            return None
    
    async def _read_response_body(self, response: Response) -> Optional[Dict]:
        """Lee y parsea el body del response."""
        try:
            # Solo para responses con content-type JSON
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                return None
            
            # Verificar tamaño
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self.max_body_size:
                return {"message": "Response body too large to log"}
            
            # Leer body (esto es complejo en Starlette, simplificamos)
            return {"message": "Response body logging not implemented"}
            
        except Exception:
            return None
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filtra headers sensibles.
        
        Args:
            headers: Headers originales
            
        Returns:
            Headers filtrados
        """
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "[FILTERED]"
            else:
                filtered[key] = value
        
        return filtered
    
    def _should_exclude_path(self, path: str) -> bool:
        """Verifica si debe excluir el path del logging."""
        return any(excluded in path for excluded in self.exclude_paths)


class PerformanceLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware específico para métricas de performance."""
    
    def __init__(
        self,
        app,
        slow_request_threshold: float = 1.0,  # segundos
        log_all_requests: bool = False
    ):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.log_all_requests = log_all_requests
        self.performance_logger = logging.getLogger("performance")
    
    async def dispatch(self, request: Request, call_next):
        """Procesa request con métricas de performance."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log de performance
            await self._log_performance(request, response, process_time)
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            await self._log_error_performance(request, exc, process_time)
            raise
    
    async def _log_performance(
        self, 
        request: Request, 
        response: Response, 
        process_time: float
    ):
        """Registra métricas de performance."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": round(process_time * 1000, 2),  # ms
            "is_slow": process_time > self.slow_request_threshold
        }
        
        # Información adicional para requests lentos
        if metrics["is_slow"]:
            metrics["client_ip"] = request.client.host if request.client else None
            metrics["user_agent"] = request.headers.get("user-agent")
            
            if hasattr(request.state, 'current_user') and request.state.current_user:
                metrics["user_id"] = request.state.current_user.get("id")
        
        # Log según configuración
        if self.log_all_requests or metrics["is_slow"]:
            level = logging.WARNING if metrics["is_slow"] else logging.INFO
            self.performance_logger.log(
                level,
                f"PERFORMANCE: {json.dumps(metrics)}"
            )
    
    async def _log_error_performance(
        self, 
        request: Request, 
        exc: Exception, 
        process_time: float
    ):
        """Registra métricas de errores."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "error_type": type(exc).__name__,
            "process_time": round(process_time * 1000, 2),
            "status": "error"
        }
        
        self.performance_logger.error(
            f"PERFORMANCE ERROR: {json.dumps(metrics)}"
        )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware simple para agregar Request ID."""
    
    async def dispatch(self, request: Request, call_next):
        """Agrega Request ID a todos los requests."""
        if not hasattr(request.state, 'request_id'):
            request.state.request_id = str(uuid.uuid4())
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        
        return response


def setup_request_logging(
    app,
    log_level: str = "INFO",
    include_bodies: bool = False,
    performance_monitoring: bool = True,
    slow_threshold: float = 1.0
):
    """
    Configura middleware de logging para la aplicación.
    
    Args:
        app: Aplicación FastAPI
        log_level: Nivel de logging
        include_bodies: Incluir bodies en logs
        performance_monitoring: Habilitar monitoreo de performance
        slow_threshold: Umbral para requests lentos
    """
    # Request ID (siempre primero)
    app.add_middleware(RequestIDMiddleware)
    
    # Logger principal
    app.add_middleware(
        RequestLoggerMiddleware,
        log_level=log_level,
        include_request_body=include_bodies,
        include_response_body=include_bodies
    )
    
    # Performance monitoring
    if performance_monitoring:
        app.add_middleware(
            PerformanceLoggerMiddleware,
            slow_request_threshold=slow_threshold,
            log_all_requests=False
        )