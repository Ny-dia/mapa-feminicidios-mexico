"""Agente 6: busca el sitio web y las redes sociales OFICIALES de cada
organización y los pone en la columna "Contacto".

Cómo funciona:
1. Busca el nombre de la organización + estado con Firecrawl (y, si no salen
   redes, una segunda búsqueda agregando "facebook instagram").
2. Claude revisa los resultados (URL, título y descripción) y elige solo las
   cuentas y sitios que son DE la organización: descarta notas de prensa,
   publicaciones de otras cuentas y perfiles personales de integrantes.
3. Se descarta cualquier URL que no haya salido tal cual en la búsqueda, para
   que el modelo no pueda inventar links.

Domicilios: si la organización es FORMAL (A.C., IAP, fundación, instituto,
universidad) y algún resultado trae su domicilio, también lo agrega como
"Dirección:" (o "Dirección (parcial):" si falta calle o número). A colectivas,
artistas y movimientos nunca se les agrega domicilio, por la misma razón de
seguridad que en buscar_domicilios.py. Nunca agrega teléfonos personales.

Por default solo procesa filas cuyo Contacto está vacío o solo tiene
"Fuente:" (la nota de prensa donde se encontró la organización). Las "Fuente:"
se quitan cuando se encuentra algo oficial; si no se encuentra nada, la fila
se deja igual.

Uso:
    python agentes/buscar_redes.py --csv organizaciones_nuevas.csv
    python agentes/buscar_redes.py --csv organizaciones_nuevas.csv "Nombre exacto 1" "Nombre exacto 2"
    python agentes/buscar_redes.py --csv organizaciones_nuevas.csv --simular   # no escribe el CSV

Requiere FIRECRAWL_API_KEY en .env. Gasta créditos de Firecrawl por cada
búsqueda (una o dos por organización).
"""

import argparse
import re
import sys
from typing import List

import pandas as pd
from pydantic import BaseModel

import firecrawl_client
from common import MODEL, client

COLUMNA_CONTACTO = "Contacto"
LIMITE_RESULTADOS = 10

# Etiqueta que se escribe en Contacto según el dominio. Lo que no esté aquí
# se etiqueta como "Web".
ETIQUETAS = {
    "facebook.com": "Facebook",
    "m.facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "x.com": "X",
    "twitter.com": "X",
    "tiktok.com": "TikTok",
    "youtube.com": "YouTube",
    "linkedin.com": "LinkedIn",
    "linktr.ee": "Linktree",
    "threads.net": "Threads",
}
REDES = set(ETIQUETAS.values())


class EnlaceOficial(BaseModel):
    url: str
    por_que: str


class EnlacesOficiales(BaseModel):
    enlaces: List[EnlaceOficial]
    domicilio: str = ""
    domicilio_completo: bool = False


# Organizaciones con registro formal: solo a estas se les agrega domicilio.
PATRON_FORMAL = re.compile(
    r"\bA\.?\s?C\.?(?=\W|$)|\bI\.?\s?A\.?\s?P\.?(?=\W|$)|fundaci[oó]n|instituto|universidad|UAGro",
    re.IGNORECASE,
)


def es_formal(nombre: str) -> bool:
    return bool(PATRON_FORMAL.search(nombre))


def etiqueta(url: str) -> str:
    # Reconoce subdominios: mx.linkedin.com, es-la.facebook.com, m.facebook.com...
    host = firecrawl_client.dominio(url)
    for dominio_red, nombre in ETIQUETAS.items():
        if host == dominio_red or host.endswith("." + dominio_red):
            return nombre
    return "Web"


def limpiar_url(url: str) -> str:
    """En redes sociales quita ?lang=, ?locale= y demás parámetros: la cuenta es la misma."""
    if etiqueta(url) in REDES:
        return url.split("?")[0].split("#")[0]
    return url


def piezas_contacto(contacto: str) -> list[str]:
    contacto = str(contacto or "").strip()
    if not contacto or contacto.lower() == "nan":
        return []
    return [p.strip() for p in contacto.split("|") if p.strip()]


def necesita_busqueda(contacto: str) -> bool:
    piezas = piezas_contacto(contacto)
    return not piezas or all(p.startswith("Fuente:") for p in piezas)


def elegir_oficiales(nombre: str, estado: str, resultados: list[dict]) -> tuple[list[EnlaceOficial], str]:
    """Regresa (enlaces oficiales, domicilio). El domicilio solo se pide a
    organizaciones formales y viene vacío si no aparece en los resultados."""
    if not resultados:
        return [], ""
    formal = es_formal(nombre)
    instruccion_domicilio = (
        "\nAdemás, si en algún título o descripción aparece el domicilio postal de ESTA "
        "organización, cópialo en `domicilio` tal como aparece (no lo completes ni lo "
        "corrijas) y marca domicilio_completo=true solo si incluye calle y número. "
        "Si no aparece, deja domicilio vacío.\n"
        if formal else
        "\nDeja `domicilio` vacío siempre.\n"
    )
    lista = "\n".join(
        f"{i}. {r['url']}\n   Título: {r['titulo']}\n   Descripción: {r['descripcion']}"
        for i, r in enumerate(resultados, 1)
    )
    prompt = f"""Estos son resultados de búsqueda para la organización "{nombre}" ({estado}, México),
que documenta feminicidios o trabaja contra la violencia hacia las mujeres.

Elige SOLO los enlaces que sean el sitio web oficial o una cuenta oficial en redes
sociales DE ESA organización (su página de Facebook, su perfil de Instagram, su
canal de YouTube, etc.).

Descarta:
- notas de prensa, artículos o PDFs que solo hablan de la organización
- publicaciones o videos sueltos de otras cuentas
- perfiles personales de integrantes
- organizaciones con nombre parecido pero de otro estado, de otro país o de otro tema
- dependencias de gobierno (fiscalías, institutos de la mujer, secretarías)
- enlaces a una publicación específica si no es la página principal de la cuenta

{instruccion_domicilio}
Si dudas de que una cuenta sea de esa organización, NO la incluyas. Es mejor
regresar una lista vacía que un enlace equivocado. Copia cada URL exactamente
como aparece.

{lista}
"""
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=1000,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
        output_format=EnlacesOficiales,
    )
    urls_validas = {r["url"] for r in resultados}
    elegidos = []
    for enlace in resp.parsed_output.enlaces:
        if enlace.url not in urls_validas:
            print(f"  -> descartado (no salió en la búsqueda): {enlace.url}")
            continue
        enlace.url = limpiar_url(enlace.url)
        elegidos.append(enlace)
    domicilio = resp.parsed_output.domicilio.strip() if formal else ""
    if domicilio:
        etiqueta_dom = "Dirección" if resp.parsed_output.domicilio_completo else "Dirección (parcial)"
        domicilio = f"{etiqueta_dom}: {domicilio}"
    return elegidos, domicilio


def buscar_enlaces(nombre: str, estado: str) -> tuple[list[EnlaceOficial], str]:
    resultados = firecrawl_client.buscar(f'"{nombre}" {estado}', LIMITE_RESULTADOS)
    elegidos, domicilio = elegir_oficiales(nombre, estado, resultados)

    if not any(etiqueta(e.url) in REDES for e in elegidos):
        extra = firecrawl_client.buscar(f"{nombre} {estado} facebook instagram", LIMITE_RESULTADOS)
        vistos = {r["url"] for r in resultados}
        extra = [r for r in extra if r["url"] not in vistos]
        mas, domicilio_extra = elegir_oficiales(nombre, estado, extra)
        elegidos += mas
        domicilio = domicilio or domicilio_extra

    # Una URL por etiqueta+URL, en orden de aparición.
    unicos, vistos = [], set()
    for e in elegidos:
        clave = e.url.rstrip("/").lower()
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(e)
    return unicos, domicilio


def main():
    parser = argparse.ArgumentParser(description="Agente buscador de web y redes oficiales")
    parser.add_argument("--csv", required=True, help="CSV a actualizar (columna Contacto)")
    parser.add_argument("nombres", nargs="*", help="Nombres exactos a procesar (default: filas sin contacto oficial)")
    parser.add_argument("--simular", action="store_true", help="Muestra lo que encontraría sin escribir el CSV")
    args = parser.parse_args()

    if not firecrawl_client.disponible():
        sys.exit("Falta FIRECRAWL_API_KEY en .env — este agente la necesita.")

    df = pd.read_csv(args.csv)
    if COLUMNA_CONTACTO not in df.columns:
        df[COLUMNA_CONTACTO] = ""

    if args.nombres:
        filas = df.index[df["Organización"].isin(args.nombres)].tolist()
        faltantes = set(args.nombres) - set(df.loc[filas, "Organización"])
        for n in faltantes:
            print(f"ADVERTENCIA: '{n}' no está en {args.csv}, se omite")
    else:
        filas = [i for i in df.index if necesita_busqueda(df.at[i, COLUMNA_CONTACTO])]

    print(f"Buscando web/redes para {len(filas)} organización(es)\n")
    encontradas = 0
    for i in filas:
        nombre = str(df.at[i, "Organización"])
        estado = str(df.at[i, "Estado"])
        print(f"{nombre} ({estado})")
        enlaces, domicilio = buscar_enlaces(nombre, estado)
        if not enlaces and not domicilio:
            print("  -> nada oficial encontrado, se deja como está\n")
            continue

        for e in enlaces:
            print(f"  + {etiqueta(e.url)}: {e.url}  ({e.por_que})")
        if domicilio:
            print(f"  + {domicilio}")
        print()
        encontradas += 1

        actuales = [p for p in piezas_contacto(df.at[i, COLUMNA_CONTACTO]) if not p.startswith("Fuente:")]
        ya_estan = " ".join(actuales).lower()
        nuevas = [f"{etiqueta(e.url)}: {e.url}" for e in enlaces if e.url.rstrip("/").lower() not in ya_estan]
        if domicilio and not any(p.startswith("Dirección") for p in actuales):
            nuevas.append(domicilio)
        df.at[i, COLUMNA_CONTACTO] = " | ".join(nuevas + actuales)

    print(f"Con enlaces nuevos: {encontradas} de {len(filas)}")
    if args.simular:
        print("(--simular: no se escribió el CSV)")
        return
    df.to_csv(args.csv, index=False)
    print(f"Actualizado {args.csv} — revisa los enlaces antes de fusionar con organizaciones.csv")


if __name__ == "__main__":
    main()
