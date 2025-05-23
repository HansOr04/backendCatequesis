"""
Configuración de base de datos para el Sistema de Catequesis.
Maneja la conexión con SQL Server y la configuración de stored procedures.
"""

import os
import urllib.parse
from app.config.settings import get_config

config = get_config()


class DatabaseConfig:
    """Configuración específica para la base de datos SQL Server."""
    
    @staticmethod
    def get_connection_string():
        """
        Construye la cadena de conexión para SQL Server.
        
        Returns:
            str: String de conexión completo para pyodbc.
        """
        # Escapar caracteres especiales en la contraseña
        password = urllib.parse.quote_plus(config.DB_PASSWORD)
        
        connection_string = (
            f"DRIVER={{{config.DB_DRIVER}}};"
            f"SERVER={config.DB_SERVER},{config.DB_PORT};"
            f"DATABASE={config.DB_NAME};"
            f"UID={config.DB_USER};"
            f"PWD={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout={config.DB_TIMEOUT};"
        )
        
        return connection_string
    
    @staticmethod
    def get_connection_params():
        """
        Obtiene los parámetros de conexión como diccionario.
        
        Returns:
            dict: Parámetros de conexión.
        """
        return {
            'driver': config.DB_DRIVER,
            'server': config.DB_SERVER,
            'port': config.DB_PORT,
            'database': config.DB_NAME,
            'username': config.DB_USER,
            'password': config.DB_PASSWORD,
            'timeout': config.DB_TIMEOUT,
            'encrypt': True,
            'trust_server_certificate': True
        }
    
    @staticmethod
    def get_sqlalchemy_uri():
        """
        Construye la URI para SQLAlchemy (si se decide usar ORM).
        
        Returns:
            str: URI de SQLAlchemy para SQL Server.
        """
        password = urllib.parse.quote_plus(config.DB_PASSWORD)
        
        uri = (
            f"mssql+pyodbc://{config.DB_USER}:{password}@"
            f"{config.DB_SERVER}:{config.DB_PORT}/{config.DB_NAME}"
            f"?driver={urllib.parse.quote_plus(config.DB_DRIVER)}"
            f"&Encrypt=yes&TrustServerCertificate=yes"
        )
        
        return uri


class StoredProcedureConfig:
    """Configuración y mapeo de stored procedures por esquema."""
    
    # Stored Procedures del esquema Parroquias
    PARROQUIAS_SP = {
        'crear': 'Parroquias.CrearParroquia',
        'obtener': 'Parroquias.ObtenerParroquia',
        'obtener_todas': 'Parroquias.ObtenerTodasParroquias',
        'actualizar': 'Parroquias.ActualizarParroquia',
        'eliminar': 'Parroquias.EliminarParroquia'
    }
    
    # Stored Procedures del esquema Catequesis - Catequizandos
    CATEQUIZANDOS_SP = {
        'crear': 'Catequesis.CrearCatequizando',
        'obtener': 'Catequesis.ObtenerCatequizando',
        'obtener_todos': 'Catequesis.ObtenerTodosCatequizandos',
        'buscar_por_documento': 'Catequesis.BuscarCatequizandoPorDocumento',
        'actualizar': 'Catequesis.ActualizarCatequizando',
        'eliminar': 'Catequesis.EliminarCatequizando'
    }
    
    # Stored Procedures del esquema Catequesis - Niveles
    NIVELES_SP = {
        'crear': 'Catequesis.CrearNivel',
        'obtener': 'Catequesis.ObtenerNivel',
        'obtener_todos': 'Catequesis.ObtenerTodosNiveles',
        'actualizar': 'Catequesis.ActualizarNivel',
        'eliminar': 'Catequesis.EliminarNivel'
    }
    
    # Stored Procedures del esquema Catequesis - Grupos
    GRUPOS_SP = {
        'crear': 'Catequesis.CrearGrupo',
        'obtener': 'Catequesis.ObtenerGrupo',
        'obtener_todos': 'Catequesis.ObtenerTodosGrupos',
        'obtener_por_parroquia': 'Catequesis.ObtenerGruposPorParroquia',
        'obtener_por_nivel': 'Catequesis.ObtenerGruposPorNivel',
        'actualizar': 'Catequesis.ActualizarGrupo',
        'eliminar': 'Catequesis.EliminarGrupo'
    }
    
    # Stored Procedures del esquema Catequesis - Catequistas
    CATEQUISTAS_SP = {
        'crear': 'Catequesis.CrearCatequista',
        'obtener': 'Catequesis.ObtenerCatequista',
        'obtener_todos': 'Catequesis.ObtenerTodosCatequistas',
        'buscar_por_nombre': 'Catequesis.BuscarCatequistaPorNombre',
        'actualizar': 'Catequesis.ActualizarCatequista',
        'eliminar': 'Catequesis.EliminarCatequista'
    }
    
    # Stored Procedures del esquema Catequesis - Representantes
    REPRESENTANTES_SP = {
        'crear': 'Catequesis.CrearRepresentante',
        'obtener': 'Catequesis.ObtenerRepresentante',
        'obtener_todos': 'Catequesis.ObtenerTodosRepresentantes',
        'buscar_por_correo': 'Catequesis.BuscarRepresentantePorCorreo',
        'actualizar': 'Catequesis.ActualizarRepresentante',
        'eliminar': 'Catequesis.EliminarRepresentante'
    }
    
    # Stored Procedures del esquema Catequesis - Padrinos
    PADRINOS_SP = {
        'crear': 'Catequesis.CrearPadrino',
        'obtener': 'Catequesis.ObtenerPadrino',
        'obtener_todos': 'Catequesis.ObtenerTodosPadrinos',
        'buscar_por_nombre': 'Catequesis.BuscarPadrinoPorNombre',
        'actualizar': 'Catequesis.ActualizarPadrino',
        'eliminar': 'Catequesis.EliminarPadrino'
    }
    
    # Stored Procedures del esquema Catequesis - Sacramentos
    SACRAMENTOS_SP = {
        'crear': 'Catequesis.CrearSacramento',
        'obtener': 'Catequesis.ObtenerSacramento',
        'obtener_todos': 'Catequesis.ObtenerTodosSacramentos',
        'actualizar': 'Catequesis.ActualizarSacramento',
        'eliminar': 'Catequesis.EliminarSacramento'
    }