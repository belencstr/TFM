"""Exporta una solución CP-SAT v3 del Caso 2 a JSON para Blender.

Genera de nuevo una solución con la misma formulación v3 y guarda:
- dimensiones del escenario;
- START y GOAL;
- ancho de plataforma;
- plataformas seleccionadas;
- ruta ordenada;
- métricas básicas.

El JSON se guarda con marca temporal dentro de resultados/.
"""

import json
import os
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.escenario_base import ANCHO, ALTO, START, GOAL

from modelo.grafo_saltos_segmentos import (
    ANCHO_PLATAFORMA,
    obtener_anclas_candidatas,
    construir_grafo_segmentos,
)

from solvers.generador_plataformas_cpsat_v3 import (
    generar_ruta_segmentos_cpsat,
)


MIN_SALTOS = 11
MAX_SALTOS = 14
MIN_SUBIDAS = 2
MIN_BAJADAS = 2
MAX_TIEMPO = 60.0
SEED = 20260824


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

    grafo = construir_grafo_segmentos(
        posiciones,
        START,
        GOAL,
    )

    resultado = generar_ruta_segmentos_cpsat(
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

    # Orden estable para que el JSON sea fácil de leer.
    plataformas = sorted(plataformas, key=lambda p: (p[0], p[1]))

    datos = {
        "caso": "Caso 2 - Plataformas",
        "version": "CP-SAT v3",
        "escenario": {
            "ancho": ANCHO,
            "alto": ALTO,
        },
        "start": convertir_posicion(START),
        "goal": convertir_posicion(GOAL),
        "ancho_plataforma": ANCHO_PLATAFORMA,
        "plataformas": [
            convertir_posicion(p)
            for p in plataformas
        ],
        "ruta": [
            convertir_posicion(p)
            for p in resultado["ruta"]
        ],
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

    carpeta = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta, exist_ok=True)

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")

    ruta_json = os.path.join(
        carpeta,
        f"caso2_nivel_blender_v3_{ANCHO}x{ALTO}_{marca}.json",
    )

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print("CASO 2 — EXPORTACIÓN PARA BLENDER")
    print("=" * 80)
    print(f"Estado CP-SAT: {resultado['status']}")
    print(f"Plataformas exportadas: {len(plataformas)}")
    print(f"Saltos: {resultado['num_saltos']}")
    print(f"JSON guardado en:")
    print(ruta_json)


if __name__ == "__main__":
    main()