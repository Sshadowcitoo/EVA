# Continuación práctica

## Eduardo: siguiente sesión de pruebas

1. Coordinar una bandeja libre real por recorrido; no asumir que la 1 está libre.
   Usar lote `QA-EDUARDO-20261104-N` o la fecha real de ejecución. Anotar IDs y hora
   Ecuador sin publicar el token del vínculo temporal.
2. Preparar servido y retorno de encebollado, seco y arroz/menestra/carne.
   Usar cuentas de un solo rol indicadas en la guía; no usar superusuario.
3. Ejecutar X01, X02 y X03 según la guía, conservando el mismo ID por cada par.
   X02 necesita PC y teléfono por HTTPS; X03 incluye reemplazo de etiqueta con
   motivo por Administración. Coordinar antes de modificar datos compartidos.
4. Ejecutar X04 sobre el lote propio: histórico/evaluación, cuatro demos y logout.
   No convertir SIMULADO a REAL ni aprobar criterios para obtener un porcentaje.
5. Completar E08: foto/máscara propia con sesión, sin sesión, incógnito y atrás
   después de logout. Ante acceso indebido detener el flujo y reportar P0.
6. Repetir navegación, menú móvil, errores, Tab/Enter y zoom 200 % para revisar
   J01/J02/J04/J05/J08 de Jean; contrastar sus capturas con los marcos de Figma.
7. Sustituir cada BLOQUEADO solo con evidencia de ejecución; anotar revisor y
   resultado de repetición. No compartir credenciales en CSV ni imágenes.

## Pedir al equipo

Isaac: I01–I16, X01–X04 propios y revisión crítica de Lino.
Lino: L01–L23, X01–X04 propios y revisión crítica de Isaac.
Jean: J01–J08, X01–X04 propios y revisión crítica de Eduardo.

Mensaje sugerido:

> Ya ejecuté la suite de la base 7615a24 y las comprobaciones remotas de lectura
> y permisos. Tengo la consolidación provisional de QA del 04/11. Pásenme sus
> matrices por ID, evidencias propias de X01–X04, navegador/dispositivo,
> incidencias y revisión cruzada. Faltan mis recorridos físicos y E08; todavía
> no corresponde declarar APTO PARA DEMO.

## Comandos locales para repetir

Desde `C:\Users\robin\EVA\.qa-04-noviembre`, usando el entorno existente:

```powershell
..\.venv\Scripts\python.exe -B manage.py check
..\.venv\Scripts\python.exe -B manage.py test apps.recomendaciones.test_qa_integral_eduardo --verbosity 2 --noinput
node --test tests/frontend/*.test.cjs
git diff --check
```

`check` verifica configuración; `test` crea una base temporal y prueba las nuevas
regresiones; Node prueba interfaz sin cámara; `diff --check` detecta problemas de
formato. Usarlos tras cambios pertinentes; no hace falta repetir toda la suite
sin cambios nuevos. Para repetir toda la base: `manage.py test --noinput`.

El script `ops/qa/navegador_lectura.cjs` requiere Chrome ya abierto con perfil QA
temporal y depuración local, y JSON por stdin con `accounts` y `output`. No es
necesario ejecutarlo para continuar manualmente. No guardar ese JSON con claves
en archivos ni historial. El script usa CDP nativo, sin paquetes adicionales.

## Entrega

Publicar esta rama mediante PR, con título «Registra QA integral del 4 de noviembre
y dependencias de cierre», base `main`. Mantener explícito NO APTO por evidencia
pendiente y enlazar `docs/qa_20261104/reporte_eduardo.md`. No pulsar Merge.
