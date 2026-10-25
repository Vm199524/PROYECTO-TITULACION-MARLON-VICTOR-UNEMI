/**
 * src/lib/tipos.ts — contratos de la API (backend/api/*.py). Un cambio de forma en el
 * backend se refleja aquí y TypeScript señala cada pantalla afectada.
 */
export type Rol = 'AUTORIDAD' | 'BIENESTAR' | 'ADMIN_TI'
export type Riesgo = 'ALTO' | 'MEDIO' | 'BAJO'

export interface Perfil {
  usuario: string
  nombre: string | null
  correo: string | null
  rol: Rol
  rol_descripcion: string
  capacidades: string[]
  instituciones: string[]
  ultimo_acceso: string | null
}

export interface Institucion {
  codigo: string
  nombre: string
  pais: string | null
  tipo_datos: 'SINTETICO' | 'REAL_ANONIMIZADO' | null
  unidad_periodo: string | null
  disponible: boolean
}

// ── Panel ejecutivo ────────────────────────────────────────────────────────
export interface ResumenPanel {
  institucion: { nombre: string; pais: string; tipo_datos: string; unidad_periodo: string } | null
  calificacion: { fecha: string | null; version: string | null; modelo: string | null }
  indicadores: {
    evaluados: number
    alto: number
    medio: number
    bajo: number
    tasa_abandono_hist: number | null
    carreras_prioritarias: number
    intervenciones_abiertas: number
    cobertura_alto: number | null
  }
  confiabilidad: Record<string, number | null>
  segmentos: { segmento: string; orden_segmento: number; carreras: number }[]
  riesgo_por_carrera: { carrera: string; alto: number; medio: number; activos: number }[]
  tendencia: { periodo: string; estudiantes: number; retirados: number; tasa: number }[]
  alertas: { token: string; nombre: string; carrera: string; probabilidad: number; percentil: number; factor: string | null }[]
  /** Frases calculadas con reglas sobre las cifras (las mismas del reporte ejecutivo). */
  lectura: string[]
}

// ── Estudiantes ────────────────────────────────────────────────────────────
export interface EstudianteFila {
  token: string
  cedula: string
  nombre: string
  carrera: string
  facultad: string
  nivel: number
  periodo: string
  promedio: number | null
  asistencia: number | null
  saldo: number | null
  probabilidad: number
  riesgo: Riesgo
  percentil: number
  factores: string[]
}

export interface ListaEstudiantes {
  total: number
  pagina: number
  tamano: number
  carreras: string[]
  estudiantes: EstudianteFila[]
}

export interface Contribucion {
  variable: string
  descripcion: string
  valor: number | null
  valor_texto?: string | null
  /** Positiva: empuja el riesgo hacia arriba; negativa: lo reduce (escala del modelo). */
  contribucion: number
}

export interface Recomendacion {
  tipo: string
  texto: string
  motivo?: string
}

export interface Intervencion {
  intervencion_id: number
  token?: string
  nombre?: string
  carrera?: string
  tipo: string
  tipo_descripcion?: string
  descripcion: string
  estado: 'ABIERTA' | 'CERRADA'
  resultado: string | null
  riesgo_al_registrar: Riesgo | null
  registrado_por: string
  fecha_registro: string
  fecha_cierre: string | null
}

export interface FilaTrayectoria {
  periodo_academico: string
  inicio_periodo: string
  fecha_corte: string
  nivel: number
  corte: number
  estado_matricula: string
  carrera: string
  promedio: number | null
  asistencia_pct: number | null
  saldo_pendiente: number | null
  beca_porcentaje: number | null
  actividad_lms: number | null
  dias_sin_actividad: number | null
  evaluaciones_vencidas: number | null
  evaluaciones_entregadas: number | null
  nota_evaluaciones: number | null
  numero_matricula: number | null
  creditos_matriculados: number | null
}

export interface VariableSimulable {
  grupo: string
  etiqueta: string
  min: number
  max: number
}

export interface FichaEstudiante {
  token: string
  cedula: string
  nombre: string | null
  genero: string | null
  carrera: string | null
  facultad: string | null
  sede: string | null
  modalidad: string | null
  estado: string | null
  prediccion: {
    probabilidad: number
    riesgo: Riesgo
    percentil: number
    umbral_alto: number
    umbral_medio: number
    horizonte: string
    fecha_calculo: string
    modelo_version: string
    factores: string[]
  } | null
  explicacion: Contribucion[]
  recomendaciones: Recomendacion[]
  trayectoria: FilaTrayectoria[]
  seguimiento: Intervencion[]
  simulables: Record<string, VariableSimulable>
  valores_actuales: Record<string, number | null>
}

export interface PrediccionPuntual {
  probabilidad: number
  categoria: Riesgo
  factores: string[]
  explicacion: Contribucion[]
}

export interface ResultadoSimulacion {
  actual: PrediccionPuntual
  simulado: PrediccionPuntual
  cambios: Record<string, number>
  diferencia_puntos: number
  aviso: string
}

// ── Carreras y referentes ──────────────────────────────────────────────────
export interface CarreraSegmento {
  carrera: string
  facultad_nombre: string
  segmento: string
  orden_segmento: number
  estudiantes: number
  tasa_abandono_hist: number
  promedio_hist: number
  asistencia_hist: number
  riesgo_promedio: number
  activos_en_riesgo: number
  fecha_calculo: string
}

export interface Segmentacion {
  carreras: CarreraSegmento[]
  validacion: {
    unidades?: number
    k?: number
    silhouette?: number
    estabilidad?: { remuestreos: number; ari_medio: number; ari_desviacion: number }
    kruskal_wallis?: { H: number; p: number }
    barrido_k?: { k: number; silhouette: number; davies_bouldin: number; calinski_harabasz: number }[]
    comparacion_algoritmos?: Record<string, { clusteres: number; ruido: number; silhouette: number | null }>
    ari_sin_riesgo_del_modelo?: number
  }
}

export interface Referente {
  referente_codigo: string
  nombre: string
  valor: number
  unidad: string
  anio: number | null
  definicion_indicador: string
  pais: string
  modalidad: string
  nivel_comparabilidad: 'ALTA' | 'MEDIA' | 'BAJA'
  fuente: string
  doi: string | null
  url_fuente: string | null
}

export interface Referentes {
  propia: {
    institucion: { nombre: string; pais: string; tipo_datos: string } | null
    retirados: number
    cerrados: number
    tasa: number | null
    definicion: string
  }
  referentes: Referente[]
}

// ── Calidad del modelo ─────────────────────────────────────────────────────
export interface MetricaCV {
  media: number
  desviacion: number
  pliegues: number[]
}

export interface EvaluacionUmbral {
  umbral: number
  recall: number
  precision: number
  tasa_alerta: number
  fpr: number
  matriz_confusion: number[][]
}

export interface EvaluacionProspectiva {
  positivos: number
  roc_auc: number
  pr_auc: number
  recall: number
  precision: number
  matriz_confusion: number[][]
}

export interface CalidadModelo {
  disponible: boolean
  version?: string
  fecha?: string
  horizonte?: string
  modelo_final?: string
  panel?: Record<string, number>
  grupos_de_variables?: string[]
  comparacion_cv?: Record<string, { roc_auc: MetricaCV; pr_auc: MetricaCV }>
  umbrales?: { alto: number; medio: number; recall_objetivo_alto: number; recall_objetivo_medio: number }
  calibracion?: { metodo: string }
  temporal?: {
    n: number
    positivos: number
    prevalencia: number
    roc_auc: number
    pr_auc: number
    brier_sin_calibrar: number
    brier_calibrado: number
    captura_top_10: number
    captura_top_20: number
    umbral_medio: EvaluacionUmbral
    umbral_alto: EvaluacionUmbral
    curva_roc: [number, number][]
    curva_pr: [number, number][]
    curva_calibracion: { predicha: number; observada: number; n: number }[]
    periodos: string[]
  }
  equidad?: {
    variable: string
    grupo: string
    n: number
    prevalencia: number
    roc_auc: number | null
    recall: number | null
    precision: number | null
    tasa_alerta: number
    fpr: number | null
  }[]
  importancia?: { variable: string; media: number; desviacion: number; descripcion: string }[]
  prospectiva?: {
    calificados: number
    presentacion: string
    umbral_medio: number
    y_siguiente: EvaluacionProspectiva
    y_resto: EvaluacionProspectiva
  } | null
  monitoreo?: {
    calificados: number
    distribucion: Record<string, number>
    psi: { variable: string; psi: number | null; estado: string }[]
  } | null
  consulta?: {
    fecha: string
    resumen: {
      preguntas_base: number
      exactitud_relajada_base: number
      exactitud_estricta_base: number
      preguntas_robustez: number
      exactitud_relajada_robustez: number
      exactitud_relajada_total: number
      fallas_tecnicas: number
      latencia_mediana_ms: number | null
      latencia_p95_ms: number | null
      adversariales_contenidas: string
      base_sin_cambios: boolean
      violaciones_aislamiento: number
    }
    por_categoria: Record<string, { preguntas: number; correctas: number; exactitud: number }>
    por_origen: Record<string, { preguntas: number; exactitud_relajada: number }>
    adversariales: { id: string; tipo: string; pregunta: string; intencion: string; origen: string; filas: number; contenida: boolean }[]
  } | null
  ficha?: Record<string, string>
}

// ── Consulta conversacional ────────────────────────────────────────────────
export type OrigenRespuesta = 'CERTIFICADA' | 'GENERADA_IA' | 'BARRERA' | 'SIN_RESPUESTA' | 'ERROR'

export interface RespuestaConsulta {
  id: string
  pregunta: string
  origen: OrigenRespuesta
  intencion: string
  titulo: string
  explicacion: string
  columnas: string[]
  filas: (string | number | null)[][]
  visualizacion: 'texto' | 'valor' | 'tabla' | 'barras' | 'lineas'
  metrica_id: string | null
  sql: string | null
  advertencias: string[]
  proveedor: string | null
  tiempo_ms: number
  sugerencias: Record<string, string[]> | null
}

export interface Interpretacion {
  texto: string
  verificada: boolean
  proveedor?: string | null
  modelo?: string | null
  motivo?: string | null
}

// ── Administración ─────────────────────────────────────────────────────────
export interface Cuenta {
  usuario: string
  nombre: string
  correo: string
  rol: Rol
  instituciones: string[]
  activo: boolean
  creado?: string
  ultimo_acceso?: string | null
}

export interface EventoAuditoria {
  fecha: string
  accion: string
  usuario: string
  institucion: string | null
  resultado: string
  ip?: string | null
  detalle?: Record<string, unknown> | null
}

export interface EstadoSistema {
  instituciones: {
    codigo: string
    nombre: string
    tipo_datos: string
    cargada: boolean
    filas?: number
    estudiantes?: number
    ultimo_corte?: string
    calificados?: number
    fecha_calificacion?: string | null
    error?: string
    modelo?: { nombre: string; version: string; fecha: string; roc_auc_temporal: number | null }
    deriva?: { variable: string; psi: number; estado: string }[]
  }[]
  procesos: {
    inicio: string
    fin: string | null
    resultado: string
    log?: string
    pasos: { paso: string; descripcion: string; estado: string; segundos: number | null; fin: string | null; detalle: string }[]
  } | null
  cuentas_bd: { lectura_configurada: boolean; seguimiento_configurado: boolean }
  proveedores_ia: { nombre: string; modelo: string; configurado: boolean }[]
}
