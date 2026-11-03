"""Snapshots y auditoría: ninguna decisión modifica el catálogo."""
import uuid
from django.conf import settings
from django.db import models
from .contracts import CATEGORIAS, DECISIONES


class EvaluacionEvidencia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    huella = models.CharField(max_length=64, unique=True)
    snapshot = models.JSONField()
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_permissions = ()


class Recomendacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluacion = models.OneToOneField(EvaluacionEvidencia, on_delete=models.PROTECT, related_name='recomendacion')
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    explicacion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=0)

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(categoria__in=[c for c, _ in CATEGORIAS]), name='recomendacion_categoria_valida')]


class DecisionRecomendacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recomendacion = models.ForeignKey(Recomendacion, on_delete=models.PROTECT, related_name='decisiones')
    decision = models.CharField(max_length=20, choices=DECISIONES)
    justificacion = models.CharField(max_length=1000)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField()
    sustituye = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(fields=['recomendacion', 'version'], name='decision_recomendacion_version_unica'),
            models.CheckConstraint(condition=models.Q(version__gt=0), name='decision_recomendacion_version_positiva'),
            models.CheckConstraint(condition=models.Q(decision__in=[c for c, _ in DECISIONES]), name='decision_recomendacion_valida'),
            models.CheckConstraint(condition=~models.Q(justificacion=''), name='decision_recomendacion_justificada'),
        ]


class PruebaControlada(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recomendacion = models.ForeignKey(Recomendacion, on_delete=models.PROTECT, related_name='pruebas')
    aceptacion = models.ForeignKey(DecisionRecomendacion, on_delete=models.PROTECT)
    huella = models.CharField(max_length=64, unique=True)
    cambio = models.CharField(max_length=1000)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    periodos = models.JSONField()
    fecha = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=0)

    class Meta:
        default_permissions = ()


class EvaluacionPrueba(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prueba = models.ForeignKey(PruebaControlada, on_delete=models.PROTECT, related_name='evaluaciones')
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(fields=['prueba', 'version'], name='evaluacion_prueba_version_unica'),
            models.CheckConstraint(condition=models.Q(version__gt=0), name='evaluacion_prueba_version_positiva'),
        ]
