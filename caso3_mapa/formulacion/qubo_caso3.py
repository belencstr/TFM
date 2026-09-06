"""Formulación QUBO para el Caso 3 (Mapa 2D con Obstáculos y Conectividad).

Problema:
    Generar un mapa en una cuadrícula 6x8 con START en (0,0) y GOAL en (5,7).
    - Maximizar la coherencia espacial agrupando obstáculos (muros) y suelo.
    - Controlar la densidad en 4 zonas 3x4 (exactamente 5 muros y 7 suelos por zona).
    - Garantizar START y GOAL transitables.

Variables de Decisión:
    x_{r, c} in {0, 1}:
        1 si la celda (r, c) es suelo transitable.
        0 si la celda (r, c) es un muro / obstáculo.
    Total de variables de celda: 6 x 8 = 48.

Formulación del Hamiltoniano QUBO:

1) Coherencia Espacial (Fronteras Suelo / Muro - Modelo de Ising):
    Para cada arista ortogonal (u, v) en el grafo de la cuadrícula:
        |x_u - x_v| = x_u + x_v - 2 * x_u * x_v
    Esta función es nativamente cuadrática en variables binarias y penaliza
    las transiciones entre suelo y pared, promoviendo clusters compactos.

2) Densidad por Zonas (4 zonas 3x4):
    Para cada zona Z_k:
        sum_{c in Z_k} x_c = N_SUELO_ZONA (7)
    Penalización cuadrática:
        (sum_{c in Z_k} x_c - 7)^2 = -13 * sum_{i} x_i + 2 * sum_{i < j} x_i * x_j + 49

3) Posiciones Fijas (START y GOAL):
    (1 - x_START)^2 = 1 - x_START
    (1 - x_GOAL)^2  = 1 - x_GOAL

4) Modelo Integrado con Ruta Principal (Opcional):
    Variables de ruta podadas q_{t, c} in {0, 1} para el paso t in [0, 12]:
    - Unicidad de posición en cada paso: (sum_{c} q_{t, c} - 1)^2
    - Compatibilidad de suelo: q_{t, c} * (1 - x_c) = q_{t, c} - q_{t, c} * x_c
    - Continuidad entre pasos consecutivos: q_{t, a} * q_{t+1, b} <= 0 si b no es vecino de a.
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

N_SUELO_ZONA = 12 - N_WALLS_PER_ZONE  # 7 suelos transitable por zona de 12 celdas


def var_x(r, c):
    """Nombre canónico de la variable de celda."""
    return f"x_{r}_{c}"


def var_q(t, r, c):
    """Nombre canónico de la variable de ruta en paso t."""
    return f"q_{t}_{r}_{c}"


def par_cuadratico(u, v):
    """Clave ordenada estable para términos cuadráticos."""
    return tuple(sorted((u, v)))


def construir_qubo_geometria(
    peso_frontera=1.0,
    peso_zona=10.0,
    peso_start_goal=50.0,
):
    """Construye el QUBO desacoplado de geometría (48 variables de celda).

    Este modelo optimiza la forma espacial del mapa y la densidad de zonas.
    La navegabilidad y la existencia de rutas se validan externamente con BFS,
    tal como se especifica en el diseño experimental del TFM.

    Returns:
        dict con:
            'lineal': dict con coeficientes lineales h_i
            'cuadratico': dict con coeficientes cuadráticos J_ij
            'constante': término constante E_0
            'variables': lista de nombres de variables
            'num_vars': 48
    """
    lineal = defaultdict(float)
    cuadratico = defaultdict(float)
    constante = 0.0

    variables = [var_x(r, c) for r, c in CELLS]

    # -------------------------------------------------------------------------
    # 1. OBJETIVO: MINIMIZAR FRONTERAS (MODELO DE ISING 2D)
    # -------------------------------------------------------------------------
    # Para cada arista (u, v): |x_u - x_v| = x_u + x_v - 2 * x_u * x_v
    for u, v in EDGES:
        var_u = var_x(u[0], u[1])
        var_v = var_x(v[0], v[1])

        lineal[var_u] += peso_frontera * 1.0
        lineal[var_v] += peso_frontera * 1.0
        cuadratico[par_cuadratico(var_u, var_v)] += peso_frontera * (-2.0)

    # -------------------------------------------------------------------------
    # 2. RESTRICCIÓN: DENSIDAD EXACTA EN CADA ZONA 3x4
    # -------------------------------------------------------------------------
    # Para cada zona Z: (sum_{c in Z} x_c - N_SUELO_ZONA)^2
    # = sum x_i + 2 sum_{i<j} x_i x_j - 2 * N * sum x_i + N^2
    # = (1 - 2*N) * sum x_i + 2 * sum_{i<j} x_i x_j + N^2
    N = float(N_SUELO_ZONA)  # 7
    coef_lineal_zona = (1.0 - 2.0 * N)  # 1 - 14 = -13

    for zone_name, zone_cells in ZONES.items():
        zone_vars = [var_x(r, c) for r, c in zone_cells]

        # Término constante N^2 = 49
        constante += peso_zona * (N ** 2)

        # Términos lineales
        for v in zone_vars:
            lineal[v] += peso_zona * coef_lineal_zona

        # Términos cuadráticos
        for i in range(len(zone_vars)):
            for j in range(i + 1, len(zone_vars)):
                pair = par_cuadratico(zone_vars[i], zone_vars[j])
                cuadratico[pair] += peso_zona * 2.0

    # -------------------------------------------------------------------------
    # 3. RESTRICCIÓN: START Y GOAL OBLIGATORIOS (SUELO)
    # -------------------------------------------------------------------------
    # (1 - x_START)^2 = 1 - x_START
    var_start = var_x(START[0], START[1])
    constante += peso_start_goal * 1.0
    lineal[var_start] -= peso_start_goal * 1.0

    # (1 - x_GOAL)^2 = 1 - x_GOAL
    var_goal = var_x(GOAL[0], GOAL[1])
    constante += peso_start_goal * 1.0
    lineal[var_goal] -= peso_start_goal * 1.0

    return {
        "lineal": dict(lineal),
        "cuadratico": dict(cuadratico),
        "constante": constante,
        "variables": variables,
        "num_vars": len(variables),
        "params": {
            "peso_frontera": peso_frontera,
            "peso_zona": peso_zona,
            "peso_start_goal": peso_start_goal,
        },
    }


def evaluar_energia_qubo(solucion_dict, qubo):
    """Evalúa la energía del QUBO para una asignación binaria dada."""
    energia = qubo["constante"]

    for var, val in solucion_dict.items():
        if val:
            energia += qubo["lineal"].get(var, 0.0)

    for (u, v), coeff in qubo["cuadratico"].items():
        if solucion_dict.get(u, 0) and solucion_dict.get(v, 0):
            energia += coeff

    return energia


def extraer_mapa_de_solucion(solucion_dict):
    """Extrae las celdas abiertas a partir de un diccionario {var_name: 0/1}."""
    open_cells = set()
    for r in range(ROWS):
        for c in range(COLS):
            vname = var_x(r, c)
            if solucion_dict.get(vname, 0) == 1:
                open_cells.add((r, c))
    return open_cells
