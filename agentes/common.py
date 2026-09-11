"""Utilidades compartidas por los agentes: cliente Anthropic, constantes del
mapa (reutilizadas de generar_mapa.py para no desincronizarse) y modelos Pydantic."""

import os
import re
import sys
from pathlib import Path
from typing import List, Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from generar_mapa import CATEGORY_COLORS, MX_STATES, normalize_estado  # noqa: E402

load_dotenv(ROOT / ".env")

# En consolas de Windows con encoding cp1252, imprimir texto que venga de la
# API (acentos, emojis) puede tronar con UnicodeEncodeError. Forzamos UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

client = Anthropic()

MODEL = "claude-sonnet-5"

CSV_MAESTRO = ROOT / "organizaciones.csv"
CSV_CANDIDATOS = ROOT / "organizaciones_nuevas.csv"
CSV_REPORTE_QA = ROOT / "reporte_qa.csv"

CSV_COLUMNS = [
    "Organización",
    "Latitud",
    "Longitud",
    "Estado",
    "Metodología de Registro",
    "Tipo de Datos y Productos",
    "Tipo de Organización o Proyecto",
    "Contacto",
]

CATEGORIAS_VALIDAS = list(CATEGORY_COLORS.keys())

MAX_USES_BUSQUEDA = 5
MAX_USES_FETCH = 2

NOMINATIM_USER_AGENT = "mapa-feminicidios-mexico/1.0 (https://github.com/Ny-dia/mapa-feminicidios-mexico)"

# Coordenadas de referencia (capital) por estado — fallback cuando no se
# encuentra o no se puede geocodificar la dirección exacta de una organización.
COORDENADAS_ESTADO = {
    "Aguascalientes": (21.8853, -102.2916),
    "Baja California": (32.5027, -117.0037),
    "Baja California Sur": (24.1426, -110.3128),
    "Campeche": (19.8301, -90.5349),
    "Chiapas": (16.7569, -93.1292),
    "Chihuahua": (28.6353, -106.0889),
    "Ciudad de México": (19.4326, -99.1332),
    "Coahuila": (25.4260, -101.0053),
    "Colima": (19.2433, -103.7250),
    "Durango": (24.0277, -104.6532),
    "Estado de México": (19.2926, -99.6557),
    "Guanajuato": (21.0190, -101.2574),
    "Guerrero": (17.5506, -99.5024),
    "Hidalgo": (20.0911, -98.7624),
    "Jalisco": (20.6597, -103.3496),
    "Michoacán": (19.7008, -101.1844),
    "Morelos": (18.9242, -99.2216),
    "Nayarit": (21.5041, -104.8942),
    "Nuevo León": (25.6866, -100.3161),
    "Oaxaca": (17.0732, -96.7266),
    "Puebla": (19.0414, -98.2063),
    "Querétaro": (20.5888, -100.3899),
    "Quintana Roo": (18.5001, -88.2960),
    "San Luis Potosí": (22.1565, -100.9855),
    "Sinaloa": (24.8091, -107.3940),
    "Sonora": (29.0729, -110.9559),
    "Tabasco": (17.9869, -92.9303),
    "Tamaulipas": (23.7369, -99.1411),
    "Tlaxcala": (19.3139, -98.2404),
    "Veracruz": (19.1738, -96.1342),
    "Yucatán": (20.9674, -89.5926),
    "Zacatecas": (22.7709, -102.5832),
    # Etiqueta de generar_mapa.py para registros no atados a un solo estado.
    "Nacional / Regional": (23.6345, -102.5528),
}


class Organizacion(BaseModel):
    organizacion: str
    estado: str
    metodologia_de_registro: str
    tipo_de_datos_y_productos: str
    categoria: str
    contacto: str


class ListaOrganizaciones(BaseModel):
    organizaciones: List[Organizacion]


class Clasificacion(BaseModel):
    metodologia_de_registro: str
    tipo_de_datos_y_productos: str
    categoria: str


def normalizar_nombre(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(nombre).lower())


def categoria_valida(categoria: str) -> Optional[str]:
    """Devuelve la categoría tal cual si es una de las 5 válidas, si no None."""
    return categoria if categoria in CATEGORIAS_VALIDAS else None
