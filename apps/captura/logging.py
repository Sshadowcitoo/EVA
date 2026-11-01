"""Evita registrar el secreto temporal incluso en el servidor de desarrollo."""
import logging
import re


class OcultarTokenCaptura(logging.Filter):
    def filter(self, record):
        mensaje = record.getMessage()
        record.msg = re.sub(r"(token(?:=|%3[dD]))[^&\s\"<>]+", r"\1[redacted]", mensaje)
        record.args = ()
        return True
