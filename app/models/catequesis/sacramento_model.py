"""
Modelo de Sacramento para el sistema de catequesis.
Registra la información de los sacramentos recibidos por los catequizandos.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class TipoSacramento(Enum):
    """Tipos de sacramento."""
    BAUTISMO = "bautismo"
    CONFIRMACION = "confirmacion"
    PRIMERA_COMUNION = "primera_comunion"
    MATRIMONIO = "matrimonio"
    ORDEN_SACERDOTAL = "orden_sacerdotal"
    UNCION_ENFERMOS = "uncion_enfermos"
    RECONCILIACION = "reconciliacion"


class EstadoSacramento(Enum):
    """Estados del sacramento."""
    VIGENTE = "vigente"
    ANULADO = "anulado"
    CORREGIDO = "corregido"
    PENDIENTE_VALIDACION = "pendiente_validacion"


class TipoCelebracion(Enum):
    """Tipos de celebración."""
    INDIVIDUAL = "individual"
    COMUNITARIA = "comunitaria"
    FAMILIAR = "familiar"
    ESPECIAL = "especial"


class Sacramento(BaseModel):
    """
    Modelo de Sacramento del sistema de catequesis.
    Registra los sacramentos recibidos por los catequizandos.
    """
    
    # Configuración del modelo
    _table_schema = "sacramentos"
    _primary_key = "id_sacramento"
    _required_fields = ["id_catequizando", "tipo_sacramento", "fecha_sacramento", "lugar_sacramento"]
    _unique_fields = []
    _searchable_fields = [
        "lugar_sacramento", "ministro", "padrino", "madrina", 
        "numero_acta", "libro_registro"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Sacramento."""
        # Identificación básica
        self.id_sacramento: Optional[int] = None
        self.id_catequizando: int = 0
        self.tipo_sacramento: TipoSacramento = TipoSacramento.BAUTISMO
        self.estado: EstadoSacramento = EstadoSacramento.VIGENTE
        
        # Información del sacramento
        self.fecha_sacramento: Optional[date] = None
        self.hora_sacramento: Optional[str] = None
        self.lugar_sacramento: str = ""
        self.parroquia_sacramento: Optional[str] = None
        self.diocesis: Optional[str] = None
        self.ciudad: Optional[str] = None
        self.pais: str = "Colombia"
        
        # Ministro que celebra
        self.ministro: Optional[str] = None
        self.titulo_ministro: Optional[str] = None  # Padre, Obispo, Diácono, etc.
        self.ministro_suplente: Optional[str] = None
        
        # Padrinos/testigos
        self.padrino: Optional[str] = None
        self.madrina: Optional[str] = None
        self.id_padrino: Optional[int] = None  # Referencia al modelo Padrino
        self.id_madrina: Optional[int] = None  # Referencia al modelo Padrino
        self.testigo_1: Optional[str] = None
        self.testigo_2: Optional[str] = None
        
        # Registro civil/eclesiástico
        self.numero_acta: Optional[str] = None
        self.folio: Optional[str] = None
        self.libro_registro: Optional[str] = None
        self.tomo: Optional[str] = None
        self.pagina: Optional[str] = None
        self.fecha_registro: Optional[date] = None
        self.numero_partida: Optional[str] = None
        
        # Información de los padres (para bautismo principalmente)
        self.nombre_padre: Optional[str] = None
        self.nombre_madre: Optional[str] = None
        self.lugar_nacimiento_padre: Optional[str] = None
        self.lugar_nacimiento_madre: Optional[str] = None
        
        # Detalles de la celebración
        self.tipo_celebracion: TipoCelebracion = TipoCelebracion.INDIVIDUAL
        self.numero_participantes: Optional[int] = None
        self.nombre_celebracion: Optional[str] = None  # Ej: "Primera Comunión Grupo A"
        self.tema_celebracion: Optional[str] = None
        
        # Información adicional específica por sacramento
        self.nombre_santo_confirmacion: Optional[str] = None  # Para confirmación
        self.obispo_confirmante: Optional[str] = None  # Para confirmación
        self.edad_al_recibir: Optional[int] = None
        self.condiciones_especiales: Optional[str] = None
        
        # Documentación
        self.tiene_certificado: bool = False
        self.numero_certificado: Optional[str] = None
        self.fecha_expedicion_certificado: Optional[date] = None
        self.observaciones_certificado: Optional[str] = None
        
        # Control y validación
        self.validado_por: Optional[str] = None
        self.fecha_validacion: Optional[date] = None
        self.requiere_correccion: bool = False
        self.motivo_correccion: Optional[str] = None
        
        # Observaciones generales
        self.observaciones: Optional[str] = None
        self.notas_especiales: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def descripcion_sacramento(self) -> str:
        """Obtiene la descripción del sacramento."""
        descripciones = {
            TipoSacramento.BAUTISMO: "Bautismo",
            TipoSacramento.CONFIRMACION: "Confirmación",
            TipoSacramento.PRIMERA_COMUNION: "Primera Comunión",
            TipoSacramento.MATRIMONIO: "Matrimonio",
            TipoSacramento.ORDEN_SACERDOTAL: "Orden Sacerdotal",
            TipoSacramento.UNCION_ENFERMOS: "Unción de los Enfermos",
            TipoSacramento.RECONCILIACION: "Reconciliación"
        }
        return descripciones.get(self.tipo_sacramento, "Sacramento")
    
    @property
    def esta_vigente(self) -> bool:
        """Verifica si el sacramento está vigente."""
        return self.estado == EstadoSacramento.VIGENTE
    
    @property
    def fecha_formateada(self) -> str:
        """Obtiene la fecha formateada."""
        if not self.fecha_sacramento:
            return "Fecha no especificada"
        
        return self.fecha_sacramento.strftime("%d de %B de %Y")
    
    @property
    def lugar_completo(self) -> str:
        """Obtiene la descripción completa del lugar."""
        partes_lugar = [self.lugar_sacramento]
        
        if self.parroquia_sacramento:
            partes_lugar.append(f"Parroquia {self.parroquia_sacramento}")
        if self.ciudad:
            partes_lugar.append(self.ciudad)
        if self.diocesis:
            partes_lugar.append(f"Diócesis de {self.diocesis}")
        
        return ", ".join(filter(None, partes_lugar))
    @property
    def padrinos_completo(self) -> str:
        """Obtiene la información completa de padrinos."""
        padrinos = []
        
        if self.padrino:
            padrinos.append(f"Padrino: {self.padrino}")
        if self.madrina:
            padrinos.append(f"Madrina: {self.madrina}")
        if self.testigo_1:
            padrinos.append(f"Testigo 1: {self.testigo_1}")
        if self.testigo_2:
            padrinos.append(f"Testigo 2: {self.testigo_2}")
        
        return " | ".join(padrinos) if padrinos else "Sin padrinos registrados"

    @property
    def referencia_registro(self) -> str:
        """Obtiene la referencia completa del registro."""
        referencias = []
        
        if self.numero_acta:
            referencias.append(f"Acta: {self.numero_acta}")
        if self.libro_registro:
            referencias.append(f"Libro: {self.libro_registro}")
        if self.folio:
            referencias.append(f"Folio: {self.folio}")
        if self.pagina:
            referencias.append(f"Página: {self.pagina}")
        
        return " - ".join(referencias) if referencias else "Sin referencia"

    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Sacramento."""
        # Validar ID del catequizando
        if self.id_catequizando <= 0:
            raise ValidationError("Debe especificar un catequizando válido")
        
        # Validar fecha del sacramento
        if self.fecha_sacramento:
            if self.fecha_sacramento > date.today():
                raise ValidationError("La fecha del sacramento no puede ser futura")
            
            # Validar que no sea muy antigua (más de 150 años)
            if self.fecha_sacramento.year < (date.today().year - 150):
                raise ValidationError("La fecha del sacramento es muy antigua")
        
        # Validar lugar del sacramento
        if self.lugar_sacramento and len(self.lugar_sacramento.strip()) < 3:
            raise ValidationError("El lugar del sacramento debe tener al menos 3 caracteres")
        
        # Validar número de participantes
        if self.numero_participantes is not None:
            if self.numero_participantes < 1 or self.numero_participantes > 1000:
                raise ValidationError("El número de participantes debe estar entre 1 y 1000")
        
        # Validar edad al recibir
        if self.edad_al_recibir is not None:
            if self.edad_al_recibir < 0 or self.edad_al_recibir > 100:
                raise ValidationError("La edad al recibir debe estar entre 0 y 100 años")
        
        # Validaciones específicas por tipo de sacramento
        if self.tipo_sacramento == TipoSacramento.CONFIRMACION:
            if not self.nombre_santo_confirmacion:
                raise ValidationError("La confirmación requiere el nombre del santo")
        
        if self.tipo_sacramento == TipoSacramento.BAUTISMO:
            if not (self.padrino or self.madrina):
                raise ValidationError("El bautismo requiere al menos un padrino o madrina")
        
        # Validar enums
        if isinstance(self.tipo_sacramento, str):
            try:
                self.tipo_sacramento = TipoSacramento(self.tipo_sacramento)
            except ValueError:
                raise ValidationError(f"Tipo de sacramento '{self.tipo_sacramento}' no válido")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoSacramento(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.tipo_celebracion, str):
            try:
                self.tipo_celebracion = TipoCelebracion(self.tipo_celebracion)
            except ValueError:
                raise ValidationError(f"Tipo de celebración '{self.tipo_celebracion}' no válido")
        
        # Validar fechas de registro
        if self.fecha_registro and self.fecha_sacramento:
            if self.fecha_registro < self.fecha_sacramento:
                raise ValidationError("La fecha de registro no puede ser anterior al sacramento")
        
        if self.fecha_expedicion_certificado and self.fecha_sacramento:
            if self.fecha_expedicion_certificado < self.fecha_sacramento:
                raise ValidationError("La fecha de expedición no puede ser anterior al sacramento")

    def obtener_catequizando(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información del catequizando.
        
        Returns:
            dict: Información del catequizando o None
        """
        try:
            result = self._sp_manager.catequizandos.obtener_catequizando(self.id_catequizando)
            
            if result.get('success') and result.get('data'):
                return result['data']
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo catequizando: {str(e)}")
            return None

    def obtener_padrino_info(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información del padrino registrado.
        
        Returns:
            dict: Información del padrino o None
        """
        if not self.id_padrino:
            return None
        
        try:
            result = self._sp_manager.executor.execute(
                'padrinos',
                'obtener',
                {'id_padrino': self.id_padrino}
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo padrino: {str(e)}")
            return None

    def obtener_madrina_info(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información de la madrina registrada.
        
        Returns:
            dict: Información de la madrina o None
        """
        if not self.id_madrina:
            return None
        
        try:
            result = self._sp_manager.executor.execute(
                'padrinos',
                'obtener',
                {'id_padrino': self.id_madrina}
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo madrina: {str(e)}")
            return None

    def generar_numero_acta(self) -> str:
        """
        Genera un número de acta único.
        
        Returns:
            str: Número de acta generado
        """
        if not self.fecha_sacramento:
            raise ValidationError("Se requiere fecha del sacramento para generar número de acta")
        
        # Formato: TIPO-AAAA-NNNN
        tipo_codigo = {
            TipoSacramento.BAUTISMO: "BAU",
            TipoSacramento.CONFIRMACION: "CON",
            TipoSacramento.PRIMERA_COMUNION: "PCO",
            TipoSacramento.MATRIMONIO: "MAT",
            TipoSacramento.ORDEN_SACERDOTAL: "ORD",
            TipoSacramento.UNCION_ENFERMOS: "UNE",
            TipoSacramento.RECONCILIACION: "REC"
        }
        
        codigo = tipo_codigo.get(self.tipo_sacramento, "SAC")
        año = self.fecha_sacramento.year
        
        # Obtener siguiente número secuencial
        try:
            result = self._sp_manager.executor.execute(
                'sacramentos',
                'obtener_siguiente_numero_acta',
                {
                    'tipo_sacramento': self.tipo_sacramento.value,
                    'año': año
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            numero_acta = f"{codigo}-{año}-{numero:04d}"
            self.numero_acta = numero_acta
            
            return numero_acta
            
        except Exception as e:
            logger.error(f"Error generando número de acta: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%m%d%H%M")
            return f"{codigo}-{año}-{timestamp}"

    def generar_certificado(self, plantilla: str = None) -> Dict[str, Any]:
        """
        Genera un certificado del sacramento.
        
        Args:
            plantilla: Plantilla a usar para el certificado
            
        Returns:
            dict: Información del certificado generado
        """
        try:
            # Obtener información del catequizando
            catequizando = self.obtener_catequizando()
            if not catequizando:
                raise ValidationError("No se pudo obtener información del catequizando")
            
            # Generar número de certificado si no existe
            if not self.numero_certificado:
                self.numero_certificado = self._generar_numero_certificado()
            
            # Datos para el certificado
            datos_certificado = {
                'numero_certificado': self.numero_certificado,
                'tipo_sacramento': self.descripcion_sacramento,
                'catequizando': catequizando.get('nombre_completo', ''),
                'fecha_sacramento': self.fecha_formateada,
                'lugar_sacramento': self.lugar_completo,
                'ministro': self.ministro,
                'padrinos': self.padrinos_completo,
                'numero_acta': self.numero_acta,
                'fecha_expedicion': date.today().strftime("%d de %B de %Y"),
                'plantilla': plantilla or 'certificado_estandar'
            }
            
            # Marcar como certificado expedido
            self.tiene_certificado = True
            self.fecha_expedicion_certificado = date.today()
            
            return {
                'success': True,
                'datos_certificado': datos_certificado,
                'numero_certificado': self.numero_certificado
            }
            
        except Exception as e:
            logger.error(f"Error generando certificado: {str(e)}")
            return {
                'success': False,
                'message': f"Error generando certificado: {str(e)}"
            }

    def _generar_numero_certificado(self) -> str:
        """Genera un número de certificado único."""
        try:
            result = self._sp_manager.executor.execute(
                'sacramentos',
                'obtener_siguiente_numero_certificado',
                {
                    'tipo_sacramento': self.tipo_sacramento.value,
                    'año': date.today().year
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            return f"CERT-{self.tipo_sacramento.value.upper()}-{date.today().year}-{numero:06d}"
            
        except Exception as e:
            logger.error(f"Error generando número de certificado: {str(e)}")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"CERT-{self.tipo_sacramento.value.upper()}-{timestamp}"

    def validar_sacramento(self, validador: str, observaciones: str = None) -> None:
        """
        Valida el sacramento.
        
        Args:
            validador: Usuario que valida
            observaciones: Observaciones de la validación
        """
        self.estado = EstadoSacramento.VIGENTE
        self.validado_por = validador
        self.fecha_validacion = date.today()
        
        if observaciones:
            self.observaciones = observaciones
        
        logger.info(f"Sacramento {self.descripcion_sacramento} validado por {validador}")

    def marcar_para_correccion(self, motivo: str) -> None:
        """
        Marca el sacramento para corrección.
        
        Args:
            motivo: Motivo de la corrección
        """
        self.requiere_correccion = True
        self.motivo_correccion = motivo
        self.estado = EstadoSacramento.PENDIENTE_VALIDACION
        
        logger.info(f"Sacramento marcado para corrección: {motivo}")

    def anular_sacramento(self, motivo: str) -> None:
        """
        Anula el sacramento.
        
        Args:
            motivo: Motivo de la anulación
        """
        self.estado = EstadoSacramento.ANULADO
        self.observaciones = f"ANULADO: {motivo}"
        
        logger.info(f"Sacramento anulado: {motivo}")