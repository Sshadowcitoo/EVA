# Verificación conjunta del bloque 7

La rama `dominio-recomendaciones-bloque-7` combina la base del PR #46, el dominio
persistente y la interfaz del PR #47 (commit 3585fece884c2e859f34e06b9421cf4c5dd8efa9).
Se preservan sus commits y no se ha hecho merge a main ni desplegado en AWS.
Incluye global `/recomendaciones/` y navegación para Cocina/Administración.

Leer `docs/contrato_bloque_7.md`, `docs/dominio_bloque_7.md` y los documentos de la
interfaz. Las diez firmas y DTO se mantienen; no hace falta reescribir las vistas.

## Continuación de la interfaz

Partir de esta rama conjunta en una rama propia, sin perder trabajo local:

```powershell
git fetch origin
git switch -c verificacion-recomendaciones-bloque-7 origin/dominio-recomendaciones-bloque-7
```

Responsabilidad: revisión de forms/views/urls/templates/static de recomendaciones,
pruebas HTTP y JavaScript, documentación y evidencia visual. No cambiar modelos,
migraciones, contratos, criterios ni servicios de dominio unilateralmente.

1. Confirmar localmente la migración `recomendaciones.0001_initial` en una BD de
   desarrollo/pruebas; no tocar AWS ni datos operativos.
2. Añadir pruebas HTTP con ORM real, sin reemplazar services: listado y filtros,
   evaluación insuficiente guardada/recuperada, ausencia de efectos en GET,
   roles y CSRF, intentos de generar con evidencia insuficiente, cambios de
   vigencia, 409 conservando borrador e historial de decisiones/pruebas.
3. Ya existen cinco recorridos conjuntos en `test_integracion_bloque_7.py` y pruebas
   de dominio/concurrencia. Complementarlos con casos HTTP faltantes, sin repetir
   pruebas que solo sustituyan las funciones ni asumir que el backend sigue pendiente.
   Mantener los tests explícitos del error 503 como contrato de fallo.
4. Sin contexto histórico, las evaluaciones reales son INSUFICIENTE y las
   comparaciones NO_EVALUABLE: es el límite documentado, no un fallo que se deba
   ocultar. Los tests positivos de dominio usan configuración y contexto hipotéticos
   identificados como tales; no aprobarlos en settings ni servir fixtures en la demo.
5. Comprobar la interfaz a 1440x900 y 390x844, sin números inventados, sin pérdida
   del borrador en conflictos, y con estados de guardado claros. Buscar problemas
   de accesibilidad, navegación y doble envío con/sin JavaScript.
6. Figma continúa pendiente: usar el enlace de `docs/figma_referencia.md` solo con
   acceso funcional o exportaciones. No declarar el 70 % ni inventar node-id.

Entregar un PR contra `dominio-recomendaciones-bloque-7`, sin hacer merge. Indicar
commit base, comandos/resultados, archivos modificados, capturas y pendientes.
Títulos y commits descriptivos, sin atribuciones a asistentes. No volver a mezclar
la base original de #47 como si faltara: ya está incluida en esta rama.

## Límites pendientes para operación real

Aprobar criterios numéricos y reglas con justificación, definir/persistir contexto
histórico real, y evaluar el motor con imágenes. No se resolvieron fingiendo un
criterio aprobado. El despliegue AWS y la comparación visual con Figma siguen
separados de la implementación del dominio.

## Verificación de esta integración

- Suite conjunta: 470 pruebas Django aprobadas; 42 JavaScript aprobadas.
- manage.py check sin incidencias; makemigrations --check --dry-run sin cambios.
- La suite aplica la migración en su BD aislada; no se migró ninguna BD operativa.
- Cinco recorridos HTTP reales adicionales en test_integracion_bloque_7.py.
- Prueba de concurrencia con dos conexiones: como máximo una decisión guardada,
  sin historial sobrescrito. SQLite puede devolver 409 a ambas; un nuevo intento
  explícito después de refrescar puede guardar. No hay reintento automático.
- Tras ampliar la defensa frente a reglas malformadas (categoría no textual o
  NaN numérico), su prueba dirigida también pasó.
- La prueba HTTP previa del motor necesitó permiso de conexión a loopback: sin
  él falló con WinError 10013; con él pasó en la suite completa.
- No se ejecutó una comparación nueva con Figma ni despliegue AWS.
