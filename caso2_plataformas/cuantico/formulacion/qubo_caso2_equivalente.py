"""QUBO equivalente al modelo clásico CP-SAT v4 del Caso 2.

A diferencia del QUBO reducido, esta formulación conserva:
- variables de uso de nodo u_i;
- variables de salto z_ij;
- rango de longitud mediante holgura;
- mínimo de subidas y bajadas mediante holgura;
- no solapamiento;
- prohibición de tres saltos planos consecutivos;
- restricción antiatajos;
- objetivo clásico: minimizar variación vertical.

La clase es parametrizable para poder usar:
- instancia clásica completa: 40x10, L en [11,14];
- instancia reducida de comprobación: 18x5, L en [4,5].
"""

from collections import defaultdict
from math import ceil, log2


def u_label(n):
    return f"u_{n[0]}_{n[1]}"


def z_label(o, d):
    return f"z_{o[0]}_{o[1]}__{d[0]}_{d[1]}"


def bits_necesarios(max_valor):
    if max_valor <= 0:
        return 0
    return ceil(log2(max_valor + 1))


def pesos_binarios(max_valor):
    """Pesos binarios capaces de representar 0..max_valor.

    Se usa codificación estándar 1,2,4,...; puede representar algún valor
    adicional, pero la igualdad penalizada impide usarlo en una solución válida.
    """
    n = bits_necesarios(max_valor)
    return [2**k for k in range(n)]


def add_linear(Q, v, c):
    Q[(v, v)] += float(c)


def add_quadratic(Q, v1, v2, c):
    if v1 == v2:
        add_linear(Q, v1, c)
        return
    key = tuple(sorted((v1, v2)))
    Q[key] += float(c)


def add_square(Q, offset, coeffs, constant, weight):
    """Añade weight*(constant + sum a_i x_i)^2."""
    offset += weight * constant * constant
    items = list(coeffs.items())

    for v, a in items:
        add_linear(
            Q, v,
            weight * (a*a + 2.0*constant*a)
        )

    for i in range(len(items)):
        vi, ai = items[i]
        for j in range(i+1, len(items)):
            vj, aj = items[j]
            add_quadratic(
                Q, vi, vj,
                weight * 2.0 * ai * aj
            )

    return offset


def pares_solapados(candidatas, ancho_plataforma):
    pares = []
    for i in range(len(candidatas)):
        a = candidatas[i]
        for j in range(i+1, len(candidatas)):
            b = candidatas[j]
            if a[1] != b[1]:
                continue
            a_fin = a[0] + ancho_plataforma - 1
            b_fin = b[0] + ancho_plataforma - 1
            if not (a_fin < b[0] or b_fin < a[0]):
                pares.append((a, b))
    return pares


def triples_planos(grafo):
    planos = set()
    for o, destinos in grafo.items():
        for d in destinos:
            if d[1] == o[1]:
                planos.add((o, d))

    triples = []
    for a, b in planos:
        for c in grafo.get(b, []):
            if (b, c) not in planos:
                continue
            for d in grafo.get(c, []):
                if (c, d) in planos:
                    triples.append(((a, b), (b, c), (c, d)))
    return triples


def construir_qubo_equivalente(
    grafo,
    candidatas,
    start,
    goal,
    ancho_plataforma,
    min_saltos,
    max_saltos,
    min_subidas,
    min_bajadas,
    max_subida_fisica,
    max_caida_fisica,
):
    """Construye el QUBO equivalente y devuelve también metadatos."""
    Q = defaultdict(float)
    offset = 0.0

    nodos = list(grafo.keys())
    aristas = [
        (o, d)
        for o, destinos in grafo.items()
        for d in destinos
    ]

    entradas = {n: [] for n in nodos}
    salidas = {n: [] for n in nodos}

    for o, d in aristas:
        z = z_label(o, d)
        salidas[o].append(z)
        entradas[d].append(z)

    # Cota del objetivo clásico: máximo cambio vertical por salto x Lmax.
    max_delta_y = max(max_subida_fisica, max_caida_fisica)
    max_objetivo = max_saltos * max_delta_y
    P = float(max_objetivo + 1)

    # ------------------------------------------------------------
    # OBJETIVO CLÁSICO: minimizar variación vertical
    # ------------------------------------------------------------
    for o, d in aristas:
        add_linear(
            Q,
            z_label(o, d),
            abs(d[1] - o[1])
        )

    # ------------------------------------------------------------
    # START / GOAL
    # ------------------------------------------------------------
    offset = add_square(
        Q, offset,
        {z: 1 for z in salidas[start]},
        -1, P
    )
    offset = add_square(
        Q, offset,
        {z: 1 for z in entradas[goal]},
        -1, P
    )

    # Sin entradas a START ni salidas de GOAL.
    if entradas[start]:
        offset = add_square(
            Q, offset,
            {z: 1 for z in entradas[start]},
            0, P
        )
    if salidas[goal]:
        offset = add_square(
            Q, offset,
            {z: 1 for z in salidas[goal]},
            0, P
        )

    # u_START = u_GOAL = 1.
    offset = add_square(
        Q, offset,
        {u_label(start): 1},
        -1, P
    )
    offset = add_square(
        Q, offset,
        {u_label(goal): 1},
        -1, P
    )

    # ------------------------------------------------------------
    # RELACIÓN u_i <-> entradas/salidas
    # ------------------------------------------------------------
    for n in nodos:
        if n in (start, goal):
            continue

        coeff_in = {u_label(n): 1}
        for z in entradas[n]:
            coeff_in[z] = coeff_in.get(z, 0) - 1

        coeff_out = {u_label(n): 1}
        for z in salidas[n]:
            coeff_out[z] = coeff_out.get(z, 0) - 1

        offset = add_square(
            Q, offset, coeff_in, 0, P
        )
        offset = add_square(
            Q, offset, coeff_out, 0, P
        )

    # ------------------------------------------------------------
    # LONGITUD min <= L <= max
    # L = min + slack, slack in [0, max-min]
    # ------------------------------------------------------------
    max_slack_L = max_saltos - min_saltos
    pesos_L = pesos_binarios(max_slack_L)

    coeff = {
        z_label(o, d): 1
        for o, d in aristas
    }

    labels_slack_L = []
    for k, peso in enumerate(pesos_L):
        lab = f"sL_{k}"
        labels_slack_L.append((lab, peso))
        coeff[lab] = -peso

    offset = add_square(
        Q, offset,
        coeff,
        -min_saltos,
        P
    )

    # ------------------------------------------------------------
    # MINIMO DE SUBIDAS
    # N_up = min_up + slack_up
    # El exceso máximo posible se acota por Lmax-min_up.
    # ------------------------------------------------------------
    up_edges = [
        (o, d)
        for o, d in aristas
        if d[1] > o[1]
    ]
    max_slack_up = max_saltos - min_subidas
    pesos_up = pesos_binarios(max_slack_up)

    coeff = {
        z_label(o, d): 1
        for o, d in up_edges
    }

    labels_slack_up = []
    for k, peso in enumerate(pesos_up):
        lab = f"sUP_{k}"
        labels_slack_up.append((lab, peso))
        coeff[lab] = -peso

    offset = add_square(
        Q, offset,
        coeff,
        -min_subidas,
        P
    )

    # ------------------------------------------------------------
    # MINIMO DE BAJADAS
    # ------------------------------------------------------------
    down_edges = [
        (o, d)
        for o, d in aristas
        if d[1] < o[1]
    ]
    max_slack_down = max_saltos - min_bajadas
    pesos_down = pesos_binarios(max_slack_down)

    coeff = {
        z_label(o, d): 1
        for o, d in down_edges
    }

    labels_slack_down = []
    for k, peso in enumerate(pesos_down):
        lab = f"sDOWN_{k}"
        labels_slack_down.append((lab, peso))
        coeff[lab] = -peso

    offset = add_square(
        Q, offset,
        coeff,
        -min_bajadas,
        P
    )

    # ------------------------------------------------------------
    # NO SOLAPAMIENTO: u_i + u_j <= 1
    # Para binarias basta P*u_i*u_j
    # ------------------------------------------------------------
    solapes = pares_solapados(
        candidatas,
        ancho_plataforma
    )

    for i, j in solapes:
        add_quadratic(
            Q,
            u_label(i),
            u_label(j),
            P
        )

    # ------------------------------------------------------------
    # NO TRES SALTOS PLANOS CONSECUTIVOS
    # z1+z2+z3 <= 2
    # z1+z2+z3 + r0 + 2 r1 = 2
    # ------------------------------------------------------------
    triples = triples_planos(grafo)

    triple_aux = []
    for t_idx, triple in enumerate(triples):
        coeff = {}
        for o, d in triple:
            coeff[z_label(o, d)] = 1

        r0 = f"flat_{t_idx}_0"
        r1 = f"flat_{t_idx}_1"
        coeff[r0] = 1
        coeff[r1] = 2
        triple_aux.extend([r0, r1])

        offset = add_square(
            Q, offset,
            coeff,
            -2,
            P
        )

    # ------------------------------------------------------------
    # ANTIATAJOS:
    # u_i + u_j <= 1 + z_ij
    # u_i + u_j - z_ij + a0 + 2a1 = 1
    # ------------------------------------------------------------
    anti_aux = []

    for e_idx, (o, d) in enumerate(aristas):
        a0 = f"anti_{e_idx}_0"
        a1 = f"anti_{e_idx}_1"
        anti_aux.extend([a0, a1])

        coeff = {
            u_label(o): 1,
            u_label(d): 1,
            z_label(o, d): -1,
            a0: 1,
            a1: 2,
        }

        offset = add_square(
            Q, offset,
            coeff,
            -1,
            P
        )

    # Eliminar ceros.
    Q = {
        k: v
        for k, v in Q.items()
        if abs(v) > 1e-12
    }

    variables = set()
    for a, b in Q:
        variables.add(a)
        variables.add(b)

    meta = {
        "P": P,
        "max_objetivo": max_objetivo,
        "n_nodos": len(nodos),
        "n_aristas": len(aristas),
        "n_variables_u": len(nodos),
        "n_variables_z": len(aristas),
        "n_slack_longitud": len(labels_slack_L),
        "n_slack_subidas": len(labels_slack_up),
        "n_slack_bajadas": len(labels_slack_down),
        "n_pares_solapados": len(solapes),
        "n_triples_planos": len(triples),
        "n_aux_triples": len(triple_aux),
        "n_aux_antiatajo": len(anti_aux),
        "n_variables_total": len(variables),
        "n_terminos_qubo": len(Q),
        "labels_slack_L": labels_slack_L,
        "labels_slack_up": labels_slack_up,
        "labels_slack_down": labels_slack_down,
        "triples": triples,
        "solapes": solapes,
        "aristas": aristas,
    }

    return Q, offset, meta


def codificar_entero_en_bits(valor, labels_pesos):
    """Asigna bits binarios para representar exactamente valor."""
    muestra = {}
    restante = int(valor)

    # Greedy descendente funciona para pesos potencias de dos.
    for lab, peso in reversed(labels_pesos):
        if restante >= peso:
            muestra[lab] = 1
            restante -= peso
        else:
            muestra[lab] = 0

    if restante != 0:
        raise ValueError(
            f"No se puede codificar el valor {valor} "
            f"con {labels_pesos}"
        )

    return muestra


def muestra_desde_ruta_clasica(
    grafo,
    ruta,
    meta,
    min_saltos,
    min_subidas,
    min_bajadas,
):
    """Construye una asignación completa QUBO para una ruta clásica válida."""
    muestra = {}

    nodos = list(grafo.keys())
    aristas = meta["aristas"]
    ruta_edges = set(zip(ruta[:-1], ruta[1:]))
    usados = set(ruta)

    # u
    for n in nodos:
        muestra[u_label(n)] = int(n in usados)

    # z
    for o, d in aristas:
        muestra[z_label(o, d)] = int((o, d) in ruta_edges)

    # slacks globales
    L = len(ruta) - 1
    n_up = sum(
        1 for o, d in ruta_edges
        if d[1] > o[1]
    )
    n_down = sum(
        1 for o, d in ruta_edges
        if d[1] < o[1]
    )

    muestra.update(
        codificar_entero_en_bits(
            L - min_saltos,
            meta["labels_slack_L"],
        )
    )
    muestra.update(
        codificar_entero_en_bits(
            n_up - min_subidas,
            meta["labels_slack_up"],
        )
    )
    muestra.update(
        codificar_entero_en_bits(
            n_down - min_bajadas,
            meta["labels_slack_down"],
        )
    )

    # triples planos: slack = 2 - suma(z1,z2,z3)
    for t_idx, triple in enumerate(meta["triples"]):
        suma = sum(
            muestra[z_label(o, d)]
            for o, d in triple
        )
        slack = 2 - suma

        muestra[f"flat_{t_idx}_0"] = slack & 1
        muestra[f"flat_{t_idx}_1"] = (slack >> 1) & 1

    # antiatajos: slack = 1 - (u_i + u_j - z_ij)
    for e_idx, (o, d) in enumerate(aristas):
        expr = (
            muestra[u_label(o)]
            + muestra[u_label(d)]
            - muestra[z_label(o, d)]
        )
        slack = 1 - expr

        if slack < 0 or slack > 3:
            raise ValueError(
                f"La ruta viola antiatajos en {(o,d)}"
            )

        muestra[f"anti_{e_idx}_0"] = slack & 1
        muestra[f"anti_{e_idx}_1"] = (slack >> 1) & 1

    return muestra


def energia_qubo(Q, offset, muestra):
    energia = float(offset)
    for (v1, v2), coef in Q.items():
        energia += (
            coef
            * muestra.get(v1, 0)
            * muestra.get(v2, 0)
        )
    return energia


def objetivo_vertical(ruta):
    return sum(
        abs(d[1] - o[1])
        for o, d in zip(ruta[:-1], ruta[1:])
    )