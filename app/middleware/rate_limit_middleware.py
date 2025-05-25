"""
Middleware de Rate Limiting para control de tráfico y prevención de abuso.
Implementa múltiples estrategias de limitación y protección DDoS.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, List, Optional, Callable, Union
import logging
import time
import asyncio
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import redis
import json

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """Regla de rate limiting."""
    requests: int  # Número de requests permitidos
    window: int    # Ventana de tiempo en segundos
    scope: str = "ip"  # Alcance: 'ip', 'user', 'endpoint', 'global'
    burst: Optional[int] = None  # Ráfaga permitida
    description: str = ""


@dataclass
class RateLimitStatus:
    """Estado actual del rate limit."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None


class MemoryRateLimiter:
    """Rate limiter basado en memoria (para desarrollo/testing)."""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.cleanup_interval = 60  # Limpieza cada minuto
        self.last_cleanup = time.time()
    
    async def is_allowed(
        self, 
        key: str, 
        rule: RateLimitRule
    ) -> RateLimitStatus:
        """Verifica si el request está permitido."""
        current_time = time.time()
        
        # Limpieza periódica
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_old_requests()
            self.last_cleanup = current_time
        
        # Obtener ventana de requests
        window_start = current_time - rule.window
        requests_queue = self.requests[key]
        
        # Remover requests antiguos
        while requests_queue and requests_queue[0] < window_start:
            requests_queue.popleft()
        
        # Verificar límite
        current_count = len(requests_queue)
        
        if current_count >= rule.requests:
            # Calcular tiempo de reset
            oldest_request = requests_queue[0] if requests_queue else current_time
            reset_time = datetime.fromtimestamp(oldest_request + rule.window)
            retry_after = int((oldest_request + rule.window) - current_time)
            
            return RateLimitStatus(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=max(retry_after, 1)
            )
        
        # Registrar request actual
        requests_queue.append(current_time)
        
        return RateLimitStatus(
            allowed=True,
            remaining=rule.requests - current_count - 1,
            reset_time=datetime.fromtimestamp(window_start + rule.window)
        )
    
    async def _cleanup_old_requests(self):
        """Limpia requests antiguos de memoria."""
        current_time = time.time()
        keys_to_remove = []
        
        for key, requests_queue in self.requests.items():
            # Remover requests de más de 1 hora
            cutoff_time = current_time - 3600
            while requests_queue and requests_queue[0] < cutoff_time:
                requests_queue.popleft()
            
            # Marcar clave para eliminación si está vacía
            if not requests_queue:
                keys_to_remove.append(key)
        
        # Eliminar claves vacías
        for key in keys_to_remove:
            del self.requests[key]


class RedisRateLimiter:
    """Rate limiter basado en Redis (para producción)."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def is_allowed(
        self, 
        key: str, 
        rule: RateLimitRule
    ) -> RateLimitStatus:
        """Verifica si el request está permitido usando Redis."""
        try:
            # Usar algoritmo de sliding window con Redis
            current_time = int(time.time())
            window_start = current_time - rule.window
            
            # Pipeline para operaciones atómicas
            pipe = self.redis.pipeline()
            
            # Remover requests antiguos
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Contar requests actuales
            pipe.zcard(key)
            
            # Agregar request actual
            pipe.zadd(key, {str(current_time): current_time})
            
            # Establecer expiración
            pipe.expire(key, rule.window + 10)
            
            # Ejecutar pipeline
            results = pipe.execute()
            current_count = results[1]
            
            if current_count > rule.requests:
                # Obtener el request más antiguo para calcular reset
                oldest_requests = self.redis.zrange(key, 0, 0, withscores=True)
                oldest_time = oldest_requests[0][1] if oldest_requests else current_time
                
                reset_time = datetime.fromtimestamp(oldest_time + rule.window)
                retry_after = int((oldest_time + rule.window) - current_time)
                
                # Remover el request que acabamos de agregar
                self.redis.zrem(key, str(current_time))
                
                return RateLimitStatus(
                    allowed=False,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=max(retry_after, 1)
                )
            
            return RateLimitStatus(
                allowed=True,
                remaining=rule.requests - current_count,
                reset_time=datetime.fromtimestamp(current_time + rule.window)
            )
            
        except Exception as e:
            logger.error(f"Redis rate limiter error: {str(e)}")
            # En caso de error, permitir el request
            return RateLimitStatus(
                allowed=True,
                remaining=0,
                reset_time=datetime.now() + timedelta(seconds=rule.window)
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware principal de rate limiting."""
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        default_rules: List[RateLimitRule] = None,
        path_rules: Dict[str, List[RateLimitRule]] = None,
        exclude_paths: List[str] = None,
        key_func: Optional[Callable] = None,
        error_message: str = "Rate limit exceeded"
    ):
        super().__init__(app)
        
        # Configurar limiter backend
        if redis_client:
            self.limiter = RedisRateLimiter(redis_client)
        else:
            self.limiter = MemoryRateLimiter()
        
        # Reglas por defecto
        self.default_rules = default_rules or [
            RateLimitRule(
                requests=100,
                window=60,
                scope="ip",
                description="100 requests per minute per IP"
            )
        ]
        
        # Reglas específicas por path
        self.path_rules = path_rules or {}
        
        # Paths excluidos
        self.exclude_paths = set(exclude_paths or [
            "/health", "/healthz", "/ping", "/metrics"
        ])
        
        # Función para generar clave
        self.key_func = key_func or self._default_key_func
        
        self.error_message = error_message
    
    async def dispatch(self, request: Request, call_next):
        """Procesa rate limiting en cada request."""
        try:
            # Verificar si el path está excluido
            if self._is_excluded_path(request.url.path):
                return await call_next(request)
            
            # Obtener reglas aplicables
            rules = self._get_applicable_rules(request)
            
            # Verificar cada regla
            for rule in rules:
                key = await self._generate_key(request, rule)
                status = await self.limiter.is_allowed(key, rule)
                
                if not status.allowed:
                    return self._create_rate_limit_response(status, rule)
            
            # Procesar request
            response = await call_next(request)
            
            # Agregar headers informativos
            self._add_rate_limit_headers(response, rules)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {str(e)}")
            # En caso de error, continuar sin rate limiting
            return await call_next(request)
    
    def _get_applicable_rules(self, request: Request) -> List[RateLimitRule]:
        """Obtiene reglas aplicables para el request."""
        path = request.url.path
        method = request.method
        
        # Buscar reglas específicas del path
        for pattern, rules in self.path_rules.items():
            if self._match_path_pattern(pattern, f"{method} {path}"):
                return rules
        
        # Usar reglas por defecto
        return self.default_rules
    
    async def _generate_key(self, request: Request, rule: RateLimitRule) -> str:
        """Genera clave única para el rate limit."""
        base_key = await self.key_func(request, rule)
        rule_hash = hashlib.md5(
            f"{rule.requests}:{rule.window}:{rule.scope}".encode()
        ).hexdigest()[:8]
        
        return f"rate_limit:{rule.scope}:{rule_hash}:{base_key}"
    
    async def _default_key_func(self, request: Request, rule: RateLimitRule) -> str:
        """Función por defecto para generar claves."""
        if rule.scope == "ip":
            return request.client.host if request.client else "unknown"
        
        elif rule.scope == "user":
            if hasattr(request.state, 'current_user') and request.state.current_user:
                return str(request.state.current_user.get("id", "anonymous"))
            return "anonymous"
        
        elif rule.scope == "endpoint":
            return f"{request.method}:{request.url.path}"
        
        elif rule.scope == "global":
            return "global"
        
        else:
            # Scope personalizado
            return f"{rule.scope}:{request.client.host if request.client else 'unknown'}"
    
    def _create_rate_limit_response(
        self, 
        status: RateLimitStatus, 
        rule: RateLimitRule
    ) -> JSONResponse:
        """Crea response de rate limit excedido."""
        headers = {
            "X-RateLimit-Limit": str(rule.requests),
            "X-RateLimit-Remaining": str(status.remaining),
            "X-RateLimit-Reset": str(int(status.reset_time.timestamp())),
        }
        
        if status.retry_after:
            headers["Retry-After"] = str(status.retry_after)
        
        content = {
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": self.error_message,
                "details": {
                    "limit": rule.requests,
                    "window": rule.window,
                    "remaining": status.remaining,
                    "reset_time": status.reset_time.isoformat(),
                    "retry_after": status.retry_after
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        return JSONResponse(
            status_code=429,
            content=content,
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response: Response, rules: List[RateLimitRule]):
        """Agrega headers informativos de rate limit."""
        if rules:
            # Usar la primera regla para headers informativos
            rule = rules[0]
            response.headers["X-RateLimit-Limit"] = str(rule.requests)
            response.headers["X-RateLimit-Window"] = str(rule.window)
    
    def _is_excluded_path(self, path: str) -> bool:
        """Verifica si el path está excluido."""
        return any(
            path.startswith(excluded_path.rstrip("/"))
            for excluded_path in self.exclude_paths
        )
    
    def _match_path_pattern(self, pattern: str, path: str) -> bool:
        """Verifica si un path coincide con un patrón."""
        import re
        
        # Convertir patrón a regex
        regex_pattern = pattern.replace("{id}", r"[^/]+")
        regex_pattern = regex_pattern.replace("*", ".*")
        regex_pattern = f"^{regex_pattern}$"
        
        return bool(re.match(regex_pattern, path))


class AdaptiveRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting adaptivo basado en carga del sistema."""
    
    def __init__(
        self,
        app,
        base_rule: RateLimitRule,
        redis_client: Optional[redis.Redis] = None,
        load_threshold: float = 0.8,
        adaptive_factor: float = 0.5
    ):
        super().__init__(app)
        self.base_rule = base_rule
        self.load_threshold = load_threshold
        self.adaptive_factor = adaptive_factor
        
        if redis_client:
            self.limiter = RedisRateLimiter(redis_client)
        else:
            self.limiter = MemoryRateLimiter()
        
        self.system_load = 0.0
        self.last_load_check = 0
    
    async def dispatch(self, request: Request, call_next):
        """Aplica rate limiting adaptivo."""
        # Actualizar carga del sistema
        await self._update_system_load()
        
        # Calcular límite adaptivo
        adaptive_rule = self._calculate_adaptive_rule()
        
        # Aplicar rate limiting
        key = f"adaptive:{request.client.host if request.client else 'unknown'}"
        status = await self.limiter.is_allowed(key, adaptive_rule)
        
        if not status.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "ADAPTIVE_RATE_LIMIT_EXCEEDED",
                        "message": "Sistema bajo alta carga, intente más tarde",
                        "system_load": self.system_load,
                        "adaptive_limit": adaptive_rule.requests,
                        "retry_after": status.retry_after
                    }
                },
                headers={
                    "Retry-After": str(status.retry_after) if status.retry_after else "60",
                    "X-System-Load": str(self.system_load)
                }
            )
        
        response = await call_next(request)
        response.headers["X-System-Load"] = str(self.system_load)
        response.headers["X-Adaptive-Limit"] = str(adaptive_rule.requests)
        
        return response
    
    async def _update_system_load(self):
        """Actualiza la métrica de carga del sistema."""
        current_time = time.time()
        
        # Actualizar cada 10 segundos
        if current_time - self.last_load_check < 10:
            return
        
        try:
            import psutil
            
            # Combinar CPU y memoria para carga del sistema
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            self.system_load = (cpu_percent + memory_percent) / 200.0  # Normalizar a 0-1
            self.last_load_check = current_time
            
        except ImportError:
            # Fallback si psutil no está disponible
            self.system_load = 0.5
        except Exception as e:
            logger.error(f"Error updating system load: {str(e)}")
    
    def _calculate_adaptive_rule(self) -> RateLimitRule:
        """Calcula regla de rate limit adaptiva."""
        if self.system_load < self.load_threshold:
            # Sistema con carga normal
            return self.base_rule
        
        # Reducir límite basado en la carga
        load_factor = (self.system_load - self.load_threshold) / (1.0 - self.load_threshold)
        reduction = load_factor * self.adaptive_factor
        
        adaptive_requests = max(
            int(self.base_rule.requests * (1 - reduction)),
            1  # Mínimo 1 request
        )
        
        return RateLimitRule(
            requests=adaptive_requests,
            window=self.base_rule.window,
            scope=self.base_rule.scope,
            description=f"Adaptive limit (load: {self.system_load:.2f})"
        )


class DDoSProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware especializado para protección DDoS."""
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        suspicious_threshold: int = 50,  # Requests por minuto para marcar como sospechoso
        block_duration: int = 900,       # 15 minutos de bloqueo
        whitelist_ips: List[str] = None
    ):
        super().__init__(app)
        self.suspicious_threshold = suspicious_threshold
        self.block_duration = block_duration
        self.whitelist_ips = set(whitelist_ips or [])
        
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = None
            self.blocked_ips = {}  # Fallback en memoria
            self.suspicious_ips = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        """Protección DDoS en cada request."""
        client_ip = request.client.host if request.client else "unknown"
        
        # Verificar whitelist
        if client_ip in self.whitelist_ips:
            return await call_next(request)
        
        # Verificar si IP está bloqueada
        if await self._is_ip_blocked(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "IP_BLOCKED",
                        "message": "IP temporalmente bloqueada por actividad sospechosa",
                        "blocked_until": self._get_block_expiry(client_ip)
                    }
                }
            )
        
        # Registrar actividad
        await self._record_activity(client_ip)
        
        # Verificar si debe bloquear
        if await self._should_block_ip(client_ip):
            await self._block_ip(client_ip)
            logger.warning(f"IP {client_ip} blocked for suspicious activity")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "IP_BLOCKED",
                        "message": "IP bloqueada por actividad sospechosa"
                    }
                }
            )
        
        return await call_next(request)
    
    async def _is_ip_blocked(self, ip: str) -> bool:
        """Verifica si una IP está bloqueada."""
        if self.redis:
            blocked_until = await self.redis.get(f"blocked_ip:{ip}")
            if blocked_until:
                return int(blocked_until) > time.time()
        else:
            blocked_until = self.blocked_ips.get(ip)
            if blocked_until and blocked_until > time.time():
                return True
            elif blocked_until:
                del self.blocked_ips[ip]
        
        return False
    
    async def _record_activity(self, ip: str):
        """Registra actividad de una IP."""
        current_time = time.time()
        
        if self.redis:
            # Usar Redis para tracking
            key = f"activity:{ip}"
            await self.redis.zadd(key, {str(current_time): current_time})
            await self.redis.expire(key, 3600)  # Expirar en 1 hora
        else:
            # Usar memoria
            if ip not in self.suspicious_ips:
                self.suspicious_ips[ip] = []
            
            self.suspicious_ips[ip].append(current_time)
            
            # Limpiar actividad antigua
            cutoff_time = current_time - 3600
            self.suspicious_ips[ip] = [
                t for t in self.suspicious_ips[ip] if t > cutoff_time
            ]
    
    async def _should_block_ip(self, ip: str) -> bool:
        """Determina si debe bloquear una IP."""
        current_time = time.time()
        window_start = current_time - 60  # Ventana de 1 minuto
        
        if self.redis:
            count = await self.redis.zcount(f"activity:{ip}", window_start, current_time)
        else:
            activity = self.suspicious_ips.get(ip, [])
            count = sum(1 for t in activity if t > window_start)
        
        return count > self.suspicious_threshold
    
    async def _block_ip(self, ip: str):
        """Bloquea una IP por tiempo determinado."""
        block_until = time.time() + self.block_duration
        
        if self.redis:
            await self.redis.set(f"blocked_ip:{ip}", int(block_until), ex=self.block_duration)
        else:
            self.blocked_ips[ip] = block_until
    
    def _get_block_expiry(self, ip: str) -> Optional[str]:
        """Obtiene la fecha de expiración del bloqueo."""
        if self.redis:
            # En implementación real, obtendríamos de Redis
            return (datetime.now() + timedelta(seconds=self.block_duration)).isoformat()
        else:
            blocked_until = self.blocked_ips.get(ip)
            if blocked_until:
                return datetime.fromtimestamp(blocked_until).isoformat()
        return None


def create_rate_limit_rules() -> Dict[str, List[RateLimitRule]]:
    """Crea reglas de rate limiting predefinidas."""
    return {
        # API de autenticación - más restrictivo
        "POST /auth/login": [
            RateLimitRule(
                requests=5,
                window=60,
                scope="ip",
                description="5 login attempts per minute per IP"
            ),
            RateLimitRule(
                requests=10,
                window=3600,
                scope="ip",
                description="10 login attempts per hour per IP"
            )
        ],
        
        # Recuperación de contraseña - muy restrictivo
        "POST /auth/forgot-password": [
            RateLimitRule(
                requests=3,
                window=300,
                scope="ip",
                description="3 password reset requests per 5 minutes per IP"
            )
        ],
        
        # Registro de usuarios
        "POST /auth/register": [
            RateLimitRule(
                requests=3,
                window=3600,
                scope="ip",
                description="3 registrations per hour per IP"
            )
        ],
        
        # APIs administrativas
        "*/admin/*": [
            RateLimitRule(
                requests=30,
                window=60,
                scope="user",
                description="30 admin requests per minute per user"
            )
        ],
        
        # APIs de búsqueda
        "GET /api/search/*": [
            RateLimitRule(
                requests=20,
                window=60,
                scope="user",
                description="20 search requests per minute per user"
            )
        ],
        
        # APIs de catequizandos
        "GET /api/catequizandos": [
            RateLimitRule(
                requests=100,
                window=60,
                scope="user",
                description="100 GET catequizandos per minute per user"
            )
        ],
        
        "POST /api/catequizandos": [
            RateLimitRule(
                requests=20,
                window=60,
                scope="user",
                description="20 create catequizandos per minute per user"
            )
        ],
        
        "PUT /api/catequizandos/*": [
            RateLimitRule(
                requests=30,
                window=60,
                scope="user",
                description="30 update catequizandos per minute per user"
            )
        ],
        
        "DELETE /api/catequizandos/*": [
            RateLimitRule(
                requests=10,
                window=60,
                scope="user",
                description="10 delete catequizandos per minute per user"
            )
        ],
        
        # APIs de grupos
        "GET /api/grupos": [
            RateLimitRule(
                requests=50,
                window=60,
                scope="user",
                description="50 GET grupos per minute per user"
            )
        ],
        
        "POST /api/grupos": [
            RateLimitRule(
                requests=10,
                window=60,
                scope="user",
                description="10 create grupos per minute per user"
            )
        ],
        
        # APIs de inscripciones
        "POST /api/inscripciones": [
            RateLimitRule(
                requests=15,
                window=60,
                scope="user",
                description="15 inscripciones per minute per user"
            )
        ],
        
        # APIs de asistencias
        "POST /api/asistencias": [
            RateLimitRule(
                requests=100,
                window=60,
                scope="user",
                description="100 asistencias per minute per user"
            )
        ],
        
        # API de reportes - más restrictivo por ser intensivo
        "GET /api/reportes/*": [
            RateLimitRule(
                requests=5,
                window=60,
                scope="user",
                description="5 report requests per minute per user"
            ),
            RateLimitRule(
                requests=20,
                window=3600,
                scope="user",
                description="20 report requests per hour per user"
            )
        ],
        
        # Subida de archivos
        "POST /api/upload/*": [
            RateLimitRule(
                requests=10,
                window=300,
                scope="user",
                description="10 file uploads per 5 minutes per user"
            )
        ],
        
        # APIs de notificaciones
        "POST /api/notificaciones": [
            RateLimitRule(
                requests=25,
                window=60,
                scope="user",
                description="25 notifications per minute per user"
            )
        ],
        
        # APIs de certificados
        "POST /api/certificados/generar": [
            RateLimitRule(
                requests=5,
                window=60,
                scope="user",
                description="5 certificate generations per minute per user"
            )
        ],
        
        # APIs de backup/export
        "GET /api/export/*": [
            RateLimitRule(
                requests=2,
                window=300,
                scope="user",
                description="2 exports per 5 minutes per user"
            )
        ],
        
        # APIs de configuración
        "PUT /api/configuracion/*": [
            RateLimitRule(
                requests=10,
                window=60,
                scope="user",
                description="10 config changes per minute per user"
            )
        ]
    }


class BurstRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para manejar ráfagas de tráfico con token bucket."""
    
    def __init__(
        self,
        app,
        bucket_size: int = 10,
        refill_rate: float = 1.0,  # tokens por segundo
        redis_client: Optional[redis.Redis] = None
    ):
        super().__init__(app)
        self.bucket_size = bucket_size
        self.refill_rate = refill_rate
        self.redis = redis_client
        
        if not redis_client:
            self.buckets = {}  # Fallback en memoria
    
    async def dispatch(self, request: Request, call_next):
        """Aplica token bucket rate limiting."""
        client_ip = request.client.host if request.client else "unknown"
        
        # Verificar y consumir token
        if not await self._consume_token(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "BURST_LIMIT_EXCEEDED",
                        "message": "Demasiadas requests en ráfaga. Intente más despacio.",
                        "bucket_size": self.bucket_size,
                        "refill_rate": self.refill_rate,
                        "recommendation": "Espacie sus requests para evitar este límite"
                    }
                },
                headers={
                    "Retry-After": "1",
                    "X-Burst-Limit": str(self.bucket_size),
                    "X-Refill-Rate": str(self.refill_rate)
                }
            )
        
        response = await call_next(request)
        
        # Agregar headers informativos
        remaining_tokens = await self._get_remaining_tokens(client_ip)
        response.headers["X-Burst-Remaining"] = str(remaining_tokens)
        
        return response
    
    async def _consume_token(self, key: str) -> bool:
        """Consume un token del bucket."""
        current_time = time.time()
        
        if self.redis:
            return await self._consume_token_redis(key, current_time)
        else:
            return self._consume_token_memory(key, current_time)
    
    async def _consume_token_redis(self, key: str, current_time: float) -> bool:
        """Implementación con Redis usando Lua script."""
        lua_script = """
        local key = KEYS[1]
        local bucket_size = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or bucket_size
        local last_refill = tonumber(bucket[2]) or current_time
        
        -- Calcular tokens a agregar
        local time_passed = current_time - last_refill
        local tokens_to_add = math.floor(time_passed * refill_rate)
        tokens = math.min(bucket_size, tokens + tokens_to_add)
        
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
            redis.call('EXPIRE', key, 3600)
            return 0
        end
        """
        
        try:
            result = await self.redis.eval(
                lua_script,
                1,
                f"bucket:{key}",
                self.bucket_size,
                self.refill_rate,
                current_time
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Redis token bucket error: {str(e)}")
            return True  # Permitir en caso de error
    
    def _consume_token_memory(self, key: str, current_time: float) -> bool:
        """Implementación en memoria."""
        if key not in self.buckets:
            self.buckets[key] = {
                'tokens': self.bucket_size,
                'last_refill': current_time
            }
        
        bucket = self.buckets[key]
        
        # Calcular tokens a agregar
        time_passed = current_time - bucket['last_refill']
        tokens_to_add = int(time_passed * self.refill_rate)
        
        bucket['tokens'] = min(self.bucket_size, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = current_time
        
        # Consumir token si está disponible
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True
        
        return False
    
    async def _get_remaining_tokens(self, key: str) -> int:
        """Obtiene tokens restantes en el bucket."""
        if self.redis:
            try:
                bucket = await self.redis.hmget(f"bucket:{key}", 'tokens')
                return int(bucket[0]) if bucket[0] else self.bucket_size
            except:
                return self.bucket_size
        else:
            bucket = self.buckets.get(key)
            return bucket['tokens'] if bucket else self.bucket_size


class SmartRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware inteligente que ajusta límites basado en patrones de uso."""
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        learning_window: int = 3600,  # 1 hora
        adjustment_factor: float = 0.1
    ):
        super().__init__(app)
        self.redis = redis_client
        self.learning_window = learning_window
        self.adjustment_factor = adjustment_factor
        self.base_limits = {
            "new_user": 30,      # Usuarios nuevos
            "regular_user": 60,   # Usuarios regulares
            "trusted_user": 120,  # Usuarios de confianza
            "admin_user": 200     # Administradores
        }
        self.learned_limits = {}
    
    async def dispatch(self, request: Request, call_next):
        """Aplica rate limiting inteligente."""
        user_id = None
        if hasattr(request.state, 'current_user') and request.state.current_user:
            user_id = request.state.current_user.get("id")
        
        if not user_id:
            # Para usuarios no autenticados, usar rate limiting básico
            return await call_next(request)
        
        # Obtener límite inteligente
        endpoint = f"{request.method}:{request.url.path}"
        limit = await self._get_smart_limit(user_id, endpoint)
        
        # Verificar límite
        if not await self._check_limit(user_id, endpoint, limit):
            # Obtener tiempo de reset
            reset_time = await self._get_reset_time(user_id, endpoint)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "SMART_RATE_LIMIT_EXCEEDED",
                        "message": "Límite personalizado excedido",
                        "learned_limit": limit,
                        "user_pattern": await self._get_user_pattern(user_id),
                        "reset_time": reset_time
                    }
                },
                headers={
                    "X-Smart-Limit": str(limit),
                    "X-Reset-Time": reset_time,
                    "Retry-After": str(self._calculate_retry_after(reset_time))
                }
            )
        
        # Registrar uso
        await self._record_usage(user_id, endpoint)
        
        response = await call_next(request)
        
        # Agregar headers informativos
        remaining = await self._get_remaining_requests(user_id, endpoint, limit)
        response.headers["X-Smart-Limit"] = str(limit)
        response.headers["X-Smart-Remaining"] = str(remaining)
        
        return response
    
    async def _get_smart_limit(self, user_id: str, endpoint: str) -> int:
        """Obtiene límite inteligente para usuario/endpoint."""
        cache_key = f"smart_limit:{user_id}:{endpoint}"
        
        if self.redis:
            cached_limit = await self.redis.get(cache_key)
            if cached_limit:
                return int(cached_limit)
        
        # Determinar categoría del usuario
        user_category = await self._categorize_user(user_id)
        base_limit = self.base_limits.get(user_category, 60)
        
        # Obtener patrones históricos
        historical_usage = await self._get_historical_usage(user_id, endpoint)
        
        if historical_usage and len(historical_usage) >= 10:  # Mínimo 10 datos históricos
            # Calcular límite basado en percentil 90
            sorted_usage = sorted(historical_usage)
            p90_index = int(len(sorted_usage) * 0.90)
            historical_limit = sorted_usage[p90_index] if p90_index < len(sorted_usage) else sorted_usage[-1]
            
            # Ajustar límite (promedio ponderado)
            smart_limit = int((base_limit * 0.3) + (historical_limit * 1.5 * 0.7))
            
            # Aplicar límites mínimos y máximos
            smart_limit = max(10, min(smart_limit, base_limit * 3))
        else:
            # Para usuarios sin historial suficiente
            smart_limit = base_limit
        
        # Cache el límite por 1 hora
        if self.redis:
            await self.redis.setex(cache_key, 3600, smart_limit)
        
        return smart_limit
    
    async def _categorize_user(self, user_id: str) -> str:
        """Categoriza al usuario basado en su historial."""
        if self.redis:
            # Obtener métricas del usuario
            total_requests = await self.redis.get(f"user_metrics:{user_id}:total")
            account_age = await self.redis.get(f"user_metrics:{user_id}:age")
            violation_count = await self.redis.get(f"user_metrics:{user_id}:violations")
            
            total_requests = int(total_requests) if total_requests else 0
            account_age = int(account_age) if account_age else 0
            violation_count = int(violation_count) if violation_count else 0
            
            # Lógica de categorización
            if violation_count > 5:
                return "new_user"  # Usuarios con violaciones frecuentes
            elif account_age > 30 * 24 * 3600 and total_requests > 10000:  # 30 días y >10k requests
                return "trusted_user"
            elif account_age > 7 * 24 * 3600:  # 7 días
                return "regular_user"
            else:
                return "new_user"
        
        return "regular_user"  # Fallback
    
    async def _get_historical_usage(self, user_id: str, endpoint: str) -> List[int]:
        """Obtiene patrones de uso histórico del usuario."""
        if not self.redis:
            return []
        
        try:
            # Obtener uso por hora de los últimos 7 días
            usage_data = []
            current_time = int(time.time())
            
            for i in range(24 * 7):  # 7 días * 24 horas
                hour_start = current_time - (i * 3600)
                hour_end = hour_start + 3600
                
                key = f"usage:{user_id}:{endpoint}"
                count = await self.redis.zcount(key, hour_start, hour_end)
                if count > 0:
                    usage_data.append(count)
            
            return usage_data[-50:]  # Últimas 50 horas con actividad
            
        except Exception as e:
            logger.error(f"Error getting historical usage: {str(e)}")
            return []
    
    async def _check_limit(self, user_id: str, endpoint: str, limit: int) -> bool:
        """Verifica si el usuario está dentro del límite."""
        key = f"usage:{user_id}:{endpoint}"
        current_time = int(time.time())
        window_start = current_time - 3600  # 1 hora
        
        if self.redis:
            count = await self.redis.zcount(key, window_start, current_time)
            return count < limit
        else:
            return True  # Fallback
    
    async def _record_usage(self, user_id: str, endpoint: str):
        """Registra uso del endpoint."""
        if not self.redis:
            return
        
        current_time = time.time()
        key = f"usage:{user_id}:{endpoint}"
        
        # Registrar timestamp del request
        await self.redis.zadd(key, {str(current_time): current_time})
        await self.redis.expire(key, 7 * 24 * 3600)  # 7 días
        
        # Actualizar métricas del usuario
        metrics_key = f"user_metrics:{user_id}:total"
        await self.redis.incr(metrics_key)
        await self.redis.expire(metrics_key, 30 * 24 * 3600)  # 30 días
    
    async def _get_user_pattern(self, user_id: str) -> Dict[str, Any]:
        """Obtiene patrón de uso del usuario."""
        if not self.redis:
            return {}
        
        try:
            total_requests = await self.redis.get(f"user_metrics:{user_id}:total")
            category = await self._categorize_user(user_id)
            
            return {
                "category": category,
                "total_requests": int(total_requests) if total_requests else 0,
                "trust_level": category
            }
        except:
            return {"category": "unknown"}
    
    async def _get_reset_time(self, user_id: str, endpoint: str) -> str:
        """Obtiene tiempo de reset del rate limit."""
        current_time = int(time.time())
        next_hour = ((current_time // 3600) + 1) * 3600
        return datetime.fromtimestamp(next_hour).isoformat()
    
    def _calculate_retry_after(self, reset_time: str) -> int:
        """Calcula segundos hasta el reset."""
        try:
            reset_dt = datetime.fromisoformat(reset_time.replace('Z', '+00:00'))
            now = datetime.utcnow()
            delta = (reset_dt - now).total_seconds()
            return max(1, int(delta))
        except:
            return 60  # Fallback
    
    async def _get_remaining_requests(self, user_id: str, endpoint: str, limit: int) -> int:
        """Obtiene requests restantes en la ventana actual."""
        if not self.redis:
            return limit
        
        current_time = int(time.time())
        window_start = current_time - 3600
        key = f"usage:{user_id}:{endpoint}"
        
        try:
            used = await self.redis.zcount(key, window_start, current_time)
            return max(0, limit - used)
        except:
            return limit


def setup_rate_limiting(
    app,
    environment: str = "production",
    redis_client: Optional[redis.Redis] = None,
    enable_ddos_protection: bool = True,
    enable_adaptive: bool = False,
    enable_smart_limits: bool = True
):
    """
    Configura rate limiting para la aplicación.
    
    Args:
        app: Aplicación FastAPI
        environment: Entorno de ejecución
        redis_client: Cliente Redis opcional
        enable_ddos_protection: Habilitar protección DDoS
        enable_adaptive: Habilitar rate limiting adaptivo
        enable_smart_limits: Habilitar límites inteligentes
    """
    # Configuración base según entorno
    if environment == "development":
        default_rules = [
            RateLimitRule(
                requests=1000,
                window=60,
                scope="ip",
                description="Development rate limit - very permissive"
            )
        ]
        ddos_threshold = 500
        block_duration = 60
    elif environment == "staging":
        default_rules = [
            RateLimitRule(
                requests=200,
                window=60,
                scope="ip",
                description="Staging rate limit"
            ),
            RateLimitRule(
                requests=2000,
                window=3600,
                scope="ip",
                description="Staging hourly limit"
            )
        ]
        ddos_threshold = 300
        block_duration = 300
    else:  # production
        default_rules = [
            RateLimitRule(
                requests=100,
                window=60,
                scope="ip",
                description="Production rate limit per minute"
            ),
            RateLimitRule(
                requests=1000,
                window=3600,
                scope="ip",
                description="Production rate limit per hour"
            ),
            RateLimitRule(
                requests=5000,
                window=86400,
                scope="ip",
                description="Production rate limit per day"
            )
        ]
        ddos_threshold = 150
        block_duration = 900
    
    # Middleware principal de rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        redis_client=redis_client,
        default_rules=default_rules,
        path_rules=create_rate_limit_rules(),
        exclude_paths=["/health", "/healthz", "/ping", "/metrics", "/static"]
    )
    
    # Rate limiting inteligente
    if enable_smart_limits and redis_client:
        app.add_middleware(
            SmartRateLimitMiddleware,
            redis_client=redis_client,
            learning_window=3600,
            adjustment_factor=0.15
        )
    
    # Protección DDoS
    if enable_ddos_protection and environment != "development":
        app.add_middleware(
            DDoSProtectionMiddleware,
            redis_client=redis_client,
            suspicious_threshold=ddos_threshold,
            block_duration=block_duration,
            whitelist_ips=["127.0.0.1", "::1"]  # IPs de confianza
        )
    
    # Rate limiting adaptivo (experimental)
    if enable_adaptive and redis_client:
        app.add_middleware(
            AdaptiveRateLimitMiddleware,
            base_rule=RateLimitRule(requests=75, window=60, scope="ip"),
            redis_client=redis_client,
            load_threshold=0.75,
            adaptive_factor=0.4
        )
    
    # Token bucket para ráfagas
    app.add_middleware(
        BurstRateLimitMiddleware,
        bucket_size=20 if environment == "production" else 50,
        refill_rate=2.0 if environment == "production" else 5.0,
        redis_client=redis_client
    )
    
    logger.info(
        f"Rate limiting configured for {environment} environment - "
        f"DDoS: {enable_ddos_protection}, Adaptive: {enable_adaptive}, "
        f"Smart: {enable_smart_limits}"
    )


# Configuraciones predefinidas por entorno
class RateLimitConfig:
    """Configuraciones predefinidas de rate limiting."""
    
    @staticmethod
    def get_production_config() -> Dict[str, Any]:
        """Configuración optimizada para producción."""
        return {
            "default_rules": [
                RateLimitRule(requests=60, window=60, scope="ip"),
                RateLimitRule(requests=500, window=3600, scope="ip"),
                RateLimitRule(requests=2000, window=86400, scope="ip")
            ],
            "enable_ddos_protection": True,
            "enable_adaptive": True,
            "enable_smart_limits": True,
            "suspicious_threshold": 120,
            "block_duration": 900,
            "burst_bucket_size": 15,
            "burst_refill_rate": 1.5
        }
    
    @staticmethod
    def get_development_config() -> Dict[str, Any]:
        """Configuración permisiva para desarrollo."""
        return {
            "default_rules": [
                RateLimitRule(requests=1000, window=60, scope="ip")
            ],
            "enable_ddos_protection": False,
            "enable_adaptive": False,
            "enable_smart_limits": False,
            "burst_bucket_size": 100,
            "burst_refill_rate": 10.0
        }
    
    @staticmethod
    def get_staging_config() -> Dict[str, Any]:
        """Configuración intermedia para staging."""
        return {
            "default_rules": [
                RateLimitRule(requests=150, window=60, scope="ip"),
                RateLimitRule(requests=800, window=3600, scope="ip")
            ],
            "enable_ddos_protection": True,
            "enable_adaptive": False,
            "enable_smart_limits": True,
            "suspicious_threshold": 200,
            "block_duration": 300,
            "burst_bucket_size": 25,
            "burst_refill_rate": 3.0
        }
    
    @staticmethod
    def get_high_traffic_config() -> Dict[str, Any]:
        """Configuración para alta concurrencia."""
        return {
            "default_rules": [
                RateLimitRule(requests=200, window=60, scope="ip"),
                RateLimitRule(requests=1500, window=3600, scope="ip")
            ],
            "enable_ddos_protection": True,
            "enable_adaptive": True,
            "enable_smart_limits": True,
            "suspicious_threshold": 300,
            "block_duration": 600,
            "burst_bucket_size": 30,
            "burst_refill_rate": 2.5
        }