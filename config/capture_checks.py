"""Valida contratos de captura sin acceder a AWS ni crear archivos."""

from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, register


@register()
def check_capture_configuration(app_configs, **kwargs):
    errors = []
    backend = settings.EVA_STORAGE_BACKEND
    if backend not in ("local", "s3"):
        errors.append(Error("EVA_STORAGE_BACKEND debe ser local o s3.", id="captura.E001"))

    if backend == "local":
        root = Path(settings.EVA_CAPTURE_PRIVATE_ROOT)
        public_roots = [settings.BASE_DIR, *settings.STATICFILES_DIRS]
        if settings.STATIC_ROOT:
            public_roots.append(settings.STATIC_ROOT)
        if not root.is_absolute() or any(
            root.resolve().is_relative_to(Path(path).resolve()) for path in public_roots
        ):
            errors.append(Error(
                "EVA_CAPTURE_PRIVATE_ROOT debe ser absoluto y estar fuera del checkout y estáticos.",
                id="captura.E002",
            ))

    if backend == "s3":
        if not settings.EVA_S3_BUCKET.strip() or not settings.EVA_S3_REGION.strip():
            errors.append(Error("S3 requiere EVA_S3_BUCKET y EVA_S3_REGION.", id="captura.E003"))
        prefix = settings.EVA_S3_PREFIX
        if not prefix or prefix.startswith("/") or "\\" in prefix or any(
            part in (".", "..", "") for part in prefix.rstrip("/").split("/")
        ):
            errors.append(Error("EVA_S3_PREFIX debe ser un prefijo relativo sin traversal.", id="captura.E004"))

    base_url = settings.EVA_CAPTURE_BASE_URL
    if base_url:
        try:
            parsed = urlsplit(base_url)
            valid = (
                parsed.scheme == "https" and parsed.hostname
                and parsed.hostname not in ("localhost", "127.0.0.1", "::1")
                and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment
                and parsed.path in ("", "/")
            )
            parsed.port  # Valida también puertos mal formados.
        except ValueError:
            valid = False
        if not valid:
            errors.append(Error(
                "EVA_CAPTURE_BASE_URL debe ser un origen HTTPS accesible al teléfono, sin credenciales.",
                id="captura.E005",
            ))

    return errors
