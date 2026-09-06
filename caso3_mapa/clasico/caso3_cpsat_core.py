"""CP-SAT Core para el Caso 3 (Geometría + Ruta Principal).

Este modelo resuelve EXACTAMENTE el mismo problema que el QUBO Integrado:
- Cuadrícula 6x8 con START en (0,0) y GOAL en (5,7).
- 4 zonas 3x4 con 5 obstáculos cada una (20 muros, 28 suelos).
- Ruta principal de 13 celdas (12 pasos) garantizada entre START y GOAL.
- Objetivo: Minimizar fronteras suelo/pared (coherencia espacial tipo Ising).

Sin la rama secundaria ni elementos de gameplay (que corresponden al CP-SAT
Completo demostrador), sirviendo como baseline clásico exacto para la
comparativa científica rigurosa con el QUBO Integrado.
"""

from collections import deque
from time import perf_counter
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ortools.sat.python import cp_model

from clasico.caso3_cpsat_v3 import (
    ROWS,
    COLS,
    CELLS,
    START,
    GOAL,
    ZONES,
    EDGES,
    N_WALLS_PER_ZONE,
    N_WALLS,
    N_OPEN,
    PATH_CELLS,
    CANDIDATES,
    neighbors,
    bfs_shortest_path,
    count_components,
    SEED,
    MAX_TIME,
)


def solve_case3_core(seed=SEED, max_time=MAX_TIME):
    model = cp_model.CpModel()

    # 1. Geometría: x[cell] = 1 (suelo), 0 (pared)
    x = {
        cell: model.new_bool_var(f"x_{cell[0]}_{cell[1]}")
        for cell in CELLS
    }
    model.add(x[START] == 1)
    model.add(x[GOAL] == 1)

    # Balance estricto por zonas (5 muros, 7 suelos por zona)
    for zone_cells in ZONES.values():
        model.add(
            sum(x[cell] for cell in zone_cells) == len(zone_cells) - N_WALLS_PER_ZONE
        )

    # 2. Ruta principal: q[t, cell] = 1 si la ruta ocupa cell en paso t
    q = {}
    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            q[t, cell] = model.new_bool_var(f"q_{t}_{cell[0]}_{cell[1]}")

    # Exactamente una posición por paso
    for t in range(PATH_CELLS):
        model.add(sum(q[t, cell] for cell in CANDIDATES[t]) == 1)

    model.add(q[0, START] == 1)
    model.add(q[PATH_CELLS - 1, GOAL] == 1)

    # La ruta solo atraviesa suelo
    for (t, cell), var in q.items():
        model.add(var <= x[cell])

    # Continuidad espacial entre pasos t y t+1
    for t in range(PATH_CELLS - 1):
        for cell_a in CANDIDATES[t]:
            vecinos = set(neighbors(cell_a))
            for cell_b in CANDIDATES[t + 1]:
                if cell_b not in vecinos:
                    model.add(q[t, cell_a] + q[t + 1, cell_b] <= 1)

    # 3. Objetivo: Minimizar fronteras suelo/pared (coherencia espacial tipo Ising)
    boundary = {}
    for idx, (a, b) in enumerate(EDGES):
        boundary[idx] = model.new_bool_var(f"boundary_{idx}")
        model.add_abs_equality(boundary[idx], x[a] - x[b])

    model.minimize(sum(boundary.values()))

    # Contar variables exactas del modelo
    num_vars_totales = len(model.Proto().variables)
    num_vars_x = len(x)
    num_vars_q = len(q)
    num_vars_boundary = len(boundary)

    # Resolver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = 1

    t0 = perf_counter()
    status = solver.solve(model)
    elapsed = perf_counter() - t0

    status_names = {
        cp_model.UNKNOWN: "UNKNOWN",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.OPTIMAL: "OPTIMAL",
    }
    status_name = status_names.get(status, str(status))

    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return None

    open_cells = {cell for cell in CELLS if solver.boolean_value(x[cell])}

    witness_path = []
    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            if solver.boolean_value(q[t, cell]):
                witness_path.append(cell)
                break

    bfs_path = bfs_shortest_path(open_cells)
    comp = count_components(open_cells)

    return {
        "status": status_name,
        "time": elapsed,
        "objective": solver.objective_value,
        "open_cells": open_cells,
        "witness_path": witness_path,
        "bfs_path": bfs_path,
        "components": comp,
        "num_vars_totales": num_vars_totales,
        "num_vars_x": num_vars_x,
        "num_vars_q": num_vars_q,
        "num_vars_boundary": num_vars_boundary,
    }


if __name__ == "__main__":
    res = solve_case3_core()
    print("CP-SAT Core ejecutado:")
    print(f"  Estado: {res['status']}")
    print(f"  Tiempo: {res['time']:.4f} s")
    print(f"  Objetivo (fronteras): {res['objective']}")
    print(f"  Variables totales en solver: {res['num_vars_totales']} (x={res['num_vars_x']}, q={res['num_vars_q']}, boundary={res['num_vars_boundary']})")
    print(f"  Ruta q longitud: {len(res['witness_path'])-1}")
    print(f"  Ruta BFS longitud: {len(res['bfs_path'])-1}")
    print(f"  Componentes: {res['components']}")
