"""
Modelo de Catequizando para el sistema de catequesis.
Representa a los estudiantes de catequesis con toda su información personal y académica.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator
from app.utils.constants import SystemConstants

logger = logging.getLogger(__name__)


class TipoDocumento(Enum):
    """Tipos de documento de identidad."""
    CEDULA = "cedula"
    TARJETA_IDENTIDAD = "tarjeta_identidad"
    CEDULA_EXTRANJERIA = "cedula_extranjeria"
    PASAPORTE = "pasaporte"
    REGISTRO_CIVIL = "registro_civil"
    SIN_DOCUMENTO = "sin_documento"


class EstadoCatequizando(Enum):
    """Estados del catequizando."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    GRADUADO = "graduado"
    RETIRADO = "retirado"
    SUSPENDIDO = "suspendido"
    TRANSFERIDO = "transferido"


class Genero(Enum):
    """Géneros disponibles."""
    MASCULINO = "masculino"
    FEMENINO = "femenino"
    OTRO = "otro"
    NO_ESPECIFICA = "no_especifica"


class EstadoCivil(Enum):
    """Estados civiles."""
    SOLTERO = "soltero"
    CASADO = "casado"
    UNION_LIBRE = "union_libre"
    VIUDO = "viudo"
    DIVORCIADO = "divorciado"
    SEPARADO = "separado"


class Catequizando(BaseModel):
    """
    Modelo de Catequizando del sistema de catequesis.
    Representa a los estudiantes con toda su información personal y académica.
    """
    
    # Configuración del modelo
    _table_schema = "catequizandos"
    _primary_key = "id_catequizando"
    _required_fields = ["nombres", "apellidos", "fecha_nacimiento"]
    _unique_fields = ["documento_identidad"]
    _searchable_fields = [
        "nombres", "apellidos", "documento_identidad", 
        "telefono", "email", "nombres_padre", "nombres_madre"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Catequizando."""
        # Identificación básica
        self.id_catequizando: Optional[int] = None
        self.nombres: str = ""
        self.apellidos: str = ""
        self.fecha_nacimiento: Optional[date] = None
        self.lugar_nacimiento: Optional[str] = None
        self.genero: Genero = Genero.NO_ESPECIFICA
        self.estado: EstadoCatequizando = EstadoCatequizando.ACTIVO
        
        # Documentación
        self.tipo_documento: TipoDocumento = TipoDocumento.SIN_DOCUMENTO
        self.documento_identidad: Optional[str] = None
        self.fecha_expedicion_documento: Optional[date] = None
        self.lugar_expedicion_documento: Optional[str] = None
        
        # Información de contacto
        self.direccion: Optional[str] = None
        self.barrio: Optional[str] = None
        self.ciudad: Optional[str] = None
        self.departamento: Optional[str] = None
        self.telefono: Optional[str] = None
        self.telefono_alternativo: Optional[str] = None
        self.email: Optional[str] = None
        
        # Información familiar
        self.nombres_padre: Optional[str] = None
        self.apellidos_padre: Optional[str] = None
        self.telefono_padre: Optional[str] = None
        self.email_padre: Optional[str] = None
        self.ocupacion_padre: Optional[str] = None
        
        self.nombres_madre: Optional[str] = None
        self.apellidos_madre: Optional[str] = None
        self.telefono_madre: Optional[str] = None
        self.email_madre: Optional[str] = None
        self.ocupacion_madre: Optional[str] = None
        
        # Información académica
        self.nivel_educativo: Optional[str] = None
        self.institucion_educativa: Optional[str] = None
        self.grado_cursando: Optional[str] = None
        self.tiene_necesidades_especiales: bool = False
        self.descripcion_necesidades_especiales: Optional[str] = None
        
        # Información sacramental
        self.fecha_bautismo: Optional[date] = None
        self.lugar_bautismo: Optional[str] = None
        self.padrino_bautismo: Optional[str] = None
        self.madrina_bautismo: Optional[str] = None
        
        self.fecha_primera_comunion: Optional[date] = None
        self.lugar_primera_comunion: Optional[str] = None
        
        self.fecha_confirmacion: Optional[date] = None
        self.lugar_confirmacion: Optional[str] = None
        self.padrino_confirmacion: Optional[str] = None
        
        # Estado civil (para mayores de edad)
        self.estado_civil: EstadoCivil = EstadoCivil.SOLTERO
        self.fecha_matrimonio: Optional[date] = None
        self.lugar_matrimonio: Optional[str] = None
        
        # Información médica básica
        self.tipo_sangre: Optional[str] = None
        self.alergias: List[str] = []
        self.medicamentos: List[str] = []
        self.contacto_emergencia_nombre: Optional[str] = None
        self.contacto_emergencia_telefono: Optional[str] = None
        self.contacto_emergencia_parentesco: Optional[str] = None
        
        # Control administrativo
        self.es_caso_especial: bool = False
        self.motivo_caso_especial: Optional[str] = None
        self.fecha_ingreso: Optional[date] = None
        self.fecha_retiro: Optional[date] = None
        self.motivo_retiro: Optional[str] = None
        
        # Observaciones y notas
        self.observaciones_generales: Optional[str] = None
        self.observaciones_comportamiento: Optional[str] = None
        self.observaciones_academicas: Optional[str] = None
        
        # Configuración de privacidad
        self.autoriza_fotos: bool = True
        self.autoriza_datos_contacto: bool = True
        self.autoriza_comunicaciones: bool = True
        
        super().__init__(**kwargs)
    
    @property
    def nombre_completo(self) -> str:
        """Obtiene el nombre completo."""
        return f"{self.nombres} {self.apellidos}".strip()
    
    @property
    def edad(self) -> Optional[int]:
        """Calcula la edad actual."""
        if not self.fecha_nacimiento:
            return None
        
        today = date.today()
        edad = today.year - self.fecha_nacimiento.year
        
        # Ajustar si no ha cumplido años este año
        if today.month < self.fecha_nacimiento.month or \
           (today.month == self.fecha_nacimiento.month and today.day < self.fecha_nacimiento.day):
            edad -= 1
        
        return edad
    
    @property
    def es_menor_edad(self) -> bool:
        """Verifica si es menor de edad."""
        edad = self.edad
        return edad is not None and edad < 18
    
    @property
    def esta_activo(self) -> bool:
        """Verifica si está activo."""
        return self.estado == EstadoCatequizando.ACTIVO
    
    @property
    def contacto_padre_completo(self) -> Optional[str]:
        """Obtiene el contacto completo del padre."""
        if not self.nombres_padre:
            return None
        
        padre = f"{self.nombres_padre} {self.apellidos_padre or ''}".strip()
        if self.telefono_padre:
            padre += f" - {self.telefono_padre}"
        return padre
    
    @property
    def contacto_madre_completo(self) -> Optional[str]:
        """Obtiene el contacto completo de la madre."""
        if not self.nombres_madre:
            return None
        
        madre = f"{self.nombres_madre} {self.apellidos_madre or ''}".strip()
        if self.telefono_madre:
            madre += f" - {self.telefono_madre}"
        return madre
    
    @property
    def tiene_sacramentos_previos(self) -> bool:
        """Verifica si tiene sacramentos previos."""
        return self.fecha_bautismo is not None
    
    @property
    def direccion_completa(self) -> str:
        """Obtiene la dirección completa."""
        direccion_parts = []
        
        if self.direccion:
            direccion_parts.append(self.direccion)
        if self.barrio:
            direccion_parts.append(f"Barrio {self.barrio}")
        if self.ciudad:
            direccion_parts.append(self.ciudad)
        if self.departamento:
            direccion_parts.append(self.departamento)
        
        return ", ".join(direccion_parts)
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Catequizando."""
        # Validar nombres y apellidos
        if self.nombres and len(self.nombres.strip()) < 2:
            raise ValidationError("Los nombres deben tener al menos 2 caracteres")
        
        if self.apellidos and len(self.apellidos.strip()) < 2:
            raise ValidationError("Los apellidos deben tener al menos 2 caracteres")
        
        # Validar fecha de nacimiento
        if self.fecha_nacimiento:
            today = date.today()
            edad = self.edad
            
            if self.fecha_nacimiento > today:
                raise ValidationError("La fecha de nacimiento no puede ser futura")
            
            if edad is not None:
                if edad < 3:
                    raise ValidationError("La edad mínima es 3 años")
                if edad > 80:
                    raise ValidationError("La edad máxima es 80 años")
        
        # Validar documento de identidad
        if self.documento_identidad:
            if self.tipo_documento == TipoDocumento.SIN_DOCUMENTO:
                raise ValidationError("Debe especificar el tipo de documento")
            
            # Validaciones específicas por tipo de documento
            if self.tipo_documento == TipoDocumento.CEDULA:
                if not DataValidator.validate_cedula(self.documento_identidad):
                    raise ValidationError("El número de cédula no es válido")
        
        # Validar teléfonos
        if self.telefono and not DataValidator.validate_phone(self.telefono):
            raise ValidationError("El formato del teléfono principal no es válido")
        
        if self.telefono_alternativo and not DataValidator.validate_phone(self.telefono_alternativo):
            raise ValidationError("El formato del teléfono alternativo no es válido")
        
        # Validar emails
        if self.email and not DataValidator.validate_email(self.email):
            raise ValidationError("El formato del email no es válido")
        
        if self.email_padre and not DataValidator.validate_email(self.email_padre):
            raise ValidationError("El formato del email del padre no es válido")
        
        if self.email_madre and not DataValidator.validate_email(self.email_madre):
            raise ValidationError("El formato del email de la madre no es válido")
        
        # Validar fechas sacramentales
        if self.fecha_bautismo and self.fecha_nacimiento:
            if self.fecha_bautismo < self.fecha_nacimiento:
                raise ValidationError("La fecha de bautismo no puede ser anterior al nacimiento")
        
        if self.fecha_primera_comunion and self.fecha_bautismo:
            if self.fecha_primera_comunion < self.fecha_bautismo:
                raise ValidationError("La Primera Comunión debe ser posterior al bautismo")
        
        if self.fecha_confirmacion and self.fecha_primera_comunion:
            if self.fecha_confirmacion < self.fecha_primera_comunion:
                raise ValidationError("La Confirmación debe ser posterior a la Primera Comunión")
        
        # Validar contacto de emergencia para menores
        if self.es_menor_edad:
            if not self.contacto_emergencia_nombre or not self.contacto_emergencia_telefono:
                if not (self.nombres_padre or self.nombres_madre):
                    raise ValidationError("Los menores de edad requieren contacto de emergencia o datos de padres")
        
        # Validar enums
        if isinstance(self.genero, str):
            try:
                self.genero = Genero(self.genero)
            except ValueError:
                raise ValidationError(f"Género '{self.genero}' no válido")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoCatequizando(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.tipo_documento, str):
            try:
                self.tipo_documento = TipoDocumento(self.tipo_documento)
            except ValueError:
                raise ValidationError(f"Tipo de documento '{self.tipo_documento}' no válido")
        
        if isinstance(self.estado_civil, str):
            try:
                self.estado_civil = EstadoCivil(self.estado_civil)
            except ValueError:
                raise ValidationError(f"Estado civil '{self.estado_civil}' no válido")
    
    def calcular_edad_en_fecha(self, fecha_referencia: date) -> int:
        """
        Calcula la edad en una fecha específica.
        
        Args:
            fecha_referencia: Fecha para calcular la edad
            
        Returns:
            int: Edad en la fecha de referencia
        """
        if not self.fecha_nacimiento:
            raise ValidationError("No se puede calcular la edad sin fecha de nacimiento")
        
        edad = fecha_referencia.year - self.fecha_nacimiento.year
        
        if fecha_referencia.month < self.fecha_nacimiento.month or \
           (fecha_referencia.month == self.fecha_nacimiento.month and 
            fecha_referencia.day < self.fecha_nacimiento.day):
            edad -= 1
        
        return edad
    
    def es_apto_para_nivel(self, nivel) -> Dict[str, Any]:
        """
        Verifica si es apto para un nivel específico.
        
        Args:
            nivel: Instancia del modelo Nivel
            
        Returns:
            dict: Resultado de la verificación
        """
        if not self.fecha_nacimiento:
            return {
                'apto': False,
                'razon': 'No tiene fecha de nacimiento registrada'
            }
        
        edad = self.edad
        if edad is None:
            return {
                'apto': False,
                'razon': 'No se puede calcular la edad'
            }
        
        if not nivel.verificar_edad_apropiada(edad):
            return {
                'apto': False,
                'razon': f'Edad {edad} años fuera del rango {nivel.rango_edad_descripcion}'
            }
        
        # Verificar sacramento previo si es requerido
        if nivel.prepara_sacramento:
            if nivel.prepara_sacramento.lower() == 'primera comunión' and not self.fecha_bautismo:
                return {
                    'apto': False,
                    'razon': 'Requiere bautismo para Primera Comunión'
                }
            
            if nivel.prepara_sacramento.lower() == 'confirmación' and not self.fecha_primera_comunion:
                return {
                    'apto': False,
                    'razon': 'Requiere Primera Comunión para Confirmación'
                }
        
        return {
            'apto': True,
            'razon': 'Cumple todos los requisitos'
        }
    
    def obtener_inscripciones_activas(self) -> List[Dict[str, Any]]:
        """
        Obtiene las inscripciones activas del catequizando.
        
        Returns:
            List: Lista de inscripciones activas
        """
        try:
            result = self._sp_manager.inscripciones.obtener_inscripciones_por_catequizando(
                self.id_catequizando
            )
            
            if result.get('success') and result.get('data'):
                # Filtrar solo inscripciones activas
                return [
                    inscripcion for inscripcion in result['data']
                    if inscripcion.get('estado') == 'activa'
                ]
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo inscripciones del catequizando {self.id_catequizando}: {str(e)}")
            return []
    
    def obtener_historial_asistencias(
        self,
        fecha_inicio: date = None,
        fecha_fin: date = None
    ) -> Dict[str, Any]:
        """
        Obtiene el historial de asistencias.
        
        Args:
            fecha_inicio: Fecha de inicio del período (opcional)
            fecha_fin: Fecha de fin del período (opcional)
            
        Returns:
            dict: Historial de asistencias con estadísticas
        """
        try:
            result = self._sp_manager.asistencias.obtener_asistencias_por_catequizando(
                id_catequizando=self.id_catequizando,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            if result.get('success') and result.get('data'):
                asistencias = result['data']
                
                total_clases = len(asistencias)
                asistencias_presentes = len([a for a in asistencias if a.get('presente')])
                
                porcentaje_asistencia = 0
                if total_clases > 0:
                    porcentaje_asistencia = (asistencias_presentes / total_clases) * 100
                
                return {
                    'asistencias': asistencias,
                    'estadisticas': {
                        'total_clases': total_clases,
                        'asistencias_presentes': asistencias_presentes,
                        'asistencias_ausentes': total_clases - asistencias_presentes,
                        'porcentaje_asistencia': round(porcentaje_asistencia, 2)
                    }
                }
            
            return {
                'asistencias': [],
                'estadisticas': {
                    'total_clases': 0,
                    'asistencias_presentes': 0,
                    'asistencias_ausentes': 0,
                    'porcentaje_asistencia': 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo historial de asistencias: {str(e)}")
            return {'asistencias': [], 'estadisticas': {}}
    
    def obtener_calificaciones(self, id_grupo: int = None) -> Dict[str, Any]:
        """
        Obtiene las calificaciones del catequizando.
        
        Args:
            id_grupo: ID del grupo específico (opcional)
            
        Returns:
            dict: Calificaciones con estadísticas
        """
        try:
            result = self._sp_manager.calificaciones.obtener_calificaciones_por_catequizando(
                id_catequizando=self.id_catequizando,
                id_grupo=id_grupo
            )
            
            if result.get('success') and result.get('data'):
                calificaciones = result['data']
                
                if calificaciones:
                    notas = [c['calificacion'] for c in calificaciones if c.get('calificacion') is not None]
                    
                    promedio = sum(notas) / len(notas) if notas else 0
                    nota_maxima = max(notas) if notas else 0
                    nota_minima = min(notas) if notas else 0
                    
                    return {
                        'calificaciones': calificaciones,
                        'estadisticas': {
                            'promedio': round(promedio, 2),
                            'nota_maxima': nota_maxima,
                            'nota_minima': nota_minima,
                            'total_evaluaciones': len(calificaciones)
                        }
                    }
            
            return {
                'calificaciones': [],
                'estadisticas': {
                    'promedio': 0,
                    'nota_maxima': 0,
                    'nota_minima': 0,
                    'total_evaluaciones': 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo calificaciones: {str(e)}")
            return {'calificaciones': [], 'estadisticas': {}}
    
    def agregar_alergia(self, alergia: str) -> None:
        """Agrega una alergia."""
        if alergia and alergia not in self.alergias:
            self.alergias.append(alergia)
    
    def remover_alergia(self, alergia: str) -> None:
        """Remueve una alergia."""
        if alergia in self.alergias:
            self.alergias.remove(alergia)
    
    def agregar_medicamento(self, medicamento: str) -> None:
        """Agrega un medicamento."""
        if medicamento and medicamento not in self.medicamentos:
            self.medicamentos.append(medicamento)
    
    def remover_medicamento(self, medicamento: str) -> None:
        """Remueve un medicamento."""
        if medicamento in self.medicamentos:
            self.medicamentos.remove(medicamento)
    
    def registrar_bautismo(
        self,
        fecha_bautismo: date,
        lugar_bautismo: str,
        padrino: str = None,
        madrina: str = None
    ) -> None:
        """
        Registra la información del bautismo.
        
        Args:
            fecha_bautismo: Fecha del bautismo
            lugar_bautismo: Lugar donde fue bautizado
            padrino: Nombre del padrino (opcional)
            madrina: Nombre de la madrina (opcional)
        """
        self.fecha_bautismo = fecha_bautismo
        self.lugar_bautismo = lugar_bautismo
        self.padrino_bautismo = padrino
        self.madrina_bautismo = madrina
    
    def registrar_primera_comunion(
        self,
        fecha_primera_comunion: date,
        lugar_primera_comunion: str
    ) -> None:
        """
        Registra la Primera Comunión.
        
        Args:
            fecha_primera_comunion: Fecha de la Primera Comunión
            lugar_primera_comunion: Lugar de la Primera Comunión
        """
        if not self.fecha_bautismo:
            raise ValidationError("Debe tener registro de bautismo antes de la Primera Comunión")
        
        self.fecha_primera_comunion = fecha_primera_comunion
        self.lugar_primera_comunion = lugar_primera_comunion
    
    def registrar_confirmacion(
        self,
        fecha_confirmacion: date,
        lugar_confirmacion: str,
        padrino: str = None
    ) -> None:
        """
        Registra la Confirmación.
        
        Args:
            fecha_confirmacion: Fecha de la Confirmación
            lugar_confirmacion: Lugar de la Confirmación
            padrino: Nombre del padrino (opcional)
        """
        if not self.fecha_primera_comunion:
            raise ValidationError("Debe tener registro de Primera Comunión antes de la Confirmación")
        
        self.fecha_confirmacion = fecha_confirmacion
        self.lugar_confirmacion = lugar_confirmacion
        self.padrino_confirmacion = padrino
    
    def marcar_como_caso_especial(self, motivo: str) -> None:
        """
        Marca como caso especial.
        
        Args:
            motivo: Motivo del caso especial
        """
        self.es_caso_especial = True
        self.motivo_caso_especial = motivo
    
    def quitar_caso_especial(self) -> None:
        """Quita el marcado de caso especial."""
        self.es_caso_especial = False
        self.motivo_caso_especial = None
    
    def retirar(self, motivo: str, fecha_retiro: date = None) -> None:
        """
        Retira al catequizando.
        
        Args:
            motivo: Motivo del retiro
            fecha_retiro: Fecha del retiro (por defecto hoy)
        """
        self.estado = EstadoCatequizando.RETIRADO
        self.motivo_retiro = motivo
        self.fecha_retiro = fecha_retiro or date.today()
        
        logger.info(f"Catequizando {self.nombre_completo} retirado: {motivo}")
    
    def reactivar(self) -> None:
        """Reactiva al catequizando."""
        self.estado = EstadoCatequizando.ACTIVO
        self.motivo_retiro = None
        self.fecha_retiro = None
        
        logger.info(f"Catequizando {self.nombre_completo} reactivado")
    
    def transferir(self, motivo: str = "Transferencia") -> None:
        """Marca como transferido."""
        self.estado = EstadoCatequizando.TRANSFERIDO
        self.motivo_retiro = motivo
        self.fecha_retiro = date.today()
    
    def graduar(self) -> None:
        """Marca como graduado."""
        self.estado = EstadoCatequizando.GRADUADO
        
        logger.info(f"Catequizando {self.nombre_completo} graduado")
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario.
        
        Args:
            include_audit: Si incluir información de auditoría
            include_sensitive: Si incluir datos sensibles
            
        Returns:
            dict: Datos del modelo
        """
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['genero'] = self.genero.value
        data['estado'] = self.estado.value
        data['tipo_documento'] = self.tipo_documento.value
        data['estado_civil'] = self.estado_civil.value
        
        # Agregar edad calculada
        data['edad'] = self.edad
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'documento_identidad', 'telefono', 'telefono_alternativo',
                'email', 'direccion', 'telefono_padre', 'telefono_madre',
                'email_padre', 'email_madre'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_documento(cls, documento: str) -> Optional['Catequizando']:
        """Busca un catequizando por documento."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.catequizandos.buscar_catequizando_por_documento(documento)
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando catequizando por documento {documento}: {str(e)}")
            return None
    
    @classmethod
    def find_by_edad_rango(cls, edad_min: int, edad_max: int) -> List['Catequizando']:
        """Busca catequizandos por rango de edad."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'catequizandos',
                'buscar_por_edad',
                {
                    'edad_minima': edad_min,
                    'edad_maxima': edad_max
                }
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando catequizandos por edad: {str(e)}")
            return []
    
    @classmethod
    def find_activos(cls) -> List['Catequizando']:
        """Busca todos los catequizandos activos."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'catequizandos',
                'obtener_activos',
                {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando catequizandos activos: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Catequizando':
        """Guarda el catequizando con validaciones adicionales."""
        # Establecer fecha de ingreso si es nuevo
        if self.is_new and not self.fecha_ingreso:
            self.fecha_ingreso = date.today()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('catequizando', Catequizando)