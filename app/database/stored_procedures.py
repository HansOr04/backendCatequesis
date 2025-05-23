"""
Gestión de Stored Procedures para el Sistema de Catequesis.
Proporciona una interfaz unificada para ejecutar todos los SPs del sistema.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date

from app.database.connection import get_db_connection
from app.config.database import StoredProcedureConfig
from app.core.exceptions import StoredProcedureError, ValidationError
from app.utils.constants import SystemConstants

logger = logging.getLogger(__name__)


class StoredProcedureExecutor:
    """
    Clase base para ejecutar stored procedures de manera segura y consistente.
    """
    
    def __init__(self):
        """Inicializa el ejecutor de stored procedures."""
        self.db_connection = get_db_connection()
        self.sp_config = StoredProcedureConfig()
    
    def execute(
        self,
        schema: str,
        operation: str,
        parameters: Dict[str, Any] = None,
        fetch_results: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta un stored procedure basado en esquema y operación.
        
        Args:
            schema: Esquema del SP (ej: 'catequizandos', 'usuarios')
            operation: Operación a realizar (ej: 'crear', 'obtener')
            parameters: Parámetros para el SP
            fetch_results: Si obtener resultados
            
        Returns:
            dict: Resultados del stored procedure
            
        Raises:
            StoredProcedureError: Si hay error en la ejecución
        """
        try:
            # Obtener nombre del stored procedure
            sp_name = self.sp_config.get_sp_name(schema, operation)
            
            # Limpiar y validar parámetros
            clean_params = self._clean_parameters(parameters or {})
            
            logger.debug(f"Ejecutando {sp_name} con parámetros: {clean_params}")
            
            # Ejecutar stored procedure
            result = self.db_connection.execute_stored_procedure(
                sp_name,
                clean_params,
                fetch_results
            )
            
            return result
            
        except KeyError as e:
            error_msg = f"Stored procedure no encontrado para esquema '{schema}' y operación '{operation}'"
            logger.error(error_msg)
            raise StoredProcedureError("Unknown", error_msg)
        except Exception as e:
            logger.error(f"Error ejecutando SP {schema}.{operation}: {str(e)}")
            raise
    
    def execute_by_name(
        self,
        sp_name: str,
        parameters: Dict[str, Any] = None,
        fetch_results: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta un stored procedure por nombre directo.
        
        Args:
            sp_name: Nombre completo del stored procedure
            parameters: Parámetros para el SP
            fetch_results: Si obtener resultados
            
        Returns:
            dict: Resultados del stored procedure
        """
        try:
            clean_params = self._clean_parameters(parameters or {})
            
            return self.db_connection.execute_stored_procedure(
                sp_name,
                clean_params,
                fetch_results
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando SP {sp_name}: {str(e)}")
            raise
    
    def _clean_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Limpia y convierte parámetros a tipos apropiados para SQL Server.
        
        Args:
            parameters: Parámetros originales
            
        Returns:
            dict: Parámetros limpiados
        """
        clean_params = {}
        
        for key, value in parameters.items():
            # Remover prefijo @ si existe
            clean_key = key.lstrip('@')
            
            # Convertir valores None a NULL
            if value is None:
                clean_params[clean_key] = None
            # Convertir fechas a string ISO
            elif isinstance(value, (datetime, date)):
                clean_params[clean_key] = value.isoformat()
            # Convertir booleanos a bit (0/1)
            elif isinstance(value, bool):
                clean_params[clean_key] = 1 if value else 0
            # Limpiar strings
            elif isinstance(value, str):
                clean_params[clean_key] = value.strip() if value else None
            else:
                clean_params[clean_key] = value
        
        return clean_params


class ParroquiasProcedures:
    """Procedimientos para el esquema Parroquias."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def crear_parroquia(
        self,
        nombre: str,
        direccion: str,
        telefono: str
    ) -> Dict[str, Any]:
        """Crea una nueva parroquia."""
        parameters = {
            'nombre': nombre,
            'direccion': direccion,
            'telefono': telefono
        }
        return self.executor.execute('parroquias', 'crear', parameters)
    
    def obtener_parroquia(self, id_parroquia: int) -> Dict[str, Any]:
        """Obtiene una parroquia por ID."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('parroquias', 'obtener', parameters)
    
    def obtener_todas_parroquias(self) -> Dict[str, Any]:
        """Obtiene todas las parroquias."""
        return self.executor.execute('parroquias', 'obtener_todas')
    
    def actualizar_parroquia(
        self,
        id_parroquia: int,
        nombre: str,
        direccion: str,
        telefono: str
    ) -> Dict[str, Any]:
        """Actualiza una parroquia."""
        parameters = {
            'id_parroquia': id_parroquia,
            'nombre': nombre,
            'direccion': direccion,
            'telefono': telefono
        }
        return self.executor.execute('parroquias', 'actualizar', parameters)
    
    def eliminar_parroquia(self, id_parroquia: int) -> Dict[str, Any]:
        """Elimina una parroquia."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('parroquias', 'eliminar', parameters)


class CatequizandosProcedures:
    """Procedimientos para catequizandos."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def crear_catequizando(
        self,
        nombres: str,
        apellidos: str,
        fecha_nacimiento: Union[str, date],
        documento_identidad: str,
        caso_especial: bool = False
    ) -> Dict[str, Any]:
        """Crea un nuevo catequizando."""
        parameters = {
            'nombres': nombres,
            'apellidos': apellidos,
            'fecha_nacimiento': fecha_nacimiento,
            'documento_identidad': documento_identidad,
            'caso_especial': caso_especial
        }
        return self.executor.execute('catequizandos', 'crear', parameters)
    
    def obtener_catequizando(self, id_catequizando: int) -> Dict[str, Any]:
        """Obtiene un catequizando por ID."""
        parameters = {'id_catequizando': id_catequizando}
        return self.executor.execute('catequizandos', 'obtener', parameters)
    
    def buscar_catequizando_por_documento(self, documento_identidad: str) -> Dict[str, Any]:
        """Busca un catequizando por documento de identidad."""
        parameters = {'documento_identidad': documento_identidad}
        return self.executor.execute('catequizandos', 'buscar_por_documento', parameters)
    
    def obtener_todos_catequizandos(self) -> Dict[str, Any]:
        """Obtiene todos los catequizandos."""
        return self.executor.execute('catequizandos', 'obtener_todos')
    
    def actualizar_catequizando(
        self,
        id_catequizando: int,
        nombres: str,
        apellidos: str,
        fecha_nacimiento: Union[str, date],
        documento_identidad: str,
        caso_especial: bool = False
    ) -> Dict[str, Any]:
        """Actualiza un catequizando."""
        parameters = {
            'id_catequizando': id_catequizando,
            'nombres': nombres,
            'apellidos': apellidos,
            'fecha_nacimiento': fecha_nacimiento,
            'documento_identidad': documento_identidad,
            'caso_especial': caso_especial
        }
        return self.executor.execute('catequizandos', 'actualizar', parameters)
    
    def eliminar_catequizando(self, id_catequizando: int) -> Dict[str, Any]:
        """Elimina un catequizando."""
        parameters = {'id_catequizando': id_catequizando}
        return self.executor.execute('catequizandos', 'eliminar', parameters)


class UsuariosProcedures:
    """Procedimientos para usuarios del sistema."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def crear_usuario(
        self,
        username: str,
        password: str,
        tipo_perfil: str,
        id_parroquia: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crea un nuevo usuario."""
        parameters = {
            'username': username,
            'password': password,
            'tipo_perfil': tipo_perfil,
            'id_parroquia': id_parroquia
        }
        return self.executor.execute('usuarios', 'crear', parameters)
    
    def obtener_usuario_por_username(self, username: str) -> Dict[str, Any]:
        """Obtiene un usuario por nombre de usuario."""
        parameters = {'username': username}
        return self.executor.execute('usuarios', 'obtener_por_username', parameters)
    
    def obtener_usuarios_por_parroquia(self, id_parroquia: int) -> Dict[str, Any]:
        """Obtiene usuarios de una parroquia específica."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('usuarios', 'obtener_por_parroquia', parameters)
    
    def cambiar_contrasena(
        self,
        id_usuario: int,
        password_actual: str,
        password_nueva: str
    ) -> Dict[str, Any]:
        """Cambia la contraseña de un usuario."""
        parameters = {
            'id_usuario': id_usuario,
            'password_actual': password_actual,
            'password_nueva': password_nueva
        }
        return self.executor.execute('usuarios', 'cambiar_contrasena', parameters)


"""
Continuación del Sistema de Gestión de Stored Procedures para Catequesis
"""

class InscripcionesProcedures:
    """Procedimientos para inscripciones."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def crear_inscripcion(
        self,
        id_catequizando: int,
        id_grupo: int,
        id_parroquia: int,
        fecha_inscripcion: Union[str, date] = None,
        pago_realizado: bool = False
    ) -> Dict[str, Any]:
        """Crea una nueva inscripción."""
        parameters = {
            'id_catequizando': id_catequizando,
            'id_grupo': id_grupo,
            'id_parroquia': id_parroquia,
            'fecha_inscripcion': fecha_inscripcion,
            'pago_realizado': pago_realizado
        }
        return self.executor.execute('inscripciones', 'crear', parameters)
    
    def obtener_inscripciones_por_catequizando(self, id_catequizando: int) -> Dict[str, Any]:
        """Obtiene inscripciones de un catequizando."""
        parameters = {'id_catequizando': id_catequizando}
        return self.executor.execute('inscripciones', 'obtener_por_catequizando', parameters)
    
    def obtener_inscripciones_por_grupo(self, id_grupo: int) -> Dict[str, Any]:
        """Obtiene inscripciones de un grupo."""
        parameters = {'id_grupo': id_grupo}
        return self.executor.execute('inscripciones', 'obtener_por_grupo', parameters)
    
    def obtener_inscripciones_por_parroquia(self, id_parroquia: int) -> Dict[str, Any]:
        """Obtiene inscripciones de una parroquia."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('inscripciones', 'obtener_por_parroquia', parameters)
    
    def actualizar_estado_pago(
        self,
        id_inscripcion: int,
        pago_realizado: bool,
        fecha_pago: Union[str, date] = None
    ) -> Dict[str, Any]:
        """Actualiza el estado de pago de una inscripción."""
        parameters = {
            'id_inscripcion': id_inscripcion,
            'pago_realizado': pago_realizado,
            'fecha_pago': fecha_pago
        }
        return self.executor.execute('inscripciones', 'actualizar_pago', parameters)
    
    def cancelar_inscripcion(
        self,
        id_inscripcion: int,
        motivo_cancelacion: str
    ) -> Dict[str, Any]:
        """Cancela una inscripción."""
        parameters = {
            'id_inscripcion': id_inscripcion,
            'motivo_cancelacion': motivo_cancelacion
        }
        return self.executor.execute('inscripciones', 'cancelar', parameters)


class GruposProcedures:
    """Procedimientos para grupos de catequesis."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def crear_grupo(
        self,
        nombre: str,
        nivel_catequesis: str,
        id_parroquia: int,
        id_catequista: Optional[int] = None,
        capacidad_maxima: int = 30,
        horario: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea un nuevo grupo."""
        parameters = {
            'nombre': nombre,
            'nivel_catequesis': nivel_catequesis,
            'id_parroquia': id_parroquia,
            'id_catequista': id_catequista,
            'capacidad_maxima': capacidad_maxima,
            'horario': horario
        }
        return self.executor.execute('grupos', 'crear', parameters)
    
    def obtener_grupo(self, id_grupo: int) -> Dict[str, Any]:
        """Obtiene un grupo por ID."""
        parameters = {'id_grupo': id_grupo}
        return self.executor.execute('grupos', 'obtener', parameters)
    
    def obtener_grupos_por_parroquia(self, id_parroquia: int) -> Dict[str, Any]:
        """Obtiene grupos de una parroquia."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('grupos', 'obtener_por_parroquia', parameters)
    
    def obtener_grupos_por_catequista(self, id_catequista: int) -> Dict[str, Any]:
        """Obtiene grupos de un catequista."""
        parameters = {'id_catequista': id_catequista}
        return self.executor.execute('grupos', 'obtener_por_catequista', parameters)
    
    def obtener_grupos_por_nivel(
        self,
        nivel_catequesis: str,
        id_parroquia: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obtiene grupos por nivel de catequesis."""
        parameters = {
            'nivel_catequesis': nivel_catequesis,
            'id_parroquia': id_parroquia
        }
        return self.executor.execute('grupos', 'obtener_por_nivel', parameters)
    
    def actualizar_grupo(
        self,
        id_grupo: int,
        nombre: str,
        nivel_catequesis: str,
        id_catequista: Optional[int] = None,
        capacidad_maxima: int = 30,
        horario: Optional[str] = None
    ) -> Dict[str, Any]:
        """Actualiza un grupo."""
        parameters = {
            'id_grupo': id_grupo,
            'nombre': nombre,
            'nivel_catequesis': nivel_catequesis,
            'id_catequista': id_catequista,
            'capacidad_maxima': capacidad_maxima,
            'horario': horario
        }
        return self.executor.execute('grupos', 'actualizar', parameters)
    
    def asignar_catequista(self, id_grupo: int, id_catequista: int) -> Dict[str, Any]:
        """Asigna un catequista a un grupo."""
        parameters = {
            'id_grupo': id_grupo,
            'id_catequista': id_catequista
        }
        return self.executor.execute('grupos', 'asignar_catequista', parameters)
    
    def obtener_disponibilidad_grupo(self, id_grupo: int) -> Dict[str, Any]:
        """Obtiene la disponibilidad de cupos en un grupo."""
        parameters = {'id_grupo': id_grupo}
        return self.executor.execute('grupos', 'obtener_disponibilidad', parameters)


class CatequislasProcedures:
    """Procedimientos para catequistas."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def crear_catequista(
        self,
        nombres: str,
        apellidos: str,
        documento_identidad: str,
        telefono: str,
        email: str,
        id_parroquia: int,
        especialidad: Optional[str] = None,
        fecha_certificacion: Union[str, date] = None
    ) -> Dict[str, Any]:
        """Crea un nuevo catequista."""
        parameters = {
            'nombres': nombres,
            'apellidos': apellidos,
            'documento_identidad': documento_identidad,
            'telefono': telefono,
            'email': email,
            'id_parroquia': id_parroquia,
            'especialidad': especialidad,
            'fecha_certificacion': fecha_certificacion
        }
        return self.executor.execute('catequistas', 'crear', parameters)
    
    def obtener_catequista(self, id_catequista: int) -> Dict[str, Any]:
        """Obtiene un catequista por ID."""
        parameters = {'id_catequista': id_catequista}
        return self.executor.execute('catequistas', 'obtener', parameters)
    
    def obtener_catequistas_por_parroquia(self, id_parroquia: int) -> Dict[str, Any]:
        """Obtiene catequistas de una parroquia."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('catequistas', 'obtener_por_parroquia', parameters)
    
    def buscar_catequista_por_documento(self, documento_identidad: str) -> Dict[str, Any]:
        """Busca un catequista por documento."""
        parameters = {'documento_identidad': documento_identidad}
        return self.executor.execute('catequistas', 'buscar_por_documento', parameters)
    
    def obtener_catequistas_disponibles(self, id_parroquia: int) -> Dict[str, Any]:
        """Obtiene catequistas disponibles (sin grupo asignado)."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('catequistas', 'obtener_disponibles', parameters)
    
    def actualizar_catequista(
        self,
        id_catequista: int,
        nombres: str,
        apellidos: str,
        telefono: str,
        email: str,
        especialidad: Optional[str] = None
    ) -> Dict[str, Any]:
        """Actualiza un catequista."""
        parameters = {
            'id_catequista': id_catequista,
            'nombres': nombres,
            'apellidos': apellidos,
            'telefono': telefono,
            'email': email,
            'especialidad': especialidad
        }
        return self.executor.execute('catequistas', 'actualizar', parameters)
    
    def activar_desactivar_catequista(
        self,
        id_catequista: int,
        activo: bool
    ) -> Dict[str, Any]:
        """Activa o desactiva un catequista."""
        parameters = {
            'id_catequista': id_catequista,
            'activo': activo
        }
        return self.executor.execute('catequistas', 'cambiar_estado', parameters)


class AsistenciasProcedures:
    """Procedimientos para control de asistencias."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def registrar_asistencia(
        self,
        id_catequizando: int,
        id_grupo: int,
        fecha_clase: Union[str, date],
        presente: bool = True,
        observaciones: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registra asistencia de un catequizando."""
        parameters = {
            'id_catequizando': id_catequizando,
            'id_grupo': id_grupo,
            'fecha_clase': fecha_clase,
            'presente': presente,
            'observaciones': observaciones
        }
        return self.executor.execute('asistencias', 'registrar', parameters)
    
    def registrar_asistencia_masiva(
        self,
        id_grupo: int,
        fecha_clase: Union[str, date],
        asistencias: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Registra asistencias masivas para un grupo."""
        parameters = {
            'id_grupo': id_grupo,
            'fecha_clase': fecha_clase,
            'asistencias': asistencias
        }
        return self.executor.execute('asistencias', 'registrar_masiva', parameters)
    
    def obtener_asistencias_por_catequizando(
        self,
        id_catequizando: int,
        fecha_inicio: Union[str, date] = None,
        fecha_fin: Union[str, date] = None
    ) -> Dict[str, Any]:
        """Obtiene asistencias de un catequizando."""
        parameters = {
            'id_catequizando': id_catequizando,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        return self.executor.execute('asistencias', 'obtener_por_catequizando', parameters)
    
    def obtener_asistencias_por_grupo(
        self,
        id_grupo: int,
        fecha_clase: Union[str, date] = None
    ) -> Dict[str, Any]:
        """Obtiene asistencias de un grupo."""
        parameters = {
            'id_grupo': id_grupo,
            'fecha_clase': fecha_clase
        }
        return self.executor.execute('asistencias', 'obtener_por_grupo', parameters)
    
    def generar_reporte_asistencia(
        self,
        id_grupo: int,
        fecha_inicio: Union[str, date],
        fecha_fin: Union[str, date]
    ) -> Dict[str, Any]:
        """Genera reporte de asistencia por período."""
        parameters = {
            'id_grupo': id_grupo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        return self.executor.execute('asistencias', 'generar_reporte', parameters)


class CalificacionesProcedures:
    """Procedimientos para calificaciones y evaluaciones."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def registrar_calificacion(
        self,
        id_catequizando: int,
        id_grupo: int,
        tipo_evaluacion: str,
        calificacion: float,
        fecha_evaluacion: Union[str, date],
        observaciones: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registra una calificación."""
        parameters = {
            'id_catequizando': id_catequizando,
            'id_grupo': id_grupo,
            'tipo_evaluacion': tipo_evaluacion,
            'calificacion': calificacion,
            'fecha_evaluacion': fecha_evaluacion,
            'observaciones': observaciones
        }
        return self.executor.execute('calificaciones', 'registrar', parameters)
    
    def obtener_calificaciones_por_catequizando(
        self,
        id_catequizando: int,
        id_grupo: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obtiene calificaciones de un catequizando."""
        parameters = {
            'id_catequizando': id_catequizando,
            'id_grupo': id_grupo
        }
        return self.executor.execute('calificaciones', 'obtener_por_catequizando', parameters)
    
    def obtener_calificaciones_por_grupo(
        self,
        id_grupo: int,
        tipo_evaluacion: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtiene calificaciones de un grupo."""
        parameters = {
            'id_grupo': id_grupo,
            'tipo_evaluacion': tipo_evaluacion
        }
        return self.executor.execute('calificaciones', 'obtener_por_grupo', parameters)
    
    def calcular_promedio_catequizando(
        self,
        id_catequizando: int,
        id_grupo: int
    ) -> Dict[str, Any]:
        """Calcula el promedio de un catequizando."""
        parameters = {
            'id_catequizando': id_catequizando,
            'id_grupo': id_grupo
        }
        return self.executor.execute('calificaciones', 'calcular_promedio', parameters)
    
    def generar_reporte_notas(
        self,
        id_grupo: int,
        periodo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Genera reporte de notas de un grupo."""
        parameters = {
            'id_grupo': id_grupo,
            'periodo': periodo
        }
        return self.executor.execute('calificaciones', 'generar_reporte', parameters)


class ReportesProcedures:
    """Procedimientos para generar reportes del sistema."""
    
    def __init__(self):
        self.executor = StoredProcedureExecutor()
    
    def reporte_inscripciones_por_periodo(
        self,
        fecha_inicio: Union[str, date],
        fecha_fin: Union[str, date],
        id_parroquia: Optional[int] = None
    ) -> Dict[str, Any]:
        """Genera reporte de inscripciones por período."""
        parameters = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'id_parroquia': id_parroquia
        }
        return self.executor.execute('reportes', 'inscripciones_periodo', parameters)
    
    def reporte_estadisticas_parroquia(self, id_parroquia: int) -> Dict[str, Any]:
        """Genera estadísticas generales de una parroquia."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('reportes', 'estadisticas_parroquia', parameters)
    
    def reporte_catequizandos_activos(
        self,
        id_parroquia: Optional[int] = None,
        nivel_catequesis: Optional[str] = None
    ) -> Dict[str, Any]:
        """Genera reporte de catequizandos activos."""
        parameters = {
            'id_parroquia': id_parroquia,
            'nivel_catequesis': nivel_catequesis
        }
        return self.executor.execute('reportes', 'catequizandos_activos', parameters)
    
    def reporte_pagos_pendientes(self, id_parroquia: int) -> Dict[str, Any]:
        """Genera reporte de pagos pendientes."""
        parameters = {'id_parroquia': id_parroquia}
        return self.executor.execute('reportes', 'pagos_pendientes', parameters)
    
    def reporte_certificaciones_proximas(
        self,
        id_parroquia: int,
        meses_anticipacion: int = 2
    ) -> Dict[str, Any]:
        """Genera reporte de catequizandos próximos a certificar."""
        parameters = {
            'id_parroquia': id_parroquia,
            'meses_anticipacion': meses_anticipacion
        }
        return self.executor.execute('reportes', 'certificaciones_proximas', parameters)


# Clase principal que unifica todos los procedimientos
class StoredProcedureManager:
    """
    Gestor principal que proporciona acceso a todos los stored procedures del sistema.
    """
    
    def __init__(self):
        """Inicializa el gestor con todas las clases de procedimientos."""
        self.parroquias = ParroquiasProcedures()
        self.catequizandos = CatequizandosProcedures()
        self.usuarios = UsuariosProcedures()
        self.inscripciones = InscripcionesProcedures()
        self.grupos = GruposProcedures()
        self.catequistas = CatequislasProcedures()
        self.asistencias = AsistenciasProcedures()
        self.calificaciones = CalificacionesProcedures()
        self.reportes = ReportesProcedures()
        
        # Executor directo para casos especiales
        self.executor = StoredProcedureExecutor()
    
    def execute_custom_sp(
        self,
        sp_name: str,
        parameters: Dict[str, Any] = None,
        fetch_results: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta un stored procedure personalizado por nombre.
        
        Args:
            sp_name: Nombre completo del stored procedure
            parameters: Parámetros para el SP
            fetch_results: Si obtener resultados
            
        Returns:
            dict: Resultados del stored procedure
        """
        return self.executor.execute_by_name(sp_name, parameters, fetch_results)
    
    def get_schema_procedures(self, schema: str) -> Optional[object]:
        """
        Obtiene la clase de procedimientos para un esquema específico.
        
        Args:
            schema: Nombre del esquema
            
        Returns:
            object: Clase de procedimientos correspondiente
        """
        schema_map = {
            'parroquias': self.parroquias,
            'catequizandos': self.catequizandos,
            'usuarios': self.usuarios,
            'inscripciones': self.inscripciones,
            'grupos': self.grupos,
            'catequistas': self.catequistas,
            'asistencias': self.asistencias,
            'calificaciones': self.calificaciones,
            'reportes': self.reportes
        }
        return schema_map.get(schema.lower())


# Instancia global del gestor (singleton)
sp_manager = StoredProcedureManager()

# Funciones de conveniencia para acceso rápido
def get_sp_manager() -> StoredProcedureManager:
    """Obtiene la instancia del gestor de stored procedures."""
    return sp_manager

def execute_sp(
    schema: str,
    operation: str,
    parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar stored procedures.
    
    Args:
        schema: Esquema del SP
        operation: Operación a realizar
        parameters: Parámetros para el SP
        
    Returns:
        dict: Resultados del stored procedure
    """
    return sp_manager.executor.execute(schema, operation, parameters)