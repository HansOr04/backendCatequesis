"""
Excepciones personalizadas para el Sistema de Catequesis.
Define todas las excepciones específicas del dominio de negocio.
"""

from typing import Optional, Dict, Any


class CatequesisBaseException(Exception):
    """
    Excepción base para todas las excepciones del Sistema de Catequesis.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: str = None, 
        details: Dict[str, Any] = None,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code


# ===============================================
# EXCEPCIONES DE VALIDACIÓN
# ===============================================

class ValidationError(CatequesisBaseException):
    """Excepción para errores de validación de datos."""
    
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(message, 'VALIDATION_ERROR', details, 400)
        self.field = field


class RequiredFieldError(ValidationError):
    """Excepción para campos requeridos faltantes."""
    
    def __init__(self, field: str):
        message = f"El campo '{field}' es requerido"
        super().__init__(message, field)


class InvalidFormatError(ValidationError):
    """Excepción para formatos de datos inválidos."""
    
    def __init__(self, field: str, expected_format: str):
        message = f"El campo '{field}' tiene un formato inválido. Formato esperado: {expected_format}"
        super().__init__(message, field)


class InvalidRangeError(ValidationError):
    """Excepción para valores fuera de rango."""
    
    def __init__(self, field: str, min_value: Any = None, max_value: Any = None):
        if min_value is not None and max_value is not None:
            message = f"El campo '{field}' debe estar entre {min_value} y {max_value}"
        elif min_value is not None:
            message = f"El campo '{field}' debe ser mayor o igual a {min_value}"
        elif max_value is not None:
            message = f"El campo '{field}' debe ser menor o igual a {max_value}"
        else:
            message = f"El campo '{field}' está fuera del rango permitido"
        super().__init__(message, field)


# ===============================================
# EXCEPCIONES DE BASE DE DATOS
# ===============================================

class DatabaseError(CatequesisBaseException):
    """Excepción base para errores de base de datos."""
    
    def __init__(self, message: str, query: str = None, details: Dict[str, Any] = None):
        super().__init__(message, 'DATABASE_ERROR', details, 500)
        self.query = query


class ConnectionError(DatabaseError):
    """Excepción para errores de conexión a la base de datos."""
    
    def __init__(self, message: str = "Error de conexión a la base de datos"):
        super().__init__(message, error_code='CONNECTION_ERROR')


class StoredProcedureError(DatabaseError):
    """Excepción para errores en stored procedures."""
    
    def __init__(self, procedure_name: str, message: str, details: Dict[str, Any] = None):
        full_message = f"Error en stored procedure '{procedure_name}': {message}"
        super().__init__(full_message, error_code='STORED_PROCEDURE_ERROR', details=details)
        self.procedure_name = procedure_name


class DuplicateRecordError(DatabaseError):
    """Excepción para registros duplicados."""
    
    def __init__(self, table: str, field: str, value: str):
        message = f"Ya existe un registro en '{table}' con {field} = '{value}'"
        super().__init__(message, error_code='DUPLICATE_RECORD', status_code=409)
        self.table = table
        self.field = field
        self.value = value


class RecordNotFoundError(DatabaseError):
    """Excepción para registros no encontrados."""
    
    def __init__(self, entity: str, identifier: str, value: str):
        message = f"No se encontró {entity} con {identifier} = '{value}'"
        super().__init__(message, error_code='RECORD_NOT_FOUND', status_code=404)
        self.entity = entity
        self.identifier = identifier
        self.value = value


class ForeignKeyError(DatabaseError):
    """Excepción para errores de clave foránea."""
    
    def __init__(self, message: str, referenced_table: str = None):
        super().__init__(message, error_code='FOREIGN_KEY_ERROR', status_code=409)
        self.referenced_table = referenced_table


# ===============================================
# EXCEPCIONES DE AUTENTICACIÓN Y AUTORIZACIÓN
# ===============================================

class AuthenticationError(CatequesisBaseException):
    """Excepción base para errores de autenticación."""
    
    def __init__(self, message: str = "Error de autenticación"):
        super().__init__(message, 'AUTHENTICATION_ERROR', status_code=401)


class InvalidCredentialsError(AuthenticationError):
    """Excepción para credenciales inválidas."""
    
    def __init__(self, message: str = "Credenciales inválidas"):
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Excepción para tokens expirados."""
    
    def __init__(self, message: str = "Token de acceso expirado"):
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Excepción para tokens inválidos."""
    
    def __init__(self, message: str = "Token de acceso inválido"):
        super().__init__(message)


class AuthorizationError(CatequesisBaseException):
    """Excepción base para errores de autorización."""
    
    def __init__(self, message: str = "No tiene permisos para realizar esta acción"):
        super().__init__(message, 'AUTHORIZATION_ERROR', status_code=403)


class InsufficientPermissionsError(AuthorizationError):
    """Excepción para permisos insuficientes."""
    
    def __init__(self, required_permission: str):
        message = f"Se requiere el permiso '{required_permission}' para realizar esta acción"
        super().__init__(message)
        self.required_permission = required_permission


# ===============================================
# EXCEPCIONES DE LÓGICA DE NEGOCIO
# ===============================================

class BusinessLogicError(CatequesisBaseException):
    """Excepción base para errores de lógica de negocio."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, 'BUSINESS_LOGIC_ERROR', details, 422)


class InvalidStateError(BusinessLogicError):
    """Excepción para estados inválidos en el flujo de negocio."""
    
    def __init__(self, entity: str, current_state: str, required_state: str):
        message = f"{entity} está en estado '{current_state}', se requiere estado '{required_state}'"
        super().__init__(message)
        self.entity = entity
        self.current_state = current_state
        self.required_state = required_state


class RequirementNotMetError(BusinessLogicError):
    """Excepción para requisitos no cumplidos."""
    
    def __init__(self, requirement: str, entity: str):
        message = f"{entity} no cumple con el requisito: {requirement}"
        super().__init__(message)
        self.requirement = requirement
        self.entity = entity


class CapacityExceededError(BusinessLogicError):
    """Excepción para capacidad excedida."""
    
    def __init__(self, entity: str, current_count: int, max_capacity: int):
        message = f"{entity} ha excedido su capacidad máxima ({current_count}/{max_capacity})"
        super().__init__(message)
        self.entity = entity
        self.current_count = current_count
        self.max_capacity = max_capacity


# ===============================================
# EXCEPCIONES ESPECÍFICAS DEL DOMINIO CATEQUESIS
# ===============================================

class CatequizandoError(BusinessLogicError):
    """Excepción para errores relacionados con catequizandos."""
    pass


class BautismoRequiredError(CatequizandoError):
    """Excepción para catequizandos sin bautismo registrado."""
    
    def __init__(self, catequizando_id: int):
        message = f"El catequizando {catequizando_id} debe tener su bautismo registrado para inscribirse"
        super().__init__(message)
        self.catequizando_id = catequizando_id


class InvalidLevelProgressionError(CatequizandoError):
    """Excepción para progresión inválida de niveles."""
    
    def __init__(self, catequizando_id: int, current_level: str, target_level: str):
        message = f"El catequizando {catequizando_id} no puede avanzar de '{current_level}' a '{target_level}'"
        super().__init__(message)
        self.catequizando_id = catequizando_id
        self.current_level = current_level
        self.target_level = target_level


class InsufficientAttendanceError(CatequizandoError):
    """Excepción para asistencia insuficiente."""
    
    def __init__(self, catequizando_id: int, attendance_percentage: float, required_percentage: float):
        message = f"El catequizando {catequizando_id} tiene {attendance_percentage}% de asistencia, se requiere {required_percentage}%"
        super().__init__(message)
        self.catequizando_id = catequizando_id
        self.attendance_percentage = attendance_percentage
        self.required_percentage = required_percentage


class GrupoError(BusinessLogicError):
    """Excepción para errores relacionados con grupos."""
    pass


class GroupCapacityError(GrupoError):
    """Excepción para capacidad de grupo excedida."""
    
    def __init__(self, grupo_id: int, current_count: int, max_capacity: int):
        message = f"El grupo {grupo_id} ha alcanzado su capacidad máxima ({current_count}/{max_capacity})"
        super().__init__(message)
        self.grupo_id = grupo_id
        self.current_count = current_count
        self.max_capacity = max_capacity


class CatequistNotAssignedError(GrupoError):
    """Excepción para grupos sin catequistas asignados."""
    
    def __init__(self, grupo_id: int):
        message = f"El grupo {grupo_id} debe tener al menos un catequista asignado"
        super().__init__(message)
        self.grupo_id = grupo_id


class PaymentError(BusinessLogicError):
    """Excepción para errores de pagos."""
    pass


class PaymentAlreadyProcessedError(PaymentError):
    """Excepción para pagos ya procesados."""
    
    def __init__(self, inscripcion_id: int):
        message = f"La inscripción {inscripcion_id} ya tiene el pago procesado"
        super().__init__(message)
        self.inscripcion_id = inscripcion_id


class PaymentRequiredError(PaymentError):
    """Excepción para pagos requeridos."""
    
    def __init__(self, inscripcion_id: int):
        message = f"Se requiere pago para la inscripción {inscripcion_id}"
        super().__init__(message)
        self.inscripcion_id = inscripcion_id


# ===============================================
# EXCEPCIONES DE CONFIGURACIÓN Y SISTEMA
# ===============================================

class ConfigurationError(CatequesisBaseException):
    """Excepción para errores de configuración."""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, 'CONFIGURATION_ERROR', status_code=500)
        self.config_key = config_key


class ExternalServiceError(CatequesisBaseException):
    """Excepción para errores de servicios externos."""
    
    def __init__(self, service_name: str, message: str, details: Dict[str, Any] = None):
        full_message = f"Error en servicio externo '{service_name}': {message}"
        super().__init__(full_message, 'EXTERNAL_SERVICE_ERROR', details, 503)
        self.service_name = service_name


class EmailServiceError(ExternalServiceError):
    """Excepción para errores del servicio de email."""
    
    def __init__(self, message: str, recipient: str = None):
        super().__init__('EmailService', message)
        self.recipient = recipient


class PDFGenerationError(ExternalServiceError):
    """Excepción para errores de generación de PDF."""
    
    def __init__(self, message: str, template: str = None):
        super().__init__('PDFService', message)
        self.template = template


# ===============================================
# EXCEPCIONES DE RATE LIMITING
# ===============================================

class RateLimitExceededError(CatequesisBaseException):
    """Excepción para límite de requests excedido."""
    
    def __init__(self, limit: str, retry_after: int = None):
        message = f"Límite de requests excedido: {limit}"
        super().__init__(message, 'RATE_LIMIT_EXCEEDED', status_code=429)
        self.limit = limit
        self.retry_after = retry_after