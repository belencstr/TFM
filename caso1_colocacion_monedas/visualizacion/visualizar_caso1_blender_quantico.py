r"""Visualización 3D Avanzada en Blender — Caso 1: QUBO / QAOA Mínimo (4 candidatas, k=2).

Visualiza la solución óptima obtenida mediante la formulación cuántica (QAOA / QUBO)
sobre la cuadrícula mínima del Caso 1, utilizando el motor estético procedural de dioramas:
- Zócalo subterráneo de cantería y losas biseladas.
- Muros de piedra con antorchas de hierro forjado iluminadas.
- Monedas de oro 3D reflectantes (PBR Metallic 0.95) en las coordenadas óptimas (C002 y C004).
- Halos rúnicos circulares de cobertura sobre el suelo.
- Portales de spawn (Start) y meta (Goal).
- Encuadre cinemático de estudio e iluminación 3-point.

EJECUCIÓN DIRECTA EN BLENDER:
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P caso1_colocacion_monedas/visualizacion/visualizar_caso1_blender_quantico.py
"""

from pathlib import Path
import os
import shutil
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CASO1 = SCRIPT_DIR.parent

# Ruta por defecto al JSON canónico de QUBO / QAOA
RUTA_JSON_QUBO = (
    BASE_CASO1
    / "resultados"
    / "caso1_nivel_blender_qubo_mapa_min_k2.json"
)

# Establecer variable de entorno para que el visualizador lo cargue
os.environ["CASO1_BLENDER_JSON"] = str(RUTA_JSON_QUBO)

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualizar_caso1_blender import construir_escena_caso1

if __name__ == "__main__":
    construir_escena_caso1()

    # Asegurar copia con nomenclatura qubo para simetría con Caso 2
    fig_dir = BASE_CASO1 / "figuras"
    orig = fig_dir / "caso1_blender_render_mapa_min_k2.png"
    dest = fig_dir / "caso1_blender_qubo_render_mapa_min_k2.png"
    if orig.exists():
        try:
            shutil.copy2(orig, dest)
            print(f"Copia canónica cuántica generada: {dest}")
        except Exception as e:
            print(f"Nota: No se pudo copiar {orig} a {dest}: {e}")
