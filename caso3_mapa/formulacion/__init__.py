"""Formulaciones QUBO para el Caso 3 (Mapa de mazmorra 2D).

Módulos canónicos:
- `qubo_caso3_integrado`: Formulación integrada estándar de 96 variables (Geometría + Ruta embebida).
- `qubo_caso3_completo`: Formulación extendida de 117 variables (Geometría + Ruta + Gameplay + Rama).
- `qubo_caso3`: Definiciones base de la cuadrícula, zonas, conectividad y modelo desacoplado.
"""

from .qubo_caso3 import construir_qubo_geometria
from .qubo_caso3_integrado import construir_qubo_integrado
from .qubo_caso3_completo import construir_qubo_completo

__all__ = [
    "construir_qubo_geometria",
    "construir_qubo_integrado",
    "construir_qubo_completo",
]
