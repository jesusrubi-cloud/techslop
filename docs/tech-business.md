# Perfil independiente tech_business

Especialización editorial en tecnología, IA, empresas, negocios, economía,
mercados, emprendimiento e innovación. No sustituye `international` ni el perfil
tecnológico comunitario `tech`. El valor predeterminado `NEWS_PROFILE` permanece
sin cambios; se puede elegir el perfil por CLI o mediante esa variable no secreta.

## Flujo diario sin APIs de pago

```sh
uv run --frozen python pipeline.py ingest --profile tech_business \
  --feed-report output/tech-business-feeds.json
uv run --frozen python pipeline.py list --profile tech_business
uv run --frozen python pipeline.py editorial --profile tech_business --limit 10 --dossiers
uv run --frozen python pipeline.py editorial --profile tech_business --json \
  > output/tech-business-daily.json
uv run --frozen python pipeline.py classify <ID> emprendimiento_innovacion --profile tech_business
```

`ingest` descarga metadatos RSS/Atom públicos, no artículos completos ni contenido
tras paywall. Su puntuación preliminar no es el ranking editorial: para el ranking
diario usa `editorial`. Este último trabaja sin red sobre SQLite y considera
solo fechas reportadas válidas entre ahora menos 24 horas y ahora. Si no hay diez
acontecimientos elegibles, devuelve menos y lo advierte. No amplía la ventana ni
rellena con datos simulados. No hay scheduler nuevo ni publicación automática.
`--feed-report` registra disponibilidad, cadena de solicitudes y cantidades reales;
una lista vacía nunca se presenta como prueba de conectividad exitosa.

## Fuentes investigadas y registradas

Son endpoints públicos de los propios publicadores: RSS/Atom sin clave, modelo de
pago ni autenticación. La existencia del endpoint no concede licencia para copiar
artículos, imágenes o audio. Se conservan metadatos, extractos y enlaces con
atribución; no se eluden paywalls. Las fuentes de prensa bloqueadas son candidatas
registradas, no feeds cuya disponibilidad de contenido se haya confirmado aquí.

| Fuente / idioma | Endpoint oficial o del publicador | Tipo y estado real observado |
| --- | --- | --- |
| BBC Mundo / es | https://feeds.bbci.co.uk/mundo/rss.xml | Prensa generalista filtrada: HTTP 200, noticias pertinentes captadas |
| DW Español / es | https://rss.dw.com/rdf/rss-sp-all | Prensa generalista filtrada: HTTP 200; ningún artículo pertinente en la muestra actual |
| OpenAI Python / en | https://github.com/openai/openai-python/releases.atom | Feed oficial de versiones del SDK: HTTP 200, 10 registros; declaraciones del fabricante |
| Microsoft TypeScript / en | https://github.com/microsoft/TypeScript/releases.atom | Feed oficial de versiones: HTTP 200, 10 registros; fuera de la ventana diaria actual |
| Xataka / es | https://www.xataka.com/tag/feeds/latest | Proxy CONNECT 403 en www.xataka.com |
| Genbeta / es | https://www.genbeta.com/tag/feeds/latest | Proxy CONNECT 403 en www.genbeta.com |
| elEconomista / es | https://www.eleconomista.es/rss/rss-economia.php | Proxy CONNECT 403 en www.eleconomista.es |
| Ars Technica / en | https://feeds.arstechnica.com/arstechnica/index | Proxy CONNECT 403 en feeds.arstechnica.com |
| The Verge / en | https://www.theverge.com/rss/index.xml | Proxy CONNECT 403 en www.theverge.com |
| Google Blog / en | https://blog.google/rss/ | Empresa: proxy CONNECT 403 en blog.google |
| Microsoft Blog / en | https://blogs.microsoft.com/feed/ | Empresa: proxy CONNECT 403 en blogs.microsoft.com |
| BCE / en | https://www.ecb.europa.eu/rss/press.html | Fuente oficial económica: proxy CONNECT 403 en www.ecb.europa.eu |
| Financial Times / en | https://www.ft.com/rss/home | Prensa generalista filtrada: proxy CONNECT 403 en www.ft.com |

GitHub se utiliza únicamente como feed de versiones de repositorios oficiales,
no para llamar a OpenAI o a Microsoft ni consumir sus APIs. Se comprueba también
la ruta del repositorio, no solo el hostname compartido `github.com`. Las notas de
versión son información técnica de primera parte, **no periodismo independiente**;
pueden tener escasa relevancia general y puntuaciones bajas.

Se guardaron los nueve dominios bloqueados en el borrador de configuración del
entorno, preservando los feeds existentes y speech.platform.bing.com. Hace falta
revisar, guardar y publicar los cambios para probarlos en el runtime. Guardar el
borrador no habilita la red actual. Todavía no se conocen posibles redirecciones
posteriores al bloqueo inicial; si aparecen, el reporte registra sus destinos.
No se declara validado un feed especializado basándose solo en su registro.

## Clasificación bilingüe

Categorías independientes:

- `tecnologia_ia`: software, IA, chips, nube y sistemas tecnológicos.
- `empresas_negocios`: resultados empresariales, adquisiciones, empleo y negocios.
- `economia_mercados`: inflación, mercados, banca, tipos, aranceles y economía.
- `emprendimiento_innovacion`: startups, rondas de financiación e innovación.

Son reglas deterministas en español e inglés. Prioriza el titular, luego resumen
y etiquetas para proponer categoría; todos los feeds pasan después el filtro
de calidad basado exclusivamente en título y resumen. Los feeds de
versiones se clasifican como tecnología por su ámbito declarado. No es un modelo
semántico y requiere corrección editorial: se probaron falsos positivos como
«compañeros» y beneficios alimentarios para no tratarlos como empresas.
Las correcciones manuales del perfil se conservan entre captaciones.

## Ranking explicable y diversidad

| Dimensión | Máximo |
| --- | ---: |
| Impacto tecnológico | 20 |
| Repercusión empresarial | 20 |
| Relevancia económica | 20 |
| Actualidad (descenso lineal en 24 h) | 15 |
| Interés hispanohablante | 5 |
| Novedad en el archivo local | 10 |
| Prior de confiabilidad de la fuente | 10 |

El interés hispanohablante considera referencias explícitas a México, España y
Latinoamérica; sin ellas, el idioma español recibe un bono moderado, no una
presunción de impacto regional. La confiabilidad distingue prensa, empresas,
fuentes oficiales y URLs no reconocidas. Nada de ello verifica una afirmación.
Las notas técnicas sin indicadores de impacto reciben una base temática menor.

Reutiliza las cuotas y la selección diversificada del perfil internacional,
pero cuenta **grupos de publicadores**: Xataka y Genbeta comparten `webedia`;
los feeds de Microsoft comparten `microsoft`. No se presentan como confirmaciones
independientes. La cuota inicial es 40% de las plazas disponibles (hasta diez), relajable solo con aviso si faltan fuentes
o temas, o si una cuota desplazaría noticias con más de ocho puntos de ventaja.
El orden incorpora diversidad y no tiene por qué ser descendente por puntuación
base. Los componentes y ajustes quedan en el expediente JSON.

## Agrupación y originales

Agrupa IDs/URLs compartidos, titulares idénticos y coincidencias bilingües
conservadoras: entidad, acción y vocabulario de producto compartido. Compara todos
los pares del grupo para evitar cadenas de temas vagamente relacionados. Conserva
versiones de producto diferentes como acontecimientos distintos. El pequeño
vocabulario local reconoce acciones como `launch/lanza` y `acquire/adquiere`, pero
no sustituye un sistema semántico multilingüe: habrá falsos positivos y omisiones.
Todos los grupos requieren revisión editorial.

Cada noticia mantiene el titular y resumen originales, idioma, fecha y URL. La
deduplicación y SQLite conservan esos registros incluso cuando se combinan dos
copias, no solo sus enlaces. `original_articles` permite auditar los textos que
sustentan cada afirmación. No se traduce ni reemplaza el original de manera silenciosa.

La preparación editorial en español incorpora `editorial_language=es`, un enfoque
en español y comprobaciones para la audiencia objetivo. Si hay originales en otro
idioma se marca `requires_translation`; esta versión no fabrica traducciones ni
llama a servicios de pago. Un editor puede redactar posteriormente el guion español
contra los originales conservados.

## Hechos, empresas, rumores y análisis

Cada afirmación conserva sus fuentes y uno de los roles `reported_claim`,
`company_claim`, `official_claim`, `rumor` o `analysis`. Se reconocen indicios
explícitos de rumores y análisis; las heurísticas no identifican todos los casos.
Los anuncios de empresas siempre llevan una advertencia sobre el interés de su
emisor. Las fuentes oficiales económicas tampoco se confirman a sí mismas.
La prensa que reproduce un comunicado no se da automáticamente por independiente.

`verified_facts` permanece vacío mientras no exista revisión factual externa:
este módulo no tiene un verificador automático ni importa aprobaciones de un feed.
`pending_claims` contiene los textos atribuidos y pendientes; `supported_facts`
se limita a la existencia de metadatos RSS. Las comprobaciones editoriales futuras
no deben convertir un rumor o un comunicado en un hecho solo por repetirse.

## Perfiles, contratos y seguridad

La pertenencia y la categoría se guardan en `raw_data.profiles.tech_business`.
Una noticia puede pertenecer también a `international`; se preservan la categoría
y las correcciones del otro perfil. Los nuevos feeds exclusivos de negocios no
entran en el ranking internacional. Los registros históricos sin metadatos de
perfil mantienen la interpretación internacional anterior. No hay migración
ni eliminación de noticias, credenciales o perfiles.

Los expedientes mantienen `event_id`, `sources` y los IDs y URLs de afirmaciones
que exige el contrato JSON editorial, con modo heredado de **45–75 segundos**. El formato sigue
siendo compatible con `validate_script` y el adaptador de render, que continúa
exigiendo revisión y corroboración para noticias reales. No se invocó el render,
ningún proveedor de voz ni la generación de OpenAI o fal.ai. La publicación sigue
requiriendo aprobación humana explícita.

## Pruebas y ejecución real

Las pruebas unitarias bloquean red. Cubren clasificación bilingüe, aislamiento de
perfiles, persistencia de originales y correcciones, agrupación entre idiomas,
versiones distintas, independencia de publicadores, rumores, declaraciones,
cuotas y contrato JSON. Esos casos usan **fixtures simulados**, no se presentan
como noticias captadas ni hechos corroborados.

Consulta [la ejecución real y su ranking](tech-business-validation.md) para la
muestra fechada, URLs y puntuaciones. El funcionamiento real se confirmó solo para
los cuatro feeds accesibles. La agrupación entre idiomas se probó con datos
simulados; no apareció un acontecimiento bilingüe común en la muestra real.

## Principio editorial y formatos de guion

Cada expediente añade `editorial_questions`: **qué pasó**, **por qué importa**
y **qué podría pasar después**. Las preguntas pendientes no son respuestas
inventadas: el contexto y las consecuencias requieren evidencia; los escenarios
son análisis condicional, nunca hechos corroborados.

Puntuación máxima 100: impacto tecnológico/relevancia 20, empresarial 20,
económico 20, actualidad 15, fiabilidad previa 10, novedad 10 y pertinencia
hispanohablante 5. Novedad significa ausencia de coincidencia en el archivo local
de los siete días anteriores a la ventana diaria; un seguimiento recibe 2/10.
No demuestra exclusividad mundial. La diversidad usa grupos propietarios y
categorías, pero no desplaza una noticia con más de ocho puntos de ventaja.
Las excepciones quedan en `warnings`; la elección no es un fact-check.

El contrato conserva `legacy` (45–75 s) y añade `quick` (30–45 s) y `explained`
(60–75 s). Ambos exigen escenas `event`, `context`, `consequences`, `closing`.
La narración medida y el adaptador usan los límites del formato elegido; no se
estira audio para forzarlo. Subtítulos y tiempos finales siguen el audio real.

Preparación sin modelos ni solicitudes de voz:

```bash
uv run python pipeline.py editorial --profile tech_business --json > ranking.json
uv run python pipeline.py prepare-editorial-script \
  --dossier expediente.json --copy texto-editorial.json --format quick \
  --output guion-quick.json
```

`expediente.json` es un elemento de `selected` del ranking. `texto-editorial.json`
es una lista de cuatro objetos, en el orden indicado. Cada uno contiene `section`,
`narration_es`, `claim_ids` y `source_urls` tomados del expediente. El último
incluye `conditional_outlook_es` empezando por «Si » y un cierre útil (qué vigilar
o comprobar). Repetir con `--format explained` prepara la versión explicada.
La persona editora aporta el contexto sustentado y la traducción: el programa
no inventa información para completar el guion. Valida enlaces e IDs, pero no
puede verificar semánticamente que una frase sea cierta o esté bien traducida.
Los tiempos iniciales son orientativos, no equivalen a audio sintetizado.

Todo sale en estado `draft`, `publication_approved=false`. El render de noticias
reales exige revisión y corroboración independiente; ninguna acción de este
perfil publica, genera audio de pago o invoca APIs de generación.

## Filtro de calidad editorial

La captación especializada ya no admite un artículo únicamente por pertenecer a
un feed especializado. Revisa el **título y resumen originales**, sin usar etiquetas
genéricas del feed como prueba temática. Registra la evaluación de cada entrada
en `--feed-report`, con términos observados, motivos, penalizaciones y URL.
El ranking reevalúa también los registros históricos: una etiqueta antigua no
permite saltar los nuevos filtros. No borra artículos ni sus otros perfiles.

La mención de una empresa, empleo o sanciones, por sí sola, no justifica la
selección. Se requieren términos tecnológicos específicos, un tema económico
explícito o acciones empresariales/efectos en consumidores descritos en el RSS.
No se deduce crecimiento, empleo, ingresos ni inversiones a partir de un anuncio
de IA. Los impactos empresarial y económico reciben **0** cuando no hay señales
correspondientes. Los términos son indicios de lo que relata una fuente, nunca
corroboración del hecho o medida de su magnitud.

Penalizaciones acumulables: actualización rutinaria sin consecuencias descritas
**−30**, promoción/afiliación **−25**, declaración de empresa sin consecuencias
concretas **−15**, ausencia de consecuencias descritas **−10**.
Un lanzamiento de SDK no se convierte en noticia prioritaria por ser reciente.
Una corrección de seguridad con explotación activa o vulnerabilidad crítica
explícita puede conservar relevancia. No se presupone que todo comunicado
empresarial sea publicidad: conserva su clasificación de declaración interesada.
El ranking exige **35/100**, acota la puntuación final a un mínimo de cero y
registra los descartes en `quality_excluded`. La diversidad solo actúa después
de estos filtros; no rellena plazas con artículos antiguos o de baja puntuación.

Los marcadores condicionales o de previsión limitan el componente de impacto
correspondiente a **8/20**. `consequence_status` distingue
`not_described`, `source_description_unverified` y
`scenario_or_analysis_unverified`. Ninguno equivale a verificación independiente.
La evaluación léxica es conservadora y puede tener falsos positivos/negativos;
no sustituye leer el artículo y revisar causalidad, cifras, contexto y traducción.
No accede a páginas de pago ni genera consecuencias que el RSS no contenga.

Para revisar hasta 15 acontecimientos y sus descartes:

```bash
uv run python pipeline.py ingest --profile tech_business --feed-report output/feeds.json
uv run python pipeline.py editorial --profile tech_business --limit 15 --json
```

La salida de texto del ranking muestra también fecha original y motivos.
El diagnóstico de feeds conserva la cadena de solicitudes y las respuestas con
estado y `Location`; distingue HTTP del editor de `proxy_connect_status`.
Los errores no vuelcan cuerpos de respuesta ni credenciales.
Consulta [la última evaluación real de calidad](tech-business-quality-validation.md).
