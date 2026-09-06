"""Formulación QUBO Integrada para el Caso 3 (Geometría + Ruta Embebida).

Derivación Teórica a Priori de Penalizaciones:
    En una cuadrícula 6x8 existen N_aristas = 6*7 + 5*8 = 82 aristas.
    El objetivo de fronteras tipo Ising cumple estrictamente 0 <= F <= 82.
    Para que cualquier estado que viole una sola restricción (zonas, START/GOAL,
    unicidad de paso, continuidad de ruta o pisar un obstáculo) sea energéticamente
    superior (penalizado) a cualquier solución factible, fijamos:
        P > 82  -->  P = 100.0

Variables (Exactamente 96):
    - 48 variables de celda: x_{r, c} in {0, 1} (suelo vs muro).
    - 48 variables de paso: q_{t, c} in {0, 1} (la ruta pisa la celda c en paso t).
"""

from collections import defaultdict
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3 import (
    ROWS,
    COLS,
    CELLS,
    START,
    GOAL,
    ZONES,
    EDGES,
    N_WALLS_PER_ZONE,
    N_SUELO_ZONA,
    CANDIDATES,
    PATH_CELLS,
    COTA_MAX_FRONTERAS,
    PENALIZACION_TEORICA_P,
    neighbors,
    var_x,
    var_q,
    par_cuadratico,
    construir_qubo_geometria,
)


def construir_qubo_integrado(
    peso_frontera=1.0,
    peso_zona=PENALIZACION_TEORICA_P,
    peso_start_goal=PENALIZACION_TEORICA_P,
    peso_paso=PENALIZACION_TEORICA_P,
    peso_continuidad=PENALIZACION_TEORICA_P,
    peso_compatibilidad_suelo=PENALIZACION_TEORICA_P,
):
    """Construye el QUBO integrado de 96 variables con penalización teórica P > 82."""
    qubo_base = construir_qubo_geometria(
        peso_frontera=peso_frontera,
        peso_zona=peso_zona,
        peso_start_goal=peso_start_goal,
    )

    lineal = defaultdict(float, qubo_base["lineal"])
    cuadratico = defaultdict(float, qubo_base["cuadratico"])
    constante = qubo_base["constante"]

    route_vars = []
    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            route_vars.append((t, cell, var_q(t, cell[0], cell[1])))

    all_vars = list(qubo_base["variables"]) + [vname for _, _, vname in route_vars]

    # 1. START en t=0 y GOAL en t=12
    var_q_start = var_q(0, START[0], START[1])
    constante += peso_start_goal * 1.0
    lineal[var_q_start] -= peso_start_goal * 1.0

    var_q_goal = var_q(PATH_CELLS - 1, GOAL[0], GOAL[1])
    constante += peso_start_goal * 1.0
    lineal[var_q_goal] -= peso_start_goal * 1.0

    # 2. Unicidad de posición en cada paso intermedio t: (sum q_{t, c} - 1)^2
    for t in range(1, PATH_CELLS - 1):
        step_vars = [var_q(t, c[0], c[1]) for c in CANDIDATES[t]]
        constante += peso_paso * 1.0
        for v in step_vars:
            lineal[v] -= peso_paso * 1.0
        for i in range(len(step_vars)):
            for j in range(i + 1, len(step_vars)):
                cuadratico[par_cuadratico(step_vars[i], step_vars[j])] += peso_paso * 2.0

    # 3. Continuidad entre pasos t y t+1: penalizar saltos no vecinos
    for t in range(PATH_CELLS - 1):
        for cell_a in CANDIDATES[t]:
            vecinos = set(neighbors(cell_a))
            var_a = var_q(t, cell_a[0], cell_a[1])

            for cell_b in CANDIDATES[t + 1]:
                if cell_b not in vecinos:
                    var_b = var_q(t + 1, cell_b[0], cell_b[1])
                    cuadratico[par_cuadratico(var_a, var_b)] += peso_continuidad * 1.0

    # 4. Compatibilidad de suelo: q_{t, c} * (1 - x_c) = q_{t, c} - q_{t, c} * x_c
    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            v_q = var_q(t, cell[0], cell[1])
            v_x = var_x(cell[0], cell[1])
            lineal[v_q] += peso_compatibilidad_suelo * 1.0
            cuadratico[par_cuadratico(v_q, v_x)] -= peso_compatibilidad_suelo * 1.0

    return {
        "lineal": dict(lineal),
        "cuadratico": dict(cuadratico),
        "constante": constante,
        "variables": all_vars,
        "num_vars": len(all_vars),
        "num_vars_geometria": qubo_base["num_vars"],
        "num_vars_ruta": len(route_vars),
        "cota_max_fronteras": COTA_MAX_FRONTERAS,
        "params": {
            "peso_frontera": peso_frontera,
            "peso_zona": peso_zona,
            "peso_start_goal": peso_start_goal,
            "peso_paso": peso_paso,
            "peso_continuidad": peso_continuidad,
            "peso_compatibilidad_suelo": peso_compatibilidad_suelo,
        },
    }


if __name__ == "__main__":
    q = construir_qubo_integrado()
    print(f"QUBO Integrado (P={PENALIZACION_TEORICA_P}): {q['num_vars']} vars, {len(q['cuadratico'])} cuadráticos.")
