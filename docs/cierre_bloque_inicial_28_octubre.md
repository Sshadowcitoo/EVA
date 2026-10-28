# Revisión del bloque inicial — 28 de octubre de 2026

Base revisada: `origin/main`, commit `8f685bf`, integrado por César mediante PR #13.
Se creó un worktree con HEAD separado para revisar sin modificar la rama anterior de Eduardo ni realizar merges. Posteriormente se creó allí `eduardo-pruebas-bloque-2` para documentación y preparación del siguiente bloque.

## Evidencia ejecutada

Se utilizó el Python del entorno existente desde `.revision-integrada`, sin instalar dependencias ni ejecutar migraciones sobre la base local del usuario.

| Comando | Resultado real |
|---|---|
| `..\.venv\Scripts\python.exe -B manage.py check` | Sin problemas detectados |
| `..\.venv\Scripts\python.exe -B manage.py test apps.catalogo apps.captura --verbosity 1` | 56 pruebas aprobadas en 29.464 s; base temporal creada y eliminada |
| `..\.venv\Scripts\python.exe -B manage.py makemigrations --check --dry-run` | `No changes detected` |

## Pendientes anteriores resueltos por integración

- `apps/catalogo/test_integration.py` prueba las vistas reales: sesiones por rol, errores, next, logout con CSRF, gestión del catálogo y denegaciones.
- `apps/captura/tests.py` ya utiliza sesión y catálogo, comprueba creador/composición, elementos inactivos y confirmaciones ajenas.
- La confirmación existente filtra por `creado_por=request.user`; otra cuenta de Registro y registros históricos sin creador reciben 404.
- La suite conserva las pruebas anteriores de contrato aislado, modelos, permisos y migración histórica. La planificación del 26 de octubre no debe leerse como estado actual.

No se certifica que cada escenario imaginable esté cubierto. Sigue siendo útil ampliar casos de carrera, errores y concurrencia según los endpoints nuevos. No se duplicarán casos integrados solo para aumentar el número de pruebas.

## Revisión de interfaz

Se inspeccionaron plantillas y CSS: viewport, labels, tokens CSRF, mensajes de error, navegación condicionada por roles, foco y media queries presentes. Esta inspección estática no acredita el resultado renderizado, interacción por teclado, ausencia de overflow o fidelidad visual a Figma.

No hay herramienta de navegador automatizado disponible ni Playwright instalado en el entorno revisado. No se instalaron dependencias nuevas para obtener capturas. No se tuvo acceso al diseño editable de Figma durante esta revisión. Por ello no se inventan evidencias visuales ni se declara cierre visual.

Lista de aceptación manual pendiente, con cuentas operativas y datos demo:

| Evidencia | Comprobación | Estado |
|---|---|---|
| Login, 390×844 y 1440×900 | Campos legibles, error de credenciales y sin desplazamiento horizontal | Pendiente |
| Registro, ambos tamaños | Opciones activas, error visible, selección conservada, alta y confirmación | Pendiente |
| Administración, ambos tamaños | Listar, crear, editar/desactivar y errores; menú móvil expandible | Pendiente |
| Roles | Denegación comprensible y navegación sin acciones no autorizadas | Pendiente visual; HTTP aprobado |
| Teclado | Foco visible, labels, orden de tabulación y botones accesibles | Pendiente |
| Figma | Comparación con marco/nodo de referencia al mismo tamaño | Pendiente de acceso/referencia |

Guardar capturas sin contraseñas ni datos personales, anotando commit, rol, tamaño de viewport, pasos y resultado. Si falla un caso, registrar el fallo y repetir después de corregirlo; no marcarlo aprobado por la existencia de una regla CSS.

## Siguiente bloque

La rama nueva se basa en main integrado. El plan de bloque 2 está en `docs/pruebas_bloque_2.md`. César publicó contratos separados para bloques 2 y 3; no se hizo merge de esas ramas ni se afirma que sus funciones ya existan.
