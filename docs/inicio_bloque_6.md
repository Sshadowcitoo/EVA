# Preparar la interfaz del histórico

## Acceso al proyecto

Repositorio: https://github.com/Sshadowcitoo/EVA

```powershell
git clone --branch base-historico-bloque-6 https://github.com/Sshadowcitoo/EVA.git
cd EVA
git switch -c interfaz-historico-bloque-6
```

Si se trabaja en una copia existente, conservar sus cambios locales y usar una
copia/worktree propia. No cambiar la rama de otro trabajo activo. Si GitHub solicita
acceso, usar la cuenta autorizada del proyecto o la copia ZIP adjunta, sin compartir
claves AWS ni datos de producción. El commit exacto de entrega acompaña al PR;
la base original integrada es main 55495b56251e85a11433e705b0c498f27958c718.

## Lectura inicial

1. AGENTS.md si está disponible, README.md y requirements.txt.
2. docs/contrato_bloque_6.md y apps/historico/contracts.py: nombres definitivos v1.
3. apps/historico/filtros.py, services.py y testing/fixtures.py.
4. apps/catalogo/permissions.py y context_processors.py: roles/navegación.
5. docs/figma_referencia.md y estilos/plantillas existentes.

EVA usa Django 5.2, plantillas Django y JavaScript, con catálogo/captura/análisis y
revisión ya integrados. Servicio tiene UUID e instantáneas de plato, porción y
componentes. Bandeja es reutilizable y no identifica una comida. Resultados de
análisis y decisiones de revisión son estados distintos. REAL/SIMULADO no se mezclan.
El piloto actual es ficticio y usa encebollado (yuca/pescado), seco de pollo
(arroz/pollo/maduro) y arroz con menestra y carne (arroz/menestra/carne/ensalada).

## Entrega de este trabajo

Implementar solo formularios, vistas, urls del módulo, plantillas, CSS/JS, adaptación
de Figma y pruebas web/HTTP. Archivos concretos y excepciones están en el contrato.
No crear modelos, migraciones, selectores ni otra fórmula de indicadores. El código
de producción llama services; los tests pueden sustituirlo por las fixtures.
Los servicios aún pendientes fallan explícitamente: implementar su estado 503
legible, sin fallback a datos falsos ni confirmación de guardado.

No modificar settings.py, urls globales, roles compartidos o navegación global en
paralelo. Describir los enlaces/includes necesarios en docs/entrega_web_bloque_6.md.
No cambiar el contrato unilateralmente: comunicar cualquier dato que falte antes.
No tocar los bloques 4 y 5 ni comenzar el 7 en el mismo PR.

## Verificación local

Usar Python/entorno virtual propio. requirements.txt declara las dependencias;
prepararlo según las autorizaciones de ese entorno, sin cambiar Python global ni
instalar un framework frontend. SQLite de desarrollo y fotos de prueba solamente.

```powershell
python manage.py check
python manage.py test apps.historico
python manage.py makemigrations --check --dry-run
```

Las pruebas de la interfaz pueden definir su ROOT_URLCONF para sus rutas nuevas;
el include global se añade al integrar la entrega. Ejecutar también las pruebas
frontend reales que se creen; no copiar un comando de éxito no ejecutado.

## Forma de entregar

Abrir un PR desde interfaz-historico-bloque-6 contra base-historico-bloque-6 si la
base sigue abierta; si ya está integrada, actualizarse y dirigirlo a main. No hacer
merge. Entregar commit/base, archivos, funciones consumidas, pruebas con sus
resultados, capturas móvil/escritorio, nodos Figma y pendientes explícitos.

Usar títulos y mensajes que describan el cambio, por ejemplo «Añade filtros y
pantallas del histórico». No añadir etiquetas de asistentes, numeraciones de IA o
atribuciones artificiales al trabajo, títulos, ramas o commits.
