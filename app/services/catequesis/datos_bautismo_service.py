"""
Servicio de gestión de datos de bautismo.
Maneja información sacramental específica del bautismo.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.datos_bautismo_model import DatosBautismo
from app.models.catequesis.catequizando_model import Catequizando
from app.schemas.catequesis.datos_bautismo_schema import (
    DatosBautismoCreateSchema, DatosBautismoUpdateSchema, DatosBautismoResponseSchema,
    DatosBautismoSearchSchema, ValidacionBautismalSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class DatosBautismoService(BaseService):
    """Servicio para gestión de datos bautismales."""
    
    @property
    def model(self) -> Type[DatosBautismo]:
        return DatosBautismo
    
    @property
    def create_schema(self) -> Type[DatosBautismoCreateSchema]:
        return DatosBautismoCreateSchema
    
    @property
    def update_schema(self) -> Type[DatosBautismoUpdateSchema]:
        return DatosBautismoUpdateSchema
    
    @property
    def response_schema(self) -> Type[DatosBautismoResponseSchema]:
        return DatosBautismoResponseSchema
    
    @property
    def search_schema(self) -> Type[DatosBautismoSearchSchema]:
        return DatosBautismoSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(DatosBautismo.catequizando),
            joinedload(DatosBautismo.parroquia_bautismo),
            joinedload(DatosBautismo.created_by_user)
        )
    
    @require_permission('catequizandos', 'actualizar')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que el catequizando existe
        catequizando = self.db.query(Catequizando).filter(
            Catequizando.id == data['catequizando_id']
        ).first()
        
        if not catequizando:
            raise NotFoundException("Catequizando no encontrado")
        
        # Verificar que no tenga ya datos de bautismo
        existing = self.db.query(DatosBautismo).filter(
            DatosBautismo.catequizando_id == data['catequizando_id']
        ).first()
        
        if existing:
            raise ValidationException("El catequizando ya tiene datos de bautismo registrados")
        
        # Validar fechas
        if data.get('fecha_bautismo'):
            if data['fecha_bautismo'] > date.today():
                raise ValidationException("La fecha de bautismo no puede ser futura")
            
            if catequizando.fecha_nacimiento and data['fecha_bautismo'] < catequizando.fecha_nacimiento:
                raise ValidationException("La fecha de bautismo no puede ser anterior al nacimiento")
        
        # Configuraciones por defecto
        data.setdefault('validado', False)
        data.setdefault('requiere_verificacion', True)
        
        return data
    
    def validar_datos_bautismales(self, datos_id: int, validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos bautismales.
        
        Args:
            datos_id: ID de los datos de bautismo
            validation_data: Datos de validación
            
        Returns:
            Dict con confirmación de validación
        """
        try:
            schema = ValidacionBautismalSchema()
            validated_data = schema.load(validation_data)
            
            datos = self._get_instance_by_id(datos_id)
            
            # Actualizar validación
            datos.validado = True
            datos.fecha_validacion = datetime.utcnow()
            datos.validado_por = self.current_user.get('id') if self.current_user else None
            datos.observaciones_validacion = validated_data.get('observaciones')
            datos.requiere_verificacion = False
            datos.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Datos bautismales validados para catequizando {datos.catequizando_id}")
            
            return {
                'success': True,
                'fecha_validacion': datos.fecha_validacion.isoformat(),
                'mensaje': 'Datos bautismales validados exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error validando datos bautismales: {str(e)}")
            raise BusinessLogicException("Error validando datos bautismales")
    
    def get_pendientes_validacion(self, parroquia_id: int = None) -> List[Dict[str, Any]]:
        """Obtiene datos bautismales pendientes de validación."""
        try:
            query = self.db.query(DatosBautismo).filter(
                DatosBautismo.validado == False
            ).options(joinedload(DatosBautismo.catequizando))
            
            if parroquia_id:
                query = query.join(Catequizando).filter(
                    Catequizando.parroquia_id == parroquia_id
                )
            
            datos = query.order_by(DatosBautismo.created_at).all()
            
            return [self._serialize_response(d) for d in datos]
            
        except Exception as e:
            logger.error(f"Error obteniendo pendientes: {str(e)}")
            raise BusinessLogicException("Error obteniendo datos pendientes")