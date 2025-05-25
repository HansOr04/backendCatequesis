"""
Servicio de gestión de notificaciones del sistema.
Maneja envío de notificaciones por múltiples canales.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.notificacion_model import Notificacion
from app.models.catequesis.catequizando_model import Catequizando
from app.schemas.catequesis.notificacion_schema import (
    NotificacionCreateSchema, NotificacionUpdateSchema, NotificacionResponseSchema,
    NotificacionSearchSchema, NotificacionMasivaSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
from app.utils.email_sender import send_email
from app.utils.sms_sender import send_sms
from app.utils.whatsapp_sender import send_whatsapp
import logging

logger = logging.getLogger(__name__)


class NotificacionService(BaseService):
    """Servicio para gestión de notificaciones."""
    
    @property
    def model(self) -> Type[Notificacion]:
        return Notificacion
    
    @property
    def create_schema(self) -> Type[NotificacionCreateSchema]:
        return NotificacionCreateSchema
    
    @property
    def update_schema(self) -> Type[NotificacionUpdateSchema]:
        return NotificacionUpdateSchema
    
    @property
    def response_schema(self) -> Type[NotificacionResponseSchema]:
        return NotificacionResponseSchema
    
    @property
    def search_schema(self) -> Type[NotificacionSearchSchema]:
        return NotificacionSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Notificacion.catequizando),
            joinedload(Notificacion.catequista),
            joinedload(Notificacion.created_by_user)
        )
    
    @require_permission('notificaciones', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Validar que al menos un canal esté habilitado
        canales = [
            data.get('enviar_email', False),
            data.get('enviar_sms', False),
            data.get('enviar_whatsapp', False),
            data.get('mostrar_sistema', False)
        ]
        
        if not any(canales):
            raise ValidationException("Debe seleccionar al menos un canal de notificación")
        
        # Validar información de contacto según canales
        if data.get('enviar_email') and not data.get('destinatario_email'):
            raise ValidationException("Email requerido para envío por correo")
        
        if (data.get('enviar_sms') or data.get('enviar_whatsapp')) and not data.get('destinatario_telefono'):
            raise ValidationException("Teléfono requerido para SMS/WhatsApp")
        
        # Generar número de notificación
        if not data.get('numero_notificacion'):
            data['numero_notificacion'] = self._generate_notification_number()
        
        # Configuraciones por defecto
        data.setdefault('fecha_creacion', datetime.utcnow())
        data.setdefault('estado', 'borrador')
        data.setdefault('prioridad', 'normal')
        
        return data
    
    @require_permission('notificaciones', 'enviar')
    def enviar_notificacion(self, notificacion_id: int) -> Dict[str, Any]:
        """
        Envía una notificación por los canales configurados.
        
        Args:
            notificacion_id: ID de la notificación
            
        Returns:
            Dict con resultados del envío
        """
        try:
            notificacion = self._get_instance_by_id(notificacion_id)
            
            if notificacion.estado != 'borrador':
                raise ValidationException("Solo se pueden enviar notificaciones en estado borrador")
            
            resultados = {}
            errores = []
            
            # Enviar por email
            if notificacion.enviar_email and notificacion.destinatario_email:
                try:
                    email_result = send_email(
                        to=notificacion.destinatario_email,
                        subject=notificacion.titulo,
                        body=notificacion.mensaje,
                        html=True
                    )
                    resultados['email'] = 'enviado'
                    notificacion.fecha_envio_email = datetime.utcnow()
                    notificacion.estado_email = 'enviado'
                except Exception as e:
                    errores.append(f"Error en email: {str(e)}")
                    notificacion.estado_email = 'error'
            
            # Enviar por SMS
            if notificacion.enviar_sms and notificacion.destinatario_telefono:
                try:
                    sms_result = send_sms(
                        to=notificacion.destinatario_telefono,
                        message=notificacion.mensaje_corto or notificacion.mensaje[:160]
                    )
                    resultados['sms'] = 'enviado'
                    notificacion.fecha_envio_sms = datetime.utcnow()
                    notificacion.estado_sms = 'enviado'
                except Exception as e:
                    errores.append(f"Error en SMS: {str(e)}")
                    notificacion.estado_sms = 'error'
            
            # Enviar por WhatsApp
            if notificacion.enviar_whatsapp and notificacion.destinatario_telefono:
                try:
                    whatsapp_result = send_whatsapp(
                        to=notificacion.destinatario_telefono,
                        message=notificacion.mensaje
                    )
                    resultados['whatsapp'] = 'enviado'
                    notificacion.fecha_envio_whatsapp = datetime.utcnow()
                    notificacion.estado_whatsapp = 'enviado'
                except Exception as e:
                    errores.append(f"Error en WhatsApp: {str(e)}")
                    notificacion.estado_whatsapp = 'error'
            
            # Mostrar en sistema
            if notificacion.mostrar_sistema:
                notificacion.estado_sistema = 'visible'
            
            # Actualizar estado general
            if resultados and not errores:
                notificacion.estado = 'enviada'
            elif resultados and errores:
                notificacion.estado = 'parcial'
            else:
                notificacion.estado = 'fallida'
            
            notificacion.fecha_envio = datetime.utcnow()
            notificacion.enviado_por = self.current_user.get('id') if self.current_user else None
            notificacion.intentos_envio = (notificacion.intentos_envio or 0) + 1
            notificacion.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Notificación {notificacion_id} enviada. Resultados: {resultados}")
            
            return {
                'success': len(resultados) > 0,
                'notificacion_id': notificacion_id,
                'canales_enviados': list(resultados.keys()),
                'errores': errores,
                'estado_final': notificacion.estado,
                'mensaje': f'Notificación enviada por {len(resultados)} canal(es)'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error enviando notificación: {str(e)}")
            raise BusinessLogicException("Error enviando notificación")
    
    @require_permission('notificaciones', 'enviar')
    def enviar_notificacion_masiva(self, masiva_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía notificaciones masivas a múltiples destinatarios.
        
        Args:
            masiva_data: Datos para envío masivo
            
        Returns:
            Dict con resultados del envío masivo
        """
        try:
            schema = NotificacionMasivaSchema()
            validated_data = schema.load(masiva_data)
            
            # Obtener destinatarios según criterios
            destinatarios = self._get_destinatarios_masivos(validated_data)
            
            if not destinatarios:
                raise ValidationException("No se encontraron destinatarios válidos")
            
            notificaciones_creadas = 0
            errores = []
            
            for destinatario in destinatarios:
                try:
                    # Crear notificación individual
                    notif_data = {
                        'tipo_notificacion': validated_data['tipo_notificacion'],
                        'titulo': validated_data['titulo'],
                        'mensaje': validated_data['mensaje'],
                        'destinatario_nombre': destinatario['nombre'],
                        'destinatario_email': destinatario.get('email'),
                        'destinatario_telefono': destinatario.get('telefono'),
                        'enviar_email': validated_data.get('enviar_email', False),
                        'enviar_sms': validated_data.get('enviar_sms', False),
                        'mostrar_sistema': validated_data.get('mostrar_sistema', False),
                        'prioridad': validated_data.get('prioridad', 'normal'),
                        'catequizando_id': destinatario.get('catequizando_id'),
                        'catequista_id': destinatario.get('catequista_id')
                    }
                    
                    notificacion = self.create(notif_data)
                    
                    # Enviar inmediatamente si se solicita
                    if validated_data.get('enviar_inmediatamente', True):
                        self.enviar_notificacion(notificacion['id'])
                    
                    notificaciones_creadas += 1
                    
                except Exception as e:
                    errores.append(f"Error con {destinatario['nombre']}: {str(e)}")
            
            logger.info(f"Notificación masiva enviada a {notificaciones_creadas} destinatarios")
            
            return {
                'success': True,
                'notificaciones_creadas': notificaciones_creadas,
                'total_destinatarios': len(destinatarios),
                'errores': errores,
                'mensaje': f'Notificación masiva enviada a {notificaciones_creadas} destinatarios'
            }
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error en envío masivo: {str(e)}")
            raise BusinessLogicException("Error en envío masivo de notificaciones")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas de notificaciones."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Distribución por estado
            estado_distribution = self.db.query(
                Notificacion.estado, func.count(Notificacion.id)
            ).group_by(Notificacion.estado).all()
            
            # Distribución por tipo
            tipo_distribution = self.db.query(
                Notificacion.tipo_notificacion, func.count(Notificacion.id)
            ).group_by(Notificacion.tipo_notificacion).all()
            
            # Distribución por canal
            canal_stats = {
                'email': self.db.query(Notificacion).filter(Notificacion.enviar_email == True).count(),
                'sms': self.db.query(Notificacion).filter(Notificacion.enviar_sms == True).count(),
                'whatsapp': self.db.query(Notificacion).filter(Notificacion.enviar_whatsapp == True).count(),
                'sistema': self.db.query(Notificacion).filter(Notificacion.mostrar_sistema == True).count()
           }
            
            # Tasa de entrega por canal
            tasa_entrega = {}
            for canal in ['email', 'sms', 'whatsapp']:
                enviadas = self.db.query(Notificacion).filter(
                    getattr(Notificacion, f'estado_{canal}') == 'enviado'
                ).count()
                
                total = self.db.query(Notificacion).filter(
                    getattr(Notificacion, f'enviar_{canal}') == True
                ).count()
                
                tasa_entrega[canal] = round((enviadas / total * 100), 1) if total > 0 else 0
            
            base_stats.update({
                'distribucion_estados': {estado: count for estado, count in estado_distribution},
                'distribucion_tipos': {tipo: count for tipo, count in tipo_distribution},
                'distribucion_canales': canal_stats,
                'tasa_entrega_por_canal': tasa_entrega
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _generate_notification_number(self) -> str:
        """Genera número único de notificación."""
        today = date.today()
        prefix = f"NOT{today.strftime('%Y%m%d')}"
        
        # Obtener el último número del día
        last_notification = self.db.query(Notificacion).filter(
            Notificacion.numero_notificacion.like(f"{prefix}%")
        ).order_by(Notificacion.numero_notificacion.desc()).first()
        
        if last_notification:
            last_number = int(last_notification.numero_notificacion[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:04d}"
    
    def _get_destinatarios_masivos(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtiene destinatarios para envío masivo según criterios."""
        destinatarios = []
        
        # Catequizandos específicos
        if criteria.get('catequizandos_ids'):
            catequizandos = self.db.query(Catequizando).filter(
                and_(
                    Catequizando.id.in_(criteria['catequizandos_ids']),
                    Catequizando.activo == True
                )
            ).all()
            
            for cat in catequizandos:
                destinatarios.append({
                    'catequizando_id': cat.id,
                    'nombre': f"{cat.nombres} {cat.apellidos}",
                    'email': cat.email,
                    'telefono': cat.telefono
                })
        
        # Filtros automáticos
        if criteria.get('filtro_programa') or criteria.get('filtro_nivel'):
            from app.models.catequesis.inscripcion_model import Inscripcion
            from app.models.catequesis.nivel_model import Nivel
            from app.models.catequesis.programa_catequesis_model import ProgramaCatequesis
            
            query = self.db.query(Catequizando).join(Inscripcion).join(Nivel)
            
            if criteria.get('filtro_programa'):
                query = query.join(ProgramaCatequesis).filter(
                    ProgramaCatequesis.nombre.ilike(f"%{criteria['filtro_programa']}%")
                )
            
            if criteria.get('filtro_nivel'):
                query = query.filter(
                    Nivel.nombre.ilike(f"%{criteria['filtro_nivel']}%")
                )
            
            if criteria.get('solo_activos', True):
                query = query.filter(
                    and_(
                        Catequizando.activo == True,
                        Inscripcion.estado.in_(['activa', 'en_progreso'])
                    )
                )
            
            catequizandos = query.distinct().all()
            
            for cat in catequizandos:
                if not any(d['catequizando_id'] == cat.id for d in destinatarios):
                    destinatarios.append({
                        'catequizando_id': cat.id,
                        'nombre': f"{cat.nombres} {cat.apellidos}",
                        'email': cat.email,
                        'telefono': cat.telefono
                    })
        
        return destinatarios