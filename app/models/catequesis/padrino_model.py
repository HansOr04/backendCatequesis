"""
Modelo de Padrino para el sistema de catequesis.
Maneja la información de padrinos y madrinas para los diferentes sacramentos.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class TipoPadrino(Enum):
    """Tipos de padrino/madrina."""
    PADRINO = "padrino"
    MADRINA = "madrina"
    PADRINO_PAREJA = "padrino_pareja"  # Padrino cuando actúa en pareja
    MADRINA_PAREJA = "madrina_pareja"  # Madrina cuando actúa en pareja


class EstadoPadrino(Enum):
    """Estados del padrino."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    FALLECIDO = "fallecido"


class TipoSacramento(Enum):
    """Tipos de sacramento para el padrinazgo."""
    BAUTISMO = "bautismo"
    CONFIRMACION = "confirmacion"
    PRIMERA_COMUNION = "primera_comunion"
    MATRIMONIO = "matrimonio"


class Padrino(BaseModel):
    """
    Modelo de Padrino del sistema de catequesis.
    Representa a los padrinos y madrinas de los diferentes sacramentos.
    """
    
    # Configuración del modelo
    _table_schema = "padrinos"
    _primary_key = "id_padrino"
    _required_fields = ["nombres", "apellidos", "tipo_padrino"]
    _unique_fields = ["documento_identidad"]
    _searchable_fields = [
        "nombres", "apellidos", "documento_identidad", 
        "telefono", "email"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Padrino."""
        # Identificación básica
        self.id_padrino: Optional[int] = None
        self.nombres: str = ""
        self.apellidos: str = ""
        self.fecha_nacimiento: Optional[date] = None
        self.lugar_nacimiento: Optional[str] = None
        self.documento_identidad: Optional[str] = None
        self.estado: EstadoPadrino = EstadoPadrino.ACTIVO
        
        # Tipo de padrino
        self.tipo_padrino: TipoPadrino = TipoPadrino.PADRINO
        self.es_pareja_padrinos: bool = False
        self.id_pareja: Optional[int] = None  # ID del padrino/madrina pareja
        
        # Información de contacto
        self.direccion: Optional[str] = None
        self.ciudad: Optional[str] = None
        self.departamento: Optional[str] = None
        self.telefono: Optional[str] = None
        self.telefono_alternativo: Optional[str] = None
        self.email: Optional[str] = None
        
        # Información sacramental del padrino
        self.fecha_bautismo: Optional[date] = None
        self.lugar_bautismo: Optional[str] = None
        self.fecha_confirmacion: Optional[date] = None
        self.lugar_confirmacion: Optional[str] = None
        self.fecha_matrimonio: Optional[date] = None
        self.lugar_matrimonio: Optional[str] = None
        self.es_catolico_practicante: bool = True
        
        # Información de la parroquia del padrino
        self.parroquia_pertenece: Optional[str] = None
        self.parroco_que_certifica: Optional[str] = None
        self.fecha_certificacion: Optional[date] = None
        self.numero_certificacion: Optional[str] = None
        
        # Información profesional/personal
        self.ocupacion: Optional[str] = None
        self.estado_civil: Optional[str] = None
        self.nombre_conyuge: Optional[str] = None
        
        # Control de padrinazgos
        self.numero_padrinazgos: int = 0
        self.puede_ser_padrino: bool = True
        self.motivo_inhabilitacion: Optional[str] = None
        self.fecha_inhabilitacion: Optional[date] = None
        
        # Observaciones
        self.observaciones: Optional[str] = None
        self.notas_especiales: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def nombre_completo(self) -> str:
        """Obtiene el nombre completo."""
        return f"{self.nombres} {self.apellidos}".strip()
    
    @property
    def edad(self) -> Optional[int]:
        """Calcula la edad actual."""
        if not self.fecha_nacimiento:
            return None
        
        today = date.today()
        edad = today.year - self.fecha_nacimiento.year
        
        if today.month < self.fecha_nacimiento.month or \
           (today.month == self.fecha_nacimiento.month and today.day < self.fecha_nacimiento.day):
            edad -= 1
        
        return edad
    
    @property
    def esta_activo(self) -> bool:
        """Verifica si está activo."""
        return self.estado == EstadoPadrino.ACTIVO
    
    @property
    def cumple_requisitos_basicos(self) -> bool:
        """Verifica si cumple los requisitos básicos para ser padrino."""
        # Mayor de 16 años
        if self.edad is None or self.edad < 16:
            return False
        
        # Debe estar bautizado y confirmado
        if not self.fecha_bautismo or not self.fecha_confirmacion:
            return False
        
        # Debe ser católico practicante
        if not self.es_catolico_practicante:
            return False
        
        # Debe estar habilitado
        if not self.puede_ser_padrino:
            return False
        
        return True
    
    @property
    def tiene_pareja(self) -> bool:
        """Verifica si actúa en pareja de padrinos."""
        return self.es_pareja_padrinos and self.id_pareja is not None
    
    @property
    def descripcion_tipo(self) -> str:
        """Obtiene la descripción del tipo de padrino."""
        descripciones = {
            TipoPadrino.PADRINO: "Padrino",
            TipoPadrino.MADRINA: "Madrina",
            TipoPadrino.PADRINO_PAREJA: "Padrino (en pareja)",
            TipoPadrino.MADRINA_PAREJA: "Madrina (en pareja)"
        }
        return descripciones.get(self.tipo_padrino, "No especificado")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Padrino."""
        # Validar nombres y apellidos
        if self.nombres and len(self.nombres.strip()) < 2:
            raise ValidationError("Los nombres deben tener al menos 2 caracteres")
        
        if self.apellidos and len(self.apellidos.strip()) < 2:
            raise ValidationError("Los apellidos deben tener al menos 2 caracteres")
        
        # Validar fecha de nacimiento
        if self.fecha_nacimiento:
            today = date.today()
            edad = self.edad
            
            if self.fecha_nacimiento > today:
                raise ValidationError("La fecha de nacimiento no puede ser futura")
            
            if edad is not None:
                if edad < 16:
                    raise ValidationError("Los padrinos deben tener al menos 16 años")
                if edad > 100:
                    raise ValidationError("La edad máxima es 100 años")
        
        # Validar documento de identidad
        if self.documento_identidad:
            if not DataValidator.validate_cedula(self.documento_identidad):
                raise ValidationError("El número de documento no es válido")
        
        # Validar teléfonos
        if self.telefono and not DataValidator.validate_phone(self.telefono):
            raise ValidationError("El formato del teléfono principal no es válido")
        
        if self.telefono_alternativo and not DataValidator.validate_phone(self.telefono_alternativo):
            raise ValidationError("El formato del teléfono alternativo no es válido")
        
        # Validar email
        if self.email and not DataValidator.validate_email(self.email):
            raise ValidationError("El formato del email no es válido")
        
        # Validar fechas sacramentales
        if self.fecha_bautismo and self.fecha_nacimiento:
            if self.fecha_bautismo < self.fecha_nacimiento:
                raise ValidationError("La fecha de bautismo no puede ser anterior al nacimiento")
        
        if self.fecha_confirmacion and self.fecha_bautismo:
            if self.fecha_confirmacion < self.fecha_bautismo:
                raise ValidationError("La confirmación debe ser posterior al bautismo")
        
        # Validar pareja de padrinos
        if self.es_pareja_padrinos:
            if not self.id_pareja:
                raise ValidationError("Si actúa en pareja, debe especificar el ID de la pareja")
            
            if self.id_pareja == self.id_padrino:
                raise ValidationError("No puede ser pareja de sí mismo")
        
        # Validar número de padrinazgos
        if self.numero_padrinazgos < 0:
            raise ValidationError("El número de padrinazgos no puede ser negativo")
        
        # Validar enums
        if isinstance(self.tipo_padrino, str):
            try:
                self.tipo_padrino = TipoPadrino(self.tipo_padrino)
            except ValueError:
                raise ValidationError(f"Tipo de padrino '{self.tipo_padrino}' no válido")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoPadrino(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
    
    def obtener_pareja(self) -> Optional['Padrino']:
        """
        Obtiene la información de la pareja de padrinos.
        
        Returns:
            Padrino: La pareja de padrinos o None
        """
        if not self.tiene_pareja:
            return None
        
        return Padrino.find_by_id(self.id_pareja)
    
    def obtener_padrinazgos(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de padrinazgos realizados.
        
        Returns:
            List: Lista de padrinazgos
        """
        try:
            result = self._sp_manager.executor.execute(
                'padrinos',
                'obtener_padrinazgos',
                {'id_padrino': self.id_padrino}
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo padrinazgos: {str(e)}")
            return []
    
    def verificar_disponibilidad_sacramento(self, tipo_sacramento: TipoSacramento) -> Dict[str, Any]:
        """
        Verifica si puede ser padrino para un sacramento específico.
        
        Args:
            tipo_sacramento: Tipo de sacramento
            
        Returns:
            dict: Resultado de la verificación
        """
        if not self.cumple_requisitos_basicos:
            return {
                'puede_ser_padrino': False,
                'razon': 'No cumple los requisitos básicos'
            }
        
        # Verificar requisitos específicos por sacramento
        if tipo_sacramento == TipoSacramento.MATRIMONIO:
            # Para matrimonio debe estar casado por la iglesia
            if not self.fecha_matrimonio:
                return {
                    'puede_ser_padrino': False,
                    'razon': 'Para ser padrino de matrimonio debe estar casado por la iglesia'
                }
        
        # Verificar límite de padrinazgos (máximo 3 activos)
        padrinazgos_activos = len([p for p in self.obtener_padrinazgos() 
                                 if p.get('estado') == 'activo'])
        
        if padrinazgos_activos >= 3:
            return {
                'puede_ser_padrino': False,
                'razon': 'Máximo 3 padrinazgos activos permitidos'
            }
        
        return {
            'puede_ser_padrino': True,
            'razon': 'Cumple todos los requisitos'
        }
    
    def registrar_padrinazgo(
        self,
        id_catequizando: int,
        tipo_sacramento: TipoSacramento,
        fecha_sacramento: date,
        lugar_sacramento: str,
        id_pareja: int = None
    ) -> Dict[str, Any]:
        """
        Registra un nuevo padrinazgo.
        
        Args:
            id_catequizando: ID del catequizando
            tipo_sacramento: Tipo de sacramento
            fecha_sacramento: Fecha del sacramento
            lugar_sacramento: Lugar del sacramento
            id_pareja: ID de la pareja de padrinos (opcional)
            
        Returns:
            dict: Resultado del registro
        """
        try:
            # Verificar disponibilidad
            disponibilidad = self.verificar_disponibilidad_sacramento(tipo_sacramento)
            if not disponibilidad['puede_ser_padrino']:
                return {
                    'success': False,
                    'message': disponibilidad['razon']
                }
            
            # Registrar padrinazgo
            result = self._sp_manager.executor.execute(
                'padrinos',
                'registrar_padrinazgo',
                {
                    'id_padrino': self.id_padrino,
                    'id_catequizando': id_catequizando,
                    'tipo_sacramento': tipo_sacramento.value,
                    'fecha_sacramento': fecha_sacramento,
                    'lugar_sacramento': lugar_sacramento,
                    'id_pareja': id_pareja
                }
            )
            
            if result.get('success'):
                # Actualizar contador
                self.numero_padrinazgos += 1
                self.save()
                
                logger.info(f"Padrinazgo registrado para {self.nombre_completo}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error registrando padrinazgo: {str(e)}")
            return {
                'success': False,
                'message': f"Error al registrar: {str(e)}"
            }
    
    def establecer_pareja(self, id_pareja: int) -> None:
        """
        Establece una pareja de padrinos.
        
        Args:
            id_pareja: ID de la pareja
        """
        if id_pareja == self.id_padrino:
            raise ValidationError("No puede ser pareja de sí mismo")
        
        # Verificar que la pareja existe y es del sexo opuesto
        pareja = Padrino.find_by_id(id_pareja)
        if not pareja:
            raise ValidationError("La pareja especificada no existe")
        
        # Configurar como pareja
        self.es_pareja_padrinos = True
        self.id_pareja = id_pareja
        
        # Actualizar tipo según el sexo
        if self.tipo_padrino == TipoPadrino.PADRINO:
            self.tipo_padrino = TipoPadrino.PADRINO_PAREJA
        elif self.tipo_padrino == TipoPadrino.MADRINA:
            self.tipo_padrino = TipoPadrino.MADRINA_PAREJA
        
        logger.info(f"Pareja establecida entre {self.nombre_completo} y {pareja.nombre_completo}")
    
    def remover_pareja(self) -> None:
        """Remueve la pareja de padrinos."""
        self.es_pareja_padrinos = False
        self.id_pareja = None
        
        # Restaurar tipo original
        if self.tipo_padrino == TipoPadrino.PADRINO_PAREJA:
            self.tipo_padrino = TipoPadrino.PADRINO
        elif self.tipo_padrino == TipoPadrino.MADRINA_PAREJA:
            self.tipo_padrino = TipoPadrino.MADRINA
        
        logger.info(f"Pareja removida para {self.nombre_completo}")
    
    def inhabilitar(self, motivo: str, fecha_inhabilitacion: date = None) -> None:
        """
        Inhabilita al padrino.
        
        Args:
            motivo: Motivo de la inhabilitación
            fecha_inhabilitacion: Fecha de inhabilitación
        """
        self.puede_ser_padrino = False
        self.motivo_inhabilitacion = motivo
        self.fecha_inhabilitacion = fecha_inhabilitacion or date.today()
        
        logger.info(f"Padrino {self.nombre_completo} inhabilitado: {motivo}")
    
    def rehabilitar(self) -> None:
        """Rehabilita al padrino."""
        self.puede_ser_padrino = True
        self.motivo_inhabilitacion = None
        self.fecha_inhabilitacion = None
        
        logger.info(f"Padrino {self.nombre_completo} rehabilitado")
    
    def actualizar_certificacion(
        self,
        parroco: str,
        fecha_certificacion: date = None,
        numero_certificacion: str = None
    ) -> None:
        """
        Actualiza la certificación del padrino.
        
        Args:
            parroco: Nombre del párroco que certifica
            fecha_certificacion: Fecha de certificación
            numero_certificacion: Número de certificación
        """
        self.parroco_que_certifica = parroco
        self.fecha_certificacion = fecha_certificacion or date.today()
        self.numero_certificacion = numero_certificacion
        
        logger.info(f"Certificación actualizada para {self.nombre_completo}")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_padrino'] = self.tipo_padrino.value
        data['estado'] = self.estado.value
        
        # Agregar propiedades calculadas
        data['edad'] = self.edad
        data['cumple_requisitos_basicos'] = self.cumple_requisitos_basicos
        data['tiene_pareja'] = self.tiene_pareja
        data['descripcion_tipo'] = self.descripcion_tipo
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'documento_identidad', 'telefono', 'telefono_alternativo',
                'email', 'direccion'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_documento(cls, documento: str) -> Optional['Padrino']:
        """Busca un padrino por documento."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'padrinos',
                'buscar_por_documento',
                {'documento_identidad': documento}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando padrino por documento {documento}: {str(e)}")
            return None
    
    @classmethod
    def find_disponibles_para_sacramento(cls, tipo_sacramento: TipoSacramento) -> List['Padrino']:
        """Busca padrinos disponibles para un sacramento."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'padrinos',
                'obtener_disponibles_sacramento',
                {'tipo_sacramento': tipo_sacramento.value}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando padrinos disponibles: {str(e)}")
            return []
    
    @classmethod
    def find_parejas_disponibles(cls) -> List[Dict[str, Any]]:
        """Busca parejas de padrinos disponibles."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'padrinos',
                'obtener_parejas_disponibles',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
            
        except Exception as e:
            logger.error(f"Error buscando parejas disponibles: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Padrino':
        """Guarda el padrino con validaciones adicionales."""
        # Actualizar número de padrinazgos si no es nuevo
        if not self.is_new:
            padrinazgos = self.obtener_padrinazgos()
            self.numero_padrinazgos = len(padrinazgos)
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('padrino', Padrino)