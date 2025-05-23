"""
Modelo de Usuario para el sistema de catequesis.
Maneja la autenticación, autorización y gestión de usuarios.
"""

import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError, SecurityError
from app.utils.validators import DataValidator
from app.utils.security import PasswordManager, TokenManager
from app.utils.constants import SystemConstants

logger = logging.getLogger(__name__)


class TipoPerfil(Enum):
    """Tipos de perfil de usuario."""
    ADMINISTRADOR = "administrador"
    COORDINADOR = "coordinador"
    CATEQUISTA = "catequista"
    ASISTENTE = "asistente"
    SOLO_LECTURA = "solo_lectura"


class EstadoUsuario(Enum):
    """Estados del usuario."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    BLOQUEADO = "bloqueado"
    PENDIENTE_ACTIVACION = "pendiente_activacion"
    SUSPENDIDO = "suspendido"


class Usuario(BaseModel):
    """
    Modelo de Usuario del sistema de catequesis.
    Maneja autenticación, autorización y datos del usuario.
    """
    
    # Configuración del modelo
    _table_schema = "usuarios"
    _primary_key = "id_usuario"
    _required_fields = ["username", "password", "tipo_perfil"]
    _unique_fields = ["username", "email"]
    _searchable_fields = ["username", "email", "nombres", "apellidos"]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Usuario."""
        # Datos básicos del usuario
        self.id_usuario: Optional[int] = None
        self.username: str = ""
        self.email: Optional[str] = None
        self.nombres: Optional[str] = None
        self.apellidos: Optional[str] = None
        
        # Seguridad
        self.password_hash: Optional[str] = None
        self.salt: Optional[str] = None
        self.tipo_perfil: TipoPerfil = TipoPerfil.SOLO_LECTURA
        self.estado: EstadoUsuario = EstadoUsuario.PENDIENTE_ACTIVACION
        
        # Relaciones
        self.id_parroquia: Optional[int] = None
        self.id_catequista: Optional[int] = None
        
        # Control de sesión
        self.ultimo_acceso: Optional[datetime] = None
        self.intentos_fallidos: int = 0
        self.bloqueado_hasta: Optional[datetime] = None
        self.token_session: Optional[str] = None
        self.token_expiration: Optional[datetime] = None
        
        # Control de contraseña
        self.fecha_cambio_password: Optional[datetime] = None
        self.requiere_cambio_password: bool = True
        self.token_reset_password: Optional[str] = None
        self.token_reset_expiration: Optional[datetime] = None
        
        # Configuración del usuario
        self.preferencias: Dict[str, Any] = {}
        self.permisos_especiales: Set[str] = set()
        
        # Managers de utilidad
        self._password_manager = PasswordManager()
        self._token_manager = TokenManager()
        
        super().__init__(**kwargs)
    
    @property
    def nombre_completo(self) -> str:
        """Obtiene el nombre completo del usuario."""
        nombres = self.nombres or ""
        apellidos = self.apellidos or ""
        return f"{nombres} {apellidos}".strip() or self.username
    
    @property
    def esta_activo(self) -> bool:
        """Verifica si el usuario está activo."""
        return self.estado == EstadoUsuario.ACTIVO
    
    @property
    def esta_bloqueado(self) -> bool:
        """Verifica si el usuario está bloqueado."""
        if self.estado == EstadoUsuario.BLOQUEADO:
            return True
        
        if self.bloqueado_hasta:
            return datetime.now() < self.bloqueado_hasta
        
        return False
    
    @property
    def necesita_cambiar_password(self) -> bool:
        """Verifica si necesita cambiar la contraseña."""
        if self.requiere_cambio_password:
            return True
        
        # Verificar si la contraseña ha expirado (90 días)
        if self.fecha_cambio_password:
            expiracion = self.fecha_cambio_password + timedelta(days=90)
            return datetime.now() > expiracion
        
        return False
    
    @property
    def permisos(self) -> Set[str]:
        """Obtiene los permisos del usuario basados en su perfil."""
        permisos_base = self._get_permisos_por_perfil()
        return permisos_base.union(self.permisos_especiales)
    
    def _get_permisos_por_perfil(self) -> Set[str]:
        """Obtiene permisos base según el tipo de perfil."""
        permisos_perfil = {
            TipoPerfil.ADMINISTRADOR: {
                "usuarios.crear", "usuarios.editar", "usuarios.eliminar", "usuarios.listar",
                "parroquias.crear", "parroquias.editar", "parroquias.eliminar", "parroquias.listar",
                "catequistas.crear", "catequistas.editar", "catequistas.eliminar", "catequistas.listar",
                "catequizandos.crear", "catequizandos.editar", "catequizandos.eliminar", "catequizandos.listar",
                "grupos.crear", "grupos.editar", "grupos.eliminar", "grupos.listar",
                "inscripciones.crear", "inscripciones.editar", "inscripciones.eliminar", "inscripciones.listar",
                "asistencias.crear", "asistencias.editar", "asistencias.eliminar", "asistencias.listar",
                "calificaciones.crear", "calificaciones.editar", "calificaciones.eliminar", "calificaciones.listar",
                "reportes.generar", "reportes.exportar", "sistema.configurar"
            },
            TipoPerfil.COORDINADOR: {
                "catequistas.crear", "catequistas.editar", "catequistas.listar",
                "catequizandos.crear", "catequizandos.editar", "catequizandos.listar",
                "grupos.crear", "grupos.editar", "grupos.listar",
                "inscripciones.crear", "inscripciones.editar", "inscripciones.listar",
                "asistencias.crear", "asistencias.editar", "asistencias.listar",
                "calificaciones.crear", "calificaciones.editar", "calificaciones.listar",
                "reportes.generar", "reportes.exportar"
            },
            TipoPerfil.CATEQUISTA: {
                "catequizandos.listar", "catequizandos.editar",
                "grupos.listar", "inscripciones.listar",
                "asistencias.crear", "asistencias.editar", "asistencias.listar",
                "calificaciones.crear", "calificaciones.editar", "calificaciones.listar",
                "reportes.generar"
            },
            TipoPerfil.ASISTENTE: {
                "catequizandos.crear", "catequizandos.editar", "catequizandos.listar",
                "inscripciones.crear", "inscripciones.editar", "inscripciones.listar",
                "asistencias.crear", "asistencias.listar",
                "calificaciones.listar"
            },
            TipoPerfil.SOLO_LECTURA: {
                "catequizandos.listar", "grupos.listar",
                "inscripciones.listar", "asistencias.listar",
                "calificaciones.listar"
            }
        }
        
        return permisos_perfil.get(self.tipo_perfil, set())
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Usuario."""
        # Validar username
        if self.username:
            if len(self.username) < 3:
                raise ValidationError("El username debe tener al menos 3 caracteres")
            if not self.username.replace('_', '').replace('.', '').isalnum():
                raise ValidationError("El username solo puede contener letras, números, puntos y guiones bajos")
        
        # Validar email
        if self.email and not DataValidator.validate_email(self.email):
            raise ValidationError("El formato del email no es válido")
        
        # Validar tipo de perfil
        if isinstance(self.tipo_perfil, str):
            try:
                self.tipo_perfil = TipoPerfil(self.tipo_perfil)
            except ValueError:
                raise ValidationError(f"Tipo de perfil '{self.tipo_perfil}' no válido")
        
        # Validar estado
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoUsuario(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        # Validar que usuarios coordinadores/catequistas tengan parroquia
        if self.tipo_perfil in [TipoPerfil.COORDINADOR, TipoPerfil.CATEQUISTA]:
            if not self.id_parroquia:
                raise ValidationError("Los coordinadores y catequistas deben tener una parroquia asignada")
    
    def set_password(self, password: str) -> None:
        """
        Establece la contraseña del usuario.
        
        Args:
            password: Contraseña en texto plano
            
        Raises:
            ValidationError: Si la contraseña no cumple los requisitos
        """
        # Validar fortaleza de la contraseña
        if not self._password_manager.validate_password_strength(password):
            raise ValidationError(
                "La contraseña debe tener al menos 8 caracteres, "
                "incluir mayúsculas, minúsculas, números y caracteres especiales"
            )
        
        # Generar salt y hash
        self.salt = secrets.token_hex(16)
        self.password_hash = self._password_manager.hash_password(password, self.salt)
        self.fecha_cambio_password = datetime.now()
        self.requiere_cambio_password = False
        
        logger.info(f"Contraseña actualizada para usuario {self.username}")
    
    def verify_password(self, password: str) -> bool:
        """
        Verifica la contraseña del usuario.
        
        Args:
            password: Contraseña a verificar
            
        Returns:
            bool: True si la contraseña es correcta
        """
        if not self.password_hash or not self.salt:
            return False
        
        return self._password_manager.verify_password(password, self.password_hash, self.salt)
    
    def authenticate(self, password: str) -> Dict[str, Any]:
        """
        Autentica al usuario con contraseña.
        
        Args:
            password: Contraseña a verificar
            
        Returns:
            dict: Resultado de la autenticación
            
        Raises:
            SecurityError: Si hay problemas de seguridad
        """
        # Verificar si está bloqueado
        if self.esta_bloqueado:
            raise SecurityError("Usuario bloqueado")
        
        # Verificar si está activo
        if not self.esta_activo:
            raise SecurityError("Usuario inactivo")
        
        # Verificar contraseña
        if self.verify_password(password):
            # Autenticación exitosa
            self.ultimo_acceso = datetime.now()
            self.intentos_fallidos = 0
            self.bloqueado_hasta = None
            
            # Generar token de sesión
            self.token_session = self._token_manager.generate_session_token(self.id_usuario)
            self.token_expiration = datetime.now() + timedelta(hours=8)
            
            logger.info(f"Autenticación exitosa para usuario {self.username}")
            
            return {
                "success": True,
                "token": self.token_session,
                "expires_at": self.token_expiration,
                "user_id": self.id_usuario,
                "requires_password_change": self.necesita_cambiar_password
            }
        else:
            # Autenticación fallida
            self.intentos_fallidos += 1
            
            # Bloquear después de 5 intentos fallidos
            if self.intentos_fallidos >= 5:
                self.estado = EstadoUsuario.BLOQUEADO
                self.bloqueado_hasta = datetime.now() + timedelta(minutes=30)
                logger.warning(f"Usuario {self.username} bloqueado por intentos fallidos")
            
            logger.warning(f"Intento de autenticación fallido para usuario {self.username}")
            
            return {
                "success": False,
                "message": "Credenciales incorrectas",
                "attempts_remaining": max(0, 5 - self.intentos_fallidos)
            }
    
    def logout(self) -> None:
        """Cierra la sesión del usuario."""
        self.token_session = None
        self.token_expiration = None
        logger.info(f"Sesión cerrada para usuario {self.username}")
    
    def generate_password_reset_token(self) -> str:
        """
        Genera un token para reset de contraseña.
        
        Returns:
            str: Token de reset
        """
        self.token_reset_password = self._token_manager.generate_reset_token()
        self.token_reset_expiration = datetime.now() + timedelta(hours=2)
        
        logger.info(f"Token de reset generado para usuario {self.username}")
        return self.token_reset_password
    
    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """
        Resetea la contraseña usando un token.
        
        Args:
            token: Token de reset
            new_password: Nueva contraseña
            
        Returns:
            bool: True si el reset fue exitoso
            
        Raises:
            SecurityError: Si el token es inválido
        """
        if not self.token_reset_password or self.token_reset_password != token:
            raise SecurityError("Token de reset inválido")
        
        if not self.token_reset_expiration or datetime.now() > self.token_reset_expiration:
            raise SecurityError("Token de reset expirado")
        
        # Cambiar contraseña
        self.set_password(new_password)
        
        # Limpiar token de reset
        self.token_reset_password = None
        self.token_reset_expiration = None
        
        # Reiniciar estado de bloqueo
        self.estado = EstadoUsuario.ACTIVO
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        
        logger.info(f"Contraseña reseteada para usuario {self.username}")
        return True
    
    def validate_session_token(self, token: str) -> bool:
        """
        Valida un token de sesión.
        
        Args:
            token: Token a validar
            
        Returns:
            bool: True si el token es válido
        """
        if not self.token_session or self.token_session != token:
            return False
        
        if not self.token_expiration or datetime.now() > self.token_expiration:
            return False
        
        return True
    
    def extend_session(self, hours: int = 8) -> None:
        """
        Extiende la sesión actual.
        
        Args:
            hours: Horas a extender
        """
        if self.token_session:
            self.token_expiration = datetime.now() + timedelta(hours=hours)
    
    def has_permission(self, permission: str) -> bool:
        """
        Verifica si el usuario tiene un permiso específico.
        
        Args:
            permission: Permiso a verificar
            
        Returns:
            bool: True si tiene el permiso
        """
        return permission in self.permisos
    
    def can_access_parroquia(self, id_parroquia: int) -> bool:
        """
        Verifica si el usuario puede acceder a una parroquia específica.
        
        Args:
            id_parroquia: ID de la parroquia
            
        Returns:
            bool: True si puede acceder
        """
        # Administradores pueden acceder a todas las parroquias
        if self.tipo_perfil == TipoPerfil.ADMINISTRADOR:
            return True
        
        # Otros usuarios solo a su parroquia asignada
        return self.id_parroquia == id_parroquia
    
    def add_special_permission(self, permission: str) -> None:
        """
        Añade un permiso especial al usuario.
        
        Args:
            permission: Permiso a añadir
        """
        self.permisos_especiales.add(permission)
        logger.info(f"Permiso especial '{permission}' añadido a usuario {self.username}")
    
    def remove_special_permission(self, permission: str) -> None:
        """
        Remueve un permiso especial del usuario.
        
        Args:
            permission: Permiso a remover
        """
        self.permisos_especiales.discard(permission)
        logger.info(f"Permiso especial '{permission}' removido de usuario {self.username}")
    
    def update_preferences(self, preferences: Dict[str, Any]) -> None:
        """
        Actualiza las preferencias del usuario.
        
        Args:
            preferences: Diccionario con preferencias
        """
        self.preferencias.update(preferences)
        logger.debug(f"Preferencias actualizadas para usuario {self.username}")
    
    def activate(self) -> None:
        """Activa el usuario."""
        self.estado = EstadoUsuario.ACTIVO
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        logger.info(f"Usuario {self.username} activado")
    
    def deactivate(self) -> None:
        """Desactiva el usuario."""
        self.estado = EstadoUsuario.INACTIVO
        self.logout()
        logger.info(f"Usuario {self.username} desactivado")
    
    def suspend(self, until: datetime = None) -> None:
        """
        Suspende el usuario.
        
        Args:
            until: Fecha hasta cuando está suspendido
        """
        self.estado = EstadoUsuario.SUSPENDIDO
        self.bloqueado_hasta = until
        self.logout()
        logger.info(f"Usuario {self.username} suspendido")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario.
        
        Args:
            include_audit: Si incluir información de auditoría
            include_sensitive: Si incluir datos sensibles
            
        Returns:
            dict: Datos del modelo
        """
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_perfil'] = self.tipo_perfil.value
        data['estado'] = self.estado.value
        
        # Convertir sets a listas
        data['permisos_especiales'] = list(self.permisos_especiales)
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'password_hash', 'salt', 'token_session', 'token_reset_password'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_username(cls, username: str) -> Optional['Usuario']:
        """
        Busca un usuario por nombre de usuario.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            Usuario: El usuario encontrado o None
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.usuarios.obtener_usuario_por_username(username)
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando usuario por username {username}: {str(e)}")
            return None
    
    @classmethod
    def find_by_email(cls, email: str) -> Optional['Usuario']:
        """
        Busca un usuario por email.
        
        Args:
            email: Email del usuario
            
        Returns:
            Usuario: El usuario encontrado o None
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'usuarios',
                'obtener_por_email',
                {'email': email}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando usuario por email {email}: {str(e)}")
            return None
    
    @classmethod
    def find_by_parroquia(cls, id_parroquia: int) -> List['Usuario']:
        """
        Busca usuarios de una parroquia específica.
        
        Args:
            id_parroquia: ID de la parroquia
            
        Returns:
            List: Lista de usuarios de la parroquia
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.usuarios.obtener_usuarios_por_parroquia(id_parroquia)
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando usuarios por parroquia {id_parroquia}: {str(e)}")
            return []
    
    @classmethod
    def create_admin_user(
        cls,
        username: str,
        password: str,
        email: str = None,
        nombres: str = None,
        apellidos: str = None
    ) -> 'Usuario':
        """
        Crea un usuario administrador.
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            email: Email (opcional)
            nombres: Nombres (opcional)
            apellidos: Apellidos (opcional)
            
        Returns:
            Usuario: El usuario administrador creado
        """
        admin = cls(
            username=username,
            email=email,
            nombres=nombres,
            apellidos=apellidos,
            tipo_perfil=TipoPerfil.ADMINISTRADOR,
            estado=EstadoUsuario.ACTIVO
        )
        
        admin.set_password(password)
        admin.requiere_cambio_password = False
        
        return admin


# Registrar el modelo en la factory
ModelFactory.register('usuario', Usuario)