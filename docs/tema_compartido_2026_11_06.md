# Extensión del sistema visual verde pastel

Base: main con los PR #65 (Indicadores) y #66 (prueba de captura) integrados.

## Alcance

El tema de Indicadores se comparte desde base.html y desde el acceso, que tiene
plantilla independiente. Se conservan las composiciones específicas de cada
recorrido; no se afirma equivalencia exacta con todos los marcos de Figma.

Se aplican fondo verde suave, superficies teñidas, tipografía oscura, acciones
verdes, foco visible y componentes comunes en acceso, Registro, captura, QR,
gestión, catálogo, Cocina, revisión, histórico, comparación, percepción,
recomendaciones y demostración. Indicadores mantiene su cuadrícula y agregaciones.

Se reutiliza la navegación de captura por permisos en las bases de los módulos.
Se retira de Catálogo el anuncio obsoleto «Recomendación: Pendiente», ya que existe
el acceso funcional a Recomendaciones. La sección de análisis permanece marcada
al abrir su revisión. No se alteran rutas ni permisos del servidor.

## Preservación de significado

Errores y acciones de anulación conservan rojo; avisos y simulaciones conservan
ámbar. Los botones deshabilitados siguen diferenciados. Las máscaras y sus
leyendas mantienen sus colores y las fotografías no se tiñen. Los QR conservan
su fondo blanco para facilitar su lectura.

No se cambian criterios, contratos, reglas de análisis, estados ni datos. No se
instalan dependencias. El acceso móvil reduce el espacio de presentación para
facilitar llegar al formulario.

## Verificación

- Suite completa: 583 pruebas Django ejecutadas, 580 aprobadas y 3 omitidas por
  el paquete privado ONNX. Sin fallos.
- Comprobación final de las plantillas afectadas: 95 pruebas aprobadas; 46 pruebas
  frontend aprobadas y migraciones sin cambios.
- Revisión en navegador con una base local aislada y cuentas de QA: acceso,
  registro, búsqueda inválida, catálogo, edición, gestión de bandejas, demostración
  de recomendaciones y cola vacía de Cocina.
- Comprobados acceso a 1440 x 900 y 390 x 844, catálogo móvil a 390 px y formularios
  y Cocina en escritorio de 1280 px. El menú móvil abre y permite cerrar sesión.
- En la comprobación geométrica de acceso no hubo desborde horizontal. No equivale
  a una auditoría de accesibilidad completa ni a comprobar todos los estados a
  todas las resoluciones.
- Se conserva la prueba física de QR y cámara documentada en el cierre de QA. Esta
  entrega cambia presentación; su verificación posterior no reemplaza esa prueba.

## Seguimiento

Mantener la revisión por recorrido de variantes Figma y estados particulares.
La extensión global de estilos no certifica un porcentaje de parecido ni cambia
la condición de demostración controlada del modelo visual.
