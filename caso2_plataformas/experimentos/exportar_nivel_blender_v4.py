"""Exporta una solución CP-SAT v4 del Caso 2 a JSON para Blender.

La v4 usa plataformas de ancho fijo y exige huecos reales entre plataformas.
El JSON incluye:
- dimensiones del escenario;
- START y GOAL;
- ancho de plataforma;
- plataformas seleccionadas;
- ruta ordenada;
- hueco de cada salto;
- métricas básicas.

El archivo se guarda con marca temporal dentro de resultados/.
"""

import json
import os
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.escenario_base import ANCHO, ALTO, START, GOAL

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

from solvers.generador_plataformas_cpsat_v4 import (
    generar_ruta_segmentos_cpsat_v4,
)


MIN_SALTOS = 11
MAX_SALTOS = 14
MIN_SUBIDAS = 2
MIN_BAJADAS = 2
MAX_TIEMPO = 60.0
SEED = 20260825


def convertir_posicion(pos):
    return {
        "x": int(pos[0]),
        "y": int(pos[1]),
    }


def main():
    candidatas = obtener_anclas_candidatas(
        ANCHO,
        ALTO,
        START,
        GOAL,
    )

    posiciones = [START] + candidatas + [GOAL]

    grafo = construir_grafo_segmentos_v4(
        posiciones,
        START,
        GOAL,
    )

    resultado = generar_ruta_segmentos_cpsat_v4(
        grafo,
        START,
        GOAL,
        min_saltos=MIN_SALTOS,
        max_saltos=MAX_SALTOS,
        min_subidas=MIN_SUBIDAS,
        min_bajadas=MIN_BAJADAS,
        max_tiempo=MAX_TIEMPO,
        seed=SEED,
    )

    if resultado["ruta"] is None:
        raise RuntimeError(
            f"CP-SAT no ha encontrado solución: {resultado['status']}"
        )

    plataformas = [
        p
        for p in resultado["nodos_usados"]
        if p not in (START, GOAL)
    ]

    plataformas = sorted(
        plataformas,
        key=lambda p: (p[0], p[1]),
    )

    saltos = []

    for origen, destino in zip(
        resultado["ruta"][:-1],
        resultado["ruta"][1:],
    ):
        hueco = calcular_hueco(
            origen,
            destino,
            START,
            GOAL,
        )

        saltos.append(
            {
                "origen": convertir_posicion(origen),
                "destino": convertir_posicion(destino),
                "hueco_tiles": int(hueco),
                "delta_y": int(destino[1] - origen[1]),
            }
        )

    datos = {
        "caso": "Caso 2 - Plataformas",
        "version": "CP-SAT v4",
        "escenario": {
            "ancho": ANCHO,
            "alto": ALTO,
        },
        "start": convertir_posicion(START),
        "goal": convertir_posicion(GOAL),
        "ancho_plataforma": ANCHO_PLATAFORMA,
        "fisica": {
            "hueco_min": HUECO_MIN,
            "hueco_max": HUECO_MAX,
            "subida_max": SUBIDA_MAX,
            "caida_max": CAIDA_MAX,
        },
        "plataformas": [
            convertir_posicion(p)
            for p in plataformas
        ],
        "ruta": [
            convertir_posicion(p)
            for p in resultado["ruta"]
        ],
        "saltos": saltos,
        "metricas": {
            "estado": resultado["status"],
            "tiempo_s": resultado["tiempo"],
            "saltos": resultado["num_saltos"],
            "plataformas_intermedias": len(resultado["ruta"]) - 2,
            "subidas": resultado["num_subidas"],
            "bajadas": resultado["num_bajadas"],
            "planos": resultado["num_planos"],
            "variacion_vertical": resultado["variacion_vertical"],
        },
        "parametros": {
            "min_saltos": MIN_SALTOS,
            "max_saltos": MAX_SALTOS,
            "min_subidas": MIN_SUBIDAS,
            "min_bajadas": MIN_BAJADAS,
            "seed": SEED,
        },
    }

    carpeta = os.path.join(
        RAIZ,
        "resultados",
    )
    os.makedirs(
        carpeta,
        exist_ok=True,
    )

    marca = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    ruta_json = os.path.join(
        carpeta,
        f"caso2_nivel_blender_v4_"
        f"{ANCHO}x{ALTO}_{marca}.json",
    )

    with open(
        ruta_json,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            datos,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("=" * 82)
    print("CASO 2 — EXPORTACIÓN V4 PARA BLENDER")
    print("=" * 82)
    print(f"Estado CP-SAT: {resultado['status']}")
    print(f"Plataformas exportadas: {len(plataformas)}")
    print(f"Saltos: {resultado['num_saltos']}")
    print(
        f"Huecos: "
        f"{min(s['hueco_tiles'] for s in saltos)} .. "
        f"{max(s['hueco_tiles'] for s in saltos)} tiles"
    )
    print("JSON guardado en:")
    print(ruta_json)


if __name__ == "__main__":
    main()