"""
Servicio de gestión de catequistas.
Maneja CRUD de catequistas, asignaciones, formación y evaluaciones.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text

from app.services.base_service import BaseService
from app.models.seguridad.usuario_model import Usuario
from app.models.catequesis.grupo_model import Grupo
from app.models.catequesis.asistencia_model import Asistencia
from app.models.catequesis.formacion_catequista_model import FormacionCatequista
from app.schemas.catequesis.catequista_schema import (
    CatequistaCreateSchema, CatequistaUpdateSchema, CatequistaResponseSchema,
    CatequistaSearchSchema, AsignacionGrupoSchema, FormacionSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
from app.services.seguridad.usuario_service import UsuarioService
import logging

logger = logging.getLogger(__name__)


class CatequistaService(BaseService):
    """Servicio para gestión completa de catequistas."""
    
    @property
    def model(self) -> Type[Usuario]:
        return Usuario
    
    @property
    def create_schema(self) -> Type[CatequistaCreateSchema]:
        return CatequistaCreateSchema
    
    @property
    def update_schema(self) -> Type[CatequistaUpdateSchema]:
        return CatequistaUpdateSchema
    
    @property
    def response_schema(self) -> Type[CatequistaResponseSchema]:
        return CatequistaResponseSchema
    
    @property
    def search_schema(self) -> Type[CatequistaSearchSchema]:
        return CatequistaSearchSchema
    
    def __init__(self, db: Session = None, current_user: Dict = None):
        super().__init__(db, current_user)
        self.usuario_service = UsuarioService(db, current_user)
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios para catequistas."""
        from app.models.seguridad.rol_model import Rol
        from app.models.seguridad.usuario_rol_model import UsuarioRol
        
        return self.db.query(self.model).join(UsuarioRol).join(Rol).filter(
            Rol.nombre == 'catequista'
        ).options(
            joinedload(Usuario.parroquia),
            joinedload(Usuario.roles),
            joinedload(Usuario.grupos_asignados),
            joinedload(Usuario.formaciones_catequista),
            joinedload(Usuario.created_by_user),
            joinedload(Usuario.updated_by_user)
        )
    
    def _build_search_query(self, search_data: Dict[str, Any], **kwargs):
        """Construye query de búsqueda específica para catequistas."""
        query = self._build_base_query(**kwargs)
        
        # Búsqueda por texto general
        if search_data.get('query'):
            search_term = f"%{search_data['query']}%"
            query = query.filter(
                or_(
                    Usuario.nombres.ilike(search_term),
                    Usuario.apellidos.ilike(search_term),
                    Usuario.email.ilike(search_term),
                    Usuario.telefono.ilike(search_term),
                    Usuario.username.ilike(search_term)
                )
            )
        
        # Filtros específicos
        if search_data.get('activo') is not None:
            query = query.filter(Usuario.activo == search_data['activo'])
        
        if search_data.get('parroquia_id'):
            query = query.filter(Usuario.parroquia_id == search_data['parroquia_id'])
        
        if search_data.get('con_grupos_asignados'):
            query = query.join(Grupo).filter(Grupo.activo == True)
        
        if search_data.get('sin_grupos_asignados'):
            query = query.outerjoin(Grupo).filter(Grupo.id.is_(None))
        
        if search_data.get('nivel_formacion'):
            query = query.join(FormacionCatequista).filter(
                FormacionCatequista.nivel_formacion == search_data['nivel_formacion']
            )
        
        if search_data.get('certificado_vigente'):
            query = query.join(FormacionCatequista).filter(
                and_(
                    FormacionCatequista.certificado_vigente == True,
                    FormacionCatequista.fecha_vencimiento >= date.today()
                )
            )
        
        # Filtros de experiencia
        if search_data.get('experiencia_minima_años'):
            fecha_limite = date.today() - timedelta(days=search_data['experiencia_minima_años'] * 365)
            query = query.filter(Usuario.fecha_inicio_ministerio <= fecha_limite)
        
        # Filtros de disponibilidad
        if search_data.get('disponible_fines_semana'):
            query = query.filter(Usuario.disponible_fines_semana == True)
        
        if search_data.get('disponible_entre_semana'):
            query = query.filter(Usuario.disponible_entre_semana == True)
        
        return query
    
    @require_permission('catequistas', 'crear')
    def create_catequista(self, catequista_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo catequista.
        
        Args:
            catequista_data: Datos del catequista
            
        Returns:
            Dict con el catequista creado
        """
        try:
            # Validar datos específicos de catequista
            self._validate_catequista_data(catequista_data)
            
            # Crear usuario base
            usuario_data = {
                'nombres': catequista_data['nombres'],
                'apellidos': catequista_data['apellidos'],
                'email': catequista_data['email'],
                'telefono': catequista_data.get('telefono'),
                'parroquia_id': catequista_data['parroquia_id'],
                'fecha_nacimiento': catequista_data.get('fecha_nacimiento'),
                'direccion': catequista_data.get('direccion'),
                'activo': True
            }
            
            # Agregar campos específicos de catequista
            usuario_data.update({
                'fecha_inicio_ministerio': catequista_data.get('fecha_inicio_ministerio', date.today()),
                'disponible_fines_semana': catequista_data.get('disponible_fines_semana', True),
                'disponible_entre_semana': catequista_data.get('disponible_entre_semana', False),
                'nivel_estudios': catequista_data.get('nivel_estudios'),
                'profesion': catequista_data.get('profesion'),
                'experiencia_previa': catequista_data.get('experiencia_previa'),
                'motivacion': catequista_data.get('motivacion'),
                'observaciones': catequista_data.get('observaciones')
            })
            
            # Crear usuario con rol de catequista
            usuario = self.usuario_service.create(usuario_data, roles=['catequista'])
            
            # Registrar formación inicial si se proporciona
            if catequista_data.get('formacion_inicial'):
                self._registrar_formacion_inicial(usuario['id'], catequista_data['formacion_inicial'])
            
            logger.info(f"Catequista creado: {usuario['email']}")
            
            return self._serialize_catequista_response(usuario)
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error creando catequista: {str(e)}")
            raise BusinessLogicException("Error creando catequista")
    
    def get_catequista_completo(self, catequista_id: int) -> Dict[str, Any]:
        """
        Obtiene información completa de un catequista.
        
        Args:
            catequista_id: ID del catequista
            
        Returns:
            Dict con información completa
        """
        try:
            catequista = self._get_catequista_by_id(catequista_id)
            
            # Información básica
            result = self._serialize_response(catequista)
            
            # Grupos asignados
            result['grupos_asignados'] = self._get_grupos_asignados(catequista_id)
            
            # Historial de formación
            result['formacion'] = self._get_historial_formacion(catequista_id)
            
            # Estadísticas de desempeño
            result['estadisticas'] = self._get_estadisticas_catequista(catequista_id)
            
            # Evaluaciones
            result['evaluaciones'] = self._get_evaluaciones_catequista(catequista_id)
            
            # Disponibilidad y horarios
            result['disponibilidad'] = self._get_disponibilidad_catequista(catequista_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo catequista completo: {str(e)}")
            raise BusinessLogicException("Error obteniendo información del catequista")
    
    @require_permission('catequistas', 'administrar')
    def asignar_grupo(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asigna un catequista a un grupo.
        
        Args:
            assignment_data: Datos de asignación
            
        Returns:
            Dict con confirmación de asignación
        """
        try:
            schema = AsignacionGrupoSchema()
            validated_data = schema.load(assignment_data)
            
            catequista_id = validated_data['catequista_id']
            grupo_id = validated_data['grupo_id']
            es_responsable_principal = validated_data.get('es_responsable_principal', False)
            
            # Verificar que el catequista existe y está activo
            catequista = self._get_catequista_by_id(catequista_id)
            if not catequista.activo:
                raise ValidationException("El catequista no está activo")
            
            # Verificar que el grupo existe y está activo
            grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
            if not grupo:
                raise NotFoundException("Grupo no encontrado")
            if not grupo.activo:
                raise ValidationException("El grupo no está activo")
            
            # Verificar que el catequista y grupo pertenecen a la misma parroquia
            if catequista.parroquia_id != grupo.parroquia_id:
                raise ValidationException("El catequista y el grupo deben pertenecer a la misma parroquia")
            
            # Verificar que no esté ya asignado
            if grupo.catequista_principal_id == catequista_id or grupo.catequista_auxiliar_id == catequista_id:
                raise ValidationException("El catequista ya está asignado a este grupo")
            
            # Realizar asignación
            if es_responsable_principal:
                # Mover responsable actual a auxiliar si existe
                if grupo.catequista_principal_id:
                    grupo.catequista_auxiliar_id = grupo.catequista_principal_id
                grupo.catequista_principal_id = catequista_id
            else:
                if grupo.catequista_auxiliar_id:
                    raise ValidationException("El grupo ya tiene un catequista auxiliar asignado")
                grupo.catequista_auxiliar_id = catequista_id
            
            grupo.fecha_ultima_asignacion = datetime.utcnow()
            grupo.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            tipo_asignacion = "principal" if es_responsable_principal else "auxiliar"
            logger.info(f"Catequista {catequista_id} asignado como {tipo_asignacion} al grupo {grupo_id}")
            
            return {
                'success': True,
                'tipo_asignacion': tipo_asignacion,
                'grupo_nombre': grupo.nombre,
                'mensaje': f'Catequista asignado como {tipo_asignacion} exitosamente'
            }
            
        except (ValidationException, NotFoundException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error asignando grupo: {str(e)}")
            raise BusinessLogicException("Error asignando grupo al catequista")
    
    @require_permission('catequistas', 'administrar')
    def remover_grupo(self, catequista_id: int, grupo_id: int) -> Dict[str, Any]:
        """
        Remueve un catequista de un grupo.
        
        Args:
            catequista_id: ID del catequista
            grupo_id: ID del grupo
            
        Returns:
            Dict con confirmación
        """
        try:
            # Verificar que el grupo existe
            grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
            if not grupo:
                raise NotFoundException("Grupo no encontrado")
            
            # Verificar que el catequista está asignado al grupo
            tipo_remocion = None
            if grupo.catequista_principal_id == catequista_id:
                grupo.catequista_principal_id = None
                tipo_remocion = "principal"
                
                # Promover auxiliar a principal si existe
                if grupo.catequista_auxiliar_id:
                    grupo.catequista_principal_id = grupo.catequista_auxiliar_id
                    grupo.catequista_auxiliar_id = None
                    tipo_remocion += " (auxiliar promovido a principal)"
                    
            elif grupo.catequista_auxiliar_id == catequista_id:
                grupo.catequista_auxiliar_id = None
                tipo_remocion = "auxiliar"
            else:
                raise ValidationException("El catequista no está asignado a este grupo")
            
            grupo.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Catequista {catequista_id} removido del grupo {grupo_id} como {tipo_remocion}")
            
            return {
                'success': True,
                'tipo_remocion': tipo_remocion,
                'grupo_nombre': grupo.nombre,
                'mensaje': f'Catequista removido como {tipo_remocion} exitosamente'
            }
            
        except (ValidationException, NotFoundException):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removiendo grupo: {str(e)}")
            raise BusinessLogicException("Error removiendo grupo del catequista")
    
    def registrar_formacion(self, catequista_id: int, formacion_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra formación para un catequista.
        
        Args:
            catequista_id: ID del catequista
            formacion_data: Datos de la formación
            
        Returns:
            Dict con la formación registrada
        """
        try:
            schema = FormacionSchema()
            validated_data = schema.load(formacion_data)
            
            # Verificar que el catequista existe
            catequista = self._get_catequista_by_id(catequista_id)
            
            # Crear registro de formación
            formacion = FormacionCatequista(
                catequista_id=catequista_id,
                tipo_formacion=validated_data['tipo_formacion'],
                nombre_curso=validated_data['nombre_curso'],
                institucion=validated_data.get('institucion'),
                fecha_inicio=validated_data['fecha_inicio'],
                fecha_fin=validated_data.get('fecha_fin'),
                horas_formacion=validated_data.get('horas_formacion'),
                certificado_obtenido=validated_data.get('certificado_obtenido', False),
                calificacion=validated_data.get('calificacion'),
                observaciones=validated_data.get('observaciones'),
                created_at=datetime.utcnow(),
                created_by=self.current_user.get('id') if self.current_user else None
            )
            
            # Calcular fecha de vencimiento si es certificación
            if formacion.certificado_obtenido and validated_data.get('vigencia_años'):
                vigencia_años = validated_data['vigencia_años']
                formacion.fecha_vencimiento = formacion.fecha_fin.replace(
                    year=formacion.fecha_fin.year + vigencia_años
                ) if formacion.fecha_fin else None
                formacion.certificado_vigente = formacion.fecha_vencimiento >= date.today() if formacion.fecha_vencimiento else True
            
            self.db.add(formacion)
            
            # Actualizar nivel de formación del catequista si es mayor
            self._update_catequista_formation_level(catequista, validated_data.get('nivel_formacion'))
            
            self.db.commit()
            
            logger.info(f"Formación registrada para catequista {catequista_id}")
            
            return self._serialize_formacion(formacion)
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registrando formación: {str(e)}")
            raise BusinessLogicException("Error registrando formación")
    
    def get_catequistas_disponibles(self, filtros: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Obtiene catequistas disponibles para asignación.
        
        Args:
            filtros: Filtros adicionales
            
        Returns:
            Lista de catequistas disponibles
        """
        try:
            filtros = filtros or {}
            
            query = self._build_base_query()
            
            # Solo catequistas activos
            query = query.filter(Usuario.activo == True)
            
            # Filtrar por parroquia si se especifica
            if filtros.get('parroquia_id'):
                query = query.filter(Usuario.parroquia_id == filtros['parroquia_id'])
            
            # Filtrar por disponibilidad
            if filtros.get('disponibilidad_requerida'):
                disponibilidad = filtros['disponibilidad_requerida']
                if disponibilidad == 'fines_semana':
                    query = query.filter(Usuario.disponible_fines_semana == True)
                elif disponibilidad == 'entre_semana':
                    query = query.filter(Usuario.disponible_entre_semana == True)
            
            # Filtrar catequistas sin grupos o con capacidad
            if filtros.get('solo_sin_grupos'):
                query = query.outerjoin(Grupo, or_(
                    Grupo.catequista_principal_id == Usuario.id,
                    Grupo.catequista_auxiliar_id == Usuario.id
                )).filter(Grupo.id.is_(None))
            
            # Filtrar por nivel de formación mínimo
            if filtros.get('nivel_formacion_minimo'):
                query = query.join(FormacionCatequista).filter(
                    FormacionCatequista.nivel_formacion >= filtros['nivel_formacion_minimo']
                )
            
            catequistas = query.order_by(Usuario.nombres, Usuario.apellidos).all()
            
            # Agregar información de disponibilidad
            result = []
            for catequista in catequistas:
                catequista_data = self._serialize_response(catequista)
                catequista_data['grupos_actuales'] = self._count_grupos_asignados(catequista.id)
                catequista_data['capacidad_disponible'] = self._calculate_capacity(catequista.id)
                result.append(catequista_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo catequistas disponibles: {str(e)}")
            raise BusinessLogicException("Error obteniendo catequistas disponibles")
    
    def evaluar_desempeño(self, catequista_id: int, evaluacion_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra una evaluación de desempeño para un catequista.
        
        Args:
            catequista_id: ID del catequista
            evaluacion_data: Datos de la evaluación
            
        Returns:
            Dict con la evaluación registrada
        """
        try:
            catequista = self._get_catequista_by_id(catequista_id)
            
            # Crear registro de evaluación
            from app.models.catequesis.evaluacion_catequista_model import EvaluacionCatequista
            
            evaluacion = EvaluacionCatequista(
                catequista_id=catequista_id,
                periodo_evaluacion=evaluacion_data['periodo_evaluacion'],
                evaluador_id=self.current_user.get('id') if self.current_user else None,
                puntaje_conocimiento=evaluacion_data.get('puntaje_conocimiento'),
                puntaje_metodologia=evaluacion_data.get('puntaje_metodologia'),
                puntaje_relaciones=evaluacion_data.get('puntaje_relaciones'),
                puntaje_puntualidad=evaluacion_data.get('puntaje_puntualidad'),
                puntaje_general=evaluacion_data.get('puntaje_general'),
                fortalezas=evaluacion_data.get('fortalezas'),
                areas_mejora=evaluacion_data.get('areas_mejora'),
                recomendaciones=evaluacion_data.get('recomendaciones'),
                observaciones=evaluacion_data.get('observaciones'),
                created_at=datetime.utcnow()
            )
            
            self.db.add(evaluacion)
            self.db.commit()
            
            logger.info(f"Evaluación registrada para catequista {catequista_id}")
            
            return self._serialize_evaluacion(evaluacion)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registrando evaluación: {str(e)}")
            raise BusinessLogicException("Error registrando evaluación")
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de catequistas."""
        try:
            # Estadísticas básicas
            total_catequistas = self._build_base_query().count()
            catequistas_activos = self._build_base_query().filter(Usuario.activo == True).count()
            
            # Distribución por parroquia
            parroquia_distribution = self.db.query(
                Usuario.parroquia_id, func.count(Usuario.id)
            ).join(
                self._build_base_query().subquery(), Usuario.id == text('usuario_1.id')
            ).filter(
                Usuario.activo == True
            ).group_by(Usuario.parroquia_id).all()
            
            # Catequistas con grupos asignados
            with_groups = self.db.query(Usuario).join(
                self._build_base_query().subquery(), Usuario.id == text('usuario_1.id')
            ).join(Grupo, or_(
                Grupo.catequista_principal_id == Usuario.id,
                Grupo.catequista_auxiliar_id == Usuario.id
            )).filter(
                and_(Usuario.activo == True, Grupo.activo == True)
            ).distinct().count()
            
            # Distribución por nivel de formación
            formacion_distribution = self.db.query(
                FormacionCatequista.nivel_formacion, func.count(func.distinct(FormacionCatequista.catequista_id))
            ).join(Usuario).join(
                self._build_base_query().subquery(), Usuario.id == text('usuario_1.id')
            ).filter(
                Usuario.activo == True
            ).group_by(FormacionCatequista.nivel_formacion).all()
            
            # Experiencia promedio
            experiencia_stats = self.db.query(
                func.avg(func.extract('year', func.age(func.current_date(), Usuario.fecha_inicio_ministerio))).label('promedio'),
                func.min(func.extract('year', func.age(func.current_date(), Usuario.fecha_inicio_ministerio))).label('minimo'),
                func.max(func.extract('year', func.age(func.current_date(), Usuario.fecha_inicio_ministerio))).label('maximo')
            ).join(
                self._build_base_query().subquery(), Usuario.id == text('usuario_1.id')
            ).filter(
                and_(
                    Usuario.activo == True,
                    Usuario.fecha_inicio_ministerio.isnot(None)
                )
            ).first()
            
            return {
                'total_catequistas': total_catequistas,
                'catequistas_activos': catequistas_activos,
                'catequistas_inactivos': total_catequistas - catequistas_activos,
                'con_grupos_asignados': with_groups,
                'sin_grupos_asignados': catequistas_activos - with_groups,
                'tasa_asignacion_grupos': round((with_groups / catequistas_activos) * 100, 1) if catequistas_activos > 0 else 0,
                'distribucion_parroquias': {str(pid): count for pid, count in parroquia_distribution},
                'distribucion_formacion': {nivel: count for nivel, count in formacion_distribution},
                'experiencia_promedio_años': round(experiencia_stats.promedio, 1) if experiencia_stats and experiencia_stats.promedio else 0,
                'experiencia_minima_años': experiencia_stats.minimo if experiencia_stats else 0,
                'experiencia_maxima_años': experiencia_stats.maximo if experiencia_stats else 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de catequistas: {str(e)}")
            raise BusinessLogicException("Error obteniendo estadísticas")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _get_catequista_by_id(self, catequista_id: int) -> Usuario:
        """Obtiene un catequista por ID con validaciones."""
        catequista = self._build_base_query().filter(Usuario.id == catequista_id).first()
        if not catequista:
            raise NotFoundException("Catequista no encontrado")
        return catequista
    
    def _validate_catequista_data(self, data: Dict[str, Any]):
        """Valida datos específicos de catequista."""
        # Validar fecha de inicio de ministerio
        if data.get('fecha_inicio_ministerio'):
            if data['fecha_inicio_ministerio'] > date.today():
                raise ValidationException("La fecha de inicio de ministerio no puede ser futura")
        
        # Validar disponibilidad
        if not data.get('disponible_fines_semana') and not data.get('disponible_entre_semana'):
            raise ValidationException("Debe tener disponibilidad en al menos un período")
    
    def _registrar_formacion_inicial(self, catequista_id: int, formacion_data: Dict[str, Any]):
        """Registra la formación inicial de un catequista."""
        formacion = FormacionCatequista(
            catequista_id=catequista_id,
            tipo_formacion='inicial',
            nombre_curso=formacion_data.get('nombre_curso', 'Formación Inicial'),
            institucion=formacion_data.get('institucion'),
            fecha_inicio=formacion_data.get('fecha_inicio'),
            fecha_fin=formacion_data.get('fecha_fin'),
            certificado_obtenido=formacion_data.get('certificado_obtenido', True),
            nivel_formacion=formacion_data.get('nivel_formacion', 'basico'),
            created_at=datetime.utcnow()
        )
        
        self.db.add(formacion)
    
    def _update_catequista_formation_level(self, catequista: Usuario, nuevo_nivel: str):
        """Actualiza el nivel de formación del catequista si es mayor."""
        if not nuevo_nivel:
            return
        
        niveles_jerarquia = ['basico', 'intermedio', 'avanzado', 'especializado']
        
        nivel_actual_idx = niveles_jerarquia.index(catequista.nivel_formacion or 'basico')
        nuevo_nivel_idx = niveles_jerarquia.index(nuevo_nivel)
        
        if nuevo_nivel_idx > nivel_actual_idx:
            catequista.nivel_formacion = nuevo_nivel
            catequista.updated_at = datetime.utcnow()
    
    def _get_grupos_asignados(self, catequista_id: int) -> List[Dict[str, Any]]:
        """Obtiene los grupos asignados a un catequista."""
        grupos = self.db.query(Grupo).filter(
            or_(
                Grupo.catequista_principal_id == catequista_id,
                Grupo.catequista_auxiliar_id == catequista_id
            )
        ).all()
        
        result = []
        for grupo in grupos:
            grupo_data = {
                'id': grupo.id,
                'nombre': grupo.nombre,
                'nivel': grupo.nivel.nombre if grupo.nivel else None,
                'es_responsable_principal': grupo.catequista_principal_id == catequista_id,
                'activo': grupo.activo,
                'total_catequizandos': len(grupo.inscripciones) if grupo.inscripciones else 0
            }
            result.append(grupo_data)
        
        return result
    
    def _get_historial_formacion(self, catequista_id: int) -> List[Dict[str, Any]]:
        """Obtiene el historial de formación de un catequista."""
        formaciones = self.db.query(FormacionCatequista).filter(
            FormacionCatequista.catequista_id == catequista_id
        ).order_by(FormacionCatequista.fecha_inicio.desc()).all()
        
        return [self._serialize_formacion(f) for f in formaciones]
    
    def _get_estadisticas_catequista(self, catequista_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de un catequista."""
        # Total de grupos manejados
        total_grupos = self.db.query(Grupo).filter(
            or_(
                Grupo.catequista_principal_id == catequista_id,
                Grupo.catequista_auxiliar_id == catequista_id
            )
        ).count()
        
        # Grupos activos actuales
        grupos_activos = self.db.query(Grupo).filter(
            and_(
                or_(
                    Grupo.catequista_principal_id == catequista_id,
                    Grupo.catequista_auxiliar_id == catequista_id
                ),
                Grupo.activo == True
            )
        ).count()
        
        # Años de experiencia
        catequista = self.db.query(Usuario).filter(Usuario.id == catequista_id).first()
        años_experiencia = 0
        if catequista and catequista.fecha_inicio_ministerio:
            años_experiencia = (date.today() - catequista.fecha_inicio_ministerio).days / 365
        
        return {
            'total_grupos_manejados': total_grupos,
            'grupos_activos_actuales': grupos_activos,
            'años_experiencia': round(años_experiencia, 1),
            'nivel_formacion_actual': catequista.nivel_formacion if catequista else None
        }
    
    def _get_evaluaciones_catequista(self, catequista_id: int) -> List[Dict[str, Any]]:
        """Obtiene las evaluaciones de un catequista."""
        # Implementar cuando se tenga el modelo de evaluaciones
        return []
    
    def _get_disponibilidad_catequista(self, catequista_id: int) -> Dict[str, Any]:
        """Obtiene la disponibilidad de un catequista."""
        catequista = self.db.query(Usuario).filter(Usuario.id == catequista_id).first()
        
        if not catequista:
            return {}
        
        return {
            'disponible_fines_semana': catequista.disponible_fines_semana,
            'disponible_entre_semana': catequista.disponible_entre_semana,
            'observaciones_disponibilidad': catequista.observaciones
        }
    
    def _count_grupos_asignados(self, catequista_id: int) -> int:
        """Cuenta los grupos asignados a un catequista."""
        return self.db.query(Grupo).filter(
            and_(
                or_(
                    Grupo.catequista_principal_id == catequista_id,
                    Grupo.catequista_auxiliar_id == catequista_id
                ),
                Grupo.activo == True
            )
        ).count()
    
    def _calculate_capacity(self, catequista_id: int) -> Dict[str, Any]:
        """Calcula la capacidad disponible de un catequista."""
        grupos_actuales = self._count_grupos_asignados(catequista_id)
        max_grupos = 3  # Máximo recomendado de grupos por catequista
        
        return {
            'grupos_actuales': grupos_actuales,
            'maximo_recomendado': max_grupos,
            'capacidad_disponible': max_grupos - grupos_actuales,
            'puede_tomar_mas': grupos_actuales < max_grupos
        }
    
    def _serialize_catequista_response(self, usuario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Serializa respuesta específica para catequista."""
        # Convertir respuesta de usuario a respuesta de catequista
        catequista_data = usuario_data.copy()
        
        # Agregar información específica de catequista
        if isinstance(usuario_data, dict) and 'id' in usuario_data:
            catequista_id = usuario_data['id']
            catequista_data['grupos_asignados'] = self._get_grupos_asignados(catequista_id)
            catequista_data['formacion_actual'] = self._get_formacion_actual(catequista_id)
            catequista_data['capacidad'] = self._calculate_capacity(catequista_id)
        
        return catequista_data
    
    def _get_formacion_actual(self, catequista_id: int) -> Dict[str, Any]:
        """Obtiene la formación más reciente del catequista."""
        formacion = self.db.query(FormacionCatequista).filter(
            FormacionCatequista.catequista_id == catequista_id
        ).order_by(FormacionCatequista.fecha_fin.desc()).first()
        
        if not formacion:
            return {'nivel': 'sin_formacion', 'certificado_vigente': False}
        
        return {
            'nivel': formacion.nivel_formacion,
            'ultimo_curso': formacion.nombre_curso,
            'fecha_ultimo_curso': formacion.fecha_fin.isoformat() if formacion.fecha_fin else None,
            'certificado_vigente': formacion.certificado_vigente,
            'fecha_vencimiento': formacion.fecha_vencimiento.isoformat() if formacion.fecha_vencimiento else None
        }
    
    def _serialize_formacion(self, formacion: FormacionCatequista) -> Dict[str, Any]:
        """Serializa un registro de formación."""
        return {
            'id': formacion.id,
            'tipo_formacion': formacion.tipo_formacion,
            'nombre_curso': formacion.nombre_curso,
            'institucion': formacion.institucion,
            'fecha_inicio': formacion.fecha_inicio.isoformat() if formacion.fecha_inicio else None,
            'fecha_fin': formacion.fecha_fin.isoformat() if formacion.fecha_fin else None,
            'horas_formacion': formacion.horas_formacion,
            'certificado_obtenido': formacion.certificado_obtenido,
            'certificado_vigente': formacion.certificado_vigente,
            'fecha_vencimiento': formacion.fecha_vencimiento.isoformat() if formacion.fecha_vencimiento else None,
            'nivel_formacion': formacion.nivel_formacion,
            'calificacion': formacion.calificacion,
            'observaciones': formacion.observaciones,
            'created_at': formacion.created_at.isoformat() if formacion.created_at else None
        }
    
    def _serialize_evaluacion(self, evaluacion) -> Dict[str, Any]:
        """Serializa una evaluación de catequista."""
        return {
            'id': evaluacion.id,
            'periodo_evaluacion': evaluacion.periodo_evaluacion,
            'puntaje_conocimiento': evaluacion.puntaje_conocimiento,
            'puntaje_metodologia': evaluacion.puntaje_metodologia,
            'puntaje_relaciones': evaluacion.puntaje_relaciones,
            'puntaje_puntualidad': evaluacion.puntaje_puntualidad,
            'puntaje_general': evaluacion.puntaje_general,
            'fortalezas': evaluacion.fortalezas,
            'areas_mejora': evaluacion.areas_mejora,
            'recomendaciones': evaluacion.recomendaciones,
            'observaciones': evaluacion.observaciones,
            'created_at': evaluacion.created_at.isoformat() if evaluacion.created_at else None
        }