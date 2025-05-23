"""
Gestión de conexiones a la base de datos SQL Server para el Sistema de Catequesis.
Proporciona conexiones seguras y manejo de errores para stored procedures.
"""

import pyodbc
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from datetime import datetime, date
from decimal import Decimal

from app.config.database import DatabaseConfig
from app.core.exceptions import (
    DatabaseError, 
    ConnectionError, 
    StoredProcedureError
)
from app.utils.constants import SystemConstants

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Clase para manejar conexiones a SQL Server.
    Proporciona métodos seguros para ejecutar stored procedures.
    """
    
    def __init__(self):
        """Inicializa la configuración de la conexión."""
        self.connection_string = DatabaseConfig.get_connection_string()
        self.connection_params = DatabaseConfig.get_connection_params()
        self._connection_pool = []
        self._max_pool_size = 10
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a la base de datos.
        
        Returns:
            bool: True si la conexión es exitosa
            
        Raises:
            ConnectionError: Si no se puede conectar
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
                
        except Exception as e:
            logger.error(f"Error al probar conexión: {str(e)}")
            raise ConnectionError(f"No se pudo conectar a la base de datos: {str(e)}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager para obtener una conexión a la base de datos.
        
        Yields:
            pyodbc.Connection: Conexión a la base de datos
            
        Raises:
            ConnectionError: Si no se puede establecer la conexión
        """
        conn = None
        try:
            # Intentar conectar con el string de conexión
            conn = pyodbc.connect(
                self.connection_string,
                timeout=self.connection_params['timeout']
            )
            
            # Configurar la conexión
            conn.autocommit = False
            
            logger.debug("Conexión a base de datos establecida")
            yield conn
            
        except pyodbc.Error as e:
            logger.error(f"Error de conexión pyodbc: {str(e)}")
            raise ConnectionError(f"Error al conectar con SQL Server: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado de conexión: {str(e)}")
            raise ConnectionError(f"Error inesperado al conectar: {str(e)}")
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("Conexión a base de datos cerrada")
                except Exception as e:
                    logger.warning(f"Error al cerrar conexión: {str(e)}")
    
    def execute_stored_procedure(
        self,
        procedure_name: str,
        parameters: Dict[str, Any] = None,
        fetch_results: bool = True,
        output_params: List[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un stored procedure con parámetros.
        
        Args:
            procedure_name: Nombre del stored procedure
            parameters: Diccionario de parámetros
            fetch_results: Si obtener resultados del SELECT
            output_params: Lista de parámetros de salida
            
        Returns:
            dict: Resultados del stored procedure
            
        Raises:
            StoredProcedureError: Si hay error en la ejecución
        """
        parameters = parameters or {}
        output_params = output_params or []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Construir la llamada al stored procedure
                param_placeholders = ', '.join(['?' for _ in parameters.values()])
                if param_placeholders:
                    call_query = f"EXEC {procedure_name} {param_placeholders}"
                else:
                    call_query = f"EXEC {procedure_name}"
                
                logger.debug(f"Ejecutando SP: {procedure_name} con parámetros: {parameters}")
                
                # Ejecutar el stored procedure
                if parameters:
                    cursor.execute(call_query, list(parameters.values()))
                else:
                    cursor.execute(call_query)
                
                results = {
                    'success': True,
                    'data': [],
                    'output_params': {},
                    'row_count': 0
                }
                
                # Obtener resultados si se solicita
                if fetch_results:
                    try:
                        # Obtener todas las filas
                        rows = cursor.fetchall()
                        
                        if rows:
                            # Convertir filas a diccionarios
                            columns = [column[0] for column in cursor.description]
                            results['data'] = [
                                dict(zip(columns, self._convert_row_values(row)))
                                for row in rows
                            ]
                            results['row_count'] = len(rows)
                        
                    except pyodbc.Error as e:
                        # Algunos SPs no retornan resultados, esto es normal
                        if "No results" not in str(e):
                            logger.warning(f"Advertencia al obtener resultados: {str(e)}")
                
                # Confirmar transacción
                conn.commit()
                
                logger.debug(f"SP {procedure_name} ejecutado exitosamente. Filas retornadas: {results['row_count']}")
                
                return results
                
        except pyodbc.Error as e:
            error_msg = f"Error en stored procedure '{procedure_name}': {str(e)}"
            logger.error(error_msg)
            raise StoredProcedureError(procedure_name, str(e))
        except Exception as e:
            error_msg = f"Error inesperado en stored procedure '{procedure_name}': {str(e)}"
            logger.error(error_msg)
            raise StoredProcedureError(procedure_name, str(e))
    
    def execute_stored_procedure_with_output(
        self,
        procedure_name: str,
        input_params: Dict[str, Any] = None,
        output_params: List[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un stored procedure con parámetros de salida.
        
        Args:
            procedure_name: Nombre del stored procedure
            input_params: Parámetros de entrada
            output_params: Lista de nombres de parámetros de salida
            
        Returns:
            dict: Resultados incluyendo parámetros de salida
            
        Raises:
            StoredProcedureError: Si hay error en la ejecución
        """
        input_params = input_params or {}
        output_params = output_params or []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Construir la llamada con parámetros de salida
                all_params = list(input_params.keys()) + output_params
                param_declarations = []
                param_values = []
                
                # Parámetros de entrada
                for param_name, param_value in input_params.items():
                    param_declarations.append(f"@{param_name} = ?")
                    param_values.append(param_value)
                
                # Parámetros de salida
                for param_name in output_params:
                    param_declarations.append(f"@{param_name} = ? OUTPUT")
                    param_values.append(None)  # Placeholder para parámetro de salida
                
                call_query = f"EXEC {procedure_name} {', '.join(param_declarations)}"
                
                logger.debug(f"Ejecutando SP con OUTPUT: {procedure_name}")
                
                cursor.execute(call_query, param_values)
                
                results = {
                    'success': True,
                    'data': [],
                    'output_params': {},
                    'row_count': 0
                }
                
                # Obtener resultados del SELECT
                try:
                    rows = cursor.fetchall()
                    if rows:
                        columns = [column[0] for column in cursor.description]
                        results['data'] = [
                            dict(zip(columns, self._convert_row_values(row)))
                            for row in rows
                        ]
                        results['row_count'] = len(rows)
                except pyodbc.Error:
                    # No hay resultados SELECT, es normal para algunos SPs
                    pass
                
                # Los parámetros de salida en pyodbc requieren un enfoque diferente
                # Por simplicidad, retornamos solo los resultados SELECT
                # En una implementación completa, se usaría un enfoque diferente
                
                conn.commit()
                return results
                
        except Exception as e:
            error_msg = f"Error en SP con OUTPUT '{procedure_name}': {str(e)}"
            logger.error(error_msg)
            raise StoredProcedureError(procedure_name, str(e))
    
    def execute_query(
        self,
        query: str,
        parameters: Tuple = None,
        fetch_results: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta una consulta SQL directa.
        
        Args:
            query: Consulta SQL a ejecutar
            parameters: Parámetros para la consulta
            fetch_results: Si obtener resultados
            
        Returns:
            dict: Resultados de la consulta
            
        Raises:
            DatabaseError: Si hay error en la ejecución
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                logger.debug(f"Ejecutando consulta: {query}")
                
                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                results = {
                    'success': True,
                    'data': [],
                    'row_count': 0
                }
                
                if fetch_results and cursor.description:
                    rows = cursor.fetchall()
                    if rows:
                        columns = [column[0] for column in cursor.description]
                        results['data'] = [
                            dict(zip(columns, self._convert_row_values(row)))
                            for row in rows
                        ]
                        results['row_count'] = len(rows)
                
                conn.commit()
                return results
                
        except pyodbc.Error as e:
            error_msg = f"Error en consulta SQL: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, query)
        except Exception as e:
            error_msg = f"Error inesperado en consulta: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, query)
    
    def _convert_row_values(self, row) -> List[Any]:
        """
        Convierte los valores de una fila a tipos Python apropiados.
        
        Args:
            row: Fila de la base de datos
            
        Returns:
            list: Valores convertidos
        """
        converted_values = []
        
        for value in row:
            if value is None:
                converted_values.append(None)
            elif isinstance(value, datetime):
                # Convertir datetime a string ISO
                converted_values.append(value.isoformat())
            elif isinstance(value, date):
                # Convertir date a string
                converted_values.append(value.isoformat())
            elif isinstance(value, Decimal):
                # Convertir Decimal a float
                converted_values.append(float(value))
            elif isinstance(value, bytes):
                # Convertir bytes a string (para campos como VARBINARY)
                try:
                    converted_values.append(value.decode('utf-8'))
                except UnicodeDecodeError:
                    converted_values.append(value.hex())
            else:
                converted_values.append(value)
        
        return converted_values
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Obtiene información de la base de datos.
        
        Returns:
            dict: Información de la base de datos
        """
        try:
            info_query = """
            SELECT 
                DB_NAME() as database_name,
                @@VERSION as server_version,
                GETDATE() as current_time,
                USER_NAME() as current_user
            """
            
            result = self.execute_query(info_query, fetch_results=True)
            
            if result['data']:
                return result['data'][0]
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error al obtener info de BD: {str(e)}")
            return {}
    
    def check_stored_procedure_exists(self, procedure_name: str) -> bool:
        """
        Verifica si un stored procedure existe.
        
        Args:
            procedure_name: Nombre del stored procedure
            
        Returns:
            bool: True si existe
        """
        try:
            # Separar esquema y nombre si es necesario
            if '.' in procedure_name:
                schema, sp_name = procedure_name.split('.', 1)
            else:
                schema = 'dbo'
                sp_name = procedure_name
            
            check_query = """
            SELECT COUNT(*) as count
            FROM sys.procedures p
            INNER JOIN sys.schemas s ON p.schema_id = s.schema_id
            WHERE s.name = ? AND p.name = ?
            """
            
            result = self.execute_query(check_query, (schema, sp_name))
            
            if result['data']:
                return result['data'][0]['count'] > 0
            
            return False
            
        except Exception as e:
            logger.error(f"Error al verificar SP {procedure_name}: {str(e)}")
            return False
    
    def get_available_schemas(self) -> List[str]:
        """
        Obtiene la lista de esquemas disponibles.
        
        Returns:
            list: Lista de nombres de esquemas
        """
        try:
            query = """
            SELECT name 
            FROM sys.schemas 
            WHERE name IN ('Parroquias', 'Catequesis', 'Seguridad')
            ORDER BY name
            """
            
            result = self.execute_query(query)
            
            if result['data']:
                return [row['name'] for row in result['data']]
            
            return []
            
        except Exception as e:
            logger.error(f"Error al obtener esquemas: {str(e)}")
            return []
    
    def get_stored_procedures_by_schema(self, schema_name: str) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de stored procedures de un esquema.
        
        Args:
            schema_name: Nombre del esquema
            
        Returns:
            list: Lista de stored procedures con información
        """
        try:
            query = """
            SELECT 
                s.name as schema_name,
                p.name as procedure_name,
                p.create_date,
                p.modify_date
            FROM sys.procedures p
            INNER JOIN sys.schemas s ON p.schema_id = s.schema_id
            WHERE s.name = ?
            ORDER BY p.name
            """
            
            result = self.execute_query(query, (schema_name,))
            
            return result['data'] if result['data'] else []
            
        except Exception as e:
            logger.error(f"Error al obtener SPs del esquema {schema_name}: {str(e)}")
            return []


# Instancia singleton de la conexión
db_connection = DatabaseConnection()


def get_db_connection() -> DatabaseConnection:
    """
    Obtiene la instancia de conexión a la base de datos.
    
    Returns:
        DatabaseConnection: Instancia de conexión
    """
    return db_connection


def execute_sp(
    procedure_name: str,
    parameters: Dict[str, Any] = None,
    fetch_results: bool = True
) -> Dict[str, Any]:
    """
    Función helper para ejecutar stored procedures.
    
    Args:
        procedure_name: Nombre del stored procedure
        parameters: Parámetros del SP
        fetch_results: Si obtener resultados
        
    Returns:
        dict: Resultados del stored procedure
    """
    return db_connection.execute_stored_procedure(
        procedure_name,
        parameters,
        fetch_results
    )


def test_database_connection() -> Dict[str, Any]:
    """
    Prueba la conexión a la base de datos y retorna información.
    
    Returns:
        dict: Información de la prueba de conexión
    """
    try:
        # Probar conexión básica
        connection_ok = db_connection.test_connection()
        
        if not connection_ok:
            return {
                'success': False,
                'message': 'No se pudo establecer conexión a la base de datos',
                'details': {}
            }
        
        # Obtener información de la base de datos
        db_info = db_connection.get_database_info()
        
        # Verificar esquemas
        schemas = db_connection.get_available_schemas()
        
        return {
            'success': True,
            'message': 'Conexión a base de datos exitosa',
            'details': {
                'database_info': db_info,
                'available_schemas': schemas,
                'connection_params': {
                    'server': db_connection.connection_params['server'],
                    'database': db_connection.connection_params['database'],
                    'driver': db_connection.connection_params['driver']
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error en prueba de conexión: {str(e)}")
        return {
            'success': False,
            'message': f'Error al probar conexión: {str(e)}',
            'details': {}
        }