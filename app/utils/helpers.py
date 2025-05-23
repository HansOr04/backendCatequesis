"""
Funciones auxiliares para el Sistema de Catequesis.
Contiene utilidades comunes reutilizables en todo el sistema.
"""

import re
import secrets
import string
import hashlib
import uuid
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, date
from decimal import Decimal
import unicodedata

from app.utils.constants import RegexPatterns, ValidationConstants


def generate_random_string(length: int = 32, include_symbols: bool = False) -> str:
    """
    Genera una cadena aleatoria segura.
    
    Args:
        length: Longitud de la cadena
        include_symbols: Si incluir símbolos especiales
        
    Returns:
        str: Cadena aleatoria generada
    """
    characters = string.ascii_letters + string.digits
    if include_symbols:
        characters += "!@#$%^&*"
    
    return ''.join(secrets.choice(characters) for _ in range(length))


def generate_uuid() -> str:
    """
    Genera un UUID único.
    
    Returns:
        str: UUID generado
    """
    return str(uuid.uuid4())


def generate_hash(data: str, algorithm: str = 'sha256') -> str:
    """
    Genera un hash de los datos proporcionados.
    
    Args:
        data: Datos a hashear
        algorithm: Algoritmo de hash (md5, sha1, sha256, sha512)
        
    Returns:
        str: Hash hexadecimal
    """
    if algorithm == 'md5':
        return hashlib.md5(data.encode()).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(data.encode()).hexdigest()
    elif algorithm == 'sha256':
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == 'sha512':
        return hashlib.sha512(data.encode()).hexdigest()
    else:
        raise ValueError(f"Algoritmo de hash no soportado: {algorithm}")


def clean_string(text: str, remove_accents: bool = False) -> str:
    """
    Limpia y normaliza una cadena de texto.
    
    Args:
        text: Texto a limpiar
        remove_accents: Si remover acentos
        
    Returns:
        str: Texto limpio
    """
    if not text:
        return ""
    
    # Remover espacios extras
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remover acentos si se solicita
    if remove_accents:
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    return text


def normalize_name(name: str) -> str:
    """
    Normaliza un nombre para almacenamiento consistente.
    
    Args:
        name: Nombre a normalizar
        
    Returns:
        str: Nombre normalizado
    """
    if not name:
        return ""
    
    # Limpiar y capitalizar cada palabra
    name = clean_string(name)
    return ' '.join(word.capitalize() for word in name.split())


def validate_cedula_ecuador(cedula: str) -> bool:
    """
    Valida una cédula de identidad ecuatoriana.
    
    Args:
        cedula: Número de cédula
        
    Returns:
        bool: True si la cédula es válida
    """
    if not cedula or len(cedula) != 10:
        return False
    
    if not cedula.isdigit():
        return False
    
    # Verificar que los dos primeros dígitos sean válidos (01-24)
    provincia = int(cedula[:2])
    if provincia < 1 or provincia > 24:
        return False
    
    # Algoritmo de validación del dígito verificador
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    
    for i in range(9):
        digito = int(cedula[i])
        resultado = digito * coeficientes[i]
        
        if resultado > 9:
            resultado -= 9
        
        suma += resultado
    
    residuo = suma % 10
    digito_verificador = 0 if residuo == 0 else 10 - residuo
    
    return digito_verificador == int(cedula[9])


def validate_email(email: str) -> bool:
    """
    Valida un email.
    
    Args:
        email: Email a validar
        
    Returns:
        bool: True si el email es válido
    """
    if not email:
        return False
    
    return bool(re.match(RegexPatterns.EMAIL_PATTERN, email))


def validate_phone_ecuador(phone: str) -> bool:
    """
    Valida un teléfono ecuatoriano.
    
    Args:
        phone: Número de teléfono
        
    Returns:
        bool: True si el teléfono es válido
    """
    if not phone:
        return False
    
    # Limpiar el número
    phone_clean = re.sub(r'[^\d+]', '', phone)
    
    return bool(re.match(RegexPatterns.PHONE_PATTERN, phone_clean))


def format_phone_ecuador(phone: str) -> str:
    """
    Formatea un teléfono ecuatoriano.
    
    Args:
        phone: Número de teléfono
        
    Returns:
        str: Teléfono formateado
    """
    if not phone:
        return ""
    
    # Limpiar el número
    phone_clean = re.sub(r'[^\d]', '', phone)
    
    # Si empieza con 593, agregar +
    if phone_clean.startswith('593'):
        return f"+{phone_clean}"
    
    # Si no empieza con 0, agregarlo
    if not phone_clean.startswith('0'):
        phone_clean = f"0{phone_clean}"
    
    return phone_clean


def calculate_age(birth_date: date, reference_date: date = None) -> int:
    """
    Calcula la edad basada en la fecha de nacimiento.
    
    Args:
        birth_date: Fecha de nacimiento
        reference_date: Fecha de referencia (por defecto hoy)
        
    Returns:
        int: Edad en años
    """
    if reference_date is None:
        reference_date = date.today()
    
    age = reference_date.year - birth_date.year
    
    # Ajustar si no ha cumplido años este año
    if reference_date.month < birth_date.month or \
       (reference_date.month == birth_date.month and reference_date.day < birth_date.day):
        age -= 1
    
    return age


def calculate_percentage(part: Union[int, float], total: Union[int, float], decimals: int = 2) -> float:
    """
    Calcula un porcentaje.
    
    Args:
        part: Parte del total
        total: Total
        decimals: Decimales a mostrar
        
    Returns:
        float: Porcentaje calculado
    """
    if total == 0:
        return 0.0
    
    percentage = (part / total) * 100
    return round(percentage, decimals)


def paginate_list(data: List[Any], page: int, per_page: int) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Pagina una lista de datos.
    
    Args:
        data: Lista de datos
        page: Página actual
        per_page: Elementos por página
        
    Returns:
        tuple: (datos_paginados, info_paginacion)
    """
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_data = data[start:end]
    
    total_pages = (total + per_page - 1) // per_page
    
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'next_page': page + 1 if page < total_pages else None,
        'prev_page': page - 1 if page > 1 else None
    }
    
    return paginated_data, pagination_info


def safe_cast(value: Any, target_type: type, default: Any = None) -> Any:
    """
    Convierte un valor a un tipo específico de forma segura.
    
    Args:
        value: Valor a convertir
        target_type: Tipo objetivo
        default: Valor por defecto si la conversión falla
        
    Returns:
        Any: Valor convertido o valor por defecto
    """
    try:
        if target_type == bool and isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'si', 'sí')
        return target_type(value)
    except (ValueError, TypeError):
        return default


def flatten_dict(data: Dict[str, Any], parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
    """
    Aplana un diccionario anidado.
    
    Args:
        data: Diccionario a aplanar
        parent_key: Clave padre
        separator: Separador para las claves
        
    Returns:
        dict: Diccionario aplanado
    """
    items = []
    
    for key, value in data.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def mask_sensitive_data(data: str, mask_char: str = '*', visible_start: int = 2, visible_end: int = 2) -> str:
    """
    Enmascara datos sensibles mostrando solo algunos caracteres.
    
    Args:
        data: Datos a enmascarar
        mask_char: Carácter de máscara
        visible_start: Caracteres visibles al inicio
        visible_end: Caracteres visibles al final
        
    Returns:
        str: Datos enmascarados
    """
    if not data or len(data) <= visible_start + visible_end:
        return mask_char * len(data) if data else ""
    
    start = data[:visible_start]
    end = data[-visible_end:] if visible_end > 0 else ""
    middle = mask_char * (len(data) - visible_start - visible_end)
    
    return f"{start}{middle}{end}"


def format_currency(amount: Union[int, float, Decimal], currency: str = "$") -> str:
    """
    Formatea una cantidad como moneda.
    
    Args:
        amount: Cantidad
        currency: Símbolo de moneda
        
    Returns:
        str: Cantidad formateada
    """
    if amount is None:
        return f"{currency}0.00"
    
    return f"{currency}{amount:,.2f}"


def remove_duplicates_preserve_order(data: List[Any]) -> List[Any]:
    """
    Remueve duplicados de una lista preservando el orden.
    
    Args:
        data: Lista con posibles duplicados
        
    Returns:
        list: Lista sin duplicados
    """
    seen = set()
    result = []
    
    for item in data:
        if item not in seen:
            seen.add(item)
            result.append(item)
    
    return result


def group_by_key(data: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupa una lista de diccionarios por una clave específica.
    
    Args:
        data: Lista de diccionarios
        key: Clave por la cual agrupar
        
    Returns:
        dict: Diccionario agrupado
    """
    grouped = {}
    
    for item in data:
        group_key = item.get(key)
        if group_key not in grouped:
            grouped[group_key] = []
        grouped[group_key].append(item)
    
    return grouped


def split_full_name(full_name: str) -> Tuple[str, str]:
    """
    Divide un nombre completo en nombres y apellidos.
    
    Args:
        full_name: Nombre completo
        
    Returns:
        tuple: (nombres, apellidos)
    """
    if not full_name:
        return "", ""
    
    parts = full_name.strip().split()
    
    if len(parts) <= 2:
        return parts[0] if parts else "", parts[1] if len(parts) > 1 else ""
    
    # Asumir que los últimos dos son apellidos
    nombres = " ".join(parts[:-2])
    apellidos = " ".join(parts[-2:])
    
    return nombres, apellidos


def generate_filename(original_name: str, prefix: str = "", suffix: str = "") -> str:
    """
    Genera un nombre de archivo único y seguro.
    
    Args:
        original_name: Nombre original del archivo
        prefix: Prefijo a agregar
        suffix: Sufijo a agregar
        
    Returns:
        str: Nombre de archivo generado
    """
    if not original_name:
        original_name = "file"
    
    # Limpiar el nombre del archivo
    name, ext = original_name.rsplit('.', 1) if '.' in original_name else (original_name, '')
    
    # Remover caracteres especiales
    safe_name = re.sub(r'[^\w\-_.]', '_', name)
    
    # Generar timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generar ID único corto
    unique_id = generate_random_string(6)
    
    # Construir nombre final
    parts = [prefix, safe_name, timestamp, unique_id, suffix]
    final_name = "_".join(filter(None, parts))
    
    if ext:
        final_name = f"{final_name}.{ext}"
    
    return final_name


def is_valid_date_range(start_date: date, end_date: date) -> bool:
    """
    Valida que un rango de fechas sea válido.
    
    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin
        
    Returns:
        bool: True si el rango es válido
    """
    if not start_date or not end_date:
        return False
    
    return start_date <= end_date


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo removiendo caracteres peligrosos.
    
    Args:
        filename: Nombre de archivo a sanitizar
        
    Returns:
        str: Nombre de archivo sanitizado
    """
    if not filename:
        return "unnamed_file"
    
    # Remover caracteres peligrosos
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remover espacios al inicio y final
    safe_filename = safe_filename.strip()
    
    # Evitar nombres reservados en Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_part = safe_filename.split('.')[0].upper()
    if name_part in reserved_names:
        safe_filename = f"file_{safe_filename}"
    
    return safe_filename


def extract_numbers_from_string(text: str) -> List[int]:
    """
    Extrae todos los números de una cadena de texto.
    
    Args:
        text: Texto del cual extraer números
        
    Returns:
        list: Lista de números encontrados
    """
    if not text:
        return []
    
    numbers = re.findall(r'\d+', text)
    return [int(num) for num in numbers]


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Trunca un texto a una longitud máxima.
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        suffix: Sufijo a agregar si se trunca
        
    Returns:
        str: Texto truncado
    """
    if not text or len(text) <= max_length:
        return text or ""
    
    return text[:max_length - len(suffix)] + suffix


def get_file_extension(filename: str) -> str:
    """
    Obtiene la extensión de un archivo.
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        str: Extensión del archivo (sin el punto)
    """
    if not filename or '.' not in filename:
        return ""
    
    return filename.rsplit('.', 1)[1].lower()


def is_valid_age_for_catequesis(birth_date: date, reference_date: date = None) -> bool:
    """
    Valida si la edad es apropiada para catequesis.
    
    Args:
        birth_date: Fecha de nacimiento
        reference_date: Fecha de referencia
        
    Returns:
        bool: True si la edad es válida
    """
    age = calculate_age(birth_date, reference_date)
    return ValidationConstants.MIN_CATEQUESIS_AGE <= age <= ValidationConstants.MAX_CATEQUESIS_AGE


def format_document_number(document: str, document_type: str = "cedula") -> str:
    """
    Formatea un número de documento según el tipo.
    
    Args:
        document: Número de documento
        document_type: Tipo de documento (cedula, pasaporte)
        
    Returns:
        str: Documento formateado
    """
    if not document:
        return ""
    
    # Limpiar el documento
    clean_doc = re.sub(r'[^\w]', '', document)
    
    if document_type == "cedula" and len(clean_doc) == 10:
        # Formato: 1234567890 -> 123456789-0
        return f"{clean_doc[:9]}-{clean_doc[9]}"
    
    return clean_doc


def generate_reference_code(prefix: str = "REF", length: int = 8) -> str:
    """
    Genera un código de referencia único.
    
    Args:
        prefix: Prefijo del código
        length: Longitud de la parte numérica
        
    Returns:
        str: Código de referencia
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    random_part = generate_random_string(length, include_symbols=False).upper()
    
    return f"{prefix}{timestamp}{random_part}"


def dict_to_obj(data: Dict[str, Any]) -> object:
    """
    Convierte un diccionario a un objeto con atributos.
    
    Args:
        data: Diccionario a convertir
        
    Returns:
        object: Objeto con atributos del diccionario
    """
    class DictObj:
        def __init__(self, dictionary):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    setattr(self, key, DictObj(value))
                else:
                    setattr(self, key, value)
    
    return DictObj(data)


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combina dos diccionarios de forma profunda.
    
    Args:
        dict1: Primer diccionario
        dict2: Segundo diccionario
        
    Returns:
        dict: Diccionario combinado
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Valida que los campos requeridos estén presentes.
    
    Args:
        data: Datos a validar
        required_fields: Lista de campos requeridos
        
    Returns:
        list: Lista de campos faltantes
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    return missing_fields


def clean_phone_number(phone: str) -> str:
    """
    Limpia un número de teléfono removiendo caracteres no numéricos.
    
    Args:
        phone: Número de teléfono
        
    Returns:
        str: Número limpio
    """
    if not phone:
        return ""
    
    # Mantener solo dígitos y el signo +
    return re.sub(r'[^\d+]', '', phone)


def is_weekend(date_obj: date) -> bool:
    """
    Verifica si una fecha cae en fin de semana.
    
    Args:
        date_obj: Fecha a verificar
        
    Returns:
        bool: True si es fin de semana
    """
    return date_obj.weekday() >= 5  # 5=sábado, 6=domingo


def get_next_weekday(start_date: date, weekday: int) -> date:
    """
    Obtiene la próxima fecha que cae en un día específico de la semana.
    
    Args:
        start_date: Fecha de inicio
        weekday: Día de la semana (0=lunes, 6=domingo)
        
    Returns:
        date: Próxima fecha del día especificado
    """
    from datetime import timedelta
    
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    
    return start_date + timedelta(days_ahead)


def convert_to_title_case(text: str) -> str:
    """
    Convierte texto a Title Case respetando artículos y preposiciones.
    
    Args:
        text: Texto a convertir
        
    Returns:
        str: Texto en Title Case
    """
    if not text:
        return ""
    
    # Palabras que no se capitalizan (excepto al inicio)
    articles = {'de', 'del', 'la', 'el', 'las', 'los', 'y', 'e', 'o', 'u'}
    
    words = text.lower().split()
    result = []
    
    for i, word in enumerate(words):
        if i == 0 or word not in articles:
            result.append(word.capitalize())
        else:
            result.append(word)
    
    return ' '.join(result)


def get_ordinal_number(number: int) -> str:
    """
    Convierte un número a su forma ordinal en español.
    
    Args:
        number: Número a convertir
        
    Returns:
        str: Número ordinal (ej: 1° -> "1°", 2° -> "2°")
    """
    if number <= 0:
        return str(number)
    
    return f"{number}°"


def calculate_business_days(start_date: date, end_date: date) -> int:
    """
    Calcula los días hábiles entre dos fechas.
    
    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin
        
    Returns:
        int: Número de días hábiles
    """
    from datetime import timedelta
    
    if start_date > end_date:
        return 0
    
    current_date = start_date
    business_days = 0
    
    while current_date <= end_date:
        if not is_weekend(current_date):
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


def format_duration(seconds: int) -> str:
    """
    Formatea una duración en segundos a formato legible.
    
    Args:
        seconds: Duración en segundos
        
    Returns:
        str: Duración formateada (ej: "2h 30m 15s")
    """
    if seconds < 60:
        return f"{seconds}s"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds}s"
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    parts = [f"{hours}h"]
    if remaining_minutes > 0:
        parts.append(f"{remaining_minutes}m")
    if remaining_seconds > 0:
        parts.append(f"{remaining_seconds}s")
    
    return " ".join(parts)


def chunks(data: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Divide una lista en chunks de tamaño específico.
    
    Args:
        data: Lista a dividir
        chunk_size: Tamaño de cada chunk
        
    Returns:
        list: Lista de chunks
    """
    if chunk_size <= 0:
        return [data] if data else []
    
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]