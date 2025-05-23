"""
Modelo de Nivel de Catequesis para el sistema.
Define los diferentes niveles y etapas de la formación catequética.
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class TipoNivel(Enum):
    """Tipos de nivel de catequesis."""
    PREPARACION = "preparacion"
    PRIMERA_COMUNION = "primera_comunion"
    CONFIRMACION = "confirmacion"
    PERSEVERANCIA = "perseverancia"
    CATEQUESIS_FAMILIAR = "catequesis_familiar"
    CATEQUESIS_ESPECIAL = "catequesis_especial"


class EstadoNivel(Enum):
    """Estados del nivel."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    EN_REVISION = "en_revision"
    SUSPENDIDO = "suspendido"


class ModalidadNivel(Enum):
    """Modalidades de enseñanza del nivel."""
    PRESENCIAL = "presencial"
    VIRTUAL = "virtual"
    MIXTA = "mixta"
    INTENSIVA = "intensiva"


class Nivel(BaseModel):
    """
    Modelo de Nivel de Catequesis.
    Define los niveles de formación catequética disponibles en el sistema.
    """
    
    # Configuración del modelo
    _table_schema = "niveles"
    _primary_key = "id_nivel"
    _required_fields = ["nombre", "tipo_nivel", "duracion_meses"]
    _unique_fields = ["codigo_nivel", "nombre"]
    _searchable_fields = ["nombre", "descripcion", "codigo_nivel"]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Nivel."""
        # Identificación básica
        self.id_nivel: Optional[int] = None
        self.codigo_nivel: Optional[str] = None
        self.nombre: str = ""
        self.descripcion: Optional[str] = None
        self.tipo_nivel: TipoNivel = TipoNivel.PREPARACION
        self.estado: EstadoNivel = EstadoNivel.ACTIVO
        
        # Configuración académica
        self.duracion_meses: int = 12
        self.edad_minima: int = 7
        self.edad_maxima: int = 16
        self.orden_secuencial: int = 1
        self.es_obligatorio: bool = True
        self.requiere_nivel_previo: bool = False
        self.id_nivel_previo: Optional[int] = None
        
        # Modalidad y metodología
        self.modalidad: ModalidadNivel = ModalidadNivel.PRESENCIAL
        self.numero_encuentros: int = 30
        self.duracion_encuentro_minutos: int = 90
        self.material_didactico: List[str] = []
        self.recursos_necesarios: List[str] = []
        
        # Evaluación y certificación
        self.requiere_evaluacion: bool = True
        self.nota_minima_aprobacion: float = 7.0
        self.porcentaje_asistencia_minima: float = 80.0
        self.genera_certificado: bool = True
        self.template_certificado: Optional[str] = None
        
        # Contenido curricular
        self.objetivos: List[str] = []
        self.contenidos: List[Dict[str, Any]] = []
        self.competencias: List[str] = []
        self.valores_a_desarrollar: List[str] = []
        
        # Sacramento asociado
        self.prepara_sacramento: Optional[str] = None
        self.requisitos_sacramento: List[str] = []
        
        # Configuraciones especiales
        self.permite_casos_especiales: bool = True
        self.configuracion_especial: Dict[str, Any] = {}
        self.observaciones: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_activo(self) -> bool:
        """Verifica si el nivel está activo."""
        return self.estado == EstadoNivel.ACTIVO
    
    @property
    def duracion_total_horas(self) -> float:
        """Calcula la duración total en horas."""
        return (self.numero_encuentros * self.duracion_encuentro_minutos) / 60
    
    @property
    def rango_edad_descripcion(self) -> str:
        """Obtiene descripción del rango de edad."""
        return f"{self.edad_minima} - {self.edad_maxima} años"
    
    @property
    def es_nivel_inicial(self) -> bool:
        """Verifica si es un nivel inicial (sin nivel previo)."""
        return not self.requiere_nivel_previo or self.id_nivel_previo is None
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Nivel."""
        # Validar nombre
        if self.nombre and len(self.nombre.strip()) < 3:
            raise ValidationError("El nombre del nivel debe tener al menos 3 caracteres")
        
        # Validar duración
        if self.duracion_meses < 1 or self.duracion_meses > 36:
            raise ValidationError("La duración debe estar entre 1 y 36 meses")
        
        # Validar edades
        if self.edad_minima < 3 or self.edad_minima > 25:
            raise ValidationError("La edad mínima debe estar entre 3 y 25 años")
        
        if self.edad_maxima < self.edad_minima:
            raise ValidationError("La edad máxima debe ser mayor a la edad mínima")
        
        if self.edad_maxima - self.edad_minima > 15:
            raise ValidationError("El rango de edad no puede superar los 15 años")
        
        # Validar número de encuentros
        if self.numero_encuentros < 1 or self.numero_encuentros > 100:
            raise ValidationError("El número de encuentros debe estar entre 1 y 100")
        
        # Validar duración de encuentros
        if self.duracion_encuentro_minutos < 30 or self.duracion_encuentro_minutos > 300:
            raise ValidationError("La duración del encuentro debe estar entre 30 y 300 minutos")
        
        # Validar nota mínima
        if self.nota_minima_aprobacion < 1.0 or self.nota_minima_aprobacion > 10.0:
            raise ValidationError("La nota mínima debe estar entre 1.0 y 10.0")
        
        # Validar porcentaje de asistencia
        if self.porcentaje_asistencia_minima < 0 or self.porcentaje_asistencia_minima > 100:
            raise ValidationError("El porcentaje de asistencia debe estar entre 0 y 100")
        
        # Validar orden secuencial
        if self.orden_secuencial < 1:
            raise ValidationError("El orden secuencial debe ser mayor a 0")
        
        # Validar tipo de nivel
        if isinstance(self.tipo_nivel, str):
            try:
                self.tipo_nivel = TipoNivel(self.tipo_nivel)
            except ValueError:
                raise ValidationError(f"Tipo de nivel '{self.tipo_nivel}' no válido")
        
        # Validar estado
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoNivel(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        # Validar modalidad
        if isinstance(self.modalidad, str):
            try:
                self.modalidad = ModalidadNivel(self.modalidad)
            except ValueError:
                raise ValidationError(f"Modalidad '{self.modalidad}' no válida")
        
        # Validar nivel previo si es requerido
        if self.requiere_nivel_previo and not self.id_nivel_previo:
            raise ValidationError("Se requiere especificar el nivel previo")
        
        # Validar que no se referencie a sí mismo como nivel previo
        if self.id_nivel_previo == self.id_nivel:
            raise ValidationError("Un nivel no puede ser previo a sí mismo")
    
    def generar_codigo_nivel(self) -> str:
        """
        Genera un código único para el nivel.
        
        Returns:
            str: Código generado
        """
        if not self.nombre:
            raise ValidationError("Se requiere el nombre para generar el código")
        
        # Crear código basado en tipo y nombre
        tipo_prefijo = {
            TipoNivel.PREPARACION: "PREP",
            TipoNivel.PRIMERA_COMUNION: "PC",
            TipoNivel.CONFIRMACION: "CONF",
            TipoNivel.PERSEVERANCIA: "PERS",
            TipoNivel.CATEQUESIS_FAMILIAR: "FAM",
            TipoNivel.CATEQUESIS_ESPECIAL: "ESP"
        }
        
        prefijo = tipo_prefijo.get(self.tipo_nivel, "NIV")
        orden = f"{self.orden_secuencial:02d}"
        
        codigo_base = f"{prefijo}-{orden}"
        codigo = codigo_base
        contador = 1
        
        while self._codigo_exists(codigo):
            codigo = f"{codigo_base}-{contador}"
            contador += 1
        
        self.codigo_nivel = codigo
        return codigo
    
    def _codigo_exists(self, codigo: str) -> bool:
        """Verifica si un código ya existe."""
        try:
            result = self._sp_manager.executor.execute(
                'niveles',
                'existe_codigo',
                {
                    'codigo_nivel': codigo,
                    'excluir_id': self.id_nivel
                }
            )
            return result.get('existe', False)
        except Exception:
            return False
    
    def agregar_contenido(
        self,
        titulo: str,
        descripcion: str,
        numero_encuentro: int,
        objetivos_especificos: List[str] = None,
        actividades: List[str] = None,
        recursos: List[str] = None
    ) -> None:
        """
        Agrega contenido curricular al nivel.
        
        Args:
            titulo: Título del contenido
            descripcion: Descripción del contenido
            numero_encuentro: Número del encuentro
            objetivos_especificos: Objetivos específicos
            actividades: Lista de actividades
            recursos: Recursos necesarios
        """
        contenido = {
            'numero_encuentro': numero_encuentro,
            'titulo': titulo,
            'descripcion': descripcion,
            'objetivos_especificos': objetivos_especificos or [],
            'actividades': actividades or [],
            'recursos': recursos or [],
            'fecha_creacion': date.today().isoformat()
        }
        
        # Verificar que no exista ya contenido para ese encuentro
        for i, cont in enumerate(self.contenidos):
            if cont.get('numero_encuentro') == numero_encuentro:
                self.contenidos[i] = contenido
                return
        
        self.contenidos.append(contenido)
        self.contenidos.sort(key=lambda x: x.get('numero_encuentro', 0))
    
    def remover_contenido(self, numero_encuentro: int) -> bool:
        """
        Remueve contenido curricular.
        
        Args:
            numero_encuentro: Número del encuentro a remover
            
        Returns:
            bool: True si se removió exitosamente
        """
        inicial_len = len(self.contenidos)
        self.contenidos = [
            cont for cont in self.contenidos
            if cont.get('numero_encuentro') != numero_encuentro
        ]
        return len(self.contenidos) < inicial_len
    
    def agregar_objetivo(self, objetivo: str) -> None:
        """Agrega un objetivo al nivel."""
        if objetivo and objetivo not in self.objetivos:
            self.objetivos.append(objetivo)
    
    def remover_objetivo(self, objetivo: str) -> None:
        """Remueve un objetivo del nivel."""
        if objetivo in self.objetivos:
            self.objetivos.remove(objetivo)
    
    def agregar_competencia(self, competencia: str) -> None:
        """Agrega una competencia al nivel."""
        if competencia and competencia not in self.competencias:
            self.competencias.append(competencia)
    
    def agregar_material_didactico(self, material: str) -> None:
        """Agrega material didáctico al nivel."""
        if material and material not in self.material_didactico:
            self.material_didactico.append(material)
    
    def agregar_recurso_necesario(self, recurso: str) -> None:
        """Agrega un recurso necesario."""
        if recurso and recurso not in self.recursos_necesarios:
            self.recursos_necesarios.append(recurso)
    
    def agregar_valor(self, valor: str) -> None:
        """Agrega un valor a desarrollar."""
        if valor and valor not in self.valores_a_desarrollar:
            self.valores_a_desarrollar.append(valor)
    
    def configurar_sacramento(
        self,
        nombre_sacramento: str,
        requisitos: List[str] = None
    ) -> None:
        """
        Configura el sacramento que prepara este nivel.
        
        Args:
            nombre_sacramento: Nombre del sacramento
            requisitos: Lista de requisitos para el sacramento
        """
        self.prepara_sacramento = nombre_sacramento
        self.requisitos_sacramento = requisitos or []
        self.genera_certificado = True
    
    def obtener_nivel_previo(self) -> Optional['Nivel']:
        """
        Obtiene el nivel previo si existe.
        
        Returns:
            Nivel: El nivel previo o None
        """
        if not self.id_nivel_previo:
            return None
        
        return Nivel.find_by_id(self.id_nivel_previo)
    
    def obtener_niveles_siguientes(self) -> List['Nivel']:
        """
        Obtiene los niveles que tienen este como previo.
        
        Returns:
            List: Lista de niveles siguientes
        """
        try:
            result = self._sp_manager.executor.execute(
                'niveles',
                'obtener_niveles_siguientes',
                {'id_nivel_previo': self.id_nivel}
            )
            
            if result.get('success') and result.get('data'):
                return [Nivel(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo niveles siguientes: {str(e)}")
            return []
    
    def verificar_edad_apropiada(self, edad: int) -> bool:
        """
        Verifica si una edad es apropiada para este nivel.
        
        Args:
            edad: Edad a verificar
            
        Returns:
            bool: True si la edad es apropiada
        """
        return self.edad_minima <= edad <= self.edad_maxima
    
    def calcular_progreso_contenido(self) -> Dict[str, Any]:
        """
        Calcula el progreso del contenido curricular.
        
        Returns:
            dict: Información de progreso
        """
        contenidos_definidos = len(self.contenidos)
        contenidos_esperados = self.numero_encuentros
        
        porcentaje_completitud = 0
        if contenidos_esperados > 0:
            porcentaje_completitud = (contenidos_definidos / contenidos_esperados) * 100
        
        return {
            'contenidos_definidos': contenidos_definidos,
            'contenidos_esperados': contenidos_esperados,
            'porcentaje_completitud': min(porcentaje_completitud, 100),
            'esta_completo': contenidos_definidos >= contenidos_esperados
        }
    
    def activar(self) -> None:
        """Activa el nivel."""
        # Verificar que esté completo antes de activar
        progreso = self.calcular_progreso_contenido()
        if not progreso['esta_completo']:
            raise ValidationError(
                f"No se puede activar el nivel. "
                f"Faltan {progreso['contenidos_esperados'] - progreso['contenidos_definidos']} contenidos"
            )
        
        self.estado = EstadoNivel.ACTIVO
        logger.info(f"Nivel {self.nombre} activado")
    
    def desactivar(self) -> None:
        """Desactiva el nivel."""
        self.estado = EstadoNivel.INACTIVO
        logger.info(f"Nivel {self.nombre} desactivado")
    
    def to_dict(self, include_audit: bool = False) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_nivel'] = self.tipo_nivel.value
        data['estado'] = self.estado.value
        data['modalidad'] = self.modalidad.value
        
        return data
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['Nivel']:
        """Busca un nivel por código."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'niveles',
                'obtener_por_codigo',
                {'codigo_nivel': codigo}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando nivel por código {codigo}: {str(e)}")
            return None
    
    @classmethod
    def find_by_tipo(cls, tipo_nivel: TipoNivel) -> List['Nivel']:
        """Busca niveles por tipo."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'niveles',
                'obtener_por_tipo',
                {'tipo_nivel': tipo_nivel.value}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando niveles por tipo {tipo_nivel}: {str(e)}")
            return []
    
    @classmethod
    def find_activos(cls) -> List['Nivel']:
        """Busca todos los niveles activos ordenados secuencialmente."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'niveles',
                'obtener_activos_ordenados',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando niveles activos: {str(e)}")
            return []
    
    @classmethod
    def find_iniciales(cls) -> List['Nivel']:
        """Busca niveles iniciales (sin nivel previo)."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'niveles',
                'obtener_iniciales',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando niveles iniciales: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Nivel':
        """Guarda el nivel con validaciones adicionales."""
        # Generar código si no existe
        if not self.codigo_nivel:
            self.generar_codigo_nivel()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('nivel', Nivel)