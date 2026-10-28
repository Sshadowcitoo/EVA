from .permissions import ADMINISTRACION, COCINA, REGISTRO, tiene_rol


def roles_eva(request):
    """Navegación según roles; las vistas mantienen la autorización real."""
    return {
        "puede_registrar": tiene_rol(request.user, REGISTRO),
        "puede_administrar_catalogo": tiene_rol(request.user, ADMINISTRACION),
        "puede_cocina": tiene_rol(request.user, COCINA),
    }
