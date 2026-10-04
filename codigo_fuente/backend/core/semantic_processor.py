import json
import os
import pathlib
import re
import unicodedata
from typing import Optional, Tuple, Dict, Any

class SemanticProcessor:
    """
    Procesador Semántico para IA con Tri.
    Implementa:
    1. Traductor Humano (Mapping de términos coloquiales a vistas).
    2. Caché Semántico (Almacenamiento de intenciones con placeholders {DB}).
    """

    def __init__(self):
        self.base_dir = pathlib.Path(__file__).parent.parent
        self.dict_path = self.base_dir / "data" / "diccionario_semantico.json"
        self.cache_path = self.base_dir / "cache" / "semantic_query_cache.json"
        self.dictionary = self._load_dictionary()
        self._ensure_cache_exists()

    def _load_dictionary(self) -> dict:
        try:
            if self.dict_path.exists():
                with open(self.dict_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[SEMANTIC] Error cargando diccionario: {e}")
        return {"mappings": []}

    def _ensure_cache_exists(self):
        self.cache_path.parent.mkdir(exist_ok=True)
        if not self.cache_path.exists():
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def normalize_text(self, text: str) -> str:
        s = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        s = re.sub(r'[?!¿¡.,;:]', '', s)
        return s.lower().strip()

    def translate_intent(self, prompt: str) -> Optional[str]:
        """
        Busca términos humanos en el prompt y sugiere la vista técnica correspondiente.
        """
        norm_prompt = self.normalize_text(prompt)
        words = set(norm_prompt.split())
        
        for mapping in self.dictionary.get("mappings", []):
            for term in mapping.get("human_terms", []):
                norm_term = self.normalize_text(term)
                if norm_term in norm_prompt: # Búsqueda por frase/término
                    return mapping.get("view_template")
        return None

    def _clave_cache(self, prompt: str, company_code: str, motor: str = "") -> str:
        """
        Clave del caché: SIEMPRE incluye la empresa, y desde el 30/08/2026
        también el motor de IA (flash, pro o un proveedor puntual).

        Antes la clave era solo el texto de la pregunta. Como en esta
        arquitectura todas las consultas se ejecutan contra la base `CHAT`
        (`active_db` == "CHAT" para todas las empresas), una respuesta
        guardada mientras estaba activa la empresa A se reutilizaba tal cual
        al preguntar lo mismo estando en la empresa B: mismo texto de
        explicación y, si las vistas de CHAT no estaban apuntando a donde
        correspondía, también los mismos números. Es una fuga de datos entre
        empresas y es inaceptable en un producto multiempresa.

        El motor se agregó cuando se creó el selector manual de motores: sin
        esto, una respuesta cacheada mientras el usuario tenía Pro elegido se
        serviría también cuando eligiera Flash para la
        misma pregunta — el "cruce entre motores" que ya se había eliminado
        del camino en vivo, pero que seguía existiendo en el caché. Ahora
        cada motor tiene su propia memoria, aislada de los demás: preguntar
        lo mismo con Flash y con Pro guarda y sirve dos entradas distintas.
        """
        empresa = str(company_code or "SIN_EMPRESA").strip().upper()
        motor_key = (motor or "flash").strip().lower()
        return f"{empresa}::{motor_key}::{self.normalize_text(prompt)}"

    def get_cached_query(
        self, prompt: str, active_db: str, company_code: str = "", motor: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Busca en el caché semántico. Si encuentra un match, reemplaza {DB} por la base actual.
        El match SOLO es válido dentro de la misma empresa Y el mismo motor de IA.
        """
        clave = self._clave_cache(prompt, company_code, motor)
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)

            # Nota: las entradas antiguas (guardadas con la clave sin empresa)
            # se ignoran deliberadamente. No hay forma de saber de qué empresa
            # provienen, así que se tratan como no confiables y se descartan.
            entry = cache.get(clave)
            if entry:
                # Reemplazo dinámico de la base de datos en el SQL guardado
                sql_template = entry.get("sql", "")
                # Reemplazamos tanto {DB} como [DB] o cualquier marcador que hayamos definido
                final_sql = sql_template.replace("{DB}", f"[{active_db}]")
                final_sql = final_sql.replace("[{DB}]", f"[{active_db}]")
                
                # Si el SQL original no tenía placeholders, intentamos inyectar el nombre de la BD si es necesario
                # Pero la regla es que el caché DEBE guardar con placeholders.
                
                result = dict(entry)
                result["sql"] = final_sql
                result["cache_hit"] = True
                return result
        except Exception as e:
            print(f"[SEMANTIC] Error leyendo caché: {e}")
        return None

    def save_to_cache(
        self, prompt: str, sql: str, viz_type: str, explanation: str, active_db: str,
        company_code: str = "", motor: str = "",
    ):
        """
        Guarda una consulta exitosa en el caché, abstrayendo el nombre de la base
        de datos y aislando la entrada por empresa Y por motor de IA.
        """
        norm_prompt = self._clave_cache(prompt, company_code, motor)
        # Abstraer el nombre de la base de datos activa para que sea reusable
        # Buscamos el nombre de la DB entre corchetes o como palabra suelta y lo reemplazamos por {DB}
        
        sql_template = sql
        if active_db:
            # Escapar caracteres especiales en el nombre de la DB
            safe_db = re.escape(active_db)
            # Reemplazar [DB_NAME] o DB_NAME por {DB}
            sql_template = re.sub(rf'\[{safe_db}\]', '{DB}', sql, flags=re.IGNORECASE)
            # Si no estaba con corchetes (poco probable en nuestro sistema pero por si las dudas)
            if sql_template == sql:
                sql_template = re.sub(rf'\b{safe_db}\b', '{DB}', sql, flags=re.IGNORECASE)

        entry = {
            "sql": sql_template,
            "viz_type": viz_type,
            "explanation": explanation,
            "timestamp": datetime.now().isoformat()
        }

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            
            cache[norm_prompt] = entry
            
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[SEMANTIC] Error guardando en caché: {e}")

from datetime import datetime
