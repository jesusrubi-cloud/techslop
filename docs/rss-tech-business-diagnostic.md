# Diagnóstico RSS Tech Business mediante GitHub Actions

El workflow `.github/workflows/rss-tech-business-diagnostic.yml` ejecuta solo un
diagnóstico HTTP de lectura. **No se ha ejecutado todavía en GitHub Actions**:
ninguna fuente se declara accesible desde ese runner hasta revisar una ejecución
real. Los resultados anteriores del proxy Codex no predicen el resultado de GitHub.

## Ejecutarlo desde GitHub

1. Abre y revisa el Pull Request de la rama `feat/tech-business-editorial-formats`
   hacia `main`. El workflow debe incorporarse primero a la rama predeterminada
   para aparecer y poder activarse con `workflow_dispatch`.
2. En el repositorio, entra en **Actions**.
3. En la lista de workflows, selecciona **Diagnóstico RSS Tech Business**.
4. Pulsa **Run workflow**, elige la rama que contiene el workflow (normalmente
   `main`) y pulsa el botón verde **Run workflow**. No requiere secretos ni Voice ID.
5. Abre la ejecución y el job **diagnose**. El paso **Diagnosticar nueve feeds
   públicos** muestra HTTP, errores seguros, redirecciones, formato y registros.
6. En **Summary**, revisa el informe y baja hasta **Artifacts**. Pulsa
   **rss-tech-business-diagnostic-<run_id>-<intento>** para descargar el ZIP.
7. Extrae `rss-report.json` y `rss-report.md`. El Markdown se puede abrir como
   texto; el JSON contiene los campos completos. Los artefactos duran **14 días**.

Se necesita una cuenta con permiso para activar Actions. Si Actions está
inhabilitado por la política del repositorio, debe habilitarlo su administrador.
La existencia del workflow en una rama de PR no significa que ya se haya ejecutado.
No se dispara por `push`, PR, horario ni por cambios en las fuentes.

## Qué se comprueba

Lee directamente los nueve endpoints registrados en
`techslop/profiles/tech_business.py`: Xataka, Genbeta, elEconomista, Ars Technica,
The Verge, Google Blog, Microsoft Blog, BCE y Financial Times. No modifica ese
registro, ninguna regla editorial, las categorías ni los perfiles existentes.
Los feeds de BBC, DW y los repositorios de versiones no forman parte de esta
prueba especializada. Si deja de haber exactamente nueve fuentes esperadas, el
programa falla explícitamente en vez de diagnosticar otra lista silenciosamente.

El script usa exclusivamente la biblioteca estándar de Python: no instala el
proyecto ni carga clientes de voz, modelos o publicadores; tampoco accede a la
base SQLite. Realiza un GET por endpoint y sigue como máximo cinco redirecciones
HTTPS ordinarias. Registra cada estado de redirección y destino, y el último
destino solicitado. No reintenta bloqueos, cambia de identidad ni busca mirrors.
No sigue redirecciones a login, OAuth, suscripción o paywall, ni URLs con usuario
y contraseña. Respeta TLS y el proxy del runner; no suministra autenticación.

Límites fijos: **2 MiB más un byte de detección** por descarga, socket de hasta
**8 segundos**, presupuesto de **30 segundos** por fuente comprobado antes de cada
solicitud/lectura, y job de **8 minutos**. Una operación en curso puede agotar su
timeout de socket antes de comprobar otra vez el presupuesto. No se aceptan
respuestas comprimidas: solicita `identity` para limitar los bytes que analiza.
No lee cuerpos HTTP de error ni descarga páginas enlazadas por los artículos.

## Interpretar el informe

| Estado JSON | Significado |
|---|---|
| `accessible` | HTTP 200, XML RSS/Atom/RSS 1.0 válido estructuralmente y al menos un registro. |
| `blocked` | HTTP 401/402/403/407/429/451 o denegación CONNECT 403/407 reconocida. No se evade ni se reintenta. |
| `invalid` | HTTP 404/410, XML malformado o documento que no es RSS/Atom (incluye HTML con HTTP 200). |
| `pending_confirmation` | Timeout, error de red/TLS, servidor temporalmente fallido, límite alcanzado, redirección no admitida o feed válido vacío. |

`http_status` es el último código HTTP recibido, no un estado supuesto; puede
ser `null` si el proxy bloquea antes de contactar al editor. `error_code` no
contiene mensajes arbitrarios de excepción. Los informes omiten usuario,
contraseña, consultas y fragmentos de URL para no conservar tokens redirigidos.
No registran cabeceras de autenticación, cookies ni cuerpos de error.

La validación XML comprueba formato y estructura básica y cuenta `item`/`entry`;
no garantiza que cada registro tenga título, enlace o fecha útil, ni que sea
reciente. No declara autorización para reproducir artículos, licencias,
corroboración, calidad editorial ni derecho a superar un paywall. Un feed vacío
requiere nueva comprobación manual, no se declara funcionando.

Un job verde significa que **se completó el diagnóstico**, no que todos los feeds
funcionen. Los fallos por fuente se guardan y se continúa con las otras. Los
informes se suben incluso cuando falla un paso, si llegaron a generarse; una
cancelación o timeout del job puede impedir la subida. No se versionan respuestas
simuladas como resultados reales.

## Validación local sin red ni APIs de pago

```bash
UV_CACHE_DIR=/workspace/.cache/uv uv run --frozen pytest tests/test_rss_diagnostic.py -q
UV_CACHE_DIR=/workspace/.cache/uv uv run --frozen pytest tests/ --ignore=tests/integration -q
```

Las pruebas usan respuestas simuladas para RSS/Atom/RDF, HTML, XML inválido,
feeds vacíos, bloqueos, redirecciones, timeouts y límites. La suite bloquea la
red externa. Para un diagnóstico real local, opcional y distinto de las pruebas:

```bash
python3 scripts/diagnose_rss_tech_business.py --output-dir output/rss-diagnostic
```

No ejecuta captación, ranking, guiones, narración, render ni publicación. No usa
ElevenLabs, OpenAI u otras APIs de pago. El runner alojado y los artefactos sí
están sujetos a las cuotas/minutos de GitHub Actions de tu cuenta; no se activan
servicios ni planes de pago desde el workflow. Esta prueba no decide qué fuentes
integrar definitivamente: esa decisión sigue pendiente del informe real.
