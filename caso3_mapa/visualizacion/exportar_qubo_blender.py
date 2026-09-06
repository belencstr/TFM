"""Exporta la mejor solución válida del QUBO Integrado a JSON para Blender.

Genera una representación 3D del modelo Core resuelto mediante Simulated Annealing:
- Celdas de suelo y muros agrupadas por coherencia espacial (Ising).
- START en (0,0) y GOAL en (5,7).
- Ruta principal 3D extraída directamente de las variables binarias q_{t, c}.
"""

from datetime import datetime
from pathlib import Path
import json
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3 import ROWS, COLS, START, GOAL
from formulacion.qubo_caso3_integrado import construir_qubo_integrado
from solvers.simulated_annealing_caso3 import resolver_qubo_sa

EXPORT_DIR = BASE_DIR / "experimentos" / "resultados"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def exportar_qubo_para_blender(seed=42, num_reads=100, num_sweeps=1500):
    print(f"Resolviendo QUBO Integrado con SA (semilla={seed})...")
    qubo = construir_qubo_integrado()
    res = resolver_qubo_sa(
        qubo,
        num_reads=num_reads,
        num_sweeps=num_sweeps,
        seed=seed,
        es_modelo_integrado=True,
    )

    mejor_valida = res["mejor_muestra_valida"]
    if mejor_valida is None:
        raise RuntimeError("No se encontró ninguna solución válida en las muestras de SA.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    open_cells = mejor_valida["open_cells"]
    ruta_q = mejor_valida["ruta_q"]
    path_set = set(ruta_q)

    cells_data = []
    for r in range(ROWS):
        for c in range(COLS):
            cell = (r, c)
            is_open = cell in open_cells

            if cell == START:
                cell_type = "START"
            elif cell == GOAL:
                cell_type = "GOAL"
            elif cell in path_set:
                cell_type = "PATH"
            elif is_open:
                cell_type = "FLOOR"
            else:
                cell_type = "WALL"

            cells_data.append({
                "row": r,
                "col": c,
                "type": cell_type,
                "is_open": is_open,
                "is_path": cell in path_set,
                "is_branch": False,
                "is_reward": False,
                "is_enemy": False,
            })

    data = {
        "metadata": {
            "caso": 3,
            "titulo": "Mapa 2D generado con QUBO Integrado + Simulated Annealing",
            "solver": "QUBO Integrado (96 vars) + Simulated Annealing (P=100)",
            "status": "VALID_SAMPLE",
            "seed": seed,
            "timestamp": timestamp,
            "solve_time_seconds": round(res["tiempo_segundos"], 6),
            "objective_value": mejor_valida["fronteras"],
            "grid_rows": ROWS,
            "grid_cols": COLS,
            "total_cells": ROWS * COLS,
            "floor_cells_count": len(open_cells),
            "wall_cells_count": ROWS * COLS - len(open_cells),
            "components_count": mejor_valida["componentes"],
            "bfs_path_length": mejor_valida["longitud_bfs"],
            "witness_path_length": len(ruta_q) - 1,
            "es_ruta_q_valida": mejor_valida["es_ruta_q_valida"],
            "tts_99_ms": round(res["tts_99_segundos"] * 1000, 2),
            "p_exito": res["p_exito"],
        },
        "points_of_interest": {
            "start": {"row": START[0], "col": START[1]},
            "goal": {"row": GOAL[0], "col": GOAL[1]},
            "route_rewards": [],
            "route_enemies": [],
            "branch_attachment": None,
            "branch_a": None,
            "branch_b": None,
            "branch_reward": None,
        },
        "paths": {
            "main_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(ruta_q)],
            "branch_path": [],
            "bfs_shortest_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(mejor_valida["camino_bfs"])] if mejor_valida["camino_bfs"] else None,
        },
        "cells": cells_data,
    }

    json_path = EXPORT_DIR / f"caso3_nivel_blender_qubo_6x8_seed{seed}_{timestamp}.json"
    json_path_fijo = EXPORT_DIR / "caso3_nivel_blender_qubo_6x8.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    with open(json_path_fijo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Solución QUBO exportada para Blender en: {json_path}")
    print(f"Copia fija en: {json_path_fijo}")
    return json_path_fijo


if __name__ == "__main__":
    exportar_qubo_para_blender()
