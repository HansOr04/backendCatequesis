"""
Utilidades para manejo de fechas y tiempo en el Sistema de Catequesis.
Funciones específicas para trabajar con fechas, tiempo y períodos del sistema.
"""

import calendar
from datetime import datetime, date, time, timedelta
from typing import List, Tuple, Optional, Union
import pytz
from app.utils.constants import SystemConstants


# Configuración de timezone
ECUADOR_TZ = pytz.timezone(SystemConstants.DEFAULT_TIMEZONE)
UTC_TZ = pytz.UTC


def get_current_datetime(timezone_aware: bool = True) -> datetime:
    """
    Obtiene la fecha y hora actual.
    
    Args:
        timezone_aware: Si incluir información de timezone
        
    Returns:
        datetime: Fecha y hora actual
    """
    if timezone_aware:
        return datetime.now(ECUADOR_TZ)
    return datetime.now()


def get_current_date() -> date:
    """
    Obtiene la fecha actual.
    
    Returns:
        date: Fecha actual
    """
    return date.today()


def get_current_time() -> time:
    """
    Obtiene la hora actual.
    
    Returns:
        time: Hora actual
    """
    return datetime.now().time()


def convert_to_ecuador_time(dt: datetime) -> datetime:
    """
    Convierte una fecha/hora a timezone de Ecuador.
    
    Args:
        dt: Datetime a convertir
        
    Returns:
        datetime: Datetime en timezone de Ecuador
    """
    if dt.tzinfo is None:
        # Asumir que es UTC si no tiene timezone
        dt = UTC_TZ.localize(dt)
    
    return dt.astimezone(ECUADOR_TZ)


def convert_to_utc(dt: datetime) -> datetime:
    """
    Convierte una fecha/hora a UTC.
    
    Args:
        dt: Datetime a convertir
        
    Returns:
        datetime: Datetime en UTC
    """
    if dt.tzinfo is None:
        # Asumir que es timezone local si no tiene timezone
        dt = ECUADOR_TZ.localize(dt)
    
    return dt.astimezone(UTC_TZ)


def parse_date(date_str: str, format_str: str = None) -> Optional[date]:
    """
    Parsea una cadena de fecha a objeto date.
    
    Args:
        date_str: Cadena de fecha
        format_str: Formato de la fecha (por defecto %d/%m/%Y)
        
    Returns:
        date: Objeto date o None si falla
    """
    if not date_str:
        return None
    
    if format_str is None:
        format_str = SystemConstants.DATE_FORMAT
    
    try:
        return datetime.strptime(date_str, format_str).date()
    except ValueError:
        # Intentar con otros formatos comunes
        common_formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%Y/%m/%d"
        ]
        
        for fmt in common_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None


def parse_datetime(datetime_str: str, format_str: str = None) -> Optional[datetime]:
    """
    Parsea una cadena de fecha/hora a objeto datetime.
    
    Args:
        datetime_str: Cadena de fecha/hora
        format_str: Formato de la fecha/hora
        
    Returns:
        datetime: Objeto datetime o None si falla
    """
    if not datetime_str:
        return None
    
    if format_str is None:
        format_str = SystemConstants.DATETIME_FORMAT
    
    try:
        return datetime.strptime(datetime_str, format_str)
    except ValueError:
        # Intentar con formatos ISO
        iso_formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f"
        ]
        
        for fmt in iso_formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        return None


def format_date(date_obj: date, format_str: str = None) -> str:
    """
    Formatea un objeto date a string.
    
    Args:
        date_obj: Objeto date
        format_str: Formato deseado
        
    Returns:
        str: Fecha formateada
    """
    if not date_obj:
        return ""
    
    if format_str is None:
        format_str = SystemConstants.DATE_FORMAT
    
    return date_obj.strftime(format_str)


def format_datetime(datetime_obj: datetime, format_str: str = None, include_timezone: bool = False) -> str:
    """
    Formatea un objeto datetime a string.
    
    Args:
        datetime_obj: Objeto datetime
        format_str: Formato deseado
        include_timezone: Si incluir información de timezone
        
    Returns:
        str: Fecha/hora formateada
    """
    if not datetime_obj:
        return ""
    
    if format_str is None:
        format_str = SystemConstants.DATETIME_FORMAT
    
    if include_timezone and datetime_obj.tzinfo:
        format_str += " %Z"
    
    return datetime_obj.strftime(format_str)


def get_age_in_years(birth_date: date, reference_date: date = None) -> int:
    """
    Calcula la edad en años.
    
    Args:
        birth_date: Fecha de nacimiento
        reference_date: Fecha de referencia (por defecto hoy)
        
    Returns:
        int: Edad en años
    """
    if reference_date is None:
        reference_date = get_current_date()
    
    age = reference_date.year - birth_date.year
    
    # Verificar si ya cumplió años este año
    if reference_date.month < birth_date.month or \
       (reference_date.month == birth_date.month and reference_date.day < birth_date.day):
        age -= 1
    
    return age


def get_age_in_months(birth_date: date, reference_date: date = None) -> int:
    """
    Calcula la edad en meses.
    
    Args:
        birth_date: Fecha de nacimiento
        reference_date: Fecha de referencia
        
    Returns:
        int: Edad en meses
    """
    if reference_date is None:
        reference_date = get_current_date()
    
    months = (reference_date.year - birth_date.year) * 12
    months += reference_date.month - birth_date.month
    
    if reference_date.day < birth_date.day:
        months -= 1
    
    return months


def get_catequesis_year() -> int:
    """
    Obtiene el año de catequesis actual basado en la fecha.
    El año de catequesis va de agosto a julio del siguiente año.
    
    Returns:
        int: Año de catequesis
    """
    current_date = get_current_date()
    
    if current_date.month >= 8:  # Agosto o después
        return current_date.year
    else:  # Enero a julio
        return current_date.year - 1


def get_catequesis_period(year: int = None) -> str:
    """
    Obtiene el período de catequesis en formato string.
    
    Args:
        year: Año de inicio (por defecto año actual)
        
    Returns:
        str: Período en formato "2024-2025"
    """
    if year is None:
        year = get_catequesis_year()
    
    return f"{year}-{year + 1}"


def is_enrollment_period(reference_date: date = None) -> bool:
    """
    Verifica si estamos en período de inscripciones.
    Las inscripciones suelen ser de junio a agosto.
    
    Args:
        reference_date: Fecha de referencia
        
    Returns:
        bool: True si estamos en período de inscripciones
    """
    if reference_date is None:
        reference_date = get_current_date()
    
    return 6 <= reference_date.month <= 8


def is_catequesis_active_period(reference_date: date = None) -> bool:
    """
    Verifica si estamos en período activo de catequesis.
    El período activo suele ser de septiembre a junio.
    
    Args:
        reference_date: Fecha de referencia
        
    Returns:
        bool: True si estamos en período activo
    """
    if reference_date is None:
        reference_date = get_current_date()
    
    return reference_date.month >= 9 or reference_date.month <= 6


def get_next_confirmation_date() -> date:
    """
    Calcula la próxima fecha probable de confirmación.
    Las confirmaciones suelen ser en junio.
    
    Returns:
        date: Próxima fecha de confirmación
    """
    current_date = get_current_date()
    confirmation_month = 6  # Junio
    
    if current_date.month <= confirmation_month:
        # Este año
        year = current_date.year
    else:
        # Próximo año
        year = current_date.year + 1
    
    # Buscar el primer sábado de junio
    first_day = date(year, confirmation_month, 1)
    days_until_saturday = (5 - first_day.weekday()) % 7
    return first_day + timedelta(days=days_until_saturday)


def get_weekday_name(date_obj: date, lang: str = "es") -> str:
    """
    Obtiene el nombre del día de la semana.
    
    Args:
        date_obj: Fecha
        lang: Idioma (es/en)
        
    Returns:
        str: Nombre del día
    """
    if lang == "es":
        weekdays = [
            "Lunes", "Martes", "Miércoles", "Jueves", 
            "Viernes", "Sábado", "Domingo"
        ]
        return weekdays[date_obj.weekday()]
    else:
        return date_obj.strftime("%A")


def get_month_name(month: int, lang: str = "es") -> str:
    """
    Obtiene el nombre del mes.
    
    Args:
        month: Número del mes (1-12)
        lang: Idioma (es/en)
        
    Returns:
        str: Nombre del mes
    """
    if lang == "es":
        months = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        return months[month - 1] if 1 <= month <= 12 else ""
    else:
        return calendar.month_name[month]


def get_date_range_for_month(year: int, month: int) -> Tuple[date, date]:
    """
    Obtiene el rango de fechas para un mes específico.
    
    Args:
        year: Año
        month: Mes
        
    Returns:
        tuple: (primer_dia, ultimo_dia)
    """
    first_day = date(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)
    
    return first_day, last_day


def get_date_range_for_year(year: int) -> Tuple[date, date]:
    """
    Obtiene el rango de fechas para un año específico.
    
    Args:
        year: Año
        
    Returns:
        tuple: (primer_dia, ultimo_dia)
    """
    first_day = date(year, 1, 1)
    last_day = date(year, 12, 31)
    
    return first_day, last_day


def get_catequesis_session_dates(year: int = None) -> List[date]:
    """
    Genera las fechas de sesiones de catequesis para un año.
    Asume sesiones los sábados de septiembre a junio.
    
    Args:
        year: Año de inicio del período
        
    Returns:
        list: Lista de fechas de sesiones
    """
    if year is None:
        year = get_catequesis_year()
    
    session_dates = []
    
    # Meses de catequesis (septiembre a junio del siguiente año)
    months = [
        (year, 9), (year, 10), (year, 11), (year, 12),  # Sep-Dic
        (year + 1, 1), (year + 1, 2), (year + 1, 3), 
        (year + 1, 4), (year + 1, 5), (year + 1, 6)     # Ene-Jun
    ]
    
    for year_month, month in months:
        # Obtener todos los sábados del mes
        first_day, last_day = get_date_range_for_month(year_month, month)
        
        current_date = first_day
        while current_date <= last_day:
            if current_date.weekday() == 5:  # Sábado
                session_dates.append(current_date)
            current_date += timedelta(days=1)
    
    return session_dates


def calculate_attendance_percentage(attended: int, total_sessions: int) -> float:
    """
    Calcula el porcentaje de asistencia.
    
    Args:
        attended: Sesiones asistidas
        total_sessions: Total de sesiones
        
    Returns:
        float: Porcentaje de asistencia
    """
    if total_sessions == 0:
        return 0.0
    
    return round((attended / total_sessions) * 100, 2)


def get_business_days_count(start_date: date, end_date: date) -> int:
    """
    Cuenta los días hábiles entre dos fechas (excluyendo sábados y domingos).
    
    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin
        
    Returns:
        int: Número de días hábiles
    """
    if start_date > end_date:
        return 0
    
    current_date = start_date
    business_days = 0
    
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Lunes a viernes
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


def get_time_until_date(target_date: date) -> dict:
    """
    Calcula el tiempo restante hasta una fecha específica.
    
    Args:
        target_date: Fecha objetivo
        
    Returns:
        dict: Diccionario con días, horas, minutos restantes
    """
    current_datetime = get_current_datetime(timezone_aware=False)
    target_datetime = datetime.combine(target_date, time.max)
    
    if target_datetime <= current_datetime:
        return {"days": 0, "hours": 0, "minutes": 0, "expired": True}
    
    time_diff = target_datetime - current_datetime
    
    days = time_diff.days
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "expired": False
    }


def is_valid_birth_date(birth_date: date, min_age: int = 0, max_age: int = 120) -> bool:
    """
    Valida si una fecha de nacimiento es válida.
    
    Args:
        birth_date: Fecha de nacimiento
        min_age: Edad mínima permitida
        max_age: Edad máxima permitida
        
    Returns:
        bool: True si la fecha es válida
    """
    if not birth_date:
        return False
    
    current_date = get_current_date()
    
    # No puede ser una fecha futura
    if birth_date > current_date:
        return False
    
    age = get_age_in_years(birth_date, current_date)
    
    return min_age <= age <= max_age


def get_relative_time_string(target_datetime: datetime, reference_datetime: datetime = None) -> str:
    """
    Obtiene una representación de tiempo relativo en español.
    
    Args:
        target_datetime: Fecha/hora objetivo
        reference_datetime: Fecha/hora de referencia
        
    Returns:
        str: Tiempo relativo (ej: "hace 2 horas", "en 3 días")
    """
    if reference_datetime is None:
        reference_datetime = get_current_datetime(timezone_aware=False)
    
    time_diff = target_datetime - reference_datetime
    
    if time_diff.total_seconds() == 0:
        return "ahora"
    
    future = time_diff.total_seconds() > 0
    abs_diff = abs(time_diff.total_seconds())
    
    # Convertir a diferentes unidades
    minutes = abs_diff / 60
    hours = minutes / 60
    days = hours / 24
    weeks = days / 7
    months = days / 30
    years = days / 365
    
    if abs_diff < 60:
        return "ahora"
    elif minutes < 60:
        unit = "minuto" if int(minutes) == 1 else "minutos"
        time_str = f"{int(minutes)} {unit}"
    elif hours < 24:
        unit = "hora" if int(hours) == 1 else "horas"
        time_str = f"{int(hours)} {unit}"
    elif days < 7:
        unit = "día" if int(days) == 1 else "días"
        time_str = f"{int(days)} {unit}"
    elif weeks < 4:
        unit = "semana" if int(weeks) == 1 else "semanas"
        time_str = f"{int(weeks)} {unit}"
    elif months < 12:
        unit = "mes" if int(months) == 1 else "meses"
        time_str = f"{int(months)} {unit}"
    else:
        unit = "año" if int(years) == 1 else "años"
        time_str = f"{int(years)} {unit}"
    
    if future:
        return f"en {time_str}"
    else:
        return f"hace {time_str}"


def get_easter_date(year: int) -> date:
    """
    Calcula la fecha de Pascua para un año específico.
    Útil para calcular fechas relacionadas con el calendario litúrgico.
    
    Args:
        year: Año
        
    Returns:
        date: Fecha de Pascua
    """
    # Algoritmo de Gauss para calcular la Pascua
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    
    return date(year, month, day)


def get_liturgical_season_dates(year: int) -> dict:
    """
    Obtiene las fechas importantes del calendario litúrgico.
    
    Args:
        year: Año
        
    Returns:
        dict: Diccionario con fechas litúrgicas importantes
    """
    easter = get_easter_date(year)
    
    return {
        "epifania": date(year, 1, 6),
        "miercoles_ceniza": easter - timedelta(days=46),
        "domingo_ramos": easter - timedelta(days=7),
        "jueves_santo": easter - timedelta(days=3),
        "viernes_santo": easter - timedelta(days=2),
        "pascua": easter,
        "ascension": easter + timedelta(days=39),
        "pentecostes": easter + timedelta(days=49),
        "corpus_christi": easter + timedelta(days=60),
        "sagrado_corazon": easter + timedelta(days=68),
        "navidad": date(year, 12, 25)
    }


def is_liturgical_season(season: str, reference_date: date = None) -> bool:
    """
    Verifica si estamos en una temporada litúrgica específica.
    
    Args:
        season: Temporada litúrgica (adviento, navidad, cuaresma, pascua, ordinario)
        reference_date: Fecha de referencia
        
    Returns:
        bool: True si estamos en la temporada especificada
    """
    if reference_date is None:
        reference_date = get_current_date()
    
    year = reference_date.year
    liturgical_dates = get_liturgical_season_dates(year)
    
    if season == "adviento":
        # 4 domingos antes de Navidad
        advent_start = liturgical_dates["navidad"] - timedelta(days=28)
        return advent_start <= reference_date <= liturgical_dates["navidad"]
    
    elif season == "navidad":
        # De Navidad a Epifanía
        christmas_start = liturgical_dates["navidad"]
        epiphany_next_year = date(year + 1, 1, 6)
        return christmas_start <= reference_date <= epiphany_next_year
    
    elif season == "cuaresma":
        # De Miércoles de Ceniza a Jueves Santo
        return liturgical_dates["miercoles_ceniza"] <= reference_date <= liturgical_dates["jueves_santo"]
    
    elif season == "pascua":
        # De Pascua a Pentecostés
        return liturgical_dates["pascua"] <= reference_date <= liturgical_dates["pentecostes"]
    
    else:
        # Tiempo ordinario (el resto del año)
        return not any([
            is_liturgical_season("adviento", reference_date),
            is_liturgical_season("navidad", reference_date),
            is_liturgical_season("cuaresma", reference_date),
            is_liturgical_season("pascua", reference_date)
        ])


def get_confirmation_season_dates(year: int) -> List[date]:
    """
    Obtiene las fechas típicas para confirmaciones en el año.
    
    Args:
        year: Año
        
    Returns:
        list: Lista de fechas probables para confirmaciones
    """
    confirmation_dates = []
    
    # Pentecostés (fecha tradicional)
    liturgical_dates = get_liturgical_season_dates(year)
    confirmation_dates.append(liturgical_dates["pentecostes"])
    
    # Sábados de mayo y junio
    for month in [5, 6]:
        first_day, last_day = get_date_range_for_month(year, month)
        current_date = first_day
        
        while current_date <= last_day:
            if current_date.weekday() == 5:  # Sábado
                confirmation_dates.append(current_date)
            current_date += timedelta(days=1)
    
    return sorted(set(confirmation_dates))


def format_time_duration(start_time: time, end_time: time) -> str:
    """
    Formatea la duración entre dos horas.
    
    Args:
        start_time: Hora de inicio
        end_time: Hora de fin
        
    Returns:
        str: Duración formateada (ej: "2 horas 30 minutos")
    """
    # Convertir a datetime para calcular diferencia
    today = get_current_date()
    start_dt = datetime.combine(today, start_time)
    end_dt = datetime.combine(today, end_time)
    
    # Si end_time es menor, asumir que es del día siguiente
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    
    duration = end_dt - start_dt
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        unit = "hora" if hours == 1 else "horas"
        parts.append(f"{int(hours)} {unit}")
    
    if minutes > 0:
        unit = "minuto" if minutes == 1 else "minutos"
        parts.append(f"{int(minutes)} {unit}")
    
    return " ".join(parts) if parts else "0 minutos"


def get_academic_semester(reference_date: date = None) -> str:
    """
    Determina el semestre académico basado en la fecha.
    
    Args:
        reference_date: Fecha de referencia
        
    Returns:
        str: Semestre académico ("2024-1" o "2024-2")
    """
    if reference_date is None:
        reference_date = get_current_date()
    
    if 1 <= reference_date.month <= 7:
        # Primer semestre (enero-julio)
        return f"{reference_date.year}-1"
    else:
        # Segundo semestre (agosto-diciembre)
        return f"{reference_date.year}-2"


def is_holiday_ecuador(check_date: date) -> bool:
    """
    Verifica si una fecha es feriado en Ecuador.
    
    Args:
        check_date: Fecha a verificar
        
    Returns:
        bool: True si es feriado
    """
    year = check_date.year
    
    # Feriados fijos
    fixed_holidays = [
        date(year, 1, 1),   # Año Nuevo
        date(year, 5, 1),   # Día del Trabajador
        date(year, 5, 24),  # Batalla de Pichincha
        date(year, 8, 10),  # Primer Grito de Independencia
        date(year, 10, 9),  # Independencia de Guayaquil
        date(year, 11, 2),  # Día de los Difuntos
        date(year, 11, 3),  # Independencia de Cuenca
        date(year, 12, 25), # Navidad
    ]
    
    # Feriados móviles (basados en Pascua)
    liturgical_dates = get_liturgical_season_dates(year)
    mobile_holidays = [
        liturgical_dates["viernes_santo"],
        liturgical_dates["miercoles_ceniza"],
    ]
    
    all_holidays = fixed_holidays + mobile_holidays
    
    return check_date in all_holidays


def get_next_business_day(reference_date: date = None) -> date:
    """
    Obtiene el próximo día hábil (excluyendo fines de semana y feriados).
    
    Args:
        reference_date: Fecha de referencia
        
    Returns:
        date: Próximo día hábil
    """
    if reference_date is None:
        reference_date = get_current_date()
    
    next_day = reference_date + timedelta(days=1)
    
    while next_day.weekday() >= 5 or is_holiday_ecuador(next_day):
        next_day += timedelta(days=1)
    
    return next_day


def generate_attendance_calendar(year: int, group_schedule: str = "saturday") -> List[date]:
    """
    Genera un calendario de asistencia para el año de catequesis.
    
    Args:
        year: Año de inicio del período
        group_schedule: Día de la semana para las clases
        
    Returns:
        list: Lista de fechas de clases
    """
    schedule_map = {
        "saturday": 5,
        "sunday": 6,
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4
    }
    
    target_weekday = schedule_map.get(group_schedule, 5)  # Por defecto sábado
    
    session_dates = []
    
    # Período de catequesis: septiembre a junio
    start_date = date(year, 9, 1)
    end_date = date(year + 1, 6, 30)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == target_weekday:
            # Excluir feriados y vacaciones
            if not is_holiday_ecuador(current_date) and not is_vacation_period(current_date):
                session_dates.append(current_date)
        current_date += timedelta(days=1)
    
    return session_dates


def is_vacation_period(check_date: date) -> bool:
    """
    Verifica si una fecha está en período de vacaciones escolares.
    
    Args:
        check_date: Fecha a verificar
        
    Returns:
        bool: True si está en vacaciones
    """
    month = check_date.month
    day = check_date.day
    
    # Vacaciones de Navidad (15 dic - 15 ene)
    if (month == 12 and day >= 15) or (month == 1 and day <= 15):
        return True
    
    # Vacaciones de Semana Santa (variable)
    year = check_date.year
    liturgical_dates = get_liturgical_season_dates(year)
    easter = liturgical_dates["pascua"]
    
    # Una semana antes y después de Pascua
    vacation_start = easter - timedelta(days=7)
    vacation_end = easter + timedelta(days=7)
    
    if vacation_start <= check_date <= vacation_end:
        return True
    
    # Vacaciones de verano (julio-agosto para algunas instituciones)
    if month in [7, 8]:
        return True
    
    return False


def calculate_session_number(session_date: date, calendar_dates: List[date]) -> int:
    """
    Calcula el número de sesión basado en la fecha y el calendario.
    
    Args:
        session_date: Fecha de la sesión
        calendar_dates: Lista de fechas del calendario
        
    Returns:
        int: Número de sesión (1-based) o 0 si no se encuentra
    """
    try:
        return calendar_dates.index(session_date) + 1
    except ValueError:
        return 0