"""
Servicio de gestión de permisos y autorización para el sistema de catequesis.
Maneja roles, permisos, políticas de acceso y control de autorización.
"""

from typing import Dict, Any, List, Optional, Type, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from functools import wraps
from enum import Enum

from app.services.base_service import BaseService
from app.models.seguridad.rol_model import Rol
from app.models.seguridad.permiso_model import Permiso
from app.models.seguridad.rol_permiso_model import RolPermiso
from app.models.seguridad.usuario_model import Usuario
from app.models.seguridad.usuario_rol_model import UsuarioRol
from app.schemas.seguridad.permission_schema import (
    RolCreateSchema, RolUpdateSchema, RolResponseSchema,
    PermisoCreateSchema, PermisoUpdateSchema, PermisoResponseSchema,
    AsignacionRolSchema, AsignacionPermisoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException,
    AuthorizationException
)
from app.utils.cache import cache_manager
import logging

logger = logging.getLogger(__name__)


class AccionPermiso(Enum):
    """Enum para acciones de permisos."""
    CREAR = "crear"
    LEER = "leer"
    ACTUALIZAR = "actualizar"
    ELIMINAR = "eliminar"
    LISTAR = "listar"
    EXPORTAR = "exportar"
    IMPORTAR = "importar"
    ADMINISTRAR = "administrar"


class RecursoSistema(Enum):
    """Enum para recursos del sistema."""
    USUARIOS = "usuarios"
    ROLES = "roles"
    PERMISOS = "permisos"
    PARROQUIAS = "parroquias"
    CATEQUIZANDOS = "catequizandos"
    CATEQUISTAS = "catequistas"
    GRUPOS = "grupos"
    INSCRIPCIONES = "inscripciones"
    PAGOS = "pagos"
    CERTIFICADOS = "certificados"
    NOTIFICACIONES = "notificaciones"
    REPORTES = "reportes"
    CONFIGURACION = "configuracion"


class PermissionService(BaseService):
    """Servicio para gestión de permisos y autorización."""
    
    @property
    def model(self) -> Type[Rol]:
        return Rol
    
    @property
    def create_schema(self) -> Type[RolCreateSchema]:
        return RolCreateSchema
    
    @property
    def update_schema(self) -> Type[RolUpdateSchema]:
        return RolUpdateSchema
    
    @property
    def response_schema(self) -> Type[RolResponseSchema]:
        return RolResponseSchema
    
    def __init__(self, db: Session = None, current_user: Dict = None):
        super().__init__(db, current_user)
        self.cache_timeout = 300  # 5 minutos
    
    # ==========================================
    # GESTIÓN DE ROLES
    # ==========================================
    
    def create_rol(self, rol_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo rol con permisos opcionales.
        
        Args:
            rol_data: Datos del rol incluyendo permisos
            
        Returns:
            Dict con el rol creado
        """
        try:
            # Validar permisos para crear roles
            self._require_permission('roles', 'crear')
            
            # Validar datos
            schema = RolCreateSchema()
            validated_data = schema.load(rol_data)
            
            # Verificar que el nombre del rol no existe
            if self.db.query(Rol).filter(Rol.nombre == validated_data['nombre']).first():
                raise ValidationException("Ya existe un rol con ese nombre")
            
            # Crear rol
            permisos_nombres = validated_data.pop('permisos', [])
            rol = Rol(**validated_data)
            rol.created_at = datetime.utcnow()
            rol.created_by = self.current_user.get('id') if self.current_user else None
            
            self.db.add(rol)
            self.db.flush()
            
            # Asignar permisos si se especificaron
            if permisos_nombres:
                self._assign_permissions_to_role(rol, permisos_nombres)
            
            self.db.commit()
            
            # Limpiar caché
            self._clear_permissions_cache()
            
            logger.info(f"Rol creado: {rol.nombre} por usuario {self.current_user.get('id')}")
            
            return self._serialize_rol_with_permissions(rol)
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando rol: {str(e)}")
            raise BusinessLogicException("Error creando rol")
    
    def update_rol(self, rol_id: int, rol_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un rol y sus permisos.
        
        Args:
            rol_id: ID del rol
            rol_data: Datos a actualizar
            
        Returns:
            Dict con el rol actualizado
        """
        try:
            self._require_permission('roles', 'actualizar')
            
            # Obtener rol
            rol = self.db.query(Rol).filter(Rol.id == rol_id).first()
            if not rol:
                raise NotFoundException("Rol no encontrado")
            
            # Validar que no sea un rol del sistema
            if rol.es_sistema:
                raise BusinessLogicException("No se puede modificar un rol del sistema")
            
            # Validar datos
            schema = RolUpdateSchema()
            validated_data = schema.load(rol_data)
            
            # Verificar nombre único (si cambió)
            if 'nombre' in validated_data and validated_data['nombre'] != rol.nombre:
                if self.db.query(Rol).filter(Rol.nombre == validated_data['nombre']).first():
                    raise ValidationException("Ya existe un rol con ese nombre")
            
            # Actualizar permisos si se especificaron
            if 'permisos' in validated_data:
                permisos_nombres = validated_data.pop('permisos')
                self._update_role_permissions(rol, permisos_nombres)
            
            # Actualizar campos del rol
            for key, value in validated_data.items():
                setattr(rol, key, value)
            
            rol.updated_at = datetime.utcnow()
            rol.updated_by = self.current_user.get('id') if self.current_user else None
            
            self.db.commit()
            
            # Limpiar caché
            self._clear_permissions_cache()
            
            logger.info(f"Rol actualizado: {rol.nombre}")
            
            return self._serialize_rol_with_permissions(rol)
            
        except (ValidationException, NotFoundException, BusinessLogicException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error actualizando rol: {str(e)}")
            raise BusinessLogicException("Error actualizando rol")
    
    def delete_rol(self, rol_id: int) -> Dict[str, Any]:
        """
        Elimina un rol si no tiene usuarios asignados.
        
        Args:
            rol_id: ID del rol
            
        Returns:
            Dict con confirmación
        """
        try:
            self._require_permission('roles', 'eliminar')
            
            # Obtener rol
            rol = self.db.query(Rol).filter(Rol.id == rol_id).first()
            if not rol:
                raise NotFoundException("Rol no encontrado")
            
            # Validar que no sea un rol del sistema
            if rol.es_sistema:
                raise BusinessLogicException("No se puede eliminar un rol del sistema")
            
            # Verificar que no tenga usuarios asignados
            usuarios_count = self.db.query(UsuarioRol).filter(UsuarioRol.rol_id == rol_id).count()
            if usuarios_count > 0:
                raise BusinessLogicException(f"No se puede eliminar. Tiene {usuarios_count} usuarios asignados")
            
            # Eliminar permisos del rol
            self.db.query(RolPermiso).filter(RolPermiso.rol_id == rol_id).delete()
            
            # Eliminar rol
            rol_nombre = rol.nombre
            self.db.delete(rol)
            self.db.commit()
            
            # Limpiar caché
            self._clear_permissions_cache()
            
            logger.info(f"Rol eliminado: {rol_nombre}")
            
            return {
                'success': True,
                'message': f'Rol "{rol_nombre}" eliminado exitosamente'
            }
            
        except (NotFoundException, BusinessLogicException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error eliminando rol: {str(e)}")
            raise BusinessLogicException("Error eliminando rol")
    
    def get_all_roles(self, include_permissions: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene todos los roles del sistema.
        
        Args:
            include_permissions: Si incluir permisos en la respuesta
            
        Returns:
            Lista de roles
        """
        try:
            self._require_permission('roles', 'listar')
            
            query = self.db.query(Rol).order_by(Rol.nombre)
            
            if include_permissions:
                query = query.options(
                    joinedload(Rol.permisos).joinedload(RolPermiso.permiso)
                )
            
            roles = query.all()
            
            if include_permissions:
                return [self._serialize_rol_with_permissions(rol) for rol in roles]
            else:
                schema = RolResponseSchema()
                return [schema.dump(rol) for rol in roles]
                
        except Exception as e:
            logger.error(f"Error obteniendo roles: {str(e)}")
            raise BusinessLogicException("Error obteniendo roles")
    
    # ==========================================
    # GESTIÓN DE PERMISOS
    # ==========================================
    
    def create_permiso(self, permiso_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo permiso.
        
        Args:
            permiso_data: Datos del permiso
            
        Returns:
            Dict con el permiso creado
        """
        try:
            self._require_permission('permisos', 'crear')
            
            schema = PermisoCreateSchema()
            validated_data = schema.load(permiso_data)
            
            # Verificar que no existe
            existing = self.db.query(Permiso).filter(
                and_(
                    Permiso.recurso == validated_data['recurso'],
                    Permiso.accion == validated_data['accion']
                )
            ).first()
            
            if existing:
                raise ValidationException("Ya existe un permiso para ese recurso y acción")
            
            # Crear permiso
            permiso = Permiso(**validated_data)
            permiso.created_at = datetime.utcnow()
            
            self.db.add(permiso)
            self.db.commit()
            
            # Limpiar caché
            self._clear_permissions_cache()
            
            logger.info(f"Permiso creado: {permiso.recurso}:{permiso.accion}")
            
            schema_response = PermisoResponseSchema()
            return schema_response.dump(permiso)
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creando permiso: {str(e)}")
            raise BusinessLogicException("Error creando permiso")
    
    def get_all_permisos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los permisos disponibles."""
        try:
            self._require_permission('permisos', 'listar')
            
            permisos = self.db.query(Permiso).order_by(
                Permiso.recurso, Permiso.accion
            ).all()
            
            schema = PermisoResponseSchema()
            return [schema.dump(permiso) for permiso in permisos]
            
        except Exception as e:
            logger.error(f"Error obteniendo permisos: {str(e)}")
            raise BusinessLogicException("Error obteniendo permisos")
    
    # ==========================================
    # ASIGNACIÓN DE ROLES Y PERMISOS
    # ==========================================
    
    def assign_role_to_user(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asigna un rol a un usuario.
        
        Args:
            assignment_data: Datos de asignación
            
        Returns:
            Dict con confirmación
        """
        try:
            self._require_permission('usuarios', 'administrar')
            
            schema = AsignacionRolSchema()
            validated_data = schema.load(assignment_data)
            
            user_id = validated_data['usuario_id']
            rol_id = validated_data['rol_id']
            
            # Verificar que el usuario existe
            user = self.db.query(Usuario).filter(Usuario.id == user_id).first()
            if not user:
                raise NotFoundException("Usuario no encontrado")
            
            # Verificar que el rol existe
            rol = self.db.query(Rol).filter(Rol.id == rol_id).first()
            if not rol:
                raise NotFoundException("Rol no encontrado")
            
            # Verificar que no esté ya asignado
            existing = self.db.query(UsuarioRol).filter(
                and_(
                    UsuarioRol.usuario_id == user_id,
                    UsuarioRol.rol_id == rol_id
                )
            ).first()
            
            if existing:
                raise ValidationException("El usuario ya tiene ese rol asignado")
            
            # Crear asignación
            user_rol = UsuarioRol(
                usuario_id=user_id,
                rol_id=rol_id,
                asignado_por=self.current_user.get('id'),
                fecha_asignacion=datetime.utcnow()
            )
            
            self.db.add(user_rol)
            self.db.commit()
            
            # Limpiar caché del usuario
            self._clear_user_permissions_cache(user_id)
            
            logger.info(f"Rol {rol.nombre} asignado a usuario {user.email}")
            
            return {
                'success': True,
                'message': f'Rol "{rol.nombre}" asignado exitosamente'
            }
            
        except (ValidationException, NotFoundException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error asignando rol: {str(e)}")
            raise BusinessLogicException("Error asignando rol")
    
    def remove_role_from_user(self, user_id: int, rol_id: int) -> Dict[str, Any]:
        """
        Remueve un rol de un usuario.
        
        Args:
            user_id: ID del usuario
            rol_id: ID del rol
            
        Returns:
            Dict con confirmación
        """
        try:
            self._require_permission('usuarios', 'administrar')
            
            # Verificar que la asignación existe
            user_rol = self.db.query(UsuarioRol).filter(
                and_(
                    UsuarioRol.usuario_id == user_id,
                    UsuarioRol.rol_id == rol_id
                )
            ).first()
            
            if not user_rol:
                raise NotFoundException("Asignación de rol no encontrada")
            
            # Obtener información para el log
            user = self.db.query(Usuario).filter(Usuario.id == user_id).first()
            rol = self.db.query(Rol).filter(Rol.id == rol_id).first()
            
            # Eliminar asignación
            self.db.delete(user_rol)
            self.db.commit()
            
            # Limpiar caché del usuario
            self._clear_user_permissions_cache(user_id)
            
            logger.info(f"Rol {rol.nombre if rol else rol_id} removido de usuario {user.email if user else user_id}")
            
            return {
                'success': True,
                'message': 'Rol removido exitosamente'
            }
            
        except NotFoundException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removiendo rol: {str(e)}")
            raise BusinessLogicException("Error removiendo rol")
    
    def assign_permission_to_role(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asigna un permiso a un rol.
        
        Args:
            assignment_data: Datos de asignación
            
        Returns:
            Dict con confirmación
        """
        try:
            self._require_permission('roles', 'administrar')
            
            schema = AsignacionPermisoSchema()
            validated_data = schema.load(assignment_data)
            
            rol_id = validated_data['rol_id']
            permiso_id = validated_data['permiso_id']
            
            # Verificar que el rol existe y no es del sistema
            rol = self.db.query(Rol).filter(Rol.id == rol_id).first()
            if not rol:
                raise NotFoundException("Rol no encontrado")
            
            if rol.es_sistema:
                raise BusinessLogicException("No se pueden modificar permisos de roles del sistema")
            
            # Verificar que el permiso existe
            permiso = self.db.query(Permiso).filter(Permiso.id == permiso_id).first()
            if not permiso:
                raise NotFoundException("Permiso no encontrado")
            
            # Verificar que no esté ya asignado
            existing = self.db.query(RolPermiso).filter(
                and_(
                    RolPermiso.rol_id == rol_id,
                    RolPermiso.permiso_id == permiso_id
                )
            ).first()
            
            if existing:
                raise ValidationException("El rol ya tiene ese permiso asignado")
            
            # Crear asignación
            rol_permiso = RolPermiso(
                rol_id=rol_id,
                permiso_id=permiso_id,
                asignado_por=self.current_user.get('id'),
                fecha_asignacion=datetime.utcnow()
            )
            
            self.db.add(rol_permiso)
            self.db.commit()
            
            # Limpiar caché
            self._clear_permissions_cache()
            
            logger.info(f"Permiso {permiso.recurso}:{permiso.accion} asignado a rol {rol.nombre}")
            
            return {
                'success': True,
                'message': f'Permiso asignado exitosamente'
            }
            
        except (ValidationException, NotFoundException, BusinessLogicException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error asignando permiso: {str(e)}")
            raise BusinessLogicException("Error asignando permiso")
    
    # ==========================================
    # VERIFICACIÓN DE PERMISOS
    # ==========================================
    
    def has_permission(self, user_id: int, recurso: str, accion: str) -> bool:
        """
        Verifica si un usuario tiene un permiso específico.
        
        Args:
            user_id: ID del usuario
            recurso: Recurso del permiso
            accion: Acción del permiso
            
        Returns:
            True si tiene el permiso
        """
        try:
            # Intentar obtener desde caché
            cache_key = f"user_permission:{user_id}:{recurso}:{accion}"
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Consultar base de datos
            has_perm = self.db.query(Usuario).join(UsuarioRol).join(Rol).join(RolPermiso).join(Permiso).filter(
                and_(
                    Usuario.id == user_id,
                    Usuario.activo == True,
                    Rol.activo == True,
                    Permiso.recurso == recurso,
                    Permiso.accion == accion
                )
            ).first() is not None
            
            # Guardar en caché
            cache_manager.set(cache_key, has_perm, timeout=self.cache_timeout)
            
            return has_perm
            
        except Exception as e:
            logger.error(f"Error verificando permiso: {str(e)}")
            return False
    
    def get_user_permissions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los permisos de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de permisos
        """
        try:
            # Intentar obtener desde caché
            cache_key = f"user_permissions:{user_id}"
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Consultar permisos del usuario
            permisos = self.db.query(Permiso).join(RolPermiso).join(Rol).join(UsuarioRol).filter(
                and_(
                    UsuarioRol.usuario_id == user_id,
                    Rol.activo == True
                )
            ).distinct().all()
            
            # Serializar
            schema = PermisoResponseSchema()
            result = [schema.dump(permiso) for permiso in permisos]
            
            # Guardar en caché
            cache_manager.set(cache_key, result, timeout=self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo permisos de usuario: {str(e)}")
            return []
    
    def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los roles de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de roles
        """
        try:
            roles = self.db.query(Rol).join(UsuarioRol).filter(
                UsuarioRol.usuario_id == user_id
            ).all()
            
            schema = RolResponseSchema()
            return [schema.dump(rol) for rol in roles]
            
        except Exception as e:
            logger.error(f"Error obteniendo roles de usuario: {str(e)}")
            return []
    
    def check_resource_access(self, user_id: int, recurso: str, accion: str, context: Dict[str, Any] = None) -> bool:
        """
        Verifica acceso a un recurso con contexto adicional.
        
        Args:
            user_id: ID del usuario
            recurso: Recurso solicitado
            accion: Acción solicitada
            context: Contexto adicional (parroquia, entidad específica, etc.)
            
        Returns:
            True si tiene acceso
        """
        # Verificar permiso básico
        if not self.has_permission(user_id, recurso, accion):
            return False
        
        # Verificar restricciones adicionales según contexto
        if context:
            return self._check_contextual_access(user_id, recurso, accion, context)
        
        return True
    
    # ==========================================
    # DECORADORES Y UTILIDADES
    # ==========================================
    
    def require_permission(self, recurso: str, accion: str):
        """
        Decorador para requerir permisos específicos.
        
        Args:
            recurso: Recurso requerido
            accion: Acción requerida
            
        Returns:
            Decorador
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.current_user:
                    raise AuthorizationException("Usuario no autenticado")
                
                user_id = self.current_user.get('id')
                if not self.has_permission(user_id, recurso, accion):
                    raise AuthorizationException(f"Sin permisos para {accion} {recurso}")
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _require_permission(self, recurso: str, accion: str):
        """Método auxiliar para verificar permisos en servicios."""
        if not self.current_user:
            raise AuthorizationException("Usuario no autenticado")
        
        user_id = self.current_user.get('id')
        if not self.has_permission(user_id, recurso, accion):
            raise AuthorizationException(f"Sin permisos para {accion} {recurso}")
    
    # ==========================================
    # INICIALIZACIÓN DEL SISTEMA
    # ==========================================
    
    def initialize_default_permissions(self) -> Dict[str, Any]:
        """
        Inicializa permisos por defecto del sistema.
        
        Returns:
            Dict con estadísticas de inicialización
        """
        try:
            created_permissions = 0
            created_roles = 0
            
            # Crear permisos básicos para cada recurso
            recursos_acciones = {
                RecursoSistema.USUARIOS.value: [
                    AccionPermiso.CREAR.value, AccionPermiso.LEER.value,
                    AccionPermiso.ACTUALIZAR.value, AccionPermiso.ELIMINAR.value,
                    AccionPermiso.LISTAR.value, AccionPermiso.ADMINISTRAR.value
                ],
                RecursoSistema.ROLES.value: [
                    AccionPermiso.CREAR.value, AccionPermiso.LEER.value,
                    AccionPermiso.ACTUALIZAR.value, AccionPermiso.ELIMINAR.value,
                    AccionPermiso.LISTAR.value, AccionPermiso.ADMINISTRAR.value
                ],
                RecursoSistema.CATEQUIZANDOS.value: [
                    AccionPermiso.CREAR.value, AccionPermiso.LEER.value,
                    AccionPermiso.ACTUALIZAR.value, AccionPermiso.ELIMINAR.value,
                    AccionPermiso.LISTAR.value, AccionPermiso.EXPORTAR.value
                ],
                RecursoSistema.CERTIFICADOS.value: [
                    AccionPermiso.CREAR.value, AccionPermiso.LEER.value,
                    AccionPermiso.ACTUALIZAR.value, AccionPermiso.LISTAR.value,
                    AccionPermiso.EXPORTAR.value
                ],
                RecursoSistema.REPORTES.value: [
                    AccionPermiso.LEER.value, AccionPermiso.EXPORTAR.value
                ]
            }
            
            # Crear permisos
            for recurso, acciones in recursos_acciones.items():
                for accion in acciones:
                    existing = self.db.query(Permiso).filter(
                        and_(Permiso.recurso == recurso, Permiso.accion == accion)
                    ).first()
                    
                    if not existing:
                        permiso = Permiso(
                            recurso=recurso,
                            accion=accion,
                            descripcion=f"Permiso para {accion} {recurso}",
                            created_at=datetime.utcnow()
                        )
                        self.db.add(permiso)
                        created_permissions += 1
            
            # Crear roles por defecto
            default_roles = [
                {
                    'nombre': 'super_admin',
                    'descripcion': 'Super Administrador con acceso total',
                    'es_sistema': True,
                    'activo': True
                },
                {
                    'nombre': 'admin',
                    'descripcion': 'Administrador con permisos de gestión',
                    'es_sistema': True,
                    'activo': True
                },
                {
                    'nombre': 'catequista',
                    'descripcion': 'Catequista con permisos básicos',
                    'es_sistema': True,
                    'activo': True
                },
                {
                    'nombre': 'usuario',
                    'descripcion': 'Usuario básico del sistema',
                    'es_sistema': True,
                    'activo': True
                }
            ]
            
            for rol_data in default_roles:
                existing = self.db.query(Rol).filter(Rol.nombre == rol_data['nombre']).first()
                if not existing:
                    rol = Rol(**rol_data)
                    rol.created_at = datetime.utcnow()
                    self.db.add(rol)
                    created_roles += 1
            
            self.db.commit()
            
            # Asignar permisos a roles
            self._assign_default_role_permissions()
            
            logger.info(f"Permisos inicializados: {created_permissions} permisos, {created_roles} roles")
            
            return {
                'success': True,
                'created_permissions': created_permissions,
                'created_roles': created_roles,
                'message': 'Permisos del sistema inicializados exitosamente'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inicializando permisos: {str(e)}")
            raise BusinessLogicException("Error inicializando permisos del sistema")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _assign_permissions_to_role(self, rol: Rol, permisos_nombres: List[str]):
        """Asigna permisos específicos a un rol."""
        for permiso_nombre in permisos_nombres:
            # Buscar permiso por recurso:accion
            if ':' in permiso_nombre:
                recurso, accion = permiso_nombre.split(':', 1)
                permiso = self.db.query(Permiso).filter(
                    and_(Permiso.recurso == recurso, Permiso.accion == accion)
                ).first()
            else:
                permiso = self.db.query(Permiso).filter(Permiso.id == permiso_nombre).first()
            
            if permiso:
                rol_permiso = RolPermiso(
                    rol_id=rol.id,
                    permiso_id=permiso.id,
                    asignado_por=self.current_user.get('id') if self.current_user else None,
                    fecha_asignacion=datetime.utcnow()
                )
                self.db.add(rol_permiso)
    
    def _update_role_permissions(self, rol: Rol, permisos_nombres: List[str]):
        """Actualiza todos los permisos de un rol."""
        # Eliminar permisos actuales
        self.db.query(RolPermiso).filter(RolPermiso.rol_id == rol.id).delete()
        
        # Asignar nuevos permisos
        self._assign_permissions_to_role(rol, permisos_nombres)
    
    def _serialize_rol_with_permissions(self, rol: Rol) -> Dict[str, Any]:
        """Serializa un rol con sus permisos."""
        schema = RolResponseSchema()
        rol_data = schema.dump(rol)
        
        # Agregar permisos
        permisos = []
        for rol_permiso in rol.permisos:
            permiso_schema = PermisoResponseSchema()
            permiso_data = permiso_schema.dump(rol_permiso.permiso)
            permiso_data['fecha_asignacion'] = rol_permiso.fecha_asignacion.isoformat() if rol_permiso.fecha_asignacion else None
            permisos.append(permiso_data)
        
        rol_data['permisos'] = permisos
        return rol_data
    
    def _check_contextual_access(self, user_id: int, recurso: str, accion: str, context: Dict[str, Any]) -> bool:
        """Verifica acceso contextual (ej: misma parroquia, propietario del recurso)."""
        # Implementar lógica de contexto específica
        # Por ejemplo, verificar que el usuario pertenezca a la misma parroquia
        # que el recurso que está intentando acceder
        
        parroquia_id = context.get('parroquia_id')
        if parroquia_id:
            user = self.db.query(Usuario).filter(Usuario.id == user_id).first()
            if user and user.parroquia_id != parroquia_id:
                # Verificar si tiene rol de admin que puede acceder a todas las parroquias
                user_roles = [rol.nombre for rol in user.roles]
                if 'super_admin' not in user_roles and 'admin' not in user_roles:
                    return False
        
        return True
    
    def _assign_default_role_permissions(self):
        """Asigna permisos por defecto a roles del sistema."""
        try:
            # Super Admin - todos los permisos
            super_admin = self.db.query(Rol).filter(Rol.nombre == 'super_admin').first()
            if super_admin:
                all_permisos = self.db.query(Permiso).all()
                for permiso in all_permisos:
                    existing = self.db.query(RolPermiso).filter(
                        and_(RolPermiso.rol_id == super_admin.id, RolPermiso.permiso_id == permiso.id)
                    ).first()
                    if not existing:
                        rol_permiso = RolPermiso(
                            rol_id=super_admin.id,
                            permiso_id=permiso.id,
                            fecha_asignacion=datetime.utcnow()
                        )
                        self.db.add(rol_permiso)
            
            # Admin - permisos de gestión
            admin = self.db.query(Rol).filter(Rol.nombre == 'admin').first()
            if admin:
                admin_permissions = [
                    f"{RecursoSistema.USUARIOS.value}:{AccionPermiso.CREAR.value}",
                    f"{RecursoSistema.USUARIOS.value}:{AccionPermiso.LEER.value}",
                    f"{RecursoSistema.USUARIOS.value}:{AccionPermiso.ACTUALIZAR.value}",
                    f"{RecursoSistema.USUARIOS.value}:{AccionPermiso.LISTAR.value}",
                    f"{RecursoSistema.CATEQUIZANDOS.value}:{AccionPermiso.CREAR.value}",
                    f"{RecursoSistema.CATEQUIZANDOS.value}:{AccionPermiso.LEER.value}",
                    f"{RecursoSistema.CATEQUIZANDOS.value}:{AccionPermiso.ACTUALIZAR.value}",
                    f"{RecursoSistema.CATEQUIZANDOS.value}:{AccionPermiso.LISTAR.value}",
                    f"{RecursoSistema.CERTIFICADOS.value}:{AccionPermiso.CREAR.value}",
                    f"{RecursoSistema.CERTIFICADOS.value}:{AccionPermiso.LEER.value}",
                    f"{RecursoSistema.CERTIFICADOS.value}:{AccionPermiso.LISTAR.value}",
                    f"{RecursoSistema.REPORTES.value}:{AccionPermiso.LEER.value}",
                    f"{RecursoSistema.REPORTES.value}:{AccionPermiso.EXPORTAR.value}"
                ]
                self._assign_permissions_by_name(admin, admin_permissions)
            
            # Catequista - permisos básicos
            catequista = self.db.query(Rol).filter(Rol.nombre == 'catequista').first()
            if catequista:
                catequista_permissions = [
                    f"{RecursoSistema.CATEQUIZANDOS.value}:{AccionPermiso.LEER.value}",
                    f"{RecursoSistema.CATEQUIZANDOS.value}:{AccionPermiso.LISTAR.value}",
                    f"{RecursoSistema.CERTIFICADOS.value}:{AccionPermiso.LEER.value}",
                    f"{RecursoSistema.CERTIFICADOS.value}:{AccionPermiso.LISTAR.value}"
                ]
                self._assign_permissions_by_name(catequista, catequista_permissions)
            
            # Usuario - permisos mínimos
            usuario = self.db.query(Rol).filter(Rol.nombre == 'usuario').first()
            if usuario:
                usuario_permissions = [
                    f"{RecursoSistema.CATEQUIZANDOS.value}:{AccionPermiso.LEER.value}"
                ]
                self._assign_permissions_by_name(usuario, usuario_permissions)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error asignando permisos por defecto: {str(e)}")
            raise
    
    def _assign_permissions_by_name(self, rol: Rol, permissions_list: List[str]):
        """Asigna permisos a un rol por nombre (recurso:accion)."""
        for perm_name in permissions_list:
            if ':' in perm_name:
                recurso, accion = perm_name.split(':', 1)
                permiso = self.db.query(Permiso).filter(
                    and_(Permiso.recurso == recurso, Permiso.accion == accion)
                ).first()
                
                if permiso:
                    existing = self.db.query(RolPermiso).filter(
                        and_(RolPermiso.rol_id == rol.id, RolPermiso.permiso_id == permiso.id)
                    ).first()
                    if not existing:
                        rol_permiso = RolPermiso(
                            rol_id=rol.id,
                            permiso_id=permiso.id,
                            fecha_asignacion=datetime.utcnow()
                        )
                        self.db.add(rol_permiso)
    
    def _clear_permissions_cache(self):
        """Limpia toda la caché de permisos."""
        try:
            cache_manager.delete_pattern("user_permission:*")
            cache_manager.delete_pattern("user_permissions:*")
            cache_manager.delete_pattern("role_permissions:*")
        except Exception as e:
            logger.warning(f"Error limpiando caché de permisos: {str(e)}")
    
    def _clear_user_permissions_cache(self, user_id: int):
        """Limpia la caché de permisos de un usuario específico."""
        try:
            cache_manager.delete_pattern(f"user_permission:{user_id}:*")
            cache_manager.delete(f"user_permissions:{user_id}")
        except Exception as e:
            logger.warning(f"Error limpiando caché de usuario {user_id}: {str(e)}")


# ==========================================
# FUNCIONES DE UTILIDAD PARA DECORADORES
# ==========================================

def require_permission(recurso: str, accion: str):
    """
    Decorador para métodos que requieren permisos específicos.
    
    Usage:
        @require_permission('usuarios', 'crear')
        def create_user(self, data):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'permission_service'):
                permission_service = self.permission_service
            else:
                permission_service = PermissionService(self.db, self.current_user)
            
            permission_service._require_permission(recurso, accion)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions):
    """
    Decorador que requiere al menos uno de los permisos especificados.
    
    Args:
        permissions: Tuplas de (recurso, accion)
        
    Usage:
        @require_any_permission(('usuarios', 'leer'), ('catequizandos', 'leer'))
        def get_dashboard_data(self):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'permission_service'):
                permission_service = self.permission_service
            else:
                permission_service = PermissionService(self.db, self.current_user)
            
            if not permission_service.current_user:
                raise AuthorizationException("Usuario no autenticado")
            
            user_id = permission_service.current_user.get('id')
            has_any_permission = any(
                permission_service.has_permission(user_id, recurso, accion)
                for recurso, accion in permissions
            )
            
            if not has_any_permission:
                perms_str = ', '.join([f"{r}:{a}" for r, a in permissions])
                raise AuthorizationException(f"Se requiere uno de los siguientes permisos: {perms_str}")
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles):
    """
    Decorador que requiere al menos uno de los roles especificados.
    
    Args:
        roles: Nombres de roles requeridos
        
    Usage:
        @require_role('admin', 'super_admin')
        def admin_function(self):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'current_user') or not self.current_user:
                raise AuthorizationException("Usuario no autenticado")
            
            user_roles = self.current_user.get('roles', [])
            has_required_role = any(role in user_roles for role in roles)
            
            if not has_required_role:
                roles_str = ', '.join(roles)
                raise AuthorizationException(f"Se requiere uno de los siguientes roles: {roles_str}")
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def require_own_resource_or_permission(resource_user_field: str, recurso: str, accion: str):
    """
    Decorador que permite acceso si el recurso pertenece al usuario 
    o si tiene el permiso específico.
    
    Args:
        resource_user_field: Campo que contiene el ID del usuario propietario
        recurso: Recurso del permiso alternativo
        accion: Acción del permiso alternativo
        
    Usage:
        @require_own_resource_or_permission('usuario_id', 'usuarios', 'administrar')
        def update_profile(self, user_id, data):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'current_user') or not self.current_user:
                raise AuthorizationException("Usuario no autenticado")
            
            current_user_id = self.current_user.get('id')
            
            # Obtener el ID del propietario del recurso
            resource_owner_id = None
            if resource_user_field in kwargs:
                resource_owner_id = kwargs[resource_user_field]
            elif len(args) > 0 and hasattr(args[0], resource_user_field):
                resource_owner_id = getattr(args[0], resource_user_field)
            
            # Si es el propietario, permitir acceso
            if resource_owner_id == current_user_id:
                return func(self, *args, **kwargs)
            
            # Si no es el propietario, verificar permiso
            if hasattr(self, 'permission_service'):
                permission_service = self.permission_service
            else:
                permission_service = PermissionService(self.db, self.current_user)
            
            if permission_service.has_permission(current_user_id, recurso, accion):
                return func(self, *args, **kwargs)
            
            raise AuthorizationException("Sin permisos para acceder a este recurso")
        return wrapper
    return decorator