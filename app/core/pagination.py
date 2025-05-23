"""
Utilidades de paginación para el Sistema de Catequesis.
Proporciona clases y funciones para manejar paginación de manera eficiente.
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from flask import request, url_for
from app.utils.constants import SystemConstants


@dataclass
class PaginationInfo:
    """
    Clase de datos para información de paginación.
    """
    page: int
    per_page: int
    total: int
    pages: int
    has_prev: bool
    has_next: bool
    prev_num: Optional[int]
    next_num: Optional[int]
    
    @property
    def offset(self) -> int:
        """Calcula el offset para consultas SQL."""
        return (self.page - 1) * self.per_page
    
    @property
    def start_index(self) -> int:
        """Índice del primer elemento en la página actual (1-based)."""
        return self.offset + 1 if self.total > 0 else 0
    
    @property
    def end_index(self) -> int:
        """Índice del último elemento en la página actual (1-based)."""
        return min(self.offset + self.per_page, self.total)
    
    @property
    def showing_text(self) -> str:
        """Texto descriptivo de lo que se está mostrando."""
        if self.total == 0:
            return "No se encontraron elementos"
        
        if self.total <= self.per_page:
            return f"Mostrando {self.total} elemento{'s' if self.total != 1 else ''}"
        
        return f"Mostrando {self.start_index}-{self.end_index} de {self.total} elementos"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la información de paginación a diccionario."""
        return {
            'page': self.page,
            'per_page': self.per_page,
            'total': self.total,
            'pages': self.pages,
            'has_prev': self.has_prev,
            'has_next': self.has_next,
            'prev_num': self.prev_num,
            'next_num': self.next_num,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'showing_text': self.showing_text
        }


class Paginator:
    """
    Clase principal para manejar paginación.
    """
    
    def __init__(
        self,
        page: int = 1,
        per_page: int = None,
        max_per_page: int = None
    ):
        """
        Inicializa el paginador.
        
        Args:
            page: Número de página actual
            per_page: Elementos por página
            max_per_page: Máximo elementos por página permitido
        """
        self.page = max(1, page)
        self.per_page = per_page or SystemConstants.DEFAULT_PAGE_SIZE
        self.max_per_page = max_per_page or SystemConstants.MAX_PAGE_SIZE
        
        # Validar per_page
        if self.per_page < SystemConstants.MIN_PAGE_SIZE:
            self.per_page = SystemConstants.MIN_PAGE_SIZE
        elif self.per_page > self.max_per_page:
            self.per_page = self.max_per_page
    
    def paginate(
        self, 
        total_count: int, 
        items: List[Any] = None
    ) -> Tuple[List[Any], PaginationInfo]:
        """
        Pagina elementos con información completa.
        
        Args:
            total_count: Total de elementos
            items: Lista de elementos (opcional)
            
        Returns:
            tuple: (elementos_paginados, info_paginacion)
        """
        # Calcular información de paginación
        pages = math.ceil(total_count / self.per_page) if total_count > 0 else 0
        
        # Ajustar página si está fuera de rango
        if self.page > pages and pages > 0:
            self.page = pages
        
        has_prev = self.page > 1
        has_next = self.page < pages
        prev_num = self.page - 1 if has_prev else None
        next_num = self.page + 1 if has_next else None
        
        pagination_info = PaginationInfo(
            page=self.page,
            per_page=self.per_page,
            total=total_count,
            pages=pages,
            has_prev=has_prev,
            has_next=has_next,
            prev_num=prev_num,
            next_num=next_num
        )
        
        # Si se proporcionan items, paginarlos
        if items is not None:
            start_idx = pagination_info.offset
            end_idx = start_idx + self.per_page
            paginated_items = items[start_idx:end_idx]
        else:
            paginated_items = []
        
        return paginated_items, pagination_info
    
    def get_sql_limit_offset(self) -> Tuple[int, int]:
        """
        Obtiene LIMIT y OFFSET para consultas SQL.
        
        Returns:
            tuple: (limit, offset)
        """
        offset = (self.page - 1) * self.per_page
        return self.per_page, offset


class RequestPaginator(Paginator):
    """
    Paginador que obtiene parámetros automáticamente del request de Flask.
    """
    
    def __init__(self, max_per_page: int = None):
        """
        Inicializa el paginador con parámetros del request.
        
        Args:
            max_per_page: Máximo elementos por página permitido
        """
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', SystemConstants.DEFAULT_PAGE_SIZE, type=int)
        
        super().__init__(page, per_page, max_per_page)


class AdvancedPaginator(Paginator):
    """
    Paginador avanzado con funcionalidades adicionales.
    """
    
    def __init__(
        self,
        page: int = 1,
        per_page: int = None,
        max_per_page: int = None,
        show_page_links: int = 5
    ):
        """
        Inicializa el paginador avanzado.
        
        Args:
            page: Número de página actual
            per_page: Elementos por página
            max_per_page: Máximo elementos por página permitido
            show_page_links: Número de enlaces de página a mostrar
        """
        super().__init__(page, per_page, max_per_page)
        self.show_page_links = show_page_links
    
    def get_page_range(self, total_pages: int) -> List[int]:
        """
        Obtiene el rango de páginas a mostrar en la navegación.
        
        Args:
            total_pages: Total de páginas
            
        Returns:
            list: Lista de números de página
        """
        if total_pages <= self.show_page_links:
            return list(range(1, total_pages + 1))
        
        half_links = self.show_page_links // 2
        
        if self.page <= half_links:
            # Cerca del inicio
            return list(range(1, self.show_page_links + 1))
        elif self.page >= total_pages - half_links:
            # Cerca del final
            return list(range(total_pages - self.show_page_links + 1, total_pages + 1))
        else:
            # En el medio
            return list(range(self.page - half_links, self.page + half_links + 1))
    
    def get_navigation_info(
        self, 
        total_count: int, 
        endpoint: str = None, 
        **url_kwargs
    ) -> Dict[str, Any]:
        """
        Obtiene información completa de navegación incluyendo URLs.
        
        Args:
            total_count: Total de elementos
            endpoint: Endpoint para generar URLs
            url_kwargs: Argumentos adicionales para URLs
            
        Returns:
            dict: Información de navegación
        """
        _, pagination_info = self.paginate(total_count)
        pages = pagination_info.pages
        
        # Generar URLs si se proporciona endpoint
        urls = {}
        if endpoint:
            base_args = {**url_kwargs}
            
            # URL de primera página
            urls['first'] = url_for(endpoint, page=1, per_page=self.per_page, **base_args)
            
            # URL de última página
            if pages > 0:
                urls['last'] = url_for(endpoint, page=pages, per_page=self.per_page, **base_args)
            
            # URL de página anterior
            if pagination_info.has_prev:
                urls['prev'] = url_for(endpoint, page=pagination_info.prev_num, per_page=self.per_page, **base_args)
            
            # URL de página siguiente
            if pagination_info.has_next:
                urls['next'] = url_for(endpoint, page=pagination_info.next_num, per_page=self.per_page, **base_args)
            
            # URLs de páginas en el rango
            page_range = self.get_page_range(pages)
            urls['pages'] = {}
            for page_num in page_range:
                urls['pages'][page_num] = url_for(endpoint, page=page_num, per_page=self.per_page, **base_args)
        
        return {
            **pagination_info.to_dict(),
            'page_range': self.get_page_range(pages),
            'urls': urls
        }


class StoredProcedurePaginator:
    """
    Paginador especializado para stored procedures con paginación.
    """
    
    def __init__(
        self,
        page: int = 1,
        per_page: int = None,
        max_per_page: int = None
    ):
        """
        Inicializa el paginador para stored procedures.
        
        Args:
            page: Número de página actual
            per_page: Elementos por página
            max_per_page: Máximo elementos por página permitido
        """
        self.paginator = Paginator(page, per_page, max_per_page)
    
    def get_sp_parameters(self) -> Dict[str, int]:
        """
        Obtiene parámetros para el stored procedure.
        
        Returns:
            dict: Parámetros de paginación para SP
        """
        limit, offset = self.paginator.get_sql_limit_offset()
        
        return {
            'page_number': self.paginator.page,
            'page_size': self.paginator.per_page,
            'offset_rows': offset,
            'fetch_rows': limit
        }
    
    def process_sp_result(
        self, 
        items: List[Any], 
        total_count: int
    ) -> Tuple[List[Any], PaginationInfo]:
        """
        Procesa el resultado de un stored procedure paginado.
        
        Args:
            items: Items retornados por el SP
            total_count: Conteo total retornado por el SP
            
        Returns:
            tuple: (items, info_paginacion)
        """
        _, pagination_info = self.paginator.paginate(total_count)
        return items, pagination_info


class CursorPaginator:
    """
    Paginador basado en cursor para grandes datasets.
    Útil para feeds en tiempo real o datasets muy grandes.
    """
    
    def __init__(
        self,
        cursor: Any = None,
        per_page: int = None,
        max_per_page: int = None
    ):
        """
        Inicializa el paginador por cursor.
        
        Args:
            cursor: Cursor de la posición actual
            per_page: Elementos por página
            max_per_page: Máximo elementos por página permitido
        """
        self.cursor = cursor
        self.per_page = per_page or SystemConstants.DEFAULT_PAGE_SIZE
        self.max_per_page = max_per_page or SystemConstants.MAX_PAGE_SIZE
        
        if self.per_page > self.max_per_page:
            self.per_page = self.max_per_page
    
    def paginate_cursor(
        self, 
        items: List[Any], 
        get_cursor_func: callable,
        has_more: bool = False
    ) -> Dict[str, Any]:
        """
        Pagina usando cursor.
        
        Args:
            items: Lista de elementos
            get_cursor_func: Función para obtener cursor de un item
            has_more: Si hay más elementos disponibles
            
        Returns:
            dict: Resultado paginado con cursors
        """
        # Limitar items al tamaño de página
        page_items = items[:self.per_page]
        
        # Determinar si hay siguiente página
        actual_has_more = has_more or len(items) > self.per_page
        
        # Obtener cursors
        next_cursor = None
        prev_cursor = self.cursor
        
        if page_items and actual_has_more:
            next_cursor = get_cursor_func(page_items[-1])
        
        return {
            'items': page_items,
            'pagination': {
                'per_page': self.per_page,
                'has_more': actual_has_more,
                'next_cursor': next_cursor,
                'prev_cursor': prev_cursor,
                'current_cursor': self.cursor
            }
        }


def paginate_query_result(
    total_count: int,
    items: List[Any],
    page: int = None,
    per_page: int = None
) -> Dict[str, Any]:
    """
    Función helper para paginar resultados de consulta.
    
    Args:
        total_count: Conteo total de elementos
        items: Lista de elementos de la página actual
        page: Número de página
        per_page: Elementos por página
        
    Returns:
        dict: Resultado paginado estandarizado
    """
    if page is None:
        page = request.args.get('page', 1, type=int)
    
    if per_page is None:
        per_page = request.args.get('per_page', SystemConstants.DEFAULT_PAGE_SIZE, type=int)
    
    paginator = Paginator(page, per_page)
    _, pagination_info = paginator.paginate(total_count)
    
    return {
        'data': items,
        'pagination': pagination_info.to_dict(),
        'meta': {
            'total_count': total_count,
            'page_count': pagination_info.pages,
            'current_page': pagination_info.page,
            'per_page': pagination_info.per_page
        }
    }


def validate_pagination_params(
    page: int = None, 
    per_page: int = None,
    max_per_page: int = None
) -> Tuple[int, int]:
    """
    Valida y normaliza parámetros de paginación.
    
    Args:
        page: Número de página
        per_page: Elementos por página
        max_per_page: Máximo permitido por página
        
    Returns:
        tuple: (page_validado, per_page_validado)
        
    Raises:
        ValueError: Si los parámetros son inválidos
    """
    # Valores por defecto
    if page is None:
        page = 1
    if per_page is None:
        per_page = SystemConstants.DEFAULT_PAGE_SIZE
    if max_per_page is None:
        max_per_page = SystemConstants.MAX_PAGE_SIZE
    
    # Validar página
    if not isinstance(page, int) or page < 1:
        raise ValueError("El número de página debe ser un entero mayor a 0")
    
    # Validar per_page
    if not isinstance(per_page, int) or per_page < 1:
        raise ValueError("Los elementos por página deben ser un entero mayor a 0")
    
    # Limitar per_page al máximo permitido
    if per_page > max_per_page:
        per_page = max_per_page
    
    return page, per_page


def get_pagination_from_request(max_per_page: int = None) -> Tuple[int, int]:
    """
    Obtiene parámetros de paginación validados del request actual.
    
    Args:
        max_per_page: Máximo elementos por página permitido
        
    Returns:
        tuple: (page, per_page) validados
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', SystemConstants.DEFAULT_PAGE_SIZE, type=int)
    
    return validate_pagination_params(page, per_page, max_per_page)


class SearchPaginator(Paginator):
    """
    Paginador especializado para resultados de búsqueda.
    Incluye funcionalidades adicionales para búsquedas.
    """
    
    def __init__(
        self,
        search_query: str = None,
        filters: Dict[str, Any] = None,
        sort_by: str = None,
        sort_order: str = 'asc',
        page: int = 1,
        per_page: int = None,
        max_per_page: int = None
    ):
        """
        Inicializa el paginador de búsqueda.
        
        Args:
            search_query: Consulta de búsqueda
            filters: Filtros aplicados
            sort_by: Campo de ordenamiento
            sort_order: Orden (asc/desc)
            page: Número de página
            per_page: Elementos por página
            max_per_page: Máximo elementos por página
        """
        super().__init__(page, per_page, max_per_page)
        self.search_query = search_query or ""
        self.filters = filters or {}
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order else 'asc'
        
        # Validar sort_order
        if self.sort_order not in ['asc', 'desc']:
            self.sort_order = 'asc'
    
    def get_search_info(self) -> Dict[str, Any]:
        """
        Obtiene información completa de la búsqueda.
        
        Returns:
            dict: Información de búsqueda y paginación
        """
        return {
            'search_query': self.search_query,
            'filters': self.filters,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
            'has_search': bool(self.search_query or self.filters),
            'page': self.page,
            'per_page': self.per_page
        }
    
    def paginate_search_results(
        self, 
        total_count: int, 
        items: List[Any],
        search_time: float = None
    ) -> Dict[str, Any]:
        """
        Pagina resultados de búsqueda con información adicional.
        
        Args:
            total_count: Total de resultados encontrados
            items: Elementos de la página actual
            search_time: Tiempo de búsqueda en segundos
            
        Returns:
            dict: Resultados paginados con metadatos de búsqueda
        """
        _, pagination_info = self.paginate(total_count)
        
        return {
            'data': items,
            'pagination': pagination_info.to_dict(),
            'search': self.get_search_info(),
            'meta': {
                'total_results': total_count,
                'search_time': search_time,
                'results_found': total_count > 0,
                'empty_search': total_count == 0 and bool(self.search_query or self.filters)
            }
        }


class BatchPaginator:
    """
    Paginador para procesamiento por lotes de grandes datasets.
    """
    
    def __init__(
        self,
        batch_size: int = 1000,
        max_batch_size: int = 5000
    ):
        """
        Inicializa el paginador por lotes.
        
        Args:
            batch_size: Tamaño del lote
            max_batch_size: Máximo tamaño de lote permitido
        """
        self.batch_size = min(batch_size, max_batch_size)
        self.current_offset = 0
        self.total_processed = 0
    
    def get_next_batch_params(self) -> Dict[str, int]:
        """
        Obtiene parámetros para el siguiente lote.
        
        Returns:
            dict: Parámetros de offset y limit
        """
        return {
            'offset': self.current_offset,
            'limit': self.batch_size
        }
    
    def process_batch(self, batch_items: List[Any]) -> Dict[str, Any]:
        """
        Procesa un lote y actualiza contadores.
        
        Args:
            batch_items: Elementos del lote actual
            
        Returns:
            dict: Información del lote procesado
        """
        batch_count = len(batch_items)
        self.total_processed += batch_count
        
        # Preparar para siguiente lote
        if batch_count == self.batch_size:
            self.current_offset += self.batch_size
            has_more = True
        else:
            has_more = False
        
        return {
            'batch_items': batch_items,
            'batch_size': batch_count,
            'total_processed': self.total_processed,
            'current_offset': self.current_offset,
            'has_more_batches': has_more
        }
    
    def reset(self):
        """Reinicia el paginador por lotes."""
        self.current_offset = 0
        self.total_processed = 0


def create_pagination_response(
    items: List[Any],
    total_count: int,
    page: int,
    per_page: int,
    endpoint: str = None,
    **url_kwargs
) -> Dict[str, Any]:
    """
    Crea una respuesta de paginación estandarizada.
    
    Args:
        items: Elementos de la página actual
        total_count: Total de elementos
        page: Página actual
        per_page: Elementos por página
        endpoint: Endpoint para generar URLs de navegación
        url_kwargs: Argumentos adicionales para URLs
        
    Returns:
        dict: Respuesta paginada estandarizada
    """
    paginator = AdvancedPaginator(page, per_page)
    
    if endpoint:
        navigation_info = paginator.get_navigation_info(total_count, endpoint, **url_kwargs)
    else:
        _, pagination_info = paginator.paginate(total_count)
        navigation_info = pagination_info.to_dict()
    
    return {
        'success': True,
        'data': items,
        'pagination': navigation_info,
        'meta': {
            'timestamp': get_current_timestamp(),
            'count': len(items),
            'total': total_count
        }
    }


def get_current_timestamp() -> str:
    """
    Obtiene timestamp actual en formato ISO.
    
    Returns:
        str: Timestamp actual
    """
    from datetime import datetime
    return datetime.utcnow().isoformat()


class InfiniteScrollPaginator:
    """
    Paginador para scroll infinito en interfaces web.
    """
    
    def __init__(
        self,
        per_page: int = None,
        max_per_page: int = None,
        cursor_field: str = 'id'
    ):
        """
        Inicializa el paginador para scroll infinito.
        
        Args:
            per_page: Elementos por página
            max_per_page: Máximo elementos por página
            cursor_field: Campo usado como cursor
        """
        self.per_page = per_page or SystemConstants.DEFAULT_PAGE_SIZE
        self.max_per_page = max_per_page or SystemConstants.MAX_PAGE_SIZE
        self.cursor_field = cursor_field
        
        if self.per_page > self.max_per_page:
            self.per_page = self.max_per_page
    
    def paginate_infinite(
        self,
        items: List[Dict[str, Any]],
        last_cursor: Any = None
    ) -> Dict[str, Any]:
        """
        Pagina para scroll infinito.
        
        Args:
            items: Lista de elementos (debe incluir uno extra para detectar has_more)
            last_cursor: Último cursor de la página anterior
            
        Returns:
            dict: Resultado para scroll infinito
        """
        # Determinar si hay más elementos
        has_more = len(items) > self.per_page
        
        # Limitar a per_page elementos
        page_items = items[:self.per_page]
        
        # Obtener nuevo cursor
        next_cursor = None
        if page_items and has_more:
            last_item = page_items[-1]
            next_cursor = last_item.get(self.cursor_field)
        
        return {
            'data': page_items,
            'pagination': {
                'has_more': has_more,
                'next_cursor': next_cursor,
                'prev_cursor': last_cursor,
                'per_page': self.per_page,
                'loaded_count': len(page_items)
            },
            'meta': {
                'cursor_field': self.cursor_field,
                'timestamp': get_current_timestamp()
            }
        }


# Funciones helper para casos comunes
def quick_paginate(
    items: List[Any], 
    total_count: int = None,
    page: int = None,
    per_page: int = None
) -> Dict[str, Any]:
    """
    Función helper para paginación rápida y simple.
    
    Args:
        items: Lista de elementos
        total_count: Total de elementos (si es diferente a len(items))
        page: Página actual
        per_page: Elementos por página
        
    Returns:
        dict: Resultado paginado simple
    """
    if total_count is None:
        total_count = len(items)
    
    page = page or request.args.get('page', 1, type=int)
    per_page = per_page or request.args.get('per_page', SystemConstants.DEFAULT_PAGE_SIZE, type=int)
    
    return paginate_query_result(total_count, items, page, per_page)


def paginate_stored_procedure_result(
    sp_result: List[Any],
    count_result: int,
    page: int = None,
    per_page: int = None
) -> Dict[str, Any]:
    """
    Pagina resultados de stored procedures.
    
    Args:
        sp_result: Resultado del stored procedure
        count_result: Conteo total del stored procedure
        page: Página actual
        per_page: Elementos por página
        
    Returns:
        dict: Resultado paginado
    """
    return paginate_query_result(count_result, sp_result, page, per_page)