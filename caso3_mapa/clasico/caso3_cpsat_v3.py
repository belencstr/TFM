from collections import deque
from datetime import datetime
from pathlib import Path
from time import perf_counter
import csv

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from ortools.sat.python import cp_model


# ============================================================
# CONFIGURACIÓN DEL CASO 3
# ============================================================

ROWS = 6
COLS = 8

START = (0, 0)
GOAL = (5, 7)

# Ruta principal: 13 celdas = 12 movimientos.
PATH_CELLS = 13

# Cuatro zonas 3x4, con cinco obstáculos en cada una.
N_WALLS_PER_ZONE = 5

# Gameplay final:
# - 1 recompensa en la ruta principal
# - 2 enemigos en la ruta principal
# - 1 recompensa al final de una rama secundaria de 2 celdas
N_ROUTE_REWARDS = 1
N_ROUTE_ENEMIES = 2

SEED = 42
MAX_TIME = 30.0


# ============================================================
# CARPETAS DE SALIDA
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

RESULTS_DIR = BASE_DIR / "experimentos" / "resultados"
FIGURES_DIR = BASE_DIR / "experimentos" / "figuras"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# GRID
# ============================================================

CELLS = [
    (r, c)
    for r in range(ROWS)
    for c in range(COLS)
]


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors(cell):
    r, c = cell
    result = []

    for dr, dc in [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
    ]:
        nr = r + dr
        nc = c + dc

        if 0 <= nr < ROWS and 0 <= nc < COLS:
            result.append((nr, nc))

    return result


def grid_edges():
    edges = []

    for r, c in CELLS:
        if r + 1 < ROWS:
            edges.append(((r, c), (r + 1, c)))

        if c + 1 < COLS:
            edges.append(((r, c), (r, c + 1)))

    return edges


EDGES = grid_edges()


# ============================================================
# ZONAS DEL MAPA
# ============================================================

ZONES = {
    "A": [
        (r, c)
        for r in range(0, 3)
        for c in range(0, 4)
    ],
    "B": [
        (r, c)
        for r in range(0, 3)
        for c in range(4, 8)
    ],
    "C": [
        (r, c)
        for r in range(3, 6)
        for c in range(0, 4)
    ],
    "D": [
        (r, c)
        for r in range(3, 6)
        for c in range(4, 8)
    ],
}

N_WALLS = len(ZONES) * N_WALLS_PER_ZONE
N_OPEN = ROWS * COLS - N_WALLS


# ============================================================
# PODA DE VARIABLES DE RUTA
# ============================================================

def candidate_cells_for_step(t):
    """
    Conserva solo celdas compatibles con el paso t de una ruta
    START->GOAL de longitud fija.

    Como PATH_CELLS - 1 coincide con la distancia Manhattan entre
    START y GOAL, la poda es fuerte y reduce mucho el número de
    variables de ruta.
    """

    remaining = PATH_CELLS - 1 - t
    candidates = []

    for cell in CELLS:
        d_start = manhattan(START, cell)
        d_goal = manhattan(cell, GOAL)

        reachable_from_start = (
            d_start <= t
            and (t - d_start) % 2 == 0
        )

        reachable_to_goal = (
            d_goal <= remaining
            and (remaining - d_goal) % 2 == 0
        )

        if reachable_from_start and reachable_to_goal:
            candidates.append(cell)

    return candidates


CANDIDATES = {
    t: candidate_cells_for_step(t)
    for t in range(PATH_CELLS)
}


# ============================================================
# CANDIDATAS PARA LA RAMA SECUNDARIA
# ============================================================

# La rama tiene exactamente dos celdas fuera de la ruta:
#
# ruta principal -> branch_a -> branch_b(REWARD)
#
# branch_b es un callejón sin salida.
#
# Se modela con pares ordenados (branch_a, branch_b) de celdas
# adyacentes. El solver selecciona exactamente un par.

BRANCH_PAIRS = []

for branch_a in CELLS:
    if (
        manhattan(START, branch_a) < 3
        or manhattan(branch_a, GOAL) < 3
    ):
        continue

    for branch_b in neighbors(branch_a):
        if (
            branch_b == START
            or branch_b == GOAL
            or manhattan(START, branch_b) < 3
            or manhattan(branch_b, GOAL) < 3
        ):
            continue

        BRANCH_PAIRS.append(
            (branch_a, branch_b)
        )


# ============================================================
# VALIDACIÓN INDEPENDIENTE MEDIANTE BFS
# ============================================================

def bfs_shortest_path(open_cells):
    if START not in open_cells or GOAL not in open_cells:
        return None

    queue = deque([START])
    parent = {START: None}

    while queue:
        current = queue.popleft()

        if current == GOAL:
            break

        for nxt in neighbors(current):
            if nxt not in open_cells:
                continue

            if nxt in parent:
                continue

            parent[nxt] = current
            queue.append(nxt)

    if GOAL not in parent:
        return None

    path = []
    node = GOAL

    while node is not None:
        path.append(node)
        node = parent[node]

    path.reverse()
    return path


def count_components(open_cells):
    unseen = set(open_cells)
    components = 0

    while unseen:
        components += 1

        first = next(iter(unseen))
        queue = deque([first])
        unseen.remove(first)

        while queue:
            current = queue.popleft()

            for nxt in neighbors(current):
                if nxt in unseen:
                    unseen.remove(nxt)
                    queue.append(nxt)

    return components


# ============================================================
# MODELO CP-SAT
# ============================================================

def solve_case3(seed=SEED):
    model = cp_model.CpModel()

    # --------------------------------------------------------
    # 1. GEOMETRÍA DEL NIVEL
    # --------------------------------------------------------
    # x[cell] = 1 -> suelo transitable
    # x[cell] = 0 -> obstáculo

    x = {
        cell: model.new_bool_var(
            f"x_{cell[0]}_{cell[1]}"
        )
        for cell in CELLS
    }

    model.add(x[START] == 1)
    model.add(x[GOAL] == 1)

    # Cinco paredes exactas en cada zona 3x4.
    for zone_cells in ZONES.values():
        model.add(
            sum(x[cell] for cell in zone_cells)
            == len(zone_cells) - N_WALLS_PER_ZONE
        )

    # --------------------------------------------------------
    # 2. RUTA PRINCIPAL
    # --------------------------------------------------------
    # q[t, cell] = 1 si la ruta ocupa cell en el paso t.

    q = {}

    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            q[t, cell] = model.new_bool_var(
                f"q_{t}_{cell[0]}_{cell[1]}"
            )

    # Exactamente una posición por paso.
    for t in range(PATH_CELLS):
        model.add(
            sum(
                q[t, cell]
                for cell in CANDIDATES[t]
            )
            == 1
        )

    model.add(q[0, START] == 1)
    model.add(
        q[PATH_CELLS - 1, GOAL] == 1
    )

    # La ruta solo atraviesa suelo.
    for (t, cell), variable in q.items():
        model.add(
            variable <= x[cell]
        )

    # p[cell] = 1 si la celda pertenece a la ruta principal.
    p = {}

    for cell in CELLS:
        p[cell] = model.new_bool_var(
            f"path_{cell[0]}_{cell[1]}"
        )

        appearances = [
            q[t, cell]
            for t in range(PATH_CELLS)
            if (t, cell) in q
        ]

        if appearances:
            model.add(
                p[cell] == sum(appearances)
            )
        else:
            model.add(
                p[cell] == 0
            )

    # No repetir una celda.
    for cell in CELLS:
        appearances = [
            q[t, cell]
            for t in range(PATH_CELLS)
            if (t, cell) in q
        ]

        if len(appearances) > 1:
            model.add(
                sum(appearances) <= 1
            )

    # Continuidad entre pasos consecutivos.
    for t in range(PATH_CELLS - 1):
        for cell_a in CANDIDATES[t]:
            valid_neighbors = set(
                neighbors(cell_a)
            )

            for cell_b in CANDIDATES[t + 1]:
                if cell_b not in valid_neighbors:
                    model.add(
                        q[t, cell_a]
                        + q[t + 1, cell_b]
                        <= 1
                    )

    # --------------------------------------------------------
    # 3. RAMA SECUNDARIA DE DOS CELDAS
    # --------------------------------------------------------
    # pair_var[a,b] = 1 si:
    #
    # ruta -> a -> b(REWARD)
    #
    # a:
    # - es suelo;
    # - no pertenece a la ruta;
    # - tiene exactamente dos vecinos transitables:
    #   uno de la ruta y b.
    #
    # b:
    # - es suelo;
    # - no pertenece a la ruta;
    # - tiene exactamente un vecino transitable (a).
    #
    # Por tanto b es un callejón sin salida.

    branch_pair = {
        pair: model.new_bool_var(
            f"branch_"
            f"{pair[0][0]}_{pair[0][1]}_"
            f"{pair[1][0]}_{pair[1][1]}"
        )
        for pair in BRANCH_PAIRS
    }

    model.add(
        sum(branch_pair.values()) == 1
    )

    for (
        branch_a,
        branch_b,
    ), pair_var in branch_pair.items():

        # Ambas celdas son transitables.
        model.add(
            pair_var <= x[branch_a]
        )

        model.add(
            pair_var <= x[branch_b]
        )

        # Ninguna pertenece a la ruta principal.
        model.add(
            pair_var + p[branch_a] <= 1
        )

        model.add(
            pair_var + p[branch_b] <= 1
        )

        # Primera celda de la rama:
        # exactamente 2 vecinos transitables.
        model.add(
            sum(
                x[nxt]
                for nxt in neighbors(branch_a)
            )
            == 2
        ).only_enforce_if(pair_var)

        # De ellos, exactamente 1 pertenece a la ruta.
        model.add(
            sum(
                p[nxt]
                for nxt in neighbors(branch_a)
            )
            == 1
        ).only_enforce_if(pair_var)

        # Segunda celda:
        # exactamente 1 vecino transitable.
        # Como branch_a ya es transitable y adyacente,
        # dicho vecino será necesariamente branch_a.
        model.add(
            sum(
                x[nxt]
                for nxt in neighbors(branch_b)
            )
            == 1
        ).only_enforce_if(pair_var)

    # --------------------------------------------------------
    # 4. ELEMENTOS DE GAMEPLAY SOBRE LA RUTA
    # --------------------------------------------------------

    # Una recompensa sobre la ruta.
    route_reward = {
        t: model.new_bool_var(
            f"route_reward_{t}"
        )
        for t in range(PATH_CELLS)
    }

    # Dos enemigos sobre la ruta.
    route_enemy = {
        t: model.new_bool_var(
            f"route_enemy_{t}"
        )
        for t in range(PATH_CELLS)
    }

    model.add(
        sum(route_reward.values())
        == N_ROUTE_REWARDS
    )

    model.add(
        sum(route_enemy.values())
        == N_ROUTE_ENEMIES
    )

    # START y GOAL quedan libres.
    for t in [
        0,
        PATH_CELLS - 1,
    ]:
        model.add(
            route_reward[t] == 0
        )

        model.add(
            route_enemy[t] == 0
        )

    # Una celda de la ruta no puede contener premio y enemigo.
    for t in range(PATH_CELLS):
        model.add(
            route_reward[t]
            + route_enemy[t]
            <= 1
        )

    # Evitamos elementos consecutivos en la ruta.
    for t in range(PATH_CELLS - 1):
        model.add(
            route_reward[t]
            + route_enemy[t]
            + route_reward[t + 1]
            + route_enemy[t + 1]
            <= 1
        )

    # Progresión simple:
    # recompensa temprana, enemigo intermedio y enemigo tardío.
    model.add(
        sum(
            route_reward[t]
            for t in range(2, 5)
        )
        == 1
    )

    model.add(
        sum(
            route_enemy[t]
            for t in range(5, 8)
        )
        == 1
    )

    model.add(
        sum(
            route_enemy[t]
            for t in range(9, 12)
        )
        == 1
    )

    # --------------------------------------------------------
    # 5. OBJETIVO: COHERENCIA ESPACIAL
    # --------------------------------------------------------

    boundary = {}

    for idx, (a, b) in enumerate(EDGES):
        boundary[idx] = model.new_bool_var(
            f"boundary_{idx}"
        )

        model.add_abs_equality(
            boundary[idx],
            x[a] - x[b]
        )

    model.minimize(
        sum(boundary.values())
    )

    # --------------------------------------------------------
    # 6. SOLVER
    # --------------------------------------------------------

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = (
        MAX_TIME
    )

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

    status_name = status_names.get(
        status,
        str(status),
    )

    if status not in (
        cp_model.FEASIBLE,
        cp_model.OPTIMAL,
    ):
        print(
            "No se ha encontrado solución."
        )

        print(
            "Estado:",
            status_name,
        )

        return None

    # --------------------------------------------------------
    # 7. EXTRAER SOLUCIÓN
    # --------------------------------------------------------

    open_cells = {
        cell
        for cell in CELLS
        if solver.boolean_value(
            x[cell]
        )
    }

    witness_path = []

    for t in range(PATH_CELLS):
        selected = None

        for cell in CANDIDATES[t]:
            if solver.boolean_value(
                q[t, cell]
            ):
                selected = cell
                break

        witness_path.append(
            selected
        )

    route_reward_steps = [
        t
        for t in range(PATH_CELLS)
        if solver.boolean_value(
            route_reward[t]
        )
    ]

    route_enemy_steps = [
        t
        for t in range(PATH_CELLS)
        if solver.boolean_value(
            route_enemy[t]
        )
    ]

    route_reward_cells = [
        witness_path[t]
        for t in route_reward_steps
    ]

    route_enemy_cells = [
        witness_path[t]
        for t in route_enemy_steps
    ]

    selected_branch_pair = next(
        pair
        for pair, variable
        in branch_pair.items()
        if solver.boolean_value(variable)
    )

    branch_a, branch_b = (
        selected_branch_pair
    )

    # El único vecino de branch_a que pertenece
    # a la ruta principal es el punto de conexión.
    branch_attachment = next(
        nxt
        for nxt in neighbors(branch_a)
        if nxt in set(witness_path)
    )

    # La recompensa opcional se coloca automáticamente
    # al final de la rama.
    branch_reward_cell = branch_b

    bfs_path = bfs_shortest_path(
        open_cells
    )

    components = count_components(
        open_cells
    )

    walls_by_zone = {}

    for zone_name, zone_cells in ZONES.items():
        walls_by_zone[zone_name] = sum(
            1
            for cell in zone_cells
            if cell not in open_cells
        )

    return {
        "status": status_name,
        "time": elapsed,
        "objective": solver.objective_value,
        "open_cells": open_cells,
        "witness_path": witness_path,
        "route_reward_steps": route_reward_steps,
        "route_reward_cells": route_reward_cells,
        "route_enemy_steps": route_enemy_steps,
        "route_enemy_cells": route_enemy_cells,
        "branch_attachment": branch_attachment,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "branch_reward_cell": branch_reward_cell,
        "bfs_path": bfs_path,
        "components": components,
        "walls_by_zone": walls_by_zone,
    }


# ============================================================
# REPRESENTACIÓN ASCII
# ============================================================

def print_map(result):
    open_cells = result["open_cells"]
    path = set(result["witness_path"])
    route_rewards = set(
        result["route_reward_cells"]
    )
    route_enemies = set(
        result["route_enemy_cells"]
    )
    branch_a = result["branch_a"]
    branch_reward = result[
        "branch_reward_cell"
    ]

    print()
    print(
        "Leyenda: # pared | . suelo | * ruta | "
        "R recompensa | E enemigo | + rama | "
        "B recompensa de rama"
    )
    print()

    for r in range(ROWS):
        row = ""

        for c in range(COLS):
            cell = (r, c)

            if cell == START:
                row += "S "

            elif cell == GOAL:
                row += "G "

            elif cell == branch_reward:
                row += "B "

            elif cell == branch_a:
                row += "+ "

            elif cell in route_rewards:
                row += "R "

            elif cell in route_enemies:
                row += "E "

            elif cell in path:
                row += "* "

            elif cell in open_cells:
                row += ". "

            else:
                row += "# "

        print(row)


# ============================================================
# GUARDADO DE RESULTADOS
# ============================================================

def save_results(result):
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    stem = (
        f"cpsat_{ROWS}x{COLS}_"
        f"seed{SEED}_{timestamp}"
    )

    txt_path = (
        RESULTS_DIR
        / f"{stem}.txt"
    )

    csv_path = (
        RESULTS_DIR
        / f"{stem}.csv"
    )

    bfs_path = result["bfs_path"]

    bfs_length = (
        len(bfs_path) - 1
        if bfs_path is not None
        else None
    )

    route_vars = sum(
        len(v)
        for v in CANDIDATES.values()
    )

    lines = [
        "====================================",
        "CASO 3 - CP-SAT",
        "NIVEL 2D BASADO EN TILES",
        "====================================",
        "",
        f"Tamaño: {ROWS}x{COLS}",
        f"START: {START}",
        f"GOAL: {GOAL}",
        f"Semilla: {SEED}",
        "",
        (
            "Suelo transitable: "
            f"{len(result['open_cells'])}"
        ),
        (
            "Obstáculos: "
            f"{ROWS * COLS - len(result['open_cells'])}"
        ),
        (
            "Obstáculos por zona: "
            f"{result['walls_by_zone']}"
        ),
        (
            f"Ruta principal: "
            f"{PATH_CELLS} celdas / "
            f"{PATH_CELLS - 1} movimientos"
        ),
        "Recompensas totales: 2",
        "  - Recompensa en ruta: 1",
        "  - Recompensa en rama: 1",
        "Enemigos totales: 2",
        "  - Ambos en ruta principal",
        (
            "Variables de ruta tras poda: "
            f"{route_vars}"
        ),
        (
            "Pares candidatos para rama: "
            f"{len(BRANCH_PAIRS)}"
        ),
        "",
        f"Estado: {result['status']}",
        (
            "Objetivo (fronteras suelo/pared): "
            f"{result['objective']}"
        ),
        (
            "Tiempo: "
            f"{result['time']:.6f} s"
        ),
        (
            "Componentes transitables: "
            f"{result['components']}"
        ),
        (
            "Mapa navegable START->GOAL: "
            f"{bfs_path is not None}"
        ),
        (
            "Longitud ruta principal: "
            f"{len(result['witness_path']) - 1}"
        ),
        (
            "Longitud mínima BFS: "
            f"{bfs_length}"
        ),
        "",
        "Ruta principal:",
        str(result["witness_path"]),
        "",
        "Ruta mínima BFS:",
        str(result["bfs_path"]),
        "",
        (
            "Recompensa de ruta - pasos: "
            f"{result['route_reward_steps']}"
        ),
        (
            "Recompensa de ruta - celdas: "
            f"{result['route_reward_cells']}"
        ),
        "",
        (
            "Enemigos de ruta - pasos: "
            f"{result['route_enemy_steps']}"
        ),
        (
            "Enemigos de ruta - celdas: "
            f"{result['route_enemy_cells']}"
        ),
        "",
        (
            "Rama secundaria - conexión con ruta: "
            f"{result['branch_attachment']}"
        ),
        (
            "Rama secundaria - primera celda: "
            f"{result['branch_a']}"
        ),
        (
            "Rama secundaria - final: "
            f"{result['branch_b']}"
        ),
        (
            "Recompensa de rama: "
            f"{result['branch_reward_cell']}"
        ),
        "",
        "Celdas transitables:",
        str(
            sorted(
                result["open_cells"]
            )
        ),
    ]

    txt_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    path_cells = set(
        result["witness_path"]
    )

    route_reward_cells = set(
        result["route_reward_cells"]
    )

    route_enemy_cells = set(
        result["route_enemy_cells"]
    )

    branch_a = result["branch_a"]
    branch_reward = result[
        "branch_reward_cell"
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)

        writer.writerow(
            [
                "row",
                "col",
                "type",
            ]
        )

        for r, c in CELLS:
            cell = (r, c)

            if cell == START:
                cell_type = "START"

            elif cell == GOAL:
                cell_type = "GOAL"

            elif cell == branch_reward:
                cell_type = "BRANCH_REWARD"

            elif cell == branch_a:
                cell_type = "BRANCH"

            elif cell in route_reward_cells:
                cell_type = "REWARD"

            elif cell in route_enemy_cells:
                cell_type = "ENEMY"

            elif cell in path_cells:
                cell_type = "PATH"

            elif cell in result["open_cells"]:
                cell_type = "FLOOR"

            else:
                cell_type = "WALL"

            writer.writerow(
                [
                    r,
                    c,
                    cell_type,
                ]
            )

    return (
        timestamp,
        txt_path,
        csv_path,
    )


# ============================================================
# VISUALIZACIÓN
# ============================================================

def plot_map(result, timestamp):
    matrix = np.zeros(
        (ROWS, COLS),
        dtype=int,
    )

    for cell in result["open_cells"]:
        matrix[cell] = 1

    fig, ax = plt.subplots(
        figsize=(10, 7)
    )

    cmap = ListedColormap(
        [
            "#2b2b2b",
            "#f2f2f2",
        ]
    )

    ax.imshow(
        matrix,
        cmap=cmap,
        vmin=0,
        vmax=1,
    )

    ax.set_xticks(
        np.arange(-0.5, COLS, 1),
        minor=True,
    )

    ax.set_yticks(
        np.arange(-0.5, ROWS, 1),
        minor=True,
    )

    ax.grid(
        which="minor",
        linewidth=1.5,
    )

    ax.tick_params(
        which="minor",
        bottom=False,
        left=False,
    )

    ax.set_xticks(
        range(COLS)
    )

    ax.set_yticks(
        range(ROWS)
    )

    # Ruta principal.
    path = result["witness_path"]

    xs = [
        cell[1]
        for cell in path
    ]

    ys = [
        cell[0]
        for cell in path
    ]

    ax.plot(
        xs,
        ys,
        marker="o",
        linewidth=2.5,
        label="Ruta principal",
        zorder=4,
    )

    # Rama secundaria:
    # ruta -> A -> B(REWARD)
    attachment = result[
        "branch_attachment"
    ]

    branch_a = result["branch_a"]
    branch_b = result["branch_b"]

    ax.plot(
        [
            attachment[1],
            branch_a[1],
            branch_b[1],
        ],
        [
            attachment[0],
            branch_a[0],
            branch_b[0],
        ],
        linestyle="--",
        marker="o",
        linewidth=2.5,
        label="Rama secundaria",
        zorder=5,
    )

    # START.
    ax.scatter(
        START[1],
        START[0],
        marker="s",
        s=240,
        label="START",
        zorder=7,
    )

    # GOAL.
    ax.scatter(
        GOAL[1],
        GOAL[0],
        marker="*",
        s=330,
        label="GOAL",
        zorder=7,
    )

    # Recompensa de ruta.
    route_reward_x = [
        cell[1]
        for cell in result[
            "route_reward_cells"
        ]
    ]

    route_reward_y = [
        cell[0]
        for cell in result[
            "route_reward_cells"
        ]
    ]

    ax.scatter(
        route_reward_x,
        route_reward_y,
        marker="D",
        s=190,
        label="Recompensa en ruta",
        zorder=8,
    )

    # Recompensa de rama.
    branch_reward = result[
        "branch_reward_cell"
    ]

    ax.scatter(
        branch_reward[1],
        branch_reward[0],
        marker="D",
        s=230,
        label="Recompensa en rama",
        zorder=9,
    )

    # Dos enemigos de ruta.
    enemy_x = [
        cell[1]
        for cell in result[
            "route_enemy_cells"
        ]
    ]

    enemy_y = [
        cell[0]
        for cell in result[
            "route_enemy_cells"
        ]
    ]

    ax.scatter(
        enemy_x,
        enemy_y,
        marker="X",
        s=220,
        label="Enemigo",
        zorder=8,
    )

    ax.set_title(
        "Caso 3 - nivel 2D generado con CP-SAT"
    )

    # Fuera del mapa para no tapar ninguna celda.
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0,
    )

    fig.tight_layout()

    figure_path = (
        FIGURES_DIR
        / (
            f"cpsat_{ROWS}x{COLS}_"
            f"seed{SEED}_{timestamp}.png"
        )
    )

    fig.savefig(
        figure_path,
        dpi=200,
        bbox_inches="tight",
    )

    print()
    print(
        "Figura guardada en:"
    )

    print(
        figure_path
    )

    plt.show()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    print(
        "===================================="
    )

    print(
        "CASO 3 - CP-SAT"
    )

    print(
        "NIVEL 2D BASADO EN TILES"
    )

    print(
        "===================================="
    )

    print()
    print(
        f"Tamaño: {ROWS}x{COLS}"
    )

    print(
        f"Celdas: {ROWS * COLS}"
    )

    print(
        f"START: {START}"
    )

    print(
        f"GOAL: {GOAL}"
    )

    print(
        f"Suelo objetivo: {N_OPEN}"
    )

    print(
        f"Obstáculos objetivo: {N_WALLS}"
    )

    print(
        "Obstáculos por zona:",
        N_WALLS_PER_ZONE,
    )

    print(
        f"Ruta principal: "
        f"{PATH_CELLS} celdas / "
        f"{PATH_CELLS - 1} movimientos"
    )

    print(
        "Recompensas: 2 "
        "(1 ruta + 1 rama)"
    )

    print(
        "Enemigos: 2 "
        "(ambos en ruta)"
    )

    print()
    print(
        "Variables de ruta tras poda:",
        sum(
            len(v)
            for v in CANDIDATES.values()
        ),
    )

    print(
        "Pares candidatos para rama:",
        len(BRANCH_PAIRS),
    )

    result = solve_case3()

    if result is not None:
        bfs_path = result["bfs_path"]

        bfs_length = (
            len(bfs_path) - 1
            if bfs_path is not None
            else None
        )

        print()
        print(
            "Estado:",
            result["status"],
        )

        print(
            "Objetivo "
            "(fronteras suelo/pared):",
            result["objective"],
        )

        print(
            "Tiempo:",
            f"{result['time']:.6f} s",
        )

        print(
            "Obstáculos por zona:",
            result["walls_by_zone"],
        )

        print(
            "Componentes transitables:",
            result["components"],
        )

        print(
            "Mapa navegable START->GOAL:",
            bfs_path is not None,
        )

        print(
            "Longitud ruta principal:",
            len(
                result["witness_path"]
            ) - 1,
        )

        print(
            "Longitud mínima BFS:",
            bfs_length,
        )

        print()
        print(
            "Recompensa de ruta:"
        )

        for step, cell in zip(
            result["route_reward_steps"],
            result["route_reward_cells"],
        ):
            print(
                f"  paso {step}: {cell}"
            )

        print()
        print(
            "Enemigos de ruta:"
        )

        for step, cell in zip(
            result["route_enemy_steps"],
            result["route_enemy_cells"],
        ):
            print(
                f"  paso {step}: {cell}"
            )

        print()
        print(
            "Rama secundaria:"
        )

        print(
            "  conexión con ruta:",
            result["branch_attachment"],
        )

        print(
            "  primera celda:",
            result["branch_a"],
        )

        print(
            "  final:",
            result["branch_b"],
        )

        print(
            "  recompensa:",
            result["branch_reward_cell"],
        )

        print()
        print(
            "Ruta principal:"
        )

        print(
            result["witness_path"]
        )

        print_map(
            result
        )

        (
            timestamp,
            txt_path,
            csv_path,
        ) = save_results(
            result
        )

        print()
        print(
            "Resultados guardados:"
        )

        print(
            txt_path
        )

        print(
            csv_path
        )

        plot_map(
            result,
            timestamp,
        )