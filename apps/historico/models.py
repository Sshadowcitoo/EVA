"""Percepción declarada: las correcciones conservan el registro anterior."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from .contracts import CATEGORIAS_PERCEPCION, MAX_MOTIVO


class PercepcionServicio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    servicio = models.ForeignKey('captura.Servicio', on_delete=models.PROTECT, related_name='percepciones')
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_PERCEPCION)
    motivo = models.CharField(max_length=MAX_MOTIVO, blank=True, default='')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='percepciones_registradas')
    fecha = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField()
    vigente = models.BooleanField(default=True)
    sustituye = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='correcciones')

    class Meta:
        ordering = ['servicio_id', 'version']
        default_permissions = ()  # Cambios solo mediante la operación auditada.
        constraints = [
            models.UniqueConstraint(fields=['servicio', 'version'], name='percepcion_version_unica'),
            models.UniqueConstraint(fields=['servicio'], condition=Q(vigente=True), name='percepcion_vigente_unica'),
            models.CheckConstraint(condition=Q(version__gt=0), name='percepcion_version_positiva'),
            models.CheckConstraint(condition=Q(categoria__in=[c for c, _ in CATEGORIAS_PERCEPCION]), name='percepcion_categoria_valida'),
            models.CheckConstraint(condition=~Q(categoria='NO_INFORMADO') | Q(motivo=''), name='percepcion_sin_respuesta_sin_motivo'),
        ]
