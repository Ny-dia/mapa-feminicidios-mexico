"""Agente 4: geocodificación fina.

Patrón de dos llamadas: (1) busca en la web la dirección/sede de la
organización con web_search, (2) estructura esa respuesta. Las coordenadas
finales las da Nominatim (OpenStreetMap), no el LLM directamente, para evitar
coordenadas inventadas. Si no se encuentra dirección o falla el geocode, cae
al fallback de la capital del estado.

Uso:
    python agentes/geocodificar.py --csv organizaciones_nuevas.csv
"""

import argparse
import time

import pandas as pd
import requests
from pydantic import BaseModel

from common import (
    COORDENADAS_ESTADO,
    MAX_USES_BUSQUEDA,
    MODEL,
    NOMINATIM_USER_AGENT,
    client,
    normalize_estado,
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PAUSA_ENTRE_LLAMADAS = 1.0  # política de uso de Nominatim: máx 1 req/seg


class DireccionEncontrada(BaseModel):
    direccion: str
    encontrada: bool


def buscar_direccion(nombre: str, estado: str) -> DireccionEncontrada:
    prompt = f"""Busca la dirección física, sede u oficina de la organización
"{nombre}" en {estado}, México. Si no encuentras una dirección exacta pero sí
una ciudad o colonia donde opera, repórtala. Si no encuentras nada útil,
dilo explícitamente.
"""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_USES_BUSQUEDA}],
    )
    texto = "".join(b.text for b in resp.content if b.type == "text")

    resp_estructurado = client.messages.parse(
        model=MODEL,
        max_tokens=400,
        thinking={"type": "disabled"},
        messages=[{
            "role": "user",
            "content": f"A partir de esto, da la dirección más específica y geocodificable "
                       f"posible (incluye ciudad/estado/país) y si de verdad se encontró algo "
                       f"útil.\n\n{texto}",
        }],
        output_format=DireccionEncontrada,
    )
    return resp_estructurado.parsed_output


def geocodificar_nominatim(direccion: str) -> tuple[float, float] | None:
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": direccion, "countrycodes": "mx", "format": "json", "limit": 1},
            headers={"User-Agent": NOMINATIM_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        resultados = resp.json()
    except (requests.RequestException, ValueError):
        return None
    finally:
        time.sleep(PAUSA_ENTRE_LLAMADAS)

    if not resultados:
        return None
    return float(resultados[0]["lat"]), float(resultados[0]["lon"])


def resolver_coordenadas(nombre: str, estado: str) -> tuple[float, float]:
    fallback = COORDENADAS_ESTADO.get(normalize_estado(estado), COORDENADAS_ESTADO["Nacional / Regional"])

    direccion = buscar_direccion(nombre, estado)
    if not direccion.encontrada or not direccion.direccion.strip():
        print("  -> sin dirección específica, usando capital del estado")
        return fallback

    coords = geocodificar_nominatim(direccion.direccion)
    if coords is None:
        print(f"  -> Nominatim no pudo geocodificar '{direccion.direccion}', usando capital del estado")
        return fallback

    print(f"  -> geocodificado: {direccion.direccion} -> {coords}")
    return coords


def main():
    parser = argparse.ArgumentParser(description="Agente de geocodificación fina")
    parser.add_argument("--csv", required=True, help="CSV cuyas filas se van a geocodificar")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    for idx, row in df.iterrows():
        lat, lon = row.get("Latitud"), row.get("Longitud")
        if pd.notna(lat) and pd.notna(lon) and str(lat).strip() and str(lon).strip():
            continue

        nombre = row["Organización"]
        estado = row.get("Estado", "")
        print(f"Geocodificando: {nombre} ({estado})")
        lat_f, lon_f = resolver_coordenadas(nombre, estado)
        df.at[idx, "Latitud"] = lat_f
        df.at[idx, "Longitud"] = lon_f

    df.to_csv(args.csv, index=False)
    print(f"\nActualizado {args.csv}")


if __name__ == "__main__":
    main()
