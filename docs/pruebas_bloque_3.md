# Preparación de pruebas del bloque 3 — 29/10/2026

Rama: `eduardo-b3-pruebas-nube`. Base: contrato/configuración César `7121e21`, con dependencia de su bloque 2. No equivale a main integrado ni a captura/S3 implementados. Se leyeron las ocho páginas de la guía del bloque 3 y el contrato del repositorio. No se reutiliza la rama del bloque 2.

## Código comprobable disponible

`config/capture_checks.py`, settings y permisos publicados por César; Jean publicó plantillas y JavaScript con red simulada. No están publicadas ramas de Isaac/Lino del bloque 3: faltan SesionCaptura, adaptador S3 y endpoints. No se inventan modelos, tokens o URLs para hacer pasar pruebas.

`apps/captura/test_configuracion_bloque3.py` añade casos de configuración sin red ni creación de directorios, errores explícitos de S3 y raíz privada fuera de estáticos. No usa credenciales ni realiza llamadas AWS. Los resultados se registrarán después de ejecutar.

Ejecución 29/10 en esta copia: `..\.venv\Scripts\python.exe -B manage.py test apps.captura.test_configuration apps.captura.test_configuracion_bloque3 --verbosity 1`: **9 aprobadas en 0.051 s** (6 de César y 3 complementarias), check sin problemas. Solo comprueba configuración; no acredita adaptación S3 ni enlaces reales.

## Matriz funcional pendiente

| ID | Escenario | Garantía a comprobar |
|---|---|---|
| B3-01 | Crear vínculo autorizado | Servicio/etapa correctos, digest persistido, token aleatorio según contrato |
| B3-02 | Anónimo o rol incorrecto conoce token | Sin acceso a carga ni consulta; QR no autentica |
| B3-03 | Otro operador Registro | Política del contrato permite operar; autor real guardado sin cambiar creador/emisor |
| B3-04 | Antes, justo al vencer y después del TTL | Vigencia comprobada en servidor con reloj controlado; no depende de scheduler |
| B3-05 | Cancelar o regenerar | POST/CSRF; solicitud anterior ya no admite carga |
| B3-06 | Token usado o segunda carga distinta | Sin sobrescritura ni consumo duplicado |
| B3-07 | Dos cargas concurrentes | Una aceptada; repetir según motor final |
| B3-08 | S3 put/get/delete con stub | Bucket/prefijo/claves correctos; sin red real en suite normal |
| B3-09 | Timeout, AccessDenied, clave ausente | Error estable sin secretos; no éxito falso ni fallback local silencioso |
| B3-10 | Sube archivo y falla BD | Compensación o limpieza reintentable; estado consistente |
| B3-11 | S3 falla durante carga | No foto aceptada ni vínculo completado |
| B3-12 | Versionado y convivencia local/S3 | Backend previo preservado; VersionId tratado conforme a contrato |
| B3-13 | Consultar estado | JSON mínimo, sin token, clave S3, nombres ni rutas; autorización por petición |
| B3-14 | GET/POST/CSRF | GET sin guardar; POST autorizado y con token CSRF |
| B3-15 | Login con next local/externo | Mantiene flujo local; rechaza redirección externa |
| B3-16 | Polling | Cada 3 s, sin solapamiento; pausa/fin según estado y visibilidad; errores no implican éxito |
| B3-17 | Privacidad del enlace | no-store y Referrer-Policy; no token en logs ni recursos externos |
| B3-18 | Borrado por conservación | Reloj controlado, máximo 90 días desde captura; versiones/temporales y fallos de borrado |
| B3-19 | Evidencia AWS real opt-in | Objeto de prueba en prefijo autorizado, servido por Django y lectura anónima denegada |
| B3-20 | PC → teléfono → PC | HTTPS autorizado, usuario Registro, captura real, S3 privado y confirmación de PC |

La cuenta normal de otro rol no puede operar por conocer el enlace. Otro Registro sí puede según el contrato posterior de César; la formulación genérica de “otro usuario” de la guía no debe imponer exclusividad del emisor sin acuerdo. La confirmación antigua permanece solo del creador.

## Ejecución y evidencia

La suite normal usa dobles controlados del SDK y almacenamiento temporal, no AWS. Las pruebas de SDK no se escribirán contra un adaptador inventado. Ejecutar check, suite completa y migraciones sin cambios tras disponer de dependencias. Registrar fecha, commits, comando y resultado de cada ejecución, incluyendo fallos.

Evidencia real requiere autorización de cuenta/región/bucket/prefijo y HTTPS accesible a teléfono/PC. No se crean recursos, abren puertos, instalan túneles ni borran datos de usuarios para este plan. Capturas deben ocultar tokens, cookies, credenciales y enlaces temporales. Probar borrado solo con objetos de prueba y reloj controlado: no declarar 90 días transcurridos.

## Bloqueos concretos

Faltan modelos/servicios de sesión, rutas/parámetros, errores del adaptador y tarea de conservación. También falta AWS/HTTPS autorizado y prueba de dispositivo. Las pantallas de Jean por sí solas no acreditan backend ni nube. No cerrar el bloque mientras falten estas evidencias; solo César integra PR.
