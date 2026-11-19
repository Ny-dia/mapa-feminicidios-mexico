"""Convierte organizaciones.csv en mapa3d/organizaciones.geojson para el mapa 3D.

Uso:  python exportar_geojson.py

- Separa las categorías múltiples de "Tipo de Organización o Proyecto".
- Lee "Estados que cubre": "Nacional" o una lista separada por ";".
- Genera arcos sólo hacia los estados cubiertos distintos al estado sede.
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

# Coordenadas de las capitales estatales, usadas como destino de los arcos.
CAPITALES = {
    "Aguascalientes": (21.8818, -102.2916), "Baja California": (32.6245, -115.4523),
    "Baja California Sur": (24.1426, -110.3128), "Campeche": (19.8301, -90.5349),
    "Chiapas": (16.7516, -93.1029), "Chihuahua": (28.6353, -106.0889),
    "Ciudad de México": (19.4326, -99.1332), "Coahuila": (25.4383, -100.9737),
    "Colima": (19.2433, -103.7250), "Durango": (24.0277, -104.6532),
    "Estado de México": (19.2826, -99.6557), "Guanajuato": (21.0190, -101.2574),
    "Guerrero": (17.5515, -99.5006), "Hidalgo": (20.1011, -98.7591),
    "Jalisco": (20.6597, -103.3496), "Michoacán": (19.7060, -101.1950),
    "Morelos": (18.9242, -99.2216), "Nayarit": (21.5039, -104.8946),
    "Nuevo León": (25.6866, -100.3161), "Oaxaca": (17.0732, -96.7266),
    "Puebla": (19.0414, -98.2063), "Querétaro": (20.5888, -100.3899),
    "Quintana Roo": (18.5001, -88.2961), "San Luis Potosí": (22.1565, -100.9855),
    "Sinaloa": (24.8091, -107.3940), "Sonora": (29.0729, -110.9559),
    "Tabasco": (17.9892, -92.9475), "Tamaulipas": (23.7369, -99.1411),
    "Tlaxcala": (19.3139, -98.2404), "Veracruz": (19.5438, -96.9102),
    "Yucatán": (20.9674, -89.5926), "Zacatecas": (22.7709, -102.5832),
}


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
    features, arcos = [], []
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
        for destino in estados:
            if destino != fila["Estado"] and destino in CAPITALES:
                dlat, dlon = CAPITALES[destino]
                arcos.append({"id": int(i), "nombre": fila["Organización"],
                              "categoria": cats[0], "desde": [lon, lat],
                              "hacia": [dlon, dlat], "destino": destino})
    salida = {"type": "FeatureCollection", "features": features, "arcos": arcos,
              "categorias": CATEGORIAS}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"{len(features)} organizaciones, {sum(p['properties']['nacional'] for p in features)} "
          f"nacionales, {len(arcos)} arcos -> {OUT_PATH}")


if __name__ == "__main__":
    main()
