"""Formulación QUBO Integrada para el Caso 3 (Geometría + Ruta Embebida).

Incorpora la ruta principal dentro del propio Hamiltoniano QUBO mediante
las variables podadas q_{t, c}:
- 48 variables de celda x_c in {0, 1} (suelo vs muro).
- 48 variables de paso q_{t, c} in {0, 1} (la ruta ocupa la celda c en el paso t).
Total: 96 variables binarias.

Permite comparar en la memoria del TFM:
1. Modelo Desacoplado: 48 variables, valida conectividad con BFS clásico.
2. Modelo Integrado: 96 variables, garantiza la ruta dentro del Hamiltoniano.
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
    neighbors,
    var_x,
    var_q,
    par_cuadratico,
    construir_qubo_geometria,
)


def construir_qubo_integrado(
    peso_frontera=1.0,
    peso_zona=15.0,
    peso_start_goal=50.0,
    peso_paso=25.0,
    peso_continuidad=30.0,
    peso_compatibilidad_suelo=30.0,
):
    """Construye el QUBO integrado de 96 variables (geometría + ruta)."""
    # 1. Partir de la base geométrica
    qubo_base = construir_qubo_geometria(
        peso_frontera=peso_frontera,
        peso_zona=peso_zona,
        peso_start_goal=peso_start_goal,
    )

    lineal = defaultdict(float, qubo_base["lineal"])
    cuadratico = defaultdict(float, qubo_base["cuadratico"])
    constante = qubo_base["constante"]

    # Variables de ruta
    route_vars = []
    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            route_vars.append((t, cell, var_q(t, cell[0], cell[1])))

    all_vars = list(qubo_base["variables"]) + [vname for _, _, vname in route_vars]

    # 2. START en t=0 y GOAL en t=12 fijos
    var_q_start = var_q(0, START[0], START[1])
    constante += peso_start_goal * 1.0
    lineal[var_q_start] -= peso_start_goal * 1.0

    var_q_goal = var_q(PATH_CELLS - 1, GOAL[0], GOAL[1])
    constante += peso_start_goal * 1.0
    lineal[var_q_goal] -= peso_start_goal * 1.0

    # 3. Unicidad de posición en cada paso intermedio t: (sum_{c in Cand_t} q_{t, c} - 1)^2
    for t in range(1, PATH_CELLS - 1):
        step_vars = [var_q(t, c[0], c[1]) for c in CANDIDATES[t]]
        # (sum q_i - 1)^2 = sum q_i + 2 sum_{i<j} q_i q_j - 2 sum q_i + 1 = -sum q_i + 2 sum q_i q_j + 1
        constante += peso_paso * 1.0
        for v in step_vars:
            lineal[v] -= peso_paso * 1.0
        for i in range(len(step_vars)):
            for j in range(i + 1, len(step_vars)):
                cuadratico[par_cuadratico(step_vars[i], step_vars[j])] += peso_paso * 2.0

    # 4. Continuidad entre pasos t y t+1: penalizar pares no adyacentes
    for t in range(PATH_CELLS - 1):
        for cell_a in CANDIDATES[t]:
            vecinos_validos = set(neighbors(cell_a))
            var_a = var_q(t, cell_a[0], cell_a[1])

            for cell_b in CANDIDATES[t + 1]:
                if cell_b not in vecinos_validos:
                    var_b = var_q(t + 1, cell_b[0], cell_b[1])
                    cuadratico[par_cuadratico(var_a, var_b)] += peso_continuidad * 1.0

    # 5. Compatibilidad de suelo: q_{t, c} * (1 - x_c) = q_{t, c} - q_{t, c} * x_c
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
    qubo_int = construir_qubo_integrado()
    print("QUBO Integrado construido con éxito:")
    print(f"  Variables totales: {qubo_int['num_vars']} (Geometría: {qubo_int['num_vars_geometria']}, Ruta: {qubo_int['num_vars_ruta']})")
    print(f"  Términos cuadráticos: {len(qubo_int['cuadratico'])}")
    print(f"  Constante: {qubo_int['constante']:.2f}")
