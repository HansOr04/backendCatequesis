"""
Modelo de Pago de Inscripción para el sistema de catequesis.
Gestiona los pagos realizados por las inscripciones.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.base_model import BaseModel, ModelFactory
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TipoPago(Enum):
    """Tipos de pago."""
    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    TARJETA_CREDITO = "tarjeta_credito"
    TARJETA_DEBITO = "tarjeta_debito"
    CHEQUE = "cheque"
    CONSIGNACION = "consignacion"
    PSE = "pse"
    NEQUI = "nequi"
    DAVIPLATA = "daviplata"


class EstadoPago(Enum):
    """Estados del pago."""
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    REVERSADO = "reversado"
    ANULADO = "anulado"


class ConceptoPago(Enum):
    """Conceptos de pago."""
    INSCRIPCION = "inscripcion"
    MATERIALES = "materiales"
    CERTIFICADO = "certificado"
    MORA = "mora"
    OTRO = "otro"


class PagoInscripcion(BaseModel):
    """
    Modelo de Pago de Inscripción del sistema de catequesis.
    Registra los pagos realizados por inscripciones.
    """
    
    # Configuración del modelo
    _table_schema = "pagos_inscripcion"
    _primary_key = "id_pago"
    _required_fields = ["id_inscripcion", "monto", "tipo_pago"]
    _unique_fields = ["numero_transaccion"]
    _searchable_fields = [
        "numero_transaccion", "referencia_pago", "nombre_pagador"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa el modelo Pago de Inscripción."""
        # Identificación básica
        self.id_pago: Optional[int] = None
        self.numero_transaccion: Optional[str] = None
        self.id_inscripcion: int = 0
        self.id_catequizando: Optional[int] = None
        
        # Información del pago
        self.concepto: ConceptoPago = ConceptoPago.INSCRIPCION
        self.descripcion_concepto: Optional[str] = None
        self.monto: float = 0.0
        self.monto_descuento: float = 0.0
        self.monto_recargo: float = 0.0
        self.monto_total: float = 0.0
        
        # Método de pago
        self.tipo_pago: TipoPago = TipoPago.EFECTIVO
        self.estado: EstadoPago = EstadoPago.PENDIENTE
        self.fecha_pago: date = date.today()
        self.fecha_vencimiento: Optional[date] = None
        
        # Información del pagador
        self.nombre_pagador: Optional[str] = None
        self.documento_pagador: Optional[str] = None
        self.telefono_pagador: Optional[str] = None
        self.email_pagador: Optional[str] = None
        
        # Referencias bancarias/financieras
        self.referencia_pago: Optional[str] = None
        self.numero_cheque: Optional[str] = None
        self.banco_origen: Optional[str] = None
        self.cuenta_origen: Optional[str] = None
        self.banco_destino: Optional[str] = None
        self.cuenta_destino: Optional[str] = None
        
        # Información de tarjeta (últimos 4 dígitos)
        self.ultimos_digitos_tarjeta: Optional[str] = None
        self.tipo_tarjeta: Optional[str] = None
        self.franquicia: Optional[str] = None
        
        # Control administrativo
        self.recibido_por: Optional[str] = None
        self.autorizado_por: Optional[str] = None
        self.fecha_autorizacion: Optional[date] = None
        self.numero_recibo: Optional[str] = None
        self.comprobante_fisico: bool = False
        
        # Reversión/Anulación
        self.fecha_reverso: Optional[date] = None
        self.motivo_reverso: Optional[str] = None
        self.reversado_por: Optional[str] = None
        self.id_pago_reverso: Optional[int] = None
        
        # Observaciones
        self.observaciones: Optional[str] = None
        self.notas_internas: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def esta_aprobado(self) -> bool:
        """Verifica si el pago está aprobado."""
        return self.estado == EstadoPago.APROBADO
    
    @property
    def esta_pendiente(self) -> bool:
        """Verifica si el pago está pendiente."""
        return self.estado == EstadoPago.PENDIENTE
    
    @property
    def puede_reversar(self) -> bool:
        """Verifica si el pago puede ser reversado."""
        return self.estado == EstadoPago.APROBADO and not self.fecha_reverso
    
    @property
    def descripcion_tipo_pago(self) -> str:
        """Obtiene la descripción del tipo de pago."""
        descripciones = {
            TipoPago.EFECTIVO: "Efectivo",
            TipoPago.TRANSFERENCIA: "Transferencia Bancaria",
            TipoPago.TARJETA_CREDITO: "Tarjeta de Crédito",
            TipoPago.TARJETA_DEBITO: "Tarjeta Débito",
            TipoPago.CHEQUE: "Cheque",
            TipoPago.CONSIGNACION: "Consignación",
            TipoPago.PSE: "PSE",
            TipoPago.NEQUI: "Nequi",
            TipoPago.DAVIPLATA: "Daviplata"
        }
        return descripciones.get(self.tipo_pago, "Otro")
    
    def _validate_model_specific(self) -> None:
        """Validación específica del modelo Pago de Inscripción."""
        # Validar ID de inscripción
        if self.id_inscripcion <= 0:
            raise ValidationError("Debe especificar una inscripción válida")
        
        # Validar montos
        if self.monto <= 0:
            raise ValidationError("El monto debe ser mayor a 0")
        
        if self.monto_descuento < 0:
            raise ValidationError("El descuento no puede ser negativo")
        
        if self.monto_recargo < 0:
            raise ValidationError("El recargo no puede ser negativo")
        
        # Validar fecha de vencimiento
        if self.fecha_vencimiento and self.fecha_vencimiento < self.fecha_pago:
            raise ValidationError("La fecha de vencimiento no puede ser anterior al pago")
        
        # Validar enums
        if isinstance(self.tipo_pago, str):
            try:
                self.tipo_pago = TipoPago(self.tipo_pago)
            except ValueError:
                raise ValidationError(f"Tipo de pago '{self.tipo_pago}' no válido")
        
        if isinstance(self.estado, str):
            try:
                self.estado = EstadoPago(self.estado)
            except ValueError:
                raise ValidationError(f"Estado '{self.estado}' no válido")
        
        if isinstance(self.concepto, str):
            try:
                self.concepto = ConceptoPago(self.concepto)
            except ValueError:
                raise ValidationError(f"Concepto '{self.concepto}' no válido")
        
        # Validar información específica por tipo de pago
        if self.tipo_pago == TipoPago.CHEQUE and not self.numero_cheque:
            raise ValidationError("Los pagos con cheque requieren número de cheque")
        
        if self.tipo_pago in [TipoPago.TRANSFERENCIA, TipoPago.CONSIGNACION]:
            if not self.referencia_pago:
                raise ValidationError("Las transferencias/consignaciones requieren referencia")
    
    def generar_numero_transaccion(self) -> str:
        """
        Genera un número de transacción único.
        
        Returns:
            str: Número de transacción generado
        """
        try:
            año = self.fecha_pago.year
            mes = self.fecha_pago.month
            
            # Obtener siguiente número secuencial
            result = self._sp_manager.executor.execute(
                'pagos_inscripcion',
                'obtener_siguiente_numero_transaccion',
                {
                    'año': año,
                    'mes': mes
                }
            )
            
            if result.get('success') and result.get('data'):
                numero = result['data'].get('siguiente_numero', 1)
            else:
                numero = 1
            
            numero_transaccion = f"PAG-{año}{mes:02d}-{numero:06d}"
            self.numero_transaccion = numero_transaccion
            
            return numero_transaccion
            
        except Exception as e:
            logger.error(f"Error generando número de transacción: {str(e)}")
            # Fallback con timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"PAG-{timestamp}"
    
    def calcular_monto_total(self) -> None:
        """Calcula el monto total del pago."""
        self.monto_total = self.monto - self.monto_descuento + self.monto_recargo
    
    def procesar_pago(
        self,
        recibido_por: str,
        numero_recibo: str = None,
        observaciones: str = None
    ) -> Dict[str, Any]:
        """
        Procesa el pago.
        
        Args:
            recibido_por: Usuario que recibe el pago
            numero_recibo: Número de recibo
            observaciones: Observaciones del pago
            
        Returns:
            dict: Resultado del procesamiento
        """
        try:
            if self.estado != EstadoPago.PENDIENTE:
                raise ValidationError("Solo se pueden procesar pagos pendientes")
            
            # Generar número de transacción si no existe
            if not self.numero_transaccion:
                self.generar_numero_transaccion()
            
            # Calcular monto total
            self.calcular_monto_total()
            
            # Actualizar información del pago
            self.estado = EstadoPago.PROCESANDO
            self.recibido_por = recibido_por
            self.numero_recibo = numero_recibo
            
            if observaciones:
                self.observaciones = observaciones
            
            logger.info(f"Pago {self.numero_transaccion} en procesamiento")
            
            return {
                'success': True,
                'numero_transaccion': self.numero_transaccion,
                'monto_total': self.monto_total
            }
            
        except Exception as e:
            logger.error(f"Error procesando pago: {str(e)}")
            return {
                'success': False,
                'message': f"Error procesando pago: {str(e)}"
            }
    
    def aprobar_pago(
        self,
        autorizado_por: str,
        observaciones: str = None
    ) -> None:
        """
        Aprueba el pago.
        
        Args:
            autorizado_por: Usuario que autoriza
            observaciones: Observaciones de la aprobación
        """
        if self.estado not in [EstadoPago.PENDIENTE, EstadoPago.PROCESANDO]:
            raise ValidationError("Solo se pueden aprobar pagos pendientes o en procesamiento")
        
        self.estado = EstadoPago.APROBADO
        self.autorizado_por = autorizado_por
        self.fecha_autorizacion = date.today()
        
        if observaciones:
            self.observaciones = observaciones
        
        logger.info(f"Pago {self.numero_transaccion} aprobado por {autorizado_por}")
    
    def rechazar_pago(
        self,
        motivo: str,
        rechazado_por: str
    ) -> None:
        """
        Rechaza el pago.
        
        Args:
            motivo: Motivo del rechazo
            rechazado_por: Usuario que rechaza
        """
        if self.estado == EstadoPago.APROBADO:
            raise ValidationError("No se pueden rechazar pagos aprobados")
        
        self.estado = EstadoPago.RECHAZADO
        self.observaciones = f"RECHAZADO: {motivo}"
        self.autorizado_por = rechazado_por
        self.fecha_autorizacion = date.today()
        
        logger.info(f"Pago {self.numero_transaccion} rechazado: {motivo}")
    
    def reversar_pago(
        self,
        motivo: str,
        reversado_por: str
    ) -> 'PagoInscripcion':
        """
        Reversa el pago creando un pago negativo.
        
        Args:
            motivo: Motivo de la reversión
            reversado_por: Usuario que reversa
            
        Returns:
            PagoInscripcion: Pago de reversión creado
        """
        if not self.puede_reversar:
            raise ValidationError("El pago no puede ser reversado")
        
        # Crear pago de reversión
        pago_reverso = PagoInscripcion(
            id_inscripcion=self.id_inscripcion,
            id_catequizando=self.id_catequizando,
            concepto=self.concepto,
            descripcion_concepto=f"REVERSO: {self.descripcion_concepto}",
            monto=-self.monto,
            monto_descuento=-self.monto_descuento,
            monto_recargo=-self.monto_recargo,
            monto_total=-self.monto_total,
            tipo_pago=self.tipo_pago,
            estado=EstadoPago.APROBADO,
            fecha_pago=date.today(),
            nombre_pagador=self.nombre_pagador,
            recibido_por=reversado_por,
            autorizado_por=reversado_por,
            fecha_autorizacion=date.today(),
            observaciones=f"Reversión del pago {self.numero_transaccion}: {motivo}"
        )
        
        # Generar número de transacción para el reverso
        pago_reverso.generar_numero_transaccion()
        pago_reverso.numero_transaccion += "-REV"
        
        # Actualizar este pago
        self.estado = EstadoPago.REVERSADO
        self.fecha_reverso = date.today()
        self.motivo_reverso = motivo
        self.reversado_por = reversado_por
        self.id_pago_reverso = pago_reverso.id_pago
        
        logger.info(f"Pago {self.numero_transaccion} reversado: {motivo}")
        
        return pago_reverso
    
    def to_dict(self, include_audit: bool = False, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        data = super().to_dict(include_audit)
        
        # Convertir enums a strings
        data['tipo_pago'] = self.tipo_pago.value
        data['estado'] = self.estado.value
        data['concepto'] = self.concepto.value
        
        # Agregar propiedades calculadas
        data['descripcion_tipo_pago'] = self.descripcion_tipo_pago
        data['esta_aprobado'] = self.esta_aprobado
        data['esta_pendiente'] = self.esta_pendiente
        data['puede_reversar'] = self.puede_reversar
        
        # Remover datos sensibles si no se solicitan
        if not include_sensitive:
            sensitive_fields = [
                'cuenta_origen', 'cuenta_destino', 'ultimos_digitos_tarjeta',
                'numero_cheque', 'documento_pagador'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def find_by_inscripcion(cls, id_inscripcion: int) -> List['PagoInscripcion']:
        """Busca pagos de una inscripción."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'pagos_inscripcion',
                'obtener_por_inscripcion',
                {'id_inscripcion': id_inscripcion}
            )
            
            if result.get('success') and result.get('data'):
                return [cls(**item) for item in result['data']]
            return []
            
        except Exception as e:
            logger.error(f"Error buscando pagos por inscripción: {str(e)}")
            return []
    
    @classmethod
    def find_by_numero_transaccion(cls, numero_transaccion: str) -> Optional['PagoInscripcion']:
        """Busca un pago por número de transacción."""
        try:
            sp_manager = get_sp_manager()
            result = sp_manager.executor.execute(
                'pagos_inscripcion',
                'obtener_por_numero_transaccion',
                {'numero_transaccion': numero_transaccion}
            )
            
            if result.get('success') and result.get('data'):
                return cls(**result['data'])
            return None
            
        except Exception as e:
            logger.error(f"Error buscando pago por número de transacción: {str(e)}")
            return None

    def save(self, usuario: str = None) -> 'PagoInscripcion':
        """Guarda el pago con validaciones adicionales."""
        # Generar número de transacción si no existe
        if not self.numero_transaccion:
            self.generar_numero_transaccion()
        
        # Calcular monto total antes de guardar
        self.calcular_monto_total()
        
        return super().save(usuario)


# Registrar el modelo en la factory
ModelFactory.register('pago_inscripcion', PagoInscripcion)