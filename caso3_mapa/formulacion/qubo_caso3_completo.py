"""Formulación QUBO Completa para el Caso 3 (Nivel Completo: Geometría + Ruta + Gameplay + Rama).

Extensión demostradora avanzada: QUBO Full Restringido (117 variables).
Esta formulación modela el nivel completo incorporando los requisitos de diseño del demostrador final:
- Geometría: 48 celdas x_{r, c} in {0, 1} con coherencia ferromagnética tipo Ising y balance zonal (7 suelos, 5 muros por zona).
- Ruta principal: ruta START->GOAL de 12 pasos codificada mediante penalizaciones Hamiltonianas cuadráticas (48 variables q_{t, c}).
- Gameplay en ruta (9 variables de progreso):
    * 1 Recompensa en ruta: r_t in {0, 1} para t in [2, 3, 4] (progreso temprano).
    * 1 Enemigo 1 en ruta: e1_t in {0, 1} para t in [5, 6, 7] (progreso intermedio).
    * 1 Enemigo 2 en ruta: e2_t in {0, 1} para t in [9, 10, 11] (progreso tardío).
    * Restricción de no-consecutividad: r_4 * e1_5 = 0.
- Rama secundaria de exploración (12 variables de patrón b_k):
    * Catálogo geométrico predeterminado de tripletes ordenados (u, a, b) seleccionados según criterios
      espaciales de divergencia hacia bordes y bolsas de la cuadrícula.
    * Constituye una variante restringida respecto al espacio combinatorio no acotado de CP-SAT (116 pares),
      evitando la explosión cuadrática de C(116, 2) = 6.670 acoplamientos densos de unicidad.
    * Términos de acoplamiento cuadrático puro (grado 2):
      - Unicidad: sum b_k = 1.
      - Conexión con ruta: b_k * (1 - sum_{t in T(u)} q_{t, u}) = 0.
        (Matiz teórico: como la ruta tiene longitud Manhattan mínima, cada celda u aparece como candidata
         en a lo sumo un único paso temporal t en una ruta simple, garantizando que el término sea binario y no negativo).
      - Apertura de suelo: b_k * (1 - x_a) = 0, b_k * (1 - x_b) = 0.
      - Callejón sin salida estricto (dead-end): penalización b_k * x_w para vecinos no autorizados de a y b.
      - Recompensa de exploración ubicada en el final b.

Total variables: 48 + 48 + 9 + 12 = 117 variables binarias.
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
)
from formulacion.qubo_caso3_integrado import construir_qubo_integrado

# Definición de intervalos temporales de gameplay
REWARD_ROUTE_STEPS = [2, 3, 4]
ENEMY_1_STEPS = [5, 6, 7]
ENEMY_2_STEPS = [9, 10, 11]


def var_reward_route(t):
    return f"rew_route_{t}"


def var_enemy_1(t):
    return f"enemy1_{t}"


def var_enemy_2(t):
    return f"enemy2_{t}"


def var_branch_pattern(k):
    return f"branch_pat_{k:02d}"


# Catálogo geométrico predeterminado de 12 patrones viables de rama secundaria (u, a, b)
# Seleccionados mediante criterios espaciales de divergencia ortogonal hacia bordes y bolsas:
BRANCH_PATTERNS = [
    # 0. Borde sudoeste vertical descendente
    {"id": 0, "u": (3, 0), "a": (4, 0), "b": (5, 0), "desc": "Borde sudoeste vertical hacia la esquina inferior"},
    # 1. Lateral izquierdo horizontal
    {"id": 1, "u": (2, 0), "a": (2, 1), "b": (2, 2), "desc": "Flanco izquierdo hacia el interior"},
    # 2. Borde superior horizontal
    {"id": 2, "u": (0, 3), "a": (0, 4), "b": (0, 5), "desc": "Borde norte horizontal"},
    # 3. Borde superior en L
    {"id": 3, "u": (1, 3), "a": (0, 3), "b": (0, 4), "desc": "Borde norte en L"},
    # 4. Flanco derecho vertical hacia arriba
    {"id": 4, "u": (3, 6), "a": (2, 6), "b": (1, 6), "desc": "Flanco este vertical ascendente"},
    # 5. Esquina superior derecha
    {"id": 5, "u": (2, 7), "a": (1, 7), "b": (0, 7), "desc": "Esquina nordeste terminal"},
    # 6. Borde inferior horizontal hacia la izquierda
    {"id": 6, "u": (5, 3), "a": (5, 2), "b": (5, 1), "desc": "Borde sur horizontal"},
    # 7. Borde inferior en L
    {"id": 7, "u": (4, 4), "a": (5, 4), "b": (5, 3), "desc": "Borde sur en L"},
    # 8. Centro-norte vertical
    {"id": 8, "u": (3, 2), "a": (2, 2), "b": (1, 2), "desc": "Bolsa centro-norte vertical"},
    # 9. Centro-este ascendente
    {"id": 9, "u": (2, 5), "a": (1, 5), "b": (0, 5), "desc": "Bolsa nordeste interior"},
    # 10. Flanco inferior izquierdo alternativo
    {"id": 10, "u": (4, 2), "a": (5, 2), "b": (5, 1), "desc": "Flanco sudoeste hacia el sur"},
    # 11. Flanco inferior derecho descendente
    {"id": 11, "u": (3, 5), "a": (4, 5), "b": (5, 5), "desc": "Flanco sudeste hacia el sur"},
]


def construir_qubo_completo(
    peso_frontera=1.0,
    peso_zona=PENALIZACION_TEORICA_P,
    peso_start_goal=PENALIZACION_TEORICA_P,
    peso_paso=PENALIZACION_TEORICA_P,
    peso_continuidad=PENALIZACION_TEORICA_P,
    peso_compatibilidad_suelo=PENALIZACION_TEORICA_P,
    peso_gameplay=PENALIZACION_TEORICA_P,
    peso_rama=PENALIZACION_TEORICA_P,
):
    """Construye el QUBO Completo de 117 variables para el nivel con gameplay y rama secundaria."""
    # 1. Partir del modelo integrado (96 variables)
    qubo_int = construir_qubo_integrado(
        peso_frontera=peso_frontera,
        peso_zona=peso_zona,
        peso_start_goal=peso_start_goal,
        peso_paso=peso_paso,
        peso_continuidad=peso_continuidad,
        peso_compatibilidad_suelo=peso_compatibilidad_suelo,
    )

    lineal = defaultdict(float, qubo_int["lineal"])
    cuadratico = defaultdict(float, qubo_int["cuadratico"])
    constante = qubo_int["constante"]
    variables = list(qubo_int["variables"])

    # Precomputar diccionario de variables q por celda: cell -> list of (t, var_q_name)
    q_por_celda = defaultdict(list)
    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            q_por_celda[cell].append((t, var_q(t, cell[0], cell[1])))

    # =========================================================================
    # 2. VARIABLES Y PENALIZACIONES DE GAMEPLAY (9 VARIABLES)
    # =========================================================================
    vars_reward = [var_reward_route(t) for t in REWARD_ROUTE_STEPS]
    vars_enemy1 = [var_enemy_1(t) for t in ENEMY_1_STEPS]
    vars_enemy2 = [var_enemy_2(t) for t in ENEMY_2_STEPS]
    gameplay_vars = vars_reward + vars_enemy1 + vars_enemy2
    variables.extend(gameplay_vars)

    # 2.1. Exactamente 1 recompensa en t in [2, 3, 4]: P * (sum r_t - 1)^2
    constante += peso_gameplay * 1.0
    for v in vars_reward:
        lineal[v] -= peso_gameplay * 1.0
    for i in range(len(vars_reward)):
        for j in range(i + 1, len(vars_reward)):
            cuadratico[par_cuadratico(vars_reward[i], vars_reward[j])] += peso_gameplay * 2.0

    # 2.2. Exactamente 1 enemigo 1 en t in [5, 6, 7]: P * (sum e1_t - 1)^2
    constante += peso_gameplay * 1.0
    for v in vars_enemy1:
        lineal[v] -= peso_gameplay * 1.0
    for i in range(len(vars_enemy1)):
        for j in range(i + 1, len(vars_enemy1)):
            cuadratico[par_cuadratico(vars_enemy1[i], vars_enemy1[j])] += peso_gameplay * 2.0

    # 2.3. Exactamente 1 enemigo 2 en t in [9, 10, 11]: P * (sum e2_t - 1)^2
    constante += peso_gameplay * 1.0
    for v in vars_enemy2:
        lineal[v] -= peso_gameplay * 1.0
    for i in range(len(vars_enemy2)):
        for j in range(i + 1, len(vars_enemy2)):
            cuadratico[par_cuadratico(vars_enemy2[i], vars_enemy2[j])] += peso_gameplay * 2.0

    # 2.4. No consecutividad entre recompensa temprana y enemigo 1 (pasos 4 y 5):
    # Penalizar P * r_4 * e1_5
    cuadratico[par_cuadratico(var_reward_route(4), var_enemy_1(5))] += peso_gameplay * 1.0

    # =========================================================================
    # 3. VARIABLES Y PENALIZACIONES DE RAMA SECUNDARIA (12 VARIABLES DE PATRÓN)
    # =========================================================================
    branch_vars = [var_branch_pattern(p["id"]) for p in BRANCH_PATTERNS]
    variables.extend(branch_vars)

    # 3.1. Unicidad de rama: exactamente 1 patrón seleccionado: P * (sum b_k - 1)^2
    constante += peso_rama * 1.0
    for vb in branch_vars:
        lineal[vb] -= peso_rama * 1.0
    for i in range(len(branch_vars)):
        for j in range(i + 1, len(branch_vars)):
            cuadratico[par_cuadratico(branch_vars[i], branch_vars[j])] += peso_rama * 2.0

    # 3.2. Acoplamientos estructurales de cada patrón b_k = (u, a, b)
    for p in BRANCH_PATTERNS:
        k = p["id"]
        vb = var_branch_pattern(k)
        u = p["u"]
        a = p["a"]
        b = p["b"]

        va_x = var_x(a[0], a[1])
        vb_x = var_x(b[0], b[1])

        # A) Conexión obligatoria con la ruta: la celda u DEBE estar en la ruta principal.
        # Si la ruta no pisa u, sum_{t in T(u)} q_{t, u} = 0, penalización P * b_k.
        # b_k * (1 - sum q_{t, u}) = b_k - sum (b_k * q_{t, u})
        q_steps_u = q_por_celda[u]
        if q_steps_u:
            lineal[vb] += peso_rama * 1.0
            for _, vq in q_steps_u:
                cuadratico[par_cuadratico(vb, vq)] -= peso_rama * 1.0
        else:
            # Si u no fuese alcanzable por ningún cono, se penaliza directamente
            lineal[vb] += peso_rama * 10.0

        # B) Las celdas de la rama deben ser transitables:
        # b_k * (1 - x_a) = b_k - b_k * x_a
        lineal[vb] += peso_rama * 1.0
        cuadratico[par_cuadratico(vb, va_x)] -= peso_rama * 1.0

        # b_k * (1 - x_b) = b_k - b_k * x_b
        lineal[vb] += peso_rama * 1.0
        cuadratico[par_cuadratico(vb, vb_x)] -= peso_rama * 1.0

        # C) La celda b debe ser un callejón sin salida (dead-end):
        # Todo vecino de b distinto de a debe ser MURO (x_w = 0).
        for w in neighbors(b):
            if w != a:
                vw_x = var_x(w[0], w[1])
                cuadratico[par_cuadratico(vb, vw_x)] += peso_rama * 1.0

        # D) La celda a solo debe conectar con u y b (sin desvíos parásitos):
        # Todo vecino de a distinto de u y b debe ser MURO (x_v = 0).
        for v in neighbors(a):
            if v != u and v != b:
                vv_x = var_x(v[0], v[1])
                cuadratico[par_cuadratico(vb, vv_x)] += peso_rama * 1.0

        # E) Ni a ni b deben formar parte de la ruta principal:
        for _, vq_a in q_por_celda[a]:
            cuadratico[par_cuadratico(vb, vq_a)] += peso_rama * 1.0
        for _, vq_b in q_por_celda[b]:
            cuadratico[par_cuadratico(vb, vq_b)] += peso_rama * 1.0

    return {
        "lineal": dict(lineal),
        "cuadratico": dict(cuadratico),
        "constante": constante,
        "variables": variables,
        "num_vars": len(variables),
        "num_vars_base": qubo_int["num_vars"],
        "num_vars_gameplay": len(gameplay_vars),
        "num_vars_rama": len(branch_vars),
        "branch_patterns": BRANCH_PATTERNS,
        "reward_route_steps": REWARD_ROUTE_STEPS,
        "enemy_1_steps": ENEMY_1_STEPS,
        "enemy_2_steps": ENEMY_2_STEPS,
        "cota_max_fronteras": COTA_MAX_FRONTERAS,
        "params": {
            "peso_frontera": peso_frontera,
            "peso_zona": peso_zona,
            "peso_start_goal": peso_start_goal,
            "peso_paso": peso_paso,
            "peso_continuidad": peso_continuidad,
            "peso_compatibilidad_suelo": peso_compatibilidad_suelo,
            "peso_gameplay": peso_gameplay,
            "peso_rama": peso_rama,
        },
    }


if __name__ == "__main__":
    qubo_comp = construir_qubo_completo()
    print("=" * 70)
    print("QUBO COMPLETO — CASO 3 (GEOMETRÍA + RUTA + GAMEPLAY + RAMA)")
    print("=" * 70)
    print(f"Variables totales: {qubo_comp['num_vars']}")
    print(f"  - Geometría + Ruta q: {qubo_comp['num_vars_base']} vars")
    print(f"  - Gameplay (premios y enemigos): {qubo_comp['num_vars_gameplay']} vars")
    print(f"  - Patrones de rama secundaria: {qubo_comp['num_vars_rama']} vars")
    print(f"Términos lineales: {len(qubo_comp['lineal'])}")
    print(f"Términos cuadráticos: {len(qubo_comp['cuadratico'])}")
    print(f"Término constante: {qubo_comp['constante']}")
    print("=" * 70)
