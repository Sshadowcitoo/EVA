# Observaciones y dependencias — 04/11/2026

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
