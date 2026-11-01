# Retención de fotos privadas

`python manage.py limpiar_fotografias` simula por defecto: no modifica filas ni archivos. Imprime el número de fotos de 90 días o más y las cargas de al menos 24 horas por reconciliar. El modo real requiere `--aplicar`. `--limite` acota cada grupo entre 1 y 10000 (predeterminado 500).

El límite se calcula desde la fecha de registro de cada fotografía, incluido servido, retorno y servicios anulados. Se borran únicamente los bytes mediante su backend, clave exacta y VersionId cuando existe. Se conserva la fila, autor, fechas, protocolo, checklist, servicio y resultados. `eliminada_en` registra el cierre; los fallos conservan fecha vacía, aumentan el contador y dejan un mensaje para reintentar. Un archivo ya ausente se considera limpiado. No se eliminan filas de servicios ni se liberan bandejas como efecto de la retención.

Las fotos vencidas o eliminadas no se sirven por HTTP aunque haya fallado el borrado físico: el acceso autorizado devuelve 410 y no-store. Si una fotografía reciente referencia la misma clave, el archivo se protege hasta que venza esa referencia. La ejecución diaria puede dejar un margen físico de hasta aproximadamente un día después del umbral, o más si hay errores o se supera el lote; estos casos requieren supervisión del informe. No se afirma borrado físico instantáneo al cumplir 90 días.

Antes de subir una fotografía desde el formulario, `CargaFotografia` persiste el destino. Pasadas 24 horas, se comprueba si cualquier foto referencia esa clave, incluso no vigente: si hay referencia se conserva; si no, se intenta borrar. Esto cubre también caídas entre subida y guardado de metadatos. Se conserva el resultado de reconciliación para auditoría. Las colisiones de archivo se marcan como resueltas sin autorizar su borrado. No se listan buckets ni se amplían permisos IAM.

El registro de cargas solo cubre subidas posteriores a la migración 0008 y hechas por el formulario de EVA. No se presume que objetos históricos desconocidos del bucket sean huérfanos. Los archivos técnicos de comprobación de S3 tienen su propio ciclo de limpieza.

## Activación en la demo

1. Respaldar y desplegar código; aplicar migración aditiva 0008.
2. Ejecutar simulación con `DJANGO_SETTINGS_MODULE=config.production` y el entorno privado del servidor. Revisar cantidades sin publicar claves o credenciales.
3. Tras confirmar la activación del borrado real, instalar las unidades de `ops/limpieza` en `/etc/systemd/system/`, ejecutar `systemctl daemon-reload` y `systemctl enable --now eva-limpieza.timer`.
4. Comprobar `systemctl list-timers eva-limpieza.timer` y posteriormente `journalctl -u eva-limpieza.service`. El estado de salida es fallido si hubo errores de almacenamiento, aunque otros elementos del lote sí se hayan limpiado.

El timer propone 06:15 UTC (01:15 Ecuador), con hasta cinco minutos aleatorios, después del respaldo diario. `Persistent=true` recupera una ejecución pendiente tras apagar el servidor. No hay activación implícita por desplegar código: el timer debe habilitarse de forma explícita.

Las copias SQLite preservan metadatos, no los bytes de las fotos. Restaurarlas no recupera archivos que ya fueron eliminados. S3 permanece privado, con versionado desactivado en la configuración actual; si cambia el bucket o su versionado, se deben revisar permisos de eliminación de versiones y su verificación antes de mantener esta política.
