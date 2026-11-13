"""Agente 2: extracción/clasificación a partir de un link.

Dado un link, lee la fuente y completa Metodología de Registro, Tipo de Datos
y Productos, y Tipo de Organización o Proyecto.

Si hay FIRECRAWL_API_KEY en .env, lee la página con Firecrawl (más la página de
metodología / quiénes somos si la encuentra) y hace UNA llamada a Claude. Si no,
usa el camino anterior con la herramienta web_fetch de Claude.

Uso:
    python agentes/clasificar.py --url https://ejemplo.org
    python agentes/clasificar.py --csv organizaciones_nuevas.csv
"""

import argparse
import re
from typing import Optional

import pandas as pd

from common import (
    CATEGORIAS_VALIDAS,
    MAX_USES_FETCH,
    MODEL,
    Clasificacion,
    categoria_valida,
    client,
)
import firecrawl_client

UMBRAL_VAGO = 15
MAX_CHARS_POR_PAGINA = 12000  # recorta páginas larguísimas para no gastar tokens de más
MIN_CHARS_UTILES = 300        # menos que esto = la página casi no tiene texto  # texto con menos de N caracteres se considera vacío/vago
URL_PATTERN = re.compile(r"https?://\S+")


def primera_url(contacto: str) -> str:
    """La columna Contacto guarda varios datos separados por ' | '; toma la
    primera URL real que encuentre (ignora teléfonos, emails, direcciones)."""
    match = URL_PATTERN.search(str(contacto or ""))
    return match.group(0).rstrip(".,;") if match else ""


INSTRUCCIONES_CLASIFICACION = f"""Describe con el mayor detalle posible:
1) Qué metodología usa esta organización o proyecto para registrar/documentar feminicidios
   (ej. monitoreo hemerográfico, reportes ciudadanos, solicitudes de información pública, etc.)
2) Qué tipo de datos o productos genera (base de datos descargable, mapa interactivo,
   minidocumental, performance, reporte anual, etc.)
3) A cuál de estas 5 categorías pertenece: {", ".join(CATEGORIAS_VALIDAS)}

Para categoria usa exactamente una de esas opciones. Basa todo SOLO en el texto
de las páginas; si algo no aparece ahí, deja ese campo como cadena vacía."""


def clasificar_fuente(url: str) -> Optional[Clasificacion]:
    if firecrawl_client.disponible():
        return clasificar_con_firecrawl(url)
    return clasificar_con_web_fetch(url)


def clasificar_con_firecrawl(url: str) -> Optional[Clasificacion]:
    paginas = []
    for u in [url] + firecrawl_client.subpaginas_relevantes(url):
        pagina = firecrawl_client.leer_pagina(u)
        if pagina["error"]:
            print(f"  -> Firecrawl no pudo leer {u}: {pagina['error']}")
            continue
        if pagina["markdown"].strip():
            paginas.append((u, pagina["markdown"][:MAX_CHARS_POR_PAGINA]))

    total = sum(len(md) for _, md in paginas)
    if total < MIN_CHARS_UTILES:
        print(f"  -> muy poco texto legible ({total} caracteres); "
              f"puede ser un sitio solo de redes sociales o con contenido en imágenes")
        return None

    print(f"  -> leídas {len(paginas)} página(s): {', '.join(u for u, _ in paginas)}")
    contenido = "\n\n".join(f"### Página: {u}\n\n{md}" for u, md in paginas)
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=1500,
        thinking={"type": "disabled"},
        messages=[{
            "role": "user",
            "content": f"{INSTRUCCIONES_CLASIFICACION}\n\n<paginas>\n{contenido}\n</paginas>",
        }],
        output_format=Clasificacion,
    )
    return resp.parsed_output


def clasificar_con_web_fetch(url: str) -> Optional[Clasificacion]:
    prompt = f"""Lee el contenido de esta página: {url}

Describe con el mayor detalle posible:
1) Qué metodología usa esta organización o proyecto para registrar/documentar feminicidios
   (ej. monitoreo hemerográfico, reportes ciudadanos, solicitudes de información pública, etc.)
2) Qué tipo de datos o productos genera (base de datos descargable, mapa interactivo,
   minidocumental, performance, reporte anual, etc.)
3) A cuál de estas 5 categorías pertenece: {", ".join(CATEGORIAS_VALIDAS)}

Si la página no da información suficiente, dilo explícitamente.
"""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": MAX_USES_FETCH}],
    )
    texto = "".join(b.text for b in resp.content if b.type == "text")
    if not texto.strip():
        return None

    resp_estructurado = client.messages.parse(
        model=MODEL,
        max_tokens=800,
        thinking={"type": "disabled"},
        messages=[{
            "role": "user",
            "content": f"Resume esta descripción en el formato pedido. Para categoria usa "
                       f"exactamente una de estas opciones: {', '.join(CATEGORIAS_VALIDAS)}. "
                       f"Si algo no está disponible usa cadena vacía.\n\n{texto}",
        }],
        output_format=Clasificacion,
    )
    return resp_estructurado.parsed_output


def clasificar_url_suelta(url: str) -> None:
    clasificacion = clasificar_fuente(url)
    if clasificacion is None:
        print("No se pudo extraer información de esa fuente.")
        return
    print(f"Metodología de Registro:\n  {clasificacion.metodologia_de_registro}\n")
    print(f"Tipo de Datos y Productos:\n  {clasificacion.tipo_de_datos_y_productos}\n")
    categoria = categoria_valida(clasificacion.categoria)
    if categoria:
        print(f"Tipo de Organización o Proyecto:\n  {categoria}")
    else:
        print(f"Tipo de Organización o Proyecto:\n  [ADVERTENCIA: '{clasificacion.categoria}' "
              f"no es una categoría válida — revisar a mano]")


def rellenar_csv(csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    for idx, row in df.iterrows():
        metodologia = str(row.get("Metodología de Registro", "") or "")
        tipo_datos = str(row.get("Tipo de Datos y Productos", "") or "")
        categoria = str(row.get("Tipo de Organización o Proyecto", "") or "")
        enlace = primera_url(row.get("Contacto", ""))

        necesita = (
            len(metodologia) < UMBRAL_VAGO
            or len(tipo_datos) < UMBRAL_VAGO
            or categoria not in CATEGORIAS_VALIDAS
        )
        if not necesita or not enlace:
            continue

        print(f"Clasificando: {row.get('Organización', '(sin nombre)')} <- {enlace}")
        clasificacion = clasificar_fuente(enlace)
        if clasificacion is None:
            print("  -> sin resultado, se deja como está")
            continue

        if len(metodologia) < UMBRAL_VAGO and clasificacion.metodologia_de_registro:
            df.at[idx, "Metodología de Registro"] = clasificacion.metodologia_de_registro
        if len(tipo_datos) < UMBRAL_VAGO and clasificacion.tipo_de_datos_y_productos:
            df.at[idx, "Tipo de Datos y Productos"] = clasificacion.tipo_de_datos_y_productos
        if categoria not in CATEGORIAS_VALIDAS:
            categoria_nueva = categoria_valida(clasificacion.categoria)
            if categoria_nueva:
                df.at[idx, "Tipo de Organización o Proyecto"] = categoria_nueva
            else:
                print(f"  -> ADVERTENCIA: categoría '{clasificacion.categoria}' no es válida, revisar a mano")

    df.to_csv(csv_path, index=False)
    print(f"\nActualizado {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Agente extractor/clasificador")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Clasificar una sola fuente y mostrar el resultado")
    group.add_argument("--csv", help="Rellenar campos vacíos/vagos en un CSV de candidatos")
    args = parser.parse_args()

    if args.url:
        clasificar_url_suelta(args.url)
    else:
        rellenar_csv(args.csv)


if __name__ == "__main__":
    main()
