from .permissions import ADMINISTRACION, COCINA, REGISTRO, tiene_rol
from django.urls import NoReverseMatch, reverse


def roles_eva(request):
    """Navegación según roles; las vistas mantienen la autorización real."""
    consultar = tiene_rol(request.user, COCINA, ADMINISTRACION)
    def ruta(nombre):
        if consultar:
            try:
                return reverse(nombre)
            except NoReverseMatch:
                pass
        return None
    return {
        "puede_registrar": tiene_rol(request.user, REGISTRO),
        "puede_administrar_catalogo": tiene_rol(request.user, ADMINISTRACION),
        "puede_cocina": tiene_rol(request.user, COCINA),
        "historial_url": ruta("historico:lista"),
        "comparar_historico_url": ruta("historico:comparar"),
    }
