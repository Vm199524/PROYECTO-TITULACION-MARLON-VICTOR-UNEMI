"""
Procesador semántico del chat: traductor de términos y caché de consultas.

Traduce términos coloquiales de la pregunta a la vista técnica que les
corresponde (data/diccionario_semantico.json) y guarda las consultas exitosas
con el nombre de la base abstraído como {DB}, aisladas por empresa y por motor
de IA para que una respuesta nunca se reutilice en otra empresa.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import json
import os
import pathlib
import re
import unicodedata
from typing import Optional, Tuple, Dict, Any

class SemanticProcessor:
    """Procesador semántico de preguntas en lenguaje natural.

    Implementa:
    1. Traductor de términos: asocia términos coloquiales con vistas técnicas.
    2. Caché semántico: guarda intenciones resueltas con el marcador {DB}.
    """

    def __init__(self):
        self.base_dir = pathlib.Path(__file__).parent.parent
        self.dict_path = self.base_dir / "data" / "diccionario_semantico.json"
        self.cache_path = self.base_dir / "cache" / "semantic_query_cache.json"
        self.dictionary = self._load_dictionary()
        self._ensure_cache_exists()

    def _load_dictionary(self) -> dict:
        """Carga el diccionario semántico; si falla, devuelve uno sin mapeos."""
        try:
            if self.dict_path.exists():
                with open(self.dict_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[SEMANTIC] Error cargando diccionario: {e}")
        return {"mappings": []}

    def _ensure_cache_exists(self):
        """Crea el archivo de caché vacío si todavía no existe."""
        self.cache_path.parent.mkdir(exist_ok=True)
        if not self.cache_path.exists():
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def normalize_text(self, text: str) -> str:
        """Normaliza el texto: quita tildes y signos de puntuación y lo pasa a minúsculas."""
        s = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        s = re.sub(r'[?!¿¡.,;:]', '', s)
        return s.lower().strip()

    def translate_intent(self, prompt: str) -> Optional[str]:
        """Busca términos coloquiales en la pregunta y sugiere la vista técnica correspondiente.

        Returns:
            La plantilla de vista del primer mapeo que coincide, o None.
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
        """Construye la clave del caché con la empresa, el motor de IA y la pregunta normalizada.

        La empresa es obligatoria en la clave porque todas las consultas se
        ejecutan contra la base `CHAT` (`active_db` es "CHAT" para todas las
        empresas): sin ella, una respuesta guardada en la empresa A se
        serviría en la empresa B, con su explicación y posiblemente sus
        números, lo que sería una fuga de datos entre empresas.

        El motor (flash, pro o un proveedor puntual) aísla la memoria de cada
        uno: preguntar lo mismo con Flash y con Pro guarda y sirve dos
        entradas distintas, sin cruce entre motores.
        """
        empresa = str(company_code or "SIN_EMPRESA").strip().upper()
        motor_key = (motor or "flash").strip().lower()
        return f"{empresa}::{motor_key}::{self.normalize_text(prompt)}"

    def get_cached_query(
        self, prompt: str, active_db: str, company_code: str = "", motor: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Busca la pregunta en el caché semántico y reemplaza {DB} por la base actual.

        Una coincidencia solo es válida dentro de la misma empresa y el mismo
        motor de IA.

        Returns:
            Copia de la entrada con el SQL listo y `cache_hit=True`, o None.
        """
        clave = self._clave_cache(prompt, company_code, motor)
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)

            # Las entradas guardadas con una clave sin empresa nunca coinciden
            # con la clave actual: no se sabe de qué empresa provienen, así que
            # se tratan como no confiables.
            entry = cache.get(clave)
            if entry:
                # Reemplazo dinámico de la base de datos en el SQL guardado
                sql_template = entry.get("sql", "")
                # Sustituye el marcador {DB} por la base activa entre corchetes.
                final_sql = sql_template.replace("{DB}", f"[{active_db}]")
                final_sql = final_sql.replace("[{DB}]", f"[{active_db}]")
                
                # El caché siempre guarda el SQL con marcadores; si una entrada no
                # los tiene, se devuelve tal cual.
                
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
        """Guarda una consulta exitosa en el caché.

        Abstrae el nombre de la base de datos como {DB} y aísla la entrada por
        empresa y por motor de IA.
        """
        norm_prompt = self._clave_cache(prompt, company_code, motor)
        # Se abstrae el nombre de la base activa para que la entrada sea
        # reutilizable: se busca entre corchetes o como palabra suelta y se
        # reemplaza por {DB}.
        
        sql_template = sql
        if active_db:
            # Escapa los caracteres especiales del nombre de la base.
            safe_db = re.escape(active_db)
            # Reemplaza [DB_NAME] por {DB}.
            sql_template = re.sub(rf'\[{safe_db}\]', '{DB}', sql, flags=re.IGNORECASE)
            # Si no estaba entre corchetes (poco frecuente en este sistema), se
            # busca como palabra suelta.
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
