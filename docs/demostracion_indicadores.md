# Demostración visual de Indicadores

Ruta protegida: `/historico/demostracion/`, roles Cocina o Administración.
Se abre desde «Ver interfaz con datos de demostración» en el histórico real.

La vista genera catorce servicios ficticios en memoria: seco de pollo con arroz y
pollo, arroz con menestra y carne con arroz, menestra, carne y ensalada, y
encebollado con yuca y pescado. Incluye una porción reducida identificada como
opción de ejemplo. No consulta el catálogo ni crea registros operativos.

Los datos usan origen SIMULADO y claves con prefijo demo. La cabecera, el aviso
y el título distinguen esta sección del histórico real. Se emplean los mismos
componentes y funciones de agregación para mostrar la interfaz, pero estos valores
no son inferencia, evidencia validada ni aprobación de criterios. El contexto
compatible se supone únicamente para los ejemplos. Las recomendaciones enlazadas
son también la demostración separada.

Escenarios disponibles:
- Con valores de demostración: serie de cuatro semanas, un hueco sin evidencia,
  ceros individuales confirmados en el ejemplo y perfiles separados por grupo.
- Sin evidencia apta: valores ausentes y gráficos sin datos, sin inventar ceros.

La vista solo admite GET, conserva los permisos del histórico y valida página y
escenario. Los datos permanecen fuera de la base, las fotos y el almacenamiento.
No se importan fixtures de tests desde la aplicación.

Verificación: 78 pruebas del histórico aprobadas. Tras simplificar avisos y etiquetas,
27 pruebas de demostración e interfaz aprobadas. Las pruebas cubren permisos,
método, valores y grupos, entradas inválidas, falta de evidencia y ausencia de
consultas al selector real o escrituras de servicios y fotografías. La construcción
en memoria se verifica también mediante SimpleTestCase, que prohíbe consultas ORM.

Revisión en navegador local aislado: tres puntos semanales, un solo segmento por
el hueco intermedio y seis barras del grupo inicial. Los ejemplos no se sembraron
en la base de AWS ni cambian el histórico real.
