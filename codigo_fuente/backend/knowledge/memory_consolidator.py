"""
backend/knowledge/memory_consolidator.py
Consolidación de consultas exitosas en reglas de negocio permanentes.
Analiza el historial de consultas para destilar reglas de negocio permanentes.
"""
import json
import logging
import pathlib
from datetime import datetime
from collections import Counter
from cache.query_cache import load_cache

logger = logging.getLogger(__name__)

class MemoryConsolidator:
    """
    Analiza el caché de consultas exitosas para extraer patrones de uso.
    Esto permite que la IA sepa qué tablas son las más confiables para ciertos temas.
    """
    def __init__(self, db_context: str):
        self.db_context = db_context
        self.memory_path = pathlib.Path(__file__).parent / "consolidated_patterns.json"

    def consolidar(self):
        """
        'Sueña' sobre los datos del caché para extraer sabiduría de negocio.
        """
        logger.info(f"[CONSOLIDACION] Iniciando consolidación de memoria para {self.db_context}...")
        
        cache = load_cache()
        if not cache:
            logger.info("[CONSOLIDACION] No hay suficiente historial para consolidar.")
            return {}

        relevant_entries = {k: v for k, v in cache.items() if k.startswith(f"{self.db_context}__")}
        
        if not relevant_entries:
            return {}

        # 1. Identificar entidades más utilizadas (Tablas populares)
        used_tables = []
        for entry in relevant_entries.values():
            sql = str(entry.get("sql", "") or "").upper()
            # Búsqueda simple de tablas en el SQL (Mejorable con Parser en v2)
            if "FROM " in sql:
                parts = sql.split("FROM ")[1].split(" ")[0].replace("[", "").replace("]", "").split(".")
                table = parts[-1] if parts else ""
                if table: used_tables.append(table)

        top_tables = [table for table, count in Counter(used_tables).most_common(5)]

        # 2. Generar el mapa de conocimiento consolidado
        knowledge_dna = {
            "last_consolidation": str(datetime.now()),
            "db_context": self.db_context,
            "high_confidence_entities": top_tables,
            "business_logic_hints": [
                "Priorizar vistas V_Resumen_Nomina para consultas de pagos.",
                "Usar V_Ficha_Maestra para datos personales de empleados."
            ] if "PROYECTO" in self.db_context else []
        }

        # Persistir memoria de largo plazo
        self._save_memory(knowledge_dna)
        logger.info(f"[CONSOLIDACION] Memoria consolidada con {len(top_tables)} entidades clave.")
        return knowledge_dna

    def _save_memory(self, data: dict):
        try:
            # Cargamos memoria existente para no pisar otros contextos
            current_memory = {}
            if self.memory_path.exists():
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    current_memory = json.load(f)
            
            current_memory[self.db_context] = data
            
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(current_memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[CONSOLIDACION] Error al persistir memoria: {e}")

def ejecutar_consolidacion(db_context: str):
    """Ejecuta el ciclo de sueño y consolidación."""
    consolidator = MemoryConsolidator(db_context)
    return consolidator.consolidar()
