# Selección editorial y preparación de guiones

## Uso local y gratuito

```sh
# Única operación de red: RSS públicos, sin APIs de pago.
uv run --frozen python pipeline.py ingest --profile international
# Desde SQLite, sin red:
uv run --frozen python pipeline.py editorial
uv run --frozen python pipeline.py editorial --dossiers
uv run --frozen python pipeline.py editorial --json > output/editorial-real.json
```

El comando no genera narración, imágenes, audio ni video y no publica contenido.
No modifica categorías ni estados de las noticias. El ranking y los expedientes
comparten el mismo JSON; cada expediente conserva las URLs originales completas.
`--limit` permite entre 1 y 50 acontecimientos (predeterminado 10).

La ventana es exactamente `[ahora - 24 horas, ahora]`, con fechas conscientes
de zona horaria. Se excluyen fechas futuras y registros sin fecha reportada
válida por el feed. Desde esta versión, `published_at_reported` distingue una
fecha RSS de la fecha de respaldo utilizada por la captación. Los registros
antiguos sin esa marca deben refrescarse con `ingest` antes de ser elegibles.
No se cambia el reloj ni se amplía la ventana para rellenar diez plazas.

## Puntuaciones y diversidad

La puntuación base de cada acontecimiento está entre 0 y 100:

| Componente | Máximo | Criterio local |
| --- | ---: | --- |
| Impacto público | 35 | Indicadores del titular sobre seguridad, salud, servicios y medios de vida |
| Actualidad | 25 | Descenso lineal desde la publicación más reciente del grupo hasta 24 horas |
| Importancia internacional | 20 | Indicadores de conflicto, sanciones, fronteras o países |
| Confiabilidad de la fuente | 20 | Prior editorial de publicador reconocido, comprobando también el dominio de la URL |

Son heurísticas explicables, no mediciones objetivas ni verificaciones de
veracidad. Un titular sensacionalista puede sobrepuntuar: hace falta revisión
humana. El prior distingue redacciones, fuentes oficiales y dominios desconocidos;
no verifica firmas, licencias ni independencia de una pieza concreta.

La selección voraz considera además +3 por fuente principal nueva, +3 por
categoría nueva y -2 por cada aparición previa de esa fuente/categoría. Prioriza
las categorías elegibles todavía no representadas antes de repetir temas. Por eso
el orden editorial no es necesariamente descendente por puntuación base.
`selection_score` muestra el valor ajustado en el momento de seleccionar;
`score_components`, `score_reasons` y `diversity_adjustment` permiten auditarlo.

La cuota inicial limita fuente principal y categoría al 40% de las plazas
solicitadas, redondeado hacia arriba. Solo se relaja una cuota cuando impide
completar la selección con candidatos restantes; cada relajación genera un
aviso. Con dos fuentes y diez plazas es necesario permitir cinco de cada una.
Si solo existe una fuente/categoría, se indica esa limitación en lugar de
inventar diversidad. Las cuotas cuentan la fuente principal, no los enlaces
secundarios de corroboración potencial. Si no hay diez acontecimientos recientes,
se devuelven menos, con aviso.

Las correcciones manuales de `classify` tienen prioridad. En el resto se intenta
clasificar por titular y se usa la categoría almacenada como respaldo. Una categoría
no implica que el acontecimiento solo tenga consecuencias en ese ámbito.

## Agrupación, atribución y corroboración

Primero se reconocen IDs, enlaces originales compartidos y titulares idénticos.
Para titulares diferentes, se comparan tokens normalizados, algunas equivalencias
léxicas y posibles entidades mediante mayúsculas. Se exige coincidencia de varios
términos y entidades; todos los pares de un grupo deben ser compatibles para
impedir cadenas que acaben juntando acontecimientos distintos.

Los grupos están marcados `lexical_candidate_requires_editorial_review`.
La heurística puede omitir duplicados o juntar actualizaciones diferentes del
mismo tema: revisar los grupos antes de escribir el guion. No se emplean LLM,
embeddings remotos ni servicios de pago. El identificador del acontecimiento es
una huella de sus IDs miembros y puede cambiar al incorporarse otra noticia.

Cada expediente contiene:

- Título, categoría, fecha y extracto atribuido del resumen RSS, limpiado de HTML.
- Todos los enlaces originales con publicador, tipo y grupo de independencia candidato.
- `supported_facts`: **solo metadatos observados del RSS**, con alcance explícito.
- `pending_claims`: titulares y resúmenes completos atribuidos, sin descomponerlos
  en afirmaciones inventadas. Se señalan cifras y declaraciones que requieren revisión.
- `independent_corroboration.status = not_established`: ni siquiera dos medios
  reconocidos bastan para declarar verificada una afirmación. Podrían citar la misma
  nota de agencia o comunicado. No se han leído las páginas completas ni evidencias primarias.
- Las piezas de ONU se identifican como oficiales y se advierte expresamente que
  no confirman de forma independiente sus propias declaraciones. También se deben
  contrastar las declaraciones oficiales reproducidas por otros medios.

`review_required` siempre es verdadero y `publication_approved` siempre falso.
Que un acontecimiento tenga alto impacto no elimina las comprobaciones pendientes.

## Guiones de 45 a 75 segundos

Contrato JSON: [editorial-script.schema.json](../schemas/editorial-script.schema.json).
Ejemplo de estructura: [editorial-script.example.json](../schemas/editorial-script.example.json).
**El ejemplo es una plantilla editorial, no un guion de noticias reales.**
Sustituir marcadores por los IDs de un expediente y redactar la narración tras
revisar sus evidencias. Una duración nominal no garantiza el tiempo real de voz:
medir el audio y ajustar el guion y los subtítulos antes de renderizar.

El contrato exige idioma `es`, narración por escena, referencias a afirmaciones y
URLs, subtítulos temporizados y propuestas de animación híbrida: mapas, cronologías,
tipografía, gráficos, imágenes con licencia y movimiento vectorial. Cada escena
debe ser contigua y cada subtítulo estar dentro de su escena, sin solapamientos.
Los gráficos y mapas que expresen hechos deben citar los IDs correspondientes.
No se descargan imágenes ni se generan animaciones con este módulo.

Validación local con trazabilidad:

```python
import json
from techslop.editorial.script_format import validate_script

report = json.load(open('output/editorial-real.json'))
event = report['selected'][0]
script = json.load(open('output/guion-editorial.json'))
validated = validate_script(script, event)
```

Además de validar el esquema, `validate_script` rechaza IDs de afirmaciones y URLs
ausentes del expediente, exige la fuente original de cada afirmación y comprueba
las referencias de la animación. La revisión humana debe comprobar español,
exactitud, citas, derechos de materiales y ritmo; el campo `language` no detecta
el idioma automáticamente. `editorial_status=reviewed` no equivale a aprobación
de publicación. El contrato prohíbe `publication_approved=true`.

Este formato editorial **todavía no es el `Script` del renderizador antiguo**.
No se envía directamente a `voice` o `video`; queda pendiente el adaptador de
escenas/subtítulos al renderizador. Se conserva el flujo manual anterior y su
protección de publicación. No se activa la generación de OpenAI ni fal.ai.

## Evidencia de validación

Las pruebas unitarias de selección, cuotas, agrupación, límites temporales,
trazabilidad, fuentes oficiales y contrato JSON usan datos simulados y bloquean
HTTP real. La ejecución real usa únicamente metadatos recibidos de RSS y SQLite;
no verifica el contenido factual de las noticias ni genera un video.

```sh
uv run --frozen pytest tests/ --ignore=tests/integration -q
```
