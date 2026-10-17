# Primer render híbrido local

Esta guía conserva el primer render con tono de prueba. La versión actual incorpora
[voz local, Edge configurable y mezcla musical](narration-sync.md); `auto` ya no
desciende silenciosamente a un tono: usa voz local o informa un error.

El adaptador `techslop/render/adapter.py` conecta el contrato editorial con clips
originales de Pillow y el ensamblador existente `assemble_video_motion` de FFmpeg.
No necesita Remotion: esta versión usa ilustraciones geométricas, títulos,
subtítulos ASS y transiciones; las dependencias instaladas cubren ese trabajo.
No importa módulos de publicación, OpenAI ni fal.ai.

## Reproducir la demostración

Desde el checkout existente, con las dependencias instaladas:

```sh
uv run --frozen python pipeline.py render-editorial \
  --script examples/hybrid-demo/script.json \
  --dossier examples/hybrid-demo/dossier.json \
  --presentation examples/hybrid-demo/presentation.json \
  --output-dir output/mi-demo
```

El directorio de salida debe estar vacío o no existir: no se sobrescriben
artefactos del usuario. Edge TTS se intenta únicamente con la voz gratuita
`es-MX-JorgeNeural`, respetando `HTTPS_PROXY`. Si falla, se genera un tono con
FFmpeg. `--test-audio` omite la petición y permite reproducir la demo completamente
sin red. La etiqueta `AUDIO DE PRUEBA · TONO, SIN VOZ` permanece en pantalla.
No se presenta el tono como narración en español; la narración española está
preparada en el JSON y los subtítulos.

En esta ejecución Edge TTS falló con `ClientHttpProxyError` al acceder al servicio
`speech.platform.bing.com`. La primera ejecución dejó esa evidencia en
`output/first-hybrid-demo/verification.json`. La versión final se volvió a renderizar
con `--test-audio`, sin repetir una conexión bloqueada. No se modificó la política
de Internet, no se añadieron credenciales ni se desactivó TLS.

Los expedientes actuales no tienen corroboración independiente establecida.
Por ello el ejemplo es **una demostración ficticia de producción audiovisual**,
no una noticia ni una recreación factual. Esa advertencia permanece en pantalla.
El contrato, el manifiesto visual y el expediente de ejemplo están versionados
en `examples/hybrid-demo/` y se copian junto al video para conservar trazabilidad.

## Cuatro escenas reutilizables

| Tipo | Animación local |
| --- | --- |
| `intro` | Titular que entra suavemente y marcos geométricos con acercamiento gradual |
| `explanation` | Tarjetas ilustradas de guion, escena y fuente, con desplazamiento suave |
| `chart` | Barras que crecen con easing; solo segundos reales de audio medidos con ffprobe |
| `closing` | Resumen y tarjeta de referencias, con paneo vertical leve |

Lienzo nativo 1080×1920 a 30 FPS; zonas seguras para títulos, subtítulos,
advertencias y referencias. Colores de alto contraste y tipografía DejaVu local.
No se descargan fotografías ni mapas, ni se fabrican estadísticas.

El manifiesto de presentación, independiente del contrato editorial, selecciona
el tipo, el titular y el texto de cada escena. Para los gráficos solo se acepta
`chart_metric=measured_audio_seconds`: los valores salen de los archivos reales,
no de números escritos por el guionista. Una extensión futura para datos
periodísticos necesitará valores, unidades y evidencias revisadas explícitamente.
Se rechazan campos arbitrarios de estadísticas y recursos externos no implementados.

## Audio, subtítulos y transiciones

Se genera y mide un fragmento de audio por escena. Sus duraciones reales determinan
la línea de tiempo; nunca se estira silenciosamente el audio para encajar el
plan nominal. Si la suma queda fuera de 45–75 segundos, hay que editar la narración
(la demo puede recurrir al tono explícito si Edge devuelve una duración inválida).

Si Edge devuelve límites de palabras y coinciden los textos declarados, se usan
esos tiempos. En los demás casos se conservan los textos del contrato y se escalan
sus intervalos a la duración medida de cada escena. La lectura por palabra dentro
de cada intervalo es una estimación, registrada como `scaled_contract_reading_cues`:
no es alineación forzada de voz. En modo tono, los subtítulos son instrucciones
de lectura, no palabras que se oigan en el audio.

Cada clip excepto el último lleva una cola de 0,4 segundos. Las disoluciones
`xfade` consumen esas colas: no acortan el audio ni adelantan el inicio de las escenas.
Las entradas comienzan en los límites medidos, con una disolución de 0,4 segundos.
La codificación limita hilos para funcionar en la máquina cloud, usa H.264/AAC,
píxeles `yuv420p` y `faststart` para facilitar reproducción web.

## Verificación y artefactos

La salida principal es `techslop-demo.mp4`. Se guardan además:

- `verification.json`: duración, resolución, FPS, códecs, audio, tamaño y decodificación.
- `render-plan.json`: tiempos medidos, origen del audio y datos del gráfico.
- `script.json`, `dossier.json`, `presentation.json`: entradas usadas.
- `timestamps.json` y `captions.ass`: subtítulos y sus tiempos.
- `scene-*.png`, clips y audio: material de diagnóstico local.

`verify_mp4` comprueba resolución, tasa, códecs, duración final y concordancia de
los streams; decodifica el archivo completo con `ffmpeg -xerror` y mide que el audio
no sea silencio. Esto acredita integridad técnica y compatibilidad de decodificación,
no una revisión humana en todos los navegadores ni del contenido periodístico.
Los fotogramas de la ejecución se inspeccionan también visualmente.

```sh
uv run --frozen pytest tests/ --ignore=tests/integration -q
```

Las pruebas unitarias simulan el fallo de Edge, verifican la adaptación temporal,
subtítulos, cuotas de contenido corroborado, rechazo de cifras arbitrarias y
animación de los cuatro tipos. La ejecución de aceptación genera un MP4 completo
real y decodifica todos sus paquetes. Las pruebas existentes de publicación siguen
exigiendo aprobación humana explícita. Renderizar no aprueba publicar.

## Coste y siguientes pasos

No se llama a APIs de pago: coste externo de APIs de esta prueba **0 USD**.
El cómputo y almacenamiento del entorno no tienen una tarifa visible desde este
proceso, por lo que no se afirma que la infraestructura sea gratuita.

Para un estilo híbrido definitivo faltan dirección de arte y plantillas editoriales
más variadas, ilustraciones propias con más detalle, voz accesible y mezcla de
sonido, alineación precisa de subtítulos y revisión en dispositivos. Fotografías,
mapas y gráficos periodísticos necesitarán fuentes, datos y derechos verificados.
Los movimientos actuales son 2D: acercamientos geométricos y desplazamientos suaves,
no cámara 3D ni animación de personajes. La demostración no usa imágenes generadas.
