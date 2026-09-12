"""Exporta a JSON una solución válida del QUBO reducido del Caso 2.

IMPORTANTE:
El QUBO se resuelve aquí con Simulated Annealing (SA), que es un algoritmo
clásico. El JSON representa, por tanto, una solución de la formulación QUBO
compatible con métodos cuánticos, no una ejecución sobre hardware cuántico.

La salida usa el mismo esquema JSON que exportar_nivel_blender_v4.py para
poder reutilizar el pipeline de Blender del modelo clásico.

Criterio de selección:
1. La muestra debe ser factible para el QUBO reducido.
2. La ruta reconstruida debe usar START -> GOAL.
3. No debe presentar atajo entre nodos seleccionados.
4. No debe contener más de dos saltos planos consecutivos.

Se usa la configuración de 50 sweeps porque es la que obtuvo el mejor TTS99
en el barrido realizado para el QUBO reducido 18x5.
"""

import json
import os
import sys
from collections import deque
from datetime import datetime

EXPERIMENTOS_DIR = os.path.dirname(os.path.abspath(__file__))
CUANTICO_DIR = os.path.dirname(EXPERIMENTOS_DIR)
BASE_CASO2 = os.path.dirname(CUANTICO_DIR)
RAIZ_REPO = os.path.dirname(BASE_CASO2)
RAIZ = BASE_CASO2

for p in (EXPERIMENTOS_DIR, CUANTICO_DIR, BASE_CASO2, RAIZ_REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from caso2_plataformas.modelo.grafo_saltos_segmentos_v4 import (
        ANCHO_PLATAFORMA,
        HUECO_MIN,
        HUECO_MAX,
        SUBIDA_MAX,
        CAIDA_MAX,
        obtener_anclas_candidatas,
        construir_grafo_segmentos_v4,
        calcular_hueco,
    )
    import caso2_plataformas.cuantico.formulacion.qubo_caso2_18x5 as qmod
    from caso2_plataformas.cuantico.solvers.simulated_annealing import resolver_qubo_sa
except ImportError:
    from modelo.grafo_saltos_segmentos_v4 import (
        ANCHO_PLATAFORMA,
        HUECO_MIN,
        HUECO_MAX,
        SUBIDA_MAX,
        CAIDA_MAX,
        obtener_anclas_candidatas,
        construir_grafo_segmentos_v4,
        calcular_hueco,
    )
    import cuantico.formulacion.qubo_caso2_18x5 as qmod
    from cuantico.solvers.simulated_annealing import resolver_qubo_sa


# -------------------------------------------------------------------------
# CONFIGURACIÓN FINAL DEL QUBO REDUCIDO
# -------------------------------------------------------------------------
qmod.C = 3.0

ANCHO = qmod.ANCHO
ALTO = qmod.ALTO
START = qmod.START
GOAL = qmod.GOAL

NUM_READS = 100
NUM_SWEEPS = 50
SEMILLAS = [
    20260902,
    20260903,
    20260904,
    20260905,
    20260906,
]


def convertir_posicion(pos):
    return {
        "x": int(pos[0]),
        "y": int(pos[1]),
    }


def bfs(grafo, inicio, meta):
    cola = deque([inicio])
    anterior = {inicio: None}

    while cola:
        actual = cola.popleft()

        if actual == meta:
            break

        for destino in grafo.get(actual, []):
            if destino not in anterior:
                anterior[destino] = actual
                cola.append(destino)

    if meta not in anterior:
        return None

    camino = []
    actual = meta

    while actual is not None:
        camino.append(actual)
        actual = anterior[actual]

    return list(reversed(camino))


def reconstruir_ruta(muestra):
    """Reconstruye la ruta ordenada START -> GOAL desde las aristas activas."""
    activas = [
        e
        for e, valor in muestra.items()
        if int(valor) == 1
    ]

    siguientes = {}

    for origen, destino in activas:
        siguientes.setdefault(origen, []).append(destino)

    ruta = [START]
    actual = START
    visitados = {START}

    while actual != GOAL:
        destinos = siguientes.get(actual, [])

        if len(destinos) != 1:
            return None

        actual = destinos[0]

        if actual in visitados:
            return None

        ruta.append(actual)
        visitados.add(actual)

        # Protección por si llega una muestra anómala.
        if len(ruta) > qmod.L_OBJETIVO + 2:
            return None

    return ruta


def delta_l(grafo, ruta):
    """Mide si existe un camino más corto entre los nodos seleccionados.

    delta_L = longitud de la ruta - longitud BFS mínima.
    delta_L = 0 implica que no hay atajo entre los nodos de la ruta.
    """
    nodos = set(ruta)

    subgrafo = {
        origen: [
            destino
            for destino in grafo.get(origen, [])
            if destino in nodos
        ]
        for origen in nodos
    }

    camino_bfs = bfs(
        subgrafo,
        START,
        GOAL,
    )

    if camino_bfs is None:
        return None

    return (
        (len(ruta) - 1)
        - (len(camino_bfs) - 1)
    )


def max_planos_consecutivos(ruta):
    maximo = 0
    actual = 0

    for origen, destino in zip(
        ruta[:-1],
        ruta[1:],
    ):
        if destino[1] == origen[1]:
            actual += 1
            maximo = max(maximo, actual)
        else:
            actual = 0

    return maximo


def metricas_ruta(ruta):
    saltos = list(zip(ruta[:-1], ruta[1:]))

    subidas = sum(
        1
        for o, d in saltos
        if d[1] > o[1]
    )
    bajadas = sum(
        1
        for o, d in saltos
        if d[1] < o[1]
    )
    planos = sum(
        1
        for o, d in saltos
        if d[1] == o[1]
    )
    variacion_vertical = sum(
        abs(d[1] - o[1])
        for o, d in saltos
    )

    return {
        "saltos": len(saltos),
        "subidas": subidas,
        "bajadas": bajadas,
        "planos": planos,
        "variacion_vertical": variacion_vertical,
    }


def buscar_muestra_valida(grafo, Q, offset):
    """Busca una muestra válida y devuelve una representante reproducible."""
    candidatas_validas = []

    for seed in SEMILLAS:
        print(
            f"Probando seed={seed} "
            f"con {NUM_READS} reads y {NUM_SWEEPS} sweeps..."
        )

        sampleset = resolver_qubo_sa(
            Q,
            num_reads=NUM_READS,
            num_sweeps=NUM_SWEEPS,
            seed=seed,
        )

        for datum in sampleset.data(
            fields=[
                "sample",
                "energy",
                "num_occurrences",
            ]
        ):
            muestra = {
                k: int(v)
                for k, v in datum.sample.items()
            }

            evaluacion = qmod.evaluar_restricciones(
                grafo,
                muestra,
            )

            if not evaluacion["factible_qubo"]:
                continue

            ruta = reconstruir_ruta(muestra)

            if ruta is None:
                continue

            dl = delta_l(
                grafo,
                ruta,
            )

            max_planos = max_planos_consecutivos(
                ruta
            )

            # Las dos condiciones que se dejaron fuera del QUBO reducido.
            if dl != 0:
                continue

            if max_planos > 2:
                continue

            energia_real = qmod.energia_qubo(
                Q,
                offset,
                muestra,
            )

            candidatas_validas.append(
                {
                    "seed": seed,
                    "muestra": muestra,
                    "ruta": ruta,
                    "energia": float(energia_real),
                    "ocurrencias": int(
                        datum.num_occurrences
                    ),
                    "delta_l": int(dl),
                    "max_planos_consecutivos": int(
                        max_planos
                    ),
                }
            )

    if not candidatas_validas:
        raise RuntimeError(
            "No se ha encontrado ninguna muestra que pase "
            "la validación completa. Prueba a aumentar las "
            "semillas o NUM_READS, manteniendo NUM_SWEEPS=50 "
            "si quieres conservar la configuración elegida por TTS."
        )

    # Todos los estados válidos del QUBO reducido tienen energía 0.
    # Para que la selección sea determinista, priorizo:
    #   1) menor energía,
    #   2) mayor número de ocurrencias,
    #   3) seed menor,
    #   4) ruta lexicográficamente menor.
    candidatas_validas.sort(
        key=lambda r: (
            r["energia"],
            -r["ocurrencias"],
            r["seed"],
            tuple(r["ruta"]),
        )
    )

    return candidatas_validas[0], len(candidatas_validas)


def guardar_json_nivel(ruta, seleccion=None, c=3.0, num_sweeps=NUM_SWEEPS, num_reads=NUM_READS, seed=None):
    """Genera y guarda el archivo JSON de un nivel del Caso 2 para Blender."""
    metricas = metricas_ruta(ruta)
    plataformas = [p for p in ruta if p not in (START, GOAL)]

    saltos = []
    for origen, destino in zip(ruta[:-1], ruta[1:]):
        hueco = calcular_hueco(origen, destino, START, GOAL)
        saltos.append({
            "origen": convertir_posicion(origen),
            "destino": convertir_posicion(destino),
            "hueco_tiles": int(hueco),
            "delta_y": int(destino[1] - origen[1]),
        })

    if seleccion is None:
        seleccion = {
            "energia": 0.0,
            "delta_l": 0,
            "max_planos_consecutivos": max_planos_consecutivos(ruta),
            "seed": seed if seed is not None else 20260902,
            "ocurrencias": 1,
        }

    datos = {
        "caso": "Caso 2 - Plataformas",
        "version": "QUBO reducido 18x5 + Simulated Annealing",
        "nota_metodologica": (
            "La formulación es QUBO, pero la muestra se obtiene "
            "con Simulated Annealing clásico."
        ),
        "escenario": {
            "ancho": int(ANCHO),
            "alto": int(ALTO),
        },
        "start": convertir_posicion(START),
        "goal": convertir_posicion(GOAL),
        "ancho_plataforma": int(ANCHO_PLATAFORMA),
        "fisica": {
            "hueco_min": int(HUECO_MIN),
            "hueco_max": int(HUECO_MAX),
            "subida_max": int(SUBIDA_MAX),
            "caida_max": int(CAIDA_MAX),
        },
        "plataformas": [convertir_posicion(p) for p in plataformas],
        "ruta": [convertir_posicion(p) for p in ruta],
        "saltos": saltos,
        "metricas": {
            "factible_qubo": True,
            "validacion_completa": True,
            "energia_qubo": seleccion.get("energia", 0.0),
            "delta_l_atajo": seleccion.get("delta_l", 0),
            "max_planos_consecutivos": seleccion.get("max_planos_consecutivos", 0),
            "saltos": metricas["saltos"],
            "plataformas_intermedias": len(plataformas),
            "subidas": metricas["subidas"],
            "bajadas": metricas["bajadas"],
            "planos": metricas["planos"],
            "variacion_vertical": metricas["variacion_vertical"],
        },
        "parametros": {
            "C": float(c),
            "L_objetivo": int(qmod.L_OBJETIVO),
            "subidas_objetivo": int(qmod.SUBIDAS_OBJETIVO),
            "bajadas_objetivo": int(qmod.BAJADAS_OBJETIVO),
            "num_reads": int(num_reads),
            "num_sweeps": int(num_sweeps),
            "seed_seleccionada": int(seleccion.get("seed", 0)),
            "ocurrencias_muestra": int(seleccion.get("ocurrencias", 1)),
            "semillas_probadas": [int(s) for s in SEMILLAS],
            "muestras_validas_distintas_encontradas": 1,
        },
    }

    carpeta = os.path.join(RAIZ, "cuantico", "resultados")
    os.makedirs(carpeta, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_json = os.path.join(carpeta, f"caso2_nivel_blender_qubo_reducido_{ANCHO}x{ALTO}_{marca}.json")
    ruta_fija = os.path.join(carpeta, f"caso2_nivel_blender_qubo_reducido_{ANCHO}x{ALTO}.json")

    for r_dest in (ruta_json, ruta_fija):
        with open(r_dest, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)

    # Copiar también en caso2_plataformas/resultados para compatibilidad
    res_base = os.path.join(RAIZ, "resultados")
    if os.path.exists(res_base):
        with open(os.path.join(res_base, f"caso2_nivel_blender_qubo_reducido_{ANCHO}x{ALTO}.json"), "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)

    return ruta_fija


def main():
    candidatas = obtener_anclas_candidatas(
        ANCHO,
        ALTO,
        START,
        GOAL,
    )

    posiciones = [
        START,
        *candidatas,
        GOAL,
    ]

    grafo = construir_grafo_segmentos_v4(
        posiciones,
        START,
        GOAL,
    )

    Q, offset = qmod.construir_qubo(
        grafo
    )

    seleccion, n_validas = buscar_muestra_valida(
        grafo,
        Q,
        offset,
    )

    ruta = seleccion["ruta"]
    ruta_json = guardar_json_nivel(
        ruta,
        seleccion=seleccion,
        c=qmod.C,
        num_sweeps=NUM_SWEEPS,
        num_reads=NUM_READS,
        seed=seleccion["seed"],
    )
    metricas = metricas_ruta(ruta)
    plataformas = [p for p in ruta if p not in (START, GOAL)]

    print()
    print("=" * 90)
    print("CASO 2 — EXPORTACIÓN QUBO REDUCIDO PARA BLENDER")
    print("=" * 90)
    print(
        "Método de resolución: Simulated Annealing clásico "
        "sobre formulación QUBO."
    )
    print(f"Seed seleccionada: {seleccion['seed']}")
    print(f"Energía QUBO: {seleccion['energia']}")
    print(
        f"Muestras válidas encontradas: {n_validas}"
    )
    print(
        f"Plataformas exportadas: {len(plataformas)}"
    )
    print(f"Saltos: {metricas['saltos']}")
    print(f"Subidas: {metricas['subidas']}")
    print(f"Bajadas: {metricas['bajadas']}")
    print(f"Planos: {metricas['planos']}")
    print(
        f"Delta_L antiatajo: {seleccion['delta_l']}"
    )
    print(
        "Máximo de planos consecutivos: "
        f"{seleccion['max_planos_consecutivos']}"
    )
    print("Ruta:")
    print(
        " -> ".join(
            str(p)
            for p in ruta
        )
    )
    print()
    print("JSON guardado en:")
    print(ruta_json)


if __name__ == "__main__":
    main()