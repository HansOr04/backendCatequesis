"""
Servicio de gestión de relaciones entre entidades del sistema.
Maneja conexiones, dependencias y relaciones complejas.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from app.models.catequesis.catequizando_model import Catequizando
from app.models.catequesis.representante_model import Representante
from app.models.catequesis.padrino_model import Padrino
from app.models.catequesis.inscripcion_model import Inscripcion
from app.models.catequesis.grupo_model import Grupo
from app.models.seguridad.usuario_model import Usuario
from app.core.exceptions import BusinessLogicException
from app.services.seguridad.permission_service import require_permission
import logging

logger = logging.getLogger(__name__)


class RelacionesService:
    """Servicio para gestión de relaciones entre entidades."""
    
    def __init__(self, db: Session, current_user: Dict = None):
        self.db = db
        self.current_user = current_user
    
    # ==========================================
    # RELACIONES FAMILIARES
    # ==========================================
    
    def get_estructura_familiar(self, catequizando_id: int) -> Dict[str, Any]:
        """
        Obtiene la estructura familiar completa de un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            
        Returns:
            Dict con estructura familiar
        """
        try:
            catequizando = self.db.query(Catequizando).filter(
                Catequizando.id == catequizando_id
            ).first()
            
            if not catequizando:
                return {}
            
            # Representantes
            representantes = self.db.query(Representante).filter(
                and_(
                    Representante.catequizando_id == catequizando_id,
                    Representante.activo == True
                )
            ).all()
            
            # Padrinos
            padrinos = self.db.query(Padrino).filter(
                and_(
                    Padrino.catequizando_id == catequizando_id,
                    Padrino.activo == True
                )
            ).all()
            
            # Buscar hermanos (mismo documento de representantes)
            hermanos = []
            for rep in representantes:
                otros_catequizandos = self.db.query(Catequizando).join(Representante).filter(
                    and_(
                        Representante.numero_documento == rep.numero_documento,
                        Catequizando.id != catequizando_id,
                        Catequizando.activo == True
                    )
                ).all()
                
                for hermano in otros_catequizandos:
                    if not any(h['id'] == hermano.id for h in hermanos):
                        hermanos.append({
                            'id': hermano.id,
                            'nombres': hermano.nombres,
                            'apellidos': hermano.apellidos,
                            'fecha_nacimiento': hermano.fecha_nacimiento.isoformat() if hermano.fecha_nacimiento else None
                        })
            
            return {
                'catequizando': {
                    'id': catequizando.id,
                    'nombres': catequizando.nombres,
                    'apellidos': catequizando.apellidos,
                    'fecha_nacimiento': catequizando.fecha_nacimiento.isoformat() if catequizando.fecha_nacimiento else None
                },
                'representantes': [
                    {
                        'id': r.id,
                        'nombres': r.nombres,
                        'apellidos': r.apellidos,
                        'tipo_representante': r.tipo_representante,
                        'es_contacto_principal': r.es_contacto_principal,
                        'telefono': r.telefono,
                        'email': r.email
                    }
                    for r in representantes
                ],
                'padrinos': [
                    {
                        'id': p.id,
                        'nombres': p.nombres,
                        'apellidos': p.apellidos,
                        'tipo_padrino': p.tipo_padrino,
                        'sacramento': p.sacramento.nombre if p.sacramento else None,
                        'validado': p.validado_sacramentalmente
                    }
                    for p in padrinos
                ],
                'hermanos': hermanos,
                'total_familiares': len(representantes) + len(padrinos) + len(hermanos)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estructura familiar: {str(e)}")
            raise BusinessLogicException("Error obteniendo estructura familiar")
    
    # ==========================================
    # RELACIONES ACADÉMICAS
    # ==========================================
    
    def get_historial_academico(self, catequizando_id: int) -> Dict[str, Any]:
        """
        Obtiene el historial académico completo de un catequizando.
        
        Args:
            catequizando_id: ID del catequizando
            
        Returns:
            Dict con historial académico
        """
        try:
            # Inscripciones ordenadas cronológicamente
            inscripciones = self.db.query(Inscripcion).filter(
                Inscripcion.catequizando_id == catequizando_id
            ).order_by(Inscripcion.fecha_inscripcion).all()
            
            historial = []
            for inscripcion in inscripciones:
                # Asistencias para esta inscripción
                from app.models.catequesis.asistencia_model import Asistencia
                asistencias = self.db.query(Asistencia).filter(
                    Asistencia.inscripcion_id == inscripcion.id
                ).all()
                
                total_clases = len(asistencias)
                presentes = sum(1 for a in asistencias if a.presente)
                porcentaje_asistencia = (presentes / total_clases * 100) if total_clases > 0 else 0
                
                historial.append({
                    'inscripcion_id': inscripcion.id,
                    'nivel': inscripcion.nivel.nombre if inscripcion.nivel else None,
                    'grupo': inscripcion.grupo.nombre if inscripcion.grupo else None,
                    'programa': inscripcion.nivel.programa_catequesis.nombre if inscripcion.nivel and inscripcion.nivel.programa_catequesis else None,
                    'fecha_inicio': inscripcion.fecha_inscripcion.isoformat() if inscripcion.fecha_inscripcion else None,
                    'fecha_fin': inscripcion.fecha_finalizacion.isoformat() if inscripcion.fecha_finalizacion else None,
                    'estado': inscripcion.estado,
                    'calificacion_final': inscripcion.calificacion_final,
                    'total_clases': total_clases,
                    'clases_asistidas': presentes,
                    'porcentaje_asistencia': round(porcentaje_asistencia, 1),
                    'catequista': inscripcion.grupo.catequista_principal.nombres if inscripcion.grupo and inscripcion.grupo.catequista_principal else None
                })
            
            # Estadísticas generales
            total_inscripciones = len(inscripciones)
            completadas = sum(1 for i in inscripciones if i.estado == 'completado')
            en_progreso = sum(1 for i in inscripciones if i.estado in ['activa', 'en_progreso'])
            
            return {
                'catequizando_id': catequizando_id,
                'estadisticas': {
                    'total_inscripciones': total_inscripciones,
                    'completadas': completadas,
                    'en_progreso': en_progreso,
                    'tasa_completion': round((completadas / total_inscripciones * 100), 1) if total_inscripciones > 0 else 0
                },
                'historial': historial
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo historial académico: {str(e)}")
            raise BusinessLogicException("Error obteniendo historial académico")
    
    # ==========================================
    # RELACIONES DE GRUPOS Y CATEQUISTAS
    # ==========================================
    
    def get_red_catequistas(self, parroquia_id: int = None) -> Dict[str, Any]:
        """
        Obtiene la red de catequistas y sus relaciones.
        
        Args:
            parroquia_id: ID de parroquia (opcional)
            
        Returns:
            Dict con red de catequistas
        """
        try:
            from app.models.seguridad.rol_model import Rol
            from app.models.seguridad.usuario_rol_model import UsuarioRol
            
            # Obtener catequistas
            query = self.db.query(Usuario).join(UsuarioRol).join(Rol).filter(
                and_(
                    Rol.nombre == 'catequista',
                    Usuario.activo == True
                )
            )
            
            if parroquia_id:
                query = query.filter(Usuario.parroquia_id == parroquia_id)
            
            catequistas = query.all()
            
            red = []
            for catequista in catequistas:
                # Grupos asignados
                grupos_principal = self.db.query(Grupo).filter(
                    Grupo.catequista_principal_id == catequista.id
                ).all()
                
                grupos_auxiliar = self.db.query(Grupo).filter(
                    Grupo.catequista_auxiliar_id == catequista.id
                ).all()
                
                # Catequizandos bajo su responsabilidad
                total_catequizandos = self.db.query(Catequizando).join(Inscripcion).join(Grupo).filter(
                    or_(
                        Grupo.catequista_principal_id == catequista.id,
                        Grupo.catequista_auxiliar_id == catequista.id
                    ),
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                ).distinct().count()
                
                red.append({
                    'catequista': {
                        'id': catequista.id,
                        'nombres': catequista.nombres,
                        'apellidos': catequista.apellidos,
                        'email': catequista.email,
                        'telefono': catequista.telefono
                    },
                    'grupos_como_principal': len(grupos_principal),
                    'grupos_como_auxiliar': len(grupos_auxiliar),
                    'total_grupos': len(grupos_principal) + len(grupos_auxiliar),
                    'total_catequizandos': total_catequizandos,
                    'experiencia_años': self._calcular_experiencia(catequista.fecha_inicio_ministerio)
                })
            
            return {
                'parroquia_id': parroquia_id,
                'total_catequistas': len(catequistas),
                'red_catequistas': red,
                'estadisticas': {
                    'promedio_grupos_por_catequista': round(sum(c['total_grupos'] for c in red) / len(red), 1) if red else 0,
                    'promedio_catequizandos_por_catequista': round(sum(c['total_catequizandos'] for c in red) / len(red), 1) if red else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo red de catequistas: {str(e)}")
            raise BusinessLogicException("Error obteniendo red de catequistas")
    
    # ==========================================
    # ANÁLISIS DE DEPENDENCIAS
    # ==========================================
    
    def analizar_dependencias_entidad(self, entidad_tipo: str, entidad_id: int) -> Dict[str, Any]:
        """
        Analiza las dependencias de una entidad antes de eliminación.
        
        Args:
            entidad_tipo: Tipo de entidad ('catequizando', 'grupo', 'nivel', etc.)
            entidad_id: ID de la entidad
            
        Returns:
            Dict con análisis de dependencias
        """
        try:
            dependencias = {
                'puede_eliminar': True,
                'dependencias_criticas': [],
                'dependencias_menores': [],
                'acciones_requeridas': []
            }
            
            if entidad_tipo == 'catequizando':
                dependencias = self._analizar_dependencias_catequizando(entidad_id)
            elif entidad_tipo == 'grupo':
                dependencias = self._analizar_dependencias_grupo(entidad_id)
            elif entidad_tipo == 'catequista':
                dependencias = self._analizar_dependencias_catequista(entidad_id)
            elif entidad_tipo == 'nivel':
                dependencias = self._analizar_dependencias_nivel(entidad_id)
            
            return dependencias
            
        except Exception as e:
            logger.error(f"Error analizando dependencias: {str(e)}")
            raise BusinessLogicException("Error analizando dependencias")
    
    # ==========================================
    # GESTIÓN DE TRANSFERENCIAS
    # ==========================================
    
    def transferir_catequizando(self, catequizando_id: int, nuevo_grupo_id: int, motivo: str = None) -> Dict[str, Any]:
        """
        Transfiere un catequizando a otro grupo.
        
        Args:
            catequizando_id: ID del catequizando
            nuevo_grupo_id: ID del nuevo grupo
            motivo: Motivo de la transferencia
            
        Returns:
            Dict con resultado de la transferencia
        """
        try:
            # Validar catequizando
            catequizando = self.db.query(Catequizando).filter(
                Catequizando.id == catequizando_id
            ).first()
            
            if not catequizando:
                raise BusinessLogicException("Catequizando no encontrado")
            
            # Validar nuevo grupo
            nuevo_grupo = self.db.query(Grupo).filter(
                Grupo.id == nuevo_grupo_id
            ).first()
            
            if not nuevo_grupo:
                raise BusinessLogicException("Nuevo grupo no encontrado")
            
            # Obtener inscripción activa
            inscripcion_actual = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.catequizando_id == catequizando_id,
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).first()
            
            if not inscripcion_actual:
                raise BusinessLogicException("No hay inscripción activa para transferir")
            
            # Verificar compatibilidad de niveles
            if inscripcion_actual.nivel_id != nuevo_grupo.nivel_id:
                raise BusinessLogicException("El nuevo grupo no es compatible con el nivel actual del catequizando")
            
            # Verificar cupo disponible
            inscripciones_grupo = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == nuevo_grupo_id,
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).count()
            
            if inscripciones_grupo >= nuevo_grupo.cupo_maximo:
                raise BusinessLogicException("El nuevo grupo no tiene cupo disponible")
            
            # Realizar transferencia
            grupo_anterior_id = inscripcion_actual.grupo_id
            inscripcion_actual.grupo_id = nuevo_grupo_id
            inscripcion_actual.fecha_modificacion = datetime.utcnow()
            
            # Registrar en historial de cambios
            from app.models.auditoria.historial_cambio_model import HistorialCambio
            historial = HistorialCambio(
                entidad_tipo='inscripcion',
                entidad_id=inscripcion_actual.id,
                accion='transferencia_grupo',
                valor_anterior=str(grupo_anterior_id),
                valor_nuevo=str(nuevo_grupo_id),
                motivo=motivo,
                usuario_id=self.current_user['id'] if self.current_user else None,
                fecha_cambio=datetime.utcnow()
            )
            
            self.db.add(historial)
            self.db.commit()
            
            return {
                'transferencia_exitosa': True,
                'catequizando_id': catequizando_id,
                'grupo_anterior_id': grupo_anterior_id,
                'nuevo_grupo_id': nuevo_grupo_id,
                'motivo': motivo,
                'fecha_transferencia': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en transferencia: {str(e)}")
            raise BusinessLogicException(f"Error en transferencia: {str(e)}")
    
    def cambiar_catequista_grupo(self, grupo_id: int, nuevo_catequista_id: int, tipo_catequista: str = 'principal') -> Dict[str, Any]:
        """
        Cambia el catequista de un grupo.
        
        Args:
            grupo_id: ID del grupo
            nuevo_catequista_id: ID del nuevo catequista
            tipo_catequista: Tipo ('principal' o 'auxiliar')
            
        Returns:
            Dict con resultado del cambio
        """
        try:
            # Validar grupo
            grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
            if not grupo:
                raise BusinessLogicException("Grupo no encontrado")
            
            # Validar catequista
            catequista = self.db.query(Usuario).filter(Usuario.id == nuevo_catequista_id).first()
            if not catequista:
                raise BusinessLogicException("Catequista no encontrado")
            
            # Verificar que el usuario sea catequista
            from app.models.seguridad.rol_model import Rol
            from app.models.seguridad.usuario_rol_model import UsuarioRol
            
            es_catequista = self.db.query(UsuarioRol).join(Rol).filter(
                and_(
                    UsuarioRol.usuario_id == nuevo_catequista_id,
                    Rol.nombre == 'catequista'
                )
            ).first()
            
            if not es_catequista:
                raise BusinessLogicException("El usuario no tiene rol de catequista")
            
            # Realizar cambio
            catequista_anterior_id = None
            if tipo_catequista == 'principal':
                catequista_anterior_id = grupo.catequista_principal_id
                grupo.catequista_principal_id = nuevo_catequista_id
            else:
                catequista_anterior_id = grupo.catequista_auxiliar_id
                grupo.catequista_auxiliar_id = nuevo_catequista_id
            
            grupo.fecha_modificacion = datetime.utcnow()
            
            # Registrar cambio
            from app.models.auditoria.historial_cambio_model import HistorialCambio
            historial = HistorialCambio(
                entidad_tipo='grupo',
                entidad_id=grupo_id,
                accion=f'cambio_catequista_{tipo_catequista}',
                valor_anterior=str(catequista_anterior_id) if catequista_anterior_id else None,
                valor_nuevo=str(nuevo_catequista_id),
                usuario_id=self.current_user['id'] if self.current_user else None,
                fecha_cambio=datetime.utcnow()
            )
            
            self.db.add(historial)
            self.db.commit()
            
            return {
                'cambio_exitoso': True,
                'grupo_id': grupo_id,
                'tipo_catequista': tipo_catequista,
                'catequista_anterior_id': catequista_anterior_id,
                'nuevo_catequista_id': nuevo_catequista_id,
                'fecha_cambio': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cambiando catequista: {str(e)}")
            raise BusinessLogicException(f"Error cambiando catequista: {str(e)}")
    
    # ==========================================
    # REPORTES DE RELACIONES
    # ==========================================
    
    def generar_reporte_familias(self, parroquia_id: int = None) -> Dict[str, Any]:
        """
        Genera reporte de estructuras familiares.
        
        Args:
            parroquia_id: ID de parroquia (opcional)
            
        Returns:
            Dict con reporte de familias
        """
        try:
            # Query base para catequizandos
            query = self.db.query(Catequizando).filter(Catequizando.activo == True)
            
            if parroquia_id:
                query = query.filter(Catequizando.parroquia_id == parroquia_id)
            
            catequizandos = query.all()
            
            # Estadísticas familiares
            familias_completas = 0  # Con padre y madre
            familias_monoparentales = 0  # Solo un representante
            familias_extendidas = 0  # Con abuelos u otros
            hermanos_en_catequesis = 0
            
            for catequizando in catequizandos:
                representantes = self.db.query(Representante).filter(
                    and_(
                        Representante.catequizando_id == catequizando.id,
                        Representante.activo == True
                    )
                ).all()
                
                tipos_representantes = [r.tipo_representante for r in representantes]
                
                if 'madre' in tipos_representantes and 'padre' in tipos_representantes:
                    familias_completas += 1
                elif len(tipos_representantes) == 1 and tipos_representantes[0] in ['madre', 'padre']:
                    familias_monoparentales += 1
                elif any(tipo in ['abuelo', 'abuela', 'tio', 'tia'] for tipo in tipos_representantes):
                    familias_extendidas += 1
                
                # Contar hermanos
                estructura = self.get_estructura_familiar(catequizando.id)
                if estructura.get('hermanos'):
                    hermanos_en_catequesis += len(estructura['hermanos'])
            
            return {
                'parroquia_id': parroquia_id,
                'total_catequizandos': len(catequizandos),
                'estadisticas_familiares': {
                    'familias_completas': familias_completas,
                    'familias_monoparentales': familias_monoparentales,
                    'familias_extendidas': familias_extendidas,
                    'hermanos_en_catequesis': hermanos_en_catequesis,
                    'porcentaje_familias_completas': round((familias_completas / len(catequizandos) * 100), 1) if catequizandos else 0
                },
                'fecha_generacion': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte familias: {str(e)}")
            raise BusinessLogicException("Error generando reporte de familias")
    
    def generar_mapa_relaciones(self, entidad_tipo: str, entidad_id: int) -> Dict[str, Any]:
        """
        Genera un mapa visual de relaciones para una entidad.
        
        Args:
            entidad_tipo: Tipo de entidad central
            entidad_id: ID de la entidad central
            
        Returns:
            Dict con mapa de relaciones
        """
        try:
            mapa = {
                'entidad_central': {
                    'tipo': entidad_tipo,
                    'id': entidad_id
                },
                'nodos': [],
                'conexiones': [],
                'niveles': {}
            }
            
            if entidad_tipo == 'catequizando':
                mapa = self._generar_mapa_catequizando(entidad_id)
            elif entidad_tipo == 'grupo':
                mapa = self._generar_mapa_grupo(entidad_id)
            elif entidad_tipo == 'catequista':
                mapa = self._generar_mapa_catequista(entidad_id)
            
            return mapa
            
        except Exception as e:
            logger.error(f"Error generando mapa de relaciones: {str(e)}")
            raise BusinessLogicException("Error generando mapa de relaciones")
    
    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _calcular_experiencia(self, fecha_inicio: date) -> int:
        """Calcula años de experiencia."""
        if not fecha_inicio:
            return 0
        
        today = date.today()
        return today.year - fecha_inicio.year - (
            (today.month, today.day) < (fecha_inicio.month, fecha_inicio.day)
        )
    
    def _analizar_dependencias_catequizando(self, catequizando_id: int) -> Dict[str, Any]:
        """Analiza dependencias específicas de un catequizando."""
        dependencias = {
            'puede_eliminar': True,
            'dependencias_criticas': [],
            'dependencias_menores': [],
            'acciones_requeridas': []
        }
        
        # Inscripciones activas
        inscripciones_activas = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.catequizando_id == catequizando_id,
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).all()
        
        if inscripciones_activas:
            dependencias['puede_eliminar'] = False
            dependencias['dependencias_criticas'].append({
                'tipo': 'inscripciones_activas',
                'cantidad': len(inscripciones_activas),
                'descripcion': 'Tiene inscripciones activas en curso'
            })
            dependencias['acciones_requeridas'].append(
                'Finalizar o cancelar inscripciones activas antes de eliminar'
            )
        
        # Asistencias registradas
        from app.models.catequesis.asistencia_model import Asistencia
        asistencias = self.db.query(Asistencia).join(Inscripcion).filter(
            Inscripcion.catequizando_id == catequizando_id
        ).count()
        
        if asistencias > 0:
            dependencias['dependencias_menores'].append({
                'tipo': 'asistencias',
                'cantidad': asistencias,
                'descripcion': 'Tiene registro de asistencias'
            })
        
        # Certificados emitidos
        from app.models.certificados.emision_certificado_model import EmisionCertificado
        certificados = self.db.query(EmisionCertificado).filter(
            EmisionCertificado.catequizando_id == catequizando_id
        ).count()
        
        if certificados > 0:
            dependencias['dependencias_menores'].append({
                'tipo': 'certificados',
                'cantidad': certificados,
                'descripcion': 'Tiene certificados emitidos'
            })
        
        return dependencias
    
    def _analizar_dependencias_grupo(self, grupo_id: int) -> Dict[str, Any]:
        """Analiza dependencias específicas de un grupo."""
        dependencias = {
            'puede_eliminar': True,
            'dependencias_criticas': [],
            'dependencias_menores': [],
            'acciones_requeridas': []
        }
        
        # Inscripciones activas
        inscripciones_activas = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.grupo_id == grupo_id,
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).count()
        
        if inscripciones_activas > 0:
            dependencias['puede_eliminar'] = False
            dependencias['dependencias_criticas'].append({
                'tipo': 'inscripciones_activas',
                'cantidad': inscripciones_activas,
                'descripcion': 'Tiene catequizandos activos'
            })
            dependencias['acciones_requeridas'].append(
                'Transferir catequizandos a otros grupos o finalizar inscripciones'
            )
        
        # Clases programadas
        from app.models.catequesis.clase_model import Clase
        clases_futuras = self.db.query(Clase).filter(
            and_(
                Clase.grupo_id == grupo_id,
                Clase.fecha_clase > datetime.utcnow().date()
            )
        ).count()
        
        if clases_futuras > 0:
            dependencias['dependencias_menores'].append({
                'tipo': 'clases_futuras',
                'cantidad': clases_futuras,
                'descripcion': 'Tiene clases programadas'
            })
        
        return dependencias
    
    def _analizar_dependencias_catequista(self, catequista_id: int) -> Dict[str, Any]:
        """Analiza dependencias específicas de un catequista."""
        dependencias = {
            'puede_eliminar': True,
            'dependencias_criticas': [],
            'dependencias_menores': [],
            'acciones_requeridas': []
        }
        
        # Grupos como catequista principal
        grupos_principal = self.db.query(Grupo).filter(
            Grupo.catequista_principal_id == catequista_id
        ).count()
        
        if grupos_principal > 0:
            dependencias['puede_eliminar'] = False
            dependencias['dependencias_criticas'].append({
                'tipo': 'grupos_principal',
                'cantidad': grupos_principal,
                'descripcion': 'Es catequista principal de grupos'
            })
            dependencias['acciones_requeridas'].append(
                'Asignar nuevo catequista principal a los grupos'
            )
        
        # Grupos como catequista auxiliar
        grupos_auxiliar = self.db.query(Grupo).filter(
            Grupo.catequista_auxiliar_id == catequista_id
        ).count()
        
        if grupos_auxiliar > 0:
            dependencias['dependencias_menores'].append({
                'tipo': 'grupos_auxiliar',
                'cantidad': grupos_auxiliar,
                'descripcion': 'Es catequista auxiliar de grupos'
            })
        
        return dependencias
    
    def _analizar_dependencias_nivel(self, nivel_id: int) -> Dict[str, Any]:
        """Analiza dependencias específicas de un nivel."""
        dependencias = {
            'puede_eliminar': True,
            'dependencias_criticas': [],
            'dependencias_menores': [],
            'acciones_requeridas': []
        }
        
        # Grupos activos
        grupos_activos = self.db.query(Grupo).filter(
            and_(
                Grupo.nivel_id == nivel_id,
                Grupo.activo == True
            )
        ).count()
        
        if grupos_activos > 0:
            dependencias['puede_eliminar'] = False
            dependencias['dependencias_criticas'].append({
                'tipo': 'grupos_activos',
                'cantidad': grupos_activos,
                'descripcion': 'Tiene grupos activos asociados'
            })
            dependencias['acciones_requeridas'].append(
                'Reasignar grupos a otros niveles o desactivarlos'
            )
        
        # Inscripciones históricas
        inscripciones_historicas = self.db.query(Inscripcion).filter(
            Inscripcion.nivel_id == nivel_id
        ).count()
        
        if inscripciones_historicas > 0:
            dependencias['dependencias_menores'].append({
                'tipo': 'inscripciones_historicas',
                'cantidad': inscripciones_historicas,
                'descripcion': 'Tiene inscripciones históricas'
            })
        
        return dependencias
    
    def _generar_mapa_catequizando(self, catequizando_id: int) -> Dict[str, Any]:
        """Genera mapa de relaciones para un catequizando."""
        catequizando = self.db.query(Catequizando).filter(
            Catequizando.id == catequizando_id
        ).first()
        
        if not catequizando:
            return {}
        
        mapa = {
            'entidad_central': {
                'tipo': 'catequizando',
                'id': catequizando_id,
                'nombre': f"{catequizando.nombres} {catequizando.apellidos}"
            },
            'nodos': [],
            'conexiones': []
        }
        
        # Nodo central
        mapa['nodos'].append({
            'id': f"catequizando_{catequizando_id}",
            'tipo': 'catequizando',
            'nombre': f"{catequizando.nombres} {catequizando.apellidos}",
            'nivel': 0,
            'es_central': True
        })
        
        # Representantes
        representantes = self.db.query(Representante).filter(
            and_(
                Representante.catequizando_id == catequizando_id,
                Representante.activo == True
            )
        ).all()
        
        for rep in representantes:
            nodo_id = f"representante_{rep.id}"
            mapa['nodos'].append({
                'id': nodo_id,
                'tipo': 'representante',
                'nombre': f"{rep.nombres} {rep.apellidos}",
                'subtipo': rep.tipo_representante,
                'nivel': 1
            })
            
            mapa['conexiones'].append({
                'desde': f"catequizando_{catequizando_id}",
                'hacia': nodo_id,
                'tipo': 'representacion',
                'etiqueta': rep.tipo_representante
            })
        
        # Padrinos
        padrinos = self.db.query(Padrino).filter(
            and_(
                Padrino.catequizando_id == catequizando_id,
                Padrino.activo == True
            )
        ).all()
        
        for padrino in padrinos:
            nodo_id = f"padrino_{padrino.id}"
            mapa['nodos'].append({
                'id': nodo_id,
                'tipo': 'padrino',
                'nombre': f"{padrino.nombres} {padrino.apellidos}",
                'subtipo': padrino.tipo_padrino,
                'nivel': 1
            })
            
            mapa['conexiones'].append({
                'desde': f"catequizando_{catequizando_id}",
                'hacia': nodo_id,
                'tipo': 'padrinazgo',
                'etiqueta': padrino.tipo_padrino
            })
        
        # Inscripciones y grupos
        inscripciones = self.db.query(Inscripcion).filter(
            Inscripcion.catequizando_id == catequizando_id
        ).all()
        
        for inscripcion in inscripciones:
            if inscripcion.grupo:
                nodo_id = f"grupo_{inscripcion.grupo_id}"
                if not any(n['id'] == nodo_id for n in mapa['nodos']):
                    mapa['nodos'].append({
                        'id': nodo_id,
                        'tipo': 'grupo',
                        'nombre': inscripcion.grupo.nombre,
                        'nivel': 2
                    })
                
                mapa['conexiones'].append({
                    'desde': f"catequizando_{catequizando_id}",
                    'hacia': nodo_id,
                    'tipo': 'inscripcion',
                    'etiqueta': inscripcion.estado
                })
                
                # Catequistas del grupo
                if inscripcion.grupo.catequista_principal:
                    catequista_id = f"catequista_{inscripcion.grupo.catequista_principal_id}"
                    if not any(n['id'] == catequista_id for n in mapa['nodos']):
                        mapa['nodos'].append({
                            'id': catequista_id,
                            'tipo': 'catequista',
                            'nombre': f"{inscripcion.grupo.catequista_principal.nombres} {inscripcion.grupo.catequista_principal.apellidos}",
                            'nivel': 3
                        })
                    
                    mapa['conexiones'].append({
                        'desde': nodo_id,
                        'hacia': catequista_id,
                        'tipo': 'catequesis',
                        'etiqueta': 'principal'
                    })
        
        return mapa
    
    def _generar_mapa_grupo(self, grupo_id: int) -> Dict[str, Any]:
        """Genera mapa de relaciones para un grupo."""
        grupo = self.db.query(Grupo).filter(Grupo.id == grupo_id).first()
        
        if not grupo:
            return {}
        
        mapa = {
            'entidad_central': {
                'tipo': 'grupo',
                'id': grupo_id,
                'nombre': grupo.nombre
            },
            'nodos': [],
            'conexiones': []
        }
        
        # Nodo central
        mapa['nodos'].append({
            'id': f"grupo_{grupo_id}",
            'tipo': 'grupo',
            'nombre': grupo.nombre,
            'nivel': 0,
            'es_central': True
        })
        
        # Catequistas
        if grupo.catequista_principal:
            catequista_id = f"catequista_{grupo.catequista_principal_id}"
            mapa['nodos'].append({
                'id': catequista_id,
                'tipo': 'catequista',
                'nombre': f"{grupo.catequista_principal.nombres} {grupo.catequista_principal.apellidos}",
                'subtipo': 'principal',
                'nivel': 1
            })
            
            mapa['conexiones'].append({
                'desde': f"grupo_{grupo_id}",
                'hacia': catequista_id,
                'tipo': 'catequesis',
                'etiqueta': 'principal'
            })
        
        if grupo.catequista_auxiliar:
            catequista_aux_id = f"catequista_aux_{grupo.catequista_auxiliar_id}"
            mapa['nodos'].append({
                'id': catequista_aux_id,
                'tipo': 'catequista',
                'nombre': f"{grupo.catequista_auxiliar.nombres} {grupo.catequista_auxiliar.apellidos}",
                'subtipo': 'auxiliar',
                'nivel': 1
            })
            
            mapa['conexiones'].append({
                'desde': f"grupo_{grupo_id}",
                'hacia': catequista_aux_id,
                'tipo': 'catequesis',
                'etiqueta': 'auxiliar'
            })
        
        # Catequizandos activos
        inscripciones_activas = self.db.query(Inscripcion).filter(
            and_(
                Inscripcion.grupo_id == grupo_id,
                Inscripcion.estado.in_(['activa', 'en_progreso'])
            )
        ).all()
        
        for inscripcion in inscripciones_activas:
            catequizando = inscripcion.catequizando
            nodo_id = f"catequizando_{catequizando.id}"
            mapa['nodos'].append({
                'id': nodo_id,
                'tipo': 'catequizando',
                'nombre': f"{catequizando.nombres} {catequizando.apellidos}",
                'nivel': 2
            })
            
            mapa['conexiones'].append({
                'desde': f"grupo_{grupo_id}",
                'hacia': nodo_id,
                'tipo': 'inscripcion',
                'etiqueta': inscripcion.estado
            })
        
        # Nivel
        if grupo.nivel:
            nivel_id = f"nivel_{grupo.nivel_id}"
            mapa['nodos'].append({
                'id': nivel_id,
                'tipo': 'nivel',
                'nombre': grupo.nivel.nombre,
                'nivel': -1
            })
            
            mapa['conexiones'].append({
                'desde': nivel_id,
                'hacia': f"grupo_{grupo_id}",
                'tipo': 'pertenencia',
                'etiqueta': 'nivel'
            })
        
        return mapa
    
    def _generar_mapa_catequista(self, catequista_id: int) -> Dict[str, Any]:
        """Genera mapa de relaciones para un catequista."""
        catequista = self.db.query(Usuario).filter(Usuario.id == catequista_id).first()
        
        if not catequista:
            return {}
        
        mapa = {
            'entidad_central': {
                'tipo': 'catequista',
                'id': catequista_id,
                'nombre': f"{catequista.nombres} {catequista.apellidos}"
            },
            'nodos': [],
            'conexiones': []
        }
        
        # Nodo central
        mapa['nodos'].append({
            'id': f"catequista_{catequista_id}",
            'tipo': 'catequista',
            'nombre': f"{catequista.nombres} {catequista.apellidos}",
            'nivel': 0,
            'es_central': True
        })
        
        # Grupos como principal
        grupos_principal = self.db.query(Grupo).filter(
            Grupo.catequista_principal_id == catequista_id
        ).all()
        
        for grupo in grupos_principal:
            nodo_id = f"grupo_principal_{grupo.id}"
            mapa['nodos'].append({
                'id': nodo_id,
                'tipo': 'grupo',
                'nombre': grupo.nombre,
                'subtipo': 'principal',
                'nivel': 1
            })
            
            mapa['conexiones'].append({
                'desde': f"catequista_{catequista_id}",
                'hacia': nodo_id,
                'tipo': 'catequesis',
                'etiqueta': 'principal'
            })
            
            # Catequizandos del grupo
            inscripciones = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo.id,
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).all()
            
            for inscripcion in inscripciones:
                catequizando = inscripcion.catequizando
                catequizando_id_nodo = f"catequizando_{catequizando.id}"
                if not any(n['id'] == catequizando_id_nodo for n in mapa['nodos']):
                    mapa['nodos'].append({
                        'id': catequizando_id_nodo,
                        'tipo': 'catequizando',
                        'nombre': f"{catequizando.nombres} {catequizando.apellidos}",
                        'nivel': 2
                    })
                
                mapa['conexiones'].append({
                    'desde': nodo_id,
                    'hacia': catequizando_id_nodo,
                    'tipo': 'inscripcion',
                    'etiqueta': 'estudiante'
                })
        
        # Grupos como auxiliar
        grupos_auxiliar = self.db.query(Grupo).filter(
            Grupo.catequista_auxiliar_id == catequista_id
        ).all()
        
        for grupo in grupos_auxiliar:
            nodo_id = f"grupo_auxiliar_{grupo.id}"
            mapa['nodos'].append({
                'id': nodo_id,
                'tipo': 'grupo',
                'nombre': grupo.nombre,
                'subtipo': 'auxiliar',
                'nivel': 1
            })
            
            mapa['conexiones'].append({
                'desde': f"catequista_{catequista_id}",
                'hacia': nodo_id,
                'tipo': 'catequesis',
                'etiqueta': 'auxiliar'
            })
        
        return mapa
    
    # ==========================================
    # UTILIDADES DE VALIDACIÓN
    # ==========================================
    
    def validar_relacion_familiar(self, catequizando_id: int, representante_data: Dict) -> Dict[str, Any]:
        """
        Valida una nueva relación familiar antes de crearla.
        
        Args:
            catequizando_id: ID del catequizando
            representante_data: Datos del representante
            
        Returns:
            Dict con resultado de validación
        """
        try:
            resultado = {
                'valido': True,
                'errores': [],
                'advertencias': []
            }
            
            # Validar que no exista ya un representante principal del mismo tipo
            if representante_data.get('es_contacto_principal'):
                principal_existente = self.db.query(Representante).filter(
                    and_(
                        Representante.catequizando_id == catequizando_id,
                        Representante.es_contacto_principal == True,
                        Representante.activo == True
                    )
                ).first()
                
                if principal_existente:
                    resultado['valido'] = False
                    resultado['errores'].append(
                        "Ya existe un contacto principal para este catequizando"
                    )
            
            # Validar tipo de representante
            tipo_representante = representante_data.get('tipo_representante')
            representante_mismo_tipo = self.db.query(Representante).filter(
                and_(
                    Representante.catequizando_id == catequizando_id,
                    Representante.tipo_representante == tipo_representante,
                    Representante.activo == True
                )
            ).first()
            
            if representante_mismo_tipo:
                resultado['advertencias'].append(
                    f"Ya existe un representante de tipo '{tipo_representante}' para este catequizando"
                )
            
            # Validar documento único
            numero_documento = representante_data.get('numero_documento')
            if numero_documento:
                documento_existente = self.db.query(Representante).filter(
                    and_(
                        Representante.numero_documento == numero_documento,
                        Representante.activo == True
                    )
                ).first()
                
                if documento_existente and documento_existente.catequizando_id != catequizando_id:
                    resultado['advertencias'].append(
                        f"Este documento ya está registrado para otro catequizando (ID: {documento_existente.catequizando_id})"
                    )
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error validando relación familiar: {str(e)}")
            return {
                'valido': False,
                'errores': ['Error interno en validación'],
                'advertencias': []
            }
    
    def obtener_sugerencias_transferencia(self, catequizando_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene sugerencias de grupos para transferencia.
        
        Args:
            catequizando_id: ID del catequizando
            
        Returns:
            Lista de grupos sugeridos
        """
        try:
            # Obtener inscripción actual
            inscripcion_actual = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.catequizando_id == catequizando_id,
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).first()
            
            if not inscripcion_actual:
                return []
            
            # Buscar grupos del mismo nivel con cupo disponible
            grupos_compatibles = self.db.query(Grupo).filter(
                and_(
                    Grupo.nivel_id == inscripcion_actual.nivel_id,
                    Grupo.id != inscripcion_actual.grupo_id,
                    Grupo.activo == True
                )
            ).all()
            
            sugerencias = []
            for grupo in grupos_compatibles:
                # Contar inscripciones actuales
                inscripciones_count = self.db.query(Inscripcion).filter(
                    and_(
                        Inscripcion.grupo_id == grupo.id,
                        Inscripcion.estado.in_(['activa', 'en_progreso'])
                    )
                ).count()
                
                cupo_disponible = grupo.cupo_maximo - inscripciones_count
                
                if cupo_disponible > 0:
                    sugerencias.append({
                        'grupo_id': grupo.id,
                        'nombre': grupo.nombre,
                        'cupo_disponible': cupo_disponible,
                        'horario': grupo.horario,
                        'catequista_principal': {
                            'nombres': grupo.catequista_principal.nombres if grupo.catequista_principal else None,
                            'apellidos': grupo.catequista_principal.apellidos if grupo.catequista_principal else None
                        },
                        'compatibilidad': self._calcular_compatibilidad_grupo(catequizando_id, grupo.id)
                    })
            
            # Ordenar por compatibilidad
            sugerencias.sort(key=lambda x: x['compatibilidad'], reverse=True)
            
            return sugerencias[:5]  # Top 5 sugerencias
            
        except Exception as e:
            logger.error(f"Error obteniendo sugerencias de transferencia: {str(e)}")
            return []
    
    def _calcular_compatibilidad_grupo(self, catequizando_id: int, grupo_id: int) -> float:
        """Calcula compatibilidad entre catequizando y grupo."""
        try:
            # Factores de compatibilidad:
            # 1. Edad promedio del grupo
            # 2. Hermanos en el grupo
            # 3. Horario compatible
            
            compatibilidad = 0.0
            
            # Obtener catequizando
            catequizando = self.db.query(Catequizando).filter(
                Catequizando.id == catequizando_id
            ).first()
            
            if not catequizando or not catequizando.fecha_nacimiento:
                return 0.0
            
            # Calcular edad del catequizando
            edad_catequizando = (date.today() - catequizando.fecha_nacimiento).days / 365.25
            
            # Obtener edades del grupo
            inscripciones_grupo = self.db.query(Inscripcion).join(Catequizando).filter(
                and_(
                    Inscripcion.grupo_id == grupo_id,
                    Inscripcion.estado.in_(['activa', 'en_progreso']),
                    Catequizando.fecha_nacimiento.isnot(None)
                )
            ).all()
            
            if inscripciones_grupo:
                edades_grupo = []
                for inscripcion in inscripciones_grupo:
                    edad = (date.today() - inscripcion.catequizando.fecha_nacimiento).days / 365.25
                    edades_grupo.append(edad)
                
                edad_promedio_grupo = sum(edades_grupo) / len(edades_grupo)
                diferencia_edad = abs(edad_catequizando - edad_promedio_grupo)
                
                # Compatibilidad por edad (máximo 0.5)
                if diferencia_edad <= 1:
                    compatibilidad += 0.5
                elif diferencia_edad <= 2:
                    compatibilidad += 0.3
                elif diferencia_edad <= 3:
                    compatibilidad += 0.1
            
            # Verificar hermanos en el grupo (máximo 0.3)
            estructura_familiar = self.get_estructura_familiar(catequizando_id)
            hermanos_ids = [h['id'] for h in estructura_familiar.get('hermanos', [])]
            
            hermanos_en_grupo = self.db.query(Inscripcion).filter(
                and_(
                    Inscripcion.grupo_id == grupo_id,
                    Inscripcion.catequizando_id.in_(hermanos_ids),
                    Inscripcion.estado.in_(['activa', 'en_progreso'])
                )
            ).count()
            
            if hermanos_en_grupo > 0:
                compatibilidad += 0.3
            
            # Normalizar a 1.0
            return min(compatibilidad, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando compatibilidad: {str(e)}")
            return 0.0