# Noticias internacionales en español: primera versión

## Captación y fuentes

Desde el checkout existente, con Python 3.12, uv y FFmpeg:

```sh
uv sync --frozen
uv run --frozen python pipeline.py ingest --profile international
uv run --frozen python pipeline.py list --category politica_internacional
uv run --frozen python pipeline.py show <ID>
uv run --frozen python pipeline.py classify <ID> economia
```

En el entorno cloud actual se necesita `CC=gcc CXX=g++` al compilar pkuseg;
`UV_CACHE_DIR=/workspace/.cache/uv` permite reutilizar la caché preparada.
`NEWS_PROFILE=international` es el valor predeterminado. `--profile tech` conserva
HN, Reddit, TechCrunch, 4chan y X por separado; no se mezclan con la selección editorial.
No se instalan servicios ni se necesitan claves para RSS, SQLite o clasificación.

| Fuente | Endpoint | Estado observado en este entorno |
| --- | --- | --- |
| BBC Mundo | https://feeds.bbci.co.uk/mundo/rss.xml | CONNECT 403 del proxy; parser probado con fixtures, acceso real pendiente |
| DW Español | https://rss.dw.com/rdf/rss-sp-all | CONNECT 403 del proxy; acceso real pendiente |
| Noticias ONU (fuente oficial) | https://news.un.org/feed/subscribe/es/news/all/rss.xml | CONNECT 403 del proxy; acceso real pendiente |
| Reddit (perfil tech) | https://www.reddit.com/r/technology/.rss | Bloqueado por el proxy; errores aislados por subreddit |
| Reuters, AP, AFP | Sin endpoint gratuito predeterminado | Desactivadas hasta disponer de RSS oficial autorizado; no se compró acceso |

Un bloqueo de red no demuestra que un feed haya desaparecido. Permitir
`feeds.bbci.co.uk`, `rss.dw.com`, `news.un.org` y, si procede, los destinos de sus
redirecciones en los ajustes del entorno; después repetir `ingest` y verificar
que produce noticias reales. No se eluden bloqueos, autenticación ni paywalls.
El comando devuelve error si todas las fuentes fallan o no entregan noticias.

Si ya tienes derecho de acceso a un feed de agencia, puedes configurar
`AUTHORIZED_AGENCY_RSS` como objeto JSON `{ "reuters": "https://<host-oficial>/<feed-autorizado>" }`.
Se admiten Reuters (`reuters.com`, `reutersconnect.com`), AP (`ap.org`, `apnews.com`)
y AFP (`afp.com`, `afpforum.com`), incluidos sus subdominios. No configures URLs
con credenciales. Esta opción no verifica una licencia ni contrata servicios:
úsala solo con un endpoint y permiso facilitados por la agencia. Otros hosts
requieren revisión de código. No se scrapean artículos ni se reproducen textos
completos; los metadatos RSS no otorgan derechos de reutilización de imágenes.

Cada feed internacional tiene un límite total de 30 segundos, además del timeout
HTTP y el aislamiento de errores; la captación
externa tiene un límite de 90 segundos por fuente del registro. Reddit usa un
hilo para no bloquear otras tareas, y un fallo no impide consultar los demás
subreddits. Los errores se registran; un resultado vacío no cuenta como prueba
de conectividad correcta.

## Categorías y procedencia

Categorías: `politica_internacional`, `economia`, `ciencia`, `tecnologia`,
`actualidad_general`. La asignación automática usa reglas locales sobre titular
y etiquetas (sin IA ni gastos). Es aproximada, de categoría única y revisable
con `classify`; las correcciones manuales se conservan al volver a captar.
Una fuente oficial aporta su posición, no corroboración periodística independiente.

La deduplicación combina IDs, URLs sin fragmentos/parámetros de seguimiento
conocidos, y titulares normalizados idénticos de al menos 30 caracteres en un
intervalo de 24 horas. Conserva parámetros funcionales y todos los enlaces
originales en `raw_data.sources`, visibles con `show` y en el contexto del guion.
No combina automáticamente titulares distintos sobre un mismo acontecimiento:
esa revisión editorial evita falsos positivos y queda pendiente para versiones futuras.
SQLite conserva ID, estado de producción y enlaces incluso si cambia la fuente
principal entre captaciones. No hay migración destructiva. Para esta primera
versión, la búsqueda de duplicados persistidos recorre las noticias existentes;
un archivo grande necesitará índices de URL/titular antes de escalar.

## Pruebas sin coste

```sh
uv run --frozen pytest tests/ --ignore=tests/integration -v
```

Las pruebas unitarias bloquean HTTP real y usan fixtures RSS y transportes simulados.
Cubren 403, timeout, feeds inválidos, continuidad de captación, clasificación,
deduplicación, persistencia y aprobación de publicación. No consumen APIs de pago.
Las pruebas en `tests/integration` consultan fuentes reales, son opcionales y no
sustituyen las comprobaciones sin red. No ejecutes `preview`, `run`, `script` sin
`--interactive` ni `shots` como pruebas gratuitas: pueden consumir OpenAI o fal.ai.
No se han modificado credenciales ni activado suscripciones.

## Primer video de prueba sin APIs de pago

1. Habilitar las fuentes en la política de red y ejecutar `ingest` y `show`.
2. Elegir una noticia, verificar fecha, atribución y enlaces; confirmar los hechos
   relevantes con otra fuente. Revisar la categoría antes de redactar.
3. Ejecutar `uv run --frozen python pipeline.py script <ID> --interactive`.
   Redactar y revisar un guion en español de 60–100 palabras. Guardar el JSON
   indicado en `output/<ID de 12 caracteres>/script.json`. No se llama a OpenAI.
4. Grabar narración propia y colocarla en esa carpeta como `narration.mp3`.
   Crear `timestamps.json` con una lista de palabras y sus tiempos reales:
   `[{"word":"Hoy", "start":0.0, "end":0.4}]`. Así no se descargan modelos ni
   se necesita un proveedor de voz. Como alternativa gratuita, Edge TTS usa
   `EDGE_TTS_VOICE=es-MX-JorgeNeural`, pero necesita su propia conectividad;
   `voice` también descarga el modelo Whisper si todavía no está disponible.
5. Ejecutar `uv run --frozen python pipeline.py video <ID> --no-open`.
   Sin clips en `shots/`, genera fondo estático, subtítulos y MP4 local con FFmpeg.
6. Revisar `output/<ID de 12 caracteres>/output.mp4`: precisión, español, voz,
   subtítulos y derechos de los materiales. Esto no publica nada.

La generación automática de guiones también se ha adaptado a español neutral,
atribución y distinción entre hechos y declaraciones; sigue siendo opcional y de
pago, y no se ha llamado durante este trabajo.

`run` y `preview` nunca publican. `_run_pipeline(upload=True)` rechaza la operación.
Todos los puntos públicos `upload_to_*` requieren `approved=True` por llamada,
y el CLI exige `publish <ID> --approve-publication` (plataformas seleccionables).
Esta bandera expresa la aprobación humana para ese video; no la añadas a cron,
contenedores, agentes ni tareas automáticas. No existe una aprobación global por
variable de entorno. Ninguna publicación se ejecutó durante las pruebas.
