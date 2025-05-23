"""
Modelo de Parroquia para el sistema de catequesis.
Maneja la información y operaciones relacionadas con las parroquias.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError, ModelError
from app.utils.validators import DataValidator
from app.utils.constants import SystemConstants

logger = logging.getLogger(__name__)


class EstadoParroquia(Enum):
    """Estados posibles de una parroquia."""
    ACTIVA = "activa"
    INACTIVA = "inactiva"
    SUSPENDIDA = "suspendida"
    EN_CONSTRUCCION = "en_construccion"


class TipoParroquia(Enum):
    """Tipos de parroquia según su estructura."""
    PARROQUIA = "parroquia"
    VICARIA = "vicaria"
    CAPILLA = "capilla"
    SANTUARIO = "santuario"


class Parroquia(BaseModel):
    """
    Modelo de Parroquia del sistema de catequesis.
    Maneja la información básica y operacional de las parroquias.
    """
    
    # Configuración del modelo
    _table_schema = "parroquias"
    _primary_key = "id_parroquia"
    _required_fields = ["nombre", "direccion"]
    _unique_fields = ["nombre", "codigo_parroquia"]
    _searchable_fields = ["nombre", "direccion", "telefono", "email", "parroco"]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Parroquia."""
        # Datos básicos de identificación
        self.id_parroquia: Optional[int] = None
        self.nombre: str = ""
        self.codigo_parroquia: Optional[str] = None
        self.tipo_parroquia: TipoParroquia = TipoParroquia.PARROQUIA
        self.estado: EstadoParroquia = EstadoParroquia.ACTIVA
        
        # Información de contacto
        self.direccion: str = ""
        self.ciudad: Optional[str] = None
        self.departamento: Optional[str] = None
        self.codigo_postal: Optional[str] = None
        self.telefono: Optional[str] = None
        self.telefono_alternativo: Optional[str] = None
        self.email: Optional[str] = None
        self.sitio_web: Optional[str] = None
        
        # Información eclesiástica
        self.parroco: Optional[str] = None
        self.vicario: Optional[str] = None
        self.diocesis: Optional[str] = None
        self.decanato: Optional[str] = None
        self.fecha_fundacion: Optional[date] = None
        self.fecha_ereccion: Optional[date] = None
        self.santo_patrono: Optional[str] = None
        self.festividad_patronal: Optional[date] = None
        
        # Información administrativa
        self.capacidad_maxima: Optional[int] = None
        self.numero_catequistas: int = 0
        self.numero_grupos: int = 0
        self.numero_catequizandos: int = 0
        
        # Horarios y servicios
        self.horarios_misa: Optional[str] = None
        self.horarios_catequesis: Optional[str] = None
        self.servicios_disponibles: List[str] = []
        
        # Configuración específica
        self.configuracion: Dict[str, Any] = {}
        self.observaciones: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def direccion_completa(self) -> str:
        """Obtiene la dirección completa formateada."""
        direccion_parts = [self.direccion]
        
        if self.ciudad:
            direccion_parts.append(self.ciudad)
        if self.departamento:
            direccion_parts.append(self.departamento)
        if self.codigo_postal:
            direccion_parts.append(self.codigo_postal)
        
        return ", ".join(filter(None, direccion_parts))
    
    @property
    def esta_activa(self) -> bool:
        """Verifica si la parroquia está activa."""
        return self.estado == EstadoParroquia.ACTIVA
    
    @property
    def puede_inscribir(self) -> bool:
        """Verifica si la parroquia puede recibir inscripciones."""
        if not self.esta_activa:
            return False
        
        if self.capacidad_maxima:
            return self.numero_catequizandos < self.capacidad_maxima
        
        return True
    
    @property
    def ocupacion_porcentual(self) -> float:
        """Calcula el porcentaje de ocupación."""
        if not self.capacidad_maxima or self.capacidad_maxima == 0:
            return 0.0
        
        return (self.numero_catequizandos / self.capacidad_maxima) * 100
    
    @property
    def informacion_contacto(self) -> Dict[str, str]:
        """Obtiene información de contacto formateada."""
        contacto = {}
        
        if self.telefono:
            contacto['telefono_principal'] = self.telefono
        if self.telefono_alternativo:
            contacto['telefono_alternativo'] = self.telefono_alternativo
        if self.email:
            contacto['email'] = self.email
        if self.sitio_web:
            contacto['sitio_web'] = self.sitio_web
        
        return contacto
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Parroquia."""
        # Validar nombre
        if self.nombre:
            if len(self.nombre.strip()) < 3:
                raise ValidationError("El nombre de la parroquia debe tener al menos 3 caracteres")
        
        # Validar dirección
        if self.direccion:
            if len(self.direccion.strip()) < 10:
                raise ValidationError("La dirección debe tener al menos 10 caracteres")
        
        # Validar teléfonos
        if self.telefono and not DataValidator.validate_phone(self.telefono):
            raise ValidationError("El formato del teléfono principal no es válido")
        
        if self.telefono_alternativo and not DataValidator.validate_phone(self.telefono_alternativo):
            raise ValidationError("El formato del teléfono alternativo no es válido")
        
        # Validar email
        if self.email and not DataValidator.validate_email(self.email):
            raise ValidationError("El formato del email no es válido")
        
        # Validar URL del sitio web
        if self.sitio_web and not DataValidator.validate_url(self.sitio_web):
            raise ValidationError("El formato del sitio web no es válido")
        
        # Validar capacidad
        if self.capacidad_maxima is not None and self.capacidad_maxima < 1:
            raise ValidationError("La capacidad máxima debe ser mayor a 0")
        
        # Validar tipo de parroquia
        if isinstance(self.tipo_parroquia, str):
            try:
                self.tipo_parroquia = TipoParroquia(self.tipo_parroquia)
            except ValueError:
                raise ValidationError(f"Tipo de parroquia '{self.tipo_parroquia}' no válido")
        
        # Validar estado
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoParroquia(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        # Validar fechas
        if self.fecha_fundacion and self.fecha_ereccion:
            if self.fecha_fundacion > self.fecha_ereccion:
                raise ValidationError("La fecha de fundación no puede ser posterior a la fecha de erección")
        
        # Validar código de parroquia si se proporciona
        if self.codigo_parroquia:
            if not self.codigo_parroquia.replace('-', '').replace('_', '').isalnum():
                raise ValidationError("El código de parroquia solo puede contener letras, números, guiones y guiones bajos")
    
    def generar_codigo_parroquia(self) -> str:
        """
        Genera un código único para la parroquia basado en su nombre.
        
        Returns:
            str: Código generado
        """
        if not self.nombre:
            raise ValidationError("Se requiere el nombre para generar el código")
        
        # Tomar las primeras letras de cada palabra
        palabras = self.nombre.upper().split()
        codigo_base = ''.join(palabra[0] for palabra in palabras if palabra.isalpha())
        
        # Si el código es muy corto, usar las primeras 3 letras del nombre
        if len(codigo_base) < 2:
            codigo_base = self.nombre.upper().replace(' ', '')[:3]
        
        # Añadir número secuencial si es necesario
        codigo = codigo_base
        contador = 1
        
        while self._codigo_exists(codigo):
            codigo = f"{codigo_base}{contador:02d}"
            contador += 1
        
        self.codigo_parroquia = codigo
        return codigo
    
    def _codigo_exists(self, codigo: str) -> bool:
        """
        Verifica si un código de parroquia ya existe.
        
        Args:
            codigo: Código a verificar
            
        Returns:
            bool: True si existe
        """
        try:
            result = self._sp_manager.executor.execute(
                'parroquias',
                'existe_codigo',
                {
                    'codigo_parroquia': codigo,
                    'excluir_id': self.id_parroquia
                }
            )
            return result.get('existe', False)
        except Exception:
            return False
    
    def actualizar_estadisticas(self) -> None:
        """Actualiza las estadísticas de la parroquia."""
        try:
            result = self._sp_manager.executor.execute(
                'parroquias',
                'obtener_estadisticas',
                {'id_parroquia': self.id_parroquia}
            )
            
            if result.get('success') and result.get('data'):
                stats = result['data']
                self.numero_catequistas = stats.get('numero_catequistas', 0)
                self.numero_grupos = stats.get('numero_grupos', 0)
                self.numero_catequizandos = stats.get('numero_catequizandos', 0)
                
                logger.debug(f"Estadísticas actualizadas para parroquia {self.nombre}")
        
        except Exception as e:
            logger.error(f"Error actualizando estadísticas de parroquia {self.id_parroquia}: {str(e)}")
    
    def obtener_grupos_activos(self) -> List[Dict[str, Any]]:
        """
        Obtiene los grupos activos de la parroquia.
        
        Returns:
            List: Lista de grupos activos
        """
        try:
            result = self._sp_manager.grupos.obtener_grupos_por_parroquia(self.id_parroquia)
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
        
        except Exception as e:
            logger.error(f"Error obteniendo grupos de parroquia {self.id_parroquia}: {str(e)}")
            return []
    
    def obtener_catequistas(self) -> List[Dict[str, Any]]:
        """
        Obtiene los catequistas de la parroquia.
        
        Returns:
            List: Lista de catequistas
        """
        try:
            result = self._sp_manager.catequistas.obtener_catequistas_por_parroquia(self.id_parroquia)
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
        
        except Exception as e:
            logger.error(f"Error obteniendo catequistas de parroquia {self.id_parroquia}: {str(e)}")
            return []
    
    def obtener_inscripciones_periodo(
        self,
        fecha_inicio: date,
        fecha_fin: date
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las inscripciones de un período específico.
        
        Args:
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            
        Returns:
            List: Lista de inscripciones
        """
        try:
            result = self._sp_manager.reportes.reporte_inscripciones_por_periodo(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                id_parroquia=self.id_parroquia
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
        
        except Exception as e:
            logger.error(f"Error obteniendo inscripciones de parroquia {self.id_parroquia}: {str(e)}")
            return []
    
    def activar(self) -> None:
        """Activa la parroquia."""
        self.estado = EstadoParroquia.ACTIVA
        logger.info(f"Parroquia {self.nombre} activada")
    
    def desactivar(self) -> None:
        """Desactiva la parroquia."""
        self.estado = EstadoParroquia.INACTIVA
        logger.info(f"Parroquia {self.nombre} desactivada")
    
    def suspender(self) -> None:
        """Suspende la parroquia temporalmente."""
        self.estado = EstadoParroquia.SUSPENDIDA
        logger.info(f"Parroquia {self.nombre} suspendida")
    
    def configurar_horarios_misa(self, horarios: Dict[str, List[str]]) -> None:
        """
        Configura los horarios de misa.
        
        Args:
            horarios: Diccionario con día de la semana y lista de horarios
        """
        horarios_formateados = []
        
        dias_semana = {
            'lunes': 'Lunes',
            'martes': 'Martes',
            'miércoles': 'Miércoles',
            'jueves': 'Jueves',
            'viernes': 'Viernes',
            'sábado': 'Sábado',
            'domingo': 'Domingo'
        }
        
        for dia, horas in horarios.items():
            dia_nombre = dias_semana.get(dia.lower(), dia)
            if horas:
                horas_str = ', '.join(horas)
                horarios_formateados.append(f"{dia_nombre}: {horas_str}")
        
        self.horarios_misa = ' | '.join(horarios_formateados)
    
    def configurar_horarios_catequesis(self, horarios: Dict[str, List[str]]) -> None:
        """
        Configura los horarios de catequesis.
        
        Args:
            horarios: Diccionario con día de la semana y lista de horarios
        """
        horarios_formateados = []
        
        dias_semana = {
            'lunes': 'Lunes',
            'martes': 'Martes',
            'miércoles': 'Miércoles',
            'jueves': 'Jueves',
            'viernes': 'Viernes',
            'sábado': 'Sábado',
            'domingo': 'Domingo'
        }
        
        for dia, horas in horarios.items():
            dia_nombre = dias_semana.get(dia.lower(), dia)
            if horas:
                horas_str = ', '.join(horas)
                horarios_formateados.append(f"{dia_nombre}: {horas_str}")
        
        self.horarios_catequesis = ' | '.join(horarios_formateados)
    
    def agregar_servicio(self, servicio: str) -> None:
        """
        Agrega un servicio disponible.
        
        Args:
            servicio: Nombre del servicio
        """
        if servicio not in self.servicios_disponibles:
            self.servicios_disponibles.append(servicio)
    
    def remover_servicio(self, servicio: str) -> None:
        """
        Remueve un servicio disponible.
        
        Args:
            servicio: Nombre del servicio
        """
        if servicio in self.servicios_disponibles:
            self.servicios_disponibles.remove(servicio)
    
    def actualizar_configuracion(self, config: Dict[str, Any]) -> None:
        """
        Actualiza la configuración de la parroquia.
        
        Args:
            config: Diccionario con configuraciones
        """
        self.configuracion.update(config)
    
    def obtener_configuracion(self, clave: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración.
        
        Args:
            clave: Clave de configuración
            default: Valor por defecto
            
        Returns:
            Any: Valor de configuración
        """
        return self.configuracion.get(clave, default)
    
    def to_dict(self, include_audit: bool = False) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario.
        
        Args:
            include_audit: Si incluir información de auditoría
            
        Returns:
            dict: Datos del modelo
        """
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_parroquia'] = self.tipo_parroquia.value
        data['estado'] = self.estado.value
        
        return data
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['Parroquia']:
        """
        Busca una parroquia por código.
        
        Args:
            codigo: Código de la parroquia
            
        Returns:
            Parroquia: La parroquia encontrada o None
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'parroquias',
                'obtener_por_codigo',
                {'codigo_parroquia': codigo}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando parroquia por código {codigo}: {str(e)}")
            return None
    
    @classmethod
    def find_by_diocesis(cls, diocesis: str) -> List['Parroquia']:
        """
        Busca parroquias por diócesis.
        
        Args:
            diocesis: Nombre de la diócesis
            
        Returns:
            List: Lista de parroquias de la diócesis
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'parroquias',
                'obtener_por_diocesis',
                {'diocesis': diocesis}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando parroquias por diócesis {diocesis}: {str(e)}")
            return []
    
    @classmethod
    def find_activas(cls) -> List['Parroquia']:
        """
        Busca todas las parroquias activas.
        
        Returns:
            List: Lista de parroquias activas
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'parroquias',
                'obtener_activas',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando parroquias activas: {str(e)}")
            return []
    
    @classmethod
    def find_by_ciudad(cls, ciudad: str) -> List['Parroquia']:
        """
        Busca parroquias por ciudad.
        
        Args:
            ciudad: Nombre de la ciudad
            
        Returns:
            List: Lista de parroquias en la ciudad
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'parroquias',
                'obtener_por_ciudad',
                {'ciudad': ciudad}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando parroquias por ciudad {ciudad}: {str(e)}")
            return []
    
    @classmethod
    def obtener_estadisticas_generales(cls) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de todas las parroquias.
        
        Returns:
            dict: Estadísticas generales
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'parroquias',
                'estadisticas_generales',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            
            return {
                'total_parroquias': 0,
                'parroquias_activas': 0,
                'parroquias_inactivas': 0,
                'total_catequizandos': 0,
                'total_catequistas': 0,
                'total_grupos': 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas generales: {str(e)}")
            return {}
    
    @classmethod
    def generar_reporte_ocupacion(cls) -> List[Dict[str, Any]]:
        """
        Genera un reporte de ocupación de todas las parroquias.
        
        Returns:
            List: Lista con datos de ocupación por parroquia
        """
        try:
            parroquias = cls.find_activas()
            reporte = []
            
            for parroquia in parroquias:
                parroquia.actualizar_estadisticas()
                
                ocupacion_data = {
                    'id_parroquia': parroquia.id_parroquia,
                    'nombre': parroquia.nombre,
                    'capacidad_maxima': parroquia.capacidad_maxima,
                    'catequizandos_inscritos': parroquia.numero_catequizandos,
                    'porcentaje_ocupacion': parroquia.ocupacion_porcentual,
                    'puede_inscribir': parroquia.puede_inscribir,
                    'numero_grupos': parroquia.numero_grupos,
                    'numero_catequistas': parroquia.numero_catequistas
                }
                
                reporte.append(ocupacion_data)
            
            # Ordenar por porcentaje de ocupación descendente
            reporte.sort(key=lambda x: x['porcentaje_ocupacion'], reverse=True)
            
            return reporte
            
        except Exception as e:
            logger.error(f"Error generando reporte de ocupación: {str(e)}")
            return []
    
    def save(self, usuario: str = None) -> 'Parroquia':
        """
        Guarda la parroquia con validaciones adicionales.
        
        Args:
            usuario: Usuario que realiza la operación
            
        Returns:
            Parroquia: La parroquia guardada
        """
        # Generar código si no existe
        if not self.codigo_parroquia:
            self.generar_codigo_parroquia()
        
        # Guardar usando el método padre
        result = super().save(usuario)
        
        # Actualizar estadísticas después de guardar
        if not self.is_new:
            self.actualizar_estadisticas()
        
        return result


# Funciones de utilidad para trabajar con parroquias
class ParroquiaManager:
    """Manager para operaciones avanzadas con parroquias."""
    
    @staticmethod
    def crear_parroquia_completa(
        nombre: str,
        direccion: str,
        telefono: str = None,
        email: str = None,
        parroco: str = None,
        diocesis: str = None,
        usuario_creador: str = None
    ) -> Parroquia:
        """
        Crea una parroquia con información completa.
        
        Args:
            nombre: Nombre de la parroquia
            direccion: Dirección
            telefono: Teléfono (opcional)
            email: Email (opcional)
            parroco: Nombre del párroco (opcional)
            diocesis: Diócesis (opcional)
            usuario_creador: Usuario que crea la parroquia
            
        Returns:
            Parroquia: La parroquia creada
        """
        parroquia = Parroquia(
            nombre=nombre,
            direccion=direccion,
            telefono=telefono,
            email=email,
            parroco=parroco,
            diocesis=diocesis
        )
        
        # Configuraciones por defecto
        parroquia.configuracion = {
            'permite_inscripciones_online': True,
            'requiere_pago_inscripcion': True,
            'monto_inscripcion': 0.0,
            'edad_minima_catequesis': 7,
            'edad_maxima_catequesis': 16,
            'duracion_catequesis_anos': 3,
            'certificacion_automatica': False
        }
        
        # Servicios básicos por defecto
        parroquia.servicios_disponibles = [
            'Catequesis de Primera Comunión',
            'Catequesis de Confirmación',
            'Misa Dominical',
            'Confesiones'
        ]
        
        return parroquia.save(usuario_creador)
    
    @staticmethod
    def transferir_catequizandos(
        parroquia_origen_id: int,
        parroquia_destino_id: int,
        catequizandos_ids: List[int],
        usuario: str = None
    ) -> Dict[str, Any]:
        """
        Transfiere catequizandos entre parroquias.
        
        Args:
            parroquia_origen_id: ID de la parroquia origen
            parroquia_destino_id: ID de la parroquia destino
            catequizandos_ids: Lista de IDs de catequizandos
            usuario: Usuario que realiza la transferencia
            
        Returns:
            dict: Resultado de la transferencia
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'parroquias',
                'transferir_catequizandos',
                {
                    'parroquia_origen': parroquia_origen_id,
                    'parroquia_destino': parroquia_destino_id,
                    'catequizandos': catequizandos_ids,
                    'usuario': usuario
                }
            )
            
            if result.get('success'):
                # Actualizar estadísticas de ambas parroquias
                parroquia_origen = Parroquia.find_by_id(parroquia_origen_id)
                parroquia_destino = Parroquia.find_by_id(parroquia_destino_id)
                
                if parroquia_origen:
                    parroquia_origen.actualizar_estadisticas()
                if parroquia_destino:
                    parroquia_destino.actualizar_estadisticas()
                
                logger.info(f"Transferencia exitosa de {len(catequizandos_ids)} catequizandos")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en transferencia de catequizandos: {str(e)}")
            return {
                'success': False,
                'message': f"Error en la transferencia: {str(e)}"
            }
    
    @staticmethod
    def consolidar_estadisticas() -> None:
        """Consolida las estadísticas de todas las parroquias."""
        try:
            parroquias = Parroquia.find_all()
            
            for parroquia in parroquias:
                parroquia.actualizar_estadisticas()
                parroquia.save()
            
            logger.info(f"Estadísticas consolidadas para {len(parroquias)} parroquias")
            
        except Exception as e:
            logger.error(f"Error consolidando estadísticas: {str(e)}")
    
    @staticmethod
    def generar_reporte_comparativo(
        fecha_inicio: date,
        fecha_fin: date
    ) -> Dict[str, Any]:
        """
        Genera un reporte comparativo entre parroquias.
        
        Args:
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            
        Returns:
            dict: Reporte comparativo
        """
        try:
            parroquias = Parroquia.find_activas()
            reporte = {
                'periodo': {
                    'inicio': fecha_inicio.isoformat(),
                    'fin': fecha_fin.isoformat()
                },
                'resumen_general': {
                    'total_parroquias': len(parroquias),
                    'total_catequizandos': 0,
                    'total_grupos': 0,
                    'total_catequistas': 0
                },
                'parroquias': []
            }
            
            for parroquia in parroquias:
                parroquia.actualizar_estadisticas()
                
                # Obtener inscripciones del período
                inscripciones = parroquia.obtener_inscripciones_periodo(
                    fecha_inicio, fecha_fin
                )
                
                parroquia_data = {
                    'id_parroquia': parroquia.id_parroquia,
                    'nombre': parroquia.nombre,
                    'estadisticas_actuales': {
                        'catequizandos': parroquia.numero_catequizandos,
                        'grupos': parroquia.numero_grupos,
                        'catequistas': parroquia.numero_catequistas,
                        'ocupacion_porcentual': parroquia.ocupacion_porcentual
                    },
                    'inscripciones_periodo': len(inscripciones),
                    'puede_inscribir': parroquia.puede_inscribir
                }
                
                reporte['parroquias'].append(parroquia_data)
                
                # Actualizar totales
                reporte['resumen_general']['total_catequizandos'] += parroquia.numero_catequizandos
                reporte['resumen_general']['total_grupos'] += parroquia.numero_grupos
                reporte['resumen_general']['total_catequistas'] += parroquia.numero_catequistas
            
            # Ordenar por número de catequizandos
            reporte['parroquias'].sort(
                key=lambda x: x['estadisticas_actuales']['catequizandos'],
                reverse=True
            )
            
            return reporte
            
        except Exception as e:
            logger.error(f"Error generando reporte comparativo: {str(e)}")
            return {}


# Registrar el modelo en la factory
ModelFactory.register('parroquia', Parroquia)