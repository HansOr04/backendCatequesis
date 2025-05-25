"""
Middleware CORS personalizable para manejo de Cross-Origin Resource Sharing.
Proporciona configuración flexible y logging de requests CORS.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import List, Dict, Set, Optional, Union
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CORSMiddleware(BaseHTTPMiddleware):
    """Middleware CORS personalizado con configuración avanzada."""
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        expose_headers: List[str] = None,
        max_age: int = 86400,  # 24 horas
        allow_origin_regex: str = None,
        allow_private_networks: bool = False,
        development_mode: bool = False
    ):
        super().__init__(app)
        
        # Configuración de orígenes
        self.allow_origins = set(allow_origins) if allow_origins else set()
        self.allow_all_origins = "*" in self.allow_origins
        self.allow_origin_regex = re.compile(allow_origin_regex) if allow_origin_regex else None
        self.development_mode = development_mode
        
        # Métodos permitidos
        default_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        self.allow_methods = set(allow_methods) if allow_methods else set(default_methods)
        self.allow_all_methods = "*" in self.allow_methods
        
        # Headers permitidos
        default_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID"
        ]
        self.allow_headers = set(allow_headers) if allow_headers else set(default_headers)
        self.allow_all_headers = "*" in self.allow_headers
        
        # Otras configuraciones
        self.allow_credentials = allow_credentials
        self.expose_headers = set(expose_headers) if expose_headers else set()
        self.max_age = max_age
        self.allow_private_networks = allow_private_networks
        
        # Validaciones
        self._validate_configuration()
    
    async def dispatch(self, request: Request, call_next):
        """Procesa request aplicando políticas CORS."""
        origin = request.headers.get("origin")
        
        # Log de request CORS si hay origin
        if origin:
            logger.debug(f"CORS request from origin: {origin}")
        
        # Manejar preflight requests (OPTIONS)
        if request.method == "OPTIONS":
            return self._handle_preflight_request(request)
        
        # Procesar request normal
        response = await call_next(request)
        
        # Aplicar headers CORS
        self._add_cors_headers(request, response)
        
        return response
    
    def _handle_preflight_request(self, request: Request) -> Response:
        """
        Maneja requests OPTIONS (preflight).
        
        Args:
            request: Request OPTIONS
            
        Returns:
            Response con headers CORS apropiados
        """
        origin = request.headers.get("origin")
        requested_method = request.headers.get("access-control-request-method")
        requested_headers = request.headers.get("access-control-request-headers")
        
        logger.debug(
            f"Preflight request - Origin: {origin}, "
            f"Method: {requested_method}, Headers: {requested_headers}"
        )
        
        # Verificar origen
        if not self._is_origin_allowed(origin):
            logger.warning(f"CORS: Origin not allowed: {origin}")
            return JSONResponse(
                status_code=403,
                content={"error": "Origin not allowed"},
                headers={}
            )
        
        # Verificar método
        if requested_method and not self._is_method_allowed(requested_method):
            logger.warning(f"CORS: Method not allowed: {requested_method}")
            return JSONResponse(
                status_code=405,
                content={"error": "Method not allowed"},
                headers={}
            )
        
        # Verificar headers
        if requested_headers and not self._are_headers_allowed(requested_headers):
            logger.warning(f"CORS: Headers not allowed: {requested_headers}")
            return JSONResponse(
                status_code=400,
                content={"error": "Headers not allowed"},
                headers={}
            )
        
        # Crear response con headers CORS
        headers = {}
        self._set_origin_header(headers, origin)
        self._set_methods_header(headers)
        self._set_headers_header(headers, requested_headers)
        self._set_credentials_header(headers)
        self._set_max_age_header(headers)
        self._set_private_network_header(headers, request)
        
        logger.debug(f"Preflight response headers: {headers}")
        
        return Response(status_code=204, headers=headers)
    
    def _add_cors_headers(self, request: Request, response: Response):
        """
        Agrega headers CORS al response.
        
        Args:
            request: Request original
            response: Response a modificar
        """
        origin = request.headers.get("origin")
        
        if not origin:
            return  # No es un request CORS
        
        if not self._is_origin_allowed(origin):
            logger.warning(f"CORS: Origin not allowed for actual request: {origin}")
            return
        
        # Agregar headers CORS
        self._set_origin_header(response.headers, origin)
        self._set_credentials_header(response.headers)
        self._set_expose_headers_header(response.headers)
        self._set_private_network_header(response.headers, request)
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """
        Verifica si el origen está permitido.
        
        Args:
            origin: Origen del request
            
        Returns:
            True si está permitido
        """
        if not origin:
            return True  # Request sin origen (mismo dominio)
        
        # Modo desarrollo permite localhost
        if self.development_mode and self._is_localhost(origin):
            return True
        
        # Permitir todos los orígenes
        if self.allow_all_origins:
            return True
        
        # Verificar lista específica
        if origin in self.allow_origins:
            return True
        
        # Verificar regex
        if self.allow_origin_regex and self.allow_origin_regex.match(origin):
            return True
        
        return False
    
    def _is_method_allowed(self, method: str) -> bool:
        """Verifica si el método está permitido."""
        if self.allow_all_methods:
            return True
        return method.upper() in self.allow_methods
    
    def _are_headers_allowed(self, headers_str: str) -> bool:
        """Verifica si los headers están permitidos."""
        if self.allow_all_headers:
            return True
        
        requested_headers = [h.strip().lower() for h in headers_str.split(",")]
        allowed_headers_lower = {h.lower() for h in self.allow_headers}
        
        return all(header in allowed_headers_lower for header in requested_headers)
    
    def _is_localhost(self, origin: str) -> bool:
        """Verifica si el origen es localhost."""
        try:
            parsed = urlparse(origin)
            return parsed.hostname in [
                "localhost", "127.0.0.1", "0.0.0.0", "::1"
            ] or parsed.hostname.endswith(".localhost")
        except Exception:
            return False
    
    def _set_origin_header(self, headers: Dict, origin: Optional[str]):
        """Establece el header Access-Control-Allow-Origin."""
        if self.allow_all_origins and not self.allow_credentials:
            headers["Access-Control-Allow-Origin"] = "*"
        elif origin and self._is_origin_allowed(origin):
            headers["Access-Control-Allow-Origin"] = origin
    
    def _set_methods_header(self, headers: Dict):
        """Establece el header Access-Control-Allow-Methods."""
        if self.allow_all_methods:
            headers["Access-Control-Allow-Methods"] = "*"
        else:
            methods = ", ".join(sorted(self.allow_methods))
            headers["Access-Control-Allow-Methods"] = methods
    
    def _set_headers_header(self, headers: Dict, requested_headers: Optional[str]):
        """Establece el header Access-Control-Allow-Headers."""
        if self.allow_all_headers:
            if requested_headers:
                headers["Access-Control-Allow-Headers"] = requested_headers
            else:
                headers["Access-Control-Allow-Headers"] = "*"
        else:
            allowed_headers = ", ".join(sorted(self.allow_headers))
            headers["Access-Control-Allow-Headers"] = allowed_headers
    
    def _set_credentials_header(self, headers: Dict):
        """Establece el header Access-Control-Allow-Credentials."""
        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
    
    def _set_expose_headers_header(self, headers: Dict):
        """Establece el header Access-Control-Expose-Headers."""
        if self.expose_headers:
            expose_headers = ", ".join(sorted(self.expose_headers))
            headers["Access-Control-Expose-Headers"] = expose_headers
    
    def _set_max_age_header(self, headers: Dict):
        """Establece el header Access-Control-Max-Age."""
        if self.max_age > 0:
            headers["Access-Control-Max-Age"] = str(self.max_age)
    
    def _set_private_network_header(self, headers: Dict, request: Request):
        """Establece headers para redes privadas."""
        if self.allow_private_networks:
            # Header para permitir acceso desde redes privadas
            if request.headers.get("access-control-request-private-network"):
                headers["Access-Control-Allow-Private-Network"] = "true"
    
    def _validate_configuration(self):
        """Valida la configuración CORS."""
        # Advertir sobre configuraciones inseguras
        if self.allow_all_origins and self.allow_credentials:
            logger.warning(
                "CORS: Configuración insegura - allow_all_origins=True "
                "con allow_credentials=True"
            )
        
        if self.development_mode:
            logger.info("CORS: Modo desarrollo habilitado - localhost permitido")


class SecureCORSMiddleware(CORSMiddleware):
    """Middleware CORS con configuraciones de seguridad mejoradas."""
    
    def __init__(
        self,
        app: ASGIApp,
        allowed_domains: List[str] = None,
        **kwargs
    ):
        # Configuración segura por defecto
        secure_defaults = {
            "allow_credentials": True,
            "allow_origins": allowed_domains or [],
            "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            "allow_headers": [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-Requested-With",
                "X-Request-ID"
            ],
            "expose_headers": ["X-Request-ID", "X-Process-Time"],
            "max_age": 3600,  # 1 hora
            "development_mode": False
        }
        
        # Combinar con configuración proporcionada
        config = {**secure_defaults, **kwargs}
        
        super().__init__(app, **config)
        
        # Logging de configuración
        logger.info(f"Secure CORS configured for domains: {allowed_domains}")


def setup_cors(
    app,
    environment: str = "production",
    allowed_origins: List[str] = None,
    development_mode: bool = False
):
    """
    Configura CORS según el entorno.
    
    Args:
        app: Aplicación FastAPI
        environment: Entorno (development, staging, production)
        allowed_origins: Orígenes permitidos
        development_mode: Modo desarrollo
    """
    if environment == "development" or development_mode:
        # Configuración permisiva para desarrollo
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins or ["http://localhost:3000", "http://localhost:8080"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            development_mode=True
        )
        logger.info("CORS configured for development environment")
    
    elif environment == "staging":
        # Configuración intermedia para staging
        staging_origins = allowed_origins or [
            "https://staging.catequesis.com",
            "https://test.catequesis.com"
        ]
        app.add_middleware(
            SecureCORSMiddleware,
            allowed_domains=staging_origins,
            max_age=3600
        )
        logger.info(f"CORS configured for staging: {staging_origins}")
    
    else:  # production
        # Configuración estricta para producción
        if not allowed_origins:
            logger.warning("No CORS origins specified for production!")
            return
        
        app.add_middleware(
            SecureCORSMiddleware,
            allowed_domains=allowed_origins,
            max_age=86400  # 24 horas
        )
        logger.info(f"CORS configured for production: {allowed_origins}")


class CORSConfigValidator:
    """Validador de configuración CORS."""
    
    @staticmethod
    def validate_origins(origins: List[str]) -> Dict[str, List[str]]:
        """
        Valida lista de orígenes.
        
        Returns:
            Dict con orígenes válidos e inválidos
        """
        valid_origins = []
        invalid_origins = []
        
        for origin in origins:
            if CORSConfigValidator._is_valid_origin(origin):
                valid_origins.append(origin)
            else:
                invalid_origins.append(origin)
        
        return {
            "valid": valid_origins,
            "invalid": invalid_origins
        }
    
    @staticmethod
    def _is_valid_origin(origin: str) -> bool:
        """Verifica si un origen es válido."""
        if origin == "*":
            return True
        
        try:
            parsed = urlparse(origin)
            return all([
                parsed.scheme in ["http", "https"],
                parsed.netloc,
                not parsed.path or parsed.path == "/",
                not parsed.query,
                not parsed.fragment
            ])
        except Exception:
            return False
    
    @staticmethod
    def get_security_recommendations(config: Dict) -> List[str]:
        """Obtiene recomendaciones de seguridad."""
        recommendations = []
        
        if config.get("allow_origins") == ["*"] and config.get("allow_credentials"):
            recommendations.append(
                "Evitar allow_origins='*' con allow_credentials=True"
            )
        
        if config.get("allow_methods") == ["*"]:
            recommendations.append(
                "Especificar métodos HTTP específicos en lugar de '*'"
            )
        
        if config.get("max_age", 0) > 86400:
            recommendations.append(
                "Considerar reducir max_age a máximo 24 horas"
            )
        
        return recommendations