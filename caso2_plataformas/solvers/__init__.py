"""Solvers clásicos para el Caso 2 (Generación de niveles de plataformas).

La versión canónica y definitiva para el Caso 2 es `generador_plataformas_cpsat_v4`.
Las versiones v1, v2 y v3 se conservan por motivos de trazabilidad histórica.
"""

from .generador_plataformas_cpsat_v4 import (
    generar_ruta_segmentos_cpsat_v4,
    se_solapan,
)

__all__ = [
    "generar_ruta_segmentos_cpsat_v4",
    "se_solapan",
]
