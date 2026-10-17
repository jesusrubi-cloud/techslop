# Prueba manual y acotada de ElevenLabs

La integración está aislada en `scripts/elevenlabs_manual_test.py` y el workflow
**Prueba manual ElevenLabs (máximo 15 s)**. No se activa ElevenLabs en `auto`,
`render-editorial`, la captación ni los workflows de descarga existentes.

El workflow referencia `${{ secrets.ELEVENLABS_API_KEY }}` únicamente en el paso
que ejecuta la prueba. No lee, imprime ni incorpora su valor a archivos o artefactos.
La presencia y validez de la clave solo se comprobarán cuando el propietario
active el workflow. Esta preparación no verificó la clave contra el proveedor,
no ejecutó Actions ni envió peticiones reales a ElevenLabs.

## Límites por ejecución

- Disparador exclusivo `workflow_dispatch`, sin push, calendario ni pull request.
- Autorización manual `authorize_one_request`, desactivada por defecto.
- Texto fijo de **63 caracteres**, no editable en el formulario; barrera de 80 caracteres.
- Una consulta de metadatos de voz y **como máximo un POST de generación**.
- Modelo fijo `eleven_flash_v2_5`, idioma `es`, formato MP3 44,1 kHz / 128 kbit/s.
- Sin reintentos, cambios de modelo, voces alternativas ni solicitudes de respaldo.
- Marcador local de intento: volver a ejecutar sobre la misma carpeta falla antes de pedir audio.
- Sin redirecciones, URL de API fija y tiempo de espera de 45 s por solicitud.
- Respuesta de audio limitada a 2 MB y trabajo de Actions limitado a cuatro minutos.
- MP3 final de **máximo 15 segundos**, validado con ffprobe y decodificado completamente.
- Artefactos: solo MP3 e informe sin secretos; conservación de siete días.

La API de síntesis no ofrece aquí una garantía dura de duración. Un texto tan corto
se prepara para una narración breve, pero la garantía de ≤15 s del archivo descargado
se impone localmente: se recorta a 14,8 s para dejar margen al padding MP3 y se valida
la duración final. Ese recorte no reduce los créditos ya consumidos por el proveedor.

**El límite estricto implementado es por solicitud y caracteres, no por dólares ni
por cuenta.** El precio depende de la tarifa, voz y plan vigentes. Si necesitas un
techo monetario/de créditos global, configura también la cuota de la clave en
ElevenLabs antes de activar la prueba. Cada activación o reejecución manual nueva
puede consumir créditos otra vez; la concurrencia solo evita solapamientos. Un
error de red después del POST no demuestra que no se haya cobrado: no se reintenta.

## Voz mexicana

El formulario requiere el `voice_id` de una voz a la que tu cuenta ya tenga acceso.
Selecciona una voz en español mexicano en ElevenLabs y copia su ID. No se inventó
un ID ni se eligió una voz genérica. Antes de generar se consulta `/v1/voices/{id}`
y se exige una etiqueta de acento mexicano (`Mexican`, `Mexicano`, `México` o
variantes explícitas) y, si existe, una etiqueta de idioma español. Si el acento
no está etiquetado, la prueba se detiene **antes del POST**. No utiliza otra voz
para completar la ejecución.

`language_code=es` selecciona español; el acento lo aporta la voz. La etiqueta del
proveedor es un filtro previo, no una evaluación auditiva independiente. La revisión
humana del resultado sigue siendo necesaria. La clave debe permitir leer metadatos
de esa voz y generar TTS; un 401/403 detiene la ejecución sin reintentos ni revelar
la respuesta del proveedor.

## Activar y descargar cuando decidas autorizar el consumo

1. Revisa e integra `.github/workflows/elevenlabs-manual-test.yml` en la rama
   predeterminada (`main`) para que GitHub muestre el workflow manual.
2. Abre **Actions → Prueba manual ElevenLabs (máximo 15 s) → Run workflow**.
3. Elige la rama con estos cambios, introduce el `voice_id` mexicano y marca
   **Autorizo UNA generación, máximo 80 caracteres; puede consumir créditos**
   únicamente cuando decidas ejecutar la prueba. Sin esa marca el job se omite.
4. Pulsa el botón verde **Run workflow**. Esta es la acción que autoriza la solicitud;
   preparar el código o guardar el secreto no la ejecuta.
5. Tras finalizar, abre la ejecución y baja a **Summary → Artifacts**.
6. Descarga **elevenlabs-es-mx-prueba-15s**, descomprime el ZIP y abre
   `elevenlabs-es-mx-test.mp3`. `report.json` contiene duración, caracteres y modelo,
   pero no la clave. No se publica ningún video ni audio en redes sociales.

## Validación sin llamadas al proveedor

Las pruebas simulan HTTP, incluido el fallo de generación, el rechazo de una voz
sin acento mexicano, ausencia de secreto, redirecciones, exceso de caracteres y
preservación del marcador de intento. Para verificar el tope del MP3, se utiliza
un seno local de 16 segundos como respuesta simulada; **no es narración ni audio
obtenido de ElevenLabs**. Ninguna prueba automatizada usa la clave real.

```sh
uv run --frozen pytest tests/test_elevenlabs_manual.py -q
```

La clase de ElevenLabs del flujo legado sigue bloqueada deliberadamente: una
selección accidental de `TTS_PROVIDER=elevenlabs` no debe eludir el workflow manual.
