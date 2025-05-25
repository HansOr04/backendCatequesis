"""
Servicio de gestión de padrinos de catequizandos.
Maneja CRUD de padrinos, validaciones sacramentales y certificaciones.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.padrino_model import Padrino
from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.sacramento_model import Sacramento
from app.schemas.catequesis.padrino_schema import (
    PadrinoCreateSchema, PadrinoUpdateSchema, PadrinoResponseSchema,
    PadrinoSearchSchema, ValidacionSacramentalSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class PadrinoService(BaseService):
    """Servicio para gestión completa de padrinos."""
    
    @property
    def model(self) -> Type[Padrino]:
        return Padrino
    
    @property
    def create_schema(self) -> Type[PadrinoCreateSchema]:
        return PadrinoCreateSchema
    
    @property
    def update_schema(self) -> Type[PadrinoUpdateSchema]:
        return PadrinoUpdateSchema
    
    @property
    def response_schema(self) -> Type[PadrinoResponseSchema]:
        return PadrinoResponseSchema
    
    @property
    def search_schema(self) -> Type[PadrinoSearchSchema]:
        return PadrinoSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Padrino.catequizando),
            joinedload(Padrino.sacramento),
            joinedload(Padrino.parroquia_bautismo),
            joinedload(Padrino.created_by_user),
            joinedload(Padrino.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para padrinos."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Padrino.nombres.ilike(search_term),
                    Padrino.apellidos.ilike(search_term),
                    Padrino.numero_documento.ilike(search_term),
                    Padrino.telefono.ilike(search_term),
                    Padrino.email.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('catequizando_id'):
            query = query.filter(Padrino.catequizando_id == search_data['catequizando_id'])
        
        if search_data.get('sacramento_id'):
            query = query.filter(Padrino.sacramento_id == search_data['sacramento_id'])
        
        if search_data.get('tipo_padrino'):
            query = query.filter(Padrino.tipo_padrino == search_data['tipo_padrino'])
        
        if search_data.get('tipo_documento'):
            query = query.filter(Padrino.tipo_documento == search_data['tipo_documento'])
        
        if search_data.get('numero_documento'):
            query = query.filter(Padrino.numero_documento == search_data['numero_documento'])
        
        if search_data.get('validado_sacramentalmente') is not None:
            query = query.filter(Padrino.validado_sacramentalmente == search_data['validado_sacramentalmente'])
        
        if search_data.get('activo') is not None:
            query = query.filter(Padrino.activo == search_data['activo'])
        
        # Filtros de parroquia
        if search_data.get('parroquia_bautismo_id'):
            query = query.filter(Padrino.parroquia_bautismo_id == search_data['parroquia_bautismo_id'])
        
        # Filtros por catequizando
        if search_data.get('parroquia_catequizando_id'):
            query = query.join(Catequizando).filter(
                Catequizando.parroquia_id == search_data['parroquia_catequizando_id']
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
        
        # Verificar que el sacramento existe
        if data.get('sacramento_id'):
            sacramento = self.db.query(Sacramento).filter(
                Sacramento.id == data['sacramento_id']
            ).first()
            
            if not sacramento:
                raise NotFoundException("Sacramento no encontrado")
        
        # Verificar documento único por catequizando y sacramento
        if self._exists_padrino_for_sacramento(
            data['catequizando_id'], 
            data.get('sacramento_id'), 
            data['numero_documento']
        ):
            raise ValidationException("Ya existe un padrino con ese documento para este sacramento")
        
        # Validar límite de padrinos por sacramento
        self._validate_padrino_limit(data['catequizando_id'], data.get('sacramento_id'), data['tipo_padrino'])
        
        # Validar edad mínima para ser padrino
        if data.get('fecha_nacimiento'):
            self._validate_age_requirement(data['fecha_nacimiento'])
        
        # Configuraciones por defecto
        data.setdefault('activo', True)
        data.setdefault('validado_sacramentalmente', False)
        data.setdefault('es_catolico_practicante', True)
        
        return data
    
    @require_permission('catequizandos', 'actualizar')
    def _before_update(self, instance, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Hook pre-actualización para validaciones."""
        # Verificar documento único (si cambió)
        if ('tipo_documento' in data or 'numero_documento' in data):
            tipo_doc = data.get('tipo_documento', instance.tipo_documento)
            numero_doc = data.get('numero_documento', instance.numero_documento)
            
            if (tipo_doc != instance.tipo_documento or numero_doc != instance.numero_documento):
                if self._exists_padrino_for_sacramento(
                    instance.catequizando_id, 
                    instance.sacramento_id, 
                    numero_doc, 
                    exclude_id=instance.id
                ):
                    raise ValidationException("Ya existe un padrino con ese documento para este sacramento")
        
        return data
    
    def _validate_delete(self, instance, **kwargs):
        """Validar que se puede eliminar el padrino."""
        # Verificar si hay certificados emitidos que referencien este padrino
        # (implementar según modelo de certificados)
        pass
    
    # ==========================================
    # OPERACIONES ESPECÍFICAS DE PADRINOS
    # ==========================================
    
    def get_padrinos_catequizando(self, catequizando_id: int, sacramento_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtiene los padrinos de un catequizando, opcionalmente filtrados por sacramento.
        
        Args:
            catequizando_id: ID del catequizando
            sacramento_id: ID del sacramento (opcional)
            
        Returns:
            Lista de padrinos
        """
        try:
            query = self.db.query(Padrino).filter(
                and_(
                    Padrino.catequizando_id == catequizando_id,
                    Padrino.activo == True
                )
            )
            
            if sacramento_id:
                query = query.filter(Padrino.sacramento_id == sacramento_id)
            
            padrinos = query.order_by(
                Padrino.tipo_padrino, Padrino.nombres
            ).all()
            
            return [self._serialize_response(p) for p in padrinos]
            
        except Exception as e:
            logger.error(f"Error obteniendo padrinos: {str(e)}")
            raise BusinessLogicException("Error obteniendo padrinos del catequizando")
    
    @require_permission('catequizandos', 'administrar')
    def validar_sacramentalmente(self, padrino_id: int, validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida sacramentalmente a un padrino.
        
        Args:
            padrino_id: ID del padrino
            validation_data: Datos de validación
            
        Returns:
            Dict con confirmación de validación
        """
        try:
            schema = ValidacionSacramentalSchema()
            validated_data = schema.load(validation_data)
            
            padrino = self._get_instance_by_id(padrino_id)
            
            # Actualizar datos de validación
            padrino.validado_sacramentalmente = True
            padrino.fecha_validacion = datetime.utcnow()
            padrino.validado_por = self.current_user.get('id') if self.current_user else None
            
            # Actualizar datos sacramentales
            if validated_data.get('fecha_bautismo'):
                padrino.fecha_bautismo = validated_data['fecha_bautismo']
            
            if validated_data.get('parroquia_bautismo_id'):
                padrino.parroquia_bautismo_id = validated_data['parroquia_bautismo_id']
            
            if validated_data.get('fecha_confirmacion'):
                padrino.fecha_confirmacion = validated_data['fecha_confirmacion']
                padrino.esta_confirmado = True
            
            if validated_data.get('observaciones_validacion'):
                padrino.observaciones_validacion = validated_data['observaciones_validacion']
            
            padrino.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Padrino {padrino_id} validado sacramentalmente")
            
            return {
                'success': True,
                'fecha_validacion': padrino.fecha_validacion.isoformat(),
                'mensaje': 'Padrino validado sacramentalmente exitosamente'
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error validando padrino: {str(e)}")
            raise BusinessLogicException("Error validando padrino sacramentalmente")
    
    def verificar_capacidad_madrinazgo(self, padrino_id: int) -> Dict[str, Any]:
        """
        Verifica la capacidad de madrinazgo de un padrino.
        
        Args:
            padrino_id: ID del padrino
            
        Returns:
            Dict con información de capacidad
        """
        try:
            padrino = self._get_instance_by_id(padrino_id)
            
            # Verificar edad mínima
            edad_valida = True
            if padrino.fecha_nacimiento:
                edad = self._calculate_age(padrino.fecha_nacimiento)
                edad_valida = edad >= 16  # Edad mínima canónica
            
            # Verificar estado sacramental
            sacramentos_validos = padrino.validado_sacramentalmente and padrino.esta_confirmado
            
            # Contar madrinazgos activos
            madrinazgos_activos = self.db.query(Padrino).filter(
                and_(
                    Padrino.numero_documento == padrino.numero_documento,
                    Padrino.activo == True,
                    Padrino.id != padrino.id
                )
            ).count()
            
            # Verificar límite de madrinazgos (máximo recomendado: 3-5)
            limite_madrinazgos = madrinazgos_activos < 5
            
            capacidad_completa = edad_valida and sacramentos_validos and limite_madrinazgos
            
            return {
                'puede_ser_padrino': capacidad_completa,
                'edad_valida': edad_valida,
                'sacramentos_validos': sacramentos_validos,
                'limite_madrinazgos_ok': limite_madrinazgos,
                'madrinazgos_activos': madrinazgos_activos,
                'observaciones': self._get_capacity_observations(edad_valida, sacramentos_validos, limite_madrinazgos)
            }
            
        except Exception as e:
            logger.error(f"Error verificando capacidad: {str(e)}")
            raise BusinessLogicException("Error verificando capacidad de madrinazgo")
    
    def find_padrinos_by_documento(self, tipo_documento: str, numero_documento: str) -> List[Dict[str, Any]]:
        """
        Busca padrinos por documento de identidad.
        
        Args:
            tipo_documento: Tipo de documento
            numero_documento: Número de documento
            
        Returns:
            Lista de padrinos encontrados
        """
        try:
            padrinos = self.db.query(Padrino).filter(
                and_(
                    Padrino.tipo_documento == tipo_documento,
                    Padrino.numero_documento == numero_documento,
                    Padrino.activo == True
                )
            ).options(
                joinedload(Padrino.catequizando),
                joinedload(Padrino.sacramento)
            ).all()
            
            return [self._serialize_with_context(p) for p in padrinos]
            
        except Exception as e:
            logger.error(f"Error buscando por documento: {str(e)}")
            raise BusinessLogicException("Error buscando padrinos")
    
    def asignar_padrino_multiple(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asigna un padrino existente a múltiples catequizandos.
        
        Args:
            assignment_data: Datos de asignación múltiple
            
        Returns:
            Dict con resultado de asignaciones
        """
        try:
            padrino_base_id = assignment_data['padrino_base_id']
            asignaciones = assignment_data['asignaciones']  # [{'catequizando_id', 'sacramento_id', 'tipo_padrino'}]
            
            # Obtener padrino base
            padrino_base = self._get_instance_by_id(padrino_base_id)
            
            # Verificar capacidad del padrino
            capacidad = self.verificar_capacidad_madrinazgo(padrino_base_id)
            if not capacidad['puede_ser_padrino']:
                raise ValidationException("El padrino no cumple con los requisitos para nuevas asignaciones")
            
            asignaciones_creadas = []
            errores = []
            
            for asignacion in asignaciones:
                try:
                    catequizando_id = asignacion['catequizando_id']
                    sacramento_id = asignacion['sacramento_id']
                    tipo_padrino = asignacion['tipo_padrino']
                    
                    # Verificar que no exista ya
                    if self._exists_padrino_for_sacramento(catequizando_id, sacramento_id, padrino_base.numero_documento):
                        errores.append(f"Ya es padrino del catequizando {catequizando_id}")
                        continue
                    
                    # Crear nueva asignación
                    nuevo_padrino = Padrino(
                        catequizando_id=catequizando_id,
                        sacramento_id=sacramento_id,
                        tipo_padrino=tipo_padrino,
                        nombres=padrino_base.nombres,
                        apellidos=padrino_base.apellidos,
                        tipo_documento=padrino_base.tipo_documento,
                        numero_documento=padrino_base.numero_documento,
                        fecha_nacimiento=padrino_base.fecha_nacimiento,
                        telefono=padrino_base.telefono,
                        email=padrino_base.email,
                        direccion=padrino_base.direccion,
                        fecha_bautismo=padrino_base.fecha_bautismo,
                        parroquia_bautismo_id=padrino_base.parroquia_bautismo_id,
                        fecha_confirmacion=padrino_base.fecha_confirmacion,
                        esta_confirmado=padrino_base.esta_confirmado,
                        es_catolico_practicante=padrino_base.es_catolico_practicante,
                        validado_sacramentalmente=padrino_base.validado_sacramentalmente,
                        activo=True,
                        created_at=datetime.utcnow(),
                        created_by=self.current_user.get('id') if self.current_user else None
                    )
                    
                    self.db.add(nuevo_padrino)
                    asignaciones_creadas.append({
                        'catequizando_id': catequizando_id,
                        'sacramento_id': sacramento_id,
                        'tipo_padrino': tipo_padrino
                    })
                    
                except Exception as e:
                    errores.append(f"Error con catequizando {asignacion.get('catequizando_id')}: {str(e)}")
            
            self.db.commit()
            
            logger.info(f"Padrino asignado a {len(asignaciones_creadas)} catequizandos")
            
            return {
                'success': True,
                'asignaciones_creadas': len(asignaciones_creadas),
                'total_intentos': len(asignaciones),
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
    
    def get_padrinos_pendientes_validacion(self, parroquia_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtiene padrinos pendientes de validación sacramental.
        
        Args:
            parroquia_id: ID de parroquia (opcional)
            
        Returns:
            Lista de padrinos pendientes
        """
        try:
            query = self.db.query(Padrino).filter(
                and_(
                    Padrino.activo == True,
                    Padrino.validado_sacramentalmente == False
                )
            ).options(
                joinedload(Padrino.catequizando),
                joinedload(Padrino.sacramento)
            )
            
            if parroquia_id:
                query = query.join(Catequizando).filter(
                    Catequizando.parroquia_id == parroquia_id
                )
            
            padrinos = query.order_by(Padrino.created_at).all()
            
            return [self._serialize_with_context(p) for p in padrinos]
            
        except Exception as e:
            logger.error(f"Error obteniendo padrinos pendientes: {str(e)}")
            raise BusinessLogicException("Error obteniendo padrinos pendientes")
    
    @require_permission('catequizandos', 'administrar')
    def toggle_activation(self, padrino_id: int, motivo: str = None) -> Dict[str, Any]:
        """
        Activa o desactiva un padrino.
        
        Args:
            padrino_id: ID del padrino
            motivo: Motivo del cambio
            
        Returns:
            Dict con el nuevo estado
        """
        try:
            padrino = self._get_instance_by_id(padrino_id)
            
            # Cambiar estado
            new_state = not padrino.activo
            padrino.activo = new_state
            padrino.updated_at = datetime.utcnow()
            
            if motivo:
                padrino.observaciones = f"{padrino.observaciones or ''}\n{datetime.now().strftime('%Y-%m-%d')}: {motivo}".strip()
            
            self.db.commit()
            
            action = "activado" if new_state else "desactivado"
            logger.info(f"Padrino {padrino_id} {action}")
            
            return {
                'success': True,
                'activo': new_state,
                'mensaje': f'Padrino {action} exitosamente'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando estado: {str(e)}")
            raise BusinessLogicException("Error cambiando estado del padrino")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de padrinos."""
        try:
            base_stats = super().get_statistics(**kwargs)
            
            # Estadísticas adicionales específicas de padrinos
            total_padrinos = self.db.query(Padrino).count()
            padrinos_activos = self.db.query(Padrino).filter(Padrino.activo == True).count()
            
            # Distribución por tipo
            tipo_distribution = self.db.query(
                Padrino.tipo_padrino, func.count(Padrino.id)
            ).filter(
                Padrino.activo == True
            ).group_by(Padrino.tipo_padrino).all()
            
            # Padrinos validados vs pendientes
            validados = self.db.query(Padrino).filter(
                and_(
                    Padrino.activo == True,
                    Padrino.validado_sacramentalmente == True
                )
            ).count()
            
            pendientes_validacion = padrinos_activos - validados
            
            # Distribución por sacramento
            sacramento_distribution = self.db.query(
                Sacramento.nombre, func.count(Padrino.id)
            ).join(Padrino).filter(
                Padrino.activo == True
            ).group_by(Sacramento.id, Sacramento.nombre).all()
            
            # Padrinos con múltiples madrinazgos
            multiples_madrinazgos = self.db.query(
                Padrino.numero_documento
            ).filter(
                Padrino.activo == True
            ).group_by(
                Padrino.numero_documento
            ).having(
                func.count(Padrino.id) > 1
            ).count()
            
            # Promedio de edad de padrinos
            edad_promedio = self.db.query(
                func.avg(func.extract('year', func.age(func.current_date(), Padrino.fecha_nacimiento)))
            ).filter(
                and_(
                    Padrino.activo == True,
                    Padrino.fecha_nacimiento.isnot(None)
                )
            ).scalar() or 0
            
            base_stats.update({
                'total_padrinos': total_padrinos,
                'padrinos_activos': padrinos_activos,
                'padrinos_inactivos': total_padrinos - padrinos_activos,
                'distribucion_tipos': {tipo: count for tipo, count in tipo_distribution},
                'padrinos_validados': validados,
                'pendientes_validacion': pendientes_validacion,
                'tasa_validacion': round((validados / padrinos_activos) * 100, 1) if padrinos_activos > 0 else 0,
                'distribucion_sacramentos': {sacramento: count for sacramento, count in sacramento_distribution},
                'padrinos_multiples_madrinazgos': multiples_madrinazgos,
                'edad_promedio_padrinos': round(edad_promedio, 1)
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de padrinos: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _exists_padrino_for_sacramento(self, catequizando_id: int, sacramento_id: int, numero_documento: str, exclude_id: int = None) -> bool:
        """Verifica si existe un padrino con el mismo documento para un sacramento específico."""
        query = self.db.query(Padrino).filter(
            and_(
                Padrino.catequizando_id == catequizando_id,
                Padrino.sacramento_id == sacramento_id,
                Padrino.numero_documento == numero_documento,
                Padrino.activo == True
            )
        )
        
        if exclude_id:
            query = query.filter(Padrino.id != exclude_id)
        
        return query.first() is not None
    
    def _validate_padrino_limit(self, catequizando_id: int, sacramento_id: int, tipo_padrino: str):
        """Valida el límite de padrinos por sacramento."""
        # Contar padrinos existentes del mismo tipo para este sacramento
        existing_count = self.db.query(Padrino).filter(
            and_(
                Padrino.catequizando_id == catequizando_id,
                Padrino.sacramento_id == sacramento_id,
                Padrino.tipo_padrino == tipo_padrino,
                Padrino.activo == True
            )
        ).count()
        
        # Límites según tipo de padrino
        limits = {
            'padrino': 1,
            'madrina': 1,
            'testigo': 2
        }
        
        max_allowed = limits.get(tipo_padrino, 1)
        
        if existing_count >= max_allowed:
            raise ValidationException(f"Ya se alcanzó el límite de {max_allowed} {tipo_padrino}(s) para este sacramento")
    
    def _validate_age_requirement(self, fecha_nacimiento: date):
        """Valida el requisito de edad mínima para ser padrino."""
        edad = self._calculate_age(fecha_nacimiento)
        if edad < 16:
            raise ValidationException("La edad mínima para ser padrino es 16 años")
    
    def _calculate_age(self, fecha_nacimiento: date) -> int:
        """Calcula la edad en años."""
        if not fecha_nacimiento:
            return 0
        
        today = date.today()
        return today.year - fecha_nacimiento.year - (
            (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
    
    def _get_capacity_observations(self, edad_valida: bool, sacramentos_validos: bool, limite_ok: bool) -> List[str]:
        """Obtiene observaciones sobre la capacidad del padrino."""
        observations = []
        
        if not edad_valida:
            observations.append("No cumple con la edad mínima requerida (16 años)")
        
        if not sacramentos_validos:
            observations.append("No está validado sacramentalmente o no está confirmado")
        
        if not limite_ok:
            observations.append("Ha alcanzado el límite recomendado de madrinazgos")
        
        if not observations:
            observations.append("Cumple con todos los requisitos para ser padrino")
        
        return observations
    
    def _serialize_with_context(self, padrino: Padrino) -> Dict[str, Any]:
        """Serializa padrino con información contextual."""
        result = self._serialize_response(padrino)
        
        # Agregar información del catequizando
        if padrino.catequizando:
            result['catequizando'] = {
                'id': padrino.catequizando.id,
                'nombres': padrino.catequizando.nombres,
                'apellidos': padrino.catequizando.apellidos,
                'codigo_catequizando': padrino.catequizando.codigo_catequizando
            }
        
        # Agregar información del sacramento
        if padrino.sacramento:
            result['sacramento'] = {
                'id': padrino.sacramento.id,
                'nombre': padrino.sacramento.nombre,
                'descripcion': padrino.sacramento.descripcion
            }
        
        # Agregar capacidad de madrinazgo
        try:
            capacidad = self.verificar_capacidad_madrinazgo(padrino.id)
            result['capacidad_madrinazgo'] = capacidad
        except:
            result['capacidad_madrinazgo'] = {'puede_ser_padrino': False, 'error': 'No se pudo verificar'}
        
        return result