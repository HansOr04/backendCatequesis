"""
Modelo de Asistencia para el sistema de catequesis.
Controla la asistencia de catequizandos a las clases de catequesis.
"""

import logging
from datetime import date, datetime, time
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TipoAsistencia(Enum):
    """Tipos de asistencia."""
    PRESENTE = "presente"
    AUSENTE = "ausente"
    TARDE = "tarde"
    JUSTIFICADA = "justificada"
    RETIRO_TEMPRANO = "retiro_temprano"


class MotivoAusencia(Enum):
    """Motivos de ausencia."""
    ENFERMEDAD = "enfermedad"
    VIAJE = "viaje"
    FAMILIAR = "familiar"
    ACADEMICO = "academico"
    PERSONAL = "personal"
    CLIMA = "clima"
    OTRO = "otro"


class Asistencia(BaseModel):
    """
    Modelo de Asistencia del sistema de catequesis.
    Registra la asistencia de catequizandos a las clases.
    """
    
    # Configuración del modelo
    _table_schema = "asistencias"
    _primary_key = "id_asistencia"
    _required_fields = ["id_catequizando", "id_grupo", "fecha_clase"]
    _unique_fields = []
    _searchable_fields = [
        "nombre_catequizando", "nombre_grupo", "tema_clase"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Asistencia."""
        # Identificación básica
        self.id_asistencia: Optional[int] = None
        self.id_catequizando: int = 0
        self.id_grupo: int = 0
        self.id_inscripcion: Optional[int] = None
        
        # Información de la clase
        self.fecha_clase: Optional[date] = None
        self.hora_inicio: Optional[time] = None
        self.hora_fin: Optional[time] = None
        self.tema_clase: Optional[str] = None
        self.numero_clase: Optional[int] = None
        
        # Asistencia del catequizando
        self.tipo_asistencia: TipoAsistencia = TipoAsistencia.PRESENTE
        self.presente: bool = True
        self.hora_llegada: Optional[time] = None
        self.hora_salida: Optional[time] = None
        self.minutos_tarde: int = 0
        
        # Información de ausencias
        self.motivo_ausencia: Optional[MotivoAusencia] = None
        self.descripcion_motivo: Optional[str] = None
        self.ausencia_justificada: bool = False
        self.justificacion: Optional[str] = None
        self.documento_justificacion: Optional[str] = None
        
        # Control del catequista
        self.registrado_por: Optional[str] = None
        self.fecha_registro: Optional[date] = None
        self.observaciones_catequista: Optional[str] = None
        self.comportamiento: Optional[str] = None
        self.participacion: Optional[str] = None
        
        # Información adicional
        self.actividades_realizadas: List[str] = []
        self.tareas_asignadas: Optional[str] = None
        self.material_entregado: Optional[str] = None
        self.requiere_seguimiento: bool = False
        self.motivo_seguimiento: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_presente(self) -> bool:
        """Verifica si está presente."""
        return self.tipo_asistencia in [TipoAsistencia.PRESENTE, TipoAsistencia.TARDE]
    
    @property
    def llego_tarde(self) -> bool:
        """Verifica si llegó tarde."""
        return self.tipo_asistencia == TipoAsistencia.TARDE or self.minutos_tarde > 0
    
    @property
    def descripcion_asistencia(self) -> str:
        """Obtiene descripción de la asistencia."""
        descripciones = {
            TipoAsistencia.PRESENTE: "Presente",
            TipoAsistencia.AUSENTE: "Ausente",
            TipoAsistencia.TARDE: "Llegó tarde",
            TipoAsistencia.JUSTIFICADA: "Ausencia justificada",
            TipoAsistencia.RETIRO_TEMPRANO: "Retiro temprano"
        }
        return descripciones.get(self.tipo_asistencia, "No definido")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Asistencia."""
        # Validar IDs requeridos
        if self.id_catequizando <= 0:
            raise ValidationError("Debe especificar un catequizando válido")
        
        if self.id_grupo <= 0:
            raise ValidationError("Debe especificar un grupo válido")
        
        # Validar fecha de clase
        if self.fecha_clase and self.fecha_clase > date.today():
            raise ValidationError("La fecha de clase no puede ser futura")
        
        # Validar horarios
        if self.hora_inicio and self.hora_fin:
            if self.hora_fin <= self.hora_inicio:
                raise ValidationError("La hora de fin debe ser posterior al inicio")
        
        # Validar minutos tarde
        if self.minutos_tarde < 0 or self.minutos_tarde > 120:
            raise ValidationError("Los minutos tarde deben estar entre 0 y 120")
        
        # Validar número de clase
        if self.numero_clase is not None and (self.numero_clase < 1 or self.numero_clase > 100):
            raise ValidationError("El número de clase debe estar entre 1 y 100")
        
        # Validar enums
        if isinstance(self.tipo_asistencia, str):
            try:
                self.tipo_asistencia = TipoAsistencia(self.tipo_asistencia)
            except ValueError:
                raise ValidationError(f"Tipo de asistencia '{self.tipo_asistencia}' no válido")
        
        if isinstance(self.motivo_ausencia, str) and self.motivo_ausencia:
            try:
                self.motivo_ausencia = MotivoAusencia(self.motivo_ausencia)
            except ValueError:
                raise ValidationError(f"Motivo de ausencia '{self.motivo_ausencia}' no válido")
        
        # Validar coherencia
        if self.tipo_asistencia == TipoAsistencia.AUSENTE and not self.motivo_ausencia:
            raise ValidationError("Las ausencias requieren especificar el motivo")
        
        if self.ausencia_justificada and not self.justificacion:
            raise ValidationError("Las ausencias justificadas requieren justificación")
    
    def marcar_presente(
        self,
        hora_llegada: time = None,
        catequista: str = None,
        observaciones: str = None
    ) -> None:
        """
        Marca al catequizando como presente.
        
        Args:
            hora_llegada: Hora de llegada
            catequista: Catequista que registra
            observaciones: Observaciones adicionales
        """
        self.tipo_asistencia = TipoAsistencia.PRESENTE
        self.presente = True
        self.hora_llegada = hora_llegada
        self.registrado_por = catequista
        self.fecha_registro = date.today()
        
        if observaciones:
            self.observaciones_catequista = observaciones
        
        # Calcular tardanza
        if self.hora_inicio and hora_llegada and hora_llegada > self.hora_inicio:
            inicio_dt = datetime.combine(date.today(), self.hora_inicio)
            llegada_dt = datetime.combine(date.today(), hora_llegada)
            self.minutos_tarde = int((llegada_dt - inicio_dt).total_seconds() / 60)
            
            if self.minutos_tarde > 10:  # Más de 10 minutos se considera tarde
                self.tipo_asistencia = TipoAsistencia.TARDE
        
        logger.info(f"Asistencia marcada como presente para catequizando {self.id_catequizando}")
    
    def marcar_ausente(
        self,
        motivo: MotivoAusencia,
        descripcion: str = None,
        catequista: str = None
    ) -> None:
        """
        Marca al catequizando como ausente.
        
        Args:
            motivo: Motivo de la ausencia
            descripcion: Descripción del motivo
            catequista: Catequista que registra
        """
        self.tipo_asistencia = TipoAsistencia.AUSENTE
        self.presente = False
        self.motivo_ausencia = motivo
        self.descripcion_motivo = descripcion
        self.registrado_por = catequista
        self.fecha_registro = date.today()
        
        logger.info(f"Asistencia marcada como ausente para catequizando {self.id_catequizando}")
    
    def justificar_ausencia(
        self,
        justificacion: str,
        documento: str = None,
        autorizado_por: str = None
    ) -> None:
        """
        Justifica una ausencia.
        
        Args:
            justificacion: Justificación de la ausencia
            documento: Documento de soporte
            autorizado_por: Quien autoriza la justificación
        """
        if self.tipo_asistencia != TipoAsistencia.AUSENTE:
            raise ValidationError("Solo se pueden justificar ausencias")
        
        self.ausencia_justificada = True
        self.justificacion = justificacion
        self.documento_justificacion = documento
        self.tipo_asistencia = TipoAsistencia.JUSTIFICADA
        
        if autorizado_por:
            self.registrado_por = autorizado_por
        
        logger.info(f"Ausencia justificada para catequizando {self.id_catequizando}")
    
    def registrar_retiro_temprano(
        self,
        hora_salida: time,
        motivo: str,
        catequista: str = None
    ) -> None:
        """
        Registra un retiro temprano.
        
        Args:
            hora_salida: Hora de salida
            motivo: Motivo del retiro
            catequista: Catequista que autoriza
        """
        self.tipo_asistencia = TipoAsistencia.RETIRO_TEMPRANO
        self.hora_salida = hora_salida
        self.descripcion_motivo = motivo
        self.registrado_por = catequista
        
        logger.info(f"Retiro temprano registrado para catequizando {self.id_catequizando}")
    
    def agregar_actividad_realizada(self, actividad: str) -> None:
        """Agrega una actividad realizada en clase."""
        if actividad and actividad not in self.actividades_realizadas:
            self.actividades_realizadas.append(actividad)
    
    def registrar_comportamiento(
        self,
        comportamiento: str,
        participacion: str = None,
        requiere_seguimiento: bool = False,
        motivo_seguimiento: str = None
    ) -> None:
        """
        Registra comportamiento y participación.
        
        Args:
            comportamiento: Descripción del comportamiento
            participacion: Nivel de participación
            requiere_seguimiento: Si requiere seguimiento
            motivo_seguimiento: Motivo del seguimiento
        """
        self.comportamiento = comportamiento
        self.participacion = participacion
        self.requiere_seguimiento = requiere_seguimiento
        
        if requiere_seguimiento and not motivo_seguimiento:
            raise ValidationError("Si requiere seguimiento, debe especificar el motivo")
        
        self.motivo_seguimiento = motivo_seguimiento
    
    def to_dict(self, include_audit: bool = False) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_asistencia'] = self.tipo_asistencia.value
        if self.motivo_ausencia:
            data['motivo_ausencia'] = self.motivo_ausencia.value
        
        # Convertir time a string
        if self.hora_inicio:
            data['hora_inicio'] = self.hora_inicio.strftime('%H:%M')
        if self.hora_fin:
            data['hora_fin'] = self.hora_fin.strftime('%H:%M')
        if self.hora_llegada:
            data['hora_llegada'] = self.hora_llegada.strftime('%H:%M')
        if self.hora_salida:
            data['hora_salida'] = self.hora_salida.strftime('%H:%M')
        
        # Agregar propiedades calculadas
        data['esta_presente'] = self.esta_presente
        data['llego_tarde'] = self.llego_tarde
        data['descripcion_asistencia'] = self.descripcion_asistencia
        
        return data
    
    @classmethod
    def find_by_catequizando(
        cls,
        id_catequizando: int,
        fecha_inicio: date = None,
        fecha_fin: date = None
    ) -> List['Asistencia']:
        """Busca asistencias de un catequizando."""
        try:
            sp_manager = get_sp_manager()
            params = {'id_catequizando': id_catequizando}
            
            if fecha_inicio:
                params['fecha_inicio'] = fecha_inicio
            if fecha_fin:
                params['fecha_fin'] = fecha_fin
            
            result = sp_manager.asistencias.obtener_asistencias_por_catequizando(
                id_catequizando, fecha_inicio, fecha_fin
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando asistencias por catequizando: {str(e)}")
            return []
    
    @classmethod
    def find_by_grupo_fecha(cls, id_grupo: int, fecha_clase: date) -> List['Asistencia']:
        """Busca asistencias de un grupo en una fecha específica."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.asistencias.obtener_asistencias_por_grupo(
                id_grupo, fecha_clase
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando asistencias por grupo y fecha: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Asistencia':
        """Guarda la asistencia con validaciones adicionales."""
        # Establecer fecha de registro si no existe
        if not self.fecha_registro:
            self.fecha_registro = date.today()
        
        # Actualizar estado de presente según tipo
        self.presente = self.esta_presente
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('asistencia', Asistencia)