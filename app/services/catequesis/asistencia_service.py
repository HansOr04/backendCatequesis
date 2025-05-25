"""
Servicio de gestión de asistencia a clases de catequesis.
Maneja registro, control y estadísticas de asistencia.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.services.base_service import BaseService
from app.models.catequesis.asistencia_model import Asistencia
from app.models.catequesis.inscripcion_model import Inscripcion
from app.models.catequesis.grupo_model import Grupo
from app.schemas.catequesis.asistencia_schema import (
    AsistenciaCreateSchema, AsistenciaUpdateSchema, AsistenciaResponseSchema,
    AsistenciaSearchSchema, RegistroMasivoSchema
)
from app.core.exceptions import (
    ValidationException, NotFoundException, BusinessLogicException
)
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class AsistenciaService(BaseService):
    """Servicio para gestión de asistencia."""
    
    @property
    def model(self) -> Type[Asistencia]:
        return Asistencia
    
    @property
    def create_schema(self) -> Type[AsistenciaCreateSchema]:
        return AsistenciaCreateSchema
    
    @property
    def update_schema(self) -> Type[AsistenciaUpdateSchema]:
        return AsistenciaUpdateSchema
    
    @property
    def response_schema(self) -> Type[AsistenciaResponseSchema]:
        return AsistenciaResponseSchema
    
    @property
    def search_schema(self) -> Type[AsistenciaSearchSchema]:
        return AsistenciaSearchSchema
    
    def _build_base_query(self, **kwargs):
        """Construye query base con joins necesarios."""
        return self.db.query(self.model).options(
            joinedload(Asistencia.inscripcion).joinedload(Inscripcion.catequizando),
            joinedload(Asistencia.inscripcion).joinedload(Inscripcion.grupo),
            joinedload(Asistencia.created_by_user)
        )
    
    @require_permission('asistencia', 'registrar')
    def registrar_asistencia_masiva(self, registro_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra asistencia masiva para un grupo en una fecha específica.
        
        Args:
            registro_data: Datos del registro masivo
            
        Returns:
            Dict con resultados del registro
        """
        try:
            schema = RegistroMasivoSchema()
            validated_data = schema.load(registro_data)
            
            grupo_id = validated_data['grupo_id']
            fecha_clase = validated_data['fecha_clase']
            asistencias = validated_data['asistencias']  # [{'inscripcion_id', 'presente', 'observaciones'}]
            
            # Verificar que el grupo existe
            grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
            if not grupo:
                raise NotFoundException("Grupo no encontrado")
            
            # Verificar que no exista registro para esta fecha
            existing = self.db.query(Asistencia).join(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo_id,
                    Asistencia.fecha_clase == fecha_clase
                )
            ).first()
            
            if existing:
                raise ValidationException("Ya existe registro de asistencia para esta fecha")
            
            registros_creados = 0
            errores = []
            
            for asistencia_data in asistencias:
                try:
                    inscripcion_id = asistencia_data['inscripcion_id']
                    
                    # Verificar que la inscripción pertenece al grupo
                    inscripcion = self.db.query(Inscripcion).filter(
                        and_(
                            Inscripcion.id == inscripcion_id,
                            Inscripcion.grupo_id == grupo_id,
                            Inscripcion.estado.in_(['activa', 'en_progreso'])
                        )
                    ).first()
                    
                    if not inscripcion:
                        errores.append(f"Inscripción {inscripcion_id} no válida para el grupo")
                        continue
                    
                    # Crear registro de asistencia
                    asistencia = Asistencia(
                        inscripcion_id=inscripcion_id,
                        fecha_clase=fecha_clase,
                        presente=asistencia_data['presente'],
                        tardanza=asistencia_data.get('tardanza', False),
                        justificada=asistencia_data.get('justificada', False),
                        observaciones=asistencia_data.get('observaciones'),
                        created_at=datetime.utcnow(),
                        created_by=self.current_user.get('id') if self.current_user else None
                    )
                    
                    self.db.add(asistencia)
                    registros_creados += 1
                    
                except Exception as e:
                    errores.append(f"Error con inscripción {asistencia_data.get('inscripcion_id')}: {str(e)}")
            
            self.db.commit()
            
            logger.info(f"Asistencia masiva registrada: {registros_creados} registros para grupo {grupo_id}")
            
            return {
                'success': True,
                'registros_creados': registros_creados,
                'total_intentos': len(asistencias),
                'grupo_id': grupo_id,
                'fecha_clase': fecha_clase.isoformat(),
                'errores': errores
            }
            
        except ValidationException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en registro masivo: {str(e)}")
            raise BusinessLogicException("Error en registro masivo de asistencia")
    
    def get_reporte_asistencia_grupo(self, grupo_id: int, fecha_inicio: date = None, fecha_fin: date = None) -> Dict[str, Any]:
        """
        Genera reporte de asistencia para un grupo.
        
        Args:
            grupo_id: ID del grupo
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            
        Returns:
            Dict con reporte de asistencia
        """
        try:
            if not fecha_inicio:
                fecha_inicio = date.today() - timedelta(days=30)
            if not fecha_fin:
                fecha_fin = date.today()
            
            # Obtener inscripciones del grupo
            inscripciones = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo_id,
                    Inscripcion.estado.in_(['activa', 'en_progreso', 'completado'])
                )
            ).options(joinedload(Inscripcion.catequizando)).all()
            
            # Obtener asistencias del período
            asistencias = self.db.query(Asistencia).join(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo_id,
                    Asistencia.fecha_clase >= fecha_inicio,
                    Asistencia.fecha_clase <= fecha_fin
                )
            ).all()
            
            # Organizar datos por catequizando
            reporte = []
            for inscripcion in inscripciones:
                asistencias_catequizando = [a for a in asistencias if a.inscripcion_id == inscripcion.id]
                
                total_clases = len(set(a.fecha_clase for a in asistencias))
                asistencias_presente = sum(1 for a in asistencias_catequizando if a.presente)
                tardanzas = sum(1 for a in asistencias_catequizando if a.tardanza)
                faltas_justificadas = sum(1 for a in asistencias_catequizando if not a.presente and a.justificada)
                
                porcentaje_asistencia = (asistencias_presente / total_clases * 100) if total_clases > 0 else 0
                
                reporte.append({
                    'catequizando': {
                        'id': inscripcion.catequizando.id,
                        'nombres': inscripcion.catequizando.nombres,
                        'apellidos': inscripcion.catequizando.apellidos
                    },
                    'total_clases': total_clases,
                    'asistencias': asistencias_presente,
                    'faltas': total_clases - asistencias_presente,
                    'tardanzas': tardanzas,
                    'faltas_justificadas': faltas_justificadas,
                    'porcentaje_asistencia': round(porcentaje_asistencia, 1)
                })
            
            # Estadísticas generales
            if reporte:
                promedio_asistencia = sum(r['porcentaje_asistencia'] for r in reporte) / len(reporte)
                mejor_asistencia = max(reporte, key=lambda x: x['porcentaje_asistencia'])
            else:
                promedio_asistencia = 0
                mejor_asistencia = None
            
            return {
                'grupo_id': grupo_id,
                'periodo': {
                    'fecha_inicio': fecha_inicio.isoformat(),
                    'fecha_fin': fecha_fin.isoformat()
                },
                'estadisticas_generales': {
                    'total_catequizandos': len(inscripciones),
                    'promedio_asistencia': round(promedio_asistencia, 1),
                    'mejor_asistencia': mejor_asistencia
                },
                'detalle_por_catequizando': reporte
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte: {str(e)}")
            raise BusinessLogicException("Error generando reporte de asistencia")