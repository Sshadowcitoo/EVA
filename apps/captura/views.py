from django.shortcuts import get_object_or_404, redirect, render

from .forms import ServicioForm
from .models import Servicio

def nueva_bandeja(request):
    if request.method == "POST":
        form = ServicioForm(request.POST)
        if form.is_valid():
            servicio = form.save()
            return redirect("captura:confirmacion", pk=servicio.pk)
    
    else:
        form = ServicioForm()

    return render(request, "captura/nueva_bandeja.html", {"form":form})

def confirmacion(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    return render(request,"captura/confirmacion.html", {"servicio": servicio})

# Create your views here.
