"""Exporta una solución CP-SAT v3 del Caso 3 a JSON para Blender.

El nivel se representa como una cuadrícula 2D (6x8) con:
- Celdas transitables (suelo) y obstáculos (muros).
- START y GOAL en esquinas opuestas.
- Ruta principal obligatoria y garantizada.
- Rama secundaria de 2 celdas (callejón sin salida / secreto).
- Elementos de gameplay:
  * 1 recompensa en la ruta principal.
  * 2 enemigos en la ruta principal.
  * 1 recompensa final en la rama secundaria.

El archivo JSON generado contiene toda la información geométrica,
coordenadas normalizadas, etiquetas de celda y metadatos de resolución
necesarios para que Blender construya la escena 3D automáticamente.
"""

from datetime import datetime
from pathlib import Path
import json
import sys

# Permitir importación de módulos hermanos
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from clasico.caso3_cpsat_v3 import (
    ROWS,
    COLS,
    START,
    GOAL,
    CELLS,
    solve_case3,
    SEED,
)

EXPORT_DIR = BASE_DIR / "experimentos" / "resultados"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def exportar_nivel(result=None, seed=SEED):
    """
    Resuelve (si no se proporciona un resultado previo) y exporta
    el nivel a formato JSON para Blender.
    """
    if result is None:
        print(f"Ejecutando CP-SAT v3 (semilla={seed})...")
        result = solve_case3(seed=seed)

    if result is None or result["status"] not in ("OPTIMAL", "FEASIBLE"):
        raise RuntimeError("No se pudo obtener una solución válida de CP-SAT v3.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    open_cells = set(result["open_cells"])
    witness_path = result["witness_path"]
    path_cells = set(witness_path)
    route_rewards = set(result["route_reward_cells"])
    route_enemies = set(result["route_enemy_cells"])
    branch_a = result["branch_a"]
    branch_b = result["branch_b"]
    branch_reward = result["branch_reward_cell"]
    branch_attachment = result["branch_attachment"]

    # Clasificación detallada de cada una de las celdas
    cells_data = []
    for r in range(ROWS):
        for c in range(COLS):
            cell = (r, c)
            is_open = cell in open_cells

            if cell == START:
                cell_type = "START"
            elif cell == GOAL:
                cell_type = "GOAL"
            elif cell == branch_reward:
                cell_type = "BRANCH_REWARD"
            elif cell == branch_a:
                cell_type = "BRANCH"
            elif cell in route_rewards:
                cell_type = "REWARD"
            elif cell in route_enemies:
                cell_type = "ENEMY"
            elif cell in path_cells:
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
                "is_path": cell in path_cells,
                "is_branch": cell in (branch_a, branch_b),
                "is_reward": cell in route_rewards or cell == branch_reward,
                "is_enemy": cell in route_enemies,
            })

    # Ruta secundaria completa: desde la conexión en ruta hasta el premio final
    branch_path = [branch_attachment, branch_a, branch_b]

    data = {
        "metadata": {
            "caso": 3,
            "titulo": "Mapa 2D con obstáculos y gameplay",
            "solver": "CP-SAT v3",
            "status": result["status"],
            "seed": seed,
            "timestamp": timestamp,
            "solve_time_seconds": round(result["time"], 6),
            "objective_value": result["objective"],
            "grid_rows": ROWS,
            "grid_cols": COLS,
            "total_cells": ROWS * COLS,
            "floor_cells_count": len(open_cells),
            "wall_cells_count": ROWS * COLS - len(open_cells),
            "components_count": result["components"],
            "bfs_path_length": len(result["bfs_path"]) - 1 if result["bfs_path"] else None,
            "witness_path_length": len(witness_path) - 1,
        },
        "points_of_interest": {
            "start": {"row": START[0], "col": START[1]},
            "goal": {"row": GOAL[0], "col": GOAL[1]},
            "route_rewards": [{"row": r, "col": c} for r, c in result["route_reward_cells"]],
            "route_enemies": [{"row": r, "col": c} for r, c in result["route_enemy_cells"]],
            "branch_attachment": {"row": branch_attachment[0], "col": branch_attachment[1]},
            "branch_a": {"row": branch_a[0], "col": branch_a[1]},
            "branch_b": {"row": branch_b[0], "col": branch_b[1]},
            "branch_reward": {"row": branch_reward[0], "col": branch_reward[1]},
        },
        "paths": {
            "main_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(witness_path)],
            "branch_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(branch_path)],
            "bfs_shortest_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(result["bfs_path"])] if result["bfs_path"] else None,
        },
        "cells": cells_data,
    }

    json_filename = f"caso3_nivel_blender_{ROWS}x{COLS}_seed{seed}_{timestamp}.json"
    json_path = EXPORT_DIR / json_filename

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print("EXPORTACIÓN BLENDER CASO 3 COMPLETADA")
    print("=" * 60)
    print(f"Archivo JSON generado:")
    print(f"  {json_path}")
    print(f"Estado CP-SAT: {result['status']} ({result['time']:.3f} s)")
    print(f"Fronteras suelo/pared: {result['objective']}")
    print(f"Celdas suelo: {len(open_cells)} | Muros: {ROWS * COLS - len(open_cells)}")
    print(f"Componentes transitables: {result['components']} (Conectividad perfecta: {result['components'] == 1})")
    print("=" * 60)

    return json_path


if __name__ == "__main__":
    exportar_nivel()
