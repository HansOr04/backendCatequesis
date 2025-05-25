"""
Servicio de gestión de certificados de catequesis.
Maneja emisión, validación y control de certificados.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
import uuid
import secrets

from app.services.base_service import BaseService
from app.models.catequesis.certificado_model import Certificado
from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.inscripcion_model import Inscripcion
from app.schemas.catequesis.certificado_schema import (
    CertificadoCreateSchema, CertificadoUpdateSchema, CertificadoResponseSchema,
    CertificadoSearchSchema, EmisionCertificadoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
from app.utils.pdf_generator import generate_certificate_pdf
from app.utils.qr_generator import generate_qr_code
import logging

logger = logging.getLogger(__name__)


class CertificadoService(BaseService):
    """Servicio para gestión de certificados."""
    
    @property
    def model(self) -> Type[Certificado]:
        return Certificado
    
    @property
    def create_schema(self) -> Type[CertificadoCreateSchema]:
        return CertificadoCreateSchema
    
    @property
    def update_schema(self) -> Type[CertificadoUpdateSchema]:
        return CertificadoUpdateSchema
    
    @property
    def response_schema(self) -> Type[CertificadoResponseSchema]:
        return CertificadoResponseSchema
    
    @property
    def search_schema(self) -> Type[CertificadoSearchSchema]:
        return CertificadoSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Certificado.catequizando),
            joinedload(Certificado.inscripcion),
            joinedload(Certificado.sacramento),
            joinedload(Certificado.created_by_user)
        )
    
    @require_permission('certificados', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que la inscripción esté completada
        if data.get('inscripcion_id'):
            inscripcion = self.db.query(Inscripcion).filter(
                Inscripcion.id == data['inscripcion_id']
            ).first()
            
            if not inscripcion or inscripcion.estado != 'completado':
                raise ValidationException("La inscripción debe estar completada para emitir certificado")
        
        # Generar código de verificación único
        data['codigo_verificacion'] = self._generate_verification_code()
        
        # Configuraciones por defecto
        data.setdefault('estado', 'borrador')
        data.setdefault('fecha_emision', date.today())
        
        return data
    
    @require_permission('certificados', 'emitir')
    def emitir_certificado(self, emision_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Emite un certificado generando el documento PDF.
        
        Args:
            emision_data: Datos para la emisión
            
        Returns:
            Dict con información del certificado emitido
        """
        try:
            schema = EmisionCertificadoSchema()
            validated_data = schema.load(emision_data)
            
            certificado_id = validated_data['certificado_id']
            template = validated_data.get('template', 'default')
            
            certificado = self._get_instance_by_id(certificado_id)
            
            if certificado.estado != 'borrador':
                raise ValidationException("Solo se pueden emitir certificados en estado borrador")
            
            # Generar PDF del certificado
            pdf_info = self._generate_certificate_pdf(certificado, template)
            
            # Generar código QR para verificación
            qr_code_url = self._generate_verification_qr(certificado.codigo_verificacion)
            
            # Actualizar certificado
            certificado.estado = 'emitido'
            certificado.fecha_emision = date.today()
            certificado.ruta_archivo = pdf_info['file_path']
            certificado.nombre_archivo = pdf_info['file_name']
            certificado.tamaño_archivo = pdf_info['file_size']
            certificado.hash_archivo = pdf_info['file_hash']
            certificado.url_qr_verificacion = qr_code_url
            certificado.emitido_por = self.current_user.get('id') if self.current_user else None
            certificado.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Certificado {certificado_id} emitido exitosamente")
            
            return {
                'success': True,
                'certificado_id': certificado_id,
                'codigo_verificacion': certificado.codigo_verificacion,
                'ruta_archivo': certificado.ruta_archivo,
                'url_verificacion': f"/api/certificados/verificar/{certificado.codigo_verificacion}",
                'mensaje': 'Certificado emitido exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error emitiendo certificado: {str(e)}")
            raise BusinessLogicException("Error emitiendo certificado")
    
    def verificar_certificado(self, codigo_verificacion: str) -> Dict[str, Any]:
        """
        Verifica la autenticidad de un certificado.
        
        Args:
            codigo_verificacion: Código de verificación del certificado
            
        Returns:
            Dict con información del certificado verificado
        """
        try:
            certificado = self.db.query(Certificado).filter(
                Certificado.codigo_verificacion == codigo_verificacion
            ).options(
                joinedload(Certificado.catequizando),
                joinedload(Certificado.sacramento)
            ).first()
            
            if not certificado:
                return {
                    'valido': False,
                    'mensaje': 'Código de verificación inválido'
                }
            
            # Verificar estado del certificado
            if certificado.estado not in ['emitido', 'entregado']:
                return {
                    'valido': False,
                    'mensaje': 'Certificado no válido o anulado'
                }
            
            # Verificar vigencia si aplica
            if certificado.fecha_vencimiento and certificado.fecha_vencimiento < date.today():
                return {
                    'valido': False,
                    'mensaje': 'Certificado vencido'
                }
            
            return {
                'valido': True,
                'certificado': {
                    'id': certificado.id,
                    'tipo': certificado.tipo_certificado,
                    'beneficiario': f"{certificado.catequizando.nombres} {certificado.catequizando.apellidos}",
                    'documento': certificado.catequizando.numero_documento,
                    'sacramento': certificado.sacramento.nombre if certificado.sacramento else None,
                    'fecha_emision': certificado.fecha_emision.isoformat(),
                    'fecha_vencimiento': certificado.fecha_vencimiento.isoformat() if certificado.fecha_vencimiento else None,
                    'institucion_emisora': certificado.institucion_emisora
                },
                'mensaje': 'Certificado válido y verificado'
            }
            
        except Exception as e:
            logger.error(f"Error verificando certificado: {str(e)}")
            raise BusinessLogicException("Error verificando certificado")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas de certificados."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Distribución por tipo
            tipo_distribution = self.db.query(
                Certificado.tipo_certificado, func.count(Certificado.id)
            ).group_by(Certificado.tipo_certificado).all()
            
            # Distribución por estado
            estado_distribution = self.db.query(
                Certificado.estado, func.count(Certificado.id)
            ).group_by(Certificado.estado).all()
            
            # Certificados emitidos este mes
            emitidos_mes = self.db.query(Certificado).filter(
                and_(
                    func.extract('month', Certificado.fecha_emision) == datetime.now().month,
                    func.extract('year', Certificado.fecha_emision) == datetime.now().year
                )
            ).count()
            
            base_stats.update({
                'distribucion_tipos': {tipo: count for tipo, count in tipo_distribution},
                'distribucion_estados': {estado: count for estado, count in estado_distribution},
                'emitidos_este_mes': emitidos_mes
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _generate_verification_code(self) -> str:
        """Genera un código único de verificación."""
        while True:
            code = secrets.token_urlsafe(16)
            if not self.db.query(Certificado).filter(Certificado.codigo_verificacion == code).first():
                return code
    
    def _generate_certificate_pdf(self, certificado: Certificado, template: str) -> Dict[str, Any]:
        """Genera el archivo PDF del certificado."""
        return generate_certificate_pdf(certificado, template)
    
    def _generate_verification_qr(self, codigo_verificacion: str) -> str:
        """Genera código QR para verificación."""
        verification_url = f"https://sistema.parroquia.com/verificar/{codigo_verificacion}"
        return generate_qr_code(verification_url)