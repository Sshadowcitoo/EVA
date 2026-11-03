# Interfaz del histórico e indicadores

Implementación del contrato v1 en `interfaz-historico-bloque-6`, desde
`b217b6e92dea596b14b45ca2ce25797b291437d0` de `base-historico-bloque-6`.

## Pantallas y estados

- Histórico: filtros por códigos históricos, fechas y horario local; tabla por
  servicio/componente; indicadores y grupos separados; exclusiones por servicio.
- Comparación: filtros comunes y dos periodos inclusivos sin superposición;
  muestras, versiones, exclusiones y diferencias proporcionadas por el servicio.
  No se calcula ninguna diferencia en HTML, Python web ni JavaScript.
- Percepción: respuesta opcional, NO_INFORMADO distinto de ADECUADA; aviso de
  privacidad; versión oculta; autor y fecha de la respuesta vigente.
- Sin candidatos, sin aptos, criterio pendiente y múltiples grupos se distinguen.
  None se muestra como No disponible y Decimal(0) como 0,00 %.
- BACKEND_PENDIENTE devuelve 503 explícito, sin fixtures de producción ni éxito.
- Conflicto devuelve 409, consulta nuevamente la respuesta vigente y conserva
  propuesta/versión enviada. Guardado bloqueado hasta recargar y decidir otra vez.
- Guardado correcto utiliza POST/redirect/GET y un mensaje de sesión del servidor.
  Un parámetro GET no puede fabricar confirmación de guardado.

## Acceso y formularios

Se utilizan los decoradores existentes: Cocina/Administración consultan;
Registro registra percepción. Staff no concede acceso; se conserva la excepción
existente de superusuario y los roles múltiples suman accesos expresos.
Métodos no admitidos devuelven 405 y los POST conservan CSRF.

Las entradas válidas se normalizan con services.normalizar_filtros; las opciones
proceden de services.opciones_historico, sin consultar catálogo desde las vistas.
El backend sigue siendo responsable de existencia, elegibilidad, paginación,
unicidad, idempotencia y persistencia. Las vistas no aceptan usuario ni servicio
alternativo desde el formulario y no crean modelos ni migraciones.

Los errores de dominio se presentan escapados con 400/403/404/409/503 según
contrato. Las excepciones inesperadas no se convierten en consultas exitosas.
Los enlaces de paginación conservan filtros; Consultar reinicia la página.

## Presentación y accesibilidad

Se reutiliza templates/base.html y static/css/eva.css. Los estilos del módulo
están acotados a .historico. Filtros y tarjetas pasan a una columna en móvil;
la tabla tiene desplazamiento horizontal propio. Se conservan etiquetas,
encabezados, caption, foco visible, errores asociados y avisos role=alert/status.
No se depende exclusivamente del color. No se añadió una librería de gráficos.

JavaScript solo evita un segundo envío accidental y restaura el estado al volver
con el navegador. No realiza fetch, reintentos de escritura ni cálculos.

## Referencia Figma

Referencia: https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA

Las llamadas de sesión y metadatos del conector devolvieron Unknown tool. No fue
posible inspeccionar el archivo editable en esta sesión. Los node-id de histórico,
comparación, percepción y móvil permanecen SIN VERIFICAR. Se reutilizó la base
visual existente del repositorio. No se acredita el objetivo aproximado de 70 %.
La comparación requiere restablecer el acceso al conector o recibir exportaciones
autorizadas de los marcos correspondientes.


Las capturas del ensayo están enlazadas en entrega_web_bloque_6.md. Se revisaron
20 combinaciones de estado/tamaño en Chromium sin desbordamiento global, con
fixtures únicamente en el proceso de prueba. La comparación Figma sigue pendiente.


## Actualización de conexión con el dominio

Se verificó localmente la interfaz con el PR #44 en 6b79011, sin modificar el
contrato v1 ni copiar dominio a esta rama. La prueba del estado 503 simula ahora
la indisponibilidad de obtener_percepcion explícitamente, sin depender de una
implementación ausente. Tres recorridos HTTP/ORM adicionales y la suite conjunta
pasaron; resultados y bases exactas en entrega_web_bloque_6.md. La integración
global y la comparación Figma siguen pendientes.
