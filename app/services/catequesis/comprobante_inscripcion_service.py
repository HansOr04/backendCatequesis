"""
Servicio de gestión de comprobantes de inscripción.
Maneja generación, entrega y seguimiento de comprobantes.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.comprobante_inscripcion_model import ComprobanteInscripcion
from app.models.catequesis.inscripcion_model import Inscripcion
from app.schemas.catequesis.comprobante_inscripcion_schema import (
    ComprobanteInscripcionCreateSchema, ComprobanteInscripcionUpdateSchema, ComprobanteInscripcionResponseSchema,
    ComprobanteInscripcionSearchSchema, GeneracionComprobanteSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
from app.utils.pdf_generator import generate_enrollment_receipt
import logging

logger = logging.getLogger(__name__)


class ComprobanteInscripcionService(BaseService):
    """Servicio para gestión de comprobantes de inscripción."""
    
    @property
    def model(self) -> Type[ComprobanteInscripcion]:
        return ComprobanteInscripcion
    
    @property
    def create_schema(self) -> Type[ComprobanteInscripcionCreateSchema]:
        return ComprobanteInscripcionCreateSchema
    
    @property
    def update_schema(self) -> Type[ComprobanteInscripcionUpdateSchema]:
        return ComprobanteInscripcionUpdateSchema
    
    @property
    def response_schema(self) -> Type[ComprobanteInscripcionResponseSchema]:
        return ComprobanteInscripcionResponseSchema
    
    @property
    def search_schema(self) -> Type[ComprobanteInscripcionSearchSchema]:
        return ComprobanteInscripcionSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(ComprobanteInscripcion.inscripcion).joinedload(Inscripcion.catequizando),
            joinedload(ComprobanteInscripcion.inscripcion).joinedload(Inscripcion.grupo),
            joinedload(ComprobanteInscripcion.pago),
            joinedload(ComprobanteInscripcion.created_by_user)
        )
    
    @require_permission('comprobantes', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que la inscripción existe
        inscripcion = self.db.query(Inscripcion).filter(
            Inscripcion.id == data['inscripcion_id']
        ).first()
        
        if not inscripcion:
            raise NotFoundException("Inscripción no encontrada")
        
        # Generar número de comprobante si no se proporciona
        if not data.get('numero_comprobante'):
            data['numero_comprobante'] = self._generate_receipt_number()
        
        # Configuraciones por defecto
        data.setdefault('fecha_emision', date.today())
        data.setdefault('estado', 'borrador')
        data.setdefault('formato', 'pdf')
        
        return data
    
    @require_permission('comprobantes', 'generar')
    def generar_comprobante(self, generacion_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera el documento del comprobante.
        
        Args:
            generacion_data: Datos para la generación
            
        Returns:
            Dict con información del comprobante generado
        """
        try:
            schema = GeneracionComprobanteSchema()
            validated_data = schema.load(generacion_data)
            
            comprobante_id = validated_data['comprobante_id']
            template = validated_data.get('template', 'default')
            
            comprobante = self._get_instance_by_id(comprobante_id)
            
            if comprobante.estado not in ['borrador']:
                raise ValidationException("Solo se pueden generar comprobantes en estado borrador")
            
            # Generar PDF del comprobante
            pdf_info = self._generate_receipt_pdf(comprobante, template)
            
            # Actualizar comprobante
            comprobante.estado = 'generado'
            comprobante.ruta_archivo = pdf_info['file_path']
            comprobante.nombre_archivo = pdf_info['file_name']
            comprobante.tamaño_archivo = pdf_info['file_size']
            comprobante.hash_archivo = pdf_info['file_hash']
            comprobante.template_usado = template
            comprobante.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Comprobante {comprobante_id} generado exitosamente")
            
            return {
                'success': True,
                'comprobante_id': comprobante_id,
                'numero_comprobante': comprobante.numero_comprobante,
                'ruta_archivo': comprobante.ruta_archivo,
                'mensaje': 'Comprobante generado exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error generando comprobante: {str(e)}")
            raise BusinessLogicException("Error generando comprobante")
    
    def marcar_como_entregado(self, comprobante_id: int, entrega_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Marca un comprobante como entregado.
        
        Args:
            comprobante_id: ID del comprobante
            entrega_data: Datos de la entrega
            
        Returns:
            Dict con confirmación de entrega
        """
        try:
            comprobante = self._get_instance_by_id(comprobante_id)
            
            if comprobante.estado != 'generado':
                raise ValidationException("Solo se pueden entregar comprobantes generados")
            
            # Actualizar entrega
            comprobante.estado = 'entregado'
            comprobante.fecha_entrega = entrega_data.get('fecha_entrega', date.today())
            comprobante.entregado_por = self.current_user.get('id') if self.current_user else None
            comprobante.recibido_por = entrega_data.get('recibido_por')
            comprobante.medio_entrega = entrega_data.get('medio_entrega', 'presencial')
            comprobante.observaciones_entrega = entrega_data.get('observaciones')
            comprobante.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Comprobante {comprobante_id} marcado como entregado")
            
            return {
                'success': True,
                'fecha_entrega': comprobante.fecha_entrega.isoformat(),
                'mensaje': 'Comprobante marcado como entregado'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marcando entrega: {str(e)}")
            raise BusinessLogicException("Error marcando comprobante como entregado")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas de comprobantes."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Distribución por estado
            estado_distribution = self.db.query(
                ComprobanteInscripcion.estado, func.count(ComprobanteInscripcion.id)
            ).group_by(ComprobanteInscripcion.estado).all()
            
            # Distribución por tipo
            tipo_distribution = self.db.query(
                ComprobanteInscripcion.tipo_comprobante, func.count(ComprobanteInscripcion.id)
            ).group_by(ComprobanteInscripcion.tipo_comprobante).all()
            
            # Comprobantes pendientes de entrega
            pendientes_entrega = self.db.query(ComprobanteInscripcion).filter(
                ComprobanteInscripcion.estado == 'generado'
            ).count()
            
            base_stats.update({
                'distribucion_estados': {estado: count for estado, count in estado_distribution},
                'distribucion_tipos': {tipo: count for tipo, count in tipo_distribution},
                'pendientes_entrega': pendientes_entrega
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _generate_receipt_number(self) -> str:
        """Genera número único de comprobante."""
        today = date.today()
        prefix = f"COMP{today.strftime('%Y%m%d')}"
        
        # Obtener el último número del día
        last_receipt = self.db.query(ComprobanteInscripcion).filter(
            ComprobanteInscripcion.numero_comprobante.like(f"{prefix}%")
        ).order_by(ComprobanteInscripcion.numero_comprobante.desc()).first()
        
        if last_receipt:
            last_number = int(last_receipt.numero_comprobante[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:04d}"
    
    def _generate_receipt_pdf(self, comprobante: ComprobanteInscripcion, template: str) -> Dict[str, Any]:
        """Genera el archivo PDF del comprobante."""
        return generate_enrollment_receipt(comprobante, template)