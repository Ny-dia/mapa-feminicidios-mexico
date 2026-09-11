# 🗺️ Mapa de organizaciones que documentan feminicidios en México

Mapa interactivo que visualiza organizaciones, colectivos y proyectos artísticos que documentan feminicidios y transfeminicidios en México de forma independiente del gobierno.

## 📍 Ver el mapa

### 👉 [Click aquí para ver el mapa interactivo](https://ny-dia.github.io/mapa-feminicidios-mexico/)

## 📊 Sobre el proyecto

Este mapa fue desarrollado como parte del curso Datos contra feminicidios de ILDA (Iniciativa Latinoamericana de Datos Abiertos), y presentado en Dev Day 4 Women CDMX (julio 2026). Incluye actualmente 64 organizaciones y proyectos:

- 📍 Ubicación geográfica de cada organización
- 📝 Metodología de registro
- 📈 Tipo de datos y productos generados
- 🏷️ Categorización por tipo de organización o proyecto (Base de datos/mapa interactivo, Observatorio/informe estadístico, Arte y memoria, Periodismo/documentación independiente, Incidencia y defensa legal) — una organización puede tener varias categorías
- 📞 Datos de contacto cuando están disponibles (sitio web, redes sociales, domicilio, teléfono o email)
- 🔍 Filtros interactivos por estado y por tipo de organización

## 🤝 ¿Tu organización está en el mapa? ¿Falta alguna?

Si formas parte de una organización o proyecto listado y algo está desactualizado, incompleto o mal representado, o si conoces un proyecto que debería estar y no aparece, avísame:

- Abre un [issue en este repositorio](https://github.com/Ny-dia/mapa-feminicidios-mexico/issues/new), o
- Escríbeme a nydiamz16@gmail.com

Toda corrección se agradece — la idea es que este mapa represente con precisión el trabajo de quienes documentan la violencia feminicida, no una versión aproximada.

## 🔬 Para investigadores y periodistas

El CSV base (`organizaciones.csv`) es de acceso abierto y puede usarse para investigación, análisis o reportajes, citando este repositorio como fuente. Si estás trabajando en algo relacionado con datos de feminicidios en México y quieres platicar sobre la metodología, colaborar o que te comparta más contexto, escríbeme a nydiamz16@gmail.com.

## 📂 Estructura del repositorio

- `organizaciones.csv` — fuente de datos del mapa (Organización, Latitud, Longitud, Estado, Metodología de Registro, Tipo de Datos y Productos, Tipo de Organización o Proyecto, Contacto)
- `generar_mapa.py` — script que lee `organizaciones.csv` y genera `index.html`
- `index.html` — mapa publicado vía GitHub Pages. **No editar a mano**: se regenera con el script a partir del CSV
- `agentes/` — scripts de IA de apoyo para descubrir, clasificar y validar organizaciones nuevas antes de agregarlas al CSV (ver [agentes/README.md](agentes/README.md))

## 🔄 Cómo regenerar el mapa

Para actualizar el mapa después de modificar `organizaciones.csv`:

```
pip install pandas folium
python generar_mapa.py
```

Esto sobrescribe `index.html` con los datos actualizados del CSV.

## 🛠️ Tecnologías

- Python
- Folium (generación reproducible del mapa interactivo vía script)
- Pandas (lectura y procesamiento del CSV)
- Claude (Anthropic) — agentes de IA para descubrir, clasificar y validar organizaciones antes de agregarlas al CSV

## 📅 Última actualización

Agosto 2026

## 👥 Créditos

Elaborado por Nydia Mejía Zavala

---

💜 Este proyecto busca visibilizar el trabajo fundamental de las organizaciones que documentan la violencia feminicida en México.
