# Cierre técnico de integración: contexto, histórico y recomendaciones

Actualización al integrar: se coordinó y corrigió el párrafo del contrato B6 sobre
contexto y se registró la aprobación del perfil experimental el 03/11/2026. Sus
indicadores operativos siguen desactivados. Las secciones siguientes conservan
la revisión original y sus resultados, no una lista de pendientes aún abiertos.

Base de main comprobada: `543d57572fd1c897e721b99110139b19d499541b`.
Rama: `integracion-contexto-historico-recomendaciones`. Entrega en PR borrador
contra main, sin merge ni despliegue.

Se consultaron `motor_contexto_piloto.md`, contratos v1 de bloques 6/7 y las rutas
integradas. No se reproducen fallos de producción en los recorridos de este informe;
por ello la entrega incorpora pruebas relevantes y documentación, sin cambios
especulativos de lógica, contratos o modelos.

## Recorrido probado y límites del ensayo

`apps/recomendaciones/test_integracion_contexto_historico.py` añade nueve pruebas.
Usa SQLite y almacenamiento privado temporales, catálogo ficticio y usuarios de test.
No usa datos operativos ni reemplaza services, selectores o contexto.

Cada servicio se registra por el POST real de bandeja, con sede/modalidad/lote del
formulario. Se suben dos PNG artificiales con protocolo y confirmaciones mediante
las vistas reales. La franja procede del reloj del servido, único reloj sustituido
para fijar fechas reproducibles; el retorno se envía a otra hora y debe conservar
la instantánea original.

Después se solicita un análisis mediante el servicio real. Se cargan por ORM
resultados históricos conocidos y su revisión de ensayo para verificar el recorrido
desde mediciones persistidas hacia indicadores. Son un **oráculo de test**, no una
inferencia ni una confirmación real de máscaras. Sus aprobaciones históricas no
activan la configuración actual. La rectificación posterior sí atraviesa el POST
real de Cocina. No se ejecuta un motor ni se acredita precisión científica.

Toda evaluación de recomendaciones usa los criterios actuales SIN APROBAR, conserva
INSUFICIENTE y no genera propuesta. No se importan ni activan perfiles de
`ops/analisis/`. No se modifica ningún archivo de `visual_service/` u `ops/analisis/`.

## Resultados funcionales

| Caso | Resultado comprobado |
| --- | --- |
| Captura → histórico → evaluación | La misma clave de contexto y las referencias exactas de intento se conservan; el retorno no modifica la instantánea |
| Dos lotes en el mismo contexto | Se agrupan: porcentajes 20 y 40 del oráculo dan n=2 e intensidad 30; el lote no se convierte en separador de contexto |
| Registro sin contexto junto a los anteriores | Su 90 permanece en un grupo aparte, contexto None y no comparable; no contamina la media 30 |
| Sede, modalidad o franja distintas | Grupos distintos; seis servicios del ensayo forman cinco grupos, sin media global de grupos |
| Solo registros sin contexto | Conservan mediciones descriptivas, pero el grupo no es comparable y no habilita generación de recomendaciones |
| Dos periodos, contexto igual y lotes diferentes | Se conserva la clave y la diferencia descriptiva de intensidad (-20 pp); prevalencia sigue no disponible por falta de t aprobado |
| Rectificación de revisión | El POST RECHAZADO invalida la evaluación anterior; consulta nueva excluye el servicio y conserva las dos revisiones |
| Análisis nuevo con otro modelo, pendiente | No hereda aprobación del intento anterior; desaparece de aptos y la evaluación previa queda obsoleta |
| Anulación de servicio incompleto | Cambia la exclusión a ANULADO e invalida la evaluación sin reescribir la instantánea guardada |
| Corrección del lote en una fuente del test | Invalida la evaluación aunque mantenga grupo e indicadores: la huella incluye esa evidencia de contexto |
| Retención posterior de fotografías | El borrado local del ensayo y la marca de eliminación no borran la medición revisada ni invalidan por sí solos la evaluación histórica |

En todos los casos de invalidación se comprueba GET con vigente=False, capacidad de
generación deshabilitada y POST de generación 409. El JSON del snapshot anterior
permanece idéntico; el caso de rectificación también comprueba que reevaluar crea
un ID nuevo tras cambiar la evidencia.
La corrección de lote se emula directamente en la BD de test para comprobar la
huella, no añade un endpoint ni recomienda editar instantáneas operativas.

El análisis nuevo se solicita con una versión distinta por la operación existente;
no se fuerza un reintento de un análisis completado, que el dominio no permite.
La anulación se realiza sobre un servicio incompleto por la ruta administrativa,
respetando los estados permitidos.

## Qué significa «sin contexto»

No se mezclan grupos de contexto conocido con None ni se infiere sede, modalidad,
franja o lote de un registro anterior. Los registros sin contexto pueden seguir
mostrando intensidad descriptiva de sus mediciones válidas; eso no afirma que sus
preparaciones sean comparables ni habilita recomendaciones suficientes.

Si un alcance contiene varios grupos, la cabecera devuelve MULTIPLES_GRUPOS y las
medias globales quedan ausentes. Cada grupo conserva su n y métricas. No se promedian
medias de grupos ni se agrega un filtro público por sede que altere el contrato.

## Comandos y resultados

Entorno virtual propio, dependencias declaradas (Django 5.2.19 / Pillow 12.3),
SQLite temporal y fotografías artificiales privadas eliminadas al terminar.

| Comando | Resultado |
| --- | --- |
| python manage.py test apps.recomendaciones.test_integracion_contexto_historico | 9 pruebas aprobadas |
| python manage.py test | 541 pruebas aprobadas |
| python manage.py check | Sin incidencias |
| python manage.py makemigrations --check --dry-run | No changes detected |
| node --test tests/frontend/*.test.cjs | 42 pruebas aprobadas |

La suite aplica migraciones solo en su base de pruebas. No se ejecuta migrate sobre
una base operativa, entrenamiento, activación del endpoint o modificación de pesos.
Pasar estos tests valida el recorrido técnico descrito; no sustituye el QA intensivo
del grupo ni aprueba criterios experimentales.

## Pendientes concretos para el QA del grupo

| Recorrido manual en entorno aislado | Comprobación y evidencia a registrar |
| --- | --- |
| Alta con datos completos, parciales y omitidos | Capturar los errores y valores conservados. Completo guarda sede/modalidad/lote; omisión total queda sin contexto; parcial no crea servicio |
| Servido y retorno con una bandeja real de ensayo | Anotar ID de servicio, lote y franja tras servido; confirmar que retorno a otra hora mantiene todos los datos y libera la bandeja |
| Grupos conocidos y registros anteriores sin contexto | Revisar que aparezcan separados, que None no se interprete como una sede, y que la cabecera no muestre una media global con grupos múltiples |
| Cambios de sede/modalidad/franja | Revisar separación de grupos y límites de hora de Ecuador. No enviar una hora falsa desde el navegador ni cambiar el reloj operativo |
| Filtros y periodos | Probar fechas inclusivas y horas exclusivas, combinaciones válidas/inválidas, página siguiente/anterior y contadores del conjunto completo |
| Rectificación en Cocina y análisis nuevo | Dejar una evaluación abierta, cambiar la evidencia desde la operación autorizada, refrescar y verificar obsolescencia/409. Guardar ambas referencias de evaluación/revisión |
| Dos operadores, versión obsoleta y doble envío | Comprobar conservación del borrador, autor/fecha y ausencia de sobrescritura; no reintentar escrituras automáticamente |
| Fotos retenidas y vencidas en una BD de QA | Confirmar que el histórico conserva mediciones; no confirmar imágenes no disponibles ni publicar evidencia privada |
| Roles simples y combinados | Registro captura; Cocina consulta/revisa según sus permisos; Administración evalúa. Probar URL directa, sesión caducada y CSRF |
| Escritorio, móvil y Figma | Revisar 1440x900 y 390x844, teclado, foco, errores, desplazamiento de tablas, estado sin datos y mensajes de guardado. Figma requiere acceso/exportaciones y queda a cargo del grupo |

Además:

- La aprobación de criterios, la validación de geometría y la evaluación de un motor
  con imágenes reales son decisiones separadas. La insuficiencia actual es correcta.
- El DTO de prueba controlada expone el último resultado; el historial de resultados
  anteriores está persistido. Un explorador visual de todas sus versiones necesita
  coordinación del contrato, no datos nuevos inventados desde la interfaz.
- Coordinar la actualización del párrafo histórico de contrato_bloque_6.md que aún
  dice que Servicio no registra contexto; motor_contexto_piloto.md y el contrato
  ejecutable reflejan el contexto nuevo y preservan None en registros anteriores.
  No se cambia unilateralmente el documento contractual en este PR.
- El motor/dataset y perfiles de ops quedan fuera de esta entrega y bajo revisión
  separada. No se arrastran como abiertos los hallazgos antiguos ya corregidos en main.
- No se producen capturas nuevas ni se declara terminada la comparación con Figma:
  la revisión visual e intensiva se reserva al grupo, tal como se solicitó.
