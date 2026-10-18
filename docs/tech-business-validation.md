# Validación real de tech_business

Ejecución: 2026-10-18T16:00:55.493338-06:00 (Ciudad de México).

La captación del perfil devolvió 25 registros reales: 5 en español y 20 en inglés. 5 son elegibles en las últimas 24 horas; se seleccionaron 5 acontecimientos. No se completaron diez con noticias antiguas ni simuladas.

| Fuente | Idioma | Estado real | Registros RSS | Incorporados al perfil |
| --- | --- | --- | ---: | ---: |
| ars_technica | en | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| bbc_mundo | es | HTTP 200 | 34 | 5 |
| dw | es | HTTP 200 | 16 | 0 |
| ecb | en | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| eleconomista | es | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| ft | en | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| genbeta | es | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| google_blog | en | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| microsoft_blog | en | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| openai_releases | en | HTTP 200 | 10 | 10 |
| the_verge | en | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |
| typescript_releases | en | HTTP 200 | 10 | 10 |
| xataka | es | ProxyError (CONNECT 403 observado en la comprobación inicial) | 0 | 0 |

## Ranking diario real

Las puntuaciones son bases heurísticas sobre 100; el orden incluye diversidad. Ningún contenido factual se declaró corroborado.

| Puesto | Puntos | Categoría | Titular original | Fuente y enlace original |
| --- | ---: | --- | --- | --- |
| 1 | 55.17 | economia_mercados | Cuánto aporta la rica provincia de Alberta a la economía de Canadá y qué pasaría si logra la independencia | [bbc_mundo](https://www.bbc.com/mundo/articles/c95yng8me7vmo?at_medium=RSS&at_campaign=rss) |
| 2 | 37.84 | empresas_negocios | Perdí mi cabello por la quimioterapia y ahora las estrellas llevan las pelucas que diseño | [bbc_mundo](https://www.bbc.com/mundo/articles/cq5yngv748zko?at_medium=RSS&at_campaign=rss) |
| 3 | 32.07 | tecnologia_ia | v3.35.1 | [openai_releases](https://github.com/openai/openai-python/releases/tag/v3.35.1) |
| 4 | 30.51 | tecnologia_ia | v3.35.0 | [openai_releases](https://github.com/openai/openai-python/releases/tag/v3.35.0) |
| 5 | 45.93 | economia_mercados | Trump levanta sanciones contra Rusia y se intensifica la disputa con Zelensky | [bbc_mundo](https://www.bbc.com/mundo/articles/c6x2vx8pvdv2o?at_medium=RSS&at_campaign=rss) |

Cuota por fuente relajada a 3: faltan fuentes distintas elegibles.
Solo hay 5 acontecimientos elegibles; no se completa con noticias antiguas.

Las versiones de OpenAI Python son anuncios técnicos de primera parte, no cobertura periodística independiente. Se conservaron sus títulos y resúmenes en inglés; se marcó la traducción al español como pendiente. Los diez registros de TypeScript se excluyeron del ranking por antigüedad, sin modificar sus fechas.

## Pruebas simuladas y alcance

176 pruebas unitarias aprobadas con acceso de red bloqueado. Los fixtures comprobaron clasificación en ambos idiomas, agrupación bilingüe, identificación de rumores y anuncios, trazabilidad de resúmenes, convivencia de perfiles, diversidad por publicador y compatibilidad del contrato de guion. Esas noticias de prueba no forman parte de este ranking.

La ejecución real comprobó RSS/Atom, persistencia, clasificación, ranking y expedientes. No hubo un mismo acontecimiento bilingüe entre las fuentes disponibles, por lo que esa agrupación solo tiene validación simulada. Tampoco se verificó el contenido de artículos completos ni se produjo un video.

Los diagnósticos JSON y expedientes completos de esta ejecución están en `output/tech-business-feeds.json` y `output/tech-business-real.json` dentro de la máquina; esta página versionada conserva la evidencia legible sin depender de enlaces internos descargables.

No se consumieron APIs de pago, cambiaron credenciales ni publicaron contenidos. Los dominios bloqueados se guardaron en el borrador de red y requieren aplicación antes de validar sus feeds.
