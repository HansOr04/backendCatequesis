"""
Servicio de gestión de usuarios para el sistema de catequesis.
Maneja CRUD de usuarios, perfiles, roles y configuraciones.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text
from passlib.context import CryptContext
import secrets

from app.services.base_service import BaseService
from app.models.seguridad.usuario_model import Usuario
from app.models.seguridad.rol_model import Rol
from app.models.seguridad.usuario_rol_model import UsuarioRol
from app.models.seguridad.sesion_model import Sesion
from app.schemas.seguridad.usuario_schema import (
    UsuarioCreateSchema, UsuarioUpdateSchema, UsuarioResponseSchema,
    UsuarioSearchSchema, CambioPasswordSchema, PerfilUsuarioSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException,
    DuplicateException
)
from app.utils.email import send_email
from app.utils.image_processor import process_avatar_image
from app.utils.password_validator import validate_password_strength
import logging

logger = logging.getLogger(__name__)


class UsuarioService(BaseService):
    """Servicio para gestión completa de usuarios."""
    
    @property
    def model(self) -> Type[Usuario]:
        return Usuario
    
    @property
    def create_schema(self) -> Type[UsuarioCreateSchema]:
        return UsuarioCreateSchema
    
    @property
    def update_schema(self) -> Type[UsuarioUpdateSchema]:
        return UsuarioUpdateSchema
    
    @property
    def response_schema(self) -> Type[UsuarioResponseSchema]:
        return UsuarioResponseSchema
    
    @property
    def search_schema(self) -> Type[UsuarioSearchSchema]:
        return UsuarioSearchSchema
    
    def __init__(self, db: Session = None, current_user: Dict = None):
        super().__init__(db, current_user)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # ==========================================
    # OPERACIONES CRUD EXTENDIDAS
    # ==========================================
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Usuario.roles),
            joinedload(Usuario.parroquia),
            joinedload(Usuario.created_by_user),
            joinedload(Usuario.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para usuarios."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Usuario.nombres.ilike(search_term),
                    Usuario.apellidos.ilike(search_term),
                    Usuario.email.ilike(search_term),
                    Usuario.username.ilike(search_term),
                    Usuario.telefono.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('activo') is not None:
            query = query.filter(Usuario.activo == search_data['activo'])
        
        if search_data.get('email_verificado') is not None:
            query = query.filter(Usuario.email_verificado == search_data['email_verificado'])
        
        if search_data.get('requiere_cambio_password') is not None:
            query = query.filter(Usuario.requiere_cambio_password == search_data['requiere_cambio_password'])
        
        if search_data.get('parroquia_id'):
            query = query.filter(Usuario.parroquia_id == search_data['parroquia_id'])
        
        if search_data.get('roles_incluir'):
            query = query.join(UsuarioRol).join(Rol).filter(
                Rol.nombre.in_(search_data['roles_incluir'])
            )
        
        # Filtros de fecha
        if search_data.get('creado_desde'):
            query = query.filter(Usuario.created_at >= search_data['creado_desde'])
        
        if search_data.get('creado_hasta'):
            query = query.filter(Usuario.created_at <= search_data['creado_hasta'])
        
        if search_data.get('ultimo_login_desde'):
            query = query.filter(Usuario.ultimo_login >= search_data['ultimo_login_desde'])
        
        if search_data.get('ultimo_login_hasta'):
            query = query.filter(Usuario.ultimo_login <= search_data['ultimo_login_hasta'])
        
        # Filtros por estado de sesión
        if search_data.get('con_sesion_activa'):
            query = query.join(Sesion).filter(
                and_(
                    Sesion.activa == True,
                    Sesion.ultima_actividad >= datetime.utcnow() - timedelta(minutes=30)
                )
            )
        
        return query
    
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar email único
        if self.exists(email=data['email']):
            raise DuplicateException("El email ya está registrado")
        
        # Verificar username único (si se proporciona)
        if data.get('username') and self.exists(username=data['username']):
            raise DuplicateException("El nombre de usuario ya está en uso")
        
        # Validar fortaleza de contraseña si se proporciona
        if data.get('password'):
            if not validate_password_strength(data['password']):
                raise ValidationException("La contraseña no cumple con los requisitos de seguridad")
            
            # Generar hash de contraseña
            data['password_hash'] = self._hash_password(data['password'])
            del data['password']  # Remover contraseña en texto plano
        
        # Generar username si no se proporciona
        if not data.get('username'):
            data['username'] = self._generate_username(data['nombres'], data['apellidos'])
        
        # Configuraciones por defecto
        data.setdefault('activo', True)
        data.setdefault('email_verificado', False)
        data.setdefault('requiere_cambio_password', True)
        data.setdefault('requiere_2fa', False)
        
        return data
    
    def _after_create(self, instance, data: Dict[str, Any], **kwargs):
        """Hook post-creación para asignaciones adicionales."""
        # Asignar roles por defecto si se especificaron
        roles_nombres = kwargs.get('roles', ['usuario'])
        self._assign_roles_to_user(instance, roles_nombres)
        
        # Enviar email de bienvenida si está configurado
        if kwargs.get('send_welcome_email', True):
            self._send_welcome_email(instance)
        
        return instance
    
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-actualización para validaciones."""
        # Verificar email único (si cambió)
        if 'email' in data and data['email'] != instance.email:
            if self.exists(email=data['email']):
                raise DuplicateException("El email ya está registrado")
        
        # Verificar username único (si cambió)
        if 'username' in data and data['username'] != instance.username:
            if self.exists(username=data['username']):
                raise DuplicateException("El nombre de usuario ya está en uso")
        
        # Manejar cambio de contraseña
        if data.get('password'):
            if not validate_password_strength(data['password']):
                raise ValidationException("La contraseña no cumple con los requisitos")
            
            data['password_hash'] = self._hash_password(data['password'])
            data['requiere_cambio_password'] = False
            del data['password']
        
        return data
    
    def _after_update(self, instance, data: Dict[str, Any], **kwargs):
        """Hook post-actualización."""
        # Si se desactivó el usuario, cerrar todas sus sesiones
        if 'activo' in data and not data['activo']:
            self._close_all_user_sessions(instance.id, 'user_deactivated')
        
        # Si se cambió email, marcar como no verificado
        if 'email' in data and data['email'] != instance.email:
            instance.email_verificado = False
            self._send_email_verification(instance)
        
        return instance
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar el usuario."""
        # No permitir eliminar el propio usuario
        if self.current_user and instance.id == self.current_user.get('id'):
            raise BusinessLogicException("No puede eliminar su propio usuario")
        
        # No permitir eliminar super administradores
        if any(role.nombre == 'super_admin' for role in instance.roles):
            raise BusinessLogicException("No se puede eliminar un super administrador")
        
        # Verificar dependencias
        dependencies = self._check_user_dependencies(instance.id)
        if dependencies:
            raise BusinessLogicException(f"No se puede eliminar. Tiene dependencias: {', '.join(dependencies)}")
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE USUARIOS
    # ==========================================
    
    def change_password(self, user_id: int, password_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cambia la contraseña de un usuario.
        
        Args:
            user_id: ID del usuario
            password_data: Datos con contraseña actual y nueva
            
        Returns:
            Dict con confirmación del cambio
        """
        try:
            schema = CambioPasswordSchema()
            validated_data = schema.load(password_data)
            
            # Obtener usuario
            user = self._get_instance_by_id(user_id)
            
            # Verificar contraseña actual
            if not self._verify_password(validated_data['current_password'], user.password_hash):
                raise ValidationException("Contraseña actual incorrecta")
            
            # Validar nueva contraseña
            if not validate_password_strength(validated_data['new_password']):
                raise ValidationException("La nueva contraseña no cumple con los requisitos")
            
            # Verificar que no sea la misma contraseña
            if self._verify_password(validated_data['new_password'], user.password_hash):
                raise ValidationException("La nueva contraseña debe ser diferente a la actual")
            
            # Actualizar contraseña
            user.password_hash = self._hash_password(validated_data['new_password'])
            user.requiere_cambio_password = False
            user.fecha_cambio_password = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            # Cerrar otras sesiones si se solicita
            if validated_data.get('logout_other_sessions', True):
                self._close_other_user_sessions(user_id)
            
            self.db.commit()
            
            # Log de seguridad
            logger.info(f"Contraseña cambiada para usuario {user.email}")
            
            return {
                'success': True,
                'message': 'Contraseña cambiada exitosamente'
            }
            
        except ValidationException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando contraseña: {str(e)}")
            raise BusinessLogicException("Error cambiando contraseña")
    
    def update_profile(self, user_id: int, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza el perfil de un usuario.
        
        Args:
            user_id: ID del usuario
            profile_data: Datos del perfil a actualizar
            
        Returns:
            Dict con el perfil actualizado
        """
        try:
            schema = PerfilUsuarioSchema()
            validated_data = schema.load(profile_data)
            
            # Obtener usuario
            user = self._get_instance_by_id(user_id)
            
            # Procesar avatar si se proporciona
            if validated_data.get('avatar_file'):
                avatar_url = self._process_avatar(validated_data['avatar_file'], user_id)
                validated_data['avatar_url'] = avatar_url
                del validated_data['avatar_file']
            
            # Actualizar campos del perfil
            for key, value in validated_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            
            return self._serialize_response(user)
            
        except ValidationException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error actualizando perfil: {str(e)}")
            raise BusinessLogicException("Error actualizando perfil")
    
    def assign_roles(self, user_id: int, roles_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asigna roles a un usuario.
        
        Args:
            user_id: ID del usuario
            roles_data: Datos con roles a asignar
            
        Returns:
            Dict con roles asignados
        """
        try:
            user = self._get_instance_by_id(user_id)
            roles_nombres = roles_data.get('roles', [])
            
            # Verificar permisos para asignar roles
            self._validate_role_assignment_permissions(roles_nombres)
            
            # Limpiar roles actuales
            self.db.query(UsuarioRol).filter(UsuarioRol.usuario_id == user_id).delete()
            
            # Asignar nuevos roles
            self._assign_roles_to_user(user, roles_nombres)
            
            self.db.commit()
            
            # Invalidar sesiones para que los nuevos roles tomen efecto
            self._invalidate_user_tokens(user_id)
            
            logger.info(f"Roles asignados a usuario {user.email}: {roles_nombres}")
            
            return {
                'success': True,
                'roles': roles_nombres,
                'message': 'Roles asignados exitosamente'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error asignando roles: {str(e)}")
            raise BusinessLogicException("Error asignando roles")
    
    def toggle_activation(self, user_id: int) -> Dict[str, Any]:
        """
        Activa o desactiva un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con el nuevo estado
        """
        try:
            user = self._get_instance_by_id(user_id)
            
            # Validaciones
            if user.id == self.current_user.get('id'):
                raise BusinessLogicException("No puede cambiar su propio estado")
            
            if any(role.nombre == 'super_admin' for role in user.roles):
                raise BusinessLogicException("No se puede desactivar un super administrador")
            
            # Cambiar estado
            new_state = not user.activo
            user.activo = new_state
            user.updated_at = datetime.utcnow()
            
            # Si se desactiva, cerrar sesiones
            if not new_state:
                self._close_all_user_sessions(user_id, 'user_deactivated')
            
            self.db.commit()
            
            action = "activado" if new_state else "desactivado"
            logger.info(f"Usuario {user.email} {action}")
            
            return {
                'success': True,
                'activo': new_state,
                'message': f'Usuario {action} exitosamente'
            }
            
        except BusinessLogicException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando estado de usuario: {str(e)}")
            raise BusinessLogicException("Error cambiando estado del usuario")
    
    def reset_user_password(self, user_id: int, reset_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Restablece la contraseña de un usuario (solo admin).
        
        Args:
            user_id: ID del usuario
            reset_data: Datos opcionales con nueva contraseña
            
        Returns:
            Dict con información del restablecimiento
        """
        try:
            user = self._get_instance_by_id(user_id)
            
            # Generar nueva contraseña o usar la proporcionada
            if reset_data and reset_data.get('new_password'):
                new_password = reset_data['new_password']
                if not validate_password_strength(new_password):
                    raise ValidationException("La contraseña no cumple con los requisitos")
            else:
                new_password = self._generate_secure_password()
            
            # Actualizar contraseña
            user.password_hash = self._hash_password(new_password)
            user.requiere_cambio_password = True
            user.fecha_cambio_password = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            # Cerrar todas las sesiones del usuario
            self._close_all_user_sessions(user_id, 'password_reset_by_admin')
            
            self.db.commit()
            
            # Enviar email con nueva contraseña
            send_password_only = reset_data.get('send_email', True) if reset_data else True
            if send_password_only:
                self._send_password_reset_notification(user, new_password if not reset_data.get('new_password') else None)
            
            logger.info(f"Contraseña restablecida para usuario {user.email} por admin")
            
            result = {
                'success': True,
                'message': 'Contraseña restablecida exitosamente',
                'requires_password_change': True
            }
            
            # Solo incluir la contraseña en la respuesta si fue generada automáticamente
            if not reset_data or not reset_data.get('new_password'):
                result['temporary_password'] = new_password
            
            return result
            
        except ValidationException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error restableciendo contraseña: {str(e)}")
            raise BusinessLogicException("Error restableciendo contraseña")
    
    def get_user_activity(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene la actividad reciente de un usuario.
        
        Args:
            user_id: ID del usuario
            days: Días hacia atrás para obtener actividad
            
        Returns:
            Dict con información de actividad
        """
        try:
            user = self._get_instance_by_id(user_id)
            fecha_limite = datetime.utcnow() - timedelta(days=days)
            
            # Sesiones recientes
            sesiones = self.db.query(Sesion).filter(
                and_(
                    Sesion.usuario_id == user_id,
                    Sesion.fecha_inicio >= fecha_limite
                )
            ).order_by(Sesion.fecha_inicio.desc()).limit(10).all()
            
            # Estadísticas de actividad
            stats = {
                'total_sessions': len(sesiones),
                'active_sessions': sum(1 for s in sesiones if s.activa),
                'unique_ips': len(set(s.ip_address for s in sesiones)),
                'devices_used': len(set(s.dispositivo for s in sesiones)),
                'last_login': user.ultimo_login.isoformat() if user.ultimo_login else None,
                'days_since_last_login': (datetime.utcnow() - user.ultimo_login).days if user.ultimo_login else None
            }
            
            # Detalles de sesiones
            sessions_detail = [
                {
                    'id': str(session.id),
                    'start_time': session.fecha_inicio.isoformat(),
                    'last_activity': session.ultima_actividad.isoformat(),
                    'ip_address': session.ip_address,
                    'device': session.dispositivo,
                    'browser': session.navegador,
                    'location': session.ubicacion,
                    'active': session.activa,
                    'duration_minutes': int((
                        (session.fecha_cierre or session.ultima_actividad) - session.fecha_inicio
                    ).total_seconds() / 60)
                }
                for session in sesiones
            ]
            
            return {
                'user_id': user_id,
                'period_days': days,
                'statistics': stats,
                'recent_sessions': sessions_detail
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo actividad de usuario: {str(e)}")
            raise BusinessLogicException("Error obteniendo actividad del usuario")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de usuarios."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de usuarios
            total_users = self.db.query(Usuario).count()
            active_users = self.db.query(Usuario).filter(Usuario.activo == True).count()
            verified_emails = self.db.query(Usuario).filter(Usuario.email_verificado == True).count()
            
            # Usuarios con sesiones activas (últimos 30 minutos)
            active_sessions = self.db.query(Usuario).join(Sesion).filter(
                and_(
                    Sesion.activa == True,
                    Sesion.ultima_actividad >= datetime.utcnow() - timedelta(minutes=30)
                )
            ).distinct().count()
            
            # Distribución por roles
            roles_distribution = self.db.query(
                Rol.nombre, func.count(UsuarioRol.usuario_id)
            ).join(UsuarioRol).join(Usuario).filter(
                Usuario.activo == True
            ).group_by(Rol.nombre).all()
            
            base_stats.update({
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': total_users - active_users,
                'verified_emails': verified_emails,
                'unverified_emails': total_users - verified_emails,
                'users_online': active_sessions,
                'verification_rate': round((verified_emails / total_users) * 100, 1) if total_users > 0 else 0,
                'activation_rate': round((active_users / total_users) * 100, 1) if total_users > 0 else 0,
                'roles_distribution': {role: count for role, count in roles_distribution}
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de usuarios: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _hash_password(self, password: str) -> str:
        """Genera hash de contraseña."""
        return self.pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica contraseña contra hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def _generate_username(self, nombres: str, apellidos: str) -> str:
        """Genera username único basado en nombres y apellidos."""
        base_username = f"{nombres.split()[0].lower()}.{apellidos.split()[0].lower()}"
        username = base_username
        counter = 1
        
        while self.exists(username=username):
            username = f"{base_username}{counter}"
            counter += 1
        
        return username
    
    def _generate_secure_password(self, length: int = 12) -> str:
        """Genera una contraseña segura aleatoria."""
        import string
        import random
        
        chars = string.ascii_letters + string.digits + "!@#$%&*"
        password = ''.join(random.choice(chars) for _ in range(length))
        
        # Asegurar que tenga al menos una mayúscula, minúscula, número y símbolo
        if not any(c.isupper() for c in password):
            password = password[:-1] + random.choice(string.ascii_uppercase)
        if not any(c.islower() for c in password):
            password = password[:-1] + random.choice(string.ascii_lowercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + random.choice(string.digits)
        if not any(c in "!@#$%&*" for c in password):
            password = password[:-1] + random.choice("!@#$%&*")
        
        return password
    
    def _assign_roles_to_user(self, user: Usuario, roles_nombres: List[str]):
        """Asigna roles específicos a un usuario."""
        for role_name in roles_nombres:
            role = self.db.query(Rol).filter(Rol.nombre == role_name).first()
            if role:
                usuario_rol = UsuarioRol(
                    usuario_id=user.id,
                    rol_id=role.id,
                    asignado_por=self.current_user.get('id') if self.current_user else None,
                    fecha_asignacion=datetime.utcnow()
                )
                self.db.add(usuario_rol)
    
    def _close_all_user_sessions(self, user_id: int, reason: str):
        """Cierra todas las sesiones activas de un usuario."""
        self.db.query(Sesion).filter(
            and_(
                Sesion.usuario_id == user_id,
                Sesion.activa == True
            )
        ).update({
            'activa': False,
            'fecha_cierre': datetime.utcnow(),
            'razon_cierre': reason
        })
    
    def _close_other_user_sessions(self, user_id: int):
        """Cierra otras sesiones del usuario (excepto la actual)."""
        current_session_id = self.current_user.get('session_id') if self.current_user else None
        
        query = self.db.query(Sesion).filter(
            and_(
                Sesion.usuario_id == user_id,
                Sesion.activa == True
            )
        )
        
        if current_session_id:
            query = query.filter(Sesion.id != current_session_id)
        
        query.update({
            'activa': False,
            'fecha_cierre': datetime.utcnow(),
            'razon_cierre': 'password_changed'
        })
    
    def _invalidate_user_tokens(self, user_id: int):
        """Invalida los tokens de un usuario forzando nuevo login."""
        self._close_all_user_sessions(user_id, 'roles_changed')
    
    def _validate_role_assignment_permissions(self, roles_nombres: List[str]):
        """Valida que el usuario actual pueda asignar los roles especificados."""
        # Implementar lógica de validación de permisos según roles del usuario actual
        current_user_roles = self.current_user.get('roles', []) if self.current_user else []
        
        # Super admin puede asignar cualquier rol
        if 'super_admin' in current_user_roles:
            return
        
        # Admin puede asignar roles básicos
        if 'admin' in current_user_roles:
            restricted_roles = ['super_admin']
            if any(role in restricted_roles for role in roles_nombres):
                raise BusinessLogicException("No tiene permisos para asignar ese rol")
            return
        
        # Otros usuarios no pueden asignar roles
        raise BusinessLogicException("No tiene permisos para asignar roles")
    
    def _check_user_dependencies(self, user_id: int) -> List[str]:
        """Verifica dependencias del usuario antes de eliminar."""
        dependencies = []
        
        # Verificar si tiene catequizandos asignados
        # dependencies.append('catequizandos') si tiene
        
        # Verificar si es catequista de algún grupo
        # dependencies.append('grupos_catequesis') si tiene
        
        # Verificar si ha creado registros importantes
        # dependencies.append('registros_creados') si tiene
        
        return dependencies
    
    def _process_avatar(self, avatar_file, user_id: int) -> str:
        """Procesa y guarda el avatar del usuario."""
        # Implementar procesamiento de imagen
        # Redimensionar, optimizar, guardar
        return process_avatar_image(avatar_file, user_id)
    
    def _send_welcome_email(self, user: Usuario):
        """Envía email de bienvenida al usuario."""
        try:
            # Implementar envío de email de bienvenida
            pass
        except Exception as e:
            logger.warning(f"No se pudo enviar email de bienvenida a {user.email}: {str(e)}")
    
    def _send_email_verification(self, user: Usuario):
        """Envía email de verificación."""
        try:
            # Implementar envío de email de verificación
            pass
        except Exception as e:
            logger.warning(f"No se pudo enviar email de verificación a {user.email}: {str(e)}")
    
    def _send_password_reset_notification(self, user: Usuario, temp_password: str = None):
        """Envía notificación de restablecimiento de contraseña."""
        try:
            # Implementar envío de notificación
            pass
        except Exception as e:
            logger.warning(f"No se pudo enviar notificación a {user.email}: {str(e)}")