"""Agente 1: descubrimiento de organizaciones/colectivos/proyectos nuevos.

Patrón de dos llamadas: (1) investigación libre con web_search, (2) se
estructura ese texto en JSON validado con Pydantic via messages.parse().

Uso:
    python agentes/descubrir.py "tema 1" "tema 2" ...
    python agentes/descubrir.py   # usa la lista de temas por default
"""

import sys

import pandas as pd

from common import (
    CSV_CANDIDATOS,
    CSV_COLUMNS,
    CSV_MAESTRO,
    MAX_USES_BUSQUEDA,
    MODEL,
    ListaOrganizaciones,
    Organizacion,
    categoria_valida,
    client,
    normalizar_nombre,
)

TEMAS_DEFAULT = [
    "colectivos que documentan feminicidios en el norte de México",
    "proyectos artísticos, minidocumentales o performance sobre feminicidios en México",
    "bases de datos ciudadanas de feminicidios por estado en México",
    "arte memorial y monumentos independientes sobre feminicidios en México",
]


def investigar_tema(tema: str) -> str:
    prompt = f"""Busca en internet organizaciones, colectivos o proyectos artísticos
(minidocumentales, performances, arte memorial, mapas, bases de datos) que documenten
feminicidios en México de forma INDEPENDIENTE al gobierno, relacionados con: {tema}.

No incluyas dependencias de gobierno ni fiscalías. Prioriza organizaciones que estén
basadas en o enfocadas específicamente en el/los estado(s) mencionados en el tema —
NO reportes proyectos nacionales que solo mencionan ese estado de pasada entre muchos
otros, a menos que el tema pida explícitamente cobertura nacional.

Para cada resultado que encuentres, reporta:
- nombre de la organización o proyecto
- estado(s) de México donde opera o enfoca su trabajo
- qué metodología usa para registrar/documentar los casos
- qué tipo de datos o productos genera (base de datos descargable, mapa interactivo,
  documental, performance, reporte, etc.)
- a cuál de estas 5 categorías pertenece (elige SOLO UNA, nunca combines varias):
  "Observatorio / informe estadístico", "Base de datos / mapa interactivo",
  "Arte y memoria", "Periodismo / documentación independiente",
  "Incidencia y defensa legal"
- el link de la fuente principal (su sitio, redes o repositorio), SOLO si encontraste
  una URL real y verificable en los resultados de búsqueda. Si no encontraste un link
  concreto, dilo explícitamente ("sin fuente verificable") — NUNCA escribas una
  instrucción de búsqueda (como "buscar 'X' en redes sociales") como si fuera un link.
"""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_USES_BUSQUEDA}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def estructurar_investigacion(texto: str) -> list[Organizacion]:
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=3000,
        thinking={"type": "disabled"},
        messages=[{
            "role": "user",
            "content": f"A partir de esta investigación, extrae una lista estructurada de "
                       f"organizaciones. Si un dato no está disponible usa cadena vacía. "
                       f"Para enlace_fuente: solo pon una URL real (empieza con http:// o "
                       f"https://); si el texto dice que no hay fuente verificable o solo "
                       f"sugiere buscarla, deja el campo vacío en vez de escribir esa "
                       f"instrucción.\n\n{texto}",
        }],
        output_format=ListaOrganizaciones,
    )
    return resp.parsed_output.organizaciones


def descubrir(temas: list[str]) -> list[Organizacion]:
    encontradas = []
    for tema in temas:
        print(f"Investigando: {tema}")
        texto = investigar_tema(tema)
        nuevas = estructurar_investigacion(texto)
        print(f"  -> {len(nuevas)} encontradas")
        encontradas.extend(nuevas)
    return encontradas


def cargar_nombres_existentes() -> set[str]:
    """Nombres normalizados ya presentes en el CSV maestro Y en candidatos
    pendientes de una corrida anterior (para no perder ni duplicar trabajo)."""
    nombres = set()
    for ruta in (CSV_MAESTRO, CSV_CANDIDATOS):
        if ruta.exists():
            df = pd.read_csv(ruta)
            nombres |= {normalizar_nombre(n) for n in df["Organización"]}
    return nombres


def cargar_candidatos_previos() -> pd.DataFrame:
    if CSV_CANDIDATOS.exists():
        return pd.read_csv(CSV_CANDIDATOS)
    return pd.DataFrame(columns=CSV_COLUMNS)


def main():
    temas = sys.argv[1:] or TEMAS_DEFAULT
    resultados_crudos = descubrir(temas)
    print(f"\nTotal encontradas (con duplicados): {len(resultados_crudos)}")

    nombres_existentes = cargar_nombres_existentes()
    vistos = set()
    nuevas_unicas = []
    for o in resultados_crudos:
        key = normalizar_nombre(o.organizacion)
        if key in nombres_existentes or key in vistos:
            continue
        vistos.add(key)
        nuevas_unicas.append(o)

    print(f"Organizaciones nuevas (no repetidas ni ya en el CSV maestro/candidatos): {len(nuevas_unicas)}")

    filas = []
    for o in nuevas_unicas:
        categoria = categoria_valida(o.categoria)
        if categoria is None:
            print(f"  ADVERTENCIA: '{o.organizacion}' tiene categoría inválida "
                  f"('{o.categoria}'), se deja vacía para revisión manual")
        filas.append({
            "Organización": o.organizacion,
            "Latitud": "",
            "Longitud": "",
            "Estado": o.estado,
            "Metodología de Registro": o.metodologia_de_registro,
            "Tipo de Datos y Productos": o.tipo_de_datos_y_productos,
            "Enlace / Fuente": o.enlace_fuente,
            "Tipo de Organización o Proyecto": categoria or "",
        })

    df_candidatos_previos = cargar_candidatos_previos()
    df_nuevas = pd.DataFrame(filas, columns=CSV_COLUMNS)
    df_combinado = pd.concat([df_candidatos_previos, df_nuevas], ignore_index=True)
    df_combinado.to_csv(CSV_CANDIDATOS, index=False)
    print(f"\n{len(df_candidatos_previos)} candidatos previos + {len(df_nuevas)} nuevos "
          f"= {len(df_combinado)} en total, guardado en {CSV_CANDIDATOS}")
    print("Siguiente paso: python agentes/clasificar.py --csv organizaciones_nuevas.csv")


if __name__ == "__main__":
    main()
