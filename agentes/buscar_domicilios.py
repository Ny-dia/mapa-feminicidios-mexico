"""Agente 5: busca el domicilio físico oficial de organizaciones formales
(A.C., IAP, Fundaciones, Institutos) y lo agrega a la columna "Contacto" del
CSV (junto con teléfono, email y redes que ya pueda tener esa fila).

Reservado para organizaciones formales con oficina/registro público. NO usar
con colectivos informales, artistas individuales o movimientos activistas:
para esos, buscar y publicar un domicilio implica un riesgo de seguridad real
para las personas involucradas, y muchas veces no existe un domicilio físico
que buscar (son proyectos digitales, arte que viaja entre ciudades, etc.).

Uso:
    python agentes/buscar_domicilios.py --csv ../organizaciones.csv "Nombre org 1" "Nombre org 2" ...
"""

import argparse

import pandas as pd
from pydantic import BaseModel

from common import MAX_USES_BUSQUEDA, MODEL, client

COLUMNA_CONTACTO = "Contacto"


class DomicilioEncontrado(BaseModel):
    domicilio: str
    encontrado: bool


def buscar_domicilio(nombre: str, estado: str) -> DomicilioEncontrado:
    prompt = f"""Busca el domicilio físico OFICIAL (dirección postal completa: calle,
número, colonia, ciudad, código postal si es posible) de la organización
"{nombre}" en {estado}, México. Prioriza la página de "Contacto" de su sitio
oficial, directorios públicos (ej. CLUNI/INDESOL para asociaciones civiles,
Instituto Nacional de las Mujeres) o sus redes sociales oficiales.

Si NO encuentras una dirección postal completa y verificable, dilo
explícitamente — no inventes ni te conformes con solo la ciudad o el estado.
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
            "content": f"Extrae el domicilio postal completo de este texto. Si el texto dice "
                       f"que no se encontró una dirección verificable, deja domicilio vacío y "
                       f"encontrado=false.\n\n{texto}",
        }],
        output_format=DomicilioEncontrado,
    )
    return resp_estructurado.parsed_output


def main():
    parser = argparse.ArgumentParser(description="Agente buscador de domicilios oficiales")
    parser.add_argument("--csv", required=True, help="CSV donde se actualizará la columna Contacto")
    parser.add_argument("nombres", nargs="+", help="Nombres exactos de organizaciones (columna Organización)")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    if COLUMNA_CONTACTO not in df.columns:
        df[COLUMNA_CONTACTO] = ""

    for nombre in args.nombres:
        mask = df["Organización"] == nombre
        if not mask.any():
            print(f"ADVERTENCIA: '{nombre}' no se encontró en {args.csv}, se omite")
            continue

        estado = str(df.loc[mask, "Estado"].values[0])
        print(f"Buscando domicilio: {nombre} ({estado})")
        resultado = buscar_domicilio(nombre, estado)
        if resultado.encontrado and resultado.domicilio.strip():
            contacto_existente = str(df.loc[mask, COLUMNA_CONTACTO].values[0] or "").strip()
            pieza = f"Dirección: {resultado.domicilio}"
            nuevo_contacto = f"{pieza} | {contacto_existente}" if contacto_existente and contacto_existente.lower() != "nan" else pieza
            df.loc[mask, COLUMNA_CONTACTO] = nuevo_contacto
            print(f"  -> {resultado.domicilio}")
        else:
            print("  -> no se encontró un domicilio verificable")

    df.to_csv(args.csv, index=False)
    print(f"\nActualizado {args.csv}")


if __name__ == "__main__":
    main()
