"""Traduce únicamente la contención conocida de SQLite al contrato de dominio."""
from functools import wraps
import sqlite3

from django.core.exceptions import ValidationError
from django.db import OperationalError, connection


def rechazar_bloqueo_sqlite(operacion):
    @wraps(operacion)
    def ejecutar(*args, **kwargs):
        try:
            return operacion(*args, **kwargs)
        except OperationalError as exc:
            codigo = getattr(exc.__cause__, "sqlite_errorcode", None)
            if connection.vendor != "sqlite" or codigo is None or (codigo & 0xFF) not in (
                sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED,
            ):
                raise
            # La operación ya salió de atomic: no se consulta ni se reintenta
            # una transacción rota y se conserva el rollback de todas sus filas.
            raise ValidationError(
                "Hay otro registro en curso. Vuelve a intentarlo y comprueba la bandeja."
            ) from exc
    return ejecutar
