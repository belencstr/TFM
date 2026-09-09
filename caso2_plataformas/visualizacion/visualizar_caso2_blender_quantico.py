r"""Visualización 3D Avanzada en Blender — Caso 2: QUBO Reducido 18x5 (Simulated Annealing).

Visualiza la solución obtenida mediante la formulación QUBO reducida resuelta con
Simulated Annealing clásico, utilizando el motor estético 2.5D procedural del Caso 2:
- Plataformas multicapa (losa superior biselada + cuerpo rocoso + ménsulas de apoyo).
- Checkpoints de aventurero (campamento Start y santuario rúnico Goal).
- Arcos parabólicos de salto calculados con física real de impulso y caída.
- Foso de lava incandescente inferior y fondo de caverna en perspectiva.
- Encuadre cinemático 2.5D adaptado a la cuadrícula 18x5.

EJECUCIÓN:
  blender -b -P caso2_plataformas/visualizacion/visualizar_caso2_blender_quantico.py
"""

from pathlib import Path
import os
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CASO2 = SCRIPT_DIR.parent

# Ruta por defecto al JSON de QUBO reducido
RUTA_JSON_QUBO = (
    BASE_CASO2
    / "cuantico"
    / "resultados"
    / "caso2_nivel_blender_qubo_reducido_18x5_20260903_180117.json"
)

# Establecer variable de entorno para que el visualizador unificado lo cargue
os.environ["CASO2_BLENDER_JSON"] = str(RUTA_JSON_QUBO)

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Importar y ejecutar el visualizador avanzado de plataformas
from visualizar_caso2_blender import construir_escena_caso2

if __name__ == "__main__":
    construir_escena_caso2()
