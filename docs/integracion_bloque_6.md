# Integración del bloque 6

Combina base #42 (b217b6e), dominio #44 (6b79011) e interfaz #43
(2d68b925278b0057cd42b976aef6e9c2cc3309c2), conservando su historial.

Se registra /historico/ en las rutas globales, se añaden enlaces de histórico y
comparación a la navegación por roles y se conecta percepción opcional desde la
confirmación/estado del servicio. No se amplían los permisos de Registro a la
consulta analítica. La percepción sigue sin bloquear el recorrido de captura.

Verificación conjunta: 410 pruebas Django aprobadas, 39 JavaScript aprobadas,
comprobaciones sin incidencias y makemigrations --check --dry-run sin cambios.
Incluye los recorridos ORM de la interfaz y dos pruebas de la conexión global.
La primera ejecución detectó que la rama de interfaz aún no contenía el dominio;
se incorporó explícitamente antes de repetir la suite. No se omitieron tests.

Para activar en un entorno operativo se requiere respaldo y despliegue separado,
migrate y collectstatic, además del ensayo de roles y recorrido. Esta integración
no despliega AWS ni migra su base. No se ejecutó migrate sobre la base local operativa.

La comparación con Figma continúa pendiente de acceso/exportaciones. El valor de t
sigue sin aprobarse y no se fabrica contexto histórico: el sistema muestra los
avisos y valores no disponibles definidos en el contrato. Las pruebas con fixtures
no acreditan calidad de IA ni validación en un restaurante real.
