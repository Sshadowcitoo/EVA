# Preparar la interfaz de recomendaciones

Los PR del bloque 6 ya están integrados en main mediante #45. Actualizar la copia
propia sin perder cambios locales. Base de partida del bloque 7:

```powershell
git fetch origin
git switch -c interfaz-recomendaciones-bloque-7 origin/base-recomendaciones-bloque-7
```

Repositorio https://github.com/Sshadowcitoo/EVA. Base main
fb1e0684e48c80efbf97d4edf5aed90a9412cbfe. El commit de esta entrega se indica en su PR.
Trabajar en una copia propia; no cambiar la rama de otro trabajo activo.

## Leer primero

1. docs/contrato_bloque_7.md y apps/recomendaciones/contracts.py: nombres definitivos v1.
2. services.py, filtros.py y testing/fixtures.py del mismo módulo.
3. docs/figma_referencia.md, estilos existentes y contratos de histórico/revisión.
4. README y AGENTS.md si está disponible. Reutilizar el entorno y dependencias del proyecto.

## Implementar

Formularios, vistas y URLs del módulo, plantillas, CSS/JS y pruebas HTTP/interfaz.
Pantallas: lista/filtros, evaluar evidencia, detalle suficiente/insuficiente,
recomendación con evidencia y vigencia, tres decisiones e historial, registro de
prueba desde aceptación y detalle/comparación o no evaluable. Cocina consulta;
Administración además evalúa/genera/decide/registra pruebas. Registro no hereda acceso.

No crear modelos/migraciones, reglas de suficiencia ni otra fórmula de indicadores.
No cambiar contracts.py ni los archivos de otros bloques unilateralmente. No dar
por resueltos los parámetros de muestra/persistencia/calidad/confianza/contexto
porque existan fixtures. Presentar valores del DTO, sin inventar causales o números.

Las operaciones de datos de services.py todavía devuelven BackendRecomendacionesNoDisponible.
Implementar el 503 legible. En tests sustituir cada servicio explícitamente con las
fixtures; en producción no usar fallback. Cuando el dominio esté publicado, actualizar
la dependencia y probar la conexión sin reemplazar las funciones.

El formulario puede mantener las decisiones en el detalle, con confirmación y
errores claros. Cada POST lleva CSRF y los IDs/versiones indicados. Usar las
capacidades del backend para mostrar acciones; la autorización real sigue en servidor.
No modificar catálogo ni porciones al aceptar, ni guardar estados de revisión de
Cocina como si fueran decisiones de recomendación.

## Figma y verificación

Archivo: https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA
Acceso solo lectura. Si no hay acceso funcional, pedir exportaciones; documentar
el bloqueo sin afirmar comparación terminada ni inventar node-id. Objetivo visual
acordado: aproximadamente 70 %, con revisión en 1440x900 y 390x844.

Ejecutar check, tests de apps.recomendaciones, migraciones sin cambios inesperados
y los tests JavaScript propios. Probar todos los estados, roles, CSRF, campos
conservados/escapados y pérdida de vigencia. No certificar conexión con el dominio
solo con mocks, ni IA real con estas muestras.

## Entrega

Rama interfaz-recomendaciones-bloque-7; PR contra base-recomendaciones-bloque-7 si
la base sigue abierta, o main una vez integrada y actualizada la rama. No hacer
merge ni desplegar. Entregar archivos, firmas consumidas, commit/base, resultados
reales de comandos, capturas, nodos verificados y pendientes. Usar títulos/commits
descriptivos de los cambios, sin atribuciones a asistentes ni numeraciones personales.

Anotar en docs/entrega_web_bloque_7.md el include global y enlaces de navegación
requeridos; la integración compartida se hace aparte. No mezclar este PR con
correcciones pendientes de Figma del bloque 6.
