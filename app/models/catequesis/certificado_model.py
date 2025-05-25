"""
Modelo de Certificado para el sistema de catequesis.
Gestiona los certificados emitidos por sacramentos y cursos.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TipoCertificado(Enum):
    """Tipos de certificado."""
    BAUTISMO = "bautismo"
    CONFIRMACION = "confirmacion"
    PRIMERA_COMUNION = "primera_comunion"
    MATRIMONIO = "matrimonio"
    PARTICIPACION = "participacion"
    APROVECHAMIENTO = "aprovechamiento"
    CATEQUISTA = "catequista"


class EstadoCertificado(Enum):
    """Estados del certificado."""
    BORRADOR = "borrador"
    EXPEDIDO = "expedido"
    ENTREGADO = "entregado"
    ANULADO = "anulado"
    REEMPLAZADO = "reemplazado"


class FormatoCertificado(Enum):
    """Formatos del certificado."""
    PDF = "pdf"
    WORD = "word"
    FISICO = "fisico"


class Certificado(BaseModel):
    """
    Modelo de Certificado del sistema de catequesis.
    Gestiona la emisión y control de certificados.
    """
    
    # Configuración del modelo
    _table_schema = "certificados"
    _primary_key = "id_certificado"
    _required_fields = ["tipo_certificado", "beneficiario", "id_parroquia"]
    _unique_fields = ["numero_certificado"]
    _searchable_fields = [
        "numero_certificado", "beneficiario", "concepto", "expedido_por"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Certificado."""
        # Identificación básica
        self.id_certificado: Optional[int] = None
        self.numero_certificado: Optional[str] = None
        self.tipo_certificado: TipoCertificado = TipoCertificado.PARTICIPACION
        self.estado: EstadoCertificado = EstadoCertificado.BORRADOR
        
        # Información del beneficiario
        self.beneficiario: str = ""
        self.documento_beneficiario: Optional[str] = None
        self.id_catequizando: Optional[int] = None
        self.id_sacramento: Optional[int] = None
        
        # Información del certificado
        self.concepto: str = ""
        self.descripcion_detallada: Optional[str] = None
        self.fecha_evento: Optional[date] = None
        self.lugar_evento: Optional[str] = None
        self.duracion_horas: Optional[int] = None
        
        # Información de expedición
        self.id_parroquia: int = 0
        self.expedido_por: Optional[str] = None
        self.cargo_expedidor: Optional[str] = None
        self.fecha_expedicion: Optional[date] = None
        self.fecha_entrega: Optional[date] = None
        self.entregado_a: Optional[str] = None
        
        # Formato y plantilla
        self.formato: FormatoCertificado = FormatoCertificado.PDF
        self.plantilla_utilizada: Optional[str] = None
        self.ruta_archivo: Optional[str] = None
        self.hash_documento: Optional[str] = None
        
        # Validación y firma
        self.requiere_firma: bool = True
        self.firmado: bool = False
        self.fecha_firma: Optional[date] = None
        self.firmado_por: Optional[str] = None
        self.sello_aplicado: bool = False
        
        # Referencias legales
        self.base_legal: Optional[str] = None
        self.numero_resolucion: Optional[str] = None
        self.codigo_verificacion: Optional[str] = None
        self.qr_code: Optional[str] = None
        
        # Control de copias
        self.es_copia: bool = False
        self.numero_copia: int = 1
        self.motivo_copia: Optional[str] = None
        self.autorizacion_copia: Optional[str] = None
        
        # Anulación/Reemplazo
        self.motivo_anulacion: Optional[str] = None
        self.fecha_anulacion: Optional[date] = None
        self.anulado_por: Optional[str] = None
        self.id_certificado_reemplazo: Optional[int] = None
        
        # Observaciones
        self.observaciones: Optional[str] = None
        self.notas_internas: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_vigente(self) -> bool:
        """Verifica si el certificado está vigente."""
        return self.estado in [EstadoCertificado.EXPEDIDO, EstadoCertificado.ENTREGADO]
    
    @property
    def puede_entregar(self) -> bool:
        """Verifica si puede ser entregado."""
        return (self.estado == EstadoCertificado.EXPEDIDO and 
                self.firmado and 
                not self.fecha_entrega)
    
    @property
    def descripcion_tipo(self) -> str:
        """Obtiene la descripción del tipo."""
        descripciones = {
            TipoCertificado.BAUTISMO: "Certificado de Bautismo",
            TipoCertificado.CONFIRMACION: "Certificado de Confirmación",
            TipoCertificado.PRIMERA_COMUNION: "Certificado de Primera Comunión",
            TipoCertificado.MATRIMONIO: "Certificado de Matrimonio",
            TipoCertificado.PARTICIPACION: "Certificado de Participación",
            TipoCertificado.APROVECHAMIENTO: "Certificado de Aprovechamiento",
            TipoCertificado.CATEQUISTA: "Certificado de Catequista"
        }
        return descripciones.get(self.tipo_certificado, "Certificado")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Certificado."""
        # Validar beneficiario
        if self.beneficiario and len(self.beneficiario.strip()) < 3:
            raise ValidationError("El beneficiario debe tener al menos 3 caracteres")
        
        # Validar concepto
        if self.concepto and len(self.concepto.strip()) < 5:
            raise ValidationError("El concepto debe tener al menos 5 caracteres")
        
        # Validar fecha del evento
        if self.fecha_evento and self.fecha_evento > date.today():
            raise ValidationError("La fecha del evento no puede ser futura")
        
        # Validar duración
        if self.duracion_horas is not None and (self.duracion_horas < 1 or self.duracion_horas > 1000):
            raise ValidationError("La duración debe estar entre 1 y 1000 horas")
        
        # Validar parroquia
        if self.id_parroquia <= 0:
            raise ValidationError("Debe especificar una parroquia válida")
        
        # Validar enums
        if isinstance(self.tipo_certificado, str):
            try:
                self.tipo_certificado = TipoCertificado(self.tipo_certificado)
            except ValueError:
                raise ValidationError(f"Tipo de certificado '{self.tipo_certificado}' no válido")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoCertificado(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.formato, str):
            try:
                self.formato = FormatoCertificado(self.formato)
            except ValueError:
                raise ValidationError(f"Formato '{self.formato}' no válido")
        
        # Validar número de copia
        if self.numero_copia < 1 or self.numero_copia > 10:
            raise ValidationError("El número de copia debe estar entre 1 y 10")
        
        # Validar coherencia de estados
        if self.estado == EstadoCertificado.ENTREGADO and not self.fecha_entrega:
            raise ValidationError("Los certificados entregados requieren fecha de entrega")
        
        if self.estado == EstadoCertificado.ANULADO and not self.motivo_anulacion:
            raise ValidationError("Los certificados anulados requieren motivo")
    
    def generar_numero_certificado(self) -> str:
        """
        Genera un número de certificado único.
        
        Returns:
            str: Número de certificado generado
        """
        try:
            año_actual = date.today().year
            
            # Obtener código del tipo
            codigo_tipo = {
                TipoCertificado.BAUTISMO: "BAU",
                TipoCertificado.CONFIRMACION: "CON",
                TipoCertificado.PRIMERA_COMUNION: "PCO",
                TipoCertificado.MATRIMONIO: "MAT",
                TipoCertificado.PARTICIPACION: "PAR",
                TipoCertificado.APROVECHAMIENTO: "APR",
                TipoCertificado.CATEQUISTA: "CAT"
            }
            
            codigo = codigo_tipo.get(self.tipo_certificado, "CER")
            
            # Obtener siguiente número secuencial
            result = self._sp_manager.executor.execute(
                'certificados',
                'obtener_siguiente_numero',
                {
                    'tipo_certificado': self.tipo_certificado.value,
                    'año': año_actual,
                    'id_parroquia': self.id_parroquia
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            numero_certificado = f"{codigo}-{año_actual}-{self.id_parroquia:02d}-{numero:06d}"
            self.numero_certificado = numero_certificado
            
            return numero_certificado
            
        except Exception as e:
            logger.error(f"Error generando número de certificado: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"CER-{timestamp}"
    
    def generar_codigo_verificacion(self) -> str:
        """Genera un código de verificación único."""
        import hashlib
        import secrets
        
        # Crear string para hash
        data_string = f"{self.numero_certificado}{self.beneficiario}{self.fecha_expedicion}"
        salt = secrets.token_hex(8)
        
        # Generar hash
        hash_object = hashlib.sha256((data_string + salt).encode())
        self.codigo_verificacion = hash_object.hexdigest()[:12].upper()
        
        return self.codigo_verificacion
    
    def expedir_certificado(
        self,
        expedido_por: str,
        cargo: str = None,
        plantilla: str = None,
        usuario: str = None
    ) -> Dict[str, Any]:
        """
        Expide el certificado.
        
        Args:
            expedido_por: Quien expide el certificado
            cargo: Cargo de quien expide
            plantilla: Plantilla a utilizar
            usuario: Usuario que realiza la operación
            
        Returns:
            dict: Resultado de la expedición
        """
        try:
            if self.estado != EstadoCertificado.BORRADOR:
                raise ValidationError("Solo se pueden expedir certificados en borrador")
            
            # Generar número si no existe
            if not self.numero_certificado:
                self.generar_numero_certificado()
            
            # Generar código de verificación
            self.generar_codigo_verificacion()
            
            # Actualizar información de expedición
            self.expedido_por = expedido_por
            self.cargo_expedidor = cargo
            self.fecha_expedicion = date.today()
            self.plantilla_utilizada = plantilla
            self.estado = EstadoCertificado.EXPEDIDO
            
            logger.info(f"Certificado {self.numero_certificado} expedido por {expedido_por}")
            
            return {
                'success': True,
                'numero_certificado': self.numero_certificado,
                'codigo_verificacion': self.codigo_verificacion,
                'fecha_expedicion': self.fecha_expedicion
            }
            
        except Exception as e:
            logger.error(f"Error expidiendo certificado: {str(e)}")
            return {
                'success': False,
                'message': f"Error expidiendo certificado: {str(e)}"
            }
    
    def firmar_certificado(self, firmado_por: str) -> None:
        """
        Firma el certificado.
        
        Args:
            firmado_por: Quien firma el certificado
        """
        if self.estado != EstadoCertificado.EXPEDIDO:
            raise ValidationError("Solo se pueden firmar certificados expedidos")
        
        self.firmado = True
        self.fecha_firma = date.today()
        self.firmado_por = firmado_por
        
        logger.info(f"Certificado {self.numero_certificado} firmado por {firmado_por}")
    
    def entregar_certificado(
        self,
        entregado_a: str,
        usuario: str = None
    ) -> None:
        """
        Registra la entrega del certificado.
        
        Args:
            entregado_a: A quien se entrega
            usuario: Usuario que registra la entrega
        """
        if not self.puede_entregar:
            raise ValidationError("El certificado no puede ser entregado en su estado actual")
        
        self.estado = EstadoCertificado.ENTREGADO
        self.fecha_entrega = date.today()
        self.entregado_a = entregado_a
        
        logger.info(f"Certificado {self.numero_certificado} entregado a {entregado_a}")
    
    def anular_certificado(
        self,
        motivo: str,
        anulado_por: str
    ) -> None:
        """
        Anula el certificado.
        
        Args:
            motivo: Motivo de la anulación
            anulado_por: Quien anula
        """
        if self.estado == EstadoCertificado.ANULADO:
            raise ValidationError("El certificado ya está anulado")
        
        self.estado = EstadoCertificado.ANULADO
        self.motivo_anulacion = motivo
        self.fecha_anulacion = date.today()
        self.anulado_por = anulado_por
        
        logger.info(f"Certificado {self.numero_certificado} anulado: {motivo}")
    def crear_copia(
       self,
       motivo: str,
       autorizado_por: str,
       usuario: str = None
   ) -> 'Certificado':
        """
        Crea una copia del certificado.
        
        Args:
            motivo: Motivo de la copia
            autorizado_por: Quien autoriza la copia
            usuario: Usuario que crea la copia
            
        Returns:
            Certificado: Nueva copia del certificado
        """
        if not self.esta_vigente:
            raise ValidationError("Solo se pueden crear copias de certificados vigentes")
        
        # Crear nueva instancia
        copia = Certificado(
            tipo_certificado=self.tipo_certificado,
            beneficiario=self.beneficiario,
            documento_beneficiario=self.documento_beneficiario,
            id_catequizando=self.id_catequizando,
            id_sacramento=self.id_sacramento,
            concepto=self.concepto,
            descripcion_detallada=self.descripcion_detallada,
            fecha_evento=self.fecha_evento,
            lugar_evento=self.lugar_evento,
            duracion_horas=self.duracion_horas,
            id_parroquia=self.id_parroquia,
            expedido_por=self.expedido_por,
            cargo_expedidor=self.cargo_expedidor,
            formato=self.formato,
            base_legal=self.base_legal,
            numero_resolucion=self.numero_resolucion,
            es_copia=True,
            numero_copia=self.numero_copia + 1,
            motivo_copia=motivo,
            autorizacion_copia=autorizado_por
        )
        
        # Generar nuevo número para la copia
        copia.generar_numero_certificado()
        copia.numero_certificado += f"-COPIA{copia.numero_copia}"
        
        # Expedir automáticamente
        copia.expedir_certificado(autorizado_por, "Autoridad Competente", usuario=usuario)
        
        logger.info(f"Copia creada del certificado {self.numero_certificado}")
        
        return copia
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_certificado'] = self.tipo_certificado.value
        data['estado'] = self.estado.value
        data['formato'] = self.formato.value
        
        # Agregar propiedades calculadas
        data['descripcion_tipo'] = self.descripcion_tipo
        data['esta_vigente'] = self.esta_vigente
        data['puede_entregar'] = self.puede_entregar
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'hash_documento', 'codigo_verificacion', 'ruta_archivo'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_numero(cls, numero_certificado: str) -> Optional['Certificado']:
        """Busca un certificado por número."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'certificados',
                'obtener_por_numero',
                {'numero_certificado': numero_certificado}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando certificado por número {numero_certificado}: {str(e)}")
            return None
    
    @classmethod
    def find_by_beneficiario(cls, beneficiario: str) -> List['Certificado']:
        """Busca certificados de un beneficiario."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'certificados',
                'obtener_por_beneficiario',
                {'beneficiario': beneficiario}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando certificados por beneficiario: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Certificado':
        """Guarda el certificado con validaciones adicionales."""
        # Generar número si no existe y está siendo expedido
        if not self.numero_certificado and self.estado == EstadoCertificado.EXPEDIDO:
            self.generar_numero_certificado()
        
        return super().save(usuario)


    # Registrar el modelo en la factory
    ModelFactory.register('certificado', Certificado)