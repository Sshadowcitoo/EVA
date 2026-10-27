from django.contrib.auth.views import LoginView
from django.urls import reverse

from .permissions import ADMINISTRACION, REGISTRO, tiene_rol

def destino_por_rol(user):
    if tiene_rol(user, REGISTRO):
        return reverse("captura:nueva_bandeja")
    if tiene_rol(user, ADMINISTRACION)
        return reverse("catalogo:platos")
    #cocina o sin roll:  en este bolque todavia no tienen pantallas.
    return None

class EvaLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        #la contrasena ya es correcta aqui: falta ver si tiene a donde ir.
        if destino_por_rol(form.get_user()) is None
            form.add_error(
                None, "Tu cuenta todavia no tiene pantallas disponibles en EVA."
            )
            return self.form_invalid(form)
        return super().form_valid(form)

def get_default_redirect_url(self):
    # se usa cuando la url no trae un ?next= valido
    return destino_por_rol(self.request.user)