# 🗺️ Mapa de organizaciones que documentan feminicidios en México

Mapa interactivo de organizaciones, colectivas y proyectos artísticos que documentan feminicidios y transfeminicidios en México de forma independiente del gobierno: desde observatorios con bases de datos y mapas interactivos hasta minidocumentales, performances y arte memorial que visibilizan a las víctimas.

## 📍 Ver el mapa

### 👉 [Nueva versión: mapa con MapLibre + deck.gl](https://ny-dia.github.io/mapa-feminicidios-mexico/mapa3d/)

Al abrir la ficha de una organización se iluminan los estados donde trabaja y el mapa se encuadra para mostrarlos. Incluye búsqueda, filtros por tipo y por estado de cobertura, y una vista inclinada en 3D.

### 👉 [Versión original (Folium)](https://ny-dia.github.io/mapa-feminicidios-mexico/)

### 👉 [Mapa municipal de feminicidios con cifras oficiales (SESNSP 2026)](https://ny-dia.github.io/mapa-feminicidios-mexico/feminicidios_municipal/)

Víctimas de feminicidio, tentativa de feminicidio y muertes violentas de mujeres (feminicidio + homicidio doloso de mujeres) por municipio, enero–septiembre de 2026, con el porcentaje de asesinatos de mujeres que cada fiscalía registró como feminicidio. Fuente: SESNSP, RNID Fuero común – Víctimas, incidencia delictiva municipal. Los datos se regeneran con `feminicidios_municipal/preparar_datos_municipales.py`.

## 📊 Sobre el proyecto

Este mapa fue desarrollado como parte del curso Datos contra feminicidios de ILDA (Iniciativa Latinoamericana de Datos Abiertos), y presentado en Dev Day 4 Women CDMX (julio 2026). Incluye actualmente **105 organizaciones y proyectos** (22 de alcance nacional) con sede en 31 estados:

- 📍 Ubicación geográfica de cada organización (muchos puntos marcan la ciudad, no una dirección exacta)
- 🗺️ Estados que cubre cada organización, además de su sede
- 📝 Metodología de registro
- 📈 Tipo de datos y productos generados
- 🏷️ Categorización por tipo de organización o proyecto (Base de datos/mapa interactivo, Observatorio/informe estadístico, Arte y memoria, Periodismo/documentación independiente, Incidencia y defensa legal). Una organización puede tener varias categorías
- 📞 Datos de contacto cuando están disponibles públicamente (sitio web, redes sociales, domicilio, teléfono o email)

Querétaro todavía no tiene ninguna organización registrada.

## 🤝 ¿Tu organización está en el mapa? ¿Falta alguna?

Si formas parte de una organización o proyecto listado y algo está desactualizado, incompleto o mal representado, o si conoces un proyecto que debería estar y no aparece, avísame:

- Abre un [issue en este repositorio](https://github.com/Ny-dia/mapa-feminicidios-mexico/issues/new), o
- Escríbeme a nydiamz16@gmail.com

Toda corrección se agradece — la idea es que este mapa represente con precisión el trabajo de quienes documentan la violencia feminicida, no una versión aproximada.

## 🔬 Para investigadores y periodistas

El CSV base (`organizaciones.csv`) es de acceso abierto y puede usarse para investigación, análisis o reportajes, citando este repositorio como fuente. Si estás trabajando en algo relacionado con datos de feminicidios en México y quieres platicar sobre la metodología, colaborar o que te comparta más contexto, escríbeme a nydiamz16@gmail.com.

## 📂 Estructura del repositorio

- `organizaciones.csv` — fuente de datos de ambos mapas. Columnas: Organización, Latitud, Longitud, Estado, Metodología de Registro, Tipo de Datos y Productos, Tipo de Organización o Proyecto, Contacto, Estados que cubre (`Nacional` o lista separada por `;`)
- `generar_mapa.py` — lee el CSV y genera `index.html` (versión Folium)
- `index.html` — mapa Folium publicado vía GitHub Pages. **No editar a mano**
- `exportar_geojson.py` — lee el CSV y genera `mapa3d/organizaciones.geojson`
- `mapa3d/` — nueva versión del mapa:
  - `index.html` — página con la interfaz (MapLibre + deck.gl)
  - `organizaciones.geojson` — datos generados por `exportar_geojson.py`. **No editar a mano**
  - `estados.geojson` — límites estatales simplificados
  - `vendor/` — copias locales de MapLibre GL JS y deck.gl
- `feminicidios_municipal/` — mapa municipal con cifras oficiales
- `agentes/` — scripts de IA de apoyo para descubrir, clasificar, geocodificar y validar organizaciones nuevas antes de agregarlas al CSV (ver [agentes/README.md](agentes/README.md))

## 🔄 Cómo actualizar los mapas

Después de modificar `organizaciones.csv`:

```
pip install pandas folium
python generar_mapa.py       # versión Folium → index.html
python exportar_geojson.py   # nueva versión → mapa3d/organizaciones.geojson
```

Si cambias los datos de la nueva versión, actualiza también `VERSION_DATOS` en `mapa3d/index.html` para que los navegadores no muestren copias viejas guardadas en caché.

Para ver la nueva versión localmente (no funciona abriendo el archivo directo):

```
python -m http.server 8000
# abre http://localhost:8000/mapa3d/
```

## 🧭 De Folium a MapLibre + deck.gl

La primera versión se hizo con Python y Folium en Google Colab: ideal para prototipar, pero cada cambio implicaba regenerar todo el HTML y era difícil conectar búsqueda, filtros, lista y mapa. En la nueva versión los datos y la interfaz están separados:

- **Python** prepara los datos: convierte el CSV en GeoJSON, separa categorías, interpreta la cobertura por estado y reparte ligeramente los puntos que comparten coordenadas para que no se encimen.
- **MapLibre GL JS** dibuja el fondo: solo límites estatales, sin mosaicos de calles, para que el protagonismo sea de las organizaciones. Un filtro sobre la capa de estados ilumina la cobertura de la organización seleccionada.
- **deck.gl** dibuja los puntos: color por tipo, anillo de segundo color cuando hay dos categorías y estrella para las organizaciones nacionales.
- Sigue siendo un sitio estático en GitHub Pages, sin servidor.

## 🛠️ Tecnologías

- Python, Pandas
- Folium (versión original)
- MapLibre GL JS y deck.gl (nueva versión)
- mapshaper (simplificación de límites estatales)
- Firecrawl — búsqueda y validación de organizaciones, sitios web y domicilios
- Claude (Anthropic) — agentes de IA para descubrir, clasificar y validar organizaciones antes de agregarlas al CSV

## 📅 Última actualización

Noviembre 2026

## 👥 Créditos

Elaborado por Nydia Mejía Zavala.

Gracias a Firecrawl por los créditos otorgados en la Mexico Tech Week, que permitieron ampliar y validar la base de organizaciones.

---

💜 Este proyecto busca visibilizar el trabajo fundamental de las organizaciones que documentan la violencia feminicida en México.
