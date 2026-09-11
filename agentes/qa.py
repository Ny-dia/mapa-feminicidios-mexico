"""Agente 3: QA de organizaciones.csv. Solo lectura — nunca modifica el CSV
maestro, solo genera un reporte (reporte_qa.csv) para revisión humana.

Checks técnicos (sin IA): duplicados, enlaces rotos, categoría inválida,
coordenadas faltantes o fuera de México.
Check de IA (una llamada batched, sin tools): metodología/tipo de datos vagos,
categoría que no calza con la descripción.

Uso:
    python agentes/qa.py
    python agentes/qa.py --csv otra_ruta.csv
"""

import argparse
import difflib
import re
from concurrent.futures import ThreadPoolExecutor
from typing import List

import pandas as pd
import requests
from pydantic import BaseModel

from common import (
    CATEGORIAS_VALIDAS,
    CSV_MAESTRO,
    CSV_REPORTE_QA,
    MODEL,
    NOMINATIM_USER_AGENT,
    client,
    normalizar_nombre,
)

MEXICO_BBOX = {"lat_min": 14.0, "lat_max": 33.0, "lon_min": -118.0, "lon_max": -86.0}
TAMANO_LOTE_IA = 30
TIMEOUT_ENLACE = 10


class HallazgoQA(BaseModel):
    organizacion: str
    problema: str
    detalle: str


class ListaHallazgosQA(BaseModel):
    hallazgos: List[HallazgoQA]


def check_duplicados(df: pd.DataFrame) -> list[dict]:
    hallazgos = []
    nombres = df["Organización"].fillna("").astype(str).tolist()
    normalizados = [normalizar_nombre(n) for n in nombres]

    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            if normalizados[i] == normalizados[j]:
                hallazgos.append({
                    "organizacion": nombres[i],
                    "tipo_problema": "duplicado_exacto",
                    "detalle": f"Mismo nombre normalizado que fila {j}: '{nombres[j]}'",
                })
            else:
                ratio = difflib.SequenceMatcher(None, normalizados[i], normalizados[j]).ratio()
                if ratio > 0.85:
                    hallazgos.append({
                        "organizacion": nombres[i],
                        "tipo_problema": "posible_duplicado",
                        "detalle": f"Nombre muy similar a fila {j}: '{nombres[j]}' (ratio={ratio:.2f})",
                    })
    return hallazgos


URL_PATTERN = re.compile(r"https?://\S+")


def _check_url(nombre: str, url: str) -> dict | None:
    try:
        resp = requests.get(
            url, timeout=TIMEOUT_ENLACE, headers={"User-Agent": NOMINATIM_USER_AGENT}, allow_redirects=True
        )
        if resp.status_code >= 400:
            return {
                "organizacion": nombre,
                "tipo_problema": "enlace_roto",
                "detalle": f"HTTP {resp.status_code} en {url}",
            }
    except requests.RequestException as e:
        return {"organizacion": nombre, "tipo_problema": "enlace_roto", "detalle": f"{type(e).__name__} en {url}"}
    return None


def _check_contacto(nombre: str, contacto: str) -> list[dict]:
    # La columna Contacto guarda domicilio/teléfono/email/redes separados por
    # ' | '; revisamos cada URL que encontremos ahí (puede haber varias).
    contacto = str(contacto or "").strip()
    if not contacto or contacto.lower() == "nan":
        return [{"organizacion": nombre, "tipo_problema": "contacto_vacio", "detalle": "Sin datos de contacto"}]

    urls = [u.rstrip(".,;") for u in URL_PATTERN.findall(contacto)]
    if not urls:
        return []  # tiene contacto (tel/email/dirección) aunque no tenga link — no es un problema

    hallazgos = []
    for url in urls:
        resultado = _check_url(nombre, url)
        if resultado is not None:
            hallazgos.append(resultado)
    return hallazgos


def check_enlaces(df: pd.DataFrame) -> list[dict]:
    # .fillna("") antes de .astype(str): en pandas con dtype nativo "str",
    # los valores faltantes quedan como float NaN real incluso tras astype(str).
    pares = list(zip(
        df["Organización"].fillna("").astype(str),
        df["Contacto"].fillna("").astype(str),
    ))
    with ThreadPoolExecutor(max_workers=8) as executor:
        resultados = executor.map(lambda p: _check_contacto(*p), pares)
    return [hallazgo for lista in resultados for hallazgo in lista]


def check_categorias(df: pd.DataFrame) -> list[dict]:
    # Una organización puede tener varias categorías separadas por coma (ej. "Incidencia
    # y defensa legal, Observatorio / informe estadístico") — cada una debe ser válida.
    hallazgos = []
    for _, row in df.iterrows():
        categoria_raw = str(row.get("Tipo de Organización o Proyecto", ""))
        partes = [c.strip() for c in categoria_raw.split(",") if c.strip()]
        invalidas = [c for c in partes if c not in CATEGORIAS_VALIDAS]
        if not partes or invalidas:
            hallazgos.append({
                "organizacion": row["Organización"],
                "tipo_problema": "categoria_invalida",
                "detalle": f"'{categoria_raw}' — parte(s) no válida(s): {invalidas or '(vacío)'}",
            })
    return hallazgos


def check_coordenadas(df: pd.DataFrame) -> list[dict]:
    hallazgos = []
    for _, row in df.iterrows():
        lat, lon = row.get("Latitud"), row.get("Longitud")
        if pd.isna(lat) or pd.isna(lon):
            hallazgos.append({
                "organizacion": row["Organización"],
                "tipo_problema": "coordenadas_faltantes",
                "detalle": "Latitud/Longitud vacíos",
            })
            continue
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (TypeError, ValueError):
            hallazgos.append({
                "organizacion": row["Organización"],
                "tipo_problema": "coordenadas_invalidas",
                "detalle": f"No numéricas: lat={lat!r}, lon={lon!r}",
            })
            continue
        if not (MEXICO_BBOX["lat_min"] <= lat_f <= MEXICO_BBOX["lat_max"]
                and MEXICO_BBOX["lon_min"] <= lon_f <= MEXICO_BBOX["lon_max"]):
            hallazgos.append({
                "organizacion": row["Organización"],
                "tipo_problema": "coordenadas_fuera_de_mexico",
                "detalle": f"lat={lat_f}, lon={lon_f} fuera del rango esperado",
            })
    return hallazgos


def check_texto_vago_con_ia(df: pd.DataFrame) -> list[dict]:
    hallazgos = []
    filas = df.to_dict("records")
    for inicio in range(0, len(filas), TAMANO_LOTE_IA):
        lote = filas[inicio:inicio + TAMANO_LOTE_IA]
        resumen = "\n\n".join(
            f"- Organización: {f.get('Organización')}\n"
            f"  Categoría: {f.get('Tipo de Organización o Proyecto')}\n"
            f"  Metodología de Registro: {f.get('Metodología de Registro')}\n"
            f"  Tipo de Datos y Productos: {f.get('Tipo de Datos y Productos')}"
            for f in lote
        )
        prompt = f"""Revisa estas organizaciones del mapa de feminicidios en México y señala,
para cada una que tenga un problema real (no todas lo tendrán), si:
1) "Metodología de Registro" o "Tipo de Datos y Productos" es vago o poco informativo
   (ej. "no especificado", una sola palabra, texto genérico que no dice nada concreto)
2) La "Categoría" no parece calzar con lo que describe la metodología/tipo de datos

Solo reporta los que tengan un problema genuino. Para cada uno da: organizacion, problema
(una frase corta) y detalle (por qué).

{resumen}
"""
        resp = client.messages.parse(
            model=MODEL,
            max_tokens=3000,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
            output_format=ListaHallazgosQA,
        )
        for h in resp.parsed_output.hallazgos:
            hallazgos.append({
                "organizacion": h.organizacion,
                "tipo_problema": "texto_vago_o_categoria_dudosa (IA)",
                "detalle": f"{h.problema}: {h.detalle}",
            })
    return hallazgos


def main():
    parser = argparse.ArgumentParser(description="Agente de QA del CSV maestro")
    parser.add_argument("--csv", default=str(CSV_MAESTRO), help="Ruta al CSV a revisar")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    print(f"Revisando {len(df)} filas de {args.csv}\n")

    hallazgos = []
    print("Checando duplicados...")
    hallazgos += check_duplicados(df)
    print("Checando enlaces...")
    hallazgos += check_enlaces(df)
    print("Checando categorías...")
    hallazgos += check_categorias(df)
    print("Checando coordenadas...")
    hallazgos += check_coordenadas(df)
    print("Checando texto vago/categoría dudosa con IA...")
    hallazgos += check_texto_vago_con_ia(df)

    if not hallazgos:
        print("\nSin hallazgos. Todo se ve bien.")
        return

    df_reporte = pd.DataFrame(hallazgos)
    df_reporte.to_csv(CSV_REPORTE_QA, index=False)

    print(f"\n{len(hallazgos)} hallazgos encontrados:\n")
    for h in hallazgos:
        print(f"  [{h['tipo_problema']}] {h['organizacion']}: {h['detalle']}")
    print(f"\nReporte guardado en {CSV_REPORTE_QA} (organizaciones.csv NO fue modificado)")


if __name__ == "__main__":
    main()
