"""Formulación QUBO Desacoplada para el Caso 3 (Geometría y Balance de Zonas).

Derivación Teórica a Priori de Penalizaciones (Tutor Check):
    En una cuadrícula 6x8 existen exactamente:
        N_aristas = 6*(8 - 1) + (6 - 1)*8 = 42 + 40 = 82 aristas ortogonales.
    Dado que cada arista contribuye como máximo 1 al objetivo de fronteras:
        0 <= F <= 82
    Por consiguiente, el coste máximo posible de la función objetivo está
    acotado superiormente por 82 de forma estricta e independiente del óptimo.

    Para garantizar a priori que cualquier violación de una restricción dura
    (zonas o START/GOAL) resulte energéticamente inviable frente a cualquier
    configuración factible, fijamos una penalización teórica conservadora:
        P > 82  -->  P = 100.0 (o 85.0)

Variables de Decisión:
    x_{r, c} in {0, 1}:
        1 si la celda (r, c) es suelo transitable.
        0 si la celda (r, c) es un muro / obstáculo.
    Total: 6 x 8 = 48 variables binarias.

Hamiltoniano QUBO:
    H = H_fronteras + P * H_zonas + P * H_start_goal
"""

from collections import defaultdict
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from clasico.caso3_cpsat_v3 import (
    ROWS,
    COLS,
    CELLS,
    START,
    GOAL,
    ZONES,
    EDGES,
    N_WALLS_PER_ZONE,
    CANDIDATES,
    PATH_CELLS,
    neighbors,
)

# Cota superior teórica del número de aristas en la rejilla 6x8
N_ARISTAS_TOTALES = len(EDGES)  # 6*7 + 5*8 = 82
COTA_MAX_FRONTERAS = float(N_ARISTAS_TOTALES)  # 82.0
PENALIZACION_TEORICA_P = 100.0  # P > 82 garantiza penalización estricta a priori

N_SUELO_ZONA = 12 - N_WALLS_PER_ZONE  # 7 suelos por zona de 12 celdas


def var_x(r, c):
    return f"x_{r}_{c}"


def var_q(t, r, c):
    return f"q_{t}_{r}_{c}"


def par_cuadratico(u, v):
    return tuple(sorted((u, v)))


def construir_qubo_geometria(
    peso_frontera=1.0,
    peso_zona=PENALIZACION_TEORICA_P,
    peso_start_goal=PENALIZACION_TEORICA_P,
):
    """Construye el QUBO desacoplado de 48 variables con penalización teórica P > 82."""
    lineal = defaultdict(float)
    cuadratico = defaultdict(float)
    constante = 0.0

    variables = [var_x(r, c) for r, c in CELLS]

    # 1. Coherencia espacial tipo Ising: |x_u - x_v| = x_u + x_v - 2*x_u*x_v
    for u, v in EDGES:
        var_u = var_x(u[0], u[1])
        var_v = var_x(v[0], v[1])
        lineal[var_u] += peso_frontera * 1.0
        lineal[var_v] += peso_frontera * 1.0
        cuadratico[par_cuadratico(var_u, var_v)] += peso_frontera * (-2.0)

    # 2. Control de zonas: (sum_{c in Z} x_c - 7)^2
    # = -13 * sum x_i + 2 * sum_{i<j} x_i*x_j + 49
    N = float(N_SUELO_ZONA)  # 7.0
    coef_lin_zona = 1.0 - 2.0 * N  # -13.0

    for zone_name, zone_cells in ZONES.items():
        zvars = [var_x(r, c) for r, c in zone_cells]
        constante += peso_zona * (N ** 2)

        for v in zvars:
            lineal[v] += peso_zona * coef_lin_zona

        for i in range(len(zvars)):
            for j in range(i + 1, len(zvars)):
                cuadratico[par_cuadratico(zvars[i], zvars[j])] += peso_zona * 2.0

    # 3. START y GOAL obligatorios: (1 - x_S)^2 + (1 - x_G)^2
    var_start = var_x(START[0], START[1])
    constante += peso_start_goal * 1.0
    lineal[var_start] -= peso_start_goal * 1.0

    var_goal = var_x(GOAL[0], GOAL[1])
    constante += peso_start_goal * 1.0
    lineal[var_goal] -= peso_start_goal * 1.0

    return {
        "lineal": dict(lineal),
        "cuadratico": dict(cuadratico),
        "constante": constante,
        "variables": variables,
        "num_vars": len(variables),
        "cota_max_fronteras": COTA_MAX_FRONTERAS,
        "params": {
            "peso_frontera": peso_frontera,
            "peso_zona": peso_zona,
            "peso_start_goal": peso_start_goal,
        },
    }


def evaluar_energia_qubo(solucion_dict, qubo):
    energia = qubo["constante"]
    for var, val in solucion_dict.items():
        if val:
            energia += qubo["lineal"].get(var, 0.0)
    for (u, v), coeff in qubo["cuadratico"].items():
        if solucion_dict.get(u, 0) and solucion_dict.get(v, 0):
            energia += coeff
    return energia


def extraer_mapa_de_solucion(solucion_dict):
    open_cells = set()
    for r in range(ROWS):
        for c in range(COLS):
            if solucion_dict.get(var_x(r, c), 0) == 1:
                open_cells.add((r, c))
    return open_cells
