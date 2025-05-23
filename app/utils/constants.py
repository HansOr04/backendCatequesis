"""
Constantes para el Sistema de Catequesis.
Define todas las constantes utilizadas en el sistema.
"""

from enum import Enum


# ===============================================
# CONSTANTES GENERALES DEL SISTEMA
# ===============================================

class SystemConstants:
    """Constantes generales del sistema."""
    
    # Información del sistema
    SYSTEM_NAME = "Sistema de Catequesis"
    SYSTEM_VERSION = "1.0.0"
    API_VERSION = "v1"
    
    # Configuración por defecto
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1
    
    # Timeouts y límites
    DEFAULT_TIMEOUT = 30
    MAX_UPLOAD_SIZE = 16 * 1024 * 1024  # 16MB
    MAX_EXPORT_RECORDS = 10000
    
    # Formatos de fecha
    DATE_FORMAT = "%d/%m/%Y"
    DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"
    TIME_FORMAT = "%H:%M:%S"
    
    # Timezone
    DEFAULT_TIMEZONE = "America/Guayaquil"
    
    # Configuración de cache
    CACHE_TTL_SHORT = 300    # 5 minutos
    CACHE_TTL_MEDIUM = 1800  # 30 minutos
    CACHE_TTL_LONG = 3600    # 1 hora


# ===============================================
# TIPOS DE PERFIL DE USUARIO
# ===============================================

class UserProfileType(Enum):
    """Tipos de perfil de usuario en el sistema."""
    
    ADMIN = "admin"
    SECRETARIA = "secretaria"
    CATEQUISTA = "catequista"
    PARROCO = "parroco"
    CONSULTA = "consulta"


# ===============================================
# TIPOS DE CATEQUISTA
# ===============================================

class CatequistaType(Enum):
    """Tipos de catequista."""
    
    PRINCIPAL = "principal"
    APOYO = "apoyo"


# ===============================================
# ESTADOS DE PAGO
# ===============================================

class PaymentStatus(Enum):
    """Estados de pago de inscripción."""
    
    PENDING = "pendiente"
    PAID = "pagado"
    OVERDUE = "vencido"
    CANCELLED = "cancelado"


# ===============================================
# MÉTODOS DE PAGO
# ===============================================

class PaymentMethod(Enum):
    """Métodos de pago disponibles."""
    
    CASH = "efectivo"
    TRANSFER = "transferencia"
    CARD = "tarjeta"
    CHECK = "cheque"


# ===============================================
# TIPOS DE SACRAMENTO
# ===============================================

class SacramentType(Enum):
    """Tipos de sacramento."""
    
    BAUTISMO = "Bautismo"
    RECONCILIACION = "Reconciliación"
    EUCARISTIA = "Eucaristía"
    CONFIRMACION = "Confirmación"


# ===============================================
# TIPOS DE NOTIFICACIÓN
# ===============================================

class NotificationType(Enum):
    """Tipos de notificación del sistema."""
    
    # Notificaciones de inscripción
    INSCRIPCION_CONFIRMADA = "inscripcion_confirmada"
    PAGO_CONFIRMADO = "pago_confirmado"
    PAGO_VENCIDO = "pago_vencido"
    
    # Notificaciones de asistencia
    ASISTENCIA_BAJA = "asistencia_baja"
    FALTA_RECURRENTE = "falta_recurrente"
    
    # Notificaciones de certificación
    CERTIFICADO_LISTO = "certificado_listo"
    REQUISITOS_COMPLETADOS = "requisitos_completados"
    
    # Notificaciones de eventos
    INICIO_CATEQUESIS = "inicio_catequesis"
    FIN_PERIODO = "fin_periodo"
    CONFIRMACION_PROXIMA = "confirmacion_proxima"
    
    # Notificaciones administrativas
    TRASLADO_PARROQUIA = "traslado_parroquia"
    CAMBIO_GRUPO = "cambio_grupo"
    RECORDATORIO_GENERAL = "recordatorio_general"


# ===============================================
# ESTADOS DE CERTIFICADO
# ===============================================

class CertificateStatus(Enum):
    """Estados de certificado."""
    
    PENDING = "pendiente"
    APPROVED = "aprobado"
    REJECTED = "rechazado"
    ISSUED = "emitido"


# ===============================================
# TIPOS DE RECORDATORIO
# ===============================================

class ReminderType(Enum):
    """Tipos de recordatorio automático."""
    
    INICIO_INSCRIPCIONES = "inicio_inscripciones"
    FIN_INSCRIPCIONES = "fin_inscripciones"
    INICIO_CATEQUESIS = "inicio_catequesis"
    FINALIZACION_NIVEL = "finalizacion_nivel"
    CONFIRMACION_PROXIMA = "confirmacion_proxima"
    PAGO_VENCIDO = "pago_vencido"
    ASISTENCIA_BAJA = "asistencia_baja"


# ===============================================
# CONSTANTES DE VALIDACIÓN
# ===============================================

class ValidationConstants:
    """Constantes para validación de datos."""
    
    # Longitudes de campos
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 100
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 255
    
    # Documento de identidad (Ecuador)
    CEDULA_LENGTH = 10
    PASSPORT_MIN_LENGTH = 6
    PASSPORT_MAX_LENGTH = 20
    
    # Teléfono
    PHONE_MIN_LENGTH = 7
    PHONE_MAX_LENGTH = 20
    
    # Email
    MAX_EMAIL_LENGTH = 100
    
    # Direcciones
    MAX_ADDRESS_LENGTH = 255
    
    # Edades
    MIN_CATEQUESIS_AGE = 6
    MAX_CATEQUESIS_AGE = 18
    MIN_CATEQUISTA_AGE = 16
    
    # Grupos
    MAX_CATEQUIZANDOS_PER_GROUP = 30
    MIN_CATEQUIZANDOS_PER_GROUP = 5
    
    # Asistencia
    MIN_ATTENDANCE_PERCENTAGE = 75.0
    MIN_ATTENDANCE_SESSIONS = 3


# ===============================================
# EXPRESIONES REGULARES
# ===============================================

class RegexPatterns:
    """Patrones de expresiones regulares para validación."""
    
    # Documento de identidad ecuatoriano
    CEDULA_PATTERN = r'^\d{10}$'
    
    # Teléfono (formato ecuatoriano)
    PHONE_PATTERN = r'^(\+593|0)[0-9]{8,9}$'
    MOBILE_PATTERN = r'^(\+593|0)[9][0-9]{8}$'
    
    # Email
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Nombres (solo letras, espacios y algunos caracteres especiales)
    NAME_PATTERN = r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\-'\.]+$"
    
    # Código postal (Ecuador)
    POSTAL_CODE_PATTERN = r'^\d{6}$'
    
    # Placa de vehículo (Ecuador)
    LICENSE_PLATE_PATTERN = r'^[A-Z]{3}-\d{3,4}$'


# ===============================================
# MENSAJES DEL SISTEMA
# ===============================================

class SystemMessages:
    """Mensajes estándar del sistema."""
    
    # Mensajes de éxito
    SUCCESS_CREATED = "Recurso creado exitosamente"
    SUCCESS_UPDATED = "Recurso actualizado exitosamente"
    SUCCESS_DELETED = "Recurso eliminado exitosamente"
    SUCCESS_LOGIN = "Inicio de sesión exitoso"
    SUCCESS_LOGOUT = "Cierre de sesión exitoso"
    
    # Mensajes de error
    ERROR_NOT_FOUND = "Recurso no encontrado"
    ERROR_UNAUTHORIZED = "No autorizado"
    ERROR_FORBIDDEN = "Acceso prohibido"
    ERROR_BAD_REQUEST = "Solicitud inválida"
    ERROR_INTERNAL_SERVER = "Error interno del servidor"
    ERROR_VALIDATION = "Error de validación"
    ERROR_DUPLICATE = "El recurso ya existe"
    
    # Mensajes específicos de catequesis
    ERROR_BAUTISMO_REQUIRED = "Se requiere tener el bautismo registrado"
    ERROR_INVALID_LEVEL_PROGRESSION = "Progresión de nivel inválida"
    ERROR_INSUFFICIENT_ATTENDANCE = "Asistencia insuficiente"
    ERROR_GROUP_CAPACITY_EXCEEDED = "Capacidad del grupo excedida"
    ERROR_PAYMENT_REQUIRED = "Se requiere pago"
    ERROR_ALREADY_ENROLLED = "Ya está inscrito en este nivel"
    
    # Mensajes de validación
    VALIDATION_REQUIRED_FIELD = "Este campo es requerido"
    VALIDATION_INVALID_FORMAT = "Formato inválido"
    VALIDATION_INVALID_LENGTH = "Longitud inválida"
    VALIDATION_INVALID_RANGE = "Valor fuera de rango"
    VALIDATION_INVALID_EMAIL = "Formato de email inválido"
    VALIDATION_INVALID_PHONE = "Formato de teléfono inválido"
    VALIDATION_INVALID_CEDULA = "Cédula inválida"


# ===============================================
# CÓDIGOS DE ERROR
# ===============================================

class ErrorCodes:
    """Códigos de error del sistema."""
    
    # Errores generales
    GENERIC_ERROR = "GENERIC_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    
    # Errores de base de datos
    DATABASE_ERROR = "DATABASE_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    STORED_PROCEDURE_ERROR = "STORED_PROCEDURE_ERROR"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    FOREIGN_KEY_ERROR = "FOREIGN_KEY_ERROR"
    
    # Errores de autenticación
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Errores de negocio
    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"
    INVALID_STATE = "INVALID_STATE"
    REQUIREMENT_NOT_MET = "REQUIREMENT_NOT_MET"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    
    # Errores específicos de catequesis
    BAUTISMO_REQUIRED = "BAUTISMO_REQUIRED"
    INVALID_LEVEL_PROGRESSION = "INVALID_LEVEL_PROGRESSION"
    INSUFFICIENT_ATTENDANCE = "INSUFFICIENT_ATTENDANCE"
    GROUP_CAPACITY_ERROR = "GROUP_CAPACITY_ERROR"
    PAYMENT_ERROR = "PAYMENT_ERROR"


# ===============================================
# CONFIGURACIÓN DE ARCHIVOS
# ===============================================

class FileConstants:
    """Constantes para manejo de archivos."""
    
    # Extensiones permitidas
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
    ALLOWED_ALL_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS
    
    # Tamaños máximos
    MAX_IMAGE_SIZE = 5 * 1024 * 1024      # 5MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Directorios
    UPLOAD_DIR = "uploads"
    TEMP_DIR = "temp"
    BACKUP_DIR = "backups"
    REPORTS_DIR = "reports"
    CERTIFICATES_DIR = "certificates"
    
    # Tipos MIME
    IMAGE_MIME_TYPES = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif'
    }
    
    DOCUMENT_MIME_TYPES = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain'
    }


# ===============================================
# CONFIGURACIÓN DE REPORTES
# ===============================================

class ReportConstants:
    """Constantes para generación de reportes."""
    
    # Tipos de reporte
    REPORT_ATTENDANCE = "asistencia"
    REPORT_PAYMENTS = "pagos"
    REPORT_CERTIFICATES = "certificados"
    REPORT_STATISTICS = "estadisticas"
    REPORT_ENROLLMENT = "inscripciones"
    
    # Formatos de exportación
    FORMAT_PDF = "pdf"
    FORMAT_EXCEL = "excel"
    FORMAT_CSV = "csv"
    
    # Configuración de PDF
    PDF_PAGE_SIZE = "A4"
    PDF_MARGIN = 72  # puntos (1 pulgada)
    
    # Configuración de Excel
    EXCEL_SHEET_NAME = "Datos"
    EXCEL_MAX_ROWS = 65536


# ===============================================
# CONFIGURACIÓN DE EMAIL
# ===============================================

class EmailConstants:
    """Constantes para envío de emails."""
    
    # Tipos de plantilla
    TEMPLATE_WELCOME = "welcome"
    TEMPLATE_ENROLLMENT_CONFIRMATION = "enrollment_confirmation"
    TEMPLATE_PAYMENT_CONFIRMATION = "payment_confirmation"
    TEMPLATE_CERTIFICATE_READY = "certificate_ready"
    TEMPLATE_REMINDER = "reminder"
    TEMPLATE_PASSWORD_RESET = "password_reset"
    
    # Configuración
    DEFAULT_SENDER = "Sistema de Catequesis"
    REPLY_TO = "noreply@catequesis.com"
    
    # Prioridades
    PRIORITY_HIGH = "high"
    PRIORITY_NORMAL = "normal"
    PRIORITY_LOW = "low"


# ===============================================
# HTTP STATUS CODES PERSONALIZADOS
# ===============================================

class HTTPStatus:
    """Códigos de estado HTTP utilizados en el sistema."""
    
    # Códigos de éxito
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # Códigos de redirección
    MOVED_PERMANENTLY = 301
    FOUND = 302
    NOT_MODIFIED = 304
    
    # Códigos de error del cliente
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # Códigos de error del servidor
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504