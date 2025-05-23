"""
Modelo de Grupo para el sistema de catequesis.
Representa los grupos de catequesis con catequizandos y catequistas asignados.
"""

import logging
from datetime import date, datetime, time
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class EstadoGrupo(Enum):
    """Estados del grupo."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    FINALIZADO = "finalizado"
    EN_FORMACION = "en_formacion"


class ModalidadGrupo(Enum):
    """Modalidades del grupo."""
    PRESENCIAL = "presencial"
    VIRTUAL = "virtual"
    MIXTA = "mixta"


class DiasSemana(Enum):
    """Días de la semana."""
    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miércoles"
    JUEVES = "jueves"
    VIERNES = "viernes"
    SABADO = "sábado"
    DOMINGO = "domingo"


class Grupo(BaseModel):
    """
    Modelo de Grupo del sistema de catequesis.
    Representa los grupos de formación catequética.
    """
    
    # Configuración del modelo
    _table_schema = "grupos"
    _primary_key = "id_grupo"
    _required_fields = ["nombre", "id_nivel", "id_parroquia"]
    _unique_fields = ["codigo_grupo"]
    _searchable_fields = [
        "nombre", "codigo_grupo", "descripcion", 
        "nombre_catequista", "horario"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Grupo."""
        # Identificación básica
        self.id_grupo: Optional[int] = None
        self.codigo_grupo: Optional[str] = None
        self.nombre: str = ""
        self.descripcion: Optional[str] = None
        self.estado: EstadoGrupo = EstadoGrupo.EN_FORMACION
        
        # Relaciones institucionales
        self.id_parroquia: int = 0
        self.id_nivel: int = 0
        self.id_catequista_principal: Optional[int] = None
        self.catequistas_auxiliares: List[int] = []
        
        # Configuración académica
        self.capacidad_maxima: int = 25
        self.capacidad_minima: int = 8
        self.edad_minima: Optional[int] = None
        self.edad_maxima: Optional[int] = None
        self.requiere_casos_especiales: bool = False
        
        # Fechas importantes
        self.fecha_inicio: Optional[date] = None
        self.fecha_fin_estimada: Optional[date] = None
        self.fecha_fin_real: Optional[date] = None
        self.fecha_inscripciones_inicio: Optional[date] = None
        self.fecha_inscripciones_fin: Optional[date] = None
        
        # Horarios y modalidad
        self.modalidad: ModalidadGrupo = ModalidadGrupo.PRESENCIAL
        self.dia_encuentro: Optional[DiasSemana] = None
        self.hora_inicio: Optional[time] = None
        self.hora_fin: Optional[time] = None
        self.duracion_minutos: int = 90
        self.frecuencia_semanal: int = 1
        
        # Información del lugar
        self.salon_asignado: Optional[str] = None
        self.ubicacion_detalle: Optional[str] = None
        self.direccion_encuentro: Optional[str] = None
        self.enlace_virtual: Optional[str] = None
        self.plataforma_virtual: Optional[str] = None
        
        # Control de inscripciones
        self.permite_inscripciones: bool = True
        self.requiere_pago: bool = False
        self.monto_inscripcion: float = 0.0
        self.monto_materiales: float = 0.0
        self.descuento_hermanos: float = 0.0
        
        # Estadísticas y control
        self.numero_inscritos: int = 0
        self.numero_activos: int = 0
        self.numero_retirados: int = 0
        self.numero_graduados: int = 0
        self.porcentaje_asistencia_promedio: float = 0.0
        self.calificacion_promedio: float = 0.0
        
        # Configuración de evaluación
        self.requiere_evaluaciones: bool = True
        self.nota_minima_aprobacion: float = 7.0
        self.porcentaje_asistencia_minima: float = 80.0
        self.permite_recuperaciones: bool = True
        self.numero_max_faltas: int = 5
        
        # Recursos y materiales
        self.materiales_necesarios: List[str] = []
        self.recursos_disponibles: List[str] = []
        self.material_didactico_asignado: Optional[str] = None
        self.libros_texto: List[str] = []
        
        # Comunicación
        self.grupo_whatsapp: Optional[str] = None
        self.email_grupo: Optional[str] = None
        self.canal_comunicacion: Optional[str] = None
        
        # Observaciones y notas
        self.observaciones: Optional[str] = None
        self.notas_especiales: Optional[str] = None
        self.requisitos_especiales: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_activo(self) -> bool:
        """Verifica si el grupo está activo."""
        return self.estado == EstadoGrupo.ACTIVO
    
    @property
    def tiene_cupos_disponibles(self) -> bool:
        """Verifica si tiene cupos disponibles."""
        return (self.permite_inscripciones and 
                self.numero_inscritos < self.capacidad_maxima and
                self.esta_activo)
    
    @property
    def cupos_disponibles(self) -> int:
        """Calcula cupos disponibles."""
        return max(0, self.capacidad_maxima - self.numero_inscritos)
    
    @property
    def porcentaje_ocupacion(self) -> float:
        """Calcula el porcentaje de ocupación."""
        if self.capacidad_maxima == 0:
            return 0.0
        return (self.numero_inscritos / self.capacidad_maxima) * 100
    
    @property
    def cumple_minimo(self) -> bool:
        """Verifica si cumple el mínimo de inscritos."""
        return self.numero_inscritos >= self.capacidad_minima
    
    @property
    def horario_formateado(self) -> str:
        """Obtiene el horario formateado."""
        if not self.dia_encuentro:
            return "Sin horario definido"
        
        horario_parts = [self.dia_encuentro.value.capitalize()]
        
        if self.hora_inicio and self.hora_fin:
            horario_parts.append(f"{self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}")
        elif self.hora_inicio:
            horario_parts.append(f"desde {self.hora_inicio.strftime('%H:%M')}")
        
        return " ".join(horario_parts)
    
    @property
    def duracion_formateada(self) -> str:
        """Obtiene la duración formateada."""
        horas = self.duracion_minutos // 60
        minutos = self.duracion_minutos % 60
        
        if horas > 0 and minutos > 0:
            return f"{horas}h {minutos}min"
        elif horas > 0:
            return f"{horas}h"
        else:
            return f"{minutos}min"
    
    @property
    def esta_en_periodo_inscripciones(self) -> bool:
        """Verifica si está en período de inscripciones."""
        if not self.permite_inscripciones:
            return False
        
        today = date.today()
        
        if self.fecha_inscripciones_inicio and today < self.fecha_inscripciones_inicio:
            return False
        
        if self.fecha_inscripciones_fin and today > self.fecha_inscripciones_fin:
            return False
        
        return True
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Grupo."""
        # Validar nombre
        if self.nombre and len(self.nombre.strip()) < 3:
            raise ValidationError("El nombre del grupo debe tener al menos 3 caracteres")
        
        # Validar capacidades
        if self.capacidad_minima < 1:
            raise ValidationError("La capacidad mínima debe ser mayor a 0")
        
        if self.capacidad_maxima < self.capacidad_minima:
            raise ValidationError("La capacidad máxima debe ser mayor a la mínima")
        
        if self.capacidad_maxima > 50:
            raise ValidationError("La capacidad máxima no puede superar 50 catequizandos")
        
        # Validar edades
        if self.edad_minima is not None and (self.edad_minima < 3 or self.edad_minima > 25):
            raise ValidationError("La edad mínima debe estar entre 3 y 25 años")
        
        if self.edad_maxima is not None and (self.edad_maxima < 3 or self.edad_maxima > 25):
            raise ValidationError("La edad máxima debe estar entre 3 y 25 años")
        
        if (self.edad_minima is not None and self.edad_maxima is not None and 
            self.edad_maxima < self.edad_minima):
            raise ValidationError("La edad máxima debe ser mayor a la mínima")
        
        # Validar duración
        if self.duracion_minutos < 30 or self.duracion_minutos > 300:
            raise ValidationError("La duración debe estar entre 30 y 300 minutos")
        
        # Validar frecuencia
        if self.frecuencia_semanal < 1 or self.frecuencia_semanal > 7:
            raise ValidationError("La frecuencia semanal debe estar entre 1 y 7")
        
        # Validar horarios
        if self.hora_inicio and self.hora_fin:
            if self.hora_fin <= self.hora_inicio:
                raise ValidationError("La hora de fin debe ser posterior a la hora de inicio")
        
        # Validar fechas
        if self.fecha_inicio and self.fecha_fin_estimada:
            if self.fecha_fin_estimada <= self.fecha_inicio:
                raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio")
        
        if self.fecha_inscripciones_inicio and self.fecha_inscripciones_fin:
            if self.fecha_inscripciones_fin <= self.fecha_inscripciones_inicio:
                raise ValidationError("La fecha de fin de inscripciones debe ser posterior al inicio")
        
        # Validar montos
        if self.monto_inscripcion < 0:
            raise ValidationError("El monto de inscripción no puede ser negativo")
        
        if self.monto_materiales < 0:
            raise ValidationError("El monto de materiales no puede ser negativo")
        
        if self.descuento_hermanos < 0 or self.descuento_hermanos > 100:
            raise ValidationError("El descuento por hermanos debe estar entre 0 y 100%")
        
        # Validar nota mínima
        if self.nota_minima_aprobacion < 1 or self.nota_minima_aprobacion > 10:
            raise ValidationError("La nota mínima debe estar entre 1 y 10")
        
        # Validar porcentaje de asistencia
        if self.porcentaje_asistencia_minima < 0 or self.porcentaje_asistencia_minima > 100:
            raise ValidationError("El porcentaje de asistencia debe estar entre 0 y 100")
        
        # Validar número máximo de faltas
        if self.numero_max_faltas < 0:
            raise ValidationError("El número máximo de faltas no puede ser negativo")
        
        # Validar IDs requeridos
        if self.id_parroquia <= 0:
            raise ValidationError("Debe asignar una parroquia válida")
        
        if self.id_nivel <= 0:
            raise ValidationError("Debe asignar un nivel válido")
        
        # Validar enums
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoGrupo(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.modalidad, str):
            try:
                self.modalidad = ModalidadGrupo(self.modalidad)
            except ValueError:
                raise ValidationError(f"Modalidad '{self.modalidad}' no válida")
        
        if isinstance(self.dia_encuentro, str):
            try:
                self.dia_encuentro = DiasSemana(self.dia_encuentro)
            except ValueError:
                raise ValidationError(f"Día de encuentro '{self.dia_encuentro}' no válido")
        
        # Validar modalidad virtual
        if self.modalidad in [ModalidadGrupo.VIRTUAL, ModalidadGrupo.MIXTA]:
            if not self.enlace_virtual:
                raise ValidationError("Los grupos virtuales/mixtos requieren enlace virtual")
    
    def generar_codigo_grupo(self) -> str:
        """
        Genera un código único para el grupo.
        
        Returns:
            str: Código generado
        """
        if not self.nombre:
            raise ValidationError("Se requiere el nombre para generar el código")
        
        # Crear código basado en parroquia, nivel y nombre
        codigo_base = ""
        
        # Agregar prefijo de parroquia si está disponible
        if self.id_parroquia:
            codigo_base += f"P{self.id_parroquia:02d}"
        
        # Agregar prefijo de nivel
        if self.id_nivel:
            codigo_base += f"N{self.id_nivel:02d}"
        
        # Agregar iniciales del nombre
        palabras = self.nombre.upper().split()
        iniciales = ''.join(palabra[0] for palabra in palabras if palabra.isalpha())[:3]
        codigo_base += iniciales
        
        # Verificar unicidad y agregar número secuencial si es necesario
        codigo = codigo_base
        contador = 1
        
        while self._codigo_exists(codigo):
            codigo = f"{codigo_base}{contador:02d}"
            contador += 1
        
        self.codigo_grupo = codigo
        return codigo
    
    def _codigo_exists(self, codigo: str) -> bool:
        """Verifica si un código ya existe."""
        try:
            result = self._sp_manager.executor.execute(
                'grupos',
                'existe_codigo',
                {
                    'codigo_grupo': codigo,
                    'excluir_id': self.id_grupo
                }
            )
            return result.get('existe', False)
        except Exception:
            return False
    
    def obtener_catequizandos(self) -> List[Dict[str, Any]]:
        """
        Obtiene los catequizandos inscritos en el grupo.
        
        Returns:
            List: Lista de catequizandos
        """
        try:
            result = self._sp_manager.inscripciones.obtener_inscripciones_por_grupo(self.id_grupo)
            
            if result.get('success') and result.get('data'):
                return result['data']
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo catequizandos del grupo {self.id_grupo}: {str(e)}")
            return []
    
    def obtener_catequista_principal(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del catequista principal.
        
        Returns:
            dict: Información del catequista principal o None
        """
        if not self.id_catequista_principal:
            return None
        
        try:
            result = self._sp_manager.catequistas.obtener_catequista(self.id_catequista_principal)
            
            if result.get('success') and result.get('data'):
                return result['data']
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo catequista principal: {str(e)}")
            return None
    
    def obtener_catequistas_auxiliares(self) -> List[Dict[str, Any]]:
        """
        Obtiene información de los catequistas auxiliares.
        
        Returns:
            List: Lista de catequistas auxiliares
        """
        if not self.catequistas_auxiliares:
            return []
        
        catequistas = []
        for id_catequista in self.catequistas_auxiliares:
            try:
                result = self._sp_manager.catequistas.obtener_catequista(id_catequista)
                if result.get('success') and result.get('data'):
                    catequistas.append(result['data'])
            except Exception as e:
                logger.error(f"Error obteniendo catequista auxiliar {id_catequista}: {str(e)}")
        
        return catequistas
    
    def asignar_catequista_principal(self, id_catequista: int) -> None:
        """
        Asigna un catequista principal al grupo.
        
        Args:
            id_catequista: ID del catequista principal
        """
        # Verificar que el catequista esté disponible
        try:
            result = self._sp_manager.catequistas.obtener_catequista(id_catequista)
            if not (result.get('success') and result.get('data')):
                raise ValidationError("Catequista no encontrado")
            
            catequista_data = result['data']
            if not catequista_data.get('esta_disponible', False):
                raise ValidationError("El catequista no está disponible para asignación")
            
            self.id_catequista_principal = id_catequista
            logger.info(f"Catequista principal {id_catequista} asignado al grupo {self.nombre}")
            
        except Exception as e:
            logger.error(f"Error asignando catequista principal: {str(e)}")
            raise
    
    def agregar_catequista_auxiliar(self, id_catequista: int) -> None:
        """
        Agrega un catequista auxiliar al grupo.
        
        Args:
            id_catequista: ID del catequista auxiliar
        """
        if id_catequista in self.catequistas_auxiliares:
            raise ValidationError("El catequista ya está asignado como auxiliar")
        
        if id_catequista == self.id_catequista_principal:
            raise ValidationError("El catequista ya es el principal del grupo")
        
        self.catequistas_auxiliares.append(id_catequista)
        logger.info(f"Catequista auxiliar {id_catequista} agregado al grupo {self.nombre}")
    
    def remover_catequista_auxiliar(self, id_catequista: int) -> None:
        """
        Remueve un catequista auxiliar del grupo.
        
        Args:
            id_catequista: ID del catequista auxiliar
        """
        if id_catequista in self.catequistas_auxiliares:
            self.catequistas_auxiliares.remove(id_catequista)
            logger.info(f"Catequista auxiliar {id_catequista} removido del grupo {self.nombre}")
    
    def configurar_horario(
        self,
        dia: DiasSemana,
        hora_inicio: time,
        hora_fin: time = None,
        duracion_minutos: int = None
    ) -> None:
        """
        Configura el horario del grupo.
        
        Args:
            dia: Día de la semana
            hora_inicio: Hora de inicio
            hora_fin: Hora de fin (opcional)
            duracion_minutos: Duración en minutos (opcional)
        """
        self.dia_encuentro = dia
        self.hora_inicio = hora_inicio
        
        if hora_fin:
            self.hora_fin = hora_fin
            # Calcular duración
            inicio_dt = datetime.combine(date.today(), hora_inicio)
            fin_dt = datetime.combine(date.today(), hora_fin)
            self.duracion_minutos = int((fin_dt - inicio_dt).total_seconds() / 60)
        elif duracion_minutos:
            self.duracion_minutos = duracion_minutos
            # Calcular hora de fin
            inicio_dt = datetime.combine(date.today(), hora_inicio)
            fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)
            self.hora_fin = fin_dt.time()
    
    def configurar_inscripciones(
        self,
        permite_inscripciones: bool = True,
        fecha_inicio: date = None,
        fecha_fin: date = None,
        requiere_pago: bool = False,
        monto_inscripcion: float = 0.0,
        monto_materiales: float = 0.0
    ) -> None:
        """
        Configura las inscripciones del grupo.
        
        Args:
            permite_inscripciones: Si permite inscripciones
            fecha_inicio: Fecha de inicio de inscripciones
            fecha_fin: Fecha de fin de inscripciones
            requiere_pago: Si requiere pago
            monto_inscripcion: Monto de inscripción
            monto_materiales: Monto de materiales
        """
        self.permite_inscripciones = permite_inscripciones
        self.fecha_inscripciones_inicio = fecha_inicio
        self.fecha_inscripciones_fin = fecha_fin
        self.requiere_pago = requiere_pago
        self.monto_inscripcion = monto_inscripcion
        self.monto_materiales = monto_materiales
    
    def agregar_material_necesario(self, material: str) -> None:
        """Agrega un material necesario."""
        if material and material not in self.materiales_necesarios:
            self.materiales_necesarios.append(material)
    
    def agregar_recurso_disponible(self, recurso: str) -> None:
        """Agrega un recurso disponible."""
        if recurso and recurso not in self.recursos_disponibles:
            self.recursos_disponibles.append(recurso)
    
    def agregar_libro_texto(self, libro: str) -> None:
        """Agrega un libro de texto."""
        if libro and libro not in self.libros_texto:
            self.libros_texto.append(libro)
    
    def calcular_estadisticas(self) -> Dict[str, Any]:
        """
        Calcula estadísticas del grupo.
        
        Returns:
            dict: Estadísticas del grupo
        """
        try:
            # Obtener estadísticas de inscripciones
            inscripciones = self.obtener_catequizandos()
            
            activos = len([i for i in inscripciones if i.get('estado') == 'activa'])
            retirados = len([i for i in inscripciones if i.get('estado') == 'retirada'])
            graduados = len([i for i in inscripciones if i.get('estado') == 'graduada'])
            
            # Obtener estadísticas de asistencias
            asistencias_result = self._sp_manager.asistencias.obtener_asistencias_por_grupo(self.id_grupo)
            porcentaje_asistencia = 0.0
            
            if asistencias_result.get('success') and asistencias_result.get('data'):
                asistencias = asistencias_result['data']
                if asistencias:
                    total_asistencias = len(asistencias)
                    presentes = len([a for a in asistencias if a.get('presente')])
                    porcentaje_asistencia = (presentes / total_asistencias) * 100 if total_asistencias > 0 else 0
            
            # Obtener estadísticas de calificaciones
            calificaciones_result = self._sp_manager.calificaciones.obtener_calificaciones_por_grupo(self.id_grupo)
            promedio_calificaciones = 0.0
            
            if calificaciones_result.get('success') and calificaciones_result.get('data'):
                calificaciones = calificaciones_result['data']
                if calificaciones:
                    notas = [c['calificacion'] for c in calificaciones if c.get('calificacion') is not None]
                    promedio_calificaciones = sum(notas) / len(notas) if notas else 0
            
            # Actualizar propiedades del modelo
            self.numero_inscritos = len(inscripciones)
            self.numero_activos = activos
            self.numero_retirados = retirados
            self.numero_graduados = graduados
            self.porcentaje_asistencia_promedio = round(porcentaje_asistencia, 2)
            self.calificacion_promedio = round(promedio_calificaciones, 2)
            
            return {
                'total_inscritos': self.numero_inscritos,
                'activos': self.numero_activos,
                'retirados': self.numero_retirados,
                'graduados': self.numero_graduados,
                'porcentaje_ocupacion': self.porcentaje_ocupacion,
                'cupos_disponibles': self.cupos_disponibles,
                'porcentaje_asistencia': self.porcentaje_asistencia_promedio,
                'promedio_calificaciones': self.calificacion_promedio,
                'cumple_minimo': self.cumple_minimo
            }
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas del grupo {self.id_grupo}: {str(e)}")
            return {}
    
    def activar(self) -> None:
        """Activa el grupo."""
        if not self.cumple_minimo:
            raise ValidationError(f"No se puede activar: requiere mínimo {self.capacidad_minima} inscritos")
        
        if not self.id_catequista_principal:
            raise ValidationError("No se puede activar: requiere catequista principal asignado")
        
        self.estado = EstadoGrupo.ACTIVO
        
        if not self.fecha_inicio:
            self.fecha_inicio = date.today()
        
        logger.info(f"Grupo {self.nombre} activado")
    
    def suspender(self, motivo: str = None) -> None:
        """
        Suspende el grupo.
        
        Args:
            motivo: Motivo de la suspensión
        """
        self.estado = EstadoGrupo.SUSPENDIDO
        
        if motivo:
            self.observaciones = f"Suspendido: {motivo}"
        
        logger.info(f"Grupo {self.nombre} suspendido")
    
    def finalizar(self, fecha_fin: date = None) -> None:
        """
        Finaliza el grupo.
        
        Args:
            fecha_fin: Fecha de finalización
        """
        self.estado = EstadoGrupo.FINALIZADO
        self.fecha_fin_real = fecha_fin or date.today()
        self.permite_inscripciones = False
        
        logger.info(f"Grupo {self.nombre} finalizado")
    
    def reactivar(self) -> None:
        """Reactiva un grupo suspendido."""
        if self.estado == EstadoGrupo.SUSPENDIDO:
            self.estado = EstadoGrupo.ACTIVO
            logger.info(f"Grupo {self.nombre} reactivado")
        else:
            raise ValidationError("Solo se pueden reactivar grupos suspendidos")
    
    def verificar_disponibilidad_catequizando(self, edad_catequizando: int) -> Dict[str, Any]:
        """
        Verifica si un catequizando puede inscribirse en el grupo.
        
        Args:
            edad_catequizando: Edad del catequizando
            
        Returns:
            dict: Resultado de la verificación
        """
        if not self.tiene_cupos_disponibles:
            return {
                'puede_inscribirse': False,
                'razon': 'No hay cupos disponibles'
            }
        
        if not self.esta_en_periodo_inscripciones:
            return {
                'puede_inscribirse': False,
                'razon': 'Fuera del período de inscripciones'
            }
        
        # Verificar edad si está configurada
        if self.edad_minima is not None and edad_catequizando < self.edad_minima:
            return {
                'puede_inscribirse': False,
                'razon': f'Edad mínima requerida: {self.edad_minima} años'
            }
        
        if self.edad_maxima is not None and edad_catequizando > self.edad_maxima:
            return {
                'puede_inscribirse': False,
                'razon': f'Edad máxima permitida: {self.edad_maxima} años'
            }
        
        return {
            'puede_inscribirse': True,
            'razon': 'Cumple todos los requisitos'
        }
    
    def to_dict(self, include_audit: bool = False) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['estado'] = self.estado.value
        data['modalidad'] = self.modalidad.value
        if self.dia_encuentro:
            data['dia_encuentro'] = self.dia_encuentro.value
        
        # Convertir time a string
        if self.hora_inicio:
            data['hora_inicio'] = self.hora_inicio.strftime('%H:%M')
        if self.hora_fin:
            data['hora_fin'] = self.hora_fin.strftime('%H:%M')
        
        # Agregar propiedades calculadas
        data['horario_formateado'] = self.horario_formateado
        data['tiene_cupos_disponibles'] = self.tiene_cupos_disponibles
        data['cupos_disponibles'] = self.cupos_disponibles
        data['porcentaje_ocupacion'] = self.porcentaje_ocupacion
        data['cumple_minimo'] = self.cumple_minimo
        data['esta_en_periodo_inscripciones'] = self.esta_en_periodo_inscripciones
        
        return data
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['Grupo']:
        """Busca un grupo por código."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'grupos',
                'obtener_por_codigo',
                {'codigo_grupo': codigo}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando grupo por código {codigo}: {str(e)}")
            return None
    
    @classmethod
    def find_by_parroquia(cls, id_parroquia: int) -> List['Grupo']:
        """Busca grupos de una parroquia."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.grupos.obtener_grupos_por_parroquia(id_parroquia)
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando grupos por parroquia {id_parroquia}: {str(e)}")
            return []
    
    @classmethod
    def find_by_catequista(cls, id_catequista: int) -> List['Grupo']:
        """Busca grupos de un catequista."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.grupos.obtener_grupos_por_catequista(id_catequista)
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando grupos por catequista {id_catequista}: {str(e)}")
            return []
    
    @classmethod
    def find_activos_con_cupos(cls, id_parroquia: int = None) -> List['Grupo']:
        """Busca grupos activos con cupos disponibles."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'grupos',
                'obtener_activos_con_cupos',
                {'id_parroquia': id_parroquia} if id_parroquia else {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando grupos activos con cupos: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Grupo':
        """Guarda el grupo con validaciones adicionales."""
        # Generar código si no existe
        if not self.codigo_grupo:
            self.generar_codigo_grupo()
        
        # Calcular estadísticas antes de guardar si no es nuevo
        if not self.is_new:
            self.calcular_estadisticas()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('grupo', Grupo)