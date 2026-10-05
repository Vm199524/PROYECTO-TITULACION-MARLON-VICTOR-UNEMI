"""
Consolidación de las consultas exitosas en memoria de largo plazo.

Analiza la caché de consultas exitosas de un contexto de base de datos,
identifica las tablas más consultadas y las guarda, junto con pistas de
negocio, en consolidated_patterns.json como memoria permanente del motor
NL2SQL.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import json
import logging
import pathlib
from datetime import datetime
from collections import Counter
from cache.query_cache import load_cache

logger = logging.getLogger(__name__)

class MemoryConsolidator:
    """Extrae patrones de uso de la caché de consultas exitosas de un contexto.

    Sirve para que el motor NL2SQL sepa qué tablas son las más confiables
    para ciertos temas.
    """
    def __init__(self, db_context: str):
        self.db_context = db_context
        self.memory_path = pathlib.Path(__file__).parent / "consolidated_patterns.json"

    def consolidar(self):
        """Consolida la memoria del contexto a partir de su caché de consultas.

        Toma las entradas de la caché cuya clave empieza por el contexto,
        cuenta la tabla que sigue al primer FROM de cada SQL y guarda las 5
        más usadas; si el contexto contiene "PROYECTO", agrega pistas fijas
        de negocio sobre las vistas de nómina.

        Returns:
            El conocimiento guardado, o {} si no hay historial del contexto.
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
            # Extracción simple: solo la tabla que sigue al primer FROM (no
            # analiza JOIN ni subconsultas; un parser de SQL sería más preciso).
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
        """Guarda la memoria del contexto sin borrar la de otros; un error solo se registra en el log."""
        try:
            # Se carga la memoria existente para no pisar la de otros contextos.
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
    """Ejecuta la consolidación de memoria del contexto indicado y devuelve su resultado."""
    consolidator = MemoryConsolidator(db_context)
    return consolidator.consolidar()
