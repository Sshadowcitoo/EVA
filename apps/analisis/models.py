import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q

RETENCION_DIAS = 90  # máximo acordado; las máscaras heredan el plazo de la foto de origen


class AnalisisServicio(models.Model):
    """Análisis de un par servido/retorno con una versión de modelo y configuración."""

    class Origen(models.TextChoices):
        REAL = "REAL", "Real"
        SIMULADO = "SIMULADO", "Simulado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    servicio = models.ForeignKey(
        "captura.Servicio", on_delete=models.PROTECT, related_name="analisis"
    )
    foto_servido = models.ForeignKey(
        "captura.FotografiaServicio", on_delete=models.PROTECT, related_name="+"
    )
    foto_retorno = models.ForeignKey(
        "captura.FotografiaServicio", on_delete=models.PROTECT, related_name="+"
    )
    version_modelo = models.CharField(max_length=50)
    version_configuracion = models.CharField(max_length=50)
    origen = models.CharField(max_length=10, choices=Origen.choices)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="analisis_solicitados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    intento_vigente = models.ForeignKey(
        "analisis.IntentoAnalisis",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "foto_servido",
                    "foto_retorno",
                    "version_modelo",
                    "version_configuracion",
                    "origen",
                ],
                name="analisis_unico_por_par_y_version",
            )
        ]

    def __str__(self):
        return f"{self.servicio_id} - {self.version_modelo} ({self.origen})"


class IntentoAnalisis(models.Model):
    """Cada ejecución (o reintento) del análisis. Nunca se sobrescribe."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        COMPLETADO = "COMPLETADO", "Completado"
        FALLIDO = "FALLIDO", "Fallido"
        TIEMPO_AGOTADO = "TIEMPO_AGOTADO", "Tiempo agotado"

    class TipoError(models.TextChoices):
        ERROR_MOTOR = "ERROR_MOTOR", "Error del motor"
        RESPUESTA_INVALIDA = "RESPUESTA_INVALIDA", "Respuesta inválida"
        ERROR_ALMACENAMIENTO = "ERROR_ALMACENAMIENTO", "Error de almacenamiento"
        SIN_CONEXION = "SIN_CONEXION", "Sin conexión con el motor"
        OTRO = "OTRO", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analisis = models.ForeignKey(
        AnalisisServicio, on_delete=models.PROTECT, related_name="intentos"
    )
    numero = models.PositiveIntegerField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    comenzado_en = models.DateTimeField(null=True, blank=True)
    limite_en = models.DateTimeField(null=True, blank=True)
    finalizado_en = models.DateTimeField(null=True, blank=True)
    duracion_ms = models.PositiveIntegerField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True, default="")
    error_tipo = models.CharField(
        max_length=25, choices=TipoError.choices, blank=True, default=""
    )
    error_mensaje = models.TextField(blank=True, default="")  # sin secretos ni rutas

    class Meta:
        ordering = ["analisis", "numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["analisis", "numero"], name="intento_numero_unico"
            ),
            models.UniqueConstraint(
                fields=["analisis"],
                condition=Q(estado__in=["PENDIENTE", "EN_PROCESO"]),
                name="un_intento_activo_por_analisis",
            ),
        ]

    def __str__(self):
        return f"{self.analisis_id} #{self.numero} ({self.estado})"


class ResultadoComponente(models.Model):
    """Resultado por componente de la composición histórica del servicio."""

    class Estado(models.TextChoices):
        CONCLUYENTE = "CONCLUYENTE", "Concluyente"
        NO_CONCLUYENTE = "NO_CONCLUYENTE", "No concluyente"

    class Motivo(models.TextChoices):
        AREA_INICIAL_CERO = "AREA_INICIAL_CERO", "Área inicial cero"
        NO_COMPARABLE = "NO_COMPARABLE", "Fotos no comparables"
        OCULTACION = "OCULTACION", "Componente oculto"
        SIN_DETECCION = "SIN_DETECCION", "Sin detección"
        MAYOR_100 = "MAYOR_100", "Porcentaje superior a 100"
        SIN_CRITERIO = "SIN_CRITERIO", "Sin criterio de confianza configurado"
        BAJA_CONFIANZA = "BAJA_CONFIANZA", "Baja confianza"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intento = models.ForeignKey(
        IntentoAnalisis, on_delete=models.PROTECT, related_name="resultados"
    )
    servicio_componente = models.ForeignKey(
        "captura.ServicioComponente",
        on_delete=models.PROTECT,
        related_name="resultados_analisis",
    )
    area_inicial = models.FloatField(null=True, blank=True)
    area_residual = models.FloatField(null=True, blank=True)
    # Estimación visual de área, no gramos ni volumen. Puede superar 100: se conserva.
    porcentaje = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    confianza = models.FloatField(null=True, blank=True)
    criterio = models.CharField(max_length=100, blank=True, default="")
    estado = models.CharField(max_length=20, choices=Estado.choices)
    motivo = models.CharField(
        max_length=20, choices=Motivo.choices, blank=True, default=""
    )

    class Meta:
        ordering = ["intento", "servicio_componente__componente_nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["intento", "servicio_componente"],
                name="resultado_unico_por_intento_y_componente",
            ),
            models.CheckConstraint(
                condition=Q(estado="NO_CONCLUYENTE") | Q(porcentaje__isnull=False),
                name="concluyente_requiere_porcentaje",
            ),
            models.CheckConstraint(
                condition=Q(estado="CONCLUYENTE") | ~Q(motivo=""),
                name="no_concluyente_requiere_motivo",
            ),
            models.CheckConstraint(
                condition=Q(confianza__isnull=True)
                | (Q(confianza__gte=0) & Q(confianza__lte=1)),
                name="confianza_entre_0_y_1",
            ),
        ]

    def __str__(self):
        return f"{self.servicio_componente_id} - {self.estado}"


class ArtefactoAnalisis(models.Model):
    """Máscara privada por etapa y componente. El archivo vive en storage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resultado = models.ForeignKey(
        ResultadoComponente, on_delete=models.PROTECT, related_name="artefactos"
    )
    etapa = models.CharField(
        max_length=10,
        choices=[("SERVIDO", "Servido"), ("RETORNO", "Retorno")],
    )
    foto_padre = models.ForeignKey(
        "captura.FotografiaServicio",
        on_delete=models.PROTECT,
        related_name="mascaras",
    )
    backend = models.CharField(max_length=20, default="local")
    clave_archivo = models.CharField(max_length=255)
    hash_sha256 = models.CharField(max_length=64)
    ancho = models.PositiveIntegerField()
    alto = models.PositiveIntegerField()
    version_id = models.CharField(max_length=255, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    eliminado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["resultado", "etapa"],
                name="artefacto_unico_por_resultado_y_etapa",
            )
        ]

    @property
    def vence_en(self):
        """Hereda el plazo de la foto de origen, no 90 días desde el análisis."""
        return self.foto_padre.fecha + timedelta(days=RETENCION_DIAS)

    def __str__(self):
        return f"{self.resultado_id} - {self.etapa}"