"""
Servicio de emisión de certificados sacramentales.
Maneja el proceso completo de emisión de certificados oficiales.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
import secrets

from app.services.base_service import BaseService
from app.models.catequesis.emision_certificado_model import EmisionCertificado
from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.inscripcion_model import Inscripcion
from app.models.catequesis.sacramento_model import Sacramento
from app.schemas.catequesis.emision_certificado_schema import (
    EmisionCertificadoCreateSchema, EmisionCertificadoUpdateSchema, EmisionCertificadoResponseSchema,
    EmisionCertificadoSearchSchema, FirmaCertificadoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
from app.utils.certificate_generator import generate_sacramental_certificate
from app.utils.digital_signature import sign_document
import logging

logger = logging.getLogger(__name__)


class EmisionCertificadoService(BaseService):
    """Servicio para emisión de certificados sacramentales."""
    
    @property
    def model(self) -> Type[EmisionCertificado]:
        return EmisionCertificado
    
    @property
    def create_schema(self) -> Type[EmisionCertificadoCreateSchema]:
        return EmisionCertificadoCreateSchema
    
    @property
    def update_schema(self) -> Type[EmisionCertificadoUpdateSchema]:
        return EmisionCertificadoUpdateSchema
    
    @property
    def response_schema(self) -> Type[EmisionCertificadoResponseSchema]:
        return EmisionCertificadoResponseSchema
    
    @property
    def search_schema(self) -> Type[EmisionCertificadoSearchSchema]:
        return EmisionCertificadoSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(EmisionCertificado.catequizando),
            joinedload(EmisionCertificado.sacramento),
            joinedload(EmisionCertificado.inscripcion),
            joinedload(EmisionCertificado.padrinos),
            joinedload(EmisionCertificado.created_by_user)
        )
    
    @require_permission('certificados', 'emitir')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que el catequizando existe
        catequizando = self.db.query(Catequizando).filter(
            Catequizando.id == data['catequizando_id']
        ).first()
        
        if not catequizando:
            raise NotFoundException("Catequizando no encontrado")
        
        # Verificar que el sacramento requiere certificado
        if data.get('sacramento_id'):
            sacramento = self.db.query(Sacramento).filter(
                Sacramento.id == data['sacramento_id']
            ).first()
            
            if not sacramento:
                raise NotFoundException("Sacramento no encontrado")
        
        # Verificar prerequisitos sacramentales
        if data.get('inscripcion_id'):
            inscripcion = self.db.query(Inscripcion).filter(
                Inscripcion.id == data['inscripcion_id']
            ).first()
            
            if not inscripcion or inscripcion.estado != 'completado':
                raise ValidationException("La formación debe estar completada para emitir certificado")
        
        # Generar códigos únicos
        data['numero_certificado'] = self._generate_certificate_number(data['sacramento_id'])
        data['codigo_verificacion'] = self._generate_verification_code()
        
        # Configuraciones por defecto
        data.setdefault('fecha_emision', date.today())
        data.setdefault('estado', 'borrador')
        data.setdefault('formato_certificado', 'pdf')
        
        return data
    
    @require_permission('certificados', 'firmar')
    def firmar_certificado(self, certificado_id: int, firma_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Firma digitalmente un certificado.
        
        Args:
            certificado_id: ID del certificado
            firma_data: Datos de la firma
            
        Returns:
            Dict con confirmación de firma
        """
        try:
            schema = FirmaCertificadoSchema()
            validated_data = schema.load(firma_data)
            
            certificado = self._get_instance_by_id(certificado_id)
            
            if certificado.estado != 'generado':
                raise ValidationException("Solo se pueden firmar certificados generados")
            
            # Aplicar firma digital
            if validated_data['tipo_firma'] == 'digital':
                signature_info = sign_document(
                    certificado.ruta_archivo,
                    validated_data.get('certificado_digital_id')
                )
                certificado.huella_firma = signature_info['fingerprint']
                certificado.certificado_digital_id = validated_data.get('certificado_digital_id')
            
            # Actualizar estado
            certificado.estado = 'firmado'
            certificado.fecha_firma = datetime.utcnow()
            certificado.firmado_por = self.current_user.get('id') if self.current_user else None
            certificado.tipo_firma = validated_data['tipo_firma']
            certificado.observaciones_firma = validated_data.get('observaciones')
            certificado.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Certificado {certificado_id} firmado exitosamente")
            
            return {
                'success': True,
                'fecha_firma': certificado.fecha_firma.isoformat(),
                'tipo_firma': certificado.tipo_firma,
                'mensaje': 'Certificado firmado exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error firmando certificado: {str(e)}")
            raise BusinessLogicException("Error firmando certificado")
    
    def generar_certificado(self, certificado_id: int, template: str = 'oficial') -> Dict[str, Any]:
        """
        Genera el documento del certificado.
        
        Args:
            certificado_id: ID del certificado
            template: Plantilla a usar
            
        Returns:
            Dict con información del archivo generado
        """
        try:
            certificado = self._get_instance_by_id(certificado_id)
            
            if certificado.estado != 'borrador':
                raise ValidationException("Solo se pueden generar certificados en estado borrador")
            
            # Generar documento
            doc_info = generate_sacramental_certificate(certificado, template)
            
            # Actualizar certificado
            certificado.estado = 'generado'
            certificado.ruta_archivo = doc_info['file_path']
            certificado.nombre_archivo = doc_info['file_name']
            certificado.tamaño_archivo = doc_info['file_size']
            certificado.hash_archivo = doc_info['file_hash']
            certificado.template_certificado = template
            certificado.fecha_generacion = datetime.utcnow()
            certificado.generado_por = self.current_user.get('id') if self.current_user else None
            certificado.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Certificado {certificado_id} generado exitosamente")
            
            return {
                'success': True,
                'ruta_archivo': certificado.ruta_archivo,
                'nombre_archivo': certificado.nombre_archivo,
                'mensaje': 'Certificado generado exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error generando certificado: {str(e)}")
            raise BusinessLogicException("Error generando certificado")
    
    def verificar_certificado_sacramental(self, codigo_verificacion: str) -> Dict[str, Any]:
        """
        Verifica la autenticidad de un certificado sacramental.
        
        Args:
            codigo_verificacion: Código de verificación
            
        Returns:
            Dict con información de verificación
        """
        try:
            certificado = self.db.query(EmisionCertificado).filter(
                EmisionCertificado.codigo_verificacion == codigo_verificacion
            ).options(
                joinedload(EmisionCertificado.catequizando),
                joinedload(EmisionCertificado.sacramento)
            ).first()
            
            if not certificado:
                return {
                    'valido': False,
                    'mensaje': 'Código de verificación inválido'
                }
            
            # Verificar estado
            if certificado.estado not in ['firmado', 'entregado']:
                return {
                    'valido': False,
                    'mensaje': 'Certificado no válido o sin firmar'
                }
            
            # Verificar vigencia
            if certificado.fecha_vencimiento and certificado.fecha_vencimiento < date.today():
                return {
                    'valido': False,
                    'mensaje': 'Certificado vencido'
                }
            
            return {
                'valido': True,
                'certificado': {
                    'numero': certificado.numero_certificado,
                    'tipo': certificado.tipo_certificado,
                    'beneficiario': f"{certificado.catequizando.nombres} {certificado.catequizando.apellidos}",
                    'documento': certificado.catequizando.numero_documento,
                    'sacramento': certificado.sacramento.nombre if certificado.sacramento else None,
                    'fecha_emision': certificado.fecha_emision.isoformat(),
                    'lugar_evento': certificado.lugar_evento,
                    'celebrante': certificado.celebrante_principal,
                    'parroquia': certificado.parroquia.nombre if certificado.parroquia else None
                },
                'mensaje': 'Certificado sacramental válido y verificado'
            }
            
        except Exception as e:
            logger.error(f"Error verificando certificado: {str(e)}")
            raise BusinessLogicException("Error verificando certificado")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _generate_certificate_number(self, sacramento_id: int) -> str:
        """Genera número único de certificado."""
        sacramento = self.db.query(Sacramento).filter(Sacramento.id == sacramento_id).first()
        sacramento_code = sacramento.nombre[:3].upper() if sacramento else 'CER'
        
        year = datetime.now().year
        
        # Contar certificados del año para este sacramento
        count = self.db.query(EmisionCertificado).filter(
            and_(
                EmisionCertificado.sacramento_id == sacramento_id,
                func.extract('year', EmisionCertificado.fecha_emision) == year
            )
        ).count()
        
        return f"{sacramento_code}{year}{count + 1:04d}"
    
    def _generate_verification_code(self) -> str:
        """Genera código único de verificación."""
        while True:
            code = secrets.token_urlsafe(12)
            if not self.db.query(EmisionCertificado).filter(
                EmisionCertificado.codigo_verificacion == code
            ).first():
                return code