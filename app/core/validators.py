"""
Validadores para el Sistema de Catequesis.
Contiene validaciones específicas del dominio de negocio.
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from marshmallow import ValidationError

from app.utils.constants import (
    ValidationConstants, 
    RegexPatterns, 
    SystemMessages,
    UserProfileType,
    CatequistaType,
    PaymentMethod
)
from app.utils.helpers import (
    validate_cedula_ecuador,
    validate_email,
    validate_phone_ecuador,
    calculate_age,
    is_valid_age_for_catequesis
)
from app.utils.date_utils import (
    get_current_date,
    is_valid_birth_date,
    get_catequesis_year
)


class BaseValidator:
    """Clase base para validadores del sistema."""
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> Any:
        """
        Valida que un campo sea requerido.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            
        Returns:
            Any: Valor validado
            
        Raises:
            ValidationError: Si el campo está vacío
        """
        if value is None or value == "" or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"El campo '{field_name}' es requerido")
        return value
    
    @staticmethod
    def validate_length(value: str, field_name: str, min_length: int = None, max_length: int = None) -> str:
        """
        Valida la longitud de una cadena.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            min_length: Longitud mínima
            max_length: Longitud máxima
            
        Returns:
            str: Valor validado
            
        Raises:
            ValidationError: Si la longitud es inválida
        """
        if not isinstance(value, str):
            raise ValidationError(f"El campo '{field_name}' debe ser texto")
        
        length = len(value.strip())
        
        if min_length is not None and length < min_length:
            raise ValidationError(f"El campo '{field_name}' debe tener al menos {min_length} caracteres")
        
        if max_length is not None and length > max_length:
            raise ValidationError(f"El campo '{field_name}' no puede tener más de {max_length} caracteres")
        
        return value.strip()
    
    @staticmethod
    def validate_pattern(value: str, pattern: str, field_name: str, message: str = None) -> str:
        """
        Valida que un valor coincida con un patrón regex.
        
        Args:
            value: Valor a validar
            pattern: Patrón regex
            field_name: Nombre del campo
            message: Mensaje de error personalizado
            
        Returns:
            str: Valor validado
            
        Raises:
            ValidationError: Si no coincide con el patrón
        """
        if not re.match(pattern, value):
            error_message = message or f"El campo '{field_name}' tiene un formato inválido"
            raise ValidationError(error_message)
        
        return value


class PersonValidator(BaseValidator):
    """Validador para datos de personas (catequizandos, representantes, etc.)."""
    
    @staticmethod
    def validate_names(names: str) -> str:
        """
        Valida nombres de persona.
        
        Args:
            names: Nombres a validar
            
        Returns:
            str: Nombres validados
            
        Raises:
            ValidationError: Si los nombres son inválidos
        """
        names = PersonValidator.validate_required(names, "nombres")
        names = PersonValidator.validate_length(
            names, "nombres", 
            ValidationConstants.MIN_NAME_LENGTH, 
            ValidationConstants.MAX_NAME_LENGTH
        )
        
        PersonValidator.validate_pattern(
            names, RegexPatterns.NAME_PATTERN, "nombres",
            "Los nombres solo pueden contener letras, espacios y algunos caracteres especiales"
        )
        
        return names.title()
    
    @staticmethod
    def validate_surnames(surnames: str) -> str:
        """
        Valida apellidos de persona.
        
        Args:
            surnames: Apellidos a validar
            
        Returns:
            str: Apellidos validados
            
        Raises:
            ValidationError: Si los apellidos son inválidos
        """
        surnames = PersonValidator.validate_required(surnames, "apellidos")
        surnames = PersonValidator.validate_length(
            surnames, "apellidos", 
            ValidationConstants.MIN_NAME_LENGTH, 
            ValidationConstants.MAX_NAME_LENGTH
        )
        
        PersonValidator.validate_pattern(
            surnames, RegexPatterns.NAME_PATTERN, "apellidos",
            "Los apellidos solo pueden contener letras, espacios y algunos caracteres especiales"
        )
        
        return surnames.title()
    
    @staticmethod
    def validate_cedula(cedula: str) -> str:
        """
        Valida cédula de identidad ecuatoriana.
        
        Args:
            cedula: Cédula a validar
            
        Returns:
            str: Cédula validada
            
        Raises:
            ValidationError: Si la cédula es inválida
        """
        cedula = PersonValidator.validate_required(cedula, "cédula")
        
        # Limpiar la cédula
        clean_cedula = re.sub(r'[^\d]', '', cedula)
        
        if len(clean_cedula) != ValidationConstants.CEDULA_LENGTH:
            raise ValidationError(f"La cédula debe tener {ValidationConstants.CEDULA_LENGTH} dígitos")
        
        if not validate_cedula_ecuador(clean_cedula):
            raise ValidationError("La cédula de identidad no es válida")
        
        return clean_cedula
    
    @staticmethod
    def validate_birth_date(birth_date: Union[str, date], for_catequesis: bool = False) -> date:
        """
        Valida fecha de nacimiento.
        
        Args:
            birth_date: Fecha de nacimiento
            for_catequesis: Si es para validar edad de catequesis
            
        Returns:
            date: Fecha validada
            
        Raises:
            ValidationError: Si la fecha es inválida
        """
        if isinstance(birth_date, str):
            try:
                birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Formato de fecha inválido. Use YYYY-MM-DD")
        
        if not isinstance(birth_date, date):
            raise ValidationError("La fecha de nacimiento debe ser una fecha válida")
        
        if not is_valid_birth_date(birth_date, 0, 120):
            raise ValidationError("La fecha de nacimiento no es válida")
        
        if for_catequesis and not is_valid_age_for_catequesis(birth_date):
            min_age = ValidationConstants.MIN_CATEQUESIS_AGE
            max_age = ValidationConstants.MAX_CATEQUESIS_AGE
            raise ValidationError(f"La edad debe estar entre {min_age} y {max_age} años para catequesis")
        
        return birth_date
    
    @staticmethod
    def validate_email(email: str) -> str:
        """
        Valida email.
        
        Args:
            email: Email a validar
            
        Returns:
            str: Email validado
            
        Raises:
            ValidationError: Si el email es inválido
        """
        email = PersonValidator.validate_required(email, "email")
        email = PersonValidator.validate_length(email, "email", max_length=ValidationConstants.MAX_EMAIL_LENGTH)
        
        if not validate_email(email):
            raise ValidationError("El formato del email no es válido")
        
        return email.lower()
    
    @staticmethod
    def validate_phone(phone: str) -> str:
        """
        Valida teléfono.
        
        Args:
            phone: Teléfono a validar
            
        Returns:
            str: Teléfono validado
            
        Raises:
            ValidationError: Si el teléfono es inválido
        """
        phone = PersonValidator.validate_required(phone, "teléfono")
        
        if not validate_phone_ecuador(phone):
            raise ValidationError("El formato del teléfono no es válido")
        
        # Limpiar y formatear
        clean_phone = re.sub(r'[^\d+]', '', phone)
        return clean_phone
    
    @staticmethod
    def validate_address(address: str) -> str:
        """
        Valida dirección.
        
        Args:
            address: Dirección a validar
            
        Returns:
            str: Dirección validada
            
        Raises:
            ValidationError: Si la dirección es inválida
        """
        address = PersonValidator.validate_required(address, "dirección")
        address = PersonValidator.validate_length(
            address, "dirección", 
            max_length=ValidationConstants.MAX_ADDRESS_LENGTH
        )
        
        return address.strip()


class CatequesisValidator(BaseValidator):
    """Validador para entidades específicas del dominio de catequesis."""
    
    @staticmethod
    def validate_level_order(order: int) -> int:
        """
        Valida el orden de un nivel.
        
        Args:
            order: Orden del nivel
            
        Returns:
            int: Orden validado
            
        Raises:
            ValidationError: Si el orden es inválido
        """
        if not isinstance(order, int) or order < 1:
            raise ValidationError("El orden del nivel debe ser un número entero positivo")
        
        if order > 10:  # Máximo razonable de niveles
            raise ValidationError("El orden del nivel no puede ser mayor a 10")
        
        return order
    
    @staticmethod
    def validate_group_capacity(capacity: int) -> int:
        """
        Valida la capacidad de un grupo.
        
        Args:
            capacity: Capacidad del grupo
            
        Returns:
            int: Capacidad validada
            
        Raises:
            ValidationError: Si la capacidad es inválida
        """
        min_capacity = ValidationConstants.MIN_CATEQUIZANDOS_PER_GROUP
        max_capacity = ValidationConstants.MAX_CATEQUIZANDOS_PER_GROUP
        
        if not isinstance(capacity, int):
            raise ValidationError("La capacidad debe ser un número entero")
        
        if capacity < min_capacity or capacity > max_capacity:
            raise ValidationError(f"La capacidad debe estar entre {min_capacity} y {max_capacity}")
        
        return capacity
    
    @staticmethod
    def validate_attendance_percentage(percentage: float) -> float:
        """
        Valida porcentaje de asistencia.
        
        Args:
            percentage: Porcentaje a validar
            
        Returns:
            float: Porcentaje validado
            
        Raises:
            ValidationError: Si el porcentaje es inválido
        """
        if not isinstance(percentage, (int, float)):
            raise ValidationError("El porcentaje debe ser un número")
        
        if percentage < 0 or percentage > 100:
            raise ValidationError("El porcentaje debe estar entre 0 y 100")
        
        return float(percentage)
    
    @staticmethod
    def validate_catequesis_period(period: str) -> str:
        """
        Valida período de catequesis.
        
        Args:
            period: Período a validar (formato: "2024-2025")
            
        Returns:
            str: Período validado
            
        Raises:
            ValidationError: Si el período es inválido
        """
        period = CatequesisValidator.validate_required(period, "período")
        
        # Validar formato YYYY-YYYY
        pattern = r'^\d{4}-\d{4}$'
        if not re.match(pattern, period):
            raise ValidationError("El período debe tener el formato YYYY-YYYY (ej: 2024-2025)")
        
        start_year, end_year = map(int, period.split('-'))
        
        if end_year != start_year + 1:
            raise ValidationError("El período debe ser de años consecutivos")
        
        current_year = get_catequesis_year()
        if start_year < current_year - 5 or start_year > current_year + 5:
            raise ValidationError("El período debe estar dentro de un rango razonable")
        
        return period
    
    @staticmethod
    def validate_catequista_type(catequista_type: str) -> str:
        """
        Valida tipo de catequista.
        
        Args:
            catequista_type: Tipo de catequista
            
        Returns:
            str: Tipo validado
            
        Raises:
            ValidationError: Si el tipo es inválido
        """
        catequista_type = CatequesisValidator.validate_required(catequista_type, "tipo de catequista")
        
        valid_types = [t.value for t in CatequistaType]
        if catequista_type not in valid_types:
            raise ValidationError(f"El tipo de catequista debe ser uno de: {', '.join(valid_types)}")
        
        return catequista_type
    
    @staticmethod
    def validate_payment_amount(amount: Union[int, float]) -> float:
        """
        Valida monto de pago.
        
        Args:
            amount: Monto a validar
            
        Returns:
            float: Monto validado
            
        Raises:
            ValidationError: Si el monto es inválido
        """
        if not isinstance(amount, (int, float)):
            raise ValidationError("El monto debe ser un número")
        
        if amount <= 0:
            raise ValidationError("El monto debe ser mayor a cero")
        
        if amount > 1000:  # Límite razonable
            raise ValidationError("El monto no puede ser mayor a $1000")
        
        return round(float(amount), 2)
    
    @staticmethod
    def validate_payment_method(method: str) -> str:
        """
        Valida método de pago.
        
        Args:
            method: Método de pago
            
        Returns:
            str: Método validado
            
        Raises:
            ValidationError: Si el método es inválido
        """
        method = CatequesisValidator.validate_required(method, "método de pago")
        
        valid_methods = [m.value for m in PaymentMethod]
        if method not in valid_methods:
            raise ValidationError(f"El método de pago debe ser uno de: {', '.join(valid_methods)}")
        
        return method


class UserValidator(BaseValidator):
    """Validador para usuarios del sistema."""
    
    @staticmethod
    def validate_username(username: str) -> str:
        """
        Valida nombre de usuario.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            str: Username validado
            
        Raises:
            ValidationError: Si el username es inválido
        """
        username = UserValidator.validate_required(username, "nombre de usuario")
        username = UserValidator.validate_length(username, "nombre de usuario", 3, 50)
        
        # Solo letras, números y guiones bajos
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("El nombre de usuario solo puede contener letras, números y guiones bajos")
        
        return username.lower()
    
    @staticmethod
    def validate_password(password: str) -> str:
        """
        Valida contraseña.
        
        Args:
            password: Contraseña
            
        Returns:
            str: Contraseña validada
            
        Raises:
            ValidationError: Si la contraseña es inválida
        """
        password = UserValidator.validate_required(password, "contraseña")
        
        min_length = ValidationConstants.MIN_PASSWORD_LENGTH
        if len(password) < min_length:
            raise ValidationError(f"La contraseña debe tener al menos {min_length} caracteres")
        
        # Verificar que tenga al menos una letra y un número
        if not re.search(r'[A-Za-z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra")
        
        if not re.search(r'\d', password):
            raise ValidationError("La contraseña debe contener al menos un número")
        
        return password
    
    @staticmethod
    def validate_user_profile(profile: str) -> str:
        """
        Valida perfil de usuario.
        
        Args:
            profile: Perfil de usuario
            
        Returns:
            str: Perfil validado
            
        Raises:
            ValidationError: Si el perfil es inválido
        """
        profile = UserValidator.validate_required(profile, "perfil de usuario")
        
        valid_profiles = [p.value for p in UserProfileType]
        if profile not in valid_profiles:
            raise ValidationError(f"El perfil debe ser uno de: {', '.join(valid_profiles)}")
        
        return profile


class BusinessRuleValidator:
    """Validador para reglas de negocio específicas del sistema."""
    
    @staticmethod
    def validate_enrollment_age(birth_date: date, enrollment_date: date = None) -> bool:
        """
        Valida que la edad sea apropiada para inscripción.
        
        Args:
            birth_date: Fecha de nacimiento
            enrollment_date: Fecha de inscripción
            
        Returns:
            bool: True si la edad es válida
            
        Raises:
            ValidationError: Si la edad no es apropiada
        """
        if enrollment_date is None:
            enrollment_date = get_current_date()
        
        age = calculate_age(birth_date, enrollment_date)
        min_age = ValidationConstants.MIN_CATEQUESIS_AGE
        max_age = ValidationConstants.MAX_CATEQUESIS_AGE
        
        if age < min_age:
            raise ValidationError(f"El catequizando debe tener al menos {min_age} años")
        
        if age > max_age:
            raise ValidationError(f"El catequizando no puede tener más de {max_age} años")
        
        return True
    
    @staticmethod
    def validate_level_progression(current_level_order: int, target_level_order: int, is_special_case: bool = False) -> bool:
        """
        Valida la progresión secuencial de niveles.
        
        Args:
            current_level_order: Orden del nivel actual
            target_level_order: Orden del nivel objetivo
            is_special_case: Si es un caso especial
            
        Returns:
            bool: True si la progresión es válida
            
        Raises:
            ValidationError: Si la progresión es inválida
        """
        if is_special_case:
            return True
        
        if current_level_order is None and target_level_order != 1:
            raise ValidationError("Debe comenzar por el primer nivel de catequesis")
        
        if current_level_order is not None and target_level_order != current_level_order + 1:
            raise ValidationError("Debe seguir la progresión secuencial de niveles")
        
        return True
    
    @staticmethod
    def validate_minimum_attendance(attended_sessions: int, total_sessions: int) -> bool:
        """
        Valida que se cumpla la asistencia mínima.
        
        Args:
            attended_sessions: Sesiones asistidas
            total_sessions: Total de sesiones
            
        Returns:
            bool: True si cumple la asistencia mínima
            
        Raises:
            ValidationError: Si no cumple la asistencia mínima
        """
        if total_sessions == 0:
            return True
        
        attendance_percentage = (attended_sessions / total_sessions) * 100
        min_percentage = ValidationConstants.MIN_ATTENDANCE_PERCENTAGE
        
        if attendance_percentage < min_percentage:
            raise ValidationError(f"Se requiere al menos {min_percentage}% de asistencia")
        
        if attended_sessions < ValidationConstants.MIN_ATTENDANCE_SESSIONS:
            min_sessions = ValidationConstants.MIN_ATTENDANCE_SESSIONS
            raise ValidationError(f"Se requiere al menos {min_sessions} sesiones de asistencia")
        
        return True
    
    @staticmethod
    def validate_group_capacity_available(current_enrollment: int, max_capacity: int) -> bool:
        """
        Valida que haya capacidad disponible en el grupo.
        
        Args:
            current_enrollment: Inscripciones actuales
            max_capacity: Capacidad máxima
            
        Returns:
            bool: True si hay capacidad disponible
            
        Raises:
            ValidationError: Si no hay capacidad
        """
        if current_enrollment >= max_capacity:
            raise ValidationError(f"El grupo ha alcanzado su capacidad máxima ({max_capacity})")
        
        return True
    
    @staticmethod
    def validate_unique_enrollment_per_level(catequizando_id: int, level_id: int, existing_enrollments: List[Dict]) -> bool:
        """
        Valida que no haya inscripciones duplicadas en el mismo nivel.
        
        Args:
            catequizando_id: ID del catequizando
            level_id: ID del nivel
            existing_enrollments: Inscripciones existentes
            
        Returns:
            bool: True si no hay duplicados
            
        Raises:
            ValidationError: Si ya está inscrito
        """
        for enrollment in existing_enrollments:
            if (enrollment.get('catequizando_id') == catequizando_id and 
                enrollment.get('level_id') == level_id):
                raise ValidationError("El catequizando ya está inscrito en este nivel")
        
        return True


def validate_data_dict(data: Dict[str, Any], validation_rules: Dict[str, List]) -> Dict[str, Any]:
    """
    Valida un diccionario de datos usando reglas específicas.
    
    Args:
        data: Datos a validar
        validation_rules: Reglas de validación por campo
        
    Returns:
        dict: Datos validados
        
    Raises:
        ValidationError: Si alguna validación falla
    """
    validated_data = {}
    errors = {}
    
    for field, rules in validation_rules.items():
        try:
            value = data.get(field)
            
            for rule in rules:
                if callable(rule):
                    value = rule(value)
                elif isinstance(rule, dict):
                    validator_func = rule.get('validator')
                    params = rule.get('params', {})
                    if validator_func:
                        value = validator_func(value, **params)
            
            validated_data[field] = value
            
        except ValidationError as e:
            errors[field] = str(e)
    
    if errors:
        raise ValidationError(errors)
    
    return validated_data