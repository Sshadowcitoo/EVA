# Bloque inicial: base de César

> Documento histórico de la entrega de César. En `integracion-bloque-inicial`
> ya se conectaron los modelos de Isaac, vistas de Lino y pantallas de Jean;
> las referencias siguientes a rutas vacías, sesiones ausentes y captura sin
> permisos describen la base original, no el estado integrado. Consultar el
> README de la raíz y las pruebas de integración para el estado vigente.

## Alcance de esta entrega

Se registra `apps.catalogo.apps.CatalogoConfig` y el namespace `catalogo` bajo
`/catalogo/`. `apps/catalogo/urls.py` es un punto de integración vacío que Lino
completará. No se crean modelos de Isaac ni pantallas de Jean.

Se conservan UUID, fecha, opciones y registros anteriores de captura. Esta
entrega no ejecuta migraciones sobre la base del equipo ni reinterpreta sus datos.
Las vistas actuales de captura todavía son las del avance y **no están protegidas
por estos helpers**: Lino debe conectar los controles al implementar las sesiones.
No presentar esta base como un control de acceso completo ni desplegarla como tal.

## Acuerdos ya definidos en la planificación

- Usar autenticación estándar de Django y sus grupos; sin usuario personalizado.
- Nombres exactos: `Registro`, `Cocina`, `Administración`.
- Sin herencia de roles. Quien cubre dos funciones recibe ambos grupos.
- `is_staff` solo habilita lo que corresponda en Django Admin; no concede un rol.
- El superusuario activo conserva acceso técnico extraordinario. No usarlo para
  probar roles ni como cuenta operativa habitual. Un usuario inactivo se deniega.
- Administración gestiona catálogo; desactiva en lugar de borrar registros usados.
- Los datos históricos de servicios no cambian al editar el catálogo.
- El arroz se comparte entre seco de pollo y arroz con menestra y carne.
- Encebollado: yuca y pescado; seco: arroz, pollo y maduro; arroz con menestra y
  carne: arroz, menestra, carne y ensalada. El caldo queda fuera de medición.

## Permisos de este bloque

| Rol | Permisos Django previstos |
| --- | --- |
| Registro | `add_servicio`, `view_servicio`; lectura del catálogo necesaria para registrar |
| Cocina | Grupo preparado, sin permisos de captura o edición de catálogo |
| Administración | `view`, `add`, `change` de modelos del catálogo acordados; sin `delete` |

`configurar_roles` resuelve permisos ya creados por Django tras migrar. Los
permisos de modelos todavía inexistentes se reportan como pendientes y no se
inventan. Repetir el comando después de integrar y migrar los modelos de Isaac.
La matriz exacta vive en `apps/catalogo/permissions.py`: los nombres de modelos
deben coincidir con el contrato definitivo. Los demás módulos añadirán sus
permisos cuando se implementen, no de forma anticipada.

El comando sincroniza permisos de `captura` y `catalogo` en esos tres grupos;
retira permisos extra de esas aplicaciones. Conserva usuarios, membresías,
permisos directos y permisos de otras aplicaciones. No crea cuentas ni contraseñas.
No reutilizar estos grupos para excepciones manuales dentro de esos dos módulos.

## Uso tras aplicar las migraciones correspondientes

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py configurar_roles
```

Asignar usuarios a grupos mediante administración local autorizada; ningún usuario
recibe grupos automáticamente. No guardar contraseñas o credenciales en Git.

Para vistas de función:

```python
from apps.catalogo.permissions import ADMINISTRACION, roles_required

@roles_required(ADMINISTRACION)
def administrar_catalogo(request):
    ...
```

Para vistas de clase, poner `RolesRequiredMixin` antes de `View` y declarar
`allowed_roles = (ADMINISTRACION,)`. Anónimos redirigen al login; autenticados sin
rol reciben 403. Aplicar en GET y POST; ocultar botones no protege endpoints.
Para DRF se implementará el adaptador correspondiente cuando exista esa API;
no aplicar automáticamente este decorador de Django sobre vistas DRF.

Esto controla acciones por rol, no propiedad de objetos. `view_servicio` no
autoriza revelar cualquier UUID: Lino debe filtrar objetos y validar servicio,
etapa y contexto conforme al contrato que se confirme para la captura.

## Sesiones y rutas

`LOGIN_URL` apunta a `/cuentas/login/`; `LOGIN_REDIRECT_URL` a
`captura:nueva_bandeja`, y logout vuelve al login. La ruta de sesión todavía
no existe: Lino implementará sus vistas y César conectará sus rutas globales
cuando el módulo esté disponible. No añadir includes de módulos inexistentes.

Lino debe sustituir el destino de login para usuarios sin rol Registro por una
página permitida según sus roles. El valor actual sirve al recorrido de registro
existente y no representa una política de navegación final para todos los roles.

## Decisiones de datos que siguen necesitando ratificación

La captura compartida por el compañero no incluye la lista completa de
«Decisiones que debe ratificar César». No se aprueba esa sección a ciegas.
Antes de crear migraciones se debe confirmar:

1. Campos y restricciones de `Plato`, `Componente`, `PlatoComponente`,
   `TipoPorcion` y el contexto realmente requerido.
2. Instantánea o versionado de la composición en cada servicio y su contrato de alta.
3. Migración de servicios antiguos: preservar sus etiquetas sin mapear
   `arroz_con_pollo` a `seco_de_pollo` ni inventar equivalencias.
4. Política de acceso a objetos por Registro y destino de cada rol tras login.

Esta base no toma esas decisiones sobre arquitectura o datos en lugar del usuario.

## Reparto y entrega

- César: configuración, registro de aplicación, permisos, comando de roles,
  contratos y revisión/integración.
- Isaac: modelos, nuevas migraciones y carga de catálogo.
- Lino: sesiones, formularios, vistas y rutas. Completa `catalogo/urls.py` después
  de integrar esta base, sin volver a crear `CatalogoConfig` ni tocar settings.
- Jean: plantillas y CSS siguiendo Figma.
- Eduardo: ampliar pruebas funcionales y documentación del bloque completo.

Cada integrante abre su Pull Request; solo César integra. Este trabajo no hace
commit, push ni merge y no sustituye el trabajo de los compañeros.

## Verificación mínima

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test apps.catalogo apps.captura
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Las pruebas de catálogo verifican roles, GET/POST, denegación, repetibilidad y
preservación de membresías. Las de captura conservan las garantías del avance.
No hacen falta nuevas dependencias ni cambios en AWS para esta entrega.
