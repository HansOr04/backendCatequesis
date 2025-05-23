"""
Modelo de Representante para el sistema de catequesis.
Maneja la información de los representantes/acudientes de los catequizandos.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class TipoRepresentante(Enum):
    """Tipos de representante."""
    PADRE = "padre"
    MADRE = "madre"
    ABUELO = "abuelo"
    ABUELA = "abuela"
    TIO = "tio"
    TIA = "tia"
    HERMANO = "hermano"
    HERMANA = "hermana"
    TUTOR_LEGAL = "tutor_legal"
    ACUDIENTE = "acudiente"
    OTRO_FAMILIAR = "otro_familiar"
    NO_FAMILIAR = "no_familiar"


class TipoDocumentoRep(Enum):
    """Tipos de documento para representantes."""
    CEDULA = "cedula"
    CEDULA_EXTRANJERIA = "cedula_extranjeria"
    PASAPORTE = "pasaporte"
    TARJETA_IDENTIDAD = "tarjeta_identidad"


class EstadoRepresentante(Enum):
    """Estados del representante."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"


class EstadoCivilRep(Enum):
    """Estados civiles del representante."""
    SOLTERO = "soltero"
    CASADO = "casado"
    UNION_LIBRE = "union_libre"
    VIUDO = "viudo"
    DIVORCIADO = "divorciado"
    SEPARADO = "separado"


class NivelEducativo(Enum):
    """Niveles educativos."""
    PRIMARIA_INCOMPLETA = "primaria_incompleta"
    PRIMARIA_COMPLETA = "primaria_completa"
    SECUNDARIA_INCOMPLETA = "secundaria_incompleta"
    SECUNDARIA_COMPLETA = "secundaria_completa"
    TECNICO = "tecnico"
    TECNOLOGICO = "tecnologico"
    UNIVERSITARIO_INCOMPLETO = "universitario_incompleto"
    UNIVERSITARIO_COMPLETO = "universitario_completo"
    POSTGRADO = "postgrado"
    SIN_ESTUDIOS = "sin_estudios"


class Representante(BaseModel):
    """
    Modelo de Representante del sistema de catequesis.
    Maneja la información de padres, acudientes y representantes de los catequizandos.
    """
    
    # Configuración del modelo
    _table_schema = "representantes"
    _primary_key = "id_representante"
    _required_fields = ["nombres", "apellidos", "tipo_representante"]
    _unique_fields = ["documento_identidad"]
    _searchable_fields = [
        "nombres", "apellidos", "documento_identidad", 
        "telefono", "email", "ocupacion"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Representante."""
        # Identificación básica
        self.id_representante: Optional[int] = None
        self.nombres: str = ""
        self.apellidos: str = ""
        self.fecha_nacimiento: Optional[date] = None
        self.lugar_nacimiento: Optional[str] = None
        self.estado: EstadoRepresentante = EstadoRepresentante.ACTIVO
        
        # Tipo de representante
        self.tipo_representante: TipoRepresentante = TipoRepresentante.ACUDIENTE
        self.es_representante_principal: bool = False
        self.es_contacto_emergencia: bool = False
        self.prioridad_contacto: int = 1
        
        # Documentación
        self.tipo_documento: TipoDocumentoRep = TipoDocumentoRep.CEDULA
        self.documento_identidad: Optional[str] = None
        self.fecha_expedicion: Optional[date] = None
        self.lugar_expedicion: Optional[str] = None
        
        # Información de contacto
        self.direccion: Optional[str] = None
        self.barrio: Optional[str] = None
        self.ciudad: Optional[str] = None
        self.departamento: Optional[str] = None
        self.telefono_principal: Optional[str] = None
        self.telefono_secundario: Optional[str] = None
        self.telefono_trabajo: Optional[str] = None
        self.email: Optional[str] = None
        self.email_alternativo: Optional[str] = None
        
        # Información personal
        self.estado_civil: EstadoCivilRep = EstadoCivilRep.SOLTERO
        self.nivel_educativo: NivelEducativo = NivelEducativo.SECUNDARIA_COMPLETA
        self.ocupacion: Optional[str] = None
        self.empresa: Optional[str] = None
        self.cargo: Optional[str] = None
        self.direccion_trabajo: Optional[str] = None
        self.telefono_empresa: Optional[str] = None
        
        # Información económica
        self.nivel_ingresos: Optional[str] = None
        self.tipo_vivienda: Optional[str] = None
        self.personas_a_cargo: int = 0
        
        # Información sacramental y religiosa
        self.es_catolico: bool = True
        self.parroquia_pertenece: Optional[str] = None
        self.fecha_bautismo: Optional[date] = None
        self.fecha_matrimonio_religioso: Optional[date] = None
        self.participa_actividades_parroquiales: bool = False
        self.actividades_que_participa: List[str] = []
        
        # Autorización y permisos
        self.autoriza_recoger_menor: bool = True
        self.autoriza_emergencia_medica: bool = True
        self.autoriza_actividades_especiales: bool = True
        self.autoriza_transporte: bool = False
        self.autoriza_comunicaciones: bool = True
        self.autoriza_fotos: bool = True
        
        # Observaciones y notas
        self.observaciones: Optional[str] = None
        self.restricciones: Optional[str] = None
        self.notas_importantes: Optional[str] = None
        
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
        return self.estado == EstadoRepresentante.ACTIVO
    
    @property
    def contacto_principal(self) -> Optional[str]:
        """Obtiene el contacto principal."""
        return self.telefono_principal or self.email
    
    @property
    def informacion_contacto(self) -> Dict[str, str]:
        """Obtiene toda la información de contacto."""
        contacto = {}
        
        if self.telefono_principal:
            contacto['telefono_principal'] = self.telefono_principal
        if self.telefono_secundario:
            contacto['telefono_secundario'] = self.telefono_secundario
        if self.telefono_trabajo:
            contacto['telefono_trabajo'] = self.telefono_trabajo
        if self.email:
            contacto['email'] = self.email
        if self.email_alternativo:
            contacto['email_alternativo'] = self.email_alternativo
        
        return contacto
    
    @property
    def direccion_completa(self) -> str:
        """Obtiene la dirección completa."""
        direccion_parts = []
        
        if self.direccion:
            direccion_parts.append(self.direccion)
        if self.barrio:
            direccion_parts.append(f"Barrio {self.barrio}")
        if self.ciudad:
            direccion_parts.append(self.ciudad)
        if self.departamento:
            direccion_parts.append(self.departamento)
        
        return ", ".join(direccion_parts)
    
    @property
    def descripcion_parentesco(self) -> str:
        """Obtiene la descripción del parentesco."""
        descripciones = {
            TipoRepresentante.PADRE: "Padre",
            TipoRepresentante.MADRE: "Madre",
            TipoRepresentante.ABUELO: "Abuelo",
            TipoRepresentante.ABUELA: "Abuela",
            TipoRepresentante.TIO: "Tío",
            TipoRepresentante.TIA: "Tía",
            TipoRepresentante.HERMANO: "Hermano",
            TipoRepresentante.HERMANA: "Hermana",
            TipoRepresentante.TUTOR_LEGAL: "Tutor Legal",
            TipoRepresentante.ACUDIENTE: "Acudiente",
            TipoRepresentante.OTRO_FAMILIAR: "Otro Familiar",
            TipoRepresentante.NO_FAMILIAR: "No Familiar"
        }
        return descripciones.get(self.tipo_representante, "No especificado")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Representante."""
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
                if edad < 18:
                    raise ValidationError("Los representantes deben ser mayores de edad")
                if edad > 100:
                    raise ValidationError("La edad máxima es 100 años")
        
        # Validar documento de identidad
        if self.documento_identidad:
            if self.tipo_documento == TipoDocumentoRep.CEDULA:
                if not DataValidator.validate_cedula(self.documento_identidad):
                    raise ValidationError("El número de cédula no es válido")
        
        # Validar teléfonos
        if self.telefono_principal and not DataValidator.validate_phone(self.telefono_principal):
            raise ValidationError("El formato del teléfono principal no es válido")
        
        if self.telefono_secundario and not DataValidator.validate_phone(self.telefono_secundario):
            raise ValidationError("El formato del teléfono secundario no es válido")
        
        if self.telefono_trabajo and not DataValidator.validate_phone(self.telefono_trabajo):
            raise ValidationError("El formato del teléfono de trabajo no es válido")
        
        # Validar emails
        if self.email and not DataValidator.validate_email(self.email):
            raise ValidationError("El formato del email no es válido")
        
        if self.email_alternativo and not DataValidator.validate_email(self.email_alternativo):
            raise ValidationError("El formato del email alternativo no es válido")
        
        # Validar prioridad de contacto
        if self.prioridad_contacto < 1 or self.prioridad_contacto > 10:
            raise ValidationError("La prioridad de contacto debe estar entre 1 y 10")
        
        # Validar personas a cargo
        if self.personas_a_cargo < 0 or self.personas_a_cargo > 20:
            raise ValidationError("El número de personas a cargo debe estar entre 0 y 20")
        
        # Validar que tenga al menos un medio de contacto
        if not any([self.telefono_principal, self.telefono_secundario, self.email]):
            raise ValidationError("Debe tener al menos un teléfono o email de contacto")
        
        # Validar enums
        if isinstance(self.tipo_representante, str):
            try:
                self.tipo_representante = TipoRepresentante(self.tipo_representante)
            except ValueError:
                raise ValidationError(f"Tipo de representante '{self.tipo_representante}' no válido")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoRepresentante(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.tipo_documento, str):
            try:
                self.tipo_documento = TipoDocumentoRep(self.tipo_documento)
            except ValueError:
                raise ValidationError(f"Tipo de documento '{self.tipo_documento}' no válido")
        
        if isinstance(self.estado_civil, str):
            try:
                self.estado_civil = EstadoCivilRep(self.estado_civil)
            except ValueError:
                raise ValidationError(f"Estado civil '{self.estado_civil}' no válido")
        
        if isinstance(self.nivel_educativo, str):
            try:
                self.nivel_educativo = NivelEducativo(self.nivel_educativo)
            except ValueError:
                raise ValidationError(f"Nivel educativo '{self.nivel_educativo}' no válido")
    
    def obtener_catequizandos_representados(self) -> List[Dict[str, Any]]:
        """
        Obtiene los catequizandos que representa.
        
        Returns:
            List: Lista de catequizandos representados
        """
        try:
            result = self._sp_manager.executor.execute(
                'representantes',
                'obtener_catequizandos_representados',
                {'id_representante': self.id_representante}
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo catequizandos representados: {str(e)}")
            return []
    
    def agregar_actividad_parroquial(self, actividad: str) -> None:
        """
        Agrega una actividad parroquial en la que participa.
        
        Args:
            actividad: Nombre de la actividad
        """
        if actividad and actividad not in self.actividades_que_participa:
            self.actividades_que_participa.append(actividad)
            self.participa_actividades_parroquiales = True
    
    def remover_actividad_parroquial(self, actividad: str) -> None:
        """
        Remueve una actividad parroquial.
        
        Args:
            actividad: Nombre de la actividad
        """
        if actividad in self.actividades_que_participa:
            self.actividades_que_participa.remove(actividad)
            
            # Si no quedan actividades, marcar como no participante
            if not self.actividades_que_participa:
                self.participa_actividades_parroquiales = False
    
    def establecer_como_principal(self) -> None:
        """Establece este representante como principal."""
        self.es_representante_principal = True
        self.prioridad_contacto = 1
        
        logger.info(f"Representante {self.nombre_completo} establecido como principal")
    
    def establecer_como_contacto_emergencia(self) -> None:
        """Establece como contacto de emergencia."""
        self.es_contacto_emergencia = True
        
        # Validar que tenga autorización médica
        if not self.autoriza_emergencia_medica:
            raise ValidationError("El contacto de emergencia debe autorizar emergencias médicas")
        
        logger.info(f"Representante {self.nombre_completo} establecido como contacto de emergencia")
    
    def actualizar_autorizaciones(self, autorizaciones: Dict[str, bool]) -> None:
        """
        Actualiza las autorizaciones del representante.
        
        Args:
            autorizaciones: Diccionario con las autorizaciones
        """
        autorizaciones_validas = {
            'autoriza_recoger_menor',
            'autoriza_emergencia_medica',
            'autoriza_actividades_especiales',
            'autoriza_transporte',
            'autoriza_comunicaciones',
            'autoriza_fotos'
        }
        
        for key, value in autorizaciones.items():
            if key in autorizaciones_validas:
                setattr(self, key, bool(value))
        
        logger.debug(f"Autorizaciones actualizadas para {self.nombre_completo}")
    
    def verificar_autorizacion(self, tipo_autorizacion: str) -> bool:
        """
        Verifica si tiene una autorización específica.
        
        Args:
            tipo_autorizacion: Tipo de autorización a verificar
            
        Returns:
            bool: True si tiene la autorización
        """
        return getattr(self, f"autoriza_{tipo_autorizacion}", False)
    
    def obtener_resumen_contacto(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de la información de contacto.
        
        Returns:
            dict: Resumen de contacto
        """
        return {
            'nombre_completo': self.nombre_completo,
            'parentesco': self.descripcion_parentesco,
            'es_principal': self.es_representante_principal,
            'es_emergencia': self.es_contacto_emergencia,
            'prioridad': self.prioridad_contacto,
            'telefono_principal': self.telefono_principal,
            'telefono_secundario': self.telefono_secundario,
            'email': self.email,
            'autoriza_recoger': self.autoriza_recoger_menor,
            'autoriza_emergencia': self.autoriza_emergencia_medica,
            'activo': self.esta_activo
        }
    
    def activar(self) -> None:
        """Activa el representante."""
        self.estado = EstadoRepresentante.ACTIVO
        logger.info(f"Representante {self.nombre_completo} activado")
    
    def desactivar(self) -> None:
        """Desactiva el representante."""
        self.estado = EstadoRepresentante.INACTIVO
        logger.info(f"Representante {self.nombre_completo} desactivado")
    
    def suspender(self, motivo: str = None) -> None:
        """
        Suspende el representante.
        
        Args:
            motivo: Motivo de la suspensión
        """
        self.estado = EstadoRepresentante.SUSPENDIDO
        if motivo:
            self.observaciones = f"Suspendido: {motivo}"
        
        logger.info(f"Representante {self.nombre_completo} suspendido")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario.
        
        Args:
            include_audit: Si incluir información de auditoría
            include_sensitive: Si incluir datos sensibles
            
        Returns:
            dict: Datos del modelo
        """
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_representante'] = self.tipo_representante.value
        data['estado'] = self.estado.value
        data['tipo_documento'] = self.tipo_documento.value
        data['estado_civil'] = self.estado_civil.value
        data['nivel_educativo'] = self.nivel_educativo.value
        
        # Agregar edad calculada
        data['edad'] = self.edad
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'documento_identidad', 'telefono_principal', 'telefono_secundario',
                'telefono_trabajo', 'email', 'email_alternativo', 'direccion',
                'direccion_trabajo', 'nivel_ingresos'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_documento(cls, documento: str) -> Optional['Representante']:
        """
        Busca un representante por documento.
        
        Args:
            documento: Número de documento
            
        Returns:
            Representante: El representante encontrado o None
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'representantes',
                'buscar_por_documento',
                {'documento_identidad': documento}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando representante por documento {documento}: {str(e)}")
            return None
    
    @classmethod
    def find_by_catequizando(cls, id_catequizando: int) -> List['Representante']:
        """
        Busca representantes de un catequizando específico.
        
        Args:
            id_catequizando: ID del catequizando
            
        Returns:
            List: Lista de representantes
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'representantes',
                'obtener_por_catequizando',
                {'id_catequizando': id_catequizando}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando representantes del catequizando {id_catequizando}: {str(e)}")
            return []
    
    @classmethod
    def find_principales(cls) -> List['Representante']:
        """
        Busca todos los representantes principales.
        
        Returns:
            List: Lista de representantes principales
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'representantes',
                'obtener_principales',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando representantes principales: {str(e)}")
            return []
    
    @classmethod
    def find_contactos_emergencia(cls) -> List['Representante']:
        """
        Busca todos los contactos de emergencia.
        
        Returns:
            List: Lista de contactos de emergencia
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'representantes',
                'obtener_contactos_emergencia',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando contactos de emergencia: {str(e)}")
            return []


class RepresentanteManager:
    """Manager para operaciones avanzadas con representantes."""
    
    @staticmethod
    def crear_representante_completo(
        nombres: str,
        apellidos: str,
        tipo_representante: TipoRepresentante,
        documento_identidad: str,
        telefono_principal: str,
        email: str = None,
        direccion: str = None,
        es_principal: bool = False,
        usuario_creador: str = None
    ) -> 'Representante':
        """
        Crea un representante con información básica completa.
        
        Args:
            nombres: Nombres del representante
            apellidos: Apellidos del representante
            tipo_representante: Tipo de representante
            documento_identidad: Documento de identidad
            telefono_principal: Teléfono principal
            email: Email (opcional)
            direccion: Dirección (opcional)
            es_principal: Si es representante principal
            usuario_creador: Usuario que crea el representante
            
        Returns:
            Representante: El representante creado
        """
        representante = Representante(
            nombres=nombres,
            apellidos=apellidos,
            tipo_representante=tipo_representante,
            documento_identidad=documento_identidad,
            telefono_principal=telefono_principal,
            email=email,
            direccion=direccion,
            es_representante_principal=es_principal,
            es_contacto_emergencia=es_principal
        )
        
        # Autorizaciones por defecto
        representante.autoriza_recoger_menor = True
        representante.autoriza_emergencia_medica = True
        representante.autoriza_actividades_especiales = True
        representante.autoriza_comunicaciones = True
        representante.autoriza_fotos = True
        
        return representante.save(usuario_creador)
    
    @staticmethod
    def vincular_catequizando(
        id_representante: int,
        id_catequizando: int,
        usuario: str = None
    ) -> Dict[str, Any]:
        """
        Vincula un representante con un catequizando.
        
        Args:
            id_representante: ID del representante
            id_catequizando: ID del catequizando
            usuario: Usuario que realiza la vinculación
            
        Returns:
            dict: Resultado de la vinculación
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'representantes',
                'vincular_catequizando',
                {
                    'id_representante': id_representante,
                    'id_catequizando': id_catequizando,
                    'usuario': usuario
                }
            )
            
            if result.get('success'):
                logger.info(f"Representante {id_representante} vinculado con catequizando {id_catequizando}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error vinculando representante: {str(e)}")
            return {
                'success': False,
                'message': f"Error en la vinculación: {str(e)}"
            }
    
    @staticmethod
    def desvincular_catequizando(
        id_representante: int,
        id_catequizando: int,
        usuario: str = None
    ) -> Dict[str, Any]:
        """
        Desvincula un representante de un catequizando.
        
        Args:
            id_representante: ID del representante
            id_catequizando: ID del catequizando
            usuario: Usuario que realiza la desvinculación
            
        Returns:
            dict: Resultado de la desvinculación
        """
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'representantes',
                'desvincular_catequizando',
                {
                    'id_representante': id_representante,
                    'id_catequizando': id_catequizando,
                    'usuario': usuario
                }
            )
            
            if result.get('success'):
                logger.info(f"Representante {id_representante} desvinculado de catequizando {id_catequizando}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error desvinculando representante: {str(e)}")
            return {
                'success': False,
                'message': f"Error en la desvinculación: {str(e)}"
            }
    
    @staticmethod
    def generar_reporte_contactos_emergencia(id_parroquia: int = None) -> Dict[str, Any]:
        """
        Genera un reporte de contactos de emergencia.
        
        Args:
            id_parroquia: ID de la parroquia (opcional, si no se especifica se incluyen todas)
            
        Returns:
            dict: Reporte de contactos de emergencia
        """
        try:
            sp_manager = get_sp_manager()
            
            # Obtener contactos de emergencia
            if id_parroquia:
                # Filtrar por parroquia a través de los catequizandos
                result = sp_manager.executor.execute(
                    'representantes',
                    'obtener_contactos_emergencia_por_parroquia',
                    {'id_parroquia': id_parroquia}
                )
            else:
                result = sp_manager.executor.execute(
                    'representantes',
                    'obtener_contactos_emergencia',
                    {}
                )
            
            if result.get('success') and result.get('data'):
                contactos = result['data']
                
                # Generar estadísticas
                total_contactos = len(contactos)
                por_tipo = {}
                sin_telefono = 0
                sin_autorizacion_medica = 0
                
                for contacto in contactos:
                    tipo = contacto.get('tipo_representante', 'no_especificado')
                    por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
                    
                    if not contacto.get('telefono_principal'):
                        sin_telefono += 1
                    
                    if not contacto.get('autoriza_emergencia_medica'):
                        sin_autorizacion_medica += 1
                
                return {
                    'total_contactos': total_contactos,
                    'distribucion_por_tipo': por_tipo,
                    'sin_telefono': sin_telefono,
                    'sin_autorizacion_medica': sin_autorizacion_medica,
                    'contactos': contactos,
                    'fecha_generacion': date.today().isoformat()
                }
            
            return {
                'total_contactos': 0,
                'distribucion_por_tipo': {},
                'sin_telefono': 0,
                'sin_autorizacion_medica': 0,
                'contactos': [],
                'fecha_generacion': date.today().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de contactos de emergencia: {str(e)}")
            return {
                'error': str(e),
                'fecha_generacion': date.today().isoformat()
            }
    
    @staticmethod
    def validar_autorizaciones_masivas(
        representantes_ids: List[int],
        autorizaciones_requeridas: List[str]
    ) -> Dict[str, Any]:
        """
        Valida autorizaciones masivas para múltiples representantes.
        
        Args:
            representantes_ids: Lista de IDs de representantes
            autorizaciones_requeridas: Lista de autorizaciones requeridas
            
        Returns:
            dict: Resultado de la validación
        """
        try:
            representantes_sin_autorizacion = []
            representantes_validados = []
            
            for id_rep in representantes_ids:
                representante = Representante.find_by_id(id_rep)
                if representante:
                    falta_autorizacion = False
                    autorizaciones_faltantes = []
                    
                    for autorizacion in autorizaciones_requeridas:
                        if not representante.verificar_autorizacion(autorizacion):
                            falta_autorizacion = True
                            autorizaciones_faltantes.append(autorizacion)
                    
                    if falta_autorizacion:
                        representantes_sin_autorizacion.append({
                            'id_representante': id_rep,
                            'nombre_completo': representante.nombre_completo,
                            'autorizaciones_faltantes': autorizaciones_faltantes
                        })
                    else:
                        representantes_validados.append({
                            'id_representante': id_rep,
                            'nombre_completo': representante.nombre_completo
                        })
            
            return {
                'total_validados': len(representantes_validados),
                'total_sin_autorizacion': len(representantes_sin_autorizacion),
                'representantes_validados': representantes_validados,
                'representantes_sin_autorizacion': representantes_sin_autorizacion,
                'todos_autorizados': len(representantes_sin_autorizacion) == 0
            }
            
        except Exception as e:
            logger.error(f"Error validando autorizaciones masivas: {str(e)}")
            return {
                'error': str(e),
                'todos_autorizados': False
            }


# Registrar el modelo en la factory
ModelFactory.register('representante', Representante)