"""
Radar de noticias en tiempo real a partir del RSS de Google News.

Detecta preguntas de actualidad que no se responden con la base de datos
(noticias, cargos actuales, cotizaciones) y obtiene titulares recientes sin
costo de API. Las dependencias de red (requests, BeautifulSoup) se importan
dentro de cada método para no cargarlas si el radar no se usa.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import logging
from email.utils import parsedate_to_datetime
from typing import List, Dict

logger = logging.getLogger("Aura-WebReader")

import urllib.parse
import re

class WebReader:
    """Acceso ligero a internet para preguntas de actualidad.

    Usa el RSS de Google News para obtener titulares recientes sin costo de API.
    """

    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    LIVE_QUERY_MARKERS = (
        "en tiempo real", "noticias", "que pasa en el mundo", "ultimo minuto",
        "presidente actual", "guerra", "conflicto en", "google news",
        "elecciones de", "cotizacion de", "que sucede con", "radar de noticias",
    )

    @staticmethod
    def _normalize(text: str) -> str:
        """Pasa el texto a minúsculas y deja solo letras, dígitos y espacios simples."""
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9áéíóúñü\s]", " ", str(text or "").lower())).strip()

    @staticmethod
    def is_live_query(text: str) -> bool:
        """Indica si la pregunta pide información de actualidad.

        Es verdadera si contiene un marcador de LIVE_QUERY_MARKERS o si
        pregunta por un cargo («presidente», «alcalde», «ceo») junto con
        «quién es», «actual» u «hoy».
        """
        normalized = WebReader._normalize(text)
        if not normalized:
            return False
        if any(marker in normalized for marker in WebReader.LIVE_QUERY_MARKERS):
            return True
        role_queries = ("presidente", "presidenta", "primer ministro", "alcalde", "gobernador", "ceo")
        return any(token in normalized for token in role_queries) and any(
            marker in normalized for marker in ("quien es", "quién es", "actual", "hoy")
        )

    @staticmethod
    def _extract_keywords(text: str) -> str:
        """Quita signos, conectores y expresiones coloquiales para armar la búsqueda en Google News."""
        text = text.lower()
        text = re.sub(r'[¿?¡!,.()"\']', '', text)
        
        # Palabras vacías y expresiones coloquiales latinoamericanas comunes.
        stopwords = {
            "que", "quien", "cual", "cuales", "como", "cuando", "donde", "por", "para", "es", "el", "la", "los", "las", 
            "un", "una", "unos", "unas", "de", "del", "al", "a", "en", "con", "y", "o", "actual", "hoy", "ahora", 
            "ahorita", "pana", "mijo", "wey", "guey", "che", "chamo", "mae", "sucede", "pasa", "noticias", 
            "novedades", "sobre", "esto", "este", "esta", "estos", "estas", "dime", "cuentame", "sabes"
        }
        
        words = text.split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return " ".join(keywords) if keywords else text.replace(" ", "+")

    @staticmethod
    def get_news(query: str, limit: int = 5) -> str:
        """Busca noticias de las últimas 24 horas en Google News para la consulta.

        Returns:
            Un boletín numerado con los titulares, un aviso si no hay
            resultados, un texto de error si falla la lectura, o una cadena
            vacía si la consulta tiene menos de 3 caracteres.
        """
        if not query or len(query) < 3:
            return ""

        clean_query = WebReader._extract_keywords(query)
        encoded_query = urllib.parse.quote(type(clean_query) is str and clean_query or "noticias")

        # URL del RSS en español latinoamericano (es-419), limitada a las últimas 24 h.
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:1d&hl=es-419&gl=US&ceid=US:es-419"
        
        try:
            import requests
            from bs4 import BeautifulSoup
            logger.info(f"[RADAR] Input: '{query}' -> Query Limpia: '{clean_query}'")
            response = requests.get(rss_url, timeout=8, headers=WebReader.REQUEST_HEADERS)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all("item")[:limit]

            if not items:
                return "No se encontraron noticias recientes sobre este tema."

            bulletin_lines = ["[BOLETIN DE NOTICIAS DE HOY]:"]
            for i, item in enumerate(items, 1):
                title = item.title.text
                pub_date = item.pubDate.text
                # Retira del título el nombre de la fuente, que va al final tras « - ».
                clean_title = title.rsplit(" - ", 1)[0] if " - " in title else title
                bulletin_lines.append(f"{i}. {clean_title} ({pub_date})")

            return "\n".join(bulletin_lines)

        except Exception as e:
            logger.error(f"[RADAR] Error al leer noticias: {e}")
            return f"Error al recuperar informacion de actualidad: {e}"

    @staticmethod
    def get_general_trends() -> str:
        """Obtiene los 5 titulares generales del momento, sin consulta; cadena vacía si falla."""
        rss_url = "https://news.google.com/rss?hl=es-419&gl=US&ceid=US:es-419"
        try:
            import requests
            from bs4 import BeautifulSoup
            response = requests.get(rss_url, timeout=8, headers=WebReader.REQUEST_HEADERS)
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all("item")[:5]
            
            bulletin_lines = ["[NOTICIAS DEL MOMENTO]:"]
            for i, item in enumerate(items, 1):
                bulletin_lines.append(f"{i}. {item.title.text}")
            return "\n".join(bulletin_lines)
        except Exception:
            return ""

    @staticmethod
    def get_news_entries(query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Devuelve las noticias de las últimas 24 horas como dicts con title, published_at y link.

        Devuelve una lista vacía si la consulta es muy corta o si falla la lectura.
        """
        if not query or len(str(query).strip()) < 3:
            return []
        clean_query = WebReader._extract_keywords(query)
        encoded_query = urllib.parse.quote(clean_query or "noticias")
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:1d&hl=es-419&gl=US&ceid=US:es-419"

        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(rss_url, timeout=8, headers=WebReader.REQUEST_HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all("item")[:limit]
            entries: List[Dict[str, str]] = []
            for item in items:
                title = getattr(item.title, "text", "").strip()
                pub_date = getattr(item.pubDate, "text", "").strip()
                link = getattr(item.link, "text", "").strip()
                clean_title = title.rsplit(" - ", 1)[0] if " - " in title else title
                entries.append(
                    {
                        "title": clean_title,
                        "published_at": pub_date,
                        "link": link,
                    }
                )
            return entries
        except Exception as exc:
            logger.warning("[RADAR] No se pudieron leer entradas de noticias: %s", exc)
            return []

    @staticmethod
    def format_live_brief(query: str, limit: int = 4) -> str:
        """Arma un resumen en texto con los titulares recientes de la consulta.

        Si no hay titulares específicos, recurre a las noticias generales del
        momento y, si tampoco las hay, devuelve un aviso para reintentar.
        """
        entries = WebReader.get_news_entries(query, limit=limit)
        if not entries:
            general = WebReader.get_general_trends()
            if general:
                return (
                    f"No encontre titulares recientes lo bastante claros para '{query}'. "
                    "Te comparto el pulso general del momento:\n"
                    f"{general}"
                )
            return (
                f"No pude recuperar noticias recientes para '{query}' en este momento. "
                "Prueba de nuevo en unos segundos."
            )

        first_date = entries[0].get("published_at", "")
        try:
            dt = parsedate_to_datetime(first_date)
            lead = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            lead = first_date or "hoy"

        lines = [
            f"Resumen en tiempo real para '{query}' basado en titulares recientes de Google News ({lead}):"
        ]
        for idx, item in enumerate(entries, 1):
            published = item.get("published_at", "").strip()
            suffix = f" [{published}]" if published else ""
            lines.append(f"{idx}. {item.get('title', 'Sin titular')}{suffix}")
        lines.append("Si quieres, puedo seguir con un resumen puntual, cronologia o impacto del tema.")
        return "\n".join(lines)
