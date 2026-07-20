# 🗺️ Mapa de organizaciones que documentan feminicidios en México

Mapa interactivo que visualiza organizaciones, colectivos y proyectos artísticos que documentan feminicidios y transfeminicidios en México de forma independiente del gobierno.

## 📍 Ver el mapa

### 👉 [Click aquí para ver el mapa interactivo](https://ny-dia.github.io/mapa-feminicidios-mexico/)

## 📊 Sobre el proyecto

Este mapa fue desarrollado como parte del curso Datos contra feminicidios de ILDA. Incluye actualmente 60 organizaciones y proyectos:

- 📍 Ubicación geográfica de cada organización
- 📝 Metodología de registro
- 📈 Tipo de datos y productos generados
- 🏷️ Categorización por tipo de organización o proyecto (Base de datos/mapa interactivo, Observatorio/informe estadístico, Arte y memoria, Periodismo/documentación independiente, Incidencia y defensa legal)
- 🔗 Enlaces a fuentes verificables
- 🔍 Filtros interactivos por estado y por tipo de organización

## 📂 Estructura del repositorio

- `organizaciones.csv` — fuente de datos del mapa (Organización, Latitud, Longitud, Estado, Metodología de Registro, Tipo de Datos y Productos, Enlace/Fuente, Tipo de Organización o Proyecto)
- `generar_mapa.py` — script que lee `organizaciones.csv` y genera `index.html`
- `index.html` — mapa publicado vía GitHub Pages. **No editar a mano**: se regenera con el script a partir del CSV

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

## 📅 Última actualización

Julio 2026

## 👥 Créditos

Elaborado por Nydia Mejía Zavala

---

💜 Este proyecto busca visibilizar el trabajo fundamental de las organizaciones que documentan la violencia feminicida en México.
