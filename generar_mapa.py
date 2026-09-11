import html
import json
import re

import folium
import pandas as pd
from folium.plugins import MarkerCluster

CSV_PATH = "organizaciones.csv"
OUTPUT_PATH = "index.html"

MEXICO_CENTER = [23.6345, -102.5528]
ZOOM_START = 5

PAGE_TITLE = "Organizaciones y colectivos que documentan feminicidios en México"
PAGE_DESCRIPTION = (
    "Este mapa reúne organizaciones, colectivos y proyectos artísticos que documentan "
    "feminicidios en México de forma independiente del gobierno: desde observatorios con "
    "bases de datos y mapas interactivos hasta minidocumentales, performances y arte "
    "memorial que visibilizan a las víctimas. Usa los filtros para explorar por estado o "
    "por tipo de organización."
)

# Categorical palette (validated: scripts/validate_palette.js, --pairs all, light mode).
# Fixed order = descending frequency in the dataset; never reassigned per-render.
CATEGORY_COLORS = {
    "Observatorio / informe estadístico": "#2a78d6",        # blue
    "Base de datos / mapa interactivo": "#008300",          # green
    "Arte y memoria": "#e87ba4",                             # magenta
    "Periodismo / documentación independiente": "#eda100",  # yellow
    "Incidencia y defensa legal": "#1baf7a",                 # aqua
}
DEFAULT_COLOR = "#898781"  # muted gray fallback for any uncategorized row
MAGENTA = CATEGORY_COLORS["Arte y memoria"]  # reused for title + filter-panel heading

# States that get their own filter bucket. Any Estado value not clearly naming one
# of these (e.g. "Nacional (registra casos en los 32 estados)", "Regional (América
# Latina y el Caribe)...") falls back to the NACIONAL_LABEL bucket below.
MX_STATES = [
    "Aguascalientes", "Baja California Sur", "Baja California", "Campeche", "Chiapas",
    "Chihuahua", "Coahuila", "Colima", "Durango", "Estado de México", "Guanajuato",
    "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit", "Nuevo León",
    "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa",
    "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
]
CDMX_LABEL = "Ciudad de México"
NACIONAL_LABEL = "Nacional / Regional"

POPUP_TEMPLATE = """
<div style="font-family: Arial; width: 300px;">
    <h4 style="color: #8B0000;">{organizacion}</h4>
    <p><strong>Estado:</strong> {estado}</p>{contacto_html}
    <p><strong>Tipo de Organización/Proyecto:</strong><br>{categorias_html}</p>
    <p><strong>Metodología:</strong><br>{metodologia}</p>
    <p><strong>Tipo de Datos:</strong><br>{tipo_datos}</p>
</div>
"""

PAGE_HEADER_TEMPLATE = """
<style>
    html, body {
        height: 100%;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
    }
    #page-header {
        flex: 0 0 auto;
        font-family: Arial, sans-serif;
        padding: 14px 24px;
        background: #fcfcfb;
        border-bottom: 1px solid rgba(11,11,11,0.10);
    }
    #page-header h1 {
        margin: 0 0 6px 0;
        font-size: 20pt;
        font-weight: bold;
        color: __MAGENTA__;
        text-transform: uppercase;
    }
    #page-header p.description {
        margin: 0;
        font-size: 13pt;
        color: #52514e;
        max-width: 960px;
    }
    #content-row {
        flex: 1 1 auto;
        display: flex;
        flex-direction: row;
        min-height: 0;
    }
    .folium-map {
        flex: 1 1 auto !important;
        height: 100% !important;
        width: auto !important;
    }
    #filter-sidebar {
        flex: 0 0 260px;
        font-family: Arial, sans-serif;
        background: #fcfcfb;
        border-left: 1px solid rgba(11,11,11,0.10);
        padding: 16px;
        overflow-y: auto;
    }
    #filter-sidebar h2 {
        margin: 0 0 12px 0;
        font-size: 1.05rem;
        color: __MAGENTA__;
    }
    #filter-sidebar .filter-group-title {
        font-weight: bold;
        font-size: 0.85rem;
        margin-bottom: 4px;
        color: #0b0b0b;
    }
    #filter-estado {
        max-height: 260px;
        overflow-y: auto;
        border: 1px solid rgba(11,11,11,0.10);
        border-radius: 4px;
        padding: 6px 10px;
        margin-bottom: 16px;
    }
    #filter-categoria {
        border: 1px solid rgba(11,11,11,0.10);
        border-radius: 4px;
        padding: 6px 10px;
        margin-bottom: 16px;
    }
    .filter-checkbox-label {
        display: block;
        font-size: 0.82rem;
        white-space: nowrap;
        margin-bottom: 2px;
        color: #0b0b0b;
    }
    #filter-reset {
        width: 100%;
        font-family: Arial, sans-serif;
        font-size: 0.85rem;
        padding: 6px 12px;
        border: 1px solid rgba(11,11,11,0.10);
        border-radius: 4px;
        background: #fcfcfb;
        cursor: pointer;
    }
    #filter-reset:hover {
        background: #f0efec;
    }
</style>
<div id="page-header">
    <h1>__TITLE__</h1>
    <p class="description">__DESCRIPTION__</p>
</div>
"""

FILTER_SIDEBAR_TEMPLATE = """
<div id="filter-sidebar">
    <h2>Filtros</h2>
    <div class="filter-group-title">Estado</div>
    <div id="filter-estado">__ESTADO_CHECKBOXES__</div>
    <div class="filter-group-title">Tipo de Organización o Proyecto</div>
    <div id="filter-categoria">__CATEGORIA_CHECKBOXES__</div>
    <button id="filter-reset" type="button">Quitar filtros</button>
</div>
"""

CUSTOM_JS_TEMPLATE = """
<script>
document.addEventListener('DOMContentLoaded', function () {
    var FEM_MARKERS = __FEM_MARKERS__;
    var clusterGroup = __CLUSTER_VAR__;

    function getChecked(containerId) {
        return Array.from(
            document.querySelectorAll('#' + containerId + ' input[type=checkbox]:checked')
        ).map(function (cb) { return cb.value; });
    }

    function applyFilters() {
        var estados = getChecked('filter-estado');
        var categorias = getChecked('filter-categoria');
        FEM_MARKERS.forEach(function (entry) {
            var tieneCategoria = entry.categorias.some(function (c) { return categorias.indexOf(c) !== -1; });
            var show = estados.indexOf(entry.estado) !== -1 && tieneCategoria;
            var present = clusterGroup.hasLayer(entry.marker);
            if (show && !present) { clusterGroup.addLayer(entry.marker); }
            if (!show && present) { clusterGroup.removeLayer(entry.marker); }
        });
    }

    document.querySelectorAll('#filter-estado input[type=checkbox], #filter-categoria input[type=checkbox]')
        .forEach(function (cb) { cb.addEventListener('change', applyFilters); });

    var resetBtn = document.getElementById('filter-reset');
    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            document.querySelectorAll('#filter-estado input[type=checkbox], #filter-categoria input[type=checkbox]')
                .forEach(function (cb) { cb.checked = true; });
            applyFilters();
        });
    }
});
</script>
"""


def parse_categorias(raw):
    """Una organización puede pertenecer a varias categorías, separadas por coma
    (no "/" porque varios nombres de categoría ya usan "/" internamente, ej.
    "Observatorio / informe estadístico")."""
    partes = [c.strip() for c in str(raw).split(",")]
    return [c for c in partes if c]


def marker_color(categorias):
    for categoria in categorias:
        if categoria in CATEGORY_COLORS:
            return CATEGORY_COLORS[categoria]
    return DEFAULT_COLOR


def normalize_estado(raw):
    text = str(raw)
    low = text.lower()
    if low.startswith("nacional") or low.startswith("regional"):
        return NACIONAL_LABEL
    if "cdmx" in low or "ciudad de méxico" in low or "ciudad de mexico" in low:
        return CDMX_LABEL
    for state in MX_STATES:
        if state.lower() in low:
            return state
    return NACIONAL_LABEL


def build_categorias_html(categorias):
    return "<br>".join(
        f'<span style="color: {CATEGORY_COLORS.get(categoria, DEFAULT_COLOR)};">&#9679;</span> '
        f'{html.escape(categoria)}'
        for categoria in categorias
    )


URL_PATTERN = re.compile(r"https?://\S+")


def linkify(texto_pieza):
    """Convierte la URL dentro de una pieza de texto (ej. 'Web: https://...')
    en un link clicable, dejando el resto del texto como texto plano escapado."""
    match = URL_PATTERN.search(texto_pieza)
    if not match:
        return html.escape(texto_pieza)
    url = match.group(0).rstrip(".,;")
    antes = texto_pieza[:match.start()]
    despues = texto_pieza[match.start() + len(url):]
    return (
        f"{html.escape(antes)}"
        f'<a href="{html.escape(url, quote=True)}" target="_blank">{html.escape(url)}</a>'
        f"{html.escape(despues)}"
    )


def build_contacto_html(contacto):
    """La columna Contacto guarda varios datos (domicilio, teléfono, email,
    redes) separados por ' | '; cada uno se muestra en su propia línea, con
    cualquier URL convertida en link clicable."""
    texto = str(contacto).strip()
    if not texto or texto.lower() == "nan":
        return ""
    partes = "<br>".join(linkify(p.strip()) for p in texto.split("|") if p.strip())
    return f"\n    <p><strong>Contacto:</strong><br>{partes}</p>"


def build_popup_html(row, categorias):
    return POPUP_TEMPLATE.format(
        organizacion=html.escape(str(row["Organización"])),
        estado=html.escape(str(row["Estado"])),
        contacto_html=build_contacto_html(row.get("Contacto", "")),
        categorias_html=build_categorias_html(categorias),
        metodologia=html.escape(str(row["Metodología de Registro"])),
        tipo_datos=html.escape(str(row["Tipo de Datos y Productos"])),
    )


def build_dot_icon(color):
    dot_html = (
        f'<div style="background-color:{color}; width:14px; height:14px; '
        f'border-radius:50%; border:2px solid white; '
        f'box-shadow:0 0 2px rgba(0,0,0,0.5);"></div>'
    )
    return folium.DivIcon(html=dot_html, icon_size=(14, 14), icon_anchor=(7, 7))


def build_checkbox(group_id, value, label_html, checked=True):
    checkbox_id = f"{group_id}-" + re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    checked_attr = " checked" if checked else ""
    return (
        f'<label class="filter-checkbox-label" for="{checkbox_id}">'
        f'<input type="checkbox" id="{checkbox_id}" value="{html.escape(value, quote=True)}"{checked_attr}> '
        f"{label_html}</label>"
    )


def build_estado_checkboxes(estados_presentes):
    ordered = [NACIONAL_LABEL] + sorted(e for e in estados_presentes if e != NACIONAL_LABEL)
    return "\n".join(
        build_checkbox("filter-estado", estado, html.escape(estado))
        for estado in ordered
        if estado in estados_presentes
    )


def build_categoria_checkboxes():
    boxes = []
    for categoria, color in CATEGORY_COLORS.items():
        swatch = (
            f'<span style="display:inline-block; width:10px; height:10px; '
            f'border-radius:50%; background:{color}; margin-right:5px;"></span>'
        )
        boxes.append(build_checkbox("filter-categoria", categoria, swatch + html.escape(categoria)))
    return "\n".join(boxes)


def main():
    df = pd.read_csv(CSV_PATH)

    mapa = folium.Map(location=MEXICO_CENTER, zoom_start=ZOOM_START, tiles="CartoDB positron")
    cluster = MarkerCluster().add_to(mapa)
    cluster_var = cluster.get_name()

    marker_meta = []
    estados_presentes = set()

    for _, row in df.iterrows():
        categorias = parse_categorias(row["Tipo de Organización o Proyecto"])
        estado_filtro = normalize_estado(row["Estado"])
        estados_presentes.add(estado_filtro)

        popup = folium.Popup(build_popup_html(row, categorias), max_width=300)
        tooltip = folium.Tooltip(html.escape(str(row["Organización"])), sticky=True)

        marker = folium.Marker(
            location=[row["Latitud"], row["Longitud"]],
            popup=popup,
            tooltip=tooltip,
            icon=build_dot_icon(marker_color(categorias)),
        )
        marker.add_to(cluster)

        marker_meta.append({
            "marker_var": marker.get_name(),
            "estado": estado_filtro,
            "categorias": categorias,
        })

    page_header_html = (
        PAGE_HEADER_TEMPLATE
        .replace("__MAGENTA__", MAGENTA)
        .replace("__TITLE__", html.escape(PAGE_TITLE))
        .replace("__DESCRIPTION__", html.escape(PAGE_DESCRIPTION))
    )

    filter_sidebar_html = (
        FILTER_SIDEBAR_TEMPLATE
        .replace("__ESTADO_CHECKBOXES__", build_estado_checkboxes(estados_presentes))
        .replace("__CATEGORIA_CHECKBOXES__", build_categoria_checkboxes())
    )

    fem_markers_js = "[\n" + ",\n".join(
        "  {marker: %s, estado: %s, categorias: %s}" % (
            entry["marker_var"],
            json.dumps(entry["estado"], ensure_ascii=False),
            json.dumps(entry["categorias"], ensure_ascii=False),
        )
        for entry in marker_meta
    ) + "\n]"

    custom_js = CUSTOM_JS_TEMPLATE.replace("__FEM_MARKERS__", fem_markers_js).replace(
        "__CLUSTER_VAR__", cluster_var
    )

    html_out = mapa.get_root().render()
    html_out = html_out.replace("<body>", "<body>\n" + page_header_html + '\n<div id="content-row">\n', 1)

    map_div_pattern = re.compile(r'<div class="folium-map"[^>]*></div>')
    html_out, n_subs = map_div_pattern.subn(
        lambda m: m.group(0) + "\n" + filter_sidebar_html + "\n</div>\n", html_out, count=1
    )
    if n_subs != 1:
        raise RuntimeError("No se encontró el div del mapa de Folium para envolverlo en #content-row.")

    html_out = html_out.replace("</html>", custom_js + "\n</html>", 1)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Mapa generado con {len(df)} organizaciones en '{OUTPUT_PATH}'.")
    print(f"Estados detectados para filtro: {sorted(estados_presentes)}")


if __name__ == "__main__":
    main()
