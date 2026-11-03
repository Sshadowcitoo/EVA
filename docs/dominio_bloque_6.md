# Histórico e indicadores: dominio del bloque 6

Rama: `dominio-historico-bloque-6`, basada en `base-historico-bloque-6` (PR #42).
Las seis firmas públicas y todos los DTO del contrato v1 se conservan. No se
modificaron formularios, rutas, plantillas, CSS/JS ni los archivos de la entrega web.
Las fixtures de interfaz siguen disponibles exclusivamente para pruebas.

## Consulta y elegibilidad

Los selectores leen Servicio y su composición histórica, el análisis más reciente,
el intento vigente y su revisión vigente. No leen archivos ni usan el catálogo
actual para reconstruir nombres o porciones. Las opciones incluyen códigos usados
históricamente aunque estén desactivados. Códigos desconocidos o combinaciones no
registradas producen FiltrosInvalidos, no un conjunto vacío engañoso.

La elegibilidad usa evaluar_elegibilidad del bloque 5 y añade integridad de la
composición, pertenencia del par, protocolo/checklist y valores numéricos coherentes.
Todos los componentes deben ser válidos, aunque el filtro seleccione solo uno.
Un intento nuevo no hereda aprobación. Un rechazo posterior se refleja al consultar.
El vencimiento de bytes no elimina una revisión histórica válida ni exige acceso
a S3 para recuperar indicadores. No se reevalúa la confianza con parámetros actuales:
se usa configuracion_aprobada/umbral_aplicado persistidos en cada resultado.

Motivos principales, en orden: ANULADO, SIN_FECHA_SERVIDO, PAR_INCOMPLETO,
SIN_ANALISIS, INTENTO_NO_COMPLETADO, SIN_REVISION, RECHAZADO/NO_CONCLUYENTE/
REVISION_NO_CONFIRMADA, COMPONENTES_INVALIDOS y CRITERIOS_INVALIDOS.
SIMULADO se omite del alcance, no se mezcla con REAL ni con sus contadores.

Los resúmenes cuentan servicios únicos. Las filas y grupos pueden tener varios
componentes de un servicio, sin multiplicar candidatos/exclusiones. El agregado
siempre usa la muestra completa filtrada; solo las filas se paginan (30 por página).
Las lecturas se agrupan en transacciones y prefetch para evitar una consulta por fila.
Los selectores cargan en memoria el alcance filtrado; es apropiado para el piloto,
pero una explotación masiva requeriría medir y optimizar esa agregación.

## Tiempo y cálculo

Fecha del servido exacto del análisis, o primera foto SERVIDO si no hay análisis.
No se sustituye por fecha_creacion. Rango temporal local de Ecuador [inicio,fin),
con fin al día posterior a hasta; horas también con límite final exclusivo.
Servicios sin fecha no se asignan artificialmente a un periodo: se informa su
cantidad como advertencia cuando se aplica filtro temporal.

Por grupo, prevalencia = 100 * cantidad con porcentaje > t / n e intensidad =
promedio de porcentajes, incluyendo ceros confirmados. Sin n se devuelve None.
EVA_HISTORICO_CRITERIOS separa presencia de sobrante de la confianza del modelo:

```python
EVA_HISTORICO_CRITERIOS = {"version": None, "aprobada": False, "presencia_t": None}
```

Solo se acepta t finito en 0..100 con versión no vacía y aprobación explícita.
Sin t, la prevalencia es None/SIN_CRITERIO_PRESENCIA; la intensidad descriptiva
puede existir si hay registros aptos. Los tests usan t=20 como fixture, no como
criterio aprobado para la operación. Esta entrega no cambia umbrales de IA.

Se separan plato, componente, porción, modelo, configuración y protocolo. Si hay
varios grupos, la cabecera no los promedia. Cada grupo conserva su propia muestra.

## Comparación y límite conocido

Se validan fechas completas, periodos no superpuestos y filtros equivalentes.
Las diferencias son comparado - referencia, en puntos porcentuales, nunca cambio
relativo ni prueba causal. Si falta un criterio, la diferencia afectada queda None.

Servicio todavía no tiene contexto histórico persistido: contexto_clave=None,
comparable=False y SIN_CONTEXTO_HISTORICO. Se muestran métricas descriptivas por
grupo, pero NO diferencias entre periodos suponiendo un contexto inexistente.
Los tests positivos de la aritmética de comparación usan DTO sintéticos con contexto
conocido; no acreditan una captura de contexto que aún no existe. Completarla será
una decisión de datos separada, sin reconstruirla retrospectivamente del catálogo.

## Percepción y auditoría

La migración 0001_percepcion_versionada crea PercepcionServicio: servicio, categoría,
motivo, autor, fecha, versión, vigencia y referencia al registro sustituido. No añade
identidad del comensal. Sin respuesta inicial devuelve NO_INFORMADO/version=0 y no
crea una fila al consultar. Las correcciones son nuevos registros, conservan los
anteriores y solo uno queda vigente. No hay permisos genéricos de edición/borrado.

La operación exige Registro activo (o la excepción de superusuario ya existente).
No restringe al creador del servicio; is_staff o Administración solos no autorizan.
Servicio anulado/inexistente produce ServicioNoDisponible. Categoría/motivo/versión
se validan también en servidor. Un reenvío idéntico del mismo operador es idempotente;
una versión antigua o bloqueo concurrente produce ConflictoPercepcion, sin sobrescribir.
Restricciones de base garantizan versión única, categoría válida y una sola vigencia.

El motivo declarado admite hasta 1000 caracteres; NO_INFORMADO exige motivo vacío.
No se usa esa opinión para modificar resultados o porcentajes. La interfaz conserva
su obligación de advertir que no se escriban datos personales y de aplicar CSRF.

## Conexión con la interfaz y despliegue

La interfaz sigue consumiendo `from apps.historico import services`. No necesita
conocer el modelo nuevo ni importar selectores. Al combinar localmente ambas ramas,
aplicar `python manage.py migrate` en la base de desarrollo correspondiente y ejecutar
sus pruebas web junto con las de dominio. El include global y navegación se integran
cuando esté disponible esa entrega; todavía no se añadieron rutas ficticias a main.

Verificación: 383 pruebas Django aprobadas en la entrega de dominio (42 del módulo),
check sin incidencias, makemigrations --check --dry-run sin cambios y diff limpio.
Las pruebas cubren fórmulas, selección, horarios, exclusiones, cambios de catálogo,
retención, paginación, separación de versiones, integridad, roles, idempotencia,
rollback y restricciones de base. También se ejercitan dos operadores simultáneos
con conexiones SQLite reales. Si ambos obtienen bloqueo temporal, ninguno sobreescribe
y un nuevo envío después de refrescar puede registrar la respuesta.

No se aplicaron migraciones a la base operativa ni se modificó AWS. Quedan conexión
con la interfaz, decisiones de contexto/t, pruebas del recorrido y despliegue.

## Comprobación temporal con la interfaz publicada

Se combinó localmente, sin commit, la rama de interfaz en
66d60c55a75491f90d63dee2fdc1803557f67b93. La combinación se abortó limpiamente después
del ensayo; no se integraron archivos web en esta rama ni se hizo merge remoto.

- Tres recorridos HTTP adicionales contra el dominio ORM sin dobles: aprobados.
  Consulta con prevalencia/intensidad conocidas; guardado e idempotencia de percepción
  y conflicto de versión; comparación que informa contexto ausente.
- Tres tests JavaScript propios de la interfaz: aprobados.
- Suite combinada: 405 pruebas, un fallo de aislamiento en
  `test_backend_pendiente_no_se_convierte_en_vacio` del archivo
  `apps/historico/test_web_interfaz.py`. Los demás casos pasaron.

Ese test simula indisponibilidad de opciones_historico, pero no de
obtener_percepcion. La lectura de percepción ya implementada devuelve 404 para el
UUID inexistente de esa fixture, en lugar del 503 que daba la base sin implementar.
Para probar el estado pendiente debe simular explícitamente la lectura:

```python
with patch('apps.historico.services.obtener_percepcion',
           side_effect=BackendHistoricoNoDisponible()), \
     patch('apps.historico.services.registrar_percepcion') as guardar:
    # Mantener las aserciones de 503 y guardar.assert_not_called().
    ...
```

La corrección corresponde al test de la interfaz. No cambiar ServicioNoDisponible
ni devolver un 503 para un servicio realmente inexistente. Ese estado sigue siendo
404 según el contrato v1. Repetir la suite combinada después de corregir ese test.
