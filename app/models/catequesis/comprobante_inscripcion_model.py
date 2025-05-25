"""
Modelo de Comprobante de Inscripción para el sistema de catequesis.
Gestiona los comprobantes generados para las inscripciones y pagos.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TipoComprobante(Enum):
    """Tipos de comprobante."""
    RECIBO_PAGO = "recibo_pago"
    COMPROBANTE_INSCRIPCION = "comprobante_inscripcion"
    FACTURA = "factura"
    CERTIFICADO_PAGO = "certificado_pago"
    CONSTANCIA = "constancia"
    OTRO = "otro"


class EstadoComprobante(Enum):
    """Estados del comprobante."""
    BORRADOR = "borrador"
    GENERADO = "generado"
    ENVIADO = "enviado"
    ENTREGADO = "entregado"
    ANULADO = "anulado"


class FormatoComprobante(Enum):
    """Formatos de comprobante."""
    PDF = "pdf"
    HTML = "html"
    FISICO = "fisico"


class ComprobanteInscripcion(BaseModel):
    """
    Modelo de Comprobante de Inscripción del sistema de catequesis.
    Gestiona los comprobantes generados para inscripciones y pagos.
    """
    
    # Configuración del modelo
    _table_schema = "comprobantes_inscripcion"
    _primary_key = "id_comprobante"
    _required_fields = ["id_inscripcion", "tipo_comprobante"]
    _unique_fields = ["numero_comprobante"]
    _searchable_fields = [
        "numero_comprobante", "nombre_completo", "documento_identidad"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Comprobante de Inscripción."""
        # Identificación básica
        self.id_comprobante: Optional[int] = None
        self.numero_comprobante: Optional[str] = None
        self.id_inscripcion: int = 0
        self.id_catequizando: Optional[int] = None
        self.id_pago: Optional[int] = None
        
        # Información del comprobante
        self.tipo_comprobante: TipoComprobante = TipoComprobante.RECIBO_PAGO
        self.estado: EstadoComprobante = EstadoComprobante.BORRADOR
        self.formato: FormatoComprobante = FormatoComprobante.PDF
        
        # Fechas importantes
        self.fecha_emision: date = date.today()
        self.fecha_vencimiento: Optional[date] = None
        self.fecha_entrega: Optional[date] = None
        
        # Información del destinatario
        self.nombre_completo: Optional[str] = None
        self.documento_identidad: Optional[str] = None
        self.telefono: Optional[str] = None
        self.email: Optional[str] = None
        self.direccion: Optional[str] = None
        
        # Información del curso/programa
        self.programa_catequesis: Optional[str] = None
        self.nivel_catequesis: Optional[str] = None
        self.año_catequesis: int = datetime.now().year
        self.periodo: Optional[str] = None
        
        # Información financiera
        self.monto_inscripcion: float = 0.0
        self.monto_materiales: float = 0.0
        self.monto_certificado: float = 0.0
        self.descuentos: float = 0.0
        self.recargos: float = 0.0
        self.monto_total: float = 0.0
        
        # Detalles del pago
        self.forma_pago: Optional[str] = None
        self.referencia_pago: Optional[str] = None
        self.fecha_pago: Optional[date] = None
        self.estado_pago: Optional[str] = None
        
        # Control documental
        self.template_usado: Optional[str] = None
        self.ruta_archivo: Optional[str] = None
        self.nombre_archivo: Optional[str] = None
        self.tamaño_archivo: Optional[int] = None
        self.hash_archivo: Optional[str] = None
        
        # Control de entrega
        self.entregado_por: Optional[str] = None
        self.recibido_por: Optional[str] = None
        self.medio_entrega: Optional[str] = None  # email, presencial, correo
        self.acuse_recibo: bool = False
        
        # Anulación
        self.fecha_anulacion: Optional[date] = None
        self.motivo_anulacion: Optional[str] = None
        self.anulado_por: Optional[str] = None
        
        # Observaciones
        self.observaciones: Optional[str] = None
        self.notas_internas: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_generado(self) -> bool:
        """Verifica si el comprobante está generado."""
        return self.estado in [EstadoComprobante.GENERADO, EstadoComprobante.ENVIADO, EstadoComprobante.ENTREGADO]
    
    @property
    def esta_entregado(self) -> bool:
        """Verifica si el comprobante ha sido entregado."""
        return self.estado == EstadoComprobante.ENTREGADO
    
    @property
    def puede_anular(self) -> bool:
        """Verifica si el comprobante puede ser anulado."""
        return self.estado != EstadoComprobante.ANULADO and not self.fecha_anulacion
    
    @property
    def descripcion_tipo(self) -> str:
        """Obtiene la descripción del tipo de comprobante."""
        descripciones = {
            TipoComprobante.RECIBO_PAGO: "Recibo de Pago",
            TipoComprobante.COMPROBANTE_INSCRIPCION: "Comprobante de Inscripción",
            TipoComprobante.FACTURA: "Factura",
            TipoComprobante.CERTIFICADO_PAGO: "Certificado de Pago",
            TipoComprobante.CONSTANCIA: "Constancia",
            TipoComprobante.OTRO: "Otro"
        }
        return descripciones.get(self.tipo_comprobante, "Desconocido")
    
    @property
    def descripcion_estado(self) -> str:
        """Obtiene la descripción del estado del comprobante."""
        descripciones = {
            EstadoComprobante.BORRADOR: "Borrador",
            EstadoComprobante.GENERADO: "Generado",
            EstadoComprobante.ENVIADO: "Enviado",
            EstadoComprobante.ENTREGADO: "Entregado",
            EstadoComprobante.ANULADO: "Anulado"
        }
        return descripciones.get(self.estado, "Desconocido")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Comprobante de Inscripción."""
        # Validar ID de inscripción
        if self.id_inscripcion <= 0:
            raise ValidationError("Debe especificar una inscripción válida")
        
        # Validar montos
        if self.monto_total < 0:
            raise ValidationError("El monto total no puede ser negativo")
        
        if self.descuentos < 0:
            raise ValidationError("Los descuentos no pueden ser negativos")
        
        if self.recargos < 0:
            raise ValidationError("Los recargos no pueden ser negativos")
        
        # Validar fechas
        if self.fecha_vencimiento and self.fecha_vencimiento < self.fecha_emision:
            raise ValidationError("La fecha de vencimiento no puede ser anterior a la emisión")
        
        if self.fecha_entrega and self.fecha_entrega < self.fecha_emision:
            raise ValidationError("La fecha de entrega no puede ser anterior a la emisión")
        
        # Validar enums
        if isinstance(self.tipo_comprobante, str):
            try:
                self.tipo_comprobante = TipoComprobante(self.tipo_comprobante)
            except ValueError:
                raise ValidationError(f"Tipo de comprobante '{self.tipo_comprobante}' no válido")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoComprobante(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.formato, str):
            try:
                self.formato = FormatoComprobante(self.formato)
            except ValueError:
                raise ValidationError(f"Formato '{self.formato}' no válido")
        
        # Validar información del destinatario para comprobantes generados
        if self.estado != EstadoComprobante.BORRADOR:
            if not self.nombre_completo:
                raise ValidationError("El nombre completo es requerido para generar el comprobante")
    
    def generar_numero_comprobante(self) -> str:
        """
        Genera un número de comprobante único.
        
        Returns:
            str: Número de comprobante generado
        """
        try:
            año = self.fecha_emision.year
            mes = self.fecha_emision.month
            
            # Obtener siguiente número secuencial
            result = self._sp_manager.executor.execute(
                'comprobantes_inscripcion',
                'obtener_siguiente_numero_comprobante',
                {
                    'año': año,
                    'mes': mes,
                    'tipo_comprobante': self.tipo_comprobante.value
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            # Prefijo según el tipo de comprobante
            prefijos = {
                TipoComprobante.RECIBO_PAGO: "REC",
                TipoComprobante.COMPROBANTE_INSCRIPCION: "INS",
                TipoComprobante.FACTURA: "FAC",
                TipoComprobante.CERTIFICADO_PAGO: "CER",
                TipoComprobante.CONSTANCIA: "CON",
                TipoComprobante.OTRO: "OTR"
            }
            
            prefijo = prefijos.get(self.tipo_comprobante, "COM")
            numero_comprobante = f"{prefijo}-{año}{mes:02d}-{numero:06d}"
            self.numero_comprobante = numero_comprobante
            
            return numero_comprobante
            
        except Exception as e:
            logger.error(f"Error generando número de comprobante: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            prefijo = self.tipo_comprobante.value.upper()[:3]
            return f"{prefijo}-{timestamp}"
    
    def calcular_monto_total(self) -> None:
        """Calcula el monto total del comprobante."""
        subtotal = self.monto_inscripcion + self.monto_materiales + self.monto_certificado
        self.monto_total = subtotal - self.descuentos + self.recargos
    
    def generar_comprobante(
        self,
        generado_por: str,
        template: str = None,
        observaciones: str = None
    ) -> Dict[str, Any]:
        """
        Genera el comprobante.
        
        Args:
            generado_por: Usuario que genera el comprobante
            template: Template a utilizar
            observaciones: Observaciones del comprobante
            
        Returns:
            dict: Resultado de la generación
        """
        try:
            if self.estado != EstadoComprobante.BORRADOR:
                raise ValidationError("Solo se pueden generar comprobantes en borrador")
            
            # Generar número de comprobante si no existe
            if not self.numero_comprobante:
                self.generar_numero_comprobante()
            
            # Calcular monto total
            self.calcular_monto_total()
            
            # Actualizar información del comprobante
            self.estado = EstadoComprobante.GENERADO
            self.template_usado = template or "default"
            
            if observaciones:
                self.observaciones = observaciones
            
            # Generar archivo del comprobante
            resultado_generacion = self._generar_archivo_comprobante()
            
            logger.info(f"Comprobante {self.numero_comprobante} generado por {generado_por}")
            
            return {
                'success': True,
                'numero_comprobante': self.numero_comprobante,
                'ruta_archivo': self.ruta_archivo,
                **resultado_generacion
            }
            
        except Exception as e:
            logger.error(f"Error generando comprobante: {str(e)}")
            return {
                'success': False,
                'message': f"Error generando comprobante: {str(e)}"
            }
    
    def _generar_archivo_comprobante(self) -> Dict[str, Any]:
        """
        Genera el archivo físico del comprobante.
        
        Returns:
            dict: Información del archivo generado
        """
        try:
            # Llamar al procedimiento almacenado para generar el archivo
            result = self._sp_manager.executor.execute(
                'comprobantes_inscripcion',
                'generar_archivo_comprobante',
                {
                    'id_comprobante': self.id_comprobante,
                    'template': self.template_usado,
                    'formato': self.formato.value
                }
            )
            
            if result.get('success') and result.get('data'):
                archivo_info = result['data']
                self.ruta_archivo = archivo_info.get('ruta_archivo')
                self.nombre_archivo = archivo_info.get('nombre_archivo')
                self.tamaño_archivo = archivo_info.get('tamaño_archivo')
                self.hash_archivo = archivo_info.get('hash_archivo')
                
                return {
                    'archivo_generado': True,
                    'ruta_archivo': self.ruta_archivo,
                    'nombre_archivo': self.nombre_archivo
                }
            else:
                return {
                    'archivo_generado': False,
                    'message': 'No se pudo generar el archivo'
                }
                
        except Exception as e:
            logger.error(f"Error generando archivo de comprobante: {str(e)}")
            return {
                'archivo_generado': False,
                'message': f"Error: {str(e)}"
            }
    
    def enviar_comprobante(
        self,
        enviado_por: str,
        email_destino: str = None,
        mensaje: str = None
    ) -> Dict[str, Any]:
        """
        Envía el comprobante por email.
        
        Args:
            enviado_por: Usuario que envía
            email_destino: Email de destino (opcional, usa el del destinatario)
            mensaje: Mensaje adicional
            
        Returns:
            dict: Resultado del envío
        """
        try:
            if self.estado != EstadoComprobante.GENERADO:
                raise ValidationError("Solo se pueden enviar comprobantes generados")
            
            email_destino = email_destino or self.email
            if not email_destino:
                raise ValidationError("No se ha especificado email de destino")
            
            # Llamar al servicio de envío de emails
            result = self._sp_manager.executor.execute(
                'comprobantes_inscripcion',
                'enviar_comprobante_email',
                {
                    'id_comprobante': self.id_comprobante,
                    'email_destino': email_destino,
                    'mensaje': mensaje,
                    'enviado_por': enviado_por
                }
            )
            
            if result.get('success'):
                self.estado = EstadoComprobante.ENVIADO
                self.medio_entrega = "email"
                
                logger.info(f"Comprobante {self.numero_comprobante} enviado a {email_destino}")
                
                return {
                    'success': True,
                    'message': f"Comprobante enviado exitosamente a {email_destino}"
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Error enviando comprobante')
                }
                
        except Exception as e:
            logger.error(f"Error enviando comprobante: {str(e)}")
            return {
                'success': False,
                'message': f"Error enviando comprobante: {str(e)}"
            }
    
    def marcar_entregado(
        self,
        entregado_por: str,
        recibido_por: str = None,
        medio_entrega: str = "presencial",
        observaciones: str = None
    ) -> None:
        """
        Marca el comprobante como entregado.
        
        Args:
            entregado_por: Usuario que entrega
            recibido_por: Persona que recibe
            medio_entrega: Medio de entrega
            observaciones: Observaciones de la entrega
        """
        if self.estado not in [EstadoComprobante.GENERADO, EstadoComprobante.ENVIADO]:
            raise ValidationError("Solo se pueden marcar como entregados comprobantes generados o enviados")
        
        self.estado = EstadoComprobante.ENTREGADO
        self.fecha_entrega = date.today()
        self.entregado_por = entregado_por
        self.recibido_por = recibido_por or self.nombre_completo
        self.medio_entrega = medio_entrega
        self.acuse_recibo = True
        
        if observaciones:
            self.observaciones = f"{self.observaciones or ''}\nEntrega: {observaciones}".strip()
        
        logger.info(f"Comprobante {self.numero_comprobante} marcado como entregado")
    
    def anular_comprobante(
        self,
        motivo: str,
        anulado_por: str
    ) -> None:
        """
        Anula el comprobante.
        
        Args:
            motivo: Motivo de la anulación
            anulado_por: Usuario que anula
        """
        if not self.puede_anular:
            raise ValidationError("El comprobante no puede ser anulado")
        
        self.estado = EstadoComprobante.ANULADO
        self.fecha_anulacion = date.today()
        self.motivo_anulacion = motivo
        self.anulado_por = anulado_por
        
        logger.info(f"Comprobante {self.numero_comprobante} anulado: {motivo}")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_comprobante'] = self.tipo_comprobante.value
        data['estado'] = self.estado.value
        data['formato'] = self.formato.value
        
        # Agregar propiedades calculadas
        data['descripcion_tipo'] = self.descripcion_tipo
        data['descripcion_estado'] = self.descripcion_estado
        data['esta_generado'] = self.esta_generado
        data['esta_entregado'] = self.esta_entregado
        data['puede_anular'] = self.puede_anular
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'hash_archivo', 'ruta_archivo', 'notas_internas'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_inscripcion(cls, id_inscripcion: int) -> List['ComprobanteInscripcion']:
        """Busca comprobantes de una inscripción."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'comprobantes_inscripcion',
                'obtener_por_inscripcion',
                {'id_inscripcion': id_inscripcion}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando comprobantes por inscripción: {str(e)}")
            return []
    
    @classmethod
    def find_by_numero_comprobante(cls, numero_comprobante: str) -> Optional['ComprobanteInscripcion']:
        """Busca un comprobante por número."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'comprobantes_inscripcion',
                'obtener_por_numero_comprobante',
                {'numero_comprobante': numero_comprobante}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando comprobante por número: {str(e)}")
            return None
    
    @classmethod
    def find_pendientes_entrega(cls, dias_limite: int = 30) -> List['ComprobanteInscripcion']:
        """Busca comprobantes pendientes de entrega."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'comprobantes_inscripcion',
                'obtener_pendientes_entrega',
                {'dias_limite': dias_limite}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando comprobantes pendientes: {str(e)}")
            return []
    
    def save(self, usuario: str = None) -> 'ComprobanteInscripcion':
        """Guarda el comprobante con validaciones adicionales."""
        # Generar número de comprobante si no existe y no es borrador
        if not self.numero_comprobante and self.estado != EstadoComprobante.BORRADOR:
            self.generar_numero_comprobante()
        
        # Calcular monto total antes de guardar
        self.calcular_monto_total()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('comprobante_inscripcion', ComprobanteInscripcion)