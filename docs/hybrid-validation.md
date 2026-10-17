# Validación del primer MP4 híbrido

Caso ficticio, claramente etiquetado. No se eligió una noticia real: los expedientes
actuales siguen sin corroboración independiente establecida.

- Duración: 60.00 s; 1800 fotogramas.
- Resolución: 1080×1920; 30/1 FPS; H.264 / AAC, yuv420p, faststart.
- Tamaño: 2199801 bytes (2.20 MB decimales).
- Audio: tono de prueba, 60 s; volumen medio -45.5 dB.
- Edge TTS: petición real bloqueada por proxy (`ClientHttpProxyError`) hacia speech.platform.bing.com.
- Sincronización: duración medida por escena; subtítulos del contrato escalados como guías de lectura.
- Render final: 40.53 segundos de ejecución en esta máquina.
- Verificación: decodificación completa con FFmpeg aprobada; duración de audio y video coincidente.
- Inspección visual: cuatro fotogramas extraídos del MP4 final, con textos y advertencias legibles.
- Pruebas automatizadas: 87 aprobadas, incluidas las protecciones de publicación.
- Coste externo de APIs: 0 USD; 0 llamadas a APIs de pago. Cómputo y almacenamiento cloud sin tarifa observable.
- Publicación: ninguna. Se conserva el requisito de aprobación humana explícita.

Artefactos guardados en `/workspace/artifacts/`: `techslop-demo.mp4`,
`contact-sheet.jpg`, `verification.json`. No se subió contenido a un servicio externo.
Los archivos completos de diagnóstico están en `output/hybrid-demo-final/`.
La primera ejecución con el intento real de Edge está en `output/first-hybrid-demo/`.

Las animaciones reutilizables verificadas son introducción con titular animado,
explicación con tarjetas geométricas, gráfico de duraciones medidas y cierre con
referencias. El gráfico solo muestra mediciones de producción, no cifras periodísticas.
Para el estilo definitivo faltan voz accesible, mezcla sonora, ilustraciones de
más detalle, dirección de arte y datos y recursos de noticias corroborados.
