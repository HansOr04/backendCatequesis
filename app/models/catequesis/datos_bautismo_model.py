"""
Modelo de Datos de Bautismo para el sistema de catequesis.
Maneja información específica y detallada del sacramento del bautismo.
"""

import logging
from datetime import date, datetime, time
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class TipoBautismo(Enum):
    """Tipos de bautismo."""
    INFANTE = "infante"
    ADULTO = "adulto"
    EMERGENCIA = "emergencia"
    CONDICIONAL = "condicional"


class RitoBautismo(Enum):
    """Ritos del bautismo."""
    ROMANO = "romano"
    BIZANTINO = "bizantino"
    ORIENTAL = "oriental"
    ESPECIAL = "especial"


class EstadoCertificado(Enum):
    """Estados del certificado de bautismo."""
    VIGENTE = "vigente"
    ANULADO = "anulado"
    REEMPLAZADO = "reemplazado"
    PERDIDO = "perdido"


class DatosBautismo(BaseModel):
    """
    Modelo de Datos de Bautismo del sistema de catequesis.
    Contiene información detallada específica del sacramento del bautismo.
    """
    
    # Configuración del modelo
    _table_schema = "datos_bautismo"
    _primary_key = "id_datos_bautismo"
    _required_fields = ["id_catequizando", "fecha_bautismo", "lugar_bautismo"]
    _unique_fields = ["numero_partida"]
    _searchable_fields = [
        "numero_partida", "lugar_bautismo", "ministro", 
        "padrino", "madrina", "libro_bautismos"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Datos de Bautismo."""
        # Identificación básica
        self.id_datos_bautismo: Optional[int] = None
        self.id_catequizando: int = 0
        self.id_sacramento: Optional[int] = None  # Referencia al sacramento general
        
        # Información básica del bautismo
        self.fecha_bautismo: Optional[date] = None
        self.hora_bautismo: Optional[time] = None
        self.lugar_bautismo: str = ""
        self.parroquia_bautismo: Optional[str] = None
        self.ciudad_bautismo: Optional[str] = None
        self.diocesis_bautismo: Optional[str] = None
        self.pais_bautismo: str = "Colombia"
        
        # Tipo y rito del bautismo
        self.tipo_bautismo: TipoBautismo = TipoBautismo.INFANTE
        self.rito_bautismo: RitoBautismo = RitoBautismo.ROMANO
        self.es_bautismo_emergencia: bool = False
        self.motivo_emergencia: Optional[str] = None
        
        # Ministro celebrante
        self.ministro: Optional[str] = None
        self.titulo_ministro: str = "Padre"  # Padre, Obispo, Diácono
        self.diocesis_ministro: Optional[str] = None
        self.ministro_suplente: Optional[str] = None
        
        # Padrinos
        self.padrino: Optional[str] = None
        self.madrina: Optional[str] = None
        self.id_padrino: Optional[int] = None
        self.id_madrina: Optional[int] = None
        self.direccion_padrino: Optional[str] = None
        self.direccion_madrina: Optional[str] = None
        self.telefono_padrino: Optional[str] = None
        self.telefono_madrina: Optional[str] = None
        
        # Información de los padres
        self.nombre_padre: Optional[str] = None
        self.apellidos_padre: Optional[str] = None
        self.documento_padre: Optional[str] = None
        self.lugar_nacimiento_padre: Optional[str] = None
        self.fecha_nacimiento_padre: Optional[date] = None
        self.ocupacion_padre: Optional[str] = None
        self.religion_padre: str = "Católica"
        
        self.nombre_madre: Optional[str] = None
        self.apellidos_madre: Optional[str] = None
        self.documento_madre: Optional[str] = None
        self.lugar_nacimiento_madre: Optional[str] = None
        self.fecha_nacimiento_madre: Optional[date] = None
        self.ocupacion_madre: Optional[str] = None
        self.religion_madre: str = "Católica"
        
        # Datos del matrimonio de los padres
        self.padres_casados_iglesia: bool = False
        self.fecha_matrimonio_padres: Optional[date] = None
        self.lugar_matrimonio_padres: Optional[str] = None
        self.numero_acta_matrimonio: Optional[str] = None
        
        # Abuelos paternos
        self.abuelo_paterno: Optional[str] = None
        self.abuela_paterna: Optional[str] = None
        self.lugar_nacimiento_abuelo_paterno: Optional[str] = None
        self.lugar_nacimiento_abuela_paterna: Optional[str] = None
        
        # Abuelos maternos
        self.abuelo_materno: Optional[str] = None
        self.abuela_materna: Optional[str] = None
        self.lugar_nacimiento_abuelo_materno: Optional[str] = None
        self.lugar_nacimiento_abuela_materna: Optional[str] = None
        
        # Registro civil y eclesiástico
        self.numero_partida: Optional[str] = None
        self.libro_bautismos: Optional[str] = None
        self.folio: Optional[str] = None
        self.pagina: Optional[str] = None
        self.tomo: Optional[str] = None
        self.fecha_registro: Optional[date] = None
        self.registrado_por: Optional[str] = None
        
        # Certificación
        self.numero_certificado: Optional[str] = None
        self.fecha_expedicion_certificado: Optional[date] = None
        self.expedido_por: Optional[str] = None
        self.estado_certificado: EstadoCertificado = EstadoCertificado.VIGENTE
        self.motivo_anulacion: Optional[str] = None
        
        # Información adicional del bautizado
        self.edad_al_bautismo: Optional[str] = None  # "3 meses", "2 años", etc.
        self.peso_al_nacer: Optional[str] = None
        self.lugar_nacimiento_bautizado: Optional[str] = None
        self.hora_nacimiento: Optional[time] = None
        self.nombre_hospital: Optional[str] = None
        
        # Detalles de la ceremonia
        self.numero_bautizados_ceremonia: int = 1
        self.nombres_otros_bautizados: Optional[str] = None
        self.vestimenta_especial: Optional[str] = None
        self.objeto_religioso_entregado: Optional[str] = None
        self.canticos_especiales: Optional[str] = None
        
        # Documentos presentados
        self.registro_civil_presentado: bool = False
        self.numero_registro_civil: Optional[str] = None
        self.certificado_medico: bool = False
        self.constancia_catequesis_padres: bool = False
        self.constancia_catequesis_padrinos: bool = False
        
        # Observaciones y notas especiales
        self.circunstancias_especiales: Optional[str] = None
        self.observaciones_liturgicas: Optional[str] = None
        self.observaciones_administrativas: Optional[str] = None
        self.notas_historicas: Optional[str] = None
        
        # Control de correcciones
        self.requiere_correccion: bool = False
        self.correcciones_realizadas: List[Dict[str, Any]] = []
        self.validado_por: Optional[str] = None
        self.fecha_validacion: Optional[date] = None
        
        super().__init__(**kwargs)
    
    @property
    def nombre_completo_padre(self) -> str:
        """Obtiene el nombre completo del padre."""
        if self.nombre_padre and self.apellidos_padre:
            return f"{self.nombre_padre} {self.apellidos_padre}"
        return self.nombre_padre or ""
    
    @property
    def nombre_completo_madre(self) -> str:
        """Obtiene el nombre completo de la madre."""
        if self.nombre_madre and self.apellidos_madre:
            return f"{self.nombre_madre} {self.apellidos_madre}"
        return self.nombre_madre or ""
    
    @property
    def padrinos_completos(self) -> str:
        """Obtiene la información completa de padrinos."""
        padrinos = []
        if self.padrino:
            padrinos.append(f"Padrino: {self.padrino}")
        if self.madrina:
            padrinos.append(f"Madrina: {self.madrina}")
        return " | ".join(padrinos) if padrinos else "Sin padrinos registrados"
    
    @property
    def referencia_completa(self) -> str:
        """Obtiene la referencia completa del registro."""
        partes = []
        if self.numero_partida:
            partes.append(f"Partida: {self.numero_partida}")
        if self.libro_bautismos:
            partes.append(f"Libro: {self.libro_bautismos}")
        if self.folio:
            partes.append(f"Folio: {self.folio}")
        if self.pagina:
            partes.append(f"Página: {self.pagina}")
        
    @property
    def referencia_completa(self) -> str:
        """Obtiene la referencia completa del registro."""
        partes = []
        if self.numero_partida:
            partes.append(f"Partida: {self.numero_partida}")
        if self.libro_bautismos:
            partes.append(f"Libro: {self.libro_bautismos}")
        if self.folio:
            partes.append(f"Folio: {self.folio}")
        if self.pagina:
            partes.append(f"Página: {self.pagina}")
        
        return " - ".join(partes) if partes else "Sin referencia"
    
    @property
    def lugar_completo(self) -> str:
        """Obtiene la descripción completa del lugar."""
        partes = [self.lugar_bautismo]
        if self.parroquia_bautismo:
            partes.append(f"Parroquia {self.parroquia_bautismo}")
        if self.ciudad_bautismo:
            partes.append(self.ciudad_bautismo)
        if self.diocesis_bautismo:
            partes.append(f"Diócesis de {self.diocesis_bautismo}")
        
        return ", ".join(filter(None, partes))
    
    @property
    def descripcion_tipo_bautismo(self) -> str:
        """Obtiene la descripción del tipo de bautismo."""
        descripciones = {
            TipoBautismo.INFANTE: "Bautismo de Infante",
            TipoBautismo.ADULTO: "Bautismo de Adulto",
            TipoBautismo.EMERGENCIA: "Bautismo de Emergencia",
            TipoBautismo.CONDICIONAL: "Bautismo Condicional"
        }
        return descripciones.get(self.tipo_bautismo, "Bautismo")
    
    @property
    def certificado_vigente(self) -> bool:
        """Verifica si el certificado está vigente."""
        return self.estado_certificado == EstadoCertificado.VIGENTE
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Datos de Bautismo."""
        # Validar ID del catequizando
        if self.id_catequizando <= 0:
            raise ValidationError("Debe especificar un catequizando válido")
        
        # Validar fecha de bautismo
        if self.fecha_bautismo:
            if self.fecha_bautismo > date.today():
                raise ValidationError("La fecha de bautismo no puede ser futura")
            
            # Validar que no sea muy antigua
            if self.fecha_bautismo.year < 1800:
                raise ValidationError("La fecha de bautismo es muy antigua")
        
        # Validar lugar de bautismo
        if self.lugar_bautismo and len(self.lugar_bautismo.strip()) < 3:
            raise ValidationError("El lugar de bautismo debe tener al menos 3 caracteres")
        
        # Validar documentos de identidad de los padres
        if self.documento_padre and not DataValidator.validate_cedula(self.documento_padre):
            raise ValidationError("El documento del padre no es válido")
        
        if self.documento_madre and not DataValidator.validate_cedula(self.documento_madre):
            raise ValidationError("El documento de la madre no es válido")
        
        # Validar teléfonos de padrinos
        if self.telefono_padrino and not DataValidator.validate_phone(self.telefono_padrino):
            raise ValidationError("El teléfono del padrino no es válido")
        
        if self.telefono_madrina and not DataValidator.validate_phone(self.telefono_madrina):
            raise ValidationError("El teléfono de la madrina no es válido")
        
        # Validar fechas de nacimiento de los padres
        if self.fecha_nacimiento_padre and self.fecha_nacimiento_padre > date.today():
            raise ValidationError("La fecha de nacimiento del padre no puede ser futura")
        
        if self.fecha_nacimiento_madre and self.fecha_nacimiento_madre > date.today():
            raise ValidationError("La fecha de nacimiento de la madre no puede ser futura")
        
        # Validar fecha de matrimonio de los padres
        if self.fecha_matrimonio_padres:
            if self.fecha_matrimonio_padres > date.today():
                raise ValidationError("La fecha de matrimonio de los padres no puede ser futura")
            
            if self.fecha_bautismo and self.fecha_matrimonio_padres > self.fecha_bautismo:
                raise ValidationError("El matrimonio de los padres no puede ser posterior al bautismo")
        
        # Validar número de bautizados en ceremonia
        if self.numero_bautizados_ceremonia < 1 or self.numero_bautizados_ceremonia > 50:
            raise ValidationError("El número de bautizados debe estar entre 1 y 50")
        
        # Validar enums
        if isinstance(self.tipo_bautismo, str):
            try:
                self.tipo_bautismo = TipoBautismo(self.tipo_bautismo)
            except ValueError:
                raise ValidationError(f"Tipo de bautismo '{self.tipo_bautismo}' no válido")
        
        if isinstance(self.rito_bautismo, str):
            try:
                self.rito_bautismo = RitoBautismo(self.rito_bautismo)
            except ValueError:
                raise ValidationError(f"Rito de bautismo '{self.rito_bautismo}' no válido")
        
        if isinstance(self.estado_certificado, str):
            try:
                self.estado_certificado = EstadoCertificado(self.estado_certificado)
            except ValueError:
                raise ValidationError(f"Estado de certificado '{self.estado_certificado}' no válido")
        
        # Validar bautismo de emergencia
        if self.es_bautismo_emergencia and not self.motivo_emergencia:
            raise ValidationError("Los bautismos de emergencia requieren especificar el motivo")
        
        # Validar que tenga al menos un padrino para bautismos normales
        if (self.tipo_bautismo != TipoBautismo.EMERGENCIA and 
            not self.padrino and not self.madrina):
            raise ValidationError("Se requiere al menos un padrino o madrina")
    
    def obtener_catequizando(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información del catequizando.
        
        Returns:
            dict: Información del catequizando o None
        """
        try:
            result = self._sp_manager.catequizandos.obtener_catequizando(self.id_catequizando)
            
            if result.get('success') and result.get('data'):
                return result['data']
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo catequizando: {str(e)}")
            return None
    
    def generar_numero_partida(self) -> str:
        """
        Genera un número de partida único.
        
        Returns:
            str: Número de partida generado
        """
        if not self.fecha_bautismo:
            raise ValidationError("Se requiere fecha de bautismo para generar número de partida")
        
        try:
            año = self.fecha_bautismo.year
            
            # Obtener siguiente número secuencial del año
            result = self._sp_manager.executor.execute(
                'datos_bautismo',
                'obtener_siguiente_numero_partida',
                {'año': año}
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            # Formato: BAU-AAAA-NNNN
            numero_partida = f"BAU-{año}-{numero:04d}"
            self.numero_partida = numero_partida
            
            return numero_partida
            
        except Exception as e:
            logger.error(f"Error generando número de partida: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            return f"BAU-{timestamp}"
    
    def generar_certificado_bautismo(self) -> Dict[str, Any]:
        """
        Genera un certificado de bautismo.
        
        Returns:
            dict: Información del certificado generado
        """
        try:
            # Obtener información del catequizando
            catequizando = self.obtener_catequizando()
            if not catequizando:
                raise ValidationError("No se pudo obtener información del catequizando")
            
            # Generar número de certificado si no existe
            if not self.numero_certificado:
                self.numero_certificado = self._generar_numero_certificado()
            
            # Datos para el certificado
            datos_certificado = {
                'numero_certificado': self.numero_certificado,
                'catequizando': {
                    'nombre_completo': catequizando.get('nombre_completo', ''),
                    'fecha_nacimiento': catequizando.get('fecha_nacimiento', ''),
                    'lugar_nacimiento': self.lugar_nacimiento_bautizado or catequizando.get('lugar_nacimiento', '')
                },
                'bautismo': {
                    'fecha': self.fecha_bautismo.strftime("%d de %B de %Y") if self.fecha_bautismo else '',
                    'hora': self.hora_bautismo.strftime("%H:%M") if self.hora_bautismo else '',
                    'lugar': self.lugar_completo,
                    'ministro': self.ministro,
                    'tipo': self.descripcion_tipo_bautismo
                },
                'padres': {
                    'padre': self.nombre_completo_padre,
                    'madre': self.nombre_completo_madre,
                    'casados_iglesia': self.padres_casados_iglesia
                },
                'padrinos': {
                    'padrino': self.padrino,
                    'madrina': self.madrina
                },
                'abuelos': {
                    'paternos': {
                        'abuelo': self.abuelo_paterno,
                        'abuela': self.abuela_paterna
                    },
                    'maternos': {
                        'abuelo': self.abuelo_materno,
                        'abuela': self.abuela_materna
                    }
                },
                'registro': {
                    'numero_partida': self.numero_partida,
                    'libro': self.libro_bautismos,
                    'folio': self.folio,
                    'pagina': self.pagina
                },
                'expedicion': {
                    'fecha': date.today().strftime("%d de %B de %Y"),
                    'expedido_por': self.expedido_por or "Secretario Parroquial"
                }
            }
            
            # Marcar certificado como expedido
            self.fecha_expedicion_certificado = date.today()
            self.estado_certificado = EstadoCertificado.VIGENTE
            
            return {
                'success': True,
                'datos_certificado': datos_certificado,
                'numero_certificado': self.numero_certificado
            }
            
        except Exception as e:
            logger.error(f"Error generando certificado de bautismo: {str(e)}")
            return {
                'success': False,
                'message': f"Error generando certificado: {str(e)}"
            }
    
    def _generar_numero_certificado(self) -> str:
        """Genera un número de certificado único."""
        try:
            año_actual = date.today().year
            
            result = self._sp_manager.executor.execute(
                'datos_bautismo',
                'obtener_siguiente_numero_certificado',
                {'año': año_actual}
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            return f"CERT-BAU-{año_actual}-{numero:06d}"
            
        except Exception as e:
            logger.error(f"Error generando número de certificado: {str(e)}")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"CERT-BAU-{timestamp}"
    
    def registrar_correccion(
        self,
        campo_corregido: str,
        valor_anterior: str,
        valor_nuevo: str,
        motivo: str,
        autorizado_por: str
    ) -> None:
        """
        Registra una corrección en los datos del bautismo.
        
        Args:
            campo_corregido: Campo que se corrigió
            valor_anterior: Valor anterior
            valor_nuevo: Valor nuevo
            motivo: Motivo de la corrección
            autorizado_por: Usuario que autoriza la corrección
        """
        correccion = {
            'fecha': datetime.now().isoformat(),
            'campo': campo_corregido,
            'valor_anterior': valor_anterior,
            'valor_nuevo': valor_nuevo,
            'motivo': motivo,
            'autorizado_por': autorizado_por
        }
        
        self.correcciones_realizadas.append(correccion)
        self.requiere_correccion = False
        
        logger.info(f"Corrección registrada en {campo_corregido} para bautismo {self.numero_partida}")
    
    def anular_certificado(self, motivo: str, usuario: str) -> None:
        """
        Anula el certificado de bautismo.
        
        Args:
            motivo: Motivo de la anulación
            usuario: Usuario que anula
        """
        self.estado_certificado = EstadoCertificado.ANULADO
        self.motivo_anulacion = motivo
        
        # Registrar corrección
        self.registrar_correccion(
            'estado_certificado',
            'vigente',
            'anulado',
            motivo,
            usuario
        )
        
        logger.info(f"Certificado de bautismo anulado: {motivo}")
    
    def reemplazar_certificado(self, motivo: str, usuario: str) -> str:
        """
        Reemplaza el certificado de bautismo.
        
        Args:
            motivo: Motivo del reemplazo
            usuario: Usuario que reemplaza
            
        Returns:
            str: Nuevo número de certificado
        """
        # Marcar el actual como reemplazado
        self.estado_certificado = EstadoCertificado.REEMPLAZADO
        
        # Generar nuevo número
        nuevo_numero = self._generar_numero_certificado()
        numero_anterior = self.numero_certificado
        
        self.numero_certificado = nuevo_numero
        self.fecha_expedicion_certificado = date.today()
        self.estado_certificado = EstadoCertificado.VIGENTE
        
        # Registrar corrección
        self.registrar_correccion(
            'numero_certificado',
            numero_anterior or '',
            nuevo_numero,
            f"Reemplazo: {motivo}",
            usuario
        )
        
        logger.info(f"Certificado de bautismo reemplazado: {numero_anterior} -> {nuevo_numero}")
        return nuevo_numero
    
    def validar_datos(self, validador: str) -> None:
        """
        Valida los datos del bautismo.
        
        Args:
            validador: Usuario que valida
        """
        self.validado_por = validador
        self.fecha_validacion = date.today()
        self.requiere_correccion = False
        
        logger.info(f"Datos de bautismo validados por {validador}")
    
    def verificar_completitud_datos(self) -> Dict[str, Any]:
        """
        Verifica la completitud de los datos del bautismo.
        
        Returns:
            dict: Resultado de la verificación
        """
        campos_requeridos = {
            'fecha_bautismo': 'Fecha de bautismo',
            'lugar_bautismo': 'Lugar de bautismo',
            'ministro': 'Ministro celebrante',
            'nombre_padre': 'Nombre del padre',
            'nombre_madre': 'Nombre de la madre'
        }
        
        campos_faltantes = []
        campos_completos = []
        
        for campo, descripcion in campos_requeridos.items():
            valor = getattr(self, campo, None)
            if not valor:
                campos_faltantes.append(descripcion)
            else:
                campos_completos.append(descripcion)
        
        # Verificar padrinos
        if not self.padrino and not self.madrina:
            campos_faltantes.append('Al menos un padrino o madrina')
        else:
            campos_completos.append('Padrinos')
        
        porcentaje_completitud = (len(campos_completos) / (len(campos_completos) + len(campos_faltantes))) * 100
        
        return {
            'completo': len(campos_faltantes) == 0,
            'porcentaje_completitud': round(porcentaje_completitud, 2),
            'campos_completos': campos_completos,
            'campos_faltantes': campos_faltantes,
            'total_campos': len(campos_requeridos) + 1  # +1 por padrinos
        }
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_bautismo'] = self.tipo_bautismo.value
        data['rito_bautismo'] = self.rito_bautismo.value
        data['estado_certificado'] = self.estado_certificado.value
        
        # Convertir time a string
        if self.hora_bautismo:
            data['hora_bautismo'] = self.hora_bautismo.strftime('%H:%M')
        if self.hora_nacimiento:
            data['hora_nacimiento'] = self.hora_nacimiento.strftime('%H:%M')
        
        # Agregar propiedades calculadas
        data['nombre_completo_padre'] = self.nombre_completo_padre
        data['nombre_completo_madre'] = self.nombre_completo_madre
        data['padrinos_completos'] = self.padrinos_completos
        data['referencia_completa'] = self.referencia_completa
        data['lugar_completo'] = self.lugar_completo
        data['descripcion_tipo_bautismo'] = self.descripcion_tipo_bautismo
        data['certificado_vigente'] = self.certificado_vigente
        
        # Agregar verificación de completitud
        data['verificacion_completitud'] = self.verificar_completitud_datos()
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'documento_padre', 'documento_madre', 'telefono_padrino', 
                'telefono_madrina', 'numero_certificado'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_numero_partida(cls, numero_partida: str) -> Optional['DatosBautismo']:
        """Busca datos de bautismo por número de partida."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'datos_bautismo',
                'obtener_por_numero_partida',
                {'numero_partida': numero_partida}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando por número de partida {numero_partida}: {str(e)}")
            return None
    
    @classmethod
    def find_by_catequizando(cls, id_catequizando: int) -> Optional['DatosBautismo']:
        """Busca datos de bautismo por catequizando."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'datos_bautismo',
                'obtener_por_catequizando',
                {'id_catequizando': id_catequizando}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando por catequizando {id_catequizando}: {str(e)}")
            return None
    
    @classmethod
    def find_by_fecha_rango(cls, fecha_inicio: date, fecha_fin: date) -> List['DatosBautismo']:
        """Busca bautismos por rango de fechas."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'datos_bautismo',
                'obtener_por_fecha_rango',
                {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando por rango de fechas: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'DatosBautismo':
        """Guarda los datos de bautismo con validaciones adicionales."""
        # Generar número de partida si no existe
        if not self.numero_partida and self.fecha_bautismo:
            self.generar_numero_partida()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('datos_bautismo', DatosBautismo)