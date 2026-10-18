# Calidad editorial: comprobación con noticias reales

Ranking generado: **2026-10-18T22:21:00.038838+00:00 UTC**. Ventana: 2026-10-17T22:21:00.038838+00:00 → 2026-10-18T22:21:00.038838+00:00.

Rama: `feat/tech-business-editorial-formats`. Se ejecutó la captación real con la configuración de Internet disponible. No se usaron APIs de pago ni se generó o publicó video.

## Conectividad real y redirecciones

Los nueve dominios especializados están presentes en la configuración guardada consultada. Aun así, el proxy de esta instancia respondió CONNECT 403 en los nueve intentos. La configuración guardada no demuestra su aplicación efectiva a esta máquina. No se modificó la política, no se evitó el proxy y no se desactivó TLS.

| Fuente | Feed solicitado | Resultado observado | Redirecciones observadas |
|---|---|---|---|
| ars_technica | https://feeds.arstechnica.com/arstechnica/index | ProxyError; CONNECT 403 en feeds.arstechnica.com | No observables: fallo antes de respuesta HTTP del editor |
| bbc_mundo | https://feeds.bbci.co.uk/mundo/rss.xml | HTTP 200; 34 registros, 3 afines | Ninguna; respuesta directa |
| dw | https://rss.dw.com/rdf/rss-sp-all | HTTP 200; 16 registros, 0 afines | Ninguna; respuesta directa |
| ecb | https://www.ecb.europa.eu/rss/press.html | ProxyError; CONNECT 403 en www.ecb.europa.eu | No observables: fallo antes de respuesta HTTP del editor |
| eleconomista | https://www.eleconomista.es/rss/rss-economia.php | ProxyError; CONNECT 403 en www.eleconomista.es | No observables: fallo antes de respuesta HTTP del editor |
| ft | https://www.ft.com/rss/home | ProxyError; CONNECT 403 en www.ft.com | No observables: fallo antes de respuesta HTTP del editor |
| genbeta | https://www.genbeta.com/tag/feeds/latest | ProxyError; CONNECT 403 en www.genbeta.com | No observables: fallo antes de respuesta HTTP del editor |
| google_blog | https://blog.google/rss/ | ProxyError; CONNECT 403 en blog.google | No observables: fallo antes de respuesta HTTP del editor |
| microsoft_blog | https://blogs.microsoft.com/feed/ | ProxyError; CONNECT 403 en blogs.microsoft.com | No observables: fallo antes de respuesta HTTP del editor |
| openai_releases | https://github.com/openai/openai-python/releases.atom | HTTP 200; 10 registros, 10 afines | Ninguna; respuesta directa |
| the_verge | https://www.theverge.com/rss/index.xml | ProxyError; CONNECT 403 en www.theverge.com | No observables: fallo antes de respuesta HTTP del editor |
| typescript_releases | https://github.com/microsoft/TypeScript/releases.atom | HTTP 200; 10 registros, 10 afines | Ninguna; respuesta directa |
| xataka | https://www.xataka.com/tag/feeds/latest | ProxyError; CONNECT 403 en www.xataka.com | No observables: fallo antes de respuesta HTTP del editor |

Los endpoints que continúan bloqueados no pueden declararse feeds válidos o inválidos: no hubo respuesta del editor. No se inventaron endpoints alternativos ni redirecciones. Para evaluar las nueve fuentes sigue siendo necesario que la política permita estas conexiones en la instancia de ejecución; volver a comprobar tras aplicar efectivamente esa política.

## Captación y ranking

Se recibieron 70 registros RSS/Atom de las cuatro fuentes accesibles; 23 pasaron el filtro temático para archivo. Los lanzamientos rutinarios se conservan como material técnico pero no superan el umbral editorial. Dentro de las últimas 24 horas, 3 registros son afines y **1 acontecimiento supera 35/100**. No se amplía la ventana ni se rellena hasta 15.

| Puesto | Titular original y enlace | Fuente | Fecha UTC | Categoría | Puntos /100 | Justificación |
|---|---|---|---|---|---:|---|
| 1 | [Cuánto aporta la rica provincia de Alberta a la economía de Canadá y qué pasaría si logra la independencia](https://www.bbc.com/mundo/articles/c95yng8me7vmo?at_medium=RSS&at_campaign=rss) | bbc_mundo | 2026-10-18T13:12:56+00:00 | economia_mercados | 39.79 | Conexión económica explícita en el titular: aportación de Alberta a la economía canadiense. Incluye un escenario de independencia; impacto económico limitado a 8/20. El resumen no aporta cifras para verificar esa contribución ni prueba consecuencias realizadas. |

Las puntuaciones decaen con la antigüedad y corresponden a la hora indicada. La candidata es un **análisis económico pendiente de comprobación**, no una noticia de impacto ya corroborado. El sistema no afirma cifras, efectos de una independencia ni resultados futuros.

## Descartes de los registros recientes del archivo

| Registro original | Razón |
|---|---|
| Cindy Crawford habla por primera vez tras la muerte de su hijo Presley: "Estoy más que destrozada" | Sin conexión sustancial descrita en el RSS; política o empresa mencionada no implica impacto económico.; No se describe una consecuencia económica, empresarial o para consumidores: -10; no se infiere. |
| Trump levanta sanciones contra Rusia y se intensifica la disputa con Zelensky | Sin conexión sustancial descrita en el RSS; política o empresa mencionada no implica impacto económico.; No se describe una consecuencia económica, empresarial o para consumidores: -10; no se infiere. |
| Perdí mi cabello por la quimioterapia y ahora las estrellas llevan las pelucas que diseño | Sin conexión sustancial descrita en el RSS; política o empresa mencionada no implica impacto económico.; No se describe una consecuencia económica, empresarial o para consumidores: -10; no se infiere. |
| v3.35.1 | Puntuación inferior al umbral editorial 35/100; puntuación final 0.00/100. SDK rutinario: −30; declaración empresarial de bajo impacto: −15; sin consecuencias descritas: −10. |
| v3.35.0 | Puntuación inferior al umbral editorial 35/100; puntuación final 0.00/100. SDK rutinario: −30; declaración empresarial de bajo impacto: −15; sin consecuencias descritas: −10. |

La nota de sanciones no describe consecuencias comerciales, energéticas o empresariales concretas en su RSS; no se deducen. La historia personal sobre pelucas no aporta datos de escala, inversiones, competencia o empleo. También se corrigió un falso positivo descubierto en la revisión real: «investigada» coincidía con un patrón demasiado amplio de «investment». El caso de celebridades queda excluido, conservando intacto el archivo y los perfiles previos.

Los artículos sobre Starlink y centros de datos que permanecen en el archivo están fuera de la ventana; no se incorporaron para llenar plazas.

## Evidencia y limitaciones

La conectividad, los registros, títulos, fechas y ranking de esta página proceden de solicitudes reales. Los datos RSS no equivalen a hechos corroborados. Las redirecciones hacia un destino bloqueado, promoción, despidos, inversión, vulnerabilidades críticas, escenarios y aislamiento de perfiles se verifican con pruebas simuladas: no se presentan como captación real. La heurística puede omitir noticias relevantes o aceptar conexiones tangenciales; exige revisión editorial del artículo completo. No realiza traducción automática ni fact-check semántico.

Validación automatizada: **202 pruebas aprobadas**, con la red de las pruebas unitarias bloqueada. Incluye regresiones de perfiles, publicación con aprobación humana, guiones, narración y subtítulos; no se ejecutaron integraciones externas ni solicitudes a servicios de pago.
