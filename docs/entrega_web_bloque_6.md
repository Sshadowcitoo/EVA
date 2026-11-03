# Entrega web del bloque 6

Rama: interfaz-historico-bloque-6. Base exacta:
`b217b6e92dea596b14b45ca2ce25797b291437d0`.
PR dependiente de base-historico-bloque-6 mientras esta no esté integrada.
Estado funcional: interfaz preparada; BACKEND_PENDIENTE en esta base.

## Archivos

- apps/historico/forms.py, views.py y urls.py.
- templates/historico/: base, lista, comparar, percepcion y cuatro parciales.
- static/css/historico.css y static/js/historico.js.
- apps/historico/test_web_interfaz.py y tests/frontend/historico.test.cjs.
- docs/interfaz_bloque_6.md y este documento.

Se consumen las seis funciones públicas del contrato, sin modificar contracts.py,
filtros.py, services.py, modelos, migraciones, settings, URLs globales, captura,
análisis, roles ni navegación compartida. Fixtures importadas exclusivamente por
los tests. No se cambia el bloque 7.

## Integración que falta aplicar

1. Incluir path('historico/', include('apps.historico.urls')) en config/urls.py.
2. Sustituir enlaces pendientes del histórico/indicadores en la navegación común
   por historico:lista solo para Cocina/Administración; añadir historico:comparar.
3. En detalle/confirmación del servicio accesible a Registro, añadir enlace a
   historico:percepcion con su UUID. El formulario opcional puede abrirse en página
   independiente sin interrumpir captura. Para incrustarlo, usar el parcial
   historico/_percepcion_form.html, proporcionando servicio_id, PercepcionForm
   inicializado con obtener_percepcion y bloqueado si el servicio no está disponible.
   No copiar la persistencia al endpoint de captura ni anidar formularios HTML.
4. Implementar las cinco funciones de services aún pendientes y comprobar el flujo
   conectado con roles reales y SQLite de prueba antes de desplegar.

No se realiza merge ni despliegue en esta entrega.

## Verificación ejecutada

Entorno virtual aislado, Python 3.12, Django 5.2.19 y dependencias declaradas.
Base SQLite local; las pruebas usan la base temporal de Django.

| Comando | Resultado |
| --- | --- |
| python manage.py check | Sin incidencias |
| python manage.py test apps.historico | 32 pruebas aprobadas: 10 base y 22 web |
| python manage.py test | 373 pruebas aprobadas |
| python manage.py makemigrations --check --dry-run | No changes detected |
| node --test tests/frontend/historico.test.cjs | 3 pruebas aprobadas |
| node --test tests/frontend/*.test.cjs | 39 pruebas aprobadas |

Cobertura web: roles aislados/múltiples/staff/superusuario/inactivo/anónimo,
CSRF real con Client(enforce_csrf_checks=True), métodos, límites temporales,
filtros inválidos/origen simulado, conservación de campos, opciones históricas,
paginación y totales del backend, ceros/None, múltiples grupos, datos escapados,
comparación sin observaciones e incompatible, conflictos, errores del dominio y guardado PRG.
No se acredita idempotencia persistida con mocks: eso pertenece al dominio.

Los ensayos de pantalla sustituyen explícitamente services mediante fixtures en
un proceso de prueba aislado. No introducen un proveedor sintético productivo.
Los nodos Figma y el flujo con persistencia real permanecen pendientes.


## Evidencia visual del ensayo

Se renderizaron las vistas Django con RequestFactory y dobles explícitos de
services en un proceso de prueba. Chromium revisó 20 combinaciones: diez estados
por dos tamaños, 1440x900 y 390x844. No se detectó desbordamiento horizontal de la
página; la tabla conserva su desplazamiento horizontal local accesible por teclado.
Se inspeccionaron las capturas de histórico, comparación, percepción, backend
pendiente y conflicto. No equivalen a un flujo con persistencia ni a validación Figma.

Capturas de ejemplo (contenido sintético):

| Pantalla | Escritorio | Móvil |
| --- | --- | --- |
| Histórico | [1440x900](evidencias/bloque_6/historico-1440.jpg) | [390x844](evidencias/bloque_6/historico-390.jpg) |
| Comparación | [1440x900](evidencias/bloque_6/comparacion-1440.jpg) | [390x844](evidencias/bloque_6/comparacion-390.jpg) |
| Percepción | [1440x900](evidencias/bloque_6/percepcion-1440.jpg) | [390x844](evidencias/bloque_6/percepcion-390.jpg) |
| Backend pendiente | [1440x900](evidencias/bloque_6/pendiente-1440.jpg) | [390x844](evidencias/bloque_6/pendiente-390.jpg) |
| Conflicto sin sobrescritura | [1440x900](evidencias/bloque_6/conflicto-1440.jpg) | [390x844](evidencias/bloque_6/conflicto-390.jpg) |

Los tamaños indicados son los viewports del navegador; las capturas incluyen
la página completa y por ello pueden tener más altura.
