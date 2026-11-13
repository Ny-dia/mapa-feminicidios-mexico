"""Cliente compartido de Firecrawl para los agentes, con caché local.

Firecrawl cobra por página leída (~1 crédito por scrape, ~1 por map), así que
guardamos cada resultado en .cache_firecrawl/ y lo reutilizamos durante
DIAS_CACHE días. Si no hay FIRECRAWL_API_KEY en .env, disponible() regresa
False y los agentes usan su camino anterior (web_fetch / requests).
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from common import ROOT  # también carga .env

CACHE_DIR = ROOT / ".cache_firecrawl"
DIAS_CACHE = 30

# Palabras que suelen aparecer en las URLs de las páginas que explican cómo
# trabaja una organización. Se usan para elegir subpáginas con map().
PALABRAS_RELEVANTES = (
    "metodolog", "nosotr", "quienes", "quiénes", "about", "acerca",
    "informe", "datos", "proyecto", "como-trabajamos",
)

_cliente = None


def disponible() -> bool:
    return bool(os.getenv("FIRECRAWL_API_KEY"))


def _fc():
    global _cliente
    if _cliente is None:
        from firecrawl import Firecrawl
        _cliente = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    return _cliente


def _ruta_cache(clave: str) -> Path:
    return CACHE_DIR / (hashlib.sha256(clave.encode()).hexdigest()[:24] + ".json")


def _leer_cache(clave: str) -> Optional[dict]:
    ruta = _ruta_cache(clave)
    if not ruta.exists():
        return None
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if time.time() - datos.get("_guardado", 0) > DIAS_CACHE * 86400:
        return None
    return datos


def _guardar_cache(clave: str, datos: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    datos["_guardado"] = time.time()
    _ruta_cache(clave).write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def leer_pagina(url: str, usar_cache: bool = True) -> dict:
    """Scrapea una URL y regresa {markdown, status_code, url_final, titulo, error}.
    Nunca lanza excepción: si falla, error trae el mensaje."""
    clave = "scrape:" + url
    if usar_cache and (cacheado := _leer_cache(clave)):
        return cacheado

    try:
        doc = _fc().scrape(url, formats=["markdown"], only_main_content=True, timeout=30000)
        meta = doc.metadata
        datos = {
            "markdown": doc.markdown or "",
            "status_code": getattr(meta, "status_code", None),
            "url_final": getattr(meta, "url", None) or getattr(meta, "source_url", None) or url,
            "titulo": getattr(meta, "title", None) or "",
            "error": getattr(meta, "error", None),
        }
    except Exception as e:  # red, timeout, sitio que bloquea incluso a Firecrawl, sin créditos...
        datos = {"markdown": "", "status_code": None, "url_final": url, "titulo": "",
                 "error": f"{type(e).__name__}: {e}"}

    # Solo cacheamos lo que salió bien, para reintentar los fallos la próxima vez.
    if usar_cache and datos["markdown"] and not datos["error"]:
        _guardar_cache(clave, datos)
    return datos


def subpaginas_relevantes(url: str, maximo: int = 2) -> list[str]:
    """Usa map() para listar URLs del mismo sitio y elige hasta `maximo` que
    parezcan hablar de metodología / quiénes somos / informes."""
    clave = "map:" + url
    if cacheado := _leer_cache(clave):
        links = cacheado["links"]
    else:
        try:
            resultado = _fc().map(url, limit=200)
            links = [l.url for l in resultado.links]
        except Exception:
            return []
        _guardar_cache(clave, {"links": links})

    base = url.rstrip("/")
    elegidas = []
    for link in links:
        if link.rstrip("/") == base or dominio(link) != dominio(url):
            continue
        if any(p in link.lower() for p in PALABRAS_RELEVANTES):
            elegidas.append(link)
        if len(elegidas) >= maximo:
            break
    return elegidas


def dominio(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host
