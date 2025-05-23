"""
Configuración principal del Sistema de Catequesis.
Maneja las configuraciones por ambiente (desarrollo, producción, testing).
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class Config:
    """Configuración base compartida entre todos los ambientes."""
    
    # Configuración básica de Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Configuración de base de datos
    DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    DB_SERVER = os.getenv('DB_SERVER', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '1433')
    DB_NAME = os.getenv('DB_NAME', 'SistemaCatequesis')
    DB_USER = os.getenv('DB_USER', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_TIMEOUT = int(os.getenv('DB_TIMEOUT', '30'))
    
    # Configuración JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '86400')))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '2592000')))
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    
    # Configuración de CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS_METHODS = os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE,OPTIONS').split(',')
    CORS_ALLOW_HEADERS = os.getenv('CORS_ALLOW_HEADERS', 'Content-Type,Authorization,X-Requested-With').split(',')
    
    # Configuración de Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATE_LIMIT_STORAGE', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '1000 per hour')
    RATELIMIT_LOGIN = os.getenv('RATE_LIMIT_LOGIN', '5 per minute')
    RATELIMIT_API = os.getenv('RATE_LIMIT_API', '100 per minute')
    
    # Configuración de email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'Sistema Catequesis <noreply@catequesis.com>')
    MAIL_SUBJECT_PREFIX = os.getenv('MAIL_SUBJECT_PREFIX', '[Sistema Catequesis]')
    
    # Configuración de archivos
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf,jpg,jpeg,png,doc,docx').split(','))
    
    # Configuración de PDFs
    PDF_TEMPLATE_FOLDER = os.getenv('PDF_TEMPLATE_FOLDER', 'app/templates/pdf')
    PDF_OUTPUT_FOLDER = os.getenv('PDF_OUTPUT_FOLDER', 'temp/pdf')
    
    # Configuración de cache
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    CACHE_THRESHOLD = int(os.getenv('CACHE_THRESHOLD', '1000'))
    
    # Configuración de logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/catequesis_api.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configuración de notificaciones
    NOTIFICATIONS_ENABLED = os.getenv('NOTIFICATIONS_ENABLED', 'True').lower() in ['true', '1', 'yes']
    NOTIFICATION_EMAIL_ENABLED = os.getenv('NOTIFICATION_EMAIL_ENABLED', 'True').lower() in ['true', '1', 'yes']
    
    # Configuración de backup
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'True').lower() in ['true', '1', 'yes']
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
    BACKUP_FOLDER = os.getenv('BACKUP_FOLDER', 'backups')
    
    # Configuración específica del dominio
    DEFAULT_PARROQUIA_ID = int(os.getenv('DEFAULT_PARROQUIA_ID', '1'))
    MAX_CATEQUIZANDOS_POR_GRUPO = int(os.getenv('MAX_CATEQUIZANDOS_POR_GRUPO', '30'))
    EDAD_MINIMA_CATEQUESIS = int(os.getenv('EDAD_MINIMA_CATEQUESIS', '6'))
    EDAD_MAXIMA_CATEQUESIS = int(os.getenv('EDAD_MAXIMA_CATEQUESIS', '18'))
    
    # Configuración de reportes
    REPORTS_ENABLED = os.getenv('REPORTS_ENABLED', 'True').lower() in ['true', '1', 'yes']
    REPORTS_CACHE_TTL = int(os.getenv('REPORTS_CACHE_TTL', '3600'))
    REPORTS_MAX_EXPORT_RECORDS = int(os.getenv('REPORTS_MAX_EXPORT_RECORDS', '10000'))
    
    # Timezone y localización
    TIMEZONE = os.getenv('TIMEZONE', 'America/Guayaquil')
    LOCALE = os.getenv('LOCALE', 'es_EC')
    DATE_FORMAT = os.getenv('DATE_FORMAT', '%d/%m/%Y')
    DATETIME_FORMAT = os.getenv('DATETIME_FORMAT', '%d/%m/%Y %H:%M:%S')


class DevelopmentConfig(Config):
    """Configuración para ambiente de desarrollo."""
    
    DEBUG = True
    TESTING = False
    
    # Logging más detallado en desarrollo
    LOG_LEVEL = 'DEBUG'
    
    # Cache deshabilitado en desarrollo
    CACHE_TYPE = 'null'
    
    # Rate limiting más permisivo en desarrollo
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Configuración para ambiente de producción."""
    
    DEBUG = False
    TESTING = False
    
    # Logging de producción
    LOG_LEVEL = 'WARNING'
    
    # Cache en producción con Redis
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'redis')
    CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
    
    # Rate limiting estricto en producción
    RATELIMIT_ENABLED = True
    
    # Configuración adicional de seguridad
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Configuración para ambiente de testing."""
    
    DEBUG = True
    TESTING = True
    
    # Base de datos de testing
    DB_NAME = 'SistemaCatequesis_Test'
    
    # JWT con expiración corta para tests
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    
    # Cache deshabilitado en tests
    CACHE_TYPE = 'null'
    
    # Rate limiting deshabilitado en tests
    RATELIMIT_ENABLED = False
    
    # Email deshabilitado en tests
    MAIL_SUPPRESS_SEND = True
    TESTING_EMAIL_BACKEND = True


# Diccionario de configuraciones por ambiente
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """
    Obtiene la configuración basada en la variable de entorno FLASK_ENV.
    
    Returns:
        Config: Clase de configuración correspondiente al ambiente.
    """
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, config_by_name['default'])