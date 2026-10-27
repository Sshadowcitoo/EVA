from django.contrib.auth.views import LogoutView
from django.urls import path

from .auth_views import EvaLoginView

app_name = "cuentas"

urlpatterns = [
    path("login/", EvaLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]