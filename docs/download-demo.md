# Descargar el MP4 y la hoja de escenas desde GitHub

Las rutas `/workspace/artifacts/...` pertenecen a la máquina de Codex y no son
URLs de descarga pública. Esta sesión no dispone de una herramienta para adjuntar
archivos al chat. La alternativa es el workflow manual **Descargar demo híbrida**.

## Qué hace

El workflow recupera el MP4 y el JPG **ya renderizados**, guardados en
`examples/hybrid-demo/download-bundle.zip`, y comprueba sus hashes SHA-256 contra
`download-manifest.json`. No vuelve a renderizar, recodificar ni modificar el
contenido audiovisual. Esta copia versionada de unos 2 MB permite recuperarlos
sin depender de que siga existiendo la máquina de Codex.

Solo usa Python estándar y las acciones oficiales de checkout y carga de
artefactos, fijadas a commits. No instala dependencias, llama a Edge/OpenAI/fal.ai,
consulta noticias ni publica en redes. El permiso del repositorio es `contents: read`.
No se ejecuta con push, pull request ni calendario: solo `workflow_dispatch`.
GitHub puede contabilizar minutos y almacenamiento de Actions según el plan del
repositorio; esto no consume APIs de pago de generación audiovisual.

## Dónde hacer clic

1. **Primera vez: incorporar el workflow a `main`.** GitHub requiere que los
   workflows con `workflow_dispatch` estén en la rama predeterminada para mostrar
   la ejecución manual. Si `main` aún no contiene estos cambios, abre:
   https://github.com/jesusrubi-cloud/techslop/compare/main...feat/noticias-internacionales-es
   Pulsa **Create pull request**, revisa los cambios y, cuando decidas integrarlos,
   pulsa **Merge pull request** y **Confirm merge**. El workflow permanece también
   en la rama de desarrollo. No se ha realizado esta integración automáticamente.
2. Abre el repositorio y pulsa la pestaña **Actions**:
   https://github.com/jesusrubi-cloud/techslop/actions
3. En la columna izquierda selecciona **Descargar demo híbrida**. Después de
   incorporar el workflow también puedes abrir directamente:
   https://github.com/jesusrubi-cloud/techslop/actions/workflows/download-hybrid-demo.yml
4. Pulsa **Run workflow**, selecciona `feat/noticias-internacionales-es` en
   **Use workflow from** (o `main` después de integrar), y pulsa el botón verde
   **Run workflow**.
5. Abre la ejecución más reciente y espera a que el job **Preparar MP4 y hoja
   de escenas** termine con una marca verde.
6. En **Summary** de esa ejecución, baja hasta **Artifacts** y pulsa
   **techslop-demo-descargable**. GitHub descargará un ZIP.
7. Descomprime el ZIP. Contiene `techslop-demo.mp4`, `contact-sheet.jpg`,
   `verification.json` y `SHA256SUMS.txt`.
8. Abre el JPG para ver la hoja de escenas. Para reproducir el video en tu
   navegador, arrastra `techslop-demo.mp4` a una ventana de Chrome, Edge o Firefox,
   o usa su opción **Abrir archivo**. GitHub no ofrece reproducción del MP4 dentro
   del ZIP: primero hay que descargarlo y descomprimirlo.

Debes iniciar sesión en GitHub y tener acceso al repositorio. Si Actions muestra
que los workflows están deshabilitados, un administrador debe habilitar GitHub
Actions para este repositorio. Si no aparece **Run workflow**, comprueba que el
archivo ya esté en la rama predeterminada y que tu cuenta tenga permiso de escritura.

El artefacto caduca a los **7 días**. Puedes ejecutar otra vez el mismo workflow
para descargar las mismas copias, sin renderizar. La URL con un ID de ejecución
solo existirá después de una ejecución real; no se ha inventado un enlace a ella.

## Verificación realizada en Codex

Se comprobó la existencia de los dos archivos y se ejecutó localmente el mismo
script de empaquetado que usará Actions. Los bytes recuperados coinciden:

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| techslop-demo.mp4 | 2199801 | `86c7b0b0d78f60494f0bd02b6980d39237d5c1b48eb973649cb387029d7c2d17` |
| contact-sheet.jpg | 262258 | `4da004f6d15fdfe2e34e940a6952ffa88801d0f6c08eebdce29b2ed1fc3ad8c9` |

90 pruebas automatizadas aprobadas; incluye identidad de archivos, rechazo de
archivos alterados y preservación de archivos existentes. YAML comprobado como
válido, con disparador exclusivamente manual y permiso de lectura. Esto **no**
es una ejecución de Actions: la API de GitHub devolvió `Forbidden` en esta sesión.
No se ha abierto ni fusionado un PR automáticamente para instalar el workflow.
