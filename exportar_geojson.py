"""Convierte organizaciones.csv en mapa3d/organizaciones.geojson para el mapa 3D.

Uso:  python exportar_geojson.py

- Separa las categorías múltiples de "Tipo de Organización o Proyecto".
- Lee "Estados que cubre": "Nacional" o una lista separada por ";".
- Varias fichas comparten exactamente las mismas coordenadas (p. ej. el centro
  de CDMX); para que no queden encimadas se reparten en un círculo pequeño
  (~1.5 km) y se marcan con "posicion_desplazada": true.
"""
import json
import math
from collections import defaultdict

import pandas as pd

CSV_PATH = "organizaciones.csv"
OUT_PATH = "mapa3d/organizaciones.geojson"

CATEGORIAS = [
    "Observatorio / informe estadístico",
    "Base de datos / mapa interactivo",
    "Arte y memoria",
    "Periodismo / documentación independiente",
    "Incidencia y defensa legal",
]



def categorias_de(texto):
    texto = str(texto)
    encontradas = [c for c in CATEGORIAS if c in texto]
    return encontradas or ["Sin categoría"]


def cobertura_de(texto):
    texto = str(texto).strip()
    if texto.lower() == "nacional":
        return True, []
    return False, [e.strip() for e in texto.split(";") if e.strip()]


def repartir_encimadas(df):
    """Desplaza ligeramente las fichas que comparten coordenadas idénticas."""
    grupos = defaultdict(list)
    for i, fila in df.iterrows():
        grupos[(round(fila["Latitud"], 4), round(fila["Longitud"], 4))].append(i)
    pos = {}
    for (lat, lon), idx in grupos.items():
        if len(idx) == 1:
            pos[idx[0]] = (lat, lon, False)
            continue
        radio = 0.012 + 0.0006 * len(idx)
        for k, i in enumerate(idx):
            ang = 2 * math.pi * k / len(idx)
            pos[i] = (lat + radio * math.sin(ang),
                      lon + radio * math.cos(ang) / math.cos(math.radians(lat)), True)
    return pos


def main():
    df = pd.read_csv(CSV_PATH)
    posiciones = repartir_encimadas(df)
    features = []
    for i, fila in df.iterrows():
        lat, lon, desplazada = posiciones[i]
        nacional, estados = cobertura_de(fila.get("Estados que cubre", fila["Estado"]))
        cats = categorias_de(fila["Tipo de Organización o Proyecto"])
        props = {
            "id": int(i),
            "nombre": fila["Organización"],
            "estado": fila["Estado"],
            "metodologia": fila["Metodología de Registro"],
            "productos": fila["Tipo de Datos y Productos"],
            "categorias": cats,
            "contacto": "" if pd.isna(fila["Contacto"]) else str(fila["Contacto"]),
            "nacional": nacional,
            "cobertura": ["Nacional"] if nacional else estados,
            "posicion_desplazada": desplazada,
        }
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props,
        })
    salida = {"type": "FeatureCollection", "features": features,
              "categorias": CATEGORIAS}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"{len(features)} organizaciones, {sum(p['properties']['nacional'] for p in features)} "
          f"nacionales -> {OUT_PATH}")


if __name__ == "__main__":
    main()
