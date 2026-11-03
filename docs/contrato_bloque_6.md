# Bloque 6: contrato v1 del histórico, indicadores y percepción

Base integrada: main `55495b56251e85a11433e705b0c498f27958c718` (bloques 4/5).
Rama de preparación: `base-historico-bloque-6`. Fuente ejecutable de nombres y
tipos: `apps/historico/contracts.py`, CONTRACT_VERSION=1. La base fija la frontera
para trabajar por separado. La rama `dominio-historico-bloque-6` implementa consultas
ORM y percepción sin cambiar estos nombres o DTO; no incluye la interfaz ni acredita
el cierre operativo del bloque 6. Detalle en docs/dominio_bloque_6.md.

## 1. Reparto por archivos

| Dominio e integración | Web e interfaz |
| --- | --- |
| contracts.py, filtros.py, models.py, services.py, selectors.py, apps.py, migrations/ | forms.py, views.py, urls.py, presenters.py si hace falta |
| Configuración compartida, permisos que requieran modelos, include global y navegación común | templates/historico/*, static/css/historico.css, static/js/historico.js |
| test_dominio_*.py, test_contrato_*.py y fixtures compartidas | test_web_*.py, test_interfaz_*.py y tests/frontend/historico*.test.cjs |
| docs/contrato_bloque_6.md, README y notas de integración | docs/interfaz_bloque_6.md y docs/entrega_web_bloque_6.md |

No generar modelos/migraciones desde la interfaz ni duplicar el cálculo en las
vistas o JavaScript. Una corrección de contrato se acuerda y publica antes de
renombrar campos. El directorio apps/percepcion es una reserva documental, no una
segunda implementación de estas funciones. No editar captura/análisis para
conectar un formulario sin describir y coordinar el punto de inclusión.

## 2. Funciones públicas definitivas de esta versión

Importar el módulo `from apps.historico import services` y llamarlo por atributo
(facilita sustituirlo en pruebas sin acoplarse al ORM):

```python
services.normalizar_filtros(datos) -> FiltrosHistorico
services.opciones_historico() -> OpcionesHistorico
services.consultar_historico(filtros, pagina=1) -> ResumenHistorico
services.comparar_periodos(filtros_a, filtros_b) -> Comparacion
services.obtener_percepcion(servicio_id, usuario) -> Percepcion
services.registrar_percepcion(servicio_id, categoria, motivo, usuario, version_esperada) -> Percepcion
```

`normalizar_filtros` funciona sin DB. En la base original las otras cinco funciones
lanzan BackendHistoricoNoDisponible; en la rama de dominio ya consultan y persisten.
La excepción permanece en el contrato por compatibilidad. La interfaz puede usar
dobles solo en pruebas; nunca convertir un fallo en datos de muestra o éxito falso.

## 3. Filtros y tiempo

Nombres de GET/formulario: `plato`, `componente`, `porcion`, `desde`, `hasta`,
`hora_desde`, `hora_hasta` y `page` (este último lo valida la vista y lo pasa como
pagina). Los tres primeros usan códigos históricos, no nombres ni IDs de catálogo.
Las opciones incluyen códigos desactivados usados históricamente; no limitar las
listas al catálogo activo. El backend comprobará además existencia y coherencia.

Fechas AAAA-MM-DD; ambas fechas incluyen el día visible. La normalización produce
`inicio` a medianoche local y `fin` a medianoche del día posterior a hasta; consulta
[inicio, fin). Zona única America/Guayaquil. Se admite fecha inicial o final abierta.
Las horas HH:MM deben estar ambas presentes o ambas vacías; rango [hora_desde,
hora_hasta), dentro del mismo día. Un rango nocturno o igual se rechaza: dividirlo
en dos consultas; no invertirlo ni interpretar igualdad como todo el día.

Se aceptan date/time ya limpiados por formularios y cadenas HTML válidas. Una
fecha inválida o un tipo inesperado produce FiltrosInvalidos.errores por campo.
Origen de consulta REAL; pedir SIMULADO es error, no una manera de mezclarlo.

La fecha analítica procede de la foto SERVIDO exacta del caso; sin análisis se
utiliza la primera foto SERVIDO aceptada. No sustituirla por fecha_creacion ni por
la hora actual. Sin fecha no se puede asignar un servicio a un periodo/horario:
advertirlo y no inventar la pertenencia. Sin filtro temporal se puede mostrar como
excluido/SIN_FECHA_SERVIDO. Las horas de retorno siguen siendo datos independientes.

## 4. DTO y unidades

Todos los campos de los TypedDict de contracts.py se entregan, con None cuando
corresponda. Son diccionarios, no instancias ORM. Fechas Python conscientes de zona;
valores numéricos Decimal sin redondear hasta presentar. Si se añade JSON, usar un
encoder de Django documentando la representación decimal; no introducir una API
independiente solo para estas páginas.

- ResumenHistorico: version_contrato, solo_pruebas, filtros, filas, paginacion,
  resumen, indicadores, grupos y advertencias.
- Cada fila identifica servicio + componente mediante fila_id; puede haber varias
  filas de un servicio. Contiene fecha, códigos y nombres históricos, origen,
  estado APTO/EXCLUIDO, porcentaje_visual nullable y motivo_exclusion nullable.
  Origen None significa todavía sin análisis, no REAL por presunción.
- resumen: candidatos, aptos y excluidos son **servicios únicos** del alcance.
  candidatos = aptos + excluidos. proporcion_excluidos en porcentaje, None con
  denominador cero. motivos es un desglose principal determinista, sin sumar un
  servicio varias veces. Orden de motivo: anulado, sin fecha, par incompleto,
  sin análisis, intento no completado, sin revisión, revisión no confirmada,
  criterios/componentes inválidos. El detalle puede explicar más de una condición.
- indicadores: n (servicios del grupo), t, version_criterio, prevalencia, intensidad,
  motivos_no_disponible. Los porcentajes y t están en puntos porcentuales 0..100;
  no usar fracciones 0..1 para presencia o prevalencia. Un cero confirmado es 0,
  no None. Confianza del modelo sigue siendo otra magnitud en el bloque 4.
- grupos contiene la clave de comparabilidad (plato/componente/porción/contexto,
  modelo, configuración y protocolo) e indicadores por grupo. No mezclar arroz y
  pollo, porciones distintas o versiones incompatibles en una única media.
  Si hay varios grupos, los indicadores de cabecera quedan n=0 y valores None con
  MULTIPLES_GRUPOS; mostrar los n reales en cada grupo y los servicios en resumen.
- paginacion: pagina >=1, paginas >=1 incluso vacía, total_filas y por_pagina=30.
  Indicadores/resumen corresponden al conjunto completo filtrado, no a la página.
- solo_pruebas es False para la respuesta real. Las fixtures lo marcan True y deben
  mostrarse con etiqueta de datos de prueba en los ensayos de interfaz.

Los SIMULADO identificados se omiten del alcance analítico, incluso de candidatos.
Servicios todavía sin origen conocido pueden aparecer solo como excluidos. No
reclasificar fixtures como datos reales por haber rellenado una columna.

## 5. Elegibilidad y fórmulas

Usar la regla compartida del bloque 5 y seleccionar el análisis más reciente del
servicio, su intento vigente y la revisión vigente del mismo intento. Guardar la
configuración aplicada; no evaluar un resultado histórico con criterios actuales.
Se excluyen anulados, pares/resultados incompletos, fallos, pendientes, rechazados,
no concluyentes y resultados no comparables. No calcular un total de servicio con
componentes faltantes. Un join con revisiones/máscaras no puede duplicar la muestra.
Un rechazo posterior afecta nuevas consultas. Vencimiento posterior de archivos
no borra una revisión antes válida ni obliga a conservar imágenes para siempre.

Por grupo y periodo, n servicios aptos comparables:

- prevalencia = 100 * cantidad con porcentaje_visual > t / n (comparación estricta).
- intensidad = suma de porcentajes_visual / n, incluyendo ceros confirmados.
- Sin n: None y motivo, nunca cero desperdicio. Sin t aprobado: prevalencia None,
  SIN_CRITERIO_PRESENCIA; intensidad puede existir si los registros sí son aptos.

El perfil experimental aprobado el 03/11/2026 fija t=10, pero sigue sin activarse
operativamente. Los ejemplos t=20 son exclusivamente fixtures. Servicio registra
contexto_snapshot y contexto_clave desde la captura del servido: establecimiento,
sede, modalidad, lote y franja automática. El retorno conserva esa instantánea;
el lote no separa grupos equivalentes. Ver docs/motor_contexto_piloto.md.
Registros anteriores u omisiones completas conservan contexto desconocido: no usar
el catálogo actual para fabricar contexto ni rellenar el pasado. Grupo.contexto_clave
puede ser None; comparable=False con SIN_CONTEXTO_HISTORICO.

## 6. Comparación

Entrada: dos FiltrosHistorico, con periodos de fechas definidos y no superpuestos,
mismos códigos, horas y origen. DTO: referencia, comparado (dos ResumenHistorico),
comparable, motivos y diferencias {prevalencia_pp, intensidad_pp}. Las diferencias
son comparado - referencia, en puntos porcentuales. No promediar grupos ni fabricar
un cambio relativo cuando la referencia sea cero. n/exclusiones visibles en ambos.
Incompatibilidad, sin datos o criterios ausentes: diferencias afectadas None y
explicación. Una diferencia observada no demuestra mejora causal.

## 7. Percepción

Categorías exactas en CATEGORIAS_PERCEPCION: INSUFICIENTE, ADECUADA, EXCESIVA,
NO_INFORMADO. Sin respuesta: NO_INFORMADO, motivo vacío, version=0 si no hay registro,
registrada_en=None y operador_visible=None. No confundir ausencia con ADECUADA.

DTO Percepcion: servicio_id, categoria, motivo, version, registrada_en,
operador_visible. GET usa obtener_percepcion, no accede a un modelo todavía ausente.
POST toma servicio de la URL y usuario de request.user, nunca del formulario.
Motivo declarado opcional, máximo MAX_MOTIVO=1000, sin identidad del comensal.
Para NO_INFORMADO se exige motivo vacío. Mostrar aviso de no escribir datos personales.

Cualquier operador activo Registro puede registrar/corregir con el identificador
del servicio, no solo su creador. El backend verificará servicio existente y no
anulado, categoría, motivo y versión no negativa. Dos correcciones concurrentes
producen ConflictoPercepcion; idéntico reenvío no duplica. Conservar auditoría de
cambios. No modificar porcentajes ni bloquear captura si no hay respuesta.

## 8. Vistas, rutas y errores

La interfaz entrega `apps/historico/urls.py`, namespace historico:

| Nombre | Ruta relativa | Método y rol |
| --- | --- | --- |
| lista | vacía | GET, Cocina o Administración |
| comparar | comparar/ | GET, Cocina o Administración |
| percepcion | servicios/<uuid:servicio_id>/percepcion/ | GET/POST, Registro |

En comparar, los periodos usan referencia_desde/referencia_hasta y
comparado_desde/comparado_hasta; los demás filtros son compartidos. Normalizar cada
periodo con normalizar_filtros. Se incluirá el módulo globalmente bajo /historico/
al integrar la interfaz, no antes. No modificar config/urls.py en paralelo.

Usar roles_required(COCINA, ADMINISTRACION) para consulta y roles_required(REGISTRO)
para percepción. is_staff no concede roles; conservar la excepción de superusuario
del helper existente. También autorizar POST en servidor y mantener CSRF. Usuarios
con varios roles conservan los accesos expresos de cada rol.

| Situación | Tratamiento web |
| --- | --- |
| FiltrosInvalidos | 400 y errores por campo; conservar entradas |
| BackendHistoricoNoDisponible | 503, módulo pendiente de conexión; sin registros ficticios |
| ServicioNoDisponible | 404 sin revelar datos ajenos |
| ConflictoPercepcion | 409; refrescar versión, no sobrescribir ni reintentar automáticamente |
| ValidationError de Django | 400 y mensaje de campo/no campo escapado |
| PermissionDenied / sin sesión | 403 / login según helper existente |
| Resultado válido pero sin datos o sin t | 200 con DTO y motivos; no es un fallo del backend |

No convertir excepciones desconocidas en una respuesta vacía exitosa.

## 9. Pruebas compartidas y criterio de entrega

`apps/historico/testing/fixtures.py`: historico_fixture(escenario),
comparacion_fixture(comparable=True), percepcion_fixture(registrada=False) y
opciones_fixture(). Escenarios: con_datos, sin_datos, sin_aptos,
configuracion_pendiente. Son copias independientes sin ORM/archivos/red. Ejemplo
con_datos: 0,10,30,60; t=20 de prueba; n=4, prevalencia=50, intensidad=25;
un quinto servicio excluido (20 %). Las filas 'REAL' simulan ese estado en una
prueba unitaria; no son servicios reales cargables en producción.

Las pruebas web sustituyen explícitamente las funciones de services. No importar
fixtures desde código productivo. Probar roles aislados, CSRF, campos inválidos,
versiones obsoletas, n=0, cero real, parámetros pendientes, periodos incompatibles,
paginación y valores escapados. Registrar nodos/capturas Figma verificados en
390x844 y 1440x900; no inventar los que falten.

La interfaz puede entregar su PR antes de la persistencia, indicando BACKEND_PENDIENTE.
Para cerrar el bloque completo faltarán consultas/persistencia, pruebas combinadas,
conexión real y despliegue verificado. No hacer merge ni despliegue desde esa rama.
