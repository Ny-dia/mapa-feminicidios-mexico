# Agentes de IA para el mapa de feminicidios

Cuatro scripts que usan la API de Claude (Anthropic) para ayudar a mantener y ampliar `organizaciones.csv`. Ninguno modifica `organizaciones.csv` directamente — todos escriben a archivos de trabajo separados (`organizaciones_nuevas.csv`, `reporte_qa.csv`) para que los revises antes de fusionarlos.

## Instalación

Desde la raíz del repo:

```bash
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y pon tu API key:

```bash
cp .env.example .env
```

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Los 4 agentes

1. **`descubrir.py`** — busca en la web organizaciones/colectivos/proyectos nuevos que documenten feminicidios en México, y los guarda en `organizaciones_nuevas.csv` (deduplicados contra el CSV maestro).
2. **`clasificar.py`** — dado un link, completa Metodología de Registro, Tipo de Datos y Productos, y Categoría. Sirve tanto para rellenar huecos en `organizaciones_nuevas.csv` como para actualizar una fuente suelta.
3. **`qa.py`** — revisa `organizaciones.csv` (o cualquier CSV con las mismas columnas) en busca de duplicados, enlaces rotos, categorías inválidas, coordenadas fuera de México y texto vago/categoría dudosa. **Solo genera un reporte, nunca modifica el CSV.**
4. **`geocodificar.py`** — busca la dirección real de una organización y la convierte a coordenadas precisas con Nominatim (OpenStreetMap). Si no encuentra nada, usa la capital del estado como respaldo.

## Flujo recomendado para ampliar el mapa

```bash
# 1. Descubrir organizaciones nuevas
python agentes/descubrir.py

# 2. Rellenar metodología/tipo de datos/categoría donde falten
python agentes/clasificar.py --csv organizaciones_nuevas.csv

# 3. Geocodificar con precisión
python agentes/geocodificar.py --csv organizaciones_nuevas.csv

# 4. REVISAR organizaciones_nuevas.csv A MANO antes de continuar
#    (los agentes pueden alucinar organizaciones que no existen o datos desactualizados)

# 5. Fusionar con el CSV maestro (a mano, o con este snippet de pandas)
python -c "
import pandas as pd
maestro = pd.read_csv('organizaciones.csv')
nuevas = pd.read_csv('organizaciones_nuevas.csv')
combinado = pd.concat([maestro, nuevas], ignore_index=True)
combinado = combinado.drop_duplicates(subset='Organización', keep='first')
combinado.to_csv('organizaciones.csv', index=False)
"

# 6. Validar el CSV maestro actualizado (solo reporte, no modifica nada)
python agentes/qa.py

# 7. Regenerar el mapa
python generar_mapa.py
```

## Uso suelto de cada agente

```bash
# Clasificar una sola fuente (para actualizar una fila vieja del CSV a mano)
python agentes/clasificar.py --url https://ejemplo.org

# QA sobre cualquier CSV con las mismas columnas
python agentes/qa.py --csv otra_ruta.csv

# Descubrir con temas personalizados en vez de la lista por default
python agentes/descubrir.py "colectivos en Chiapas" "arte memorial en Jalisco"
```

## Costos aproximados

- `web_search`: ~$10 USD por cada 1,000 búsquedas + tokens normales del modelo.
- `web_fetch`: sin costo extra, solo tokens.
- Nominatim (geocodificación): gratis.

Con `max_uses` bajo (5 para búsqueda, 2 para fetch, en `agentes/common.py`) por llamada, el gasto por corrida es mínimo.
