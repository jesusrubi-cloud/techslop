# Narración y sincronización audiovisual

## Resultado de esta versión

Se creó la rama `feat/narracion-sincronizada`. La nueva demo ficticia tiene voz
local real, música original opcional y subtítulos temporizados con eventos del
motor. No se publicaron contenidos ni se llamaron APIs de pago.

| Comprobación del MP4 generado | Resultado |
| --- | --- |
| Duración de audio / contenedor | 67,655 s / 67,655 s |
| Formato | 1080×1920, 30 FPS, H.264 y AAC |
| Fotogramas | 2029 |
| Tamaño | 2.991.408 bytes (2,99 MB decimales) |
| Voz | eSpeak NG, `es-419`, español latinoamericano sintético |
| Subtítulos | 138 eventos de palabra del motor, sin Whisper ni estimación uniforme |
| Volumen medio / máximo del MP4 | −17,1 / −1,3 dBFS; sin clipping observado |
| Reproducción técnica | Decodificación completa de video y audio aprobada con FFmpeg |
| Pruebas automatizadas | 99 aprobadas en esta máquina |
| Coste externo de APIs | 0 USD |

No se afirma que esta voz sea la voz mexicana de Microsoft ni tenga calidad neural.
Es una alternativa local inteligible, de timbre robótico, para seguir desarrollando
sin depender del proxy. `es-419` es la variante latinoamericana del motor; sus
alias incluyen `es-mx`, pero no acredita un acento mexicano específico.
No se utilizaron voces MBROLA ni modelos que requieran licencias adicionales.

El tiempo del primer render con voz fue 43,21 s. Se corrigió después el remuestreo
de la mezcla y se reutilizaron los clips: nueva mezcla, ensamblado y verificación
tardaron 19,92 s adicionales. Cómputo/almacenamiento cloud y minutos de GitHub
Actions dependen del plan del usuario; su precio no es observable aquí.
La decodificación y los fotogramas extraídos validan integridad y presentación,
no una prueba manual de reproducción en todos los navegadores.

## Edge TTS: diagnóstico y configuración de red

La petición a `https://speech.platform.bing.com/` recibió **403 CONNECT del proxy**,
antes de TLS o del handshake WebSocket. El intento real de `auto` confirmó
`ClientHttpProxyError`, y pasó automáticamente a voz local: 67,655238 s y 138
límites de palabra. No hay evidencia de un fallo de voz, credenciales o cuotas de
Microsoft: el bloqueo observado está antes del servicio.

La lista de dominios del entorno solo contenía los tres feeds de noticias.
Se guardó en el borrador una actualización que conserva esos dominios y añade
`speech.platform.bing.com`. Es un hostname válido para la configuración permitida.
**Guardar el borrador no habilitó la conexión actual**: falta revisar y guardar
los cambios en los ajustes del entorno y publicar la configuración. Después hay
que volver a probar la síntesis completa, pues un GET HTTP por sí solo no acredita
que el proxy permita WebSocket. No se desactivó TLS ni se evitó el proxy.

Para comprobarlo tras aplicar el cambio, usa `--voice-provider edge` en un
nuevo directorio de salida. Esta opción falla explícitamente si Edge no funciona;
no oculta el resultado con otra voz. El dominio está guardado, pero no se declara
validado el audio mexicano de Edge mientras la petición real siga bloqueada.

## Proveedores y configuración

| Variable / opción | Función |
| --- | --- |
| `NARRATION_PROVIDER=auto` | Predeterminado: intenta Edge y recurre a eSpeak local si falla |
| `NARRATION_PROVIDER=edge` | Solo Edge; error explícito si no funciona |
| `EDGE_TTS_VOICE=es-MX-JorgeNeural` | Voz mexicana; también puede seleccionarse una voz `es-MX-…` disponible |
| `NARRATION_RATE=+0%` | Velocidad de Edge |
| `NARRATION_PROVIDER=espeak` | Solo voz local, sin red |
| `LOCAL_TTS_VOICE=es-419` | Variante local latinoamericana |
| `LOCAL_TTS_RATE=155` | Palabras por minuto; intervalo permitido 100–220 |
| `NARRATION_PROVIDER=provided` | Lee audio aportado por el usuario, sin llamar a ningún proveedor |
| `NARRATION_AUDIO_DIR=...` | Carpeta con `scene-1.wav`, `scene-2.wav`, etc. y opcionales `scene-1.words.json` |
| `NARRATION_PROVIDER=test` / `--test-audio` | Tono de prueba explícito; nunca se presenta como voz |
| `--voice-provider …` | Sobrescribe la selección para ese render |

Cada archivo `.words.json` aportado es una lista de objetos `word`, `start`, `end`
con segundos relativos a la escena. Sin tiempos aportados se escalan los intervalos
del contrato y se marca esa limitación; no se finge alineación de palabras real.
Los audios aportados pueden proceder de cualquier proveedor configurado fuera de
este renderizador; aquí no se contratan ni se llaman servicios de pago.

Se conserva el selector anterior `TTS_PROVIDER` y sus clases para el flujo legado.
El nuevo renderizador tiene un selector separado y solo admite los modos de la
lista: rechaza `openai` u otros servicios de pago antes de sintetizar. Tampoco
invoca Whisper, descarga modelos ni utiliza fal.ai.

En Linux se necesita `espeak-ng` para la voz local. Instalación habitual con el
administrador de paquetes: `sudo apt-get update` y `sudo apt-get install espeak-ng`.
En esta máquina Debian 13 sin root, se descargaron paquetes mediante APT usando
metadatos firmados y checksums verificados y se extrajeron en `/workspace/.tools/espeak`.
El procedimiento repetible está en `scripts/install_local_voice_debian.sh`;
no altera el sistema y está limitado a Debian 13 amd64. Para otra ubicación pueden
configurarse `ESPEAK_LIBRARY_PATH` y `ESPEAK_DATA_PATH`.

## Reproducir la demo con voz y música

```sh
bash scripts/install_local_voice_debian.sh  # solo Debian 13 amd64 sin instalación previa
uv run --frozen python scripts/create_demo_music.py --output output/voice-bed.wav
uv run --frozen python pipeline.py render-editorial \
  --script examples/hybrid-demo/script.json \
  --dossier examples/hybrid-demo/dossier.json \
  --presentation examples/hybrid-demo/presentation.json \
  --output-dir output/mi-demo-con-voz \
  --voice-provider espeak \
  --music output/voice-bed.wav \
  --music-license output/voice-bed.license.json
```

Omitir ambas opciones `--music` y `--music-license` produce voz sin música.
El directorio de salida debe ser nuevo o estar vacío. El ejemplo sigue siendo una
demostración ficticia: no se convirtió una noticia pendiente en un hecho verificado.

## Tiempos, mezcla y ritmo

Cada fragmento se mide con ffprobe y determina el inicio y el final de su escena.
No se estira el audio para encajar un tiempo nominal. La suma debe seguir dentro
de los 45–75 s del contrato; si no, hay que editar texto o velocidad.
El gráfico reutiliza esas mediciones, no estadísticas periodísticas inventadas.

Edge devuelve límites de palabra cuando está disponible. La alternativa local usa
`espeakEVENT_WORD` de la biblioteca eSpeak NG con sus posiciones de audio; conserva
las palabras Unicode, incluidas las tildes. Los finales se sitúan en el siguiente
evento o al final del PCM; pueden incluir una pausa y no equivalen a límites exactos
de fonema. No son tiempos repartidos uniformemente. Los subtítulos ASS conservan
la agrupación legible de hasta cinco palabras y se corrigió el acarreo al redondear
centésimas cerca de un cambio de segundo/minuto.

Las transiciones mantienen la cola de 0,4 s para no acortar la narración. Las tarjetas
y las barras entran de forma escalonada con easing, en lugar de moverse todas al mismo
tiempo. Sigue siendo animación 2D, con pequeños desplazamientos y acercamientos.

La música requiere un manifiesto con `title`, `author`, `source`, `license` y `sha256`.
Solo se aceptan `CC0-1.0` y `CC-BY-4.0`, con hash coincidente. El manifiesto acredita
la declaración de licencia aportada, no verifica jurídicamente una fuente externa;
la atribución se conserva en `verification.json` y debe acompañar cualquier difusión.
El generador de esta demo sintetiza tonos y acordes originales, sin muestras de terceros,
y dedica el audio a CC0-1.0. No hay descarga de música.

La mezcla normaliza la voz con un objetivo de −16 LUFS, ajusta el fondo y aplica
`sidechaincompress` controlado por la voz (ratio 12, ataque 10 ms, recuperación 250 ms).
El limitador evita saturación. Una prueba con voz intermitente mide la componente
musical y comprueba su reducción durante voz y recuperación durante silencios.
Esa prueba detectó una incompatibilidad de tasas internas tras `loudnorm`: se añadió
remuestreo explícito después de normalizar. El MP4 final incluye esa corrección.

## Descargar mediante GitHub Actions

Workflow: **Descargar demo con voz**, en
`.github/workflows/download-narrated-demo.yml`.

1. Revisa e integra `feat/narracion-sincronizada` en la rama predeterminada para que
   GitHub reconozca el nuevo workflow manual.
2. En GitHub abre **Actions → Descargar demo con voz → Run workflow** y selecciona
   `feat/narracion-sincronizada` (o `main` si ya se integró).
3. Abre la ejecución terminada y ve a **Summary → Artifacts → techslop-demo-con-voz**.
4. Descarga y descomprime el ZIP. Incluye el MP4, `contact-sheet.jpg`,
   `verification.json` (voz, música y licencia) y `SHA256SUMS.txt`.
5. Arrastra el MP4 a una ventana del navegador para reproducirlo.

El workflow solo recupera los bytes ya generados en
`examples/narrated-demo/download-bundle.zip`; comprueba hashes contra el manifiesto.
No necesita servicios de voz, instalación de eSpeak ni conexión a Edge. Solo tiene
permiso de lectura del repositorio y disparador manual. Los artefactos caducan a
los siete días y pueden recuperarse otra vez sin renderizar.

El empaquetado se ejecutó localmente y produjo archivos idénticos. Se validó el
YAML del workflow; no se afirma que esta nueva ejecución de Actions ya exista.
No se ha fusionado la rama automáticamente. La demo original y su workflow siguen
conservando sus archivos anteriores, sin sobrescribirlos.

## Límites pendientes

Para el objetivo de voz mexicana neural falta aplicar y comprobar la configuración
de red de Edge, o aportar una narración mexicana propia con `provided`. La alternativa
local actual tiene menor naturalidad. También faltan evaluación auditiva humana en
varios dispositivos, más dirección sonora y alineación de fonemas si se requiere
karaoke más preciso. La aprobación humana de publicación sigue bloqueada por defecto;
ningún modo de narración ni render concede esa aprobación.
