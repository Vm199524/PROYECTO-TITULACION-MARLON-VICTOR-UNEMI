"""
Adaptador resiliente del motor de IA.

Es la fachada que usan las rutas de consulta y la capa de sesión sobre
NL2SQLEngine. Inicializa el motor de forma diferida y, si falta toda clave de
proveedor (DeepSeek, Gemini, Groq, NVIDIA NIM) o la carga falla, entra en modo
seguro y responde degradado en lugar de tumbar la autenticación o el backend.
Los saludos simples se responden al instante sin llamar al modelo.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("DeepSeekClient")

_GREETING_WORDS = {
    "hola", "buenos dias", "buenas dias", "buenas tardes", "buenas noches", 
    "hi", "hello", "ey", "saludos", "que tal", "como estas", "como está",
    "buen dia", "buena tarde", "buena noche"
} 

# Palabras que indican que no es solo un saludo, aunque el texto contenga palabras de saludo.
_NON_GREETING_INDICATORS = {
    "consulta", "pregunta", "quiero", "necesito", "dime", "muestrame", "muestreme",
    "busco", "ayuda", "informacion", "datos", "reporte", "ver", "saber", "cuanto",
    "cuantos", "quien", "donde", "cuando", "por que", "cual", "cuales",
    # "que" y "como" no se incluyen para no bloquear "que tal" ni "como estas".
}

# Frases de saludo cortas que siempre se tratan como saludos puros.
_SHORT_GREETINGS = {"que tal", "como estas", "como está", "cómo estás", "cómo está"}


def _is_greeting(text: str) -> bool:
    """Detecta si el texto es únicamente un saludo natural.

    Devuelve False si el saludo viene acompañado de una consulta.
    """
    cleaned = (text or "").strip().lower().replace("!", "").replace(".", "").replace("?", "").replace(",", "").replace("¿", "")
    words = cleaned.split()
    if not words: 
        return False
    
    # Primero se comprueba si es una frase de saludo corta conocida.
    if cleaned in _SHORT_GREETINGS:
        return True
    
    # Con más de 6 palabras, probablemente no sea solo un saludo.
    if len(words) > 6:
        return False
    
    # Si contiene indicadores de consulta, no es un saludo puro.
    if any(indicator in cleaned for indicator in _NON_GREETING_INDICATORS):
        return False
    
    # Un texto corto con una palabra de saludo se trata como saludo instantáneo.
    if any(w in _GREETING_WORDS for w in words) and len(words) <= 4:
        return True
    
    return cleaned in _GREETING_WORDS


class DeepSeekClient:
    """Cliente de IA con modo seguro.

    - Si NL2SQLEngine está disponible, delega en él.
    - Si falla la carga o no hay ninguna clave de API, no rompe la aplicación
      ni el inicio de sesión: responde con mensajes degradados.
    """

    def __init__(
        self,
        api_key: str = "",
        database_name: str = "CHAT",
        is_sqlite: bool = False,
        is_postgres: bool = False,
        **_: Any,
    ) -> None:
        self.database_name = database_name or "CHAT"
        self.is_sqlite = is_sqlite
        self.is_postgres = is_postgres
        self.user_role = "GUEST"
        self.user_name = "Invitado"
        self.schema_text = ""
        self.semantic_relations = ""
        self.master_schema_text = ""

        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self._engine: Optional[Any] = None
        self._engine_error: Optional[str] = None
        self._try_init_engine()

    def _cascade_disponible(self) -> bool:
        """Indica si hay al menos una clave de proveedor para arrancar el motor.

        No se exige DEEPSEEK_API_KEY porque NL2SQLEngine trae su propia cascada
        de respaldo (Gemini, Groq, NVIDIA NIM; ver core/nl2sql_engine.py), así
        que basta con que una de las cuatro claves esté presente.
        """
        return bool(
            self._api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("NVIDIA_API_KEY")
        )

    def _try_init_engine(self) -> None:
        # El motor se inicializa de forma diferida para proteger el arranque.
        # Si falla, el cliente entra en modo seguro y responde degradado.
        if self._engine is not None:
            return

        if not self._cascade_disponible():
            self._engine_error = "Ningún proveedor de IA configurado (DeepSeek/Gemini/Groq/NVIDIA)."
            logger.warning("[AI SAFE MODE] %s", self._engine_error)
            return

        try:
            from core.nl2sql_engine import NL2SQLEngine

            self._engine = NL2SQLEngine(
                api_key=self._api_key,
                database_name=self.database_name,
            )
            if self.schema_text:
                tables_dict = getattr(self, "tables_dict", None)
                self._engine.set_schema(
                    self.schema_text, 
                    self.semantic_relations,
                    tables_dict=tables_dict
                )
            self._engine_error = None
        except Exception as exc:  # pragma: no cover
            self._engine = None
            self._engine_error = str(exc)
            logger.exception("[AI SAFE MODE] Fallo al cargar NL2SQLEngine: %s", exc)

    def _safe_welcome(self) -> str:
        """Devuelve un saludo de bienvenida según la hora del día."""
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Buenos días"
        elif hour < 19:
            greeting = "Buenas tardes"
        else:
            greeting = "Buenas noches"
        return f"{greeting}, soy VicMar Data AI. ¿En qué puedo ayudarte hoy?"

    def set_schema(self, schema_text: str, semantic_relations: str | None = None, **kwargs) -> None:
        """Guarda el esquema y las relaciones semánticas y los inyecta en el motor si está cargado.

        Acepta `tables_dict` en kwargs, que se conserva para pasarlo al motor
        también cuando se inicialice más tarde.
        """
        self.schema_text = schema_text or ""
        if semantic_relations is not None:
            self.semantic_relations = semantic_relations or ""
        
        # Se guarda el tables_dict si se provee.
        tables_dict = kwargs.get("tables_dict")
        if tables_dict:
            self.tables_dict = tables_dict
            
        if self._engine and hasattr(self._engine, "set_schema"):
            try:
                # Se pasa tables_dict si existe para que NL2SQLEngine lo use.
                self._engine.set_schema(
                    self.schema_text, 
                    self.semantic_relations,
                    tables_dict=tables_dict
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("No se pudo inyectar schema al motor IA: %s", exc)

    def set_master_schema(self, master_schema_text: str) -> None:
        """Guarda el texto del esquema maestro."""
        self.master_schema_text = master_schema_text or ""

    def update_context(self, schema: str, mapping: str = "") -> None:
        """Actualiza el esquema y las relaciones; alias de set_schema por compatibilidad."""
        self.set_schema(schema, mapping)

    def _normalize_generate_sql_result(self, raw: Any) -> dict:
        """Normaliza la respuesta del motor al contrato que esperan las rutas.

        Una cadena se interpreta como respuesta conversacional (prefijo "CHAT:"),
        un tipo inesperado se convierte en un aviso, y a un dict se le completan
        las claves que falten. Toda respuesta sin SQL se marca como is_greeting.
        """
        if isinstance(raw, str):
            if raw == "CHAT:STATIC_RESPONSE":
                text = self._safe_welcome()
            elif raw.startswith("CHAT:"):
                text = raw[5:].strip() or self._safe_welcome()
            else:
                text = raw.strip() or self._safe_welcome()
            return {
                "is_greeting": True,
                "sql": "",
                "explanation": text,
                "visualization_type": "text",
                "viz_config": {},
                "agent_log": ["AI Safe Greeting"],
            }

        if not isinstance(raw, dict):
            return {
                "is_greeting": True,
                "sql": "",
                "explanation": "El motor IA devolvió un formato no válido.",
                "visualization_type": "text",
                "viz_config": {},
                "agent_log": ["AI Guardrail: invalid payload"],
            }

        result = dict(raw)
        if "visualization_type" not in result and "viz_type" in result:
            result["visualization_type"] = result.get("viz_type")

        thought = result.get("pensamiento_analitico")
        if "agent_log" not in result:
            result["agent_log"] = [f"Analisis: {thought}"] if thought else ["AI Engine"]

        result.setdefault("viz_config", {})
        result.setdefault("visualization_type", "table")
        result.setdefault("sql", "")
        result.setdefault("explanation", "Análisis completado.")
        if not result.get("sql"):
            result["is_greeting"] = True
        return result

    def generate_sql(
        self,
        question: str,
        module: str = "GLOBAL",
        context_db: str = "CHAT",
        history: str = "",
        company_code: str = "",
        vistas_reales: str = "",
        modelo_forzado: str | None = None,
    ) -> tuple[dict, Optional[str]]:
        """Genera el SQL y la explicación para una pregunta en lenguaje natural.

        Responde sin llamar al modelo si la pregunta está vacía o es un saludo,
        y con un mensaje de modo seguro si el motor no está disponible.

        Returns:
            (resultado, error): el resultado normalizado y None, o un dict vacío
            y el mensaje de error del motor.
        """
        text = (question or "").strip()
        if not text:
            return (
                {
                    "is_greeting": True,
                    "sql": "",
                    "explanation": self._safe_welcome(),
                    "visualization_type": "text",
                    "viz_config": {},
                    "agent_log": ["AI Safe Greeting"],
                },
                None,
            )

        if _is_greeting(text):
            return (
                {
                    "is_greeting": True,
                    "sql": "",
                    "explanation": self._safe_welcome(),
                    "visualization_type": "text",
                    "viz_config": {},
                    "agent_log": ["AI Fast Greeting"],
                },
                None,
            )

        # Para consultas reales, el motor se inicializa de forma diferida.

        self._try_init_engine()
        if not self._engine:
            logger.warning(
                "[AI SAFE MODE] Consulta degradada. Motivo: %s",
                self._engine_error or "motor no disponible",
            )
            return (
                {
                    "is_greeting": True,
                    "sql": "",
                    "explanation": (
                        "El motor IA está en modo seguro temporal. "
                        "El acceso al sistema sigue activo; reintente en unos segundos."
                    ),
                    "visualization_type": "text",
                    "viz_config": {},
                    "agent_log": ["AI Safe Mode"],
                },
                None,
            )

        try:
            raw, error = self._engine.generate_sql(
                question=text,
                module=module,
                context_db=context_db,
                history=history,
                company_code=company_code,
                vistas_reales=vistas_reales,
                modelo_forzado=modelo_forzado,
            )
            if error:
                return {}, error
            return self._normalize_generate_sql_result(raw), None
        except Exception as exc:  # pragma: no cover
            logger.exception("Error en generate_sql: %s", exc)
            return {}, f"Error del motor IA: {exc}"

    def generate_sql_with_retry(
        self,
        question: str,
        session,
        module: str = "GLOBAL",
        context_db: str = "CHAT",
        history: str = "",
        vistas_reales: str = "",
    ) -> tuple[dict, Optional[str]]:
        """Genera el SQL con los reintentos del motor; si no están disponibles, usa generate_sql."""
        self._try_init_engine()
        if not self._engine or not hasattr(self._engine, "generate_sql_with_retry"):
            return self.generate_sql(
                question=question,
                module=module,
                context_db=context_db,
                history=history,
                vistas_reales=vistas_reales,
            )

        try:
            raw, error = self._engine.generate_sql_with_retry(
                question=question,
                session=session,
                module=module,
                context_db=context_db,
                history=history,
                vistas_reales=vistas_reales,
            )
            if error:
                return {}, error
            return self._normalize_generate_sql_result(raw), None
        except Exception as exc:  # pragma: no cover
            logger.exception("Error en generate_sql_with_retry: %s", exc)
            return {}, f"Error del motor IA: {exc}"

    def generate_correction(self, failed_sql: str, error_msg: str) -> dict:
        """Pide al motor una corrección del SQL fallido (autocuración).

        Si no hay motor o no devuelve SQL, devuelve el SQL original con un aviso.
        """
        self._try_init_engine()
        if self._engine and hasattr(self._engine, "generate_correction"):
            try:
                correction = self._engine.generate_correction(failed_sql, str(error_msg))
                if isinstance(correction, dict) and correction.get("sql"):
                    return correction
            except Exception as exc:  # pragma: no cover
                logger.warning("Auto-curación IA no disponible: %s", exc)

        return {
            "sql": failed_sql,
            "explanation": "No se pudo aplicar auto-curación en este momento.",
        }

    def analyze_images(self, question: str, images_b64: list[str]) -> dict:
        """Delega el análisis de imágenes en base64 al modelo de visión.

        En modo seguro (sin motor cargado) avisa con claridad en lugar de
        fallar en silencio.
        """
        self._try_init_engine()
        if self._engine and hasattr(self._engine, "analyze_images"):
            try:
                return self._engine.analyze_images(question, images_b64)
            except Exception as exc:  # pragma: no cover
                logger.exception("Error en analyze_images: %s", exc)
                return {
                    "explanation": f"No se pudo analizar la imagen en este momento: {exc}",
                    "visualization_type": "text",
                    "agent_log": ["Vision: motor no disponible"],
                }
        return {
            "explanation": self._engine_error
                or "El análisis de imágenes no está disponible en este momento (falta configuración de IA).",
            "visualization_type": "text",
            "agent_log": ["Vision: motor IA no inicializado"],
        }

    def chat_libre(
        self,
        question: str,
        history: str = "",
        alias: str = "VM",
        empresa: str = "",
    ) -> dict:
        """Conversa directamente con el modelo, sin esquema ni guardarraíl de alcance.

        Se usa únicamente cuando el pipeline confirmó que quien pregunta es el
        desarrollador identificado con su seña (core/modo_desarrollador.py);
        para el resto de usuarios este método no se invoca.
        """
        self._try_init_engine()
        if self._engine and hasattr(self._engine, "chat_libre"):
            try:
                return self._engine.chat_libre(
                    question=question, history=history, alias=alias, empresa=empresa
                )
            except Exception as exc:  # pragma: no cover
                logger.exception("Error en chat_libre: %s", exc)
                return {
                    "explanation": f"⚠️ No pude responder en modo libre: {exc}",
                    "visualization_type": "text",
                    "agent_log": ["Modo desarrollador: error del motor"],
                }
        return {
            "explanation": (
                self._engine_error
                or "El motor de IA no está disponible en este momento para la conversación libre."
            ),
            "visualization_type": "text",
            "agent_log": ["Modo desarrollador: motor IA no inicializado"],
        }

    def responder_demo(self, question: str, dataset: dict, history: str = "") -> dict:
        """Responde preguntas del usuario Invitado (rol GUEST) sobre el dataset de demostración.

        Se usa cuando no hay ninguna base de datos real conectada, así que nunca
        toca esquema, SQL ni conector. Si el motor no se inicializó (por
        ejemplo, sin clave de API), arma un resumen determinista con los
        indicadores del propio dataset, sin ninguna llamada externa, para que
        el Invitado nunca se quede sin respuesta.
        """
        self._try_init_engine()
        if self._engine and hasattr(self._engine, "responder_demo"):
            try:
                return self._engine.responder_demo(question=question, dataset=dataset, history=history)
            except Exception as exc:  # pragma: no cover
                logger.exception("Error en responder_demo: %s", exc)

        indicadores = (dataset or {}).get("indicadores_clave", {})
        resumen = "\n".join(f"- **{k}**: {v}" for k, v in indicadores.items()) or (
            "Sin indicadores de ejemplo disponibles."
        )
        return {
            "explanation": (
                "✨ **Demostración de VicMar Data AI** (datos de ejemplo)\n\n"
                "El motor de IA no está disponible en este momento, pero aquí tienes un "
                f"resumen de la empresa de ejemplo:\n\n{resumen}\n\n"
                "Intenta de nuevo en unos segundos, o solicita acceso a datos reales."
            ),
            "visualization_type": "text",
            "agent_log": ["Invitado: motor IA no disponible — resumen determinista"],
        }

    def generate_final_analysis(self, question: str, columns: list, rows: list) -> dict:
        """Devuelve una explicación y un análisis de negocio genéricos según haya o no filas."""
        if not rows:
            return {
                "explanation": "No se encontraron registros para los criterios solicitados.",
                "business_analysis": (
                    "### Diagnostico\n"
                    "No hay resultados disponibles con los filtros actuales. "
                    "Se recomienda revisar el periodo o los parametros de busqueda."
                ),
                "visualization_type": "text",
            }

        return {
            "explanation": (
                "Consulta procesada exitosamente."
            ),
            "business_analysis": (
                "### Resumen Ejecutivo\n"
                "Los datos han sido recuperados y organizados para su analisis. "
                "Puede profundizar en los detalles utilizando la tabla interactiva."
            ),
            "visualization_type": "table",
        }


    def generate_error_narrative(self, question: str, sql_error: str) -> str:
        """Traduce un error de SQL a un mensaje claro y accionable para el usuario."""
        _ = question
        error_lower = str(sql_error).lower()
        
        # Errores comunes con mensajes específicos.
        if "invalid column name" in error_lower or "unknown column" in error_lower:
            return (
                "El campo que intentas consultar no existe en la base de datos actual. "
                "Esto puede deberse a que ese dominio no esta sincronizado o el nombre del campo es diferente. "
                "Intenta reformular tu consulta o verifica que tablas estan disponibles preguntando 'que puedo consultar'."
            )
        elif (
            "invalid object name" in error_lower
            or "table doesn't exist" in error_lower
            or ("relation" in error_lower and "does not exist" in error_lower)
            or ("nombre de objeto" in error_lower and ("no es valido" in error_lower or "no es válido" in error_lower))
        ):
            return (
                "La tabla requerida para esta consulta no esta disponible en la base conectada. "
                "Puede que este dominio espejo aun no se haya sincronizado. "
                "Prueba preguntar 'que dominios estan disponibles' para ver las areas activas."
            )
        elif "timeout" in error_lower or "time-out" in error_lower:
            return (
                "La consulta tardo demasiado en ejecutarse. Esto puede pasar con reportes muy amplios. "
                "Intenta agregar filtros de fecha o reducir el alcance de tu pregunta."
            )
        elif "permission" in error_lower or "denied" in error_lower:
            # Este error no tiene relación con el rol del usuario (incluido
            # ADMINISTRADOR): es un límite de permisos interno de la conexión
            # que ejecuta el SQL generado por la IA, y salta cuando la IA
            # intenta leer una tabla que esa conexión no puede leer. Atribuirlo
            # al rol sería un mensaje falso que enviaría al usuario a contactar
            # al administrador sin motivo.
            return (
                "No se pudo completar esa consulta por una restricción interna de acceso a datos "
                "(no relacionada con tu usuario ni tu rol). Intenta reformular la pregunta de forma "
                "más específica — por ejemplo, indicando el nombre exacto del dato que buscas."
            )
        elif "syntax" in error_lower or "incorrect syntax" in error_lower:
            return (
                "Hubo un problema al generar la consulta SQL. Esto suele pasar cuando la pregunta es muy compleja. "
                "Intenta reformular tu consulta de manera mas simple o divide tu pregunta en partes."
            )
        else:
            return (
                "No fue posible ejecutar la consulta por un error tecnico. "
                "Recomendacion: verifica que los datos que buscas existen en esta base preguntando "
                "'que puedo consultar de [empresa]'."
            )
