"""
Servicio de gestión de representantes de catequizandos.
Maneja CRUD de representantes, relaciones familiares y contactos.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.representante_model import Representante
from app.models.catequesis.catequizando_model import Catequizando
from app.schemas.catequesis.representante_schema import (
    RepresentanteCreateSchema, RepresentanteUpdateSchema, RepresentanteResponseSchema,
    RepresentanteSearchSchema, AsignacionRepresentanteSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class RepresentanteService(BaseService):
    """Servicio para gestión completa de representantes."""
    
    @property
    def model(self) -> Type[Representante]:
        return Representante
    
    @property
    def create_schema(self) -> Type[RepresentanteCreateSchema]:
        return RepresentanteCreateSchema
    
    @property
    def update_schema(self) -> Type[RepresentanteUpdateSchema]:
        return RepresentanteUpdateSchema
    
    @property
    def response_schema(self) -> Type[RepresentanteResponseSchema]:
        return RepresentanteResponseSchema
    
    @property
    def search_schema(self) -> Type[RepresentanteSearchSchema]:
        return RepresentanteSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Representante.catequizando),
            joinedload(Representante.created_by_user),
            joinedload(Representante.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para representantes."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Representante.nombres.ilike(search_term),
                    Representante.apellidos.ilike(search_term),
                    Representante.numero_documento.ilike(search_term),
                    Representante.telefono.ilike(search_term),
                    Representante.email.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('catequizando_id'):
            query = query.filter(Representante.catequizando_id == search_data['catequizando_id'])
        
        if search_data.get('tipo_representante'):
            query = query.filter(Representante.tipo_representante == search_data['tipo_representante'])
        
        if search_data.get('tipo_documento'):
            query = query.filter(Representante.tipo_documento == search_data['tipo_documento'])
        
        if search_data.get('numero_documento'):
            query = query.filter(Representante.numero_documento == search_data['numero_documento'])
        
        if search_data.get('es_contacto_principal') is not None:
            query = query.filter(Representante.es_contacto_principal == search_data['es_contacto_principal'])
        
        if search_data.get('activo') is not None:
            query = query.filter(Representante.activo == search_data['activo'])
        
        # Filtros de parroquia (a través del catequizando)
        if search_data.get('parroquia_id'):
            query = query.join(Catequizando).filter(
                Catequizando.parroquia_id == search_data['parroquia_id']
            )
        
        return query
    
    @require_permission('catequizandos', 'actualizar')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar que el catequizando existe
        catequizando = self.db.query(Catequizando).filter(
            Catequizando.id == data['catequizando_id']
        ).first()
        
        if not catequizando:
            raise NotFoundException("Catequizando no encontrado")
        
        # Verificar documento único (si se proporciona)
        if data.get('tipo_documento') and data.get('numero_documento'):
            if self._exists_document(data['tipo_documento'], data['numero_documento']):
                raise ValidationException("Ya existe un representante con ese documento")
        
        # Validar contacto principal único por catequizando
        if data.get('es_contacto_principal', False):
            self._ensure_single_primary_contact(data['catequizando_id'])
        
        # Configuraciones por defecto
        data.setdefault('activo', True)
        data.setdefault('es_contacto_principal', False)
        
        return data
    
    @require_permission('catequizandos', 'actualizar')
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-actualización para validaciones."""
        # Verificar documento único (si cambió)
        if ('tipo_documento' in data or 'numero_documento' in data):
            tipo_doc = data.get('tipo_documento', instance.tipo_documento)
            numero_doc = data.get('numero_documento', instance.numero_documento)
            
            if (tipo_doc != instance.tipo_documento or numero_doc != instance.numero_documento):
                if self._exists_document(tipo_doc, numero_doc, exclude_id=instance.id):
                    raise ValidationException("Ya existe un representante con ese documento")
        
        # Validar contacto principal único
        if data.get('es_contacto_principal', False) and not instance.es_contacto_principal:
            self._ensure_single_primary_contact(instance.catequizando_id, exclude_id=instance.id)
        
        return data
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar el representante."""
        # No permitir eliminar si es el único contacto principal
        if instance.es_contacto_principal:
            other_contacts = self.db.query(Representante).filter(
                and_(
                    Representante.catequizando_id == instance.catequizando_id,
                    Representante.id != instance.id,
                    Representante.activo == True
                )
            ).count()
            
            if other_contacts == 0:
                raise BusinessLogicException("No se puede eliminar. Es el único representante del catequizando")
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE REPRESENTANTES
    # ==========================================
    
    def get_representantes_catequizando(self, catequizando_id: int, solo_activos: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene todos los representantes de un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            solo_activos: Si solo incluir representantes activos
            
        Returns:
            Lista de representantes
        """
        try:
            query = self.db.query(Representante).filter(
                Representante.catequizando_id == catequizando_id
            )
            
            if solo_activos:
                query = query.filter(Representante.activo == True)
            
            representantes = query.order_by(
                Representante.es_contacto_principal.desc(),
                Representante.nombres
            ).all()
            
            return [self._serialize_response(r) for r in representantes]
            
        except Exception as e:
            logger.error(f"Error obteniendo representantes: {str(e)}")
            raise BusinessLogicException("Error obteniendo representantes del catequizando")
    
    def get_contacto_principal(self, catequizando_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene el contacto principal de un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            
        Returns:
            Dict con el contacto principal o None
        """
        try:
            contacto = self.db.query(Representante).filter(
                and_(
                    Representante.catequizando_id == catequizando_id,
                    Representante.es_contacto_principal == True,
                    Representante.activo == True
                )
            ).first()
            
            return self._serialize_response(contacto) if contacto else None
            
        except Exception as e:
            logger.error(f"Error obteniendo contacto principal: {str(e)}")
            raise BusinessLogicException("Error obteniendo contacto principal")
    
    @require_permission('catequizandos', 'administrar')
    def set_contacto_principal(self, representante_id: int) -> Dict[str, Any]:
        """
        Establece un representante como contacto principal.
        
        Args:
            representante_id: ID del representante
            
        Returns:
            Dict con confirmación
        """
        try:
            representante = self._get_instance_by_id(representante_id)
            
            if not representante.activo:
                raise ValidationException("No se puede establecer como principal un representante inactivo")
            
            # Remover contacto principal actual
            self.db.query(Representante).filter(
                and_(
                    Representante.catequizando_id == representante.catequizando_id,
                    Representante.es_contacto_principal == True
                )
            ).update({
                'es_contacto_principal': False,
                'updated_at': datetime.utcnow()
            })
            
            # Establecer nuevo contacto principal
            representante.es_contacto_principal = True
            representante.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Representante {representante_id} establecido como contacto principal")
            
            return {
                'success': True,
                'mensaje': 'Contacto principal actualizado exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error estableciendo contacto principal: {str(e)}")
            raise BusinessLogicException("Error estableciendo contacto principal")
    
    def asignar_representante_multiple(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asigna un representante existente a múltiples catequizandos.
        
        Args:
            assignment_data: Datos de asignación múltiple
            
        Returns:
            Dict con resultado de asignaciones
        """
        try:
            schema = AsignacionRepresentanteSchema()
            validated_data = schema.load(assignment_data)
            
            representante_base_id = validated_data['representante_base_id']
            catequizandos_ids = validated_data['catequizandos_ids']
            
            # Obtener representante base
            representante_base = self._get_instance_by_id(representante_base_id)
            
            # Verificar que los catequizandos existen
            catequizandos = self.db.query(Catequizando).filter(
                Catequizando.id.in_(catequizandos_ids)
            ).all()
            
            if len(catequizandos) != len(catequizandos_ids):
                raise ValidationException("Algunos catequizandos no fueron encontrados")
            
            asignaciones_creadas = []
            errores = []
            
            for catequizando in catequizandos:
                # Saltar si ya es representante de este catequizando
                if catequizando.id == representante_base.catequizando_id:
                    continue
                
                try:
                    # Verificar que no exista ya como representante
                    existing = self.db.query(Representante).filter(
                        and_(
                            Representante.catequizando_id == catequizando.id,
                            Representante.numero_documento == representante_base.numero_documento
                        )
                    ).first()
                    
                    if existing:
                        errores.append(f"Ya es representante de {catequizando.nombres} {catequizando.apellidos}")
                        continue
                    
                    # Crear nueva asignación
                    nuevo_representante = Representante(
                        catequizando_id=catequizando.id,
                        nombres=representante_base.nombres,
                        apellidos=representante_base.apellidos,
                        tipo_documento=representante_base.tipo_documento,
                        numero_documento=representante_base.numero_documento,
                        telefono=representante_base.telefono,
                        email=representante_base.email,
                        tipo_representante=representante_base.tipo_representante,
                        es_contacto_principal=False,  # Nunca principal en asignación múltiple
                        activo=True,
                        created_at=datetime.utcnow(),
                        created_by=self.current_user.get('id') if self.current_user else None
                    )
                    
                    self.db.add(nuevo_representante)
                    asignaciones_creadas.append({
                        'catequizando_id': catequizando.id,
                        'catequizando_nombre': f"{catequizando.nombres} {catequizando.apellidos}"
                    })
                    
                except Exception as e:
                    errores.append(f"Error con {catequizando.nombres} {catequizando.apellidos}: {str(e)}")
            
            self.db.commit()
            
            logger.info(f"Representante asignado a {len(asignaciones_creadas)} catequizandos")
            
            return {
                'success': True,
                'asignaciones_creadas': len(asignaciones_creadas),
                'total_intentos': len(catequizandos_ids),
                'detalles_asignaciones': asignaciones_creadas,
                'errores': errores
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en asignación múltiple: {str(e)}")
            raise BusinessLogicException("Error en asignación múltiple")
    
    def find_representantes_by_documento(self, tipo_documento: str, numero_documento: str) -> List[Dict[str, Any]]:
        """
        Busca representantes por documento de identidad.
        
        Args:
            tipo_documento: Tipo de documento
            numero_documento: Número de documento
            
        Returns:
            Lista de representantes encontrados
        """
        try:
            representantes = self.db.query(Representante).filter(
                and_(
                    Representante.tipo_documento == tipo_documento,
                    Representante.numero_documento == numero_documento,
                    Representante.activo == True
                )
            ).options(joinedload(Representante.catequizando)).all()
            
            return [self._serialize_with_catequizando(r) for r in representantes]
            
        except Exception as e:
            logger.error(f"Error buscando por documento: {str(e)}")
            raise BusinessLogicException("Error buscando representantes")
    
    @require_permission('catequizandos', 'administrar')
    def toggle_activation(self, representante_id: int) -> Dict[str, Any]:
        """
        Activa o desactiva un representante.
        
        Args:
            representante_id: ID del representante
            
        Returns:
            Dict con el nuevo estado
        """
        try:
            representante = self._get_instance_by_id(representante_id)
            
            # No permitir desactivar si es el único representante activo
            if representante.activo:
                other_active = self.db.query(Representante).filter(
                    and_(
                        Representante.catequizando_id == representante.catequizando_id,
                        Representante.id != representante.id,
                        Representante.activo == True
                    )
                ).count()
                
                if other_active == 0:
                    raise BusinessLogicException("No se puede desactivar. Es el único representante activo")
            
            # Cambiar estado
            new_state = not representante.activo
            representante.activo = new_state
            
            # Si se desactiva y era contacto principal, asignar a otro
            if not new_state and representante.es_contacto_principal:
                self._reassign_primary_contact(representante.catequizando_id, representante.id)
            
            representante.updated_at = datetime.utcnow()
            self.db.commit()
            
            action = "activado" if new_state else "desactivado"
            logger.info(f"Representante {representante_id} {action}")
            
            return {
                'success': True,
                'activo': new_state,
                'mensaje': f'Representante {action} exitosamente'
            }
            
        except BusinessLogicException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando estado: {str(e)}")
            raise BusinessLogicException("Error cambiando estado del representante")
    
    def get_representantes_con_multiples_catequizandos(self) -> List[Dict[str, Any]]:
        """
        Obtiene representantes que tienen múltiples catequizandos a cargo.
        
        Returns:
            Lista de representantes con conteo de catequizandos
        """
        try:
            # Query para representantes con múltiples asignaciones
            subquery = self.db.query(
                Representante.numero_documento,
                func.count(Representante.catequizando_id).label('total_catequizandos')
            ).filter(
                Representante.activo == True
            ).group_by(
                Representante.numero_documento
            ).having(
                func.count(Representante.catequizando_id) > 1
            ).subquery()
            
            representantes = self.db.query(Representante).join(
                subquery, Representante.numero_documento == subquery.c.numero_documento
            ).options(
                joinedload(Representante.catequizando)
            ).order_by(
                Representante.numero_documento, 
                Representante.nombres
            ).all()
            
            # Agrupar por documento
            grouped = {}
            for rep in representantes:
                doc_key = rep.numero_documento
                if doc_key not in grouped:
                    grouped[doc_key] = {
                        'numero_documento': rep.numero_documento,
                        'nombres': rep.nombres,
                        'apellidos': rep.apellidos,
                        'telefono': rep.telefono,
                        'email': rep.email,
                        'catequizandos': [],
                        'total_catequizandos': 0
                    }
                
                grouped[doc_key]['catequizandos'].append({
                    'id': rep.catequizando.id,
                    'nombres': rep.catequizando.nombres,
                    'apellidos': rep.catequizando.apellidos,
                    'es_contacto_principal': rep.es_contacto_principal
                })
                grouped[doc_key]['total_catequizandos'] += 1
            
            return list(grouped.values())
            
        except Exception as e:
            logger.error(f"Error obteniendo representantes múltiples: {str(e)}")
            raise BusinessLogicException("Error obteniendo representantes")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de representantes."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de representantes
            total_representantes = self.db.query(Representante).count()
            representantes_activos = self.db.query(Representante).filter(Representante.activo == True).count()
            
            # Distribución por tipo de representante
            tipo_distribution = self.db.query(
                Representante.tipo_representante, func.count(Representante.id)
            ).filter(
                Representante.activo == True
            ).group_by(Representante.tipo_representante).all()
            
            # Representantes que son contacto principal
            contactos_principales = self.db.query(Representante).filter(
                and_(
                    Representante.activo == True,
                    Representante.es_contacto_principal == True
                )
            ).count()
            
            # Representantes con múltiples catequizandos
            multiples_catequizandos = self.db.query(
                Representante.numero_documento
            ).filter(
                Representante.activo == True
            ).group_by(
                Representante.numero_documento
            ).having(
                func.count(Representante.catequizando_id) > 1
            ).count()
            
            # Catequizandos sin representantes
            catequizandos_sin_rep = self.db.query(Catequizando).outerjoin(Representante).filter(
                and_(
                    Catequizando.activo == True,
                    Representante.id.is_(None)
                )
            ).count()
            
            base_stats.update({
                'total_representantes': total_representantes,
                'representantes_activos': representantes_activos,
                'representantes_inactivos': total_representantes - representantes_activos,
                'distribucion_tipos': {tipo: count for tipo, count in tipo_distribution},
                'contactos_principales': contactos_principales,
                'representantes_multiples': multiples_catequizandos,
                'catequizandos_sin_representante': catequizandos_sin_rep,
                'promedio_catequizandos_por_representante': round(
                    representantes_activos / multiples_catequizandos if multiples_catequizandos > 0 else 1, 1
                )
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de representantes: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _exists_document(self, tipo_documento: str, numero_documento: str, exclude_id: int = None) -> bool:
        """Verifica si existe un representante con el mismo documento."""
        query = self.db.query(Representante).filter(
            and_(
                Representante.tipo_documento == tipo_documento,
                Representante.numero_documento == numero_documento
            )
        )
        
        if exclude_id:
            query = query.filter(Representante.id != exclude_id)
        
        return query.first() is not None
    
    def _ensure_single_primary_contact(self, catequizando_id: int, exclude_id: int = None):
        """Asegura que solo haya un contacto principal por catequizando."""
        query = self.db.query(Representante).filter(
            and_(
                Representante.catequizando_id == catequizando_id,
                Representante.es_contacto_principal == True,
                Representante.activo == True
            )
        )
        
        if exclude_id:
            query = query.filter(Representante.id != exclude_id)
        
        existing_primary = query.first()
        if existing_primary:
            # Remover contacto principal actual
            existing_primary.es_contacto_principal = False
            existing_primary.updated_at = datetime.utcnow()
    
    def _reassign_primary_contact(self, catequizando_id: int, exclude_id: int):
        """Reasigna el contacto principal cuando se desactiva el actual."""
        # Buscar otro representante activo para asignar como principal
        nuevo_principal = self.db.query(Representante).filter(
            and_(
                Representante.catequizando_id == catequizando_id,
                Representante.id != exclude_id,
                Representante.activo == True
            )
        ).first()
        
        if nuevo_principal:
            nuevo_principal.es_contacto_principal = True
            nuevo_principal.updated_at = datetime.utcnow()
            logger.info(f"Contacto principal reasignado a representante {nuevo_principal.id}")
    
    def _serialize_with_catequizando(self, representante: Representante) -> Dict[str, Any]:
        """Serializa representante con información del catequizando."""
        result = self._serialize_response(representante)
        
        if representante.catequizando:
            result['catequizando'] = {
                'id': representante.catequizando.id,
                'nombres': representante.catequizando.nombres,
                'apellidos': representante.catequizando.apellidos,
                'codigo_catequizando': representante.catequizando.codigo_catequizando,
                'activo': representante.catequizando.activo
            }
        
        return result