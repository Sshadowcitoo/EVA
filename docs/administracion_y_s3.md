# Administración y almacenamiento privado S3

Actualización del 1 de noviembre de 2026. Completa las acciones operativas de
Administración del bloque 2 y conecta las capturas al adaptador S3. No implementa
los endpoints de vinculación temporal PC–celular ni cambia las políticas de IA.

## Administración

Ruta de entrada: `captura:gestion` (/captura/gestion/). Buscar por número de bandeja
o UUID exacto de servicio. No se ofrece un listado general de comidas de Registro.

- Anular: GET muestra datos/efectos; POST exige CSRF, motivo y confirmación.
  Solo Administración con captura.anular_servicio. Conserva fotografías y autoría,
  registra motivo/autor/fecha, cierra la asignación y cancela solicitudes pendientes.
  Históricos y pares completos no se anulan; repetir no sobrescribe la auditoría.
- Reemplazar: solo Administración con captura.reemplazar_etiquetabandeja.
  POST con motivo, confirmación y código esperado. La comprobación condicional en
  transacción rechaza el reenvío de una etiqueta antigua, conservando el nuevo QR.
  No cambia bandeja, comida, asignación ni fotos. La anterior queda revocada.
- QR: imagen SVG generada localmente por qrcode, descargable con el número visible.
  Solo se entrega la etiqueta vigente, con autorización y no-store. No autentica.

## Frontera de almacenamiento

`guardar(bytes, clave_relativa, tipo_contenido=...)` devuelve Guardado con backend,
clave persistida, hash_sha256 y version_id. Las vistas guardan esos metadatos y,
si falla la BD, compensan en el mismo backend y versión. Una limpieza fallida queda
registrada en EVA_CAPTURE_ORPHAN para reintento operativo. Un timeout S3 registra
EVA_CAPTURE_S3_UNCONFIRMED para reconciliar sin borrar a ciegas un objeto existente.

S3 antepone EVA_S3_PREFIX y persiste la clave completa, sin nombres de cliente.
PutObject usa IfNoneMatch='*', SSE-S3 AES256 y checksum SHA-256. No establece ACL
pública, no genera URLs prefirmadas y no incorpora credenciales al navegador.
Abrir/eliminar validan prefijo y respetan VersionId cuando exista.

`abrir` y `eliminar` aceptan backend/version_id explícitos desde FotografiaServicio.
No reinterpretar fotos locales antiguas como objetos S3 al cambiar configuración.
No se trasladan ni se borran imágenes anteriores. Errores de almacenamiento
se muestran sin confirmar éxito ni ampliar permisos; no hay fallback silencioso.

## Activación autorizada en el servidor

Instalar requirements.txt únicamente en el entorno virtual de EVA. Se añadieron
boto3 y qrcode al entorno local con autorización explícita; Pillow ya estaba
instalado localmente. El servidor debe tener esas dependencias antes de cambiar código.

Usar el rol eva-demo-ec2-role en us-east-2, bucket privado
`eva-piloto-fotos-20261028-c7d9` y prefijo `eva/capturas/`. Mantener Block Public
Access, sin access keys permanentes. El bucket actual no tiene versionado;
si se habilita en el futuro, revisar permisos GetObjectVersion/DeleteObjectVersion
y conservación, sin ampliar IAM como efecto secundario de esta entrega.

Después de respaldar y desplegar la revisión probada, establecer en el entorno
privado EVA_STORAGE_BACKEND=s3, EVA_S3_BUCKET, EVA_S3_REGION y EVA_S3_PREFIX.
No imprimir ni subir /etc/eva/eva.env. La raíz local sigue siendo privada también
con S3, para leer las fotos anteriores de forma autorizada.

Prueba explícita en la instancia, usando su rol (solo archivo técnico propio):

```bash
python manage.py verificar_storage_s3 --confirmar-prueba
```

El comando escribe, lee/compara y elimina su propio archivo en healthchecks/.
No utiliza fotos del piloto, no cambia la BD y no configura cuentas ni IAM.
Rechaza ejecución sin confirmar o sin backend s3. Solo su ejecución real exitosa
acredita conectividad; las pruebas de Stubber no sustituyen esa evidencia.

## Verificación local

156 pruebas Django y 7 JavaScript aprobadas. Checks correctos y migraciones sin
cambios. Cobertura nueva: Administración/CSRF/permisos específicos, GET sin efectos,
anulación/auditoría, cancelación de enlaces, doble reemplazo, QR revocado,
par completo, S3 Put/Get/Delete/VersionId/checksum/SSE/prefijo/no sobrescritura,
lectura mixta y flujo HTTP con compensación. S3 se simula sin llamadas a AWS.

La conservación de 90 días y la limpieza programada de huérfanos siguen siendo
trabajos separados; registrar claves para reintentar no equivale a un scheduler.
