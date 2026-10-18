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
y etiquetas; las fuentes generalistas exigen alguna señal temática. Los feeds de
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
| Actualidad (descenso lineal en 24 h) | 20 |
| Interés hispanohablante | 10 |
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
o temas; se prioriza representar categorías presentes antes de repetirlas.
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
que exige el contrato JSON editorial de **45–75 segundos**. El formato sigue
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
