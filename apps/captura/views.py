from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalogo.permissions import REGISTRO, roles_required

from .forms import ServicioForm
from .models import Servicio


@roles_required(REGISTRO)
def nueva_bandeja(request):
    if request.method == "POST":
        form = ServicioForm(request.POST)
        if form.is_valid():
            try:

                servicio = Servicio.registrar(
                    plato=form.cleaned_data["plato"],
                    porcion=form.cleaned_data["tipo_porcion"],
                    usuario=request.user,
                )
            except ValidationError as error:
                # Por si el plato se desactivó justo entre la validación
                # y el guardado: se muestra el error, no se guarda nada.
                form.add_error(None, error)
            else:
                return redirect("captura:confirmacion", pk=servicio.pk)
    else:
        form = ServicioForm()

    return render(request, "captura/nueva_bandeja.html", {"form": form})


@roles_required(REGISTRO)
def confirmacion(request, pk):
    # Solo el usuario que creó el servicio puede ver su confirmación.
    servicio = get_object_or_404(Servicio, pk=pk, creado_por=request.user)
    return render(request, "captura/confirmacion.html", {"servicio": servicio})