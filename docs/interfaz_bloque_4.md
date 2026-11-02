# Interfaz del bloque 4: análisis visual y revisión de Cocina

Responsable: Jean. Rama: `jean-b4-interfaz-analisis` (parte de `cesar-b4-contratos-motor`).
Fecha de la revisión contra Figma: 02/11/2026.

## 1. Qué se hizo

| Pantalla | Archivo | Marco de Figma | Estado |
|---|---|---|---|
| Lista de pares / Pendientes de Cocina | `templates/analisis/lista.html` | W01 | Hecha |
| Detalle del análisis (en proceso, fallido, completado, no concluyente) | `templates/analisis/detalle.html` | W03, W30, W16, W05 | Hecha |
| Menú de Cocina y encabezado `COCINA / EVA` | `templates/analisis/base.html` | W01, W03 | Hecho |
| Estados legibles y motivos legibles | `_estado.html`, `_motivo.html` | W01, W03, W16 | Hechos |
| Actualización automática mientras el análisis está en curso | `static/js/analisis.js` | W30 | Hecha |
| Estilos | `static/css/analisis.css` (se reutilizan las clases de `eva.css`) | — | Hechos |
| Pruebas de plantilla | `apps/analisis/test_interfaz_lista.py`, `test_interfaz_detalle.py` | — | 21 pruebas de `apps.analisis` en OK |

Las pantallas de revisión (confirmar, rechazar con motivo y estados guardados) **no** se tocaron aquí: dependen de la rama del bloque 5 (`cesar-b5-contratos-interfaz`) y quedan como siguiente paso.

## 2. Reglas que cumplen las pantallas

- Un enlace o botón solo aparece si la vista le entrega su URL (`detalle_url`, `reintentar_url`, `solicitar_url`, `estado_url`, `historial_url`). Si no llega, no se muestra un botón falso: se ve «—» o «Pendiente de conexión».
- Un porcentaje nulo nunca se muestra como 0: se escribe «No concluyente».
- «Sin datos» y «0 casos» son cosas distintas en las tarjetas de resumen.
- Un análisis fallido o con tiempo agotado no muestra ningún porcentaje y no borra resultados anteriores.
- Mientras el análisis está pendiente o en proceso no se muestran cifras.
- Los análisis simulados se marcan «Simulado» y se avisa que no valen para indicadores.
- Se aclara que es una estimación de área y no gramos ni volumen.
- Los estados técnicos (`TIEMPO_AGOTADO`, etc.) no se ven en pantalla; se muestran con texto legible. El motivo no concluyente muestra su texto legible y su código técnico en letra pequeña.

## 3. Datos que usan las plantillas

Del contrato de César (`docs/contrato_bloque_4.md`): `casos` (`plato_nombre`, `porcion_nombre`, `estado`, `origen`, `detalle_url`), `caso` (`plato_nombre`, `porcion_nombre`, `estado`, `origen`, `version_modelo`), `resultados` (`componente`, `porcentaje_texto`, `confianza_texto`, `estado`, `motivo`), `foto_servido_url`, `foto_retorno_url`, `error`, `solicitar_url`, `reintentar_url`.

**Datos opcionales añadidos por esta interfaz y que no están en el contrato.** Sin ellos las pantallas funcionan igual y simplemente omiten esa parte. Hay que confirmarlos con César y Lino:

| Dato | Dónde se usa | Si no llega |
|---|---|---|
| `caso.bandeja_numero` (lista) y en el detalle | columna Registro | «—» |
| `resumen.por_revisar`, `resumen.no_concluyentes` | tarjetas de la lista | «Sin datos» |
| `historial_url` | tarjeta Historial | «Pendiente de conexión» |
| `caso.intento_numero`, `caso.duracion_texto` | detalle | no se muestran |
| `mascaras` (`url`, `componente`, `etapa` = `SERVIDO` o `RETORNO`) | máscaras sobre las fotos | no se dibujan |
| `estado_url` (responde JSON `{"estado": "..."}`) | actualización automática del detalle | se pide recargar la página |

Formato de las máscaras: la plantilla las superpone con 55 % de opacidad. Si el motor las entrega como PNG sin transparencia, hay que ajustarlo con Lino.

## 4. Mapeo con Figma

Archivo: **EVA · Flujos móvil y web** (id `vSVqy8rmaejpEGo0RwXk66`), página **02 · Web · presentación por roles**, marcos de 1440 × 900. Enlace de cada marco: `https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=` + el node-id. Solo lectura: no se modificó nada en Figma. Cada node-id se leyó de la URL tras seleccionar el marco y se comprobó que el nombre coincidiera; los marcos marcados «visto» se abrieron en pantalla.

| Marco | Nombre en Figma | node-id | Pantalla de la app | Visto |
|---|---|---|---|---|
| W01 | Panel de cocina | `400-3` | `analisis/lista.html` | Sí |
| W03 | Detalle de análisis | `400-142` | `analisis/detalle.html` | Sí |
| W05 | Resultado no concluyente | `400-249` | `analisis/detalle.html` (filas no concluyentes) | Sí |
| W30 | Analizando par | `403-489` | `analisis/detalle.html` (pendiente o en proceso) | Sí |
| W16 | Fallo técnico | `400-788` | `analisis/detalle.html` (fallido o tiempo agotado) | Sí |
| W12 | Resultado incorrecto (Motivo del rechazo) | `400-570` | `analisis/revision.html` (rechazo): pendiente, bloque 5 | Sí |
| W41 | Rechazo con motivo | `412-2` | `analisis/revision.html`: pendiente, bloque 5 | Sí |
| W32 | Revisión de Cocina guardada | `403-576` | confirmación guardada: pendiente, bloque 5 | Sí |
| W33 | Rechazo de Cocina guardado | `403-599` | rechazo guardado: pendiente, bloque 5 | Parcial |
| W42 | Cocina · revisión confirmada | `412-41` | «Registros de Cocina» tras confirmar: pendiente (historial) | Sí |
| W43 | Cocina · rechazo guardado | `412-112` | «Registros de Cocina» tras rechazar: pendiente (historial) | Sí |
| W31 | Pendiente de revisión de Cocina (rol Registro) | `403-553` | fuera de la pantalla de Cocina | Sí |
| W13 | Pendiente de retorno (rol Registro) | `400-609` | no corresponde al análisis | Sí |
| W17 | Evidencia insuficiente (Administración) | `400-827` | fuera de este bloque | Sí |

Marcos con ID leído y sin abrir: W39 `403-874`, W44 `417-2`, W18 `400-866`, W35 `403-675`, W45 `418-91`, W46 `418-130`, W47 `418-169`, W49 `422-2`, W50 `422-55`, W51 `422-108`, W52 `422-132`.

**Página móvil (390 × 844): pendiente.** No se pudieron leer node-id verificables de la página «01 · Móvil · presentación por roles»; no se inventan. Hasta entonces, la versión móvil de las pantallas se revisó solo contra la propia app (sin desbordamiento horizontal a 390 px), no contra Figma.

## 5. Comparación con Figma (revisión visual aproximada, no una métrica automática)

Se compararon capturas de la app a 1440 × 900 con el marco de Figma a la misma escala, y la app a 390 × 844 para revisar desbordamientos.

| Pantalla | Parecido por revisión visual | Qué coincide | Qué difiere |
|---|---|---|---|
| Lista (W01) | Cercano, del orden del 70 % | Título, tres tarjetas, tabla con las mismas columnas, barra de etapas, estados con color | Falta el botón «Ver todos los registros», «Inicio» y «Cerrar sesión» en el menú, y la nota de datos de demostración |
| Detalle (W03) | Menor, estimado entre 55 % y 60 %: mismos elementos pero otra disposición | Título, fotos Servido y Retorno, leyenda por componente, estados, textos de aclaración | Figma usa una cuadrícula con tarjetas laterales («Registro e identificación», «Revisión de cocina», «Secuencia de evidencia») y los botones de revisión; la app apila las secciones y usa fotos reales en lugar de la ilustración de ejemplo. Los botones de revisión dependen del bloque 5 |
| Pendiente o en proceso (W30) | Parcial | Aviso azul «Analizando fotografías», sin cifras | Sin mascota, sin tarjeta «ID de bandeja», sin barra de etapas |
| Fallo (W16) | Parcial | Título de fallo técnico, nunca se muestra 0 %, botón Reintentar | Sin las tarjetas «Salida clara» y «Sin resultado analítico», sin «Revisar foto final» |
| No concluyente (W05) | Parcial | Texto «No concluyente», motivo y exclusión de indicadores, dentro de la tabla | No hay pantalla propia con «Siguiente paso» y los botones «Volver a Cocina» y «Volver a registros» |

El objetivo acordado es un parecido aproximado del 70 %. Se cumple solo en la lista; en el detalle queda por debajo, y las diferencias de arriba son la lista de lo que falta para acercarlo.

## 6. Extensiones sin marco en Figma

- Máscaras superpuestas sobre las fotos (W03 solo dibuja una ilustración de ejemplo).
- Duración del intento y número de intento.
- Etiqueta REAL o SIMULADO.
- Aviso «estimación de área, no gramos ni volumen».
- Motivo no concluyente con texto legible y código técnico en letra pequeña.
- Actualización automática del estado cada 3 segundos, con tope de unos 60 segundos.

## 7. Diferencias de Figma con las plantillas de César

| Tema | Figma | Plantilla de César (bloque 5) |
|---|---|---|
| Encabezado | `COCINA / EVA` | `REGISTRO / EVA` por defecto (resuelto en `analisis/base.html`) |
| Botones de decisión | Confirmar revisión, Marcar no concluyente, Marcar incorrecto | Confirmar resultado, Rechazar resultado, Marcar no concluyente |
| Motivo del rechazo | Se elige de una lista (W12: máscara incorrecta, fotografía dudosa, otro) | Texto libre |
| Estados | Texto legible | Códigos en bruto (resuelto en lista y detalle) |

## 8. Pendiente

1. Alinear `revision.html` con W03, W12, W41, W32, W33 cuando la rama del bloque 5 esté integrada.
2. Leer la página móvil de Figma y comparar a 390 × 844 con node-id verificados.
3. Confirmar con César y Lino los datos opcionales de la sección 3.
4. Conectar las pantallas a las vistas reales (Lino) y a los modelos (Isaac). Hoy las plantillas se probaron con datos de prueba.
5. Si se quiere subir el parecido del detalle con W03: reorganizarlo en cuadrícula con las tarjetas laterales.
