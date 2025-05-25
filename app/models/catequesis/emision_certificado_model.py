"""
Modelo de Emisión de Certificado para el sistema de catequesis.
Gestiona la emisión, validación y entrega de certificados de catequesis.
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
    PRIMERA_COMUNION = "primera_comunion"
    CONFIRMACION = "confirmacion"
    BAUTISMO = "bautismo"
    MATRIMONIO = "matrimonio"
    CATEQUESIS_COMPLETA = "catequesis_completa"
    ASISTENCIA = "asistencia"
    PARTICIPACION = "participacion"
    APROVECHAMIENTO = "aprovechamiento"
    OTRO = "otro"


class EstadoCertificado(Enum):
    """Estados del certificado."""
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    GENERADO = "generado"
    FIRMADO = "firmado"
    ENTREGADO = "entregado"
    ANULADO = "anulado"


class FormatoCertificado(Enum):
    """Formatos de certificado."""
    PDF = "pdf"
    FISICO = "fisico"
    DIGITAL_FIRMADO = "digital_firmado"


class NivelValidacion(Enum):
    """Niveles de validación del certificado."""
    BASICA = "basica"
    INTERMEDIA = "intermedia"
    COMPLETA = "completa"
    OFICIAL = "oficial"


class EmisionCertificado(BaseModel):
    """
    Modelo de Emisión de Certificado del sistema de catequesis.
    Gestiona todo el proceso de emisión de certificados.
    """
    
    # Configuración del modelo
    _table_schema = "emision_certificados"
    _primary_key = "id_emision"
    _required_fields = ["id_catequizando", "tipo_certificado"]
    _unique_fields = ["numero_certificado"]
    _searchable_fields = [
        "numero_certificado", "nombre_completo", "documento_identidad"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Emisión de Certificado."""
        # Identificación básica
        self.id_emision: Optional[int] = None
        self.numero_certificado: Optional[str] = None
        self.codigo_verificacion: Optional[str] = None
        self.id_catequizando: int = 0
        self.id_inscripcion: Optional[int] = None
        
        # Información del certificado
        self.tipo_certificado: TipoCertificado = TipoCertificado.CATEQUESIS_COMPLETA
        self.estado: EstadoCertificado = EstadoCertificado.PENDIENTE
        self.formato: FormatoCertificado = FormatoCertificado.PDF
        self.nivel_validacion: NivelValidacion = NivelValidacion.BASICA
        
        # Fechas importantes
        self.fecha_solicitud: date = date.today()
        self.fecha_emision: Optional[date] = None
        self.fecha_firma: Optional[date] = None
        self.fecha_entrega: Optional[date] = None
        self.fecha_vencimiento: Optional[date] = None
        
        # Información del certificado
        self.titulo_certificado: Optional[str] = None
        self.descripcion: Optional[str] = None
        self.motivo_emision: Optional[str] = None
        
        # Información del catequizando
        self.nombre_completo: Optional[str] = None
        self.documento_identidad: Optional[str] = None
        self.fecha_nacimiento: Optional[date] = None
        self.lugar_nacimiento: Optional[str] = None
        self.nombre_padre: Optional[str] = None
        self.nombre_madre: Optional[str] = None
        self.padrinos: Optional[str] = None
        
        # Información de la catequesis
        self.programa_catequesis: Optional[str] = None
        self.nivel_catequesis: Optional[str] = None
        self.año_catequesis: int = datetime.now().year
        self.periodo: Optional[str] = None
        self.parroquia: Optional[str] = None
        self.diocesis: Optional[str] = None
        
        # Fechas sacramentales
        self.fecha_sacramento: Optional[date] = None
        self.lugar_sacramento: Optional[str] = None
        self.celebrante: Optional[str] = None
        self.testigos: Optional[str] = None
        
        # Calificaciones y logros
        self.calificacion_final: Optional[float] = None
        self.porcentaje_asistencia: Optional[float] = None
        self.observaciones_academicas: Optional[str] = None
        self.logros_especiales: Optional[str] = None
        
        # Control de calidad
        self.revisado_por: Optional[str] = None
        self.fecha_revision: Optional[date] = None
        self.aprobado_por: Optional[str] = None
        self.fecha_aprobacion: Optional[date] = None
        
        # Firma y autorización
        self.firmado_por: Optional[str] = None
        self.cargo_firmante: Optional[str] = None
        self.numero_registro_firmante: Optional[str] = None
        self.sello_oficial: bool = False
        
        # Control documental
        self.template_usado: Optional[str] = None
        self.ruta_archivo: Optional[str] = None
        self.nombre_archivo: Optional[str] = None
        self.tamaño_archivo: Optional[int] = None
        self.hash_documento: Optional[str] = None
        
        # Entrega
        self.entregado_por: Optional[str] = None
        self.recibido_por: Optional[str] = None
        self.parentesco_receptor: Optional[str] = None
        self.documento_receptor: Optional[str] = None
        self.medio_entrega: Optional[str] = None
        
        # Validación y verificación
        self.es_duplicado: bool = False
        self.certificado_original: Optional[int] = None
        self.motivo_duplicado: Optional[str] = None
        self.verificaciones_realizadas: int = 0
        self.ultima_verificacion: Optional[datetime] = None
        
        # Anulación
        self.fecha_anulacion: Optional[date] = None
        self.motivo_anulacion: Optional[str] = None
        self.anulado_por: Optional[str] = None
        self.certificado_reemplazo: Optional[int] = None
        
        # Costos y pagos
        self.costo_emision: float = 0.0
        self.pagado: bool = False
        self.id_pago: Optional[int] = None
        self.fecha_pago: Optional[date] = None
        
        # Observaciones
        self.observaciones: Optional[str] = None
        self.notas_internas: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_emitido(self) -> bool:
        """Verifica si el certificado está emitido."""
        return self.estado in [EstadoCertificado.GENERADO, EstadoCertificado.FIRMADO, EstadoCertificado.ENTREGADO]
    
    @property
    def esta_firmado(self) -> bool:
        """Verifica si el certificado está firmado."""
        return self.estado in [EstadoCertificado.FIRMADO, EstadoCertificado.ENTREGADO]
    
    @property
    def esta_entregado(self) -> bool:
        """Verifica si el certificado ha sido entregado."""
        return self.estado == EstadoCertificado.ENTREGADO
    
    @property
    def puede_emitir(self) -> bool:
        """Verifica si el certificado puede ser emitido."""
        return self.estado == EstadoCertificado.PENDIENTE and self.pagado
    
    @property
    def puede_firmar(self) -> bool:
        """Verifica si el certificado puede ser firmado."""
        return self.estado == EstadoCertificado.GENERADO
    
    @property
    def puede_anular(self) -> bool:
        """Verifica si el certificado puede ser anulado."""
        return self.estado != EstadoCertificado.ANULADO and not self.fecha_anulacion
    
    @property
    def descripcion_tipo(self) -> str:
        """Obtiene la descripción del tipo de certificado."""
        descripciones = {
            TipoCertificado.PRIMERA_COMUNION: "Primera Comunión",
            TipoCertificado.CONFIRMACION: "Confirmación",
            TipoCertificado.BAUTISMO: "Bautismo",
            TipoCertificado.MATRIMONIO: "Matrimonio",
            TipoCertificado.CATEQUESIS_COMPLETA: "Catequesis Completa",
            TipoCertificado.ASISTENCIA: "Certificado de Asistencia",
            TipoCertificado.PARTICIPACION: "Certificado de Participación",
            TipoCertificado.APROVECHAMIENTO: "Certificado de Aprovechamiento",
            TipoCertificado.OTRO: "Otro"
        }
        return descripciones.get(self.tipo_certificado, "Desconocido")
    
    @property
    def descripcion_estado(self) -> str:
        """Obtiene la descripción del estado del certificado."""
        descripciones = {
            EstadoCertificado.PENDIENTE: "Pendiente",
            EstadoCertificado.EN_PROCESO: "En Proceso",
            EstadoCertificado.GENERADO: "Generado",
            EstadoCertificado.FIRMADO: "Firmado",
            EstadoCertificado.ENTREGADO: "Entregado",
            EstadoCertificado.ANULADO: "Anulado"
        }
        return descripciones.get(self.estado, "Desconocido")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Emisión de Certificado."""
        # Validar ID de catequizando
        if self.id_catequizando <= 0:
            raise ValidationError("Debe especificar un catequizando válido")
        
        # Validar fechas
        if self.fecha_emision and self.fecha_emision < self.fecha_solicitud:
            raise ValidationError("La fecha de emisión no puede ser anterior a la solicitud")
        
        if self.fecha_firma and self.fecha_emision and self.fecha_firma < self.fecha_emision:
            raise ValidationError("La fecha de firma no puede ser anterior a la emisión")
        
        if self.fecha_entrega and self.fecha_firma and self.fecha_entrega < self.fecha_firma:
            raise ValidationError("La fecha de entrega no puede ser anterior a la firma")
        
        if self.fecha_vencimiento and self.fecha_emision and self.fecha_vencimiento <= self.fecha_emision:
            raise ValidationError("La fecha de vencimiento debe ser posterior a la emisión")
        
        # Validar calificaciones
        if self.calificacion_final is not None:
            if not (0 <= self.calificacion_final <= 100):
                raise ValidationError("La calificación final debe estar entre 0 y 100")
        
        if self.porcentaje_asistencia is not None:
            if not (0 <= self.porcentaje_asistencia <= 100):
                raise ValidationError("El porcentaje de asistencia debe estar entre 0 y 100")
        
        # Validar costos
        if self.costo_emision < 0:
            raise ValidationError("El costo de emisión no puede ser negativo")
        
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
        
        if isinstance(self.nivel_validacion, str):
            try:
                self.nivel_validacion = NivelValidacion(self.nivel_validacion)
            except ValueError:
                raise ValidationError(f"Nivel de validación '{self.nivel_validacion}' no válido")
        
        # Validar información requerida para emisión
        if self.estado != EstadoCertificado.PENDIENTE:
            if not self.nombre_completo:
                raise ValidationError("El nombre completo es requerido para emitir el certificado")
    
    def generar_numero_certificado(self) -> str:
        """
        Genera un número de certificado único.
        
        Returns:
            str: Número de certificado generado
        """
        try:
            año = self.fecha_solicitud.year
            
            # Obtener siguiente número secuencial
            result = self._sp_manager.executor.execute(
                'emision_certificados',
                'obtener_siguiente_numero_certificado',
                {
                    'año': año,
                    'tipo_certificado': self.tipo_certificado.value
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            # Prefijo según el tipo de certificado
            prefijos = {
                TipoCertificado.PRIMERA_COMUNION: "PC",
                TipoCertificado.CONFIRMACION: "CF",
                TipoCertificado.BAUTISMO: "BA",
                TipoCertificado.MATRIMONIO: "MA",
                TipoCertificado.CATEQUESIS_COMPLETA: "CC",
                TipoCertificado.ASISTENCIA: "AS",
                TipoCertificado.PARTICIPACION: "PA",
                TipoCertificado.APROVECHAMIENTO: "AP",
                TipoCertificado.OTRO: "OT"
            }
            
            prefijo = prefijos.get(self.tipo_certificado, "CE")
            numero_certificado = f"{prefijo}-{año}-{numero:06d}"
            self.numero_certificado = numero_certificado
            
            return numero_certificado
            
        except Exception as e:
            logger.error(f"Error generando número de certificado: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            prefijo = self.tipo_certificado.value.upper()[:2]
            return f"{prefijo}-{timestamp}"
    
    def generar_codigo_verificacion(self) -> str:
        """
        Genera un código de verificación único.
        
        Returns:
            str: Código de verificación generado
        """
        try:
            import hashlib
            import secrets
            
            # Crear string único para el hash
            datos_unicos = f"{self.numero_certificado}{self.id_catequizando}{self.fecha_solicitud}{secrets.token_hex(8)}"
            
            # Generar hash
            hash_obj = hashlib.sha256(datos_unicos.encode())
            codigo_completo = hash_obj.hexdigest()
            
            # Tomar los primeros 12 caracteres y formatear
            codigo_verificacion = f"{codigo_completo[:4]}-{codigo_completo[4:8]}-{codigo_completo[8:12]}".upper()
            self.codigo_verificacion = codigo_verificacion
            
            return codigo_verificacion
            
        except Exception as e:
            logger.error(f"Error generando código de verificación: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            return f"{timestamp[:4]}-{timestamp[4:8]}-{timestamp[8:12]}"
    
    def solicitar_emision(
        self,
        solicitado_por: str,
        motivo: str = None,
        observaciones: str = None
    ) -> Dict[str, Any]:
        """
        Solicita la emisión del certificado.
        
        Args:
            solicitado_por: Usuario que solicita
            motivo: Motivo de la solicitud
            observaciones: Observaciones
            
        Returns:
            dict: Resultado de la solicitud
        """
        try:
            # Validar que se pueda solicitar
            if self.estado != EstadoCertificado.PENDIENTE:
                raise ValidationError("Solo se pueden procesar solicitudes pendientes")
            
            # Generar número de certificado si no existe
            if not self.numero_certificado:
                self.generar_numero_certificado()
            
            # Generar código de verificación
            self.generar_codigo_verificacion()
            
            # Actualizar información
            self.estado = EstadoCertificado.EN_PROCESO
            self.motivo_emision = motivo
            
            if observaciones:
                self.observaciones = observaciones
            
            logger.info(f"Solicitud de emisión de certificado {self.numero_certificado} por {solicitado_por}")
            
            return {
                'success': True,
                'numero_certificado': self.numero_certificado,
                'codigo_verificacion': self.codigo_verificacion
            }
            
        except Exception as e:
            logger.error(f"Error procesando solicitud de emisión: {str(e)}")
            return {
                'success': False,
                'message': f"Error procesando solicitud: {str(e)}"
            }
    
    def emitir_certificado(
        self,
        emitido_por: str,
        template: str = None,
        observaciones: str = None
    ) -> Dict[str, Any]:
        """
        Emite el certificado.
        
        Args:
            emitido_por: Usuario que emite
            template: Template a utilizar
            observaciones: Observaciones
            
        Returns:
            dict: Resultado de la emisión
        """
        try:
            if not self.puede_emitir:
                raise ValidationError("El certificado no puede ser emitido en este momento")
            
            # Actualizar información
            self.estado = EstadoCertificado.GENERADO
            self.fecha_emision = date.today()
            self.template_usado = template or "default"
            
            if observaciones:
                self.observaciones = observaciones
            
            # Generar archivo del certificado
            resultado_generacion = self._generar_archivo_certificado()
            
            logger.info(f"Certificado {self.numero_certificado} emitido por {emitido_por}")
            
            return {
                'success': True,
                'numero_certificado': self.numero_certificado,
                'ruta_archivo': self.ruta_archivo,
                **resultado_generacion
            }
            
        except Exception as e:
            logger.error(f"Error emitiendo certificado: {str(e)}")
            return {
                'success': False,
                'message': f"Error emitiendo certificado: {str(e)}"
            }
    
    def _generar_archivo_certificado(self) -> Dict[str, Any]:
        """
        Genera el archivo físico del certificado.
        
        Returns:
            dict: Información del archivo generado
        """
        try:
            # Llamar al procedimiento almacenado para generar el archivo
            result = self._sp_manager.executor.execute(
                'emision_certificados',
                'generar_archivo_certificado',
                {
                    'id_emision': self.id_emision,
                    'template': self.template_usado,
                    'formato': self.formato.value
                }
            )
            
            if result.get('success') and result.get('data'):
                archivo_info = result['data']
                self.ruta_archivo = archivo_info.get('ruta_archivo')
                self.nombre_archivo = archivo_info.get('nombre_archivo')
                self.tamaño_archivo = archivo_info.get('tamaño_archivo')
                self.hash_documento = archivo_info.get('hash_documento')
                
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
            logger.error(f"Error generando archivo de certificado: {str(e)}")
            return {
                'archivo_generado': False,
                'message': f"Error: {str(e)}"
            }
    
    def firmar_certificado(
        self,
        firmado_por: str,
        cargo_firmante: str,
        numero_registro: str = None,
        observaciones: str = None
    ) -> Dict[str, Any]:
        """
        Firma el certificado.
        
        Args:
            firmado_por: Usuario que firma
            cargo_firmante: Cargo del firmante
            numero_registro: Número de registro del firmante
            observaciones: Observaciones
            
        Returns:
            dict: Resultado de la firma
        """
        try:
            if not self.puede_firmar:
                raise ValidationError("El certificado no puede ser firmado en este momento")
            
            # Actualizar información de firma
            self.estado = EstadoCertificado.FIRMADO
            self.fecha_firma = date.today()
            self.firmado_por = firmado_por
            self.cargo_firmante = cargo_firmante
            self.numero_registro_firmante = numero_registro
            self.sello_oficial = True
            
            if observaciones:
                self.observaciones = f"{self.observaciones or ''}\nFirma: {observaciones}".strip()
            
            # Aplicar firma digital si corresponde
            if self.formato == FormatoCertificado.DIGITAL_FIRMADO:
                resultado_firma = self._aplicar_firma_digital()
                if not resultado_firma.get('success'):
                    return resultado_firma
            
            logger.info(f"Certificado {self.numero_certificado} firmado por {firmado_por}")
            
            return {
                'success': True,
                'message': 'Certificado firmado exitosamente',
                'fecha_firma': self.fecha_firma
            }
            
        except Exception as e:
            logger.error(f"Error firmando certificado: {str(e)}")
            return {
                'success': False,
                'message': f"Error firmando certificado: {str(e)}"
            }
    
    def _aplicar_firma_digital(self) -> Dict[str, Any]:
        """
        Aplica firma digital al certificado.
        
        Returns:
            dict: Resultado de la firma digital
        """
        try:
            # Llamar al servicio de firma digital
            result = self._sp_manager.executor.execute(
                'emision_certificados',
                'aplicar_firma_digital',
                {
                    'id_emision': self.id_emision,
                    'firmado_por': self.firmado_por,
                    'cargo_firmante': self.cargo_firmante
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error aplicando firma digital: {str(e)}")
            return {
                'success': False,
                'message': f"Error en firma digital: {str(e)}"
            }
    
    def entregar_certificado(
        self,
        entregado_por: str,
        recibido_por: str,
        documento_receptor: str = None,
        parentesco: str = None,
        medio_entrega: str = "presencial",
        observaciones: str = None
    ) -> None:
        """
        Registra la entrega del certificado.
        
        Args:
            entregado_por: Usuario que entrega
            recibido_por: Persona que recibe
            documento_receptor: Documento del receptor
            parentesco: Parentesco con el catequizando
            medio_entrega: Medio de entrega
            observaciones: Observaciones
        """
        if not self.esta_firmado:
            raise ValidationError("Solo se pueden entregar certificados firmados")
        
        self.estado = EstadoCertificado.ENTREGADO
        self.fecha_entrega = date.today()
        self.entregado_por = entregado_por
        self.recibido_por = recibido_por
        self.documento_receptor = documento_receptor
        self.parentesco_receptor = parentesco
        self.medio_entrega = medio_entrega
        
        if observaciones:
            self.observaciones = f"{self.observaciones or ''}\nEntrega: {observaciones}".strip()
        
        logger.info(f"Certificado {self.numero_certificado} entregado a {recibido_por}")
    
    def verificar_certificado(self, verificado_por: str = None) -> Dict[str, Any]:
        """
        Verifica la autenticidad del certificado.
        
        Args:
            verificado_por: Usuario que verifica
            
        Returns:
            dict: Resultado de la verificación
        """
        try:
            # Incrementar contador de verificaciones
            self.verificaciones_realizadas += 1
            self.ultima_verificacion = datetime.now()
            
            # Llamar al servicio de verificación
            result = self._sp_manager.executor.execute(
                'emision_certificados',
                'verificar_certificado',
                {
                    'numero_certificado': self.numero_certificado,
                    'codigo_verificacion': self.codigo_verificacion,
                    'verificado_por': verificado_por
                }
            )
            
            if result.get('success'):
                logger.info(f"Certificado {self.numero_certificado} verificado exitosamente")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando certificado: {str(e)}")
            return {
                'success': False,
                'message': f"Error en verificación: {str(e)}"
            }
    
    def generar_duplicado(
        self,
        motivo: str,
        solicitado_por: str
    ) -> 'EmisionCertificado':
        """
        Genera un duplicado del certificado.
        
        Args:
            motivo: Motivo del duplicado
            solicitado_por: Usuario que solicita
            
        Returns:
            EmisionCertificado: Nuevo certificado duplicado
        """
        if not self.esta_entregado:
            raise ValidationError("Solo se pueden duplicar certificados entregados")
        
        # Crear nuevo certificado como duplicado
        duplicado = EmisionCertificado(
            id_catequizando=self.id_catequizando,
            id_inscripcion=self.id_inscripcion,
            tipo_certificado=self.tipo_certificado,
            formato=self.formato,
            nivel_validacion=self.nivel_validacion,
            titulo_certificado=self.titulo_certificado,
            descripcion=self.descripcion,
            nombre_completo=self.nombre_completo,
            documento_identidad=self.documento_identidad,
            fecha_nacimiento=self.fecha_nacimiento,
            programa_catequesis=self.programa_catequesis,
            nivel_catequesis=self.nivel_catequesis,
            año_catequesis=self.año_catequesis,
            fecha_sacramento=self.fecha_sacramento,
            lugar_sacramento=self.lugar_sacramento,
            celebrante=self.celebrante,
            calificacion_final=self.calificacion_final,
            porcentaje_asistencia=self.porcentaje_asistencia,
            es_duplicado=True,
            certificado_original=self.id_emision,
            motivo_duplicado=motivo,
            costo_emision=self.costo_emision
        )
        
        logger.info(f"Generado duplicado de certificado {self.numero_certificado}: {motivo}")
        
        return duplicado
    
    def anular_certificado(
        self,
        motivo: str,
        anulado_por: str,
        certificado_reemplazo: int = None
    ) -> None:
        """
        Anula el certificado.
        
        Args:
            motivo: Motivo de la anulación
            anulado_por: Usuario que anula
            certificado_reemplazo: ID del certificado de reemplazo
        """
        if not self.puede_anular:
            raise ValidationError("El certificado no puede ser anulado")
        
        self.estado = EstadoCertificado.ANULADO
        self.fecha_anulacion = date.today()
        self.motivo_anulacion = motivo
        self.anulado_por = anulado_por
        self.certificado_reemplazo = certificado_reemplazo
        
        logger.info(f"Certificado {self.numero_certificado} anulado: {motivo}")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_certificado'] = self.tipo_certificado.value
        data['estado'] = self.estado.value
        data['formato'] = self.formato.value
        data['nivel_validacion'] = self.nivel_validacion.value
        
        # Agregar propiedades calculadas
        data['descripcion_tipo'] = self.descripcion_tipo
        data['descripcion_estado'] = self.descripcion_estado
        data['esta_emitido'] = self.esta_emitido
        data['esta_firmado'] = self.esta_firmado
        data['esta_entregado'] = self.esta_entregado
        data['puede_emitir'] = self.puede_emitir
        data['puede_firmar'] = self.puede_firmar
        data['puede_anular'] = self.puede_anular
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'hash_documento', 'ruta_archivo', 'notas_internas',
                'numero_registro_firmante', 'documento_receptor'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_catequizando(cls, id_catequizando: int) -> List['EmisionCertificado']:
        """Busca certificados de un catequizando."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'emision_certificados',
                'obtener_por_catequizando',
                {'id_catequizando': id_catequizando}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando certificados por catequizando: {str(e)}")
            return []
    
    @classmethod
    def find_by_numero_certificado(cls, numero_certificado: str) -> Optional['EmisionCertificado']:
        """Busca un certificado por número."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'emision_certificados',
                'obtener_por_numero_certificado',
                {'numero_certificado': numero_certificado}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando certificado por número: {str(e)}")
            return None
    
    @classmethod
    def verificar_por_codigo(cls, codigo_verificacion: str) -> Optional['EmisionCertificado']:
        """Verifica un certificado por código de verificación."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'emision_certificados',
                'verificar_por_codigo',
                {'codigo_verificacion': codigo_verificacion}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error verificando certificado por código: {str(e)}")
            return None
    
    @classmethod
    def find_pendientes_firma(cls) -> List['EmisionCertificado']:
        """Busca certificados pendientes de firma."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'emision_certificados',
                'obtener_pendientes_firma',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando certificados pendientes de firma: {str(e)}")
            return []
    
    def save(self, usuario: str = None) -> 'EmisionCertificado':
        """Guarda el certificado con validaciones adicionales."""
        # Generar número de certificado si no existe y no es pendiente
        if not self.numero_certificado and self.estado != EstadoCertificado.PENDIENTE:
            self.generar_numero_certificado()
        
        # Generar código de verificación si no existe
        if not self.codigo_verificacion:
            self.generar_codigo_verificacion()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('emision_certificado', EmisionCertificado)