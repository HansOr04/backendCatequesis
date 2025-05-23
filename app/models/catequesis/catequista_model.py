"""
Modelo de Catequista para el sistema de catequesis.
Representa a los educadores y formadores en la catequesis.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class EstadoCatequista(Enum):
    """Estados del catequista."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    RETIRADO = "retirado"
    EN_FORMACION = "en_formacion"


class NivelFormacion(Enum):
    """Niveles de formación del catequista."""
    INICIAL = "inicial"
    BASICO = "basico"
    INTERMEDIO = "intermedio"
    AVANZADO = "avanzado"
    ESPECIALISTA = "especialista"
    FORMADOR = "formador"


class TipoVinculacion(Enum):
    """Tipos de vinculación del catequista."""
    VOLUNTARIO = "voluntario"
    MEDIO_TIEMPO = "medio_tiempo"
    TIEMPO_COMPLETO = "tiempo_completo"
    COLABORADOR = "colaborador"
    COORDINADOR = "coordinador"


class Especialidad(Enum):
    """Especialidades del catequista."""
    PRIMERA_COMUNION = "primera_comunion"
    CONFIRMACION = "confirmacion"
    CATEQUESIS_FAMILIAR = "catequesis_familiar"
    NECESIDADES_ESPECIALES = "necesidades_especiales"
    JOVENES = "jovenes"
    ADULTOS = "adultos"
    PREPARACION_MATRIMONIAL = "preparacion_matrimonial"
    FORMACION_CATEQUISTAS = "formacion_catequistas"


class Catequista(BaseModel):
    """
    Modelo de Catequista del sistema de catequesis.
    Representa a los educadores y formadores en la catequesis.
    """
    
    # Configuración del modelo
    _table_schema = "catequistas"
    _primary_key = "id_catequista"
    _required_fields = ["nombres", "apellidos", "documento_identidad", "id_parroquia"]
    _unique_fields = ["documento_identidad", "email"]
    _searchable_fields = [
        "nombres", "apellidos", "documento_identidad", 
        "telefono", "email", "especialidades"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Catequista."""
        # Identificación básica
        self.id_catequista: Optional[int] = None
        self.nombres: str = ""
        self.apellidos: str = ""
        self.fecha_nacimiento: Optional[date] = None
        self.lugar_nacimiento: Optional[str] = None
        self.documento_identidad: str = ""
        self.estado: EstadoCatequista = EstadoCatequista.EN_FORMACION
        
        # Vinculación institucional
        self.id_parroquia: int = 0
        self.fecha_vinculacion: Optional[date] = None
        self.fecha_desvinculacion: Optional[date] = None
        self.motivo_desvinculacion: Optional[str] = None
        self.tipo_vinculacion: TipoVinculacion = TipoVinculacion.VOLUNTARIO
        
        # Información de contacto
        self.direccion: Optional[str] = None
        self.barrio: Optional[str] = None
        self.ciudad: Optional[str] = None
        self.departamento: Optional[str] = None
        self.telefono: Optional[str] = None
        self.telefono_alternativo: Optional[str] = None
        self.email: Optional[str] = None
        
        # Información académica y profesional
        self.nivel_educativo: Optional[str] = None
        self.profesion: Optional[str] = None
        self.ocupacion_actual: Optional[str] = None
        self.empresa: Optional[str] = None
        self.experiencia_docente_anos: int = 0
        self.experiencia_catequesis_anos: int = 0
        
        # Formación catequética
        self.nivel_formacion: NivelFormacion = NivelFormacion.INICIAL
        self.especialidades: List[Especialidad] = []
        self.certificaciones: List[Dict[str, Any]] = []
        self.cursos_realizados: List[Dict[str, Any]] = []
        self.fecha_ultima_certificacion: Optional[date] = None
        self.requiere_recertificacion: bool = False
        
        # Disponibilidad y horarios
        self.disponibilidad_horarios: Dict[str, List[str]] = {}
        self.disponible_fines_semana: bool = True
        self.disponible_entre_semana: bool = False
        self.horas_semanales_disponibles: int = 4
        self.puede_coordinar_grupos: bool = False
        self.puede_formar_catequistas: bool = False
        
        # Información sacramental
        self.fecha_bautismo: Optional[date] = None
        self.fecha_confirmacion: Optional[date] = None
        self.fecha_matrimonio: Optional[date] = None
        self.es_ministro_extraordinario: bool = False
        self.otros_ministerios: List[str] = []
        
        # Evaluación y desempeño
        self.calificacion_promedio: float = 0.0
        self.numero_evaluaciones: int = 0
        self.fecha_ultima_evaluacion: Optional[date] = None
        self.observaciones_evaluacion: Optional[str] = None
        
        # Control administrativo
        self.numero_grupos_asignados: int = 0
        self.numero_catequizandos_atendidos: int = 0
        self.fecha_ultima_actividad: Optional[date] = None
        self.esta_disponible_asignacion: bool = True
        
        # Información adicional
        self.motivacion_servicio: Optional[str] = None
        self.expectativas: Optional[str] = None
        self.observaciones: Optional[str] = None
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
        return self.estado == EstadoCatequista.ACTIVO
    
    @property
    def tiempo_servicio_anos(self) -> Optional[float]:
        """Calcula años de servicio."""
        if not self.fecha_vinculacion:
            return None
        
        fecha_fin = self.fecha_desvinculacion or date.today()
        delta = fecha_fin - self.fecha_vinculacion
        return round(delta.days / 365.25, 1)
    
    @property
    def necesita_recertificacion(self) -> bool:
        """Verifica si necesita recertificación."""
        if self.requiere_recertificacion:
            return True
        
        if self.fecha_ultima_certificacion:
            # Recertificación cada 3 años
            fecha_limite = self.fecha_ultima_certificacion + timedelta(days=365*3)
            return date.today() > fecha_limite
        
        return True
    
    @property
    def especialidades_nombres(self) -> List[str]:
        """Obtiene los nombres de las especialidades."""
        nombres_especialidades = {
            Especialidad.PRIMERA_COMUNION: "Primera Comunión",
            Especialidad.CONFIRMACION: "Confirmación",
            Especialidad.CATEQUESIS_FAMILIAR: "Catequesis Familiar",
            Especialidad.NECESIDADES_ESPECIALES: "Necesidades Especiales",
            Especialidad.JOVENES: "Jóvenes",
            Especialidad.ADULTOS: "Adultos",
            Especialidad.PREPARACION_MATRIMONIAL: "Preparación Matrimonial",
            Especialidad.FORMACION_CATEQUISTAS: "Formación de Catequistas"
        }
        
        return [nombres_especialidades.get(esp, str(esp)) for esp in self.especialidades]
    
    @property
    def esta_disponible(self) -> bool:
        """Verifica si está disponible para asignaciones."""
        return (self.esta_activo and 
                self.esta_disponible_asignacion and 
                not self.necesita_recertificacion)
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Catequista."""
        # Validar nombres y apellidos
        if self.nombres and len(self.nombres.strip()) < 2:
            raise ValidationError("Los nombres deben tener al menos 2 caracteres")
        
        if self.apellidos and len(self.apellidos.strip()) < 2:
            raise ValidationError("Los apellidos deben tener al menos 2 caracteres")
        
        # Validar documento de identidad
        if self.documento_identidad:
            if not DataValidator.validate_cedula(self.documento_identidad):
                raise ValidationError("El número de documento no es válido")
        
        # Validar fecha de nacimiento
        if self.fecha_nacimiento:
            today = date.today()
            edad = self.edad
            
            if self.fecha_nacimiento > today:
                raise ValidationError("La fecha de nacimiento no puede ser futura")
            
            if edad is not None:
                if edad < 16:
                    raise ValidationError("Los catequistas deben tener al menos 16 años")
                if edad > 80:
                    raise ValidationError("La edad máxima para catequistas es 80 años")
        
        # Validar teléfonos
        if self.telefono and not DataValidator.validate_phone(self.telefono):
            raise ValidationError("El formato del teléfono principal no es válido")
        
        if self.telefono_alternativo and not DataValidator.validate_phone(self.telefono_alternativo):
            raise ValidationError("El formato del teléfono alternativo no es válido")
        
        # Validar email
        if self.email and not DataValidator.validate_email(self.email):
            raise ValidationError("El formato del email no es válido")
        
        # Validar experiencia
        if self.experiencia_docente_anos < 0 or self.experiencia_docente_anos > 60:
            raise ValidationError("La experiencia docente debe estar entre 0 y 60 años")
        
        if self.experiencia_catequesis_anos < 0 or self.experiencia_catequesis_anos > 60:
            raise ValidationError("La experiencia en catequesis debe estar entre 0 y 60 años")
        
        # Validar horas semanales
        if self.horas_semanales_disponibles < 1 or self.horas_semanales_disponibles > 40:
            raise ValidationError("Las horas semanales deben estar entre 1 y 40")
        
        # Validar calificación
        if self.calificacion_promedio < 0 or self.calificacion_promedio > 10:
            raise ValidationError("La calificación promedio debe estar entre 0 y 10")
        
        # Validar fechas sacramentales
        if self.fecha_bautismo and self.fecha_nacimiento:
            if self.fecha_bautismo < self.fecha_nacimiento:
                raise ValidationError("La fecha de bautismo no puede ser anterior al nacimiento")
        
        if self.fecha_confirmacion and self.fecha_bautismo:
            if self.fecha_confirmacion < self.fecha_bautismo:
                raise ValidationError("La confirmación debe ser posterior al bautismo")
        
        # Validar fechas de vinculación
        if self.fecha_vinculacion and self.fecha_desvinculacion:
            if self.fecha_desvinculacion < self.fecha_vinculacion:
                raise ValidationError("La fecha de desvinculación no puede ser anterior a la vinculación")
        
        # Validar parroquia
        if self.id_parroquia <= 0:
            raise ValidationError("Debe asignar una parroquia válida")
        
        # Validar enums
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoCatequista(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.nivel_formacion, str):
            try:
                self.nivel_formacion = NivelFormacion(self.nivel_formacion)
            except ValueError:
                raise ValidationError(f"Nivel de formación '{self.nivel_formacion}' no válido")
        
        if isinstance(self.tipo_vinculacion, str):
            try:
                self.tipo_vinculacion = TipoVinculacion(self.tipo_vinculacion)
            except ValueError:
                raise ValidationError(f"Tipo de vinculación '{self.tipo_vinculacion}' no válido")
        
        # Validar especialidades
        if isinstance(self.especialidades, list):
            especialidades_validadas = []
            for esp in self.especialidades:
                if isinstance(esp, str):
                    try:
                        especialidades_validadas.append(Especialidad(esp))
                    except ValueError:
                        raise ValidationError(f"Especialidad '{esp}' no válida")
                else:
                    especialidades_validadas.append(esp)
            self.especialidades = especialidades_validadas
    
    def agregar_especialidad(self, especialidad: Especialidad) -> None:
        """
        Agrega una especialidad al catequista.
        
        Args:
            especialidad: Especialidad a agregar
        """
        if especialidad not in self.especialidades:
            self.especialidades.append(especialidad)
            logger.info(f"Especialidad {especialidad.value} agregada a {self.nombre_completo}")
    
    def remover_especialidad(self, especialidad: Especialidad) -> None:
        """
        Remueve una especialidad del catequista.
        
        Args:
            especialidad: Especialidad a remover
        """
        if especialidad in self.especialidades:
            self.especialidades.remove(especialidad)
            logger.info(f"Especialidad {especialidad.value} removida de {self.nombre_completo}")
    
    def agregar_certificacion(
        self,
        nombre_certificacion: str,
        institucion: str,
        fecha_obtencion: date,
        fecha_vencimiento: date = None,
        numero_certificado: str = None
    ) -> None:
        """
        Agrega una certificación al catequista.
        
        Args:
            nombre_certificacion: Nombre de la certificación
            institucion: Institución que otorga
            fecha_obtencion: Fecha de obtención
            fecha_vencimiento: Fecha de vencimiento (opcional)
            numero_certificado: Número del certificado (opcional)
        """
        certificacion = {
            'nombre': nombre_certificacion,
            'institucion': institucion,
            'fecha_obtencion': fecha_obtencion.isoformat(),
            'fecha_vencimiento': fecha_vencimiento.isoformat() if fecha_vencimiento else None,
            'numero_certificado': numero_certificado,
            'vigente': True
        }
        
        self.certificaciones.append(certificacion)
        self.fecha_ultima_certificacion = fecha_obtencion
        self.requiere_recertificacion = False
        
        logger.info(f"Certificación '{nombre_certificacion}' agregada a {self.nombre_completo}")
    
    def agregar_curso(
        self,
        nombre_curso: str,
        institucion: str,
        fecha_inicio: date,
        fecha_fin: date,
        horas_academicas: int = None,
        calificacion: float = None
    ) -> None:
        """
        Agrega un curso realizado.
        
        Args:
            nombre_curso: Nombre del curso
            institucion: Institución
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de finalización
            horas_academicas: Horas académicas (opcional)
            calificacion: Calificación obtenida (opcional)
        """
        curso = {
            'nombre': nombre_curso,
            'institucion': institucion,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'horas_academicas': horas_academicas,
            'calificacion': calificacion
        }
        
        self.cursos_realizados.append(curso)
        logger.info(f"Curso '{nombre_curso}' agregado a {self.nombre_completo}")
    
    def configurar_disponibilidad(self, horarios: Dict[str, List[str]]) -> None:
        """
        Configura la disponibilidad horaria.
        
        Args:
            horarios: Diccionario con día y lista de horarios
        """
        dias_validos = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        
        for dia, horas in horarios.items():
            if dia.lower() in dias_validos:
                self.disponibilidad_horarios[dia.lower()] = horas
        
        # Actualizar disponibilidad general
        dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']
        fin_semana = ['sábado', 'domingo']
        
        self.disponible_entre_semana = any(
            self.disponibilidad_horarios.get(dia) for dia in dias_semana
        )
        self.disponible_fines_semana = any(
            self.disponibilidad_horarios.get(dia) for dia in fin_semana
        )
    
    def agregar_ministerio(self, ministerio: str) -> None:
        """
        Agrega un ministerio adicional.
        
        Args:
            ministerio: Nombre del ministerio
        """
        if ministerio and ministerio not in self.otros_ministerios:
            self.otros_ministerios.append(ministerio)
    
    def obtener_grupos_asignados(self) -> List[Dict[str, Any]]:
        """
        Obtiene los grupos asignados al catequista.
        
        Returns:
            List: Lista de grupos asignados
        """
        try:
            result = self._sp_manager.grupos.obtener_grupos_por_catequista(self.id_catequista)
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo grupos del catequista {self.id_catequista}: {str(e)}")
            return []
    
    def obtener_historial_evaluaciones(self) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de evaluaciones.
        
        Returns:
            List: Lista de evaluaciones
        """
        try:
            result = self._sp_manager.executor.execute(
                'catequistas',
                'obtener_evaluaciones',
                {'id_catequista': self.id_catequista}
            )
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo evaluaciones: {str(e)}")
            return []
    
    def calcular_carga_trabajo(self) -> Dict[str, Any]:
        """
        Calcula la carga de trabajo actual.
        
        Returns:
            dict: Información de carga de trabajo
        """
        grupos = self.obtener_grupos_asignados()
        
        total_catequizandos = sum(grupo.get('numero_catequizandos', 0) for grupo in grupos)
        horas_semanales_usadas = len(grupos) * 2  # Aproximadamente 2 horas por grupo
        
        porcentaje_carga = 0
        if self.horas_semanales_disponibles > 0:
            porcentaje_carga = (horas_semanales_usadas / self.horas_semanales_disponibles) * 100
        
        return {
            'grupos_asignados': len(grupos),
            'catequizandos_atendidos': total_catequizandos,
            'horas_semanales_usadas': horas_semanales_usadas,
            'horas_semanales_disponibles': self.horas_semanales_disponibles,
            'porcentaje_carga': min(porcentaje_carga, 100),
            'puede_recibir_mas_grupos': porcentaje_carga < 100
        }
    
    def evaluar_desempeño(
        self,
        calificacion: float,
        observaciones: str = None,
        fecha_evaluacion: date = None,
        evaluador: str = None
    ) -> None:
        """
        Registra una evaluación de desempeño.
        
        Args:
            calificacion: Calificación obtenida (1-10)
            observaciones: Observaciones de la evaluación
            fecha_evaluacion: Fecha de la evaluación
            evaluador: Quien evalúa
        """
        if calificacion < 1 or calificacion > 10:
            raise ValidationError("La calificación debe estar entre 1 y 10")
        
        # Actualizar promedio
        if self.numero_evaluaciones == 0:
            self.calificacion_promedio = calificacion
        else:
            total_puntos = self.calificacion_promedio * self.numero_evaluaciones
            total_puntos += calificacion
            self.numero_evaluaciones += 1
            self.calificacion_promedio = total_puntos / self.numero_evaluaciones
        
        self.numero_evaluaciones += 1
        self.fecha_ultima_evaluacion = fecha_evaluacion or date.today()
        self.observaciones_evaluacion = observaciones
        
        logger.info(f"Evaluación registrada para {self.nombre_completo}: {calificacion}")
    
    def activar(self) -> None:
        """Activa el catequista."""
        if self.necesita_recertificacion:
            raise ValidationError("No se puede activar: requiere recertificación")
        
        self.estado = EstadoCatequista.ACTIVO
        self.esta_disponible_asignacion = True
        self.fecha_ultima_actividad = date.today()
        
        logger.info(f"Catequista {self.nombre_completo} activado")
    
    def desactivar(self, motivo: str = None) -> None:
        """
        Desactiva el catequista.
        
        Args:
            motivo: Motivo de la desactivación
        """
        self.estado = EstadoCatequista.INACTIVO
        self.esta_disponible_asignacion = False
        
        if motivo:
            self.observaciones = f"Desactivado: {motivo}"
        
        logger.info(f"Catequista {self.nombre_completo} desactivado")
    
    def suspender(self, motivo: str, fecha_suspension: date = None) -> None:
        """
        Suspende el catequista.
        
        Args:
            motivo: Motivo de la suspensión
            fecha_suspension: Fecha de la suspensión
        """
        self.estado = EstadoCatequista.SUSPENDIDO
        self.esta_disponible_asignacion = False
        self.fecha_desvinculacion = fecha_suspension or date.today()
        self.motivo_desvinculacion = motivo
        
        logger.info(f"Catequista {self.nombre_completo} suspendido: {motivo}")
    
    def retirar(self, motivo: str, fecha_retiro: date = None) -> None:
        """
        Retira el catequista del servicio.
        
        Args:
            motivo: Motivo del retiro
            fecha_retiro: Fecha del retiro
        """
        self.estado = EstadoCatequista.RETIRADO
        self.esta_disponible_asignacion = False
        self.fecha_desvinculacion = fecha_retiro or date.today()
        self.motivo_desvinculacion = motivo
        
        logger.info(f"Catequista {self.nombre_completo} retirado: {motivo}")
    
    def actualizar_estadisticas(self) -> None:
        """Actualiza las estadísticas del catequista."""
        try:
            grupos = self.obtener_grupos_asignados()
            self.numero_grupos_asignados = len(grupos)
            self.numero_catequizandos_atendidos = sum(
                grupo.get('numero_catequizandos', 0) for grupo in grupos
            )
            
            if grupos:
                self.fecha_ultima_actividad = date.today()
            
        except Exception as e:
            logger.error(f"Error actualizando estadísticas del catequista: {str(e)}")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['estado'] = self.estado.value
        data['nivel_formacion'] = self.nivel_formacion.value
        data['tipo_vinculacion'] = self.tipo_vinculacion.value
        data['especialidades'] = [esp.value for esp in self.especialidades]
        
        # Agregar propiedades calculadas
        data['edad'] = self.edad
        data['tiempo_servicio_anos'] = self.tiempo_servicio_anos
        data['necesita_recertificacion'] = self.necesita_recertificacion
        data['esta_disponible'] = self.esta_disponible
        
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
    def find_by_documento(cls, documento: str) -> Optional['Catequista']:
        """Busca un catequista por documento."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.catequistas.buscar_catequista_por_documento(documento)
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando catequista por documento {documento}: {str(e)}")
            return None
    
    @classmethod
    def find_by_parroquia(cls, id_parroquia: int) -> List['Catequista']:
        """Busca catequistas de una parroquia."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.catequistas.obtener_catequistas_por_parroquia(id_parroquia)
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando catequistas por parroquia {id_parroquia}: {str(e)}")
            return []
    
    @classmethod
    def find_disponibles(cls, id_parroquia: int = None) -> List['Catequista']:
        """Busca catequistas disponibles para asignación."""
        try:
            sp_manager = get_sp_manager()
            
            if id_parroquia:
                result = sp_manager.catequistas.obtener_catequistas_disponibles(id_parroquia)
            else:
                result = sp_manager.executor.execute(
                    'catequistas',
                    'obtener_todos_disponibles',
                    {}
                )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando catequistas disponibles: {str(e)}")
            return []
    
    @classmethod
    def find_by_especialidad(cls, especialidad: Especialidad) -> List['Catequista']:
        """Busca catequistas por especialidad."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'catequistas',
                'buscar_por_especialidad',
                {'especialidad': especialidad.value}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando catequistas por especialidad {especialidad}: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Catequista':
        """Guarda el catequista con validaciones adicionales."""
        # Establecer fecha de vinculación si es nuevo
        if self.is_new and not self.fecha_vinculacion:
            self.fecha_vinculacion = date.today()
        
        # Actualizar estadísticas antes de guardar
        if not self.is_new:
            self.actualizar_estadisticas()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('catequista', Catequista)