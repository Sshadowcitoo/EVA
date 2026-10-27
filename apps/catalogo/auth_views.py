from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.urls import reverse

from .permissions import ADMINISTRACION, COCINA, REGISTRO, roles_required, tiene_rol


def destino_por_rol(user):
    """Primera pantalla disponible según los roles del usuario."""
    if tiene_rol(user, REGISTRO):
        return reverse("captura:nueva_bandeja")
    if tiene_rol(user, ADMINISTRACION):
        return reverse("catalogo:platos")
    if tiene_rol(user, COCINA):
        return reverse("cuentas:cocina_pendiente")
    # Sin ningún rol de EVA: no tiene a dónde ir.
    return None


class EvaLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        if destino_por_rol(form.get_user()) is None:
            form.add_error(None, "Tu cuenta no tiene un rol asignado en EVA.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_default_redirect_url(self):
        return destino_por_rol(self.request.user)


@roles_required(COCINA)
def cocina_pendiente(request):
    return render(request, "cuentas/cocina_pendiente.html")