"""Roles del producto: sin jerarquía implícita ni acceso por is_staff."""

from functools import wraps

from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied


REGISTRO = "Registro"
COCINA = "Cocina"
ADMINISTRACION = "Administración"
ROLES = (REGISTRO, COCINA, ADMINISTRACION)

# Permisos Django disponibles en este bloque. Los modelos futuros no se inventan:
# configurar_roles informará de los ausentes y se repetirá tras sus migraciones.
PERMISOS_POR_ROL = {
    REGISTRO: (
        "captura.add_servicio",
        "captura.view_servicio",
        "catalogo.view_plato",
        "catalogo.view_componente",
        "catalogo.view_platocomponente",
        "catalogo.view_tipoporcion",
        "catalogo.view_contexto",
    ),
    COCINA: (),
    ADMINISTRACION: tuple(
        f"catalogo.{accion}_{modelo}"
        for modelo in ("plato", "componente", "platocomponente", "tipoporcion", "contexto")
        for accion in ("view", "add", "change")
    ),
}


def _validar_roles(roles):
    if not roles or any(rol not in ROLES for rol in roles):
        raise ImproperlyConfigured("Especifica al menos un rol válido de EVA.")


def tiene_rol(user, *roles):
    """Autoriza cualquier rol solicitado, sin ampliar acceso por ser staff."""
    _validar_roles(roles)
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def roles_required(*roles):
    """Redirige anónimos al login y devuelve 403 a usuarios sin rol autorizado."""
    _validar_roles(roles)

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
            if not tiene_rol(request.user, *roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


class RolesRequiredMixin(AccessMixin):
    """Colocar antes de View; declarar allowed_roles como tupla de roles EVA."""

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        _validar_roles(self.allowed_roles)
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not tiene_rol(request.user, *self.allowed_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
