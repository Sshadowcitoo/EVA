# Inventario reproducible y propuesta de carga aislada

Base `c3404ff`. Este PR entrega un inventario determinista, previsualización y pruebas de consistencia. El manifiesto es un insumo de planificación, sin escritura en Django o AWS.

```sh
python ops/presentacion/planificar.py --lote exposicion-eva
python ops/presentacion/planificar.py --lote exposicion-eva --salida /ruta/local/exposicion-eva.json
python -m unittest ops.presentacion.test_planificar
```

El identificador del lote genera UUID reproducibles y separados por lote. Repetir el comando con el mismo archivo conserva sus bytes y un archivo distinto en el destino se rechaza. La previsualización muestra cantidades, destino y ausencia de persistencia en base.

## Inventario y recorrido esperado

| Elemento | Plan |
| --- | --- |
| Servicios, fotos y bandejas | 288 servicios en cuatro semanas, 288 pares ilustrativos y 6 bandejas reutilizadas sin solapamiento. |
| Catálogo y contexto | Tres platos, siete componentes y porciones estándar/reducida. Sede principal, modalidad mesa, misma franja de servido 12:00–13:00. Lotes separados por fecha y plato. |
| Grupos | Seis combinaciones plato/porción. Cada combinación incluye ocho días en cuatro semanas. Cinco entradas sintéticas con mediciones y una sin análisis por fecha. Los componentes permanecen separados. |
| Comparación | Semanas 1–2 frente a 3–4 para un mismo grupo exacto. En cada mitad, cuatro días con cinco mediciones y cuatro lotes. 20 de 24 casos planificados con mediciones por grupo, 83,33 % bajo los supuestos del ensayo. |
| Historia para presentar | Encebollado con sobrantes visuales bajos y ceros sintéticos, seco de pollo alto y menestra con señal intermedia en el grupo de arroz. Cambios semanales sin cifras en plantillas. 240 ejemplos con mediciones y 48 sin análisis. |
| Revisión y decisiones | Revisiones y percepciones de ejemplo. Mantener yuca, revisar porción de pollo y realizar prueba controlada para menestra, evaluada contra el segundo periodo. |

Las tres pruebas verifican identidad, no reclasificación, reutilización, lotes, bloques completos, cobertura y presencia de las tres categorías previstas con los valores de la propuesta experimental vigente. Los resultados se derivan del manifiesto, sin ejecutar los selectores de Django. El lote no integra la huella de contexto; sí aporta diversidad de preparaciones.

## Carga local aprobada

El lote utiliza 576 láminas ilustrativas sin fotos reales, 240 análisis simulados, 240 revisiones de ejemplo y 48 pares sin análisis. La carga genera recomendaciones para yuca, pollo y menestra con los servicios de EVA, registra decisiones justificadas y evalúa una prueba controlada de menestra.

Prepara una carpeta local nueva y un entorno virtual. Ejecuta los comandos desde la raíz del repositorio.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings_presentacion
export EVA_PRESENTACION_LOTE=exposicion-eva
export EVA_PRESENTACION_RAIZ="$(mktemp -d)"
printf '%s\n' "$EVA_PRESENTACION_LOTE" > "$EVA_PRESENTACION_RAIZ/.eva-presentacion"
python manage.py migrate
python manage.py configurar_roles
python manage.py cargar_catalogo_demo
python manage.py shell -c "from apps.catalogo.models import TipoPorcion; TipoPorcion.objects.get_or_create(codigo='reducida', defaults={'nombre':'Reducida'})"
```

Crea tres cuentas locales en esa base y asígnales respectivamente Registro, Cocina y Administración mediante los grupos Django. Puedes crear una cuenta técnica con `python manage.py createsuperuser` para preparar esas cuentas desde el administrador local. La carga exige las cuentas existentes y conserva sus permisos y contraseñas.

```sh
python manage.py cargar_presentacion
python manage.py cargar_presentacion --aplicar --confirmar exposicion-eva \
  --registro registro-local --cocina cocina-local --administracion admin-local
python manage.py runserver 127.0.0.1:8000
```

- Indicadores e Histórico: abre `/historico/?desde=2026-10-05&hasta=2026-11-01&plato=seco_de_pollo&componente=pollo&porcion=estandar`. El gráfico recoge cuatro semanas. Elige encebollado y yuca para ver ceros confirmados del ejemplo.
- Comparar: usa 5–18 y 19 de octubre–1 de noviembre, arroz con menestra y carne, menestra, porción estándar. Mantén la misma sede, modalidad, franja y versión.
- Recomendaciones: entra como Administración o Cocina y abre los casos generados. La prueba evaluada está en el caso de menestra.
- Cocina: entra con ese rol y abre un análisis simulado para ver sus láminas, componentes y revisión de ejemplo. Registro puede consultar la percepción en los servicios que tengan una respuesta.

La versión de criterios de presentación usa el perfil experimental únicamente dentro de este proceso local. El modo conserva el origen `SIMULADO` y el selector operativo sigue excluyéndolo. Las láminas son ilustraciones genéricas y la carga no crea máscaras ni ejecuta inferencias.

La previsualización es el modo por defecto. Repetir la carga conserva el lote existente. Para retirarlo, cierra el servidor y ejecuta:

```sh
python manage.py cargar_presentacion --retirar --confirmar exposicion-eva
```

El recibo local conserva los identificadores de las filas, las claves y los hashes. Una dependencia ajena que protege una fila o una lámina modificada detiene la retirada. Si se interrumpe el borrado de láminas después de retirar las filas, repite el comando para terminar la limpieza. Las cuentas y el catálogo de arranque se conservan.

## Verificación

La suite Django ejecutó 593 pruebas, con tres omisiones correspondientes a la paridad privada del modelo. El flujo de carga y retirada se probó con ORM, incluido un archivo modificado que debe impedir la retirada, cuentas conservadas y una bandeja ajena intacta. En Django y Chromium se revisaron Indicadores, Comparar, Recomendaciones, la prueba controlada, Revisión de Cocina y Percepción a 1440×900 y 390×844. El grupo exacto de pollo tiene 40 servicios aptos en cuatro semanas. La comparación de menestra produjo diferencias a partir de dos periodos compatibles.

Las capturas corresponden al entorno local. El escaneo físico, el emparejamiento por teléfono y la inferencia con fotos reales requieren otro entorno de comprobación.
