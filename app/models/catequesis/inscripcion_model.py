"""
Modelo de Inscripción para el sistema de catequesis.
Maneja las inscripciones de catequizandos en grupos de catequesis.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError
from app.utils.validators import DataValidator

logger = logging.getLogger(__name__)


class EstadoInscripcion(Enum):
    """Estados de la inscripción."""
    ACTIVA = "activa"
    INACTIVA = "inactiva"
    SUSPENDIDA = "suspendida"
    CANCELADA = "cancelada"
    TRANSFERIDA = "transferida"
    GRADUADA = "graduada"
    RETIRADA = "retirada"


class TipoPago(Enum):
    """Tipos de pago."""
    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    TARJETA = "tarjeta"
    CHEQUE = "cheque"
    EXENTO = "exento"
    BECA = "beca"


class EstadoPago(Enum):
    """Estados del pago."""
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    PAGO_PARCIAL = "pago_parcial"
    VENCIDO = "vencido"
    EXENTO = "exento"


class TipoDescuento(Enum):
    """Tipos de descuento."""
    HERMANOS = "hermanos"
    EMPLEADO = "empleado"
    SITUACION_ECONOMICA = "situacion_economica"
    BECADO = "becado"
    ESPECIAL = "especial"


class Inscripcion(BaseModel):
    """
    Modelo de Inscripción del sistema de catequesis.
    Gestiona las inscripciones de catequizandos en grupos.
    """
    
    # Configuración del modelo
    _table_schema = "inscripciones"
    _primary_key = "id_inscripcion"
    _required_fields = ["id_catequizando", "id_grupo", "id_parroquia"]
    _unique_fields = []
    _searchable_fields = [
        "codigo_inscripcion", "numero_recibo", 
        "nombre_catequizando", "nombre_grupo"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Inscripción."""
        # Identificación básica
        self.id_inscripcion: Optional[int] = None
        self.codigo_inscripcion: Optional[str] = None
        self.numero_recibo: Optional[str] = None
        
        # Relaciones principales
        self.id_catequizando: int = 0
        self.id_grupo: int = 0
        self.id_parroquia: int = 0
        self.id_nivel: Optional[int] = None
        
        # Fechas importantes
        self.fecha_inscripcion: date = date.today()
        self.fecha_inicio_catequesis: Optional[date] = None
        self.fecha_fin_estimada: Optional[date] = None
        self.fecha_fin_real: Optional[date] = None
        self.fecha_graduacion: Optional[date] = None
        
        # Estado de la inscripción
        self.estado: EstadoInscripcion = EstadoInscripcion.ACTIVA
        self.motivo_cambio_estado: Optional[str] = None
        self.fecha_cambio_estado: Optional[date] = None
        self.usuario_cambio_estado: Optional[str] = None
        
        # Información de pagos
        self.requiere_pago: bool = True
        self.monto_inscripcion: float = 0.0
        self.monto_materiales: float = 0.0
        self.monto_total: float = 0.0
        self.monto_pagado: float = 0.0
        self.monto_pendiente: float = 0.0
        self.estado_pago: EstadoPago = EstadoPago.PENDIENTE
        
        # Descuentos
        self.tiene_descuento: bool = False
        self.tipo_descuento: Optional[TipoDescuento] = None
        self.porcentaje_descuento: float = 0.0
        self.monto_descuento: float = 0.0
        self.motivo_descuento: Optional[str] = None
        self.autorizado_por: Optional[str] = None
        
        # Información de pago
        self.fecha_limite_pago: Optional[date] = None
        self.fecha_ultimo_pago: Optional[date] = None
        self.tipo_pago: Optional[TipoPago] = None
        self.referencia_pago: Optional[str] = None
        self.comprobante_pago: Optional[str] = None
        
        # Control académico
        self.puede_presentar_sacramento: bool = False
        self.cumple_requisitos_asistencia: bool = False
        self.cumple_requisitos_calificaciones: bool = False
        self.porcentaje_asistencia: float = 0.0
        self.promedio_calificaciones: float = 0.0
        
        # Información adicional
        self.es_repitente: bool = False
        self.año_anterior: Optional[int] = None
        self.grupo_anterior: Optional[str] = None
        self.observaciones_especiales: Optional[str] = None
        
        # Control administrativo
        self.documentos_entregados: List[str] = []
        self.documentos_pendientes: List[str] = []
        self.requiere_documentos_adicionales: bool = False
        
        # Observaciones y notas
        self.observaciones: Optional[str] = None
        self.notas_administrativas: Optional[str] = None
        self.historial_cambios: List[Dict[str, Any]] = []
        
        super().__init__(**kwargs)
    
    @property
    def esta_activa(self) -> bool:
        """Verifica si la inscripción está activa."""
        return self.estado == EstadoInscripcion.ACTIVA
    
    @property
    def esta_al_dia_pagos(self) -> bool:
        """Verifica si está al día con los pagos."""
        return self.estado_pago in [EstadoPago.PAGADO, EstadoPago.EXENTO]
    
    @property
    def tiene_pagos_pendientes(self) -> bool:
        """Verifica si tiene pagos pendientes."""
        return self.monto_pendiente > 0 and self.estado_pago != EstadoPago.EXENTO
    
    @property
    def pago_vencido(self) -> bool:
        """Verifica si el pago está vencido."""
        if not self.fecha_limite_pago or self.esta_al_dia_pagos:
            return False
        
        return date.today() > self.fecha_limite_pago
    
    @property
    def puede_graduarse(self) -> bool:
        """Verifica si puede graduarse."""
        return (self.esta_activa and 
                self.puede_presentar_sacramento and
                self.cumple_requisitos_asistencia and
                self.cumple_requisitos_calificaciones and
                self.esta_al_dia_pagos)
    
    @property
    def tiempo_inscrito_dias(self) -> int:
        """Calcula días desde la inscripción."""
        return (date.today() - self.fecha_inscripcion).days
    
    @property
    def descripcion_estado(self) -> str:
        """Obtiene la descripción del estado."""
        descripciones = {
            EstadoInscripcion.ACTIVA: "Activa",
            EstadoInscripcion.INACTIVA: "Inactiva",
            EstadoInscripcion.SUSPENDIDA: "Suspendida",
            EstadoInscripcion.CANCELADA: "Cancelada",
            EstadoInscripcion.TRANSFERIDA: "Transferida",
            EstadoInscripcion.GRADUADA: "Graduada",
            EstadoInscripcion.RETIRADA: "Retirada"
        }
        return descripciones.get(self.estado, "Estado desconocido")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Inscripción."""
        # Validar IDs requeridos
        if self.id_catequizando <= 0:
            raise ValidationError("Debe especificar un catequizando válido")
        
        if self.id_grupo <= 0:
            raise ValidationError("Debe especificar un grupo válido")
        
        if self.id_parroquia <= 0:
            raise ValidationError("Debe especificar una parroquia válida")
        
        # Validar fechas
        if self.fecha_inicio_catequesis and self.fecha_inscripcion:
            if self.fecha_inicio_catequesis < self.fecha_inscripcion:
                raise ValidationError("La fecha de inicio no puede ser anterior a la inscripción")
        
        if self.fecha_fin_estimada and self.fecha_inicio_catequesis:
            if self.fecha_fin_estimada <= self.fecha_inicio_catequesis:
                raise ValidationError("La fecha de fin debe ser posterior al inicio")
        
        if self.fecha_graduacion and self.fecha_inicio_catequesis:
            if self.fecha_graduacion < self.fecha_inicio_catequesis:
                raise ValidationError("La fecha de graduación no puede ser anterior al inicio")
        
        # Validar montos
        if self.monto_inscripcion < 0:
            raise ValidationError("El monto de inscripción no puede ser negativo")
        
        if self.monto_materiales < 0:
            raise ValidationError("El monto de materiales no puede ser negativo")
        
        if self.monto_pagado < 0:
            raise ValidationError("El monto pagado no puede ser negativo")
        
        if self.monto_pagado > self.monto_total:
            raise ValidationError("El monto pagado no puede ser mayor al total")
        
        # Validar porcentajes
        if self.porcentaje_descuento < 0 or self.porcentaje_descuento > 100:
            raise ValidationError("El porcentaje de descuento debe estar entre 0 y 100")
        
        if self.porcentaje_asistencia < 0 or self.porcentaje_asistencia > 100:
            raise ValidationError("El porcentaje de asistencia debe estar entre 0 y 100")
        
        if self.promedio_calificaciones < 0 or self.promedio_calificaciones > 10:
            raise ValidationError("El promedio de calificaciones debe estar entre 0 y 10")
        
        # Validar enums
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoInscripcion(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.estado_pago, str):
            try:
                self.estado_pago = EstadoPago(self.estado_pago)
            except ValueError:
                raise ValidationError(f"Estado de pago '{self.estado_pago}' no válido")
        
        if isinstance(self.tipo_pago, str) and self.tipo_pago:
            try:
                self.tipo_pago = TipoPago(self.tipo_pago)
            except ValueError:
                raise ValidationError(f"Tipo de pago '{self.tipo_pago}' no válido")
        
        if isinstance(self.tipo_descuento, str) and self.tipo_descuento:
            try:
                self.tipo_descuento = TipoDescuento(self.tipo_descuento)
            except ValueError:
                raise ValidationError(f"Tipo de descuento '{self.tipo_descuento}' no válido")
        
        # Validar coherencia de descuentos
        if self.tiene_descuento:
            if not self.tipo_descuento:
                raise ValidationError("Si tiene descuento, debe especificar el tipo")
            if self.porcentaje_descuento <= 0:
                raise ValidationError("El porcentaje de descuento debe ser mayor a 0")
    
    def generar_codigo_inscripcion(self) -> str:
        """
        Genera un código único para la inscripción.
        
        Returns:
            str: Código generado
        """
        try:
            año = self.fecha_inscripcion.year
            mes = self.fecha_inscripcion.month
            
            # Formato: INS-AAAA-MM-NNNN
            result = self._sp_manager.executor.execute(
                'inscripciones',
                'obtener_siguiente_numero',
                {
                    'año': año,
                    'mes': mes,
                    'id_parroquia': self.id_parroquia
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            codigo = f"INS-{año}-{mes:02d}-{numero:04d}"
            self.codigo_inscripcion = codigo
            
            return codigo
            
        except Exception as e:
            logger.error(f"Error generando código de inscripción: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            return f"INS-{timestamp}"
    
    def calcular_montos(self) -> None:
        """Calcula los montos de la inscripción."""
        # Calcular monto total antes de descuentos
        monto_base = self.monto_inscripcion + self.monto_materiales
        
        # Aplicar descuentos
        if self.tiene_descuento and self.porcentaje_descuento > 0:
            self.monto_descuento = (monto_base * self.porcentaje_descuento) / 100
        else:
            self.monto_descuento = 0.0
        
        # Calcular monto total final
        self.monto_total = monto_base - self.monto_descuento
        
        # Calcular monto pendiente
        self.monto_pendiente = max(0, self.monto_total - self.monto_pagado)
        
        # Actualizar estado de pago
        if self.requiere_pago:
            if self.monto_pendiente <= 0:
                self.estado_pago = EstadoPago.PAGADO
            elif self.monto_pagado > 0:
                self.estado_pago = EstadoPago.PAGO_PARCIAL
            else:
                self.estado_pago = EstadoPago.PENDIENTE
        else:
            self.estado_pago = EstadoPago.EXENTO
    
    def aplicar_descuento(
        self,
        tipo_descuento: TipoDescuento,
        porcentaje: float,
        motivo: str,
        autorizado_por: str
    ) -> None:
        """
        Aplica un descuento a la inscripción.
        
        Args:
            tipo_descuento: Tipo de descuento
            porcentaje: Porcentaje de descuento
            motivo: Motivo del descuento
            autorizado_por: Usuario que autoriza
        """
        if porcentaje < 0 or porcentaje > 100:
            raise ValidationError("El porcentaje debe estar entre 0 y 100")
        
        self.tiene_descuento = True
        self.tipo_descuento = tipo_descuento
        self.porcentaje_descuento = porcentaje
        self.motivo_descuento = motivo
        self.autorizado_por = autorizado_por
        
        # Recalcular montos
        self.calcular_montos()
        
        # Registrar cambio
        self._registrar_cambio(
            f"Descuento aplicado: {porcentaje}% ({tipo_descuento.value})",
            autorizado_por
        )
        
        logger.info(f"Descuento de {porcentaje}% aplicado a inscripción {self.codigo_inscripcion}")
    
    def registrar_pago(
        self,
        monto: float,
        tipo_pago: TipoPago,
        referencia: str = None,
        comprobante: str = None,
        fecha_pago: date = None,
        usuario: str = None
    ) -> Dict[str, Any]:
        """
        Registra un pago para la inscripción.
        
        Args:
            monto: Monto del pago
            tipo_pago: Tipo de pago
            referencia: Referencia del pago
            comprobante: Número de comprobante
            fecha_pago: Fecha del pago
            usuario: Usuario que registra
            
        Returns:
            dict: Resultado del registro
        """
        try:
            if monto <= 0:
                raise ValidationError("El monto debe ser mayor a 0")
            
            if monto > self.monto_pendiente:
                raise ValidationError("El monto no puede ser mayor al pendiente")
            
            # Registrar el pago
            result = self._sp_manager.executor.execute(
                'inscripciones',
                'registrar_pago',
                {
                    'id_inscripcion': self.id_inscripcion,
                    'monto': monto,
                    'tipo_pago': tipo_pago.value,
                    'referencia_pago': referencia,
                    'comprobante_pago': comprobante,
                    'fecha_pago': fecha_pago or date.today(),
                    'usuario': usuario
                }
            )
            
            if result.get('success'):
                # Actualizar montos
                self.monto_pagado += monto
                self.fecha_ultimo_pago = fecha_pago or date.today()
                self.tipo_pago = tipo_pago
                self.referencia_pago = referencia
                self.comprobante_pago = comprobante
                
                # Recalcular estado
                self.calcular_montos()
                
                # Registrar cambio
                self._registrar_cambio(
                    f"Pago registrado: ${monto} ({tipo_pago.value})",
                    usuario
                )
                
                logger.info(f"Pago de ${monto} registrado para inscripción {self.codigo_inscripcion}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error registrando pago: {str(e)}")
            return {
                'success': False,
                'message': f"Error registrando pago: {str(e)}"
            }
    
    def cambiar_estado(
        self,
        nuevo_estado: EstadoInscripcion,
        motivo: str,
        usuario: str,
        fecha_cambio: date = None
    ) -> None:
        """
        Cambia el estado de la inscripción.
        
        Args:
            nuevo_estado: Nuevo estado
            motivo: Motivo del cambio
            usuario: Usuario que realiza el cambio
            fecha_cambio: Fecha del cambio
        """
        estado_anterior = self.estado
        
        self.estado = nuevo_estado
        self.motivo_cambio_estado = motivo
        self.fecha_cambio_estado = fecha_cambio or date.today()
        self.usuario_cambio_estado = usuario
        
        # Registrar en historial
        self._registrar_cambio(
            f"Estado cambiado de {estado_anterior.value} a {nuevo_estado.value}: {motivo}",
            usuario
        )
        
        logger.info(f"Estado de inscripción {self.codigo_inscripcion} cambiado a {nuevo_estado.value}")
    
    def transferir_grupo(
        self,
        nuevo_id_grupo: int,
        motivo: str,
        usuario: str
    ) -> Dict[str, Any]:
        """
        Transfiere la inscripción a otro grupo.
        
        Args:
            nuevo_id_grupo: ID del nuevo grupo
            motivo: Motivo de la transferencia
            usuario: Usuario que realiza la transferencia
            
        Returns:
            dict: Resultado de la transferencia
        """
        try:
            if nuevo_id_grupo == self.id_grupo:
                raise ValidationError("No puede transferir al mismo grupo")
            
            # Verificar disponibilidad del nuevo grupo
            result = self._sp_manager.grupos.obtener_grupo(nuevo_id_grupo)
            if not (result.get('success') and result.get('data')):
                raise ValidationError("El grupo destino no existe")
            
            grupo_destino = result['data']
            if not grupo_destino.get('tiene_cupos_disponibles', False):
                raise ValidationError("El grupo destino no tiene cupos disponibles")
            
            # Realizar transferencia
            grupo_anterior = self.id_grupo
            self.id_grupo = nuevo_id_grupo
            self.id_nivel = grupo_destino.get('id_nivel')
            
            # Cambiar estado temporalmente
            self.cambiar_estado(
                EstadoInscripcion.TRANSFERIDA,
                f"Transferido del grupo {grupo_anterior} al grupo {nuevo_id_grupo}: {motivo}",
                usuario
            )
            
            # Volver a estado activo
            self.cambiar_estado(
                EstadoInscripcion.ACTIVA,
                "Transferencia completada",
                usuario
            )
            
            return {
                'success': True,
                'message': 'Transferencia realizada exitosamente',
                'grupo_anterior': grupo_anterior,
                'grupo_nuevo': nuevo_id_grupo
            }
            
        except Exception as e:
            logger.error(f"Error en transferencia: {str(e)}")
            return {
                'success': False,
                'message': f"Error en transferencia: {str(e)}"
            }
    
    def graduar(self, fecha_graduacion: date = None, usuario: str = None) -> Dict[str, Any]:
        """
        Gradúa al catequizando.
        
        Args:
            fecha_graduacion: Fecha de graduación
            usuario: Usuario que registra la graduación
            
        Returns:
            dict: Resultado de la graduación
        """
        try:
            if not self.puede_graduarse:
                motivos = []
                if not self.cumple_requisitos_asistencia:
                    motivos.append("No cumple requisitos de asistencia")
                if not self.cumple_requisitos_calificaciones:
                    motivos.append("No cumple requisitos de calificaciones")
                if not self.esta_al_dia_pagos:
                    motivos.append("Tiene pagos pendientes")
                
                return {
                    'success': False,
                    'message': f"No puede graduarse: {', '.join(motivos)}"
                }
            
            # Registrar graduación
            self.fecha_graduacion = fecha_graduacion or date.today()
            self.cambiar_estado(
                EstadoInscripcion.GRADUADA,
                "Graduación completada",
                usuario
            )
            
            # Habilitar para sacramento
            self.puede_presentar_sacramento = True
            
            logger.info(f"Catequizando graduado en inscripción {self.codigo_inscripcion}")
            
            return {
                'success': True,
                'message': 'Graduación registrada exitosamente',
                'fecha_graduacion': self.fecha_graduacion
            }
            
        except Exception as e:
            logger.error(f"Error en graduación: {str(e)}")
            return {
                'success': False,
                'message': f"Error en graduación: {str(e)}"
            }
    
    def actualizar_requisitos_academicos(self) -> None:
        """Actualiza el cumplimiento de requisitos académicos."""
        try:
            # Obtener estadísticas de asistencia
            asistencias_result = self._sp_manager.asistencias.obtener_asistencias_por_catequizando(
                self.id_catequizando
            )
            
            if asistencias_result.get('success') and asistencias_result.get('data'):
                asistencias = asistencias_result['data']
                if asistencias:
                    total = len(asistencias)
                    presentes = len([a for a in asistencias if a.get('presente')])
                    self.porcentaje_asistencia = (presentes / total) * 100 if total > 0 else 0
            
            # Obtener calificaciones
            calificaciones_result = self._sp_manager.calificaciones.obtener_calificaciones_por_catequizando(
                self.id_catequizando,
                self.id_grupo
            )
            
            if calificaciones_result.get('success') and calificaciones_result.get('data'):
                calificaciones = calificaciones_result['data']
                if calificaciones:
                    notas = [c['calificacion'] for c in calificaciones if c.get('calificacion') is not None]
                    self.promedio_calificaciones = sum(notas) / len(notas) if notas else 0
            
            # Verificar cumplimiento de requisitos
            self.cumple_requisitos_asistencia = self.porcentaje_asistencia >= 80.0
            self.cumple_requisitos_calificaciones = self.promedio_calificaciones >= 7.0
            
        except Exception as e:
            logger.error(f"Error actualizando requisitos académicos: {str(e)}")
    
    def _registrar_cambio(self, descripcion: str, usuario: str) -> None:
        """Registra un cambio en el historial."""
        cambio = {
            'fecha': datetime.now().isoformat(),
            'descripcion': descripcion,
            'usuario': usuario
        }
        self.historial_cambios.append(cambio)
    
    def agregar_documento_entregado(self, documento: str) -> None:
        """Agrega un documento a la lista de entregados."""
        if documento not in self.documentos_entregados:
            self.documentos_entregados.append(documento)
        
        # Remover de pendientes si estaba
        if documento in self.documentos_pendientes:
            self.documentos_pendientes.remove(documento)
    
    def agregar_documento_pendiente(self, documento: str) -> None:
        """Agrega un documento a la lista de pendientes."""
        if documento not in self.documentos_pendientes:
            self.documentos_pendientes.append(documento)
        
        self.requiere_documentos_adicionales = True
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['estado'] = self.estado.value
        data['estado_pago'] = self.estado_pago.value
        if self.tipo_pago:
            data['tipo_pago'] = self.tipo_pago.value
        if self.tipo_descuento:
            data['tipo_descuento'] = self.tipo_descuento.value
        
        # Agregar propiedades calculadas
        data['descripcion_estado'] = self.descripcion_estado
        data['esta_al_dia_pagos'] = self.esta_al_dia_pagos
        data['tiene_pagos_pendientes'] = self.tiene_pagos_pendientes
        data['pago_vencido'] = self.pago_vencido
        data['puede_graduarse'] = self.puede_graduarse
        data['tiempo_inscrito_dias'] = self.tiempo_inscrito_dias
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'monto_inscripcion', 'monto_materiales', 'monto_total',
                'monto_pagado', 'monto_pendiente', 'referencia_pago',
                'comprobante_pago'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['Inscripcion']:
        """Busca una inscripción por código."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'inscripciones',
                'obtener_por_codigo',
                {'codigo_inscripcion': codigo}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando inscripción por código {codigo}: {str(e)}")
            return None
    
    @classmethod
    def find_by_catequizando(cls, id_catequizando: int) -> List['Inscripcion']:
        """Busca inscripciones de un catequizando."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.inscripciones.obtener_inscripciones_por_catequizando(id_catequizando)
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando inscripciones por catequizando: {str(e)}")
            return []
    
    @classmethod
    def find_by_grupo(cls, id_grupo: int) -> List['Inscripcion']:
        """Busca inscripciones de un grupo."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.inscripciones.obtener_inscripciones_por_grupo(id_grupo)
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando inscripciones por grupo: {str(e)}")
            return []
    
    @classmethod
    def find_con_pagos_vencidos(cls, id_parroquia: int = None) -> List['Inscripcion']:
        """Busca inscripciones con pagos vencidos."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'inscripciones',
                'obtener_pagos_vencidos',
                {'id_parroquia': id_parroquia} if id_parroquia else {}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando pagos vencidos: {str(e)}")
            return []

    def save(self, usuario: str = None) -> 'Inscripcion':
       """Guarda la inscripción con validaciones adicionales."""
       # Generar código si no existe
       if not self.codigo_inscripcion:
           self.generar_codigo_inscripcion()
       
       # Calcular montos antes de guardar
       self.calcular_montos()
       
       # Actualizar requisitos académicos si no es nueva
       if not self.is_new:
           self.actualizar_requisitos_academicos()
       
       return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('inscripcion', Inscripcion)


class InscripcionManager:
   """Manager para operaciones avanzadas con inscripciones."""
   
   @staticmethod
   def crear_inscripcion_completa(
       id_catequizando: int,
       id_grupo: int,
       id_parroquia: int,
       monto_inscripcion: float = 0.0,
       monto_materiales: float = 0.0,
       requiere_pago: bool = True,
       fecha_limite_pago: date = None,
       usuario_creador: str = None
   ) -> 'Inscripcion':
       """
       Crea una inscripción completa con validaciones.
       
       Args:
           id_catequizando: ID del catequizando
           id_grupo: ID del grupo
           id_parroquia: ID de la parroquia
           monto_inscripcion: Monto de inscripción
           monto_materiales: Monto de materiales
           requiere_pago: Si requiere pago
           fecha_limite_pago: Fecha límite de pago
           usuario_creador: Usuario que crea la inscripción
           
       Returns:
           Inscripcion: La inscripción creada
       """
       try:
           # Verificar que el catequizando no esté ya inscrito en el grupo
           inscripciones_existentes = Inscripcion.find_by_catequizando(id_catequizando)
           for inscripcion in inscripciones_existentes:
               if (inscripcion.id_grupo == id_grupo and 
                   inscripcion.estado == EstadoInscripcion.ACTIVA):
                   raise ValidationError("El catequizando ya está inscrito en este grupo")
           
           # Verificar disponibilidad del grupo
           sp_manager = get_sp_manager()
           grupo_result = sp_manager.grupos.obtener_grupo(id_grupo)
           
           if not (grupo_result.get('success') and grupo_result.get('data')):
               raise ValidationError("El grupo especificado no existe")
           
           grupo_data = grupo_result['data']
           if not grupo_data.get('tiene_cupos_disponibles', False):
               raise ValidationError("El grupo no tiene cupos disponibles")
           
           # Crear la inscripción
           inscripcion = Inscripcion(
               id_catequizando=id_catequizando,
               id_grupo=id_grupo,
               id_parroquia=id_parroquia,
               id_nivel=grupo_data.get('id_nivel'),
               monto_inscripcion=monto_inscripcion,
               monto_materiales=monto_materiales,
               requiere_pago=requiere_pago,
               fecha_limite_pago=fecha_limite_pago or (date.today() + timedelta(days=30))
           )
           
           # Verificar si es repitente
           if inscripciones_existentes:
               inscripcion.es_repitente = True
               ultima_inscripcion = max(
                   inscripciones_existentes, 
                   key=lambda x: x.fecha_inscripcion
               )
               inscripcion.año_anterior = ultima_inscripcion.fecha_inscripcion.year
               
               # Obtener información del grupo anterior
               grupo_anterior_result = sp_manager.grupos.obtener_grupo(ultima_inscripcion.id_grupo)
               if grupo_anterior_result.get('success') and grupo_anterior_result.get('data'):
                   inscripcion.grupo_anterior = grupo_anterior_result['data'].get('nombre')
           
           # Calcular montos
           inscripcion.calcular_montos()
           
           # Documentos requeridos por defecto
           inscripcion.documentos_pendientes = [
               "Fotocopia del documento de identidad",
               "Certificado de bautismo",
               "Foto 3x4"
           ]
           
           if inscripcion.es_repitente:
               inscripcion.documentos_pendientes.append("Certificado del año anterior")
           
           inscripcion.requiere_documentos_adicionales = True
           
           return inscripcion.save(usuario_creador)
           
       except Exception as e:
           logger.error(f"Error creando inscripción completa: {str(e)}")
           raise
   
   @staticmethod
   def procesar_inscripcion_masiva(
       inscripciones_data: List[Dict[str, Any]],
       usuario: str = None
   ) -> Dict[str, Any]:
       """
       Procesa múltiples inscripciones en lote.
       
       Args:
           inscripciones_data: Lista de datos de inscripciones
           usuario: Usuario que procesa
           
       Returns:
           dict: Resultado del procesamiento masivo
       """
       exitosas = []
       errores = []
       
       for i, data in enumerate(inscripciones_data):
           try:
               inscripcion = InscripcionManager.crear_inscripcion_completa(
                   **data,
                   usuario_creador=usuario
               )
               exitosas.append({
                   'fila': i + 1,
                   'inscripcion_id': inscripcion.id_inscripcion,
                   'codigo': inscripcion.codigo_inscripcion
               })
               
           except Exception as e:
               errores.append({
                   'fila': i + 1,
                   'error': str(e),
                   'datos': data
               })
       
       return {
           'total_procesadas': len(inscripciones_data),
           'exitosas': len(exitosas),
           'errores': len(errores),
           'inscripciones_exitosas': exitosas,
           'inscripciones_con_error': errores
       }
   
   @staticmethod
   def aplicar_descuento_masivo(
       inscripciones_ids: List[int],
       tipo_descuento: TipoDescuento,
       porcentaje: float,
       motivo: str,
       autorizado_por: str
   ) -> Dict[str, Any]:
       """
       Aplica descuentos masivos a múltiples inscripciones.
       
       Args:
           inscripciones_ids: Lista de IDs de inscripciones
           tipo_descuento: Tipo de descuento
           porcentaje: Porcentaje de descuento
           motivo: Motivo del descuento
           autorizado_por: Usuario que autoriza
           
       Returns:
           dict: Resultado del procesamiento
       """
       exitosas = []
       errores = []
       
       for id_inscripcion in inscripciones_ids:
           try:
               inscripcion = Inscripcion.find_by_id(id_inscripcion)
               if inscripcion:
                   inscripcion.aplicar_descuento(
                       tipo_descuento, porcentaje, motivo, autorizado_por
                   )
                   inscripcion.save(autorizado_por)
                   exitosas.append(id_inscripcion)
               else:
                   errores.append({
                       'id_inscripcion': id_inscripcion,
                       'error': 'Inscripción no encontrada'
                   })
                   
           except Exception as e:
               errores.append({
                   'id_inscripcion': id_inscripcion,
                   'error': str(e)
               })
       
       return {
           'total_procesadas': len(inscripciones_ids),
           'exitosas': len(exitosas),
           'errores': len(errores),
           'inscripciones_exitosas': exitosas,
           'inscripciones_con_error': errores
       }
   
   @staticmethod
   def generar_reporte_financiero(
       id_parroquia: int = None,
       fecha_inicio: date = None,
       fecha_fin: date = None
   ) -> Dict[str, Any]:
       """
       Genera un reporte financiero de inscripciones.
       
       Args:
           id_parroquia: ID de la parroquia (opcional)
           fecha_inicio: Fecha de inicio del período
           fecha_fin: Fecha de fin del período
           
       Returns:
           dict: Reporte financiero
       """
       try:
           sp_manager = get_sp_manager()
           
           # Parámetros de búsqueda
           params = {}
           if id_parroquia:
               params['id_parroquia'] = id_parroquia
           if fecha_inicio:
               params['fecha_inicio'] = fecha_inicio
           if fecha_fin:
               params['fecha_fin'] = fecha_fin
           
           # Obtener inscripciones del período
           result = sp_manager.executor.execute(
               'inscripciones',
               'obtener_reporte_financiero',
               params
           )
           
           if result.get('success') and result.get('data'):
               inscripciones = result['data']
           else:
               inscripciones = []
           
           # Calcular estadísticas
           total_inscripciones = len(inscripciones)
           monto_total_esperado = sum(i.get('monto_total', 0) for i in inscripciones)
           monto_total_pagado = sum(i.get('monto_pagado', 0) for i in inscripciones)
           monto_pendiente = monto_total_esperado - monto_total_pagado
           
           # Estadísticas por estado de pago
           por_estado_pago = {}
           for inscripcion in inscripciones:
               estado = inscripcion.get('estado_pago', 'sin_definir')
               por_estado_pago[estado] = por_estado_pago.get(estado, 0) + 1
           
           # Descuentos aplicados
           total_descuentos = sum(i.get('monto_descuento', 0) for i in inscripciones)
           inscripciones_con_descuento = len([i for i in inscripciones if i.get('tiene_descuento')])
           
           # Pagos vencidos
           pagos_vencidos = len([i for i in inscripciones if i.get('pago_vencido')])
           
           return {
               'periodo': {
                   'fecha_inicio': fecha_inicio.isoformat() if fecha_inicio else None,
                   'fecha_fin': fecha_fin.isoformat() if fecha_fin else None
               },
               'resumen_general': {
                   'total_inscripciones': total_inscripciones,
                   'monto_total_esperado': monto_total_esperado,
                   'monto_total_pagado': monto_total_pagado,
                   'monto_pendiente': monto_pendiente,
                   'porcentaje_recaudacion': (monto_total_pagado / monto_total_esperado * 100) if monto_total_esperado > 0 else 0
               },
               'estadisticas_pago': {
                   'por_estado': por_estado_pago,
                   'pagos_vencidos': pagos_vencidos,
                   'porcentaje_vencidos': (pagos_vencidos / total_inscripciones * 100) if total_inscripciones > 0 else 0
               },
               'descuentos': {
                   'total_descuentos': total_descuentos,
                   'inscripciones_con_descuento': inscripciones_con_descuento,
                   'porcentaje_con_descuento': (inscripciones_con_descuento / total_inscripciones * 100) if total_inscripciones > 0 else 0
               },
               'inscripciones_detalle': inscripciones,
               'fecha_generacion': date.today().isoformat()
           }
           
       except Exception as e:
           logger.error(f"Error generando reporte financiero: {str(e)}")
           return {
               'error': str(e),
               'fecha_generacion': date.today().isoformat()
           }
   
   @staticmethod
   def procesar_graduaciones_masivas(
       id_grupo: int,
       fecha_graduacion: date = None,
       usuario: str = None
   ) -> Dict[str, Any]:
       """
       Procesa graduaciones masivas de un grupo.
       
       Args:
           id_grupo: ID del grupo
           fecha_graduacion: Fecha de graduación
           usuario: Usuario que procesa
           
       Returns:
           dict: Resultado del procesamiento
       """
       try:
           # Obtener inscripciones activas del grupo
           inscripciones = Inscripcion.find_by_grupo(id_grupo)
           inscripciones_activas = [
               i for i in inscripciones 
               if i.estado == EstadoInscripcion.ACTIVA
           ]
           
           graduados = []
           no_graduados = []
           
           for inscripcion in inscripciones_activas:
               # Actualizar requisitos académicos
               inscripcion.actualizar_requisitos_academicos()
               
               if inscripcion.puede_graduarse:
                   resultado = inscripcion.graduar(fecha_graduacion, usuario)
                   if resultado['success']:
                       inscripcion.save(usuario)
                       graduados.append({
                           'id_inscripcion': inscripcion.id_inscripcion,
                           'codigo_inscripcion': inscripcion.codigo_inscripcion,
                           'id_catequizando': inscripcion.id_catequizando
                       })
                   else:
                       no_graduados.append({
                           'id_inscripcion': inscripcion.id_inscripcion,
                           'motivo': resultado['message']
                       })
               else:
                   motivos = []
                   if not inscripcion.cumple_requisitos_asistencia:
                       motivos.append(f"Asistencia: {inscripcion.porcentaje_asistencia:.1f}%")
                   if not inscripcion.cumple_requisitos_calificaciones:
                       motivos.append(f"Promedio: {inscripcion.promedio_calificaciones:.1f}")
                   if not inscripcion.esta_al_dia_pagos:
                       motivos.append("Pagos pendientes")
                   
                   no_graduados.append({
                       'id_inscripcion': inscripcion.id_inscripcion,
                       'motivo': '; '.join(motivos)
                   })
           
           return {
               'total_procesadas': len(inscripciones_activas),
               'graduados': len(graduados),
               'no_graduados': len(no_graduados),
               'inscripciones_graduadas': graduados,
               'inscripciones_no_graduadas': no_graduados,
               'fecha_graduacion': (fecha_graduacion or date.today()).isoformat()
           }
           
       except Exception as e:
           logger.error(f"Error en graduaciones masivas: {str(e)}")
           return {
               'error': str(e),
               'graduados': 0,
               'no_graduados': 0
           }
   
   @staticmethod
   def generar_reporte_academico(
       id_grupo: int = None,
       id_parroquia: int = None
   ) -> Dict[str, Any]:
       """
       Genera un reporte académico de inscripciones.
       
       Args:
           id_grupo: ID del grupo (opcional)
           id_parroquia: ID de la parroquia (opcional)
           
       Returns:
           dict: Reporte académico
       """
       try:
           # Obtener inscripciones según filtros
           if id_grupo:
               inscripciones = Inscripcion.find_by_grupo(id_grupo)
           elif id_parroquia:
               sp_manager = get_sp_manager()
               result = sp_manager.inscripciones.obtener_inscripciones_por_parroquia(id_parroquia)
               if result.get('success') and result.get('data'):
                   inscripciones = [Inscripcion(**item) for item in result['data']]
               else:
                   inscripciones = []
           else:
               inscripciones = Inscripcion.find_all({'estado': 'activa'})
           
           # Actualizar requisitos académicos
           for inscripcion in inscripciones:
               inscripcion.actualizar_requisitos_academicos()
           
           # Calcular estadísticas
           total_inscripciones = len(inscripciones)
           
           # Estadísticas de asistencia
           asistencias = [i.porcentaje_asistencia for i in inscripciones if i.porcentaje_asistencia > 0]
           promedio_asistencia = sum(asistencias) / len(asistencias) if asistencias else 0
           cumplen_asistencia = len([i for i in inscripciones if i.cumple_requisitos_asistencia])
           
           # Estadísticas de calificaciones
           calificaciones = [i.promedio_calificaciones for i in inscripciones if i.promedio_calificaciones > 0]
           promedio_calificaciones = sum(calificaciones) / len(calificaciones) if calificaciones else 0
           cumplen_calificaciones = len([i for i in inscripciones if i.cumple_requisitos_calificaciones])
           
           # Estudiantes que pueden graduarse
           pueden_graduarse = len([i for i in inscripciones if i.puede_graduarse])
           
           # Distribución por rangos de asistencia
           rangos_asistencia = {
               '90-100%': len([i for i in inscripciones if i.porcentaje_asistencia >= 90]),
               '80-89%': len([i for i in inscripciones if 80 <= i.porcentaje_asistencia < 90]),
               '70-79%': len([i for i in inscripciones if 70 <= i.porcentaje_asistencia < 80]),
               'Menos de 70%': len([i for i in inscripciones if 0 < i.porcentaje_asistencia < 70]),
               'Sin datos': len([i for i in inscripciones if i.porcentaje_asistencia == 0])
           }
           
           # Distribución por rangos de calificaciones
           rangos_calificaciones = {
               '9-10': len([i for i in inscripciones if i.promedio_calificaciones >= 9]),
               '8-8.9': len([i for i in inscripciones if 8 <= i.promedio_calificaciones < 9]),
               '7-7.9': len([i for i in inscripciones if 7 <= i.promedio_calificaciones < 8]),
               'Menos de 7': len([i for i in inscripciones if 0 < i.promedio_calificaciones < 7]),
               'Sin datos': len([i for i in inscripciones if i.promedio_calificaciones == 0])
           }
           
           return {
               'resumen_general': {
                   'total_inscripciones': total_inscripciones,
                   'promedio_asistencia_general': round(promedio_asistencia, 2),
                   'promedio_calificaciones_general': round(promedio_calificaciones, 2),
                   'pueden_graduarse': pueden_graduarse,
                   'porcentaje_graduables': (pueden_graduarse / total_inscripciones * 100) if total_inscripciones > 0 else 0
               },
               'requisitos_cumplimiento': {
                   'cumplen_asistencia': cumplen_asistencia,
                   'porcentaje_asistencia': (cumplen_asistencia / total_inscripciones * 100) if total_inscripciones > 0 else 0,
                   'cumplen_calificaciones': cumplen_calificaciones,
                   'porcentaje_calificaciones': (cumplen_calificaciones / total_inscripciones * 100) if total_inscripciones > 0 else 0
               },
               'distribuciones': {
                   'asistencia': rangos_asistencia,
                   'calificaciones': rangos_calificaciones
               },
               'fecha_generacion': date.today().isoformat()
           }
           
       except Exception as e:
           logger.error(f"Error generando reporte académico: {str(e)}")
           return {
               'error': str(e),
               'fecha_generacion': date.today().isoformat()
           }


# Funciones de utilidad para trabajar con inscripciones
def obtener_inscripciones_por_estado(
   estado: EstadoInscripcion,
   id_parroquia: int = None
) -> List[Inscripcion]:
   """
   Obtiene inscripciones filtradas por estado.
   
   Args:
       estado: Estado de las inscripciones
       id_parroquia: ID de la parroquia (opcional)
       
   Returns:
       List[Inscripcion]: Lista de inscripciones
   """
   try:
       sp_manager = get_sp_manager()
       
       params = {'estado': estado.value}
       if id_parroquia:
           params['id_parroquia'] = id_parroquia
       
       result = sp_manager.executor.execute(
           'inscripciones',
           'obtener_por_estado',
           params
       )
       
       if result.get('success') and result.get('data'):
           return [Inscripcion(**item) for item in result['data']]
       return []
       
   except Exception as e:
       logger.error(f"Error obteniendo inscripciones por estado: {str(e)}")
       return []


def obtener_estadisticas_inscripciones(id_parroquia: int = None) -> Dict[str, Any]:
   """
   Obtiene estadísticas generales de inscripciones.
   
   Args:
       id_parroquia: ID de la parroquia (opcional)
       
   Returns:
       dict: Estadísticas de inscripciones
   """
   try:
       sp_manager = get_sp_manager()
       
       params = {}
       if id_parroquia:
           params['id_parroquia'] = id_parroquia
       
       result = sp_manager.executor.execute(
           'inscripciones',
           'obtener_estadisticas_generales',
           params
       )
       
       if result.get('success') and result.get('data'):
           return result['data']
       
       return {
           'total_inscripciones': 0,
           'por_estado': {},
           'por_estado_pago': {},
           'monto_total_esperado': 0,
           'monto_total_pagado': 0,
           'porcentaje_recaudacion': 0
       }
       
   except Exception as e:
       logger.error(f"Error obteniendo estadísticas: {str(e)}")
       return {'error': str(e)}