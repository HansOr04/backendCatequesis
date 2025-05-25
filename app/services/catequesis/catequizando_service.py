"""
Servicio de gestión de catequizandos.
Maneja CRUD de catequizandos, historial, progreso y documentación.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text

from app.services.base_service import BaseService
from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.representante_model import Representante
from app.models.catequesis.inscripcion_model import Inscripcion
from app.models.catequesis.datos_bautismo_model import DatosBautismo
from app.models.catequesis.documento_model import Documento
from app.schemas.catequesis.catequizando_schema import (
    CatequizandoCreateSchema, CatequizandoUpdateSchema, CatequizandoResponseSchema,
    CatequizandoSearchSchema, HistorialCatequizandoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
from app.utils.document_processor import process_document
from app.utils.image_processor import process_photo
import logging

logger = logging.getLogger(__name__)


class CatequizandoService(BaseService):
    """Servicio para gestión completa de catequizandos."""
    
    @property
    def model(self) -> Type[Catequizando]:
        return Catequizando
    
    @property
    def create_schema(self) -> Type[CatequizandoCreateSchema]:
        return CatequizandoCreateSchema
    
    @property
    def update_schema(self) -> Type[CatequizandoUpdateSchema]:
        return CatequizandoUpdateSchema
    
    @property
    def response_schema(self) -> Type[CatequizandoResponseSchema]:
        return CatequizandoResponseSchema
    
    @property
    def search_schema(self) -> Type[CatequizandoSearchSchema]:
        return CatequizandoSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Catequizando.parroquia),
            joinedload(Catequizando.representantes),
            joinedload(Catequizando.datos_bautismo),
            joinedload(Catequizando.documentos),
            joinedload(Catequizando.inscripciones).joinedload(Inscripcion.nivel),
            joinedload(Catequizando.created_by_user),
            joinedload(Catequizando.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para catequizandos."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Catequizando.nombres.ilike(search_term),
                    Catequizando.apellidos.ilike(search_term),
                    Catequizando.numero_documento.ilike(search_term),
                    Catequizando.telefono.ilike(search_term),
                    Catequizando.email.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('activo') is not None:
            query = query.filter(Catequizando.activo == search_data['activo'])
        
        if search_data.get('parroquia_id'):
            query = query.filter(Catequizando.parroquia_id == search_data['parroquia_id'])
        
        if search_data.get('tipo_documento'):
            query = query.filter(Catequizando.tipo_documento == search_data['tipo_documento'])
        
        if search_data.get('numero_documento'):
            query = query.filter(Catequizando.numero_documento == search_data['numero_documento'])
        
        # Filtros de edad
        if search_data.get('edad_minima') or search_data.get('edad_maxima'):
            today = date.today()
            
            if search_data.get('edad_minima'):
                max_birth_date = today.replace(year=today.year - search_data['edad_minima'])
                query = query.filter(Catequizando.fecha_nacimiento <= max_birth_date)
            
            if search_data.get('edad_maxima'):
                min_birth_date = today.replace(year=today.year - search_data['edad_maxima'] - 1)
                query = query.filter(Catequizando.fecha_nacimiento >= min_birth_date)
        
        # Filtros de fecha
        if search_data.get('registrado_desde'):
            query = query.filter(Catequizando.created_at >= search_data['registrado_desde'])
        
        if search_data.get('registrado_hasta'):
            query = query.filter(Catequizando.created_at <= search_data['registrado_hasta'])
        
        # Filtros de estado
        if search_data.get('con_documentos_pendientes'):
            query = query.join(Documento).filter(Documento.estado == 'pendiente')
        
        if search_data.get('con_inscripciones_activas'):
            query = query.join(Inscripcion).filter(
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        
        if search_data.get('nivel_actual_id'):
            query = query.join(Inscripcion).filter(
                and_(
                    Inscripcion.nivel_id == search_data['nivel_actual_id'],
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            )
        
        return query
    
    @require_permission('catequizandos', 'crear')
    def _before_create(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-creación para validaciones adicionales."""
        # Verificar documento único
        if self._exists_document(data['tipo_documento'], data['numero_documento']):
            raise ValidationException("Ya existe un catequizando con ese documento")
        
        # Validar edad mínima
        if data.get('fecha_nacimiento'):
            edad = self._calculate_age(data['fecha_nacimiento'])
            if edad < 3:  # Edad mínima configurable
                raise ValidationException("La edad mínima para catequesis es 3 años")
        
        # Generar código único si no se proporciona
        if not data.get('codigo_catequizando'):
            data['codigo_catequizando'] = self._generate_unique_code()
        
        # Configuraciones por defecto
        data.setdefault('activo', True)
        data.setdefault('estado_documentos', 'pendiente')
        
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
                    raise ValidationException("Ya existe un catequizando con ese documento")
        
        return data
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar el catequizando."""
        # Verificar dependencias
        dependencies = self._check_catequizando_dependencies(instance.id)
        if dependencies:
            raise BusinessLogicException(f"No se puede eliminar. Tiene dependencias: {', '.join(dependencies)}")
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE CATEQUIZANDOS
    # ==========================================
    
    def get_catequizando_completo(self, catequizando_id: int) -> Dict[str, Any]:
        """
        Obtiene información completa de un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            
        Returns:
            Dict con información completa
        """
        try:
            catequizando = self._get_instance_by_id(catequizando_id)
            
            # Información básica
            result = self._serialize_response(catequizando)
            
            # Historial de inscripciones
            result['historial_inscripciones'] = self._get_historial_inscripciones(catequizando_id)
            
            # Progreso actual
            result['progreso_actual'] = self._get_progreso_actual(catequizando_id)
            
            # Documentos
            result['documentos'] = self._get_documentos_catequizando(catequizando_id)
            
            # Representantes
            result['representantes'] = self._get_representantes_catequizando(catequizando_id)
            
            # Estadísticas personales
            result['estadisticas'] = self._get_estadisticas_catequizando(catequizando_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo catequizando completo: {str(e)}")
            raise BusinessLogicException("Error obteniendo información del catequizando")
    
    def inscribir_en_nivel(self, catequizando_id: int, inscripcion_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inscribe un catequizando en un nivel específico.
        
        Args:
            catequizando_id: ID del catequizando
            inscripcion_data: Datos de la inscripción
            
        Returns:
            Dict con la inscripción creada
        """
        try:
            catequizando = self._get_instance_by_id(catequizando_id)
            
            # Validar que puede inscribirse en el nivel
            self._validate_nivel_inscription(catequizando, inscripcion_data['nivel_id'])
            
            # Verificar que no tenga inscripción activa en el mismo nivel
            existing_inscription = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.catequizando_id == catequizando_id,
                    Inscripcion.nivel_id == inscripcion_data['nivel_id'],
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).first()
            
            if existing_inscription:
                raise ValidationException("Ya tiene una inscripción activa en este nivel")
            
            # Crear inscripción
            from app.services.catequesis.inscripcion_service import InscripcionService
            inscripcion_service = InscripcionService(self.db, self.current_user)
            
            inscripcion_data['catequizando_id'] = catequizando_id
            inscripcion = inscripcion_service.create(inscripcion_data)
            
            logger.info(f"Catequizando {catequizando_id} inscrito en nivel {inscripcion_data['nivel_id']}")
            
            return inscripcion
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error inscribiendo catequizando: {str(e)}")
            raise BusinessLogicException("Error inscribiendo catequizando")
    
    @require_permission('catequizandos', 'administrar')
    def transferir_parroquia(self, catequizando_id: int, nueva_parroquia_id: int, observaciones: str = None) -> Dict[str, Any]:
        """
        Transfiere un catequizando a otra parroquia.
        
        Args:
            catequizando_id: ID del catequizando
            nueva_parroquia_id: ID de la nueva parroquia
            observaciones: Observaciones de la transferencia
            
        Returns:
            Dict con confirmación
        """
        try:
            catequizando = self._get_instance_by_id(catequizando_id)
            
            # Verificar que la nueva parroquia existe y está activa
            from app.models.parroquias.parroquia_model import Parroquia
            nueva_parroquia = self.db.query(Parroquia).filter(
                and_(Parroquia.id == nueva_parroquia_id, Parroquia.activa == True)
            ).first()
            
            if not nueva_parroquia:
                raise NotFoundException("Parroquia de destino no encontrada o inactiva")
            
            # Guardar parroquia anterior
            parroquia_anterior_id = catequizando.parroquia_id
            
            # Realizar transferencia
            catequizando.parroquia_id = nueva_parroquia_id
            catequizando.fecha_transferencia = datetime.utcnow()
            catequizando.updated_at = datetime.utcnow()
            
            # Registrar transferencia en historial
            self._registrar_transferencia(
                catequizando_id, parroquia_anterior_id, nueva_parroquia_id, observaciones
            )
            
            # Suspender inscripciones activas en la parroquia anterior
            self._suspend_active_inscriptions(catequizando_id, 'transferencia')
            
            self.db.commit()
            
            logger.info(f"Catequizando {catequizando_id} transferido a parroquia {nueva_parroquia_id}")
            
            return {
                'success': True,
                'parroquia_anterior_id': parroquia_anterior_id,
                'parroquia_nueva_id': nueva_parroquia_id,
                'fecha_transferencia': catequizando.fecha_transferencia.isoformat(),
                'message': 'Transferencia realizada exitosamente'
            }
            
        except (NotFoundException, ValidationException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en transferencia: {str(e)}")
            raise BusinessLogicException("Error realizando transferencia")
    
    def upload_documento(self, catequizando_id: int, documento_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sube un documento para un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            documento_data: Datos del documento
            
        Returns:
            Dict con el documento creado
        """
        try:
            catequizando = self._get_instance_by_id(catequizando_id)
            
            # Procesar archivo
            if 'archivo' in documento_data:
                file_info = process_document(
                    documento_data['archivo'], 
                    f"catequizando_{catequizando_id}"
                )
                documento_data.update(file_info)
                del documento_data['archivo']
            
            # Crear documento
            documento_data['catequizando_id'] = catequizando_id
            documento = Documento(**documento_data)
            documento.created_at = datetime.utcnow()
            documento.created_by = self.current_user.get('id') if self.current_user else None
            
            self.db.add(documento)
            
            # Actualizar estado de documentos del catequizando si es necesario
            self._update_documents_status(catequizando_id)
            
            self.db.commit()
            
            logger.info(f"Documento {documento.tipo_documento} subido para catequizando {catequizando_id}")
            
            return self._serialize_documento(documento)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error subiendo documento: {str(e)}")
            raise BusinessLogicException("Error subiendo documento")
    
    def update_foto_perfil(self, catequizando_id: int, foto_file) -> Dict[str, Any]:
        """
        Actualiza la foto de perfil de un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            foto_file: Archivo de foto
            
        Returns:
            Dict con URL de la nueva foto
        """
        try:
            catequizando = self._get_instance_by_id(catequizando_id)
            
            # Procesar imagen
            foto_info = process_photo(foto_file, f"catequizando_{catequizando_id}")
            
            # Actualizar catequizando
            catequizando.url_foto = foto_info['url']
            catequizando.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                'success': True,
                'url_foto': foto_info['url'],
                'message': 'Foto actualizada exitosamente'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error actualizando foto: {str(e)}")
            raise BusinessLogicException("Error actualizando foto de perfil")
    
    @require_permission('catequizandos', 'administrar')
    def toggle_activation(self, catequizando_id: int, motivo: str = None) -> Dict[str, Any]:
        """
        Activa o desactiva un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            motivo: Motivo del cambio de estado
            
        Returns:
            Dict con el nuevo estado
        """
        try:
            catequizando = self._get_instance_by_id(catequizando_id)
            
            # Cambiar estado
            new_state = not catequizando.activo
            catequizando.activo = new_state
            catequizando.updated_at = datetime.utcnow()
            
            # Si se desactiva, suspender inscripciones activas
            if not new_state:
                self._suspend_active_inscriptions(catequizando_id, motivo or 'desactivacion')
            
            # Registrar cambio en historial
            self._registrar_cambio_estado(catequizando_id, new_state, motivo)
            
            self.db.commit()
            
            action = "activado" if new_state else "desactivado"
            logger.info(f"Catequizando {catequizando_id} {action}")
            
            return {
                'success': True,
                'activo': new_state,
                'message': f'Catequizando {action} exitosamente'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando estado: {str(e)}")
            raise BusinessLogicException("Error cambiando estado del catequizando")
    
    def get_catequizandos_by_edad(self, edad_minima: int, edad_maxima: int, parroquia_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtiene catequizandos por rango de edad.
        
        Args:
            edad_minima: Edad mínima
            edad_maxima: Edad máxima
            parroquia_id: ID de parroquia (opcional)
            
        Returns:
            Lista de catequizandos
        """
        try:
            today = date.today()
            max_birth_date = today.replace(year=today.year - edad_minima)
            min_birth_date = today.replace(year=today.year - edad_maxima - 1)
            
            query = self.db.query(Catequizando).filter(
                and_(
                    Catequizando.activo == True,
                    Catequizando.fecha_nacimiento >= min_birth_date,
                    Catequizando.fecha_nacimiento <= max_birth_date
                )
            )
            
            if parroquia_id:
                query = query.filter(Catequizando.parroquia_id == parroquia_id)
            
            catequizandos = query.order_by(Catequizando.nombres, Catequizando.apellidos).all()
            
            return [self._serialize_response(c) for c in catequizandos]
            
        except Exception as e:
            logger.error(f"Error obteniendo catequizandos por edad: {str(e)}")
            raise BusinessLogicException("Error obteniendo catequizandos")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de catequizandos."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de catequizandos
            total_catequizandos = self.db.query(Catequizando).count()
            catequizandos_activos = self.db.query(Catequizando).filter(Catequizando.activo == True).count()
            
            # Distribución por género
            genero_distribution = self.db.query(
                Catequizando.genero, func.count(Catequizando.id)
            ).filter(
                Catequizando.activo == True
            ).group_by(Catequizando.genero).all()
            
            # Distribución por edad
            today = date.today()
            edad_ranges = [
                ('0-6', 0, 6),
                ('7-12', 7, 12),
                ('13-17', 13, 17),
                ('18+', 18, 100)
            ]
            
            edad_distribution = {}
            for range_name, min_age, max_age in edad_ranges:
                max_birth = today.replace(year=today.year - min_age)
                min_birth = today.replace(year=today.year - max_age - 1)
                
                count = self.db.query(Catequizando).filter(
                    and_(
                        Catequizando.activo == True,
                        Catequizando.fecha_nacimiento >= min_birth,
                        Catequizando.fecha_nacimiento <= max_birth
                    )
                ).count()
                
                edad_distribution[range_name] = count
            
            # Estado de documentos
            documentos_stats = self.db.query(
                Catequizando.estado_documentos, func.count(Catequizando.id)
            ).filter(
                Catequizando.activo == True
            ).group_by(Catequizando.estado_documentos).all()
            
            # Inscripciones activas
            with_active_inscriptions = self.db.query(Catequizando).join(Inscripcion).filter(
                and_(
                    Catequizando.activo == True,
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).distinct().count()
            
            base_stats.update({
                'total_catequizandos': total_catequizandos,
                'catequizandos_activos': catequizandos_activos,
                'catequizandos_inactivos': total_catequizandos - catequizandos_activos,
                'distribucion_genero': {genero: count for genero, count in genero_distribution},
                'distribucion_edad': edad_distribution,
                'estado_documentos': {estado: count for estado, count in documentos_stats},
                'con_inscripciones_activas': with_active_inscriptions,
                'sin_inscripciones_activas': catequizandos_activos - with_active_inscriptions,
                'tasa_inscripcion_activa': round((with_active_inscriptions / catequizandos_activos) * 100, 1) if catequizandos_activos > 0 else 0
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de catequizandos: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _exists_document(self, tipo_documento: str, numero_documento: str, exclude_id: int = None) -> bool:
        """Verifica si existe un catequizando con el mismo documento."""
        query = self.db.query(Catequizando).filter(
            and_(
                Catequizando.tipo_documento == tipo_documento,
                Catequizando.numero_documento == numero_documento
            )
        )
        
        if exclude_id:
            query = query.filter(Catequizando.id != exclude_id)
        
        return query.first() is not None
    
    def _generate_unique_code(self) -> str:
        """Genera un código único para el catequizando."""
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not self.db.query(Catequizando).filter(Catequizando.codigo_catequizando == code).first():
                return code
    
    def _calculate_age(self, fecha_nacimiento: date) -> int:
        """Calcula la edad en años."""
        if not fecha_nacimiento:
            return 0
        
        today = date.today()
        return today.year - fecha_nacimiento.year - (
            (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
    
    def _validate_nivel_inscription(self, catequizando: Catequizando, nivel_id: int):
        """Valida que el catequizando puede inscribirse en el nivel."""
        from app.models.catequesis.nivel_model import Nivel
        
        nivel = self.db.query(Nivel).filter(Nivel.id == nivel_id).first()
        if not nivel:
            raise NotFoundException("Nivel no encontrado")
        
        if not nivel.activo:
            raise ValidationException("El nivel no está activo")
        
        # Verificar edad
        edad = self._calculate_age(catequizando.fecha_nacimiento)
        if nivel.edad_minima and edad < nivel.edad_minima:
            raise ValidationException(f"Edad mínima requerida: {nivel.edad_minima} años")
        
        if nivel.edad_maxima and edad > nivel.edad_maxima:
            raise ValidationException(f"Edad máxima permitida: {nivel.edad_maxima} años")
        
        # Verificar prerequisitos si los hay
        if nivel.prerequisito_nivel_id:
            completed_prerequisite = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.catequizando_id == catequizando.id,
                    Inscripcion.nivel_id == nivel.prerequisito_nivel_id,
                    Inscripcion.estado == 'completado'
                )
            ).first()
            
            if not completed_prerequisite:
                raise ValidationException("Debe completar el nivel prerequisito")
    
    def _get_historial_inscripciones(self, catequizando_id: int) -> List[Dict[str, Any]]:
        """Obtiene el historial de inscripciones del catequizando."""
        inscripciones = self.db.query(Inscripcion).filter(
            Inscripcion.catequizando_id == catequizando_id
        ).order_by(Inscripcion.created_at.desc()).all()
        
        return [self._serialize_inscripcion(insc) for insc in inscripciones]
    
    def _get_progreso_actual(self, catequizando_id: int) -> Dict[str, Any]:
        """Obtiene el progreso actual del catequizando."""
        # Inscripción activa
        inscripcion_activa = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.catequizando_id == catequizando_id,
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).first()
        
        if not inscripcion_activa:
            return {'tiene_inscripcion_activa': False}
        
        # Calcular progreso
        from app.models.catequesis.asistencia_model import Asistencia
        
        total_clases = inscripcion_activa.total_clases_requeridas or 0
        asistencias = self.db.query(Asistencia).filter(
            and_(
                Asistencia.inscripcion_id == inscripcion_activa.id,
                Asistencia.presente == True
            )
        ).count()
        
        progreso_pct = (asistencias / total_clases * 100) if total_clases > 0 else 0
        
        return {
            'tiene_inscripcion_activa': True,
            'nivel_actual': inscripcion_activa.nivel.nombre if inscripcion_activa.nivel else None,
            'fecha_inicio': inscripcion_activa.fecha_inicio.isoformat() if inscripcion_activa.fecha_inicio else None,
            'progreso_porcentaje': round(progreso_pct, 1),
            'clases_asistidas': asistencias,
            'total_clases': total_clases,
            'estado': inscripcion_activa.estado
        }
    
    def _get_documentos_catequizando(self, catequizando_id: int) -> List[Dict[str, Any]]:
        """Obtiene los documentos del catequizando."""
        documentos = self.db.query(Documento).filter(
            Documento.catequizando_id == catequizando_id
        ).order_by(Documento.created_at.desc()).all()
        
        return [self._serialize_documento(doc) for doc in documentos]
    
    def _get_representantes_catequizando(self, catequizando_id: int) -> List[Dict[str, Any]]:
        """Obtiene los representantes del catequizando."""
        representantes = self.db.query(Representante).filter(
            Representante.catequizando_id == catequizando_id
        ).all()
        
        return [self._serialize_representante(rep) for rep in representantes]
    
    def _get_estadisticas_catequizando(self, catequizando_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas personales del catequizando."""
        # Total de inscripciones
        total_inscripciones = self.db.query(Inscripcion).filter(
            Inscripcion.catequizando_id == catequizando_id
        ).count()
        
        # Inscripciones completadas
        completadas = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.catequizando_id == catequizando_id,
                Inscripcion.estado == 'completado'
            )
        ).count()
        
        # Tiempo en el sistema
        catequizando = self.db.query(Catequizando).filter(Catequizando.id == catequizando_id).first()
        tiempo_sistema = (datetime.utcnow() - catequizando.created_at).days if catequizando else 0
        
        return {
            'total_inscripciones': total_inscripciones,
            'inscripciones_completadas': completadas,
            'tasa_completion': round((completadas / total_inscripciones * 100), 1) if total_inscripciones > 0 else 0,
            'dias_en_sistema': tiempo_sistema,
            'años_en_sistema': round(tiempo_sistema / 365, 1)
        }
    
    def _check_catequizando_dependencies(self, catequizando_id: int) -> List[str]:
        """Verifica dependencias del catequizando antes de eliminar."""
        dependencies = []
        
        # Verificar inscripciones
        inscripciones_count = self.db.query(Inscripcion).filter(
            Inscripcion.catequizando_id == catequizando_id
        ).count()
        if inscripciones_count > 0:
            dependencies.append(f'{inscripciones_count} inscripciones')
        
        # Verificar documentos
        documentos_count = self.db.query(Documento).filter(
            Documento.catequizando_id == catequizando_id
        ).count()
        if documentos_count > 0:
            dependencies.append(f'{documentos_count} documentos')
        
        return dependencies
    
    def _suspend_active_inscriptions(self, catequizando_id: int, motivo: str):
        """Suspende las inscripciones activas del catequizando."""
        self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.catequizando_id == catequizando_id,
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).update({
            'estado': 'suspendida',
            'fecha_suspension': datetime.utcnow(),
            'motivo_suspension': motivo,
            'updated_at': datetime.utcnow()
        })
    
    def _update_documents_status(self, catequizando_id: int):
        """Actualiza el estado general de documentos del catequizando."""
        # Contar documentos por estado
        documentos_pendientes = self.db.query(Documento).filter(
            and_(
                Documento.catequizando_id == catequizando_id,
                Documento.estado == 'pendiente'
            )
        ).count()
        
        documentos_aprobados = self.db.query(Documento).filter(
            and_(
                Documento.catequizando_id == catequizando_id,
                Documento.estado == 'aprobado'
            )
        ).count()
        
        # Determinar estado general
        if documentos_pendientes > 0:
            estado_general = 'pendiente'
        elif documentos_aprobados > 0:
            estado_general = 'completo'
        else:
            estado_general = 'pendiente'
        
        # Actualizar catequizando
        self.db.query(Catequizando).filter(Catequizando.id == catequizando_id).update({
            'estado_documentos': estado_general,
            'updated_at': datetime.utcnow()
        })
    
    def _registrar_transferencia(self, catequizando_id: int, parroquia_anterior_id: int, 
                                parroquia_nueva_id: int, observaciones: str):
        """Registra una transferencia en el historial."""
        # Implementar registro en tabla de historial o log
        pass
    
    def _registrar_cambio_estado(self, catequizando_id: int, nuevo_estado: bool, motivo: str):
        """Registra un cambio de estado en el historial."""
        # Implementar registro en tabla de historial o log
        pass
    
    def _serialize_inscripcion(self, inscripcion: Inscripcion) -> Dict[str, Any]:
        """Serializa una inscripción."""
        return {
            'id': inscripcion.id,
            'nivel_nombre': inscripcion.nivel.nombre if inscripcion.nivel else None,
            'fecha_inicio': inscripcion.fecha_inicio.isoformat() if inscripcion.fecha_inicio else None,
            'fecha_fin': inscripcion.fecha_fin.isoformat() if inscripcion.fecha_fin else None,
            'estado': inscripcion.estado,
            'created_at': inscripcion.created_at.isoformat() if inscripcion.created_at else None
        }
    
    def _serialize_documento(self, documento: Documento) -> Dict[str, Any]:
        """Serializa un documento."""
        return {
            'id': documento.id,
            'tipo_documento': documento.tipo_documento,
            'nombre_archivo': documento.nombre_archivo,
            'url_archivo': documento.url_archivo,
            'estado': documento.estado,
            'observaciones': documento.observaciones,
            'created_at': documento.created_at.isoformat() if documento.created_at else None
        }
    
    def _serialize_representante(self, representante: Representante) -> Dict[str, Any]:
        """Serializa un representante."""
        return {
            'id': representante.id,
            'nombres': representante.nombres,
            'apellidos': representante.apellidos,
            'tipo_representante': representante.tipo_representante,
            'telefono': representante.telefono,
            'email': representante.email,
            'es_contacto_principal': representante.es_contacto_principal,
            'created_at': representante.created_at.isoformat() if representante.created_at else None
        }