# Observaciones y dependencias — 04/11/2026

Actualización de auditoría: se reprodujeron localmente QA-INC-02/03 y se
documentaron QA-INC-04 a QA-INC-08. Ver [inventario, causas y pasos de
reproducción](hallazgos_validaciones.md) y la evidencia JSON enlazada allí.
Las entradas originales siguientes conservan qué se sabía al reportarlas;
la reproducción posterior es local y no confirma por sí sola el despliegue AWS.

## QA-INC-03 — búsqueda vacía recarga sin mensaje de validación

Estado: REPORTADO POR EDUARDO, pendiente de reproducción técnica y corrección.
Prioridad: P2 provisional (validación y recuperación del formulario).
Casos relacionados: L02 y J04; relacionado con QA-INC-02.
Área propuesta: captura/HTTP (Lino), interfaz (Jean).

Entorno reportado: demo HTTPS, sesión de Registro, pantalla «Identificar bandeja».
Fecha de registro: 04/11/2026; hora exacta, navegador/versión, dispositivo y commit
desplegado del incidente no confirmados.

Pasos reportados:

1. Abrir la búsqueda de bandeja pendiente de retorno.
2. Dejar vacío el campo «Número de bandeja».
3. Pulsar «Buscar registro».

Esperado: validación visible y asociada al campo, por ejemplo «Introduce el número
de bandeja o escanea su etiqueta». Conservar una pantalla usable y no ejecutar una
búsqueda de dominio con un identificador vacío. Validar también en servidor;
la validación del navegador por sí sola no basta.

Observado por Eduardo: la página recarga sin mostrar un mensaje que indique que
falta el número. No se adjuntó todavía captura posterior, registro de red ni
respuesta HTTP. Una recarga no demuestra por sí sola que haya habido consulta
a la base de datos; ese efecto sigue sin verificar.

Variante reportada posteriormente por Eduardo: al introducir únicamente espacios
y pulsar «Buscar registro», también permite continuar con la búsqueda aparente.
No se confirmó si la respuesta posterior es recarga o error genérico. Se espera
normalizar espacios y tratar ese valor como vacío, mostrando la misma validación.
Esta variante está reportada por el usuario, no reproducida por herramientas.

Control adicional reportado por Eduardo: al introducir `abc`, sí aparece un
mensaje indicando que el campo solo puede contener dígitos. Resultado de esta
variante: APROBADO según observación del usuario, pendiente de evidencia técnica.
Esto limita el hallazgo a vacío/solo espacios; no implica ausencia general de
validación del campo ni resuelve el error genérico para números no reconocidos.

Impacto: el usuario no recibe explicación ni indicación de cómo continuar.
No se ha observado creación de registros, pérdida de datos ni caída del servicio.

Repetición técnica pendiente: vacío y solo espacios; comprobar mensaje, foco y estado del
campo, comportamiento del servidor y ausencia de cambios. Probar después un
número válido coordinado. No marcar este hallazgo como reproducido por herramientas
hasta ejecutar y conservar esa evidencia.
PR de corrección: ninguno. Resultado tras corrección: pendiente.

## QA-INC-02 — búsqueda con número no reconocido muestra error genérico

Estado: REPORTADO POR EDUARDO, pendiente de reproducción técnica y corrección.
Prioridad: P2 provisional (validación/mensaje de recuperación).
Caso relacionado: L02; revisión visual J04. Área propuesta: captura/HTTP (Lino).

Entorno reportado: demo HTTPS, sesión `registro_demo`, pantalla «Identificar
bandeja», botón «Buscar registro». Fecha de registro: 04/11/2026; hora exacta,
navegador/versión, dispositivo y commit desplegado del incidente no confirmados.

Pasos reportados:

1. Iniciar sesión como Registro y abrir la pantalla de identificación.
2. Escribir el número arbitrario `2322`.
3. Pulsar «Buscar registro».

Esperado: si no existe la bandeja o no tiene un servicio pendiente de retorno,
mostrar un mensaje comprensible, conservar el dato y permitir corregirlo o volver
a buscar. No crear servicios ni asociaciones a partir de un número arbitrario.

Observado por Eduardo: navegación a una página genérica en blanco con los textos
«Not Found» y «The requested resource was not found on this server.».
La captura compartida muestra la pantalla y el número antes del envío; el mensaje
posterior se conserva como transcripción del usuario. No se dispone aún de captura
del error, ruta de destino sanitizada ni código HTTP confirmado por herramientas.
No se ha comprobado si `2322` existe o tiene una asignación pendiente.

Impacto: no se explica el motivo ni cómo recuperarse desde esa respuesta.
La denegación de un número desconocido puede ser correcta; el hallazgo reportado
es su presentación genérica. No hay evidencia de pérdida o mezcla de datos.

Repetición pendiente: número desconocido, campo vacío y bandeja existente sin/con
servicio pendiente. Confirmar ruta exacta y respuesta, sin publicar tokens de QR o
vínculos temporales. No sustituye el recorrido con una bandeja libre coordinada.
PR de corrección: ninguno. Resultado tras corrección: pendiente.

Esta entrada amplía el reporte original del PR #61. No modifica sus resultados
automáticos ni atribuye esta ejecución a la matriz propia de Lino.

## QA-OBS-01 — cabecera de caché en histórico/captura

Estado: EN INVESTIGACIÓN. Prioridad P2 provisional de endurecimiento; subir a P0
y detener el recorrido si se demuestra acceso a evidencia sin autorización.
Responsables propuestos para investigar: Eduardo y Lino (HTTP/privacidad).

Base `7615a24`, Chrome 157, demo HTTPS. Como Cocina o Administración, GET
`/historico/` responde 200 sin cabecera Cache-Control; como Registro ocurre lo
mismo en `/captura/bandeja/`. Recomendaciones sí devuelve no-store.
Evidencia: registros `E04/E25` de `navegador_resultados.json`; en la base local
las vistas de histórico no tienen decorador `never_cache`.

Esperado para cerrar E08: fotos/máscaras protegidas y ausencia de contenido
privado recuperable al volver atrás tras logout. Observado: navegar de nuevo al
histórico después de logout exige login; no se ha demostrado un bypass de sesión.
La falta de cabecera por sí sola no prueba una fuga ni permite marcar E08 aprobado.

Reproducción pendiente: con servicio QA propio y evidencia privada, abrir el
detalle/foto/máscara; logout; atrás/adelante/recarga e incógnito en los navegadores
reales. Registrar sin publicar URLs firmadas, tokens, cookies o fotos privadas.
Si requiere corrección, preparar PR separado y repetir el caso en su commit.
PR de corrección: ninguno. Repetición tras corrección: pendiente.

## QA-BLOQ-01 — recorridos físicos propios

E08 y X01–X04 completos: falta reserva coordinada de bandejas libres y pares
propios preparados de los tres platos; QR físico y teléfono real para X02.
El recorrido X04 tiene comprobación parcial de lectura/demo/logout, pero aún
no queda enlazado a un lote propio completo. No se altera la demo para forzarlo.

## QA-BLOQ-02 — revisión cruzada y cierre del equipo

No se recibieron matrices de esta ronda de Isaac, Lino y Jean. Pedir sus casos
principales, sus cuatro X propios, revisión cruzada, dispositivos e incidencias.
Eduardo consolida; no se asigna a César ejecutar o consolidar QA.

## QA-BLOQ-03 — controles privados y operación

Diez pruebas ONNX omitidas por runtime ausente; tres de paridad omitidas por
paquete privado ausente. Lino/Isaac deben adjuntar resultado propio del entorno
preparado y evidencia operativa autorizada. No instalar paquetes ni crear AWS.

## QA-BLOQ-04 — cobertura visual pendiente

Faltan marcos verificados de Figma, teléfono Android real, teclado/zoom y menú
móvil; las capturas emuladas solo cubren una parte de J02. No atribuir a Jean
revisión independiente hasta recibir su confirmación y evidencias.
