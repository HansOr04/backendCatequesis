"""
Servicio de gestión de pagos de inscripción.
Maneja registro, seguimiento y conciliación de pagos.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.pago_inscripcion_model import PagoInscripcion
from app.models.catequesis.inscripcion_model import Inscripcion
from app.schemas.catequesis.pago_inscripcion_schema import (
    PagoInscripcionCreateSchema, PagoInscripcionUpdateSchema, PagoInscripcionResponseSchema,
    PagoInscripcionSearchSchema, ConciliacionPagoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class PagoInscripcionService(BaseService):
    """Servicio para gestión de pagos de inscripción."""
    
    @property
    def model(self) -> Type[PagoInscripcion]:
        return PagoInscripcion
    
    @property
    def create_schema(self) -> Type[PagoInscripcionCreateSchema]:
        return PagoInscripcionCreateSchema
    
    @property
    def update_schema(self) -> Type[PagoInscripcionUpdateSchema]:
        return PagoInscripcionUpdateSchema
    
    @property
    def response_schema(self) -> Type[PagoInscripcionResponseSchema]:
        return PagoInscripcionResponseSchema
    
    @property
    def search_schema(self) -> Type[PagoInscripcionSearchSchema]:
        return PagoInscripcionSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(PagoInscripcion.inscripcion).joinedload(Inscripcion.catequizando),
            joinedload(PagoInscripcion.inscripcion).joinedload(Inscripcion.grupo),
            joinedload(PagoInscripcion.created_by_user)
        )
    
    @require_permission('pagos', 'registrar')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que la inscripción existe
        inscripcion = self.db.query(Inscripcion).filter(
            Inscripcion.id == data['inscripcion_id']
        ).first()
        
        if not inscripcion:
            raise NotFoundException("Inscripción no encontrada")
        
        # Verificar que no esté completamente pagada
        total_pagado = self.db.query(func.sum(PagoInscripcion.monto)).filter(
            and_(
                PagoInscripcion.inscripcion_id == data['inscripcion_id'],
                PagoInscripcion.estado == 'confirmado'
            )
        ).scalar() or Decimal('0')
        
        if total_pagado >= inscripcion.monto_total:
            raise ValidationException("La inscripción ya está completamente pagada")
        
        # Generar número de recibo si no se proporciona
        if not data.get('numero_recibo'):
            data['numero_recibo'] = self._generate_receipt_number()
        
        # Configuraciones por defecto
        data.setdefault('fecha_pago', date.today())
        data.setdefault('estado', 'pendiente')
        data.setdefault('moneda', 'COP')
       
        return data
   
    @require_permission('pagos', 'confirmar')
    def confirmar_pago(self, pago_id: int, confirmacion_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Confirma un pago pendiente.
        
        Args:
            pago_id: ID del pago
            confirmacion_data: Datos adicionales de confirmación
            
        Returns:
            Dict con confirmación del pago
        """
        try:
            pago = self._get_instance_by_id(pago_id)
            
            if pago.estado != 'pendiente':
                raise ValidationException("Solo se pueden confirmar pagos pendientes")
            
            # Actualizar estado
            pago.estado = 'confirmado'
            pago.fecha_confirmacion = datetime.utcnow()
            pago.confirmado_por = self.current_user.get('id') if self.current_user else None
            
            if confirmacion_data:
                pago.referencia_bancaria = confirmacion_data.get('referencia_bancaria')
                pago.observaciones = confirmacion_data.get('observaciones')
            
            pago.updated_at = datetime.utcnow()
            
            # Actualizar estado de la inscripción si está completamente pagada
            self._update_inscription_payment_status(pago.inscripcion_id)
            
            self.db.commit()
            
            logger.info(f"Pago {pago_id} confirmado exitosamente")
            
            return {
                'success': True,
                'numero_recibo': pago.numero_recibo,
                'monto': float(pago.monto),
                'fecha_confirmacion': pago.fecha_confirmacion.isoformat(),
                'mensaje': 'Pago confirmado exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error confirmando pago: {str(e)}")
            raise BusinessLogicException("Error confirmando pago")
    
    def get_estado_pagos_inscripcion(self, inscripcion_id: int) -> Dict[str, Any]:
        """
        Obtiene el estado de pagos de una inscripción.
        
        Args:
            inscripcion_id: ID de la inscripción
            
        Returns:
            Dict con estado de pagos
        """
        try:
            inscripcion = self.db.query(Inscripcion).filter(
                Inscripcion.id == inscripcion_id
            ).first()
            
            if not inscripcion:
                raise NotFoundException("Inscripción no encontrada")
            
            # Obtener pagos
            pagos = self.db.query(PagoInscripcion).filter(
                PagoInscripcion.inscripcion_id == inscripcion_id
            ).order_by(PagoInscripcion.fecha_pago).all()
            
            # Calcular totales
            total_pagado = sum(p.monto for p in pagos if p.estado == 'confirmado')
            total_pendiente = sum(p.monto for p in pagos if p.estado == 'pendiente')
            saldo_pendiente = inscripcion.monto_total - total_pagado
            
            return {
                'inscripcion_id': inscripcion_id,
                'monto_total': float(inscripcion.monto_total),
                'total_pagado': float(total_pagado),
                'total_pendiente': float(total_pendiente),
                'saldo_pendiente': float(saldo_pendiente),
                'porcentaje_pagado': round((total_pagado / inscripcion.monto_total) * 100, 2),
                'esta_completamente_pagado': saldo_pendiente <= 0,
                'pagos': [self._serialize_response(p) for p in pagos]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de pagos: {str(e)}")
            raise BusinessLogicException("Error obteniendo estado de pagos")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas de pagos."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Totales por estado
            estado_stats = self.db.query(
                PagoInscripcion.estado,
                func.count(PagoInscripcion.id).label('cantidad'),
                func.sum(PagoInscripcion.monto).label('total')
            ).group_by(PagoInscripcion.estado).all()
            
            # Pagos por método
            metodo_stats = self.db.query(
                PagoInscripcion.metodo_pago,
                func.count(PagoInscripcion.id).label('cantidad'),
                func.sum(PagoInscripcion.monto).label('total')
            ).filter(
                PagoInscripcion.estado == 'confirmado'
            ).group_by(PagoInscripcion.metodo_pago).all()
            
            # Ingresos del mes actual
            ingresos_mes = self.db.query(
                func.sum(PagoInscripcion.monto)
            ).filter(
                and_(
                    PagoInscripcion.estado == 'confirmado',
                    func.extract('month', PagoInscripcion.fecha_pago) == datetime.now().month,
                    func.extract('year', PagoInscripcion.fecha_pago) == datetime.now().year
                )
            ).scalar() or Decimal('0')
            
            base_stats.update({
                'por_estado': {estado: {'cantidad': cant, 'total': float(total or 0)} for estado, cant, total in estado_stats},
                'por_metodo_pago': {metodo: {'cantidad': cant, 'total': float(total or 0)} for metodo, cant, total in metodo_stats},
                'ingresos_mes_actual': float(ingresos_mes)
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _generate_receipt_number(self) -> str:
        """Genera número único de recibo."""
        today = date.today()
        prefix = f"REC{today.strftime('%Y%m%d')}"
        
        # Obtener el último número del día
        last_receipt = self.db.query(PagoInscripcion).filter(
            PagoInscripcion.numero_recibo.like(f"{prefix}%")
        ).order_by(PagoInscripcion.numero_recibo.desc()).first()
        
        if last_receipt:
            last_number = int(last_receipt.numero_recibo[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:04d}"
    
    def _update_inscription_payment_status(self, inscripcion_id: int):
        """Actualiza el estado de pago de la inscripción."""
        inscripcion = self.db.query(Inscripcion).filter(
            Inscripcion.id == inscripcion_id
        ).first()
        
        if not inscripcion:
            return
        
        # Calcular total pagado
        total_pagado = self.db.query(func.sum(PagoInscripcion.monto)).filter(
            and_(
                PagoInscripcion.inscripcion_id == inscripcion_id,
                PagoInscripcion.estado == 'confirmado'
            )
        ).scalar() or Decimal('0')
        
        # Actualizar estado de pago
        if total_pagado >= inscripcion.monto_total:
            inscripcion.estado_pago = 'pagado'
        elif total_pagado > 0:
            inscripcion.estado_pago = 'parcial'
        else:
            inscripcion.estado_pago = 'pendiente'
        
        inscripcion.updated_at = datetime.utcnow()