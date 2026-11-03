# Bloque 4: integración del motor, worker y evidencia privada

Esta entrega sustituye la parte de Lino. Depende de main con #39; no incorpora
un modelo de segmentación, entrenamiento, umbrales aprobados ni una simulación
oculta. Las plantillas de Jean se reutilizan sin sobrescribirlas; dos plantillas
adicionales permiten solicitar análisis y paginar la lista existente.

## Uso y permisos

Cocina abre `/analisis/`, ve los pares completos y solicita su análisis por POST.
Una solicitud repetida recupera el mismo intento. La consulta de estado es GET
privado y sin caché; fallos y tiempos agotados permiten reintento explícito.
Registro y Administración solos no heredan Cocina. Las escrituras requieren CSRF.
El gateway de evidencia de captura no se amplió a otros roles: se añadieron rutas
propias que comprueban que foto/máscara pertenece al análisis solicitado.

## Motor interno v1

Configurar por entorno `EVA_VISUAL_ENDPOINT`, `EVA_VISUAL_VERSION_MODELO`,
`EVA_VISUAL_TOKEN` y `EVA_VISUAL_ORIGEN` (REAL por defecto; SIMULADO explícito).
No guardar el token en Git. Endpoint HTTPS, salvo HTTP en loopback para desarrollo;
sin usuario/clave/query/fragmento, sin proxies de entorno ni redirecciones.

POST multipart: campos `servido`, `retorno` y `metadata` JSON. Metadata contiene
schema_version=1, request_id UUID del intento, servicio_id, version_modelo,
version_configuracion, origen y componentes [{id,codigo}] históricos.

La respuesta JSON debe devolver esos identificadores y versiones, origen exacto y
componentes [{id, confianza, comparable, oculto, mascaras}]. Cada máscara contiene
etapa SERVIDO/RETORNO, ancho, alto y png_base64. Área inicial/residual opcional:
si se declara debe coincidir con el conteo de píxeles de la máscara. No se confían
las cifras del motor. PNG binario de un canal, fondo 0/alimento 255, sin animación,
dimensiones idénticas a su foto padre, máximo 8 MiB por máscara/20 megapíxeles;
64 MiB por respuesta y máximo 32 componentes. Se rechazan solapamientos.

El esquema v1 solo certifica geometría con `transformacion` exactamente
`{"tipo":"IDENTIDAD","escala_comun":true}`, fotos del mismo tamaño, ambos
checklists completos y comparabilidad aprobada por configuración. Otras ROI o
alineaciones deben ampliar el contrato; no se presuponen equivalentes. La versión
de configuración debe coincidir con la aplicada al intento. Sin aprobación,
umbral o geometría se conserva la incertidumbre: no concluyente, nunca cero falso.
Componente omitido produce SIN_DETECCION mediante el dominio existente.

## Worker y límite total

Ejecutar `python manage.py procesar_analisis --una-vez` para consumir como máximo
un intento, o sin la opción para mantener la cola. Sin motor configurado termina
con un error claro, sin consumir pendientes ni producir resultados simulados.
El supervisor reclama un intento y ejecuta un proceso hijo de Django. El plazo de
30 s empieza al reclamar e incluye arranque, lectura, llamada, validación y guardado.
Al vencer mata el hijo y cierra TIEMPO_AGOTADO; la transición del dominio también
rechaza resultados tardíos. Hay logs de reclamo, inicio y fin de llamada separados,
sin cuerpos, tokens o URLs internas. Interrumpir el supervisor mata el hijo activo.

`analisis_ejecutar_intento` es un comando interno del supervisor, no una alternativa
para ejecutar manualmente la cola sin su límite. `ops/analisis/eva-analisis.service`
es una plantilla de despliegue con KillMode=control-group; no se instaló ni activó.
El proceso usa el mismo entorno y DJANGO_SETTINGS_MODULE del servidor. Cambiar
variables del motor exige reiniciar el worker, no editar el código.

## Persistencia y conservación

Las cargas se registran en CargaFotografia ANTES de escribir. Solo se publica el
resultado cuando se guardaron todos los artefactos y la transacción final del
dominio tuvo éxito. Un fallo o muerte conserva las cargas para reconciliar después
de 24 h; una colisión no permite borrar un objeto previo.

La limpieza existente ahora reconoce referencias de ArtefactoAnalisis, no borra
máscaras vinculadas como huérfanas y elimina máscaras según la fecha de su foto
padre (90 días). Respeta referencias recientes a la misma clave y conserva metadatos.
`limpiar_fotografias` sigue siendo simulación por defecto; --aplicar borra bytes.
No se ejecutó borrado en producción. La frecuencia diaria mantiene el margen y
las limitaciones de conservación ya documentadas, no garantiza borrado al segundo.

Las máscaras originales permanecen privadas. Su gateway genera PNG transparente
coloreado para visualización con color_clave estable 1..8; no altera áreas ni fechas.
Archivos vencidos/no disponibles: 410; almacenamiento caído: 503. No se exponen
claves S3, rutas locales ni mensajes internos al usuario.

## Verificación y pendientes

Suite final del bloque 4 por separado: 287 pruebas aprobadas, incluidas 17 específicas con HTTP real local autenticado,
cancelación de subproceso real bloqueado, almacenamiento temporal, cola, retención,
permisos HTTP, CSRF y fallos. Check sin problemas y migraciones sin cambios.
Pruebas usan fixtures; no acreditan segmentación o precisión de IA.

Pendientes externos: configurar y evaluar motor REAL con pesos/datos independientes,
aprobar criterios y comparabilidad, habilitar worker en el despliegue autorizado,
ensayar el recorrido real en AWS y validar visualmente móvil/Figma. El bloque 5
se entrega en otro PR, dependiente de este y de las entregas #38/#35/#37.
