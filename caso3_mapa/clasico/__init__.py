"""Solvers y modelos clásicos mediante CP-SAT para el Caso 3 (Mapa 2D).

Módulos canónicos:
- `caso3_cpsat_core`: Baseline clásico exacto equivalente al modelo cuántico integrado.
- `caso3_cpsat_v3`: Generador demostrador completo (incluye gameplay y ramas).

Las versiones `caso3_cpsat` (v1) y `caso3_cpsat_v2` (v2) se conservan para trazabilidad histórica.
"""

from .caso3_cpsat_core import solve_case3_core
from .caso3_cpsat_v3 import solve_case3

__all__ = [
    "solve_case3_core",
    "solve_case3",
]
