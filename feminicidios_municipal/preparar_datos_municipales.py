"""
Prepara los datos del mapa municipal de feminicidios (Memoria Viva de Feminicidios).

Fuente: SESNSP / Centro Nacional de Información, Registro Nacional de Incidencia
Delictiva (RNID), "Fuero común - Víctimas. Incidencia delictiva municipal",
enero-septiembre 2026 (archivo RNID-Víctimas_Municipal-2026-sep2026.csv).
Descarga: https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva

Uso:
    python preparar_datos_municipales.py RNID-Víctimas_Municipal-2026-sep2026.csv datos_municipales.json

Salida: JSON con, por municipio (clave INEGI de 5 dígitos):
    f  = víctimas de feminicidio por mes (lista de 9 meses)
    t  = víctimas de tentativa de feminicidio por mes
    h  = mujeres víctimas de homicidio doloso por mes
    hm = mujeres víctimas de homicidio doloso por modalidad (mismo orden que mo)
    mo = víctimas de feminicidio por modalidad [arma de fuego, arma blanca, otro elemento, no especificado]
    ed = víctimas de feminicidio por rango de edad [0-12, 13-17, 18-29, 30-60, 60+, no esp.]
"""
import json
import sys

import pandas as pd

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre"]
MODALIDADES = ["Con arma de fuego", "Con arma blanca", "Con otro elemento", "No especificado"]
EDADES = ["0 a 12 años", "13 a 17 años", "18 a 29 años", "30 a 60 años",
          "Más de 60 años", "No especificado"]


def main(src, dst):
    df = pd.read_csv(src, encoding="utf-8-sig",
                     dtype={"Clave_Ent": str, "Cve. Municipio": str})
    df["cve"] = df["Cve. Municipio"].str.zfill(5)
    df["total"] = df[MESES].sum(axis=1)
    homicidio = df[(df["Subtipo de delito"] == "Homicidio doloso") & (df["Sexo"] == "Mujer")]
    hom_no_id = df[(df["Subtipo de delito"] == "Homicidio doloso") & (df["Sexo"] == "No identificado")]
    df = pd.concat([df[df["Tipo de delito"] == "Feminicidio"], homicidio])

    consumado = df[df["Subtipo de delito"] == "Feminicidio"]
    tentativa = df[df["Subtipo de delito"] == "Tentativa de feminicidio"]

    out = {}
    for cve, g in df.groupby("cve"):
        c = consumado[consumado.cve == cve]
        t = tentativa[tentativa.cve == cve]
        f_mes = [int(c[m].sum()) for m in MESES]
        t_mes = [int(t[m].sum()) for m in MESES]
        h = homicidio[homicidio.cve == cve]
        h_mes = [int(h[m].sum()) for m in MESES]
        if sum(f_mes) + sum(t_mes) + sum(h_mes) == 0:
            continue
        out[cve] = {
            "f": f_mes,
            "t": t_mes,
            "h": h_mes,
            "hm": [int(h.loc[h.Modalidad == m, "total"].sum()) for m in MODALIDADES],
            "mo": [int(c.loc[c.Modalidad == m, "total"].sum()) for m in MODALIDADES],
            "ed": [int(c.loc[c["Rango de edad"] == e, "total"].sum()) for e in EDADES],
            "n": g["Municipio"].iloc[0],
            "e": g["Entidad"].iloc[0],
        }

    meta = {
        "fuente": "SESNSP-CNI, RNID Fuero común - Víctimas, incidencia delictiva municipal",
        "periodo": "enero-septiembre 2026",
        "meses": MESES,
        "total_feminicidio": int(consumado.total.sum()),
        "total_tentativa": int(tentativa.total.sum()),
        "total_homicidio_doloso_mujeres": int(homicidio.total.sum()),
        "homicidio_doloso_sexo_no_identificado": int(hom_no_id.total.sum()),
    }
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "municipios": out}, fh, ensure_ascii=False,
                  separators=(",", ":"))
    print(meta)
    print(f"{len(out)} municipios con al menos un registro")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
