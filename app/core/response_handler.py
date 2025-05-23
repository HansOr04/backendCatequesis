"""
Manejador de respuestas estandarizado para el Sistema de Catequesis.
Proporciona un formato consistente para todas las respuestas de la API.
"""

from typing import Any, Dict, List, Union
from datetime import datetime
from flask import jsonify, Response
from app.core.exceptions import CatequesisBaseException


class ResponseHandler:
    """
    Clase para manejar respuestas estandarizadas de la API.
    Proporciona métodos para diferentes tipos de respuestas.
    """
    
    @staticmethod
    def success(
        data: Any = None, 
        message: str = "Operación exitosa",
        status_code: int = 200,
        meta: Dict[str, Any] = None
    ) -> Response:
        """
        Crea una respuesta exitosa estandarizada.
        
        Args:
            data: Datos a incluir en la respuesta
            message: Mensaje descriptivo
            status_code: Código de estado HTTP
            meta: Metadatos adicionales (paginación, etc.)
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        response_data = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code
        }
        
        if meta:
            response_data["meta"] = meta
            
        return jsonify(response_data), status_code
    
    @staticmethod
    def error(
        message: str = "Ha ocurrido un error",
        error_code: str = "GENERIC_ERROR",
        status_code: int = 500,
        details: Dict[str, Any] = None,
        field_errors: Dict[str, List[str]] = None
    ) -> Response:
        """
        Crea una respuesta de error estandarizada.
        
        Args:
            message: Mensaje de error
            error_code: Código de error interno
            status_code: Código de estado HTTP
            details: Detalles adicionales del error
            field_errors: Errores específicos por campo
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        response_data = {
            "success": False,
            "message": message,
            "error_code": error_code,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code
        }
        
        if details:
            response_data["details"] = details
            
        if field_errors:
            response_data["field_errors"] = field_errors
            
        return jsonify(response_data), status_code
    
    @staticmethod
    def from_exception(exception: CatequesisBaseException) -> Response:
        """
        Crea una respuesta de error a partir de una excepción personalizada.
        
        Args:
            exception: Excepción del sistema de catequesis
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.error(
            message=exception.message,
            error_code=exception.error_code,
            status_code=exception.status_code,
            details=exception.details
        )
    
    @staticmethod
    def created(
        data: Any = None, 
        message: str = "Recurso creado exitosamente",
        resource_id: Union[int, str] = None
    ) -> Response:
        """
        Crea una respuesta para recursos creados (201).
        
        Args:
            data: Datos del recurso creado
            message: Mensaje descriptivo
            resource_id: ID del recurso creado
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        meta = {"resource_id": resource_id} if resource_id else None
        return ResponseHandler.success(data, message, 201, meta)
    
    @staticmethod
    def updated(
        data: Any = None, 
        message: str = "Recurso actualizado exitosamente"
    ) -> Response:
        """
        Crea una respuesta para recursos actualizados (200).
        
        Args:
            data: Datos del recurso actualizado
            message: Mensaje descriptivo
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.success(data, message, 200)
    
    @staticmethod
    def deleted(message: str = "Recurso eliminado exitosamente") -> Response:
        """
        Crea una respuesta para recursos eliminados (200).
        
        Args:
            message: Mensaje descriptivo
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.success(None, message, 200)
    
    @staticmethod
    def not_found(
        entity: str = "Recurso", 
        identifier: str = None
    ) -> Response:
        """
        Crea una respuesta para recursos no encontrados (404).
        
        Args:
            entity: Nombre de la entidad
            identifier: Identificador buscado
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        if identifier:
            message = f"{entity} con identificador '{identifier}' no encontrado"
        else:
            message = f"{entity} no encontrado"
            
        return ResponseHandler.error(message, "NOT_FOUND", 404)
    
    @staticmethod
    def bad_request(
        message: str = "Solicitud inválida",
        field_errors: Dict[str, List[str]] = None
    ) -> Response:
        """
        Crea una respuesta para solicitudes inválidas (400).
        
        Args:
            message: Mensaje de error
            field_errors: Errores específicos por campo
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.error(message, "BAD_REQUEST", 400, field_errors=field_errors)
    
    @staticmethod
    def unauthorized(message: str = "No autorizado") -> Response:
        """
        Crea una respuesta para acceso no autorizado (401).
        
        Args:
            message: Mensaje de error
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.error(message, "UNAUTHORIZED", 401)
    
    @staticmethod
    def forbidden(message: str = "Acceso prohibido") -> Response:
        """
        Crea una respuesta para acceso prohibido (403).
        
        Args:
            message: Mensaje de error
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.error(message, "FORBIDDEN", 403)
    
    @staticmethod
    def conflict(
        message: str = "Conflicto con el estado actual del recurso",
        details: Dict[str, Any] = None
    ) -> Response:
        """
        Crea una respuesta para conflictos (409).
        
        Args:
            message: Mensaje de error
            details: Detalles del conflicto
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.error(message, "CONFLICT", 409, details)
    
    @staticmethod
    def unprocessable_entity(
        message: str = "Entidad no procesable",
        field_errors: Dict[str, List[str]] = None
    ) -> Response:
        """
        Crea una respuesta para entidades no procesables (422).
        
        Args:
            message: Mensaje de error
            field_errors: Errores de validación por campo
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.error(message, "UNPROCESSABLE_ENTITY", 422, field_errors=field_errors)
    
    @staticmethod
    def internal_server_error(
        message: str = "Error interno del servidor",
        details: Dict[str, Any] = None
    ) -> Response:
        """
        Crea una respuesta para errores internos del servidor (500).
        
        Args:
            message: Mensaje de error
            details: Detalles del error (solo en desarrollo)
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.error(message, "INTERNAL_SERVER_ERROR", 500, details)
    
    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str = "Datos obtenidos exitosamente"
    ) -> Response:
        """
        Crea una respuesta paginada estandarizada.
        
        Args:
            data: Lista de datos paginados
            page: Página actual
            per_page: Elementos por página
            total: Total de elementos
            message: Mensaje descriptivo
            
        Returns:
            Response: Respuesta JSON de Flask con metadatos de paginación
        """
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        meta = {
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": page + 1 if has_next else None,
                "prev_page": page - 1 if has_prev else None
            }
        }
        
        return ResponseHandler.success(data, message, 200, meta)
    
    @staticmethod
    def collection(
        data: List[Any],
        total: int = None,
        message: str = "Colección obtenida exitosamente"
    ) -> Response:
        """
        Crea una respuesta para colecciones de datos.
        
        Args:
            data: Lista de datos
            total: Total de elementos (si es diferente al tamaño de data)
            message: Mensaje descriptivo
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        meta = {
            "count": len(data),
            "total": total if total is not None else len(data)
        }
        
        return ResponseHandler.success(data, message, 200, meta)
    
    @staticmethod
    def no_content(message: str = "Sin contenido") -> Response:
        """
        Crea una respuesta sin contenido (204).
        
        Args:
            message: Mensaje descriptivo
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        return ResponseHandler.success(None, message, 204)
    
    @staticmethod
    def accepted(
        message: str = "Solicitud aceptada para procesamiento",
        task_id: str = None
    ) -> Response:
        """
        Crea una respuesta para solicitudes aceptadas (202).
        Útil para operaciones asíncronas.
        
        Args:
            message: Mensaje descriptivo
            task_id: ID de la tarea asíncrona
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        meta = {"task_id": task_id} if task_id else None
        return ResponseHandler.success(None, message, 202, meta)
    
    @staticmethod
    def rate_limit_exceeded(
        limit: str,
        retry_after: int = None
    ) -> Response:
        """
        Crea una respuesta para límite de velocidad excedido (429).
        
        Args:
            limit: Descripción del límite
            retry_after: Segundos para reintentar
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        message = f"Límite de velocidad excedido: {limit}"
        details = {"retry_after": retry_after} if retry_after else None
        
        response = ResponseHandler.error(message, "RATE_LIMIT_EXCEEDED", 429, details)
        
        if retry_after:
            response[0].headers['Retry-After'] = str(retry_after)
            
        return response
    
    @staticmethod
    def service_unavailable(
        service_name: str = None,
        message: str = None
    ) -> Response:
        """
        Crea una respuesta para servicio no disponible (503).
        
        Args:
            service_name: Nombre del servicio no disponible
            message: Mensaje personalizado
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        if not message:
            if service_name:
                message = f"Servicio '{service_name}' no disponible temporalmente"
            else:
                message = "Servicio no disponible temporalmente"
                
        return ResponseHandler.error(message, "SERVICE_UNAVAILABLE", 503)
    
    @staticmethod
    def custom_response(
        success: bool,
        message: str,
        data: Any = None,
        status_code: int = 200,
        error_code: str = None,
        meta: Dict[str, Any] = None,
        details: Dict[str, Any] = None
    ) -> Response:
        """
        Crea una respuesta personalizada.
        
        Args:
            success: Indica si la operación fue exitosa
            message: Mensaje descriptivo
            data: Datos a incluir
            status_code: Código de estado HTTP
            error_code: Código de error (solo si success=False)
            meta: Metadatos adicionales
            details: Detalles adicionales
            
        Returns:
            Response: Respuesta JSON de Flask
        """
        if success:
            return ResponseHandler.success(data, message, status_code, meta)
        else:
            return ResponseHandler.error(message, error_code or "CUSTOM_ERROR", status_code, details)


class PaginationHelper:
    """
    Clase auxiliar para manejar paginación.
    """
    
    @staticmethod
    def validate_pagination_params(page: int, per_page: int, max_per_page: int = 100) -> tuple:
        """
        Valida y ajusta los parámetros de paginación.
        
        Args:
            page: Número de página
            per_page: Elementos por página
            max_per_page: Máximo elementos por página permitido
            
        Returns:
            tuple: (page, per_page) validados
            
        Raises:
            ValueError: Si los parámetros son inválidos
        """
        if page < 1:
            raise ValueError("El número de página debe ser mayor a 0")
            
        if per_page < 1:
            raise ValueError("Los elementos por página deben ser mayor a 0")
            
        if per_page > max_per_page:
            per_page = max_per_page
            
        return page, per_page
    
    @staticmethod
    def calculate_offset(page: int, per_page: int) -> int:
        """
        Calcula el offset para la consulta SQL.
        
        Args:
            page: Número de página
            per_page: Elementos por página
            
        Returns:
            int: Offset para la consulta
        """
        return (page - 1) * per_page