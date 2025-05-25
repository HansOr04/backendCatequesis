"""
Modelo de Notificación para el sistema de catequesis.
Gestiona las notificaciones del sistema hacia usuarios, catequizandos y padres.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TipoNotificacion(Enum):
    """Tipos de notificación."""
    INSCRIPCION_CONFIRMADA = "inscripcion_confirmada"
    PAGO_RECIBIDO = "pago_recibido"
    PAGO_VENCIDO = "pago_vencido"
    CLASE_CANCELADA = "clase_cancelada"
    CLASE_REPROGRAMADA = "clase_reprogramada"
    EVENTO_PROXIMO = "evento_proximo"
    CERTIFICADO_LISTO = "certificado_listo"
    RECORDATORIO_ASISTENCIA = "recordatorio_asistencia"
    FALTA_DOCUMENTACION = "falta_documentacion"
    PROCESO_CULMINADO = "proceso_culminado"
    COMUNICADO_GENERAL = "comunicado_general"
    ALERTA_SISTEMA = "alerta_sistema"
    OTRO = "otro"


class PrioridadNotificacion(Enum):
    """Prioridades de notificación."""
    BAJA = "baja"
    NORMAL = "normal"
    ALTA = "alta"
    URGENTE = "urgente"


class EstadoNotificacion(Enum):
    """Estados de la notificación."""
    PENDIENTE = "pendiente"
    ENVIANDO = "enviando"
    ENVIADA = "enviada"
    ENTREGADA = "entregada"
    LEIDA = "leida"
    ERROR = "error"
    CANCELADA = "cancelada"


class CanalNotificacion(Enum):
    """Canales de notificación."""
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    SISTEMA = "sistema"
    FISICO = "fisico"


class TipoDestinatario(Enum):
    """Tipos de destinatario."""
    CATEQUIZANDO = "catequizando"
    PADRE_FAMILIA = "padre_familia"
    USUARIO_SISTEMA = "usuario_sistema"
    CATEQUISTA = "catequista"
    COORDINADOR = "coordinador"
    ADMINISTRADOR = "administrador"
    TODOS = "todos"


class Notificacion(BaseModel):
    """
    Modelo de Notificación del sistema de catequesis.
    Gestiona todas las notificaciones del sistema.
    """
    
    # Configuración del modelo
    _table_schema = "notificaciones"
    _primary_key = "id_notificacion"
    _required_fields = ["tipo_notificacion", "titulo", "mensaje"]
    _unique_fields = []
    _searchable_fields = [
        "titulo", "mensaje", "destinatario_nombre", "destinatario_email"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Notificación."""
        # Identificación básica
        self.id_notificacion: Optional[int] = None
        self.codigo_notificacion: Optional[str] = None
        self.tipo_notificacion: TipoNotificacion = TipoNotificacion.COMUNICADO_GENERAL
        self.prioridad: PrioridadNotificacion = PrioridadNotificacion.NORMAL
        self.estado: EstadoNotificacion = EstadoNotificacion.PENDIENTE
        
        # Contenido de la notificación
        self.titulo: str = ""
        self.mensaje: str = ""
        self.mensaje_corto: Optional[str] = None
        self.datos_adicionales: Optional[str] = None  # JSON con datos extra
        
        # Programación
        self.fecha_programada: datetime = datetime.now()
        self.fecha_vencimiento: Optional[datetime] = None
        self.repetir: bool = False
        self.intervalo_repeticion: Optional[int] = None  # minutos
        self.max_repeticiones: int = 1
        self.repeticiones_realizadas: int = 0
        
        # Información del destinatario
        self.tipo_destinatario: TipoDestinatario = TipoDestinatario.CATEQUIZANDO
        self.id_destinatario: Optional[int] = None
        self.destinatario_nombre: Optional[str] = None
        self.destinatario_email: Optional[str] = None
        self.destinatario_telefono: Optional[str] = None
        
        # Referencias del sistema
        self.id_inscripcion: Optional[int] = None
        self.id_catequizando: Optional[int] = None
        self.id_pago: Optional[int] = None
        self.id_evento: Optional[int] = None
        self.id_certificado: Optional[int] = None
        
        # Canal y entrega
        self.canal: CanalNotificacion = CanalNotificacion.EMAIL
        self.canal_alternativo: Optional[CanalNotificacion] = None
        self.usar_canal_alternativo: bool = False
        
        # Control de entrega
        self.fecha_envio: Optional[datetime] = None
        self.fecha_entrega: Optional[datetime] = None
        self.fecha_lectura: Optional[datetime] = None
        self.intentos_envio: int = 0
        self.max_intentos: int = 3
        
        # Respuesta/Confirmación
        self.requiere_confirmacion: bool = False
        self.fecha_confirmacion: Optional[datetime] = None
        self.confirmado_por: Optional[str] = None
        
        # Errores
        self.ultimo_error: Optional[str] = None
        self.historial_errores: Optional[str] = None
        
        # Plantilla
        self.plantilla_usada: Optional[str] = None
        self.variables_plantilla: Optional[str] = None  # JSON
        
        # Control administrativo
        self.creado_por: Optional[str] = None
        self.enviado_por: Optional[str] = None
        self.cancelado_por: Optional[str] = None
        self.motivo_cancelacion: Optional[str] = None
        
        # Observaciones
        self.observaciones: Optional[str] = None
        self.notas_internas: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_programada(self) -> bool:
        """Verifica si la notificación está programada para el futuro."""
        return self.fecha_programada > datetime.now()
    
    @property
    def esta_vencida(self) -> bool:
        """Verifica si la notificación está vencida."""
        if not self.fecha_vencimiento:
            return False
        return datetime.now() > self.fecha_vencimiento
    
    @property
    def puede_enviar(self) -> bool:
        """Verifica si la notificación puede ser enviada."""
        return (
            self.estado == EstadoNotificacion.PENDIENTE and
            not self.esta_vencida and
            self.intentos_envio < self.max_intentos
        )
    
    @property
    def puede_repetir(self) -> bool:
        """Verifica si la notificación puede repetirse."""
        return (
            self.repetir and
            self.repeticiones_realizadas < self.max_repeticiones and
            not self.esta_vencida
        )
    
    @property
    def descripcion_tipo(self) -> str:
        """Obtiene la descripción del tipo de notificación."""
        descripciones = {
            TipoNotificacion.INSCRIPCION_CONFIRMADA: "Inscripción Confirmada",
            TipoNotificacion.PAGO_RECIBIDO: "Pago Recibido",
            TipoNotificacion.PAGO_VENCIDO: "Pago Vencido",
            TipoNotificacion.CLASE_CANCELADA: "Clase Cancelada",
            TipoNotificacion.CLASE_REPROGRAMADA: "Clase Reprogramada",
            TipoNotificacion.EVENTO_PROXIMO: "Evento Próximo",
            TipoNotificacion.CERTIFICADO_LISTO: "Certificado Listo",
            TipoNotificacion.RECORDATORIO_ASISTENCIA: "Recordatorio de Asistencia",
            TipoNotificacion.FALTA_DOCUMENTACION: "Falta Documentación",
            TipoNotificacion.PROCESO_CULMINADO: "Proceso Culminado",
            TipoNotificacion.COMUNICADO_GENERAL: "Comunicado General",
            TipoNotificacion.ALERTA_SISTEMA: "Alerta del Sistema",
            TipoNotificacion.OTRO: "Otro"
        }
        return descripciones.get(self.tipo_notificacion, "Desconocido")
    
    @property
    def descripcion_estado(self) -> str:
        """Obtiene la descripción del estado."""
        descripciones = {
            EstadoNotificacion.PENDIENTE: "Pendiente",
            EstadoNotificacion.ENVIANDO: "Enviando",
            EstadoNotificacion.ENVIADA: "Enviada",
            EstadoNotificacion.ENTREGADA: "Entregada",
            EstadoNotificacion.LEIDA: "Leída",
            EstadoNotificacion.ERROR: "Error",
            EstadoNotificacion.CANCELADA: "Cancelada"
        }
        return descripciones.get(self.estado, "Desconocido")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Notificación."""
        # Validar contenido básico
        if not self.titulo.strip():
            raise ValidationError("El título es requerido")
        
        if not self.mensaje.strip():
            raise ValidationError("El mensaje es requerido")
        
        # Validar fechas
        if self.fecha_vencimiento and self.fecha_vencimiento <= self.fecha_programada:
            raise ValidationError("La fecha de vencimiento debe ser posterior a la programada")
        
        # Validar repetición
        if self.repetir:
            if not self.intervalo_repeticion or self.intervalo_repeticion <= 0:
                raise ValidationError("El intervalo de repetición debe ser mayor a 0")
            
            if self.max_repeticiones <= 0:
                raise ValidationError("El máximo de repeticiones debe ser mayor a 0")
        
        # Validar intentos
        if self.max_intentos <= 0:
            raise ValidationError("El máximo de intentos debe ser mayor a 0")
        
        # Validar enums
        if isinstance(self.tipo_notificacion, str):
            try:
                self.tipo_notificacion = TipoNotificacion(self.tipo_notificacion)
            except ValueError:
                raise ValidationError(f"Tipo de notificación '{self.tipo_notificacion}' no válido")
        
        if isinstance(self.prioridad, str):
            try:
                self.prioridad = PrioridadNotificacion(self.prioridad)
            except ValueError:
                raise ValidationError(f"Prioridad '{self.prioridad}' no válida")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoNotificacion(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.canal, str):
            try:
                self.canal = CanalNotificacion(self.canal)
            except ValueError:
                raise ValidationError(f"Canal '{self.canal}' no válido")
        
        if isinstance(self.tipo_destinatario, str):
            try:
                self.tipo_destinatario = TipoDestinatario(self.tipo_destinatario)
            except ValueError:
                raise ValidationError(f"Tipo de destinatario '{self.tipo_destinatario}' no válido")
        
        # Validar información del destinatario según el canal
        if self.canal == CanalNotificacion.EMAIL and not self.destinatario_email:
            raise ValidationError("El email del destinatario es requerido para notificaciones por email")
        
        if self.canal in [CanalNotificacion.SMS, CanalNotificacion.WHATSAPP] and not self.destinatario_telefono:
            raise ValidationError("El teléfono del destinatario es requerido para SMS/WhatsApp")
    
    def generar_codigo_notificacion(self) -> str:
        """
        Genera un código único para la notificación.
        
        Returns:
            str: Código de notificación generado
        """
        try:
            año = datetime.now().year
            mes = datetime.now().month
            dia = datetime.now().day
            
            # Obtener siguiente número secuencial
            result = self._sp_manager.executor.execute(
                'notificaciones',
                'obtener_siguiente_numero_notificacion',
                {
                    'año': año,
                    'mes': mes,
                    'dia': dia
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            # Prefijo según el tipo
            prefijos = {
                TipoNotificacion.INSCRIPCION_CONFIRMADA: "INS",
                TipoNotificacion.PAGO_RECIBIDO: "PAG",
                TipoNotificacion.PAGO_VENCIDO: "VEN",
                TipoNotificacion.EVENTO_PROXIMO: "EVE",
                TipoNotificacion.CERTIFICADO_LISTO: "CER",
                TipoNotificacion.COMUNICADO_GENERAL: "COM",
                TipoNotificacion.ALERTA_SISTEMA: "ALR"
            }
            
            prefijo = prefijos.get(self.tipo_notificacion, "NOT")
            codigo_notificacion = f"{prefijo}-{año}{mes:02d}{dia:02d}-{numero:04d}"
            self.codigo_notificacion = codigo_notificacion
            
            return codigo_notificacion
            
        except Exception as e:
            logger.error(f"Error generando código de notificación: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"NOT-{timestamp}"
    
    def programar_notificacion(
        self,
        fecha_envio: datetime,
        creado_por: str,
        observaciones: str = None
    ) -> Dict[str, Any]:
        """
        Programa la notificación para envío futuro.
        
        Args:
            fecha_envio: Fecha y hora de envío
            creado_por: Usuario que programa
            observaciones: Observaciones
            
        Returns:
            dict: Resultado de la programación
        """
        try:
            if fecha_envio <= datetime.now():
                raise ValidationError("La fecha de envío debe ser futura")
            
            # Generar código si no existe
            if not self.codigo_notificacion:
                self.generar_codigo_notificacion()
            
            # Actualizar información
            self.fecha_programada = fecha_envio
            self.creado_por = creado_por
            self.estado = EstadoNotificacion.PENDIENTE
            
            if observaciones:
                self.observaciones = observaciones
            
            logger.info(f"Notificación {self.codigo_notificacion} programada para {fecha_envio}")
            
            return {
                'success': True,
                'codigo_notificacion': self.codigo_notificacion,
                'fecha_programada': self.fecha_programada
            }
            
        except Exception as e:
            logger.error(f"Error programando notificación: {str(e)}")
            return {
                'success': False,
                'message': f"Error programando notificación: {str(e)}"
            }
    
    def enviar_notificacion(self, enviado_por: str = None) -> Dict[str, Any]:
        """
        Envía la notificación.
        
        Args:
            enviado_por: Usuario que envía
            
        Returns:
            dict: Resultado del envío
        """
        try:
            if not self.puede_enviar:
                raise ValidationError("La notificación no puede ser enviada en este momento")
            
            # Actualizar estado
            self.estado = EstadoNotificacion.ENVIANDO
            self.fecha_envio = datetime.now()
            self.intentos_envio += 1
            self.enviado_por = enviado_por
            
            # Llamar al servicio de envío según el canal
            resultado_envio = self._enviar_por_canal()
            
            if resultado_envio.get('success'):
                self.estado = EstadoNotificacion.ENVIADA
                if resultado_envio.get('entregada'):
                    self.estado = EstadoNotificacion.ENTREGADA
                    self.fecha_entrega = datetime.now()
                
                logger.info(f"Notificación {self.codigo_notificacion} enviada exitosamente")
                
                # Programar siguiente repetición si aplica
                if self.puede_repetir:
                    self._programar_siguiente_repeticion()
                
                return {
                    'success': True,
                    'estado': self.estado.value,
                    'mensaje': 'Notificación enviada exitosamente'
                }
            else:
                self.estado = EstadoNotificacion.ERROR
                self.ultimo_error = resultado_envio.get('error', 'Error desconocido')
                self._agregar_error_historial(self.ultimo_error)
                
                # Intentar canal alternativo si está configurado
                if self.canal_alternativo and not self.usar_canal_alternativo:
                    return self._intentar_canal_alternativo()
                
                return resultado_envio
                
        except Exception as e:
            self.estado = EstadoNotificacion.ERROR
            self.ultimo_error = str(e)
            self._agregar_error_historial(str(e))
            
            logger.error(f"Error enviando notificación {self.codigo_notificacion}: {str(e)}")
            return {
                'success': False,
                'message': f"Error enviando notificación: {str(e)}"
            }
    
    def _enviar_por_canal(self) -> Dict[str, Any]:
        """
        Envía la notificación por el canal configurado.
        
        Returns:
            dict: Resultado del envío
        """
        try:
            canal_actual = self.canal_alternativo if self.usar_canal_alternativo else self.canal
            
            # Llamar al procedimiento almacenado correspondiente
            result = self._sp_manager.executor.execute(
                'notificaciones',
                f'enviar_por_{canal_actual.value}',
                {
                    'id_notificacion': self.id_notificacion,
                    'destinatario_email': self.destinatario_email,
                    'destinatario_telefono': self.destinatario_telefono,
                    'titulo': self.titulo,
                    'mensaje': self.mensaje,
                    'mensaje_corto': self.mensaje_corto,
                    'datos_adicionales': self.datos_adicionales,
                    'plantilla': self.plantilla_usada,
                    'variables': self.variables_plantilla
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error en envío por canal {self.canal}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _intentar_canal_alternativo(self) -> Dict[str, Any]:
        """Intenta envío por canal alternativo."""
        try:
            self.usar_canal_alternativo = True
            logger.info(f"Intentando envío por canal alternativo: {self.canal_alternativo}")
            return self.enviar_notificacion()
            
        except Exception as e:
            logger.error(f"Error en canal alternativo: {str(e)}")
            return {
                'success': False,
                'message': f"Error en canal alternativo: {str(e)}"
            }
    
    def _programar_siguiente_repeticion(self) -> None:
        """Programa la siguiente repetición."""
        try:
            if self.puede_repetir:
                self.repeticiones_realizadas += 1
                self.fecha_programada = datetime.now() + timedelta(minutes=self.intervalo_repeticion)
                self.estado = EstadoNotificacion.PENDIENTE
                
                logger.info(f"Programada repetición {self.repeticiones_realizadas} de {self.max_repeticiones}")
                
        except Exception as e:
            logger.error(f"Error programando repetición: {str(e)}")
    
    def _agregar_error_historial(self, error: str) -> None:
        """Agrega un error al historial."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevo_error = f"[{timestamp}] {error}"
        
        if self.historial_errores:
            self.historial_errores += f"\n{nuevo_error}"
        else:
            self.historial_errores = nuevo_error
    
    def marcar_leida(self, leido_por: str = None) -> None:
        """
        Marca la notificación como leída.
        
        Args:
            leido_por: Usuario que leyó la notificación
        """
        if self.estado in [EstadoNotificacion.ENVIADA, EstadoNotificacion.ENTREGADA]:
            self.estado = EstadoNotificacion.LEIDA
            self.fecha_lectura = datetime.now()
            
            if leido_por:
                self.confirmado_por = leido_por
            
            logger.info(f"Notificación {self.codigo_notificacion} marcada como leída")
    
    def confirmar_recepcion(self, confirmado_por: str) -> None:
        """
        Confirma la recepción de la notificación.
        
        Args:
            confirmado_por: Usuario que confirma
        """
        if self.requiere_confirmacion and self.estado == EstadoNotificacion.ENTREGADA:
            self.fecha_confirmacion = datetime.now()
            self.confirmado_por = confirmado_por
            
            logger.info(f"Confirmada recepción de notificación {self.codigo_notificacion}")
    
    def cancelar_notificacion(self, motivo: str, cancelado_por: str) -> None:
        """
        Cancela la notificación.
        
        Args:
            motivo: Motivo de la cancelación
            cancelado_por: Usuario que cancela
        """
        if self.estado == EstadoNotificacion.PENDIENTE:
            self.estado = EstadoNotificacion.CANCELADA
            self.motivo_cancelacion = motivo
            self.cancelado_por = cancelado_por
            
            logger.info(f"Notificación {self.codigo_notificacion} cancelada: {motivo}")
        else:
            raise ValidationError("Solo se pueden cancelar notificaciones pendientes")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_notificacion'] = self.tipo_notificacion.value
        data['prioridad'] = self.prioridad.value
        data['estado'] = self.estado.value
        data['canal'] = self.canal.value
        data['tipo_destinatario'] = self.tipo_destinatario.value
        
        if self.canal_alternativo:
            data['canal_alternativo'] = self.canal_alternativo.value
        
        # Agregar propiedades calculadas
        data['descripcion_tipo'] = self.descripcion_tipo
        data['descripcion_estado'] = self.descripcion_estado
        data['esta_programada'] = self.esta_programada
        data['esta_vencida'] = self.esta_vencida
        data['puede_enviar'] = self.puede_enviar
        data['puede_repetir'] = self.puede_repetir
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'destinatario_telefono', 'destinatario_email', 'historial_errores',
                'notas_internas', 'variables_plantilla'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_pendientes_envio(cls) -> List['Notificacion']:
        """Busca notificaciones pendientes de envío."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'notificaciones',
                'obtener_pendientes_envio',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando notificaciones pendientes: {str(e)}")
            return []
    
    @classmethod
    def find_by_destinatario(cls, tipo_destinatario: str, id_destinatario: int) -> List['Notificacion']:
        """Busca notificaciones por destinatario."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'notificaciones',
                'obtener_por_destinatario',
                {
                    'tipo_destinatario': tipo_destinatario,
                    'id_destinatario': id_destinatario
                }
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando notificaciones por destinatario: {str(e)}")
            return []
    
    def save(self, usuario: str = None) -> 'Notificacion':
        """Guarda la notificación con validaciones adicionales."""
        # Generar código si no existe
        if not self.codigo_notificacion:
            self.generar_codigo_notificacion()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('notificacion', Notificacion)