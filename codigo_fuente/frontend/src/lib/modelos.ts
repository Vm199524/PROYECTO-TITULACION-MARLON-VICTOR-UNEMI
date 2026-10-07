/** src/lib/modelos.ts — nombres legibles de los modelos candidatos (backend/ml/entrenar.py). */
export const NOMBRE_MODELO: Record<string, string> = {
  LIGHTGBM: 'LightGBM',
  RF_PONDERADO: 'Random Forest ponderado',
  RF_SMOTE: 'Random Forest con SMOTE',
  LOGISTICA: 'Regresión logística',
}
