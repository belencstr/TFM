"""Formulaciones QUBO para el Caso 2 (Generación de niveles de plataformas).

La versión canónica equivalente al modelo CP-SAT v4 es `qubo_caso2_equivalente`.
Las formulaciones reducidas o preliminares se conservan para estudios comparativos y barridos TTS.
"""

from .qubo_caso2_equivalente import (
    construir_qubo_equivalente,
    muestra_desde_ruta_clasica,
    energia_qubo,
    objetivo_vertical,
)

__all__ = [
    "construir_qubo_equivalente",
    "muestra_desde_ruta_clasica",
    "energia_qubo",
    "objetivo_vertical",
]
