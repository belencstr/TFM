"""Comparación directa CP-SAT v4 vs QUBO equivalente.

Prueba reducida:
- mapa 18x5
- L en [4,5]
- al menos 2 subidas
- al menos 2 bajadas
- no 3 planos consecutivos
- antiatajos
- no solapamiento
- mismo objetivo: minimizar variación vertical

No se resuelve todavía el QUBO con SA. Primero se verifica la equivalencia:
la solución clásica debe tener penalización cero y energía igual al objetivo
clásico.
"""

import os
import sys
from datetime import datetime

RAIZ = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    ANCHO_PLATAFORMA,
    SUBIDA_MAX,
    CAIDA_MAX,
    obtener_anclas_candidatas,
    construir_grafo_segmentos_v4,
)

from solvers.generador_plataformas_cpsat_v4 import (
    generar_ruta_segmentos_cpsat_v4,
)

from cuantico.formulacion.qubo_caso2_equivalente import (
    construir_qubo_equivalente,
    muestra_desde_ruta_clasica,
    energia_qubo,
    objetivo_vertical,
)


ANCHO = 18
ALTO = 5
START = (0, 2)
GOAL = (17, 2)

MIN_SALTOS = 4
MAX_SALTOS = 5
MIN_SUBIDAS = 2
MIN_BAJADAS = 2

MAX_TIEMPO = 60.0
SEED = 20260827


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()


def ejecutar():
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

    # ----------------------------------------------------------
    # 1. MODELO CLÁSICO
    # ----------------------------------------------------------
    clasico = generar_ruta_segmentos_cpsat_v4(
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

    if clasico["ruta"] is None:
        raise RuntimeError(
            "CP-SAT no encuentra solución para la prueba."
        )

    ruta = clasico["ruta"]
    obj_clasico = objetivo_vertical(ruta)

    # ----------------------------------------------------------
    # 2. QUBO EQUIVALENTE
    # ----------------------------------------------------------
    Q, offset, meta = construir_qubo_equivalente(
        grafo=grafo,
        candidatas=candidatas,
        start=START,
        goal=GOAL,
        ancho_plataforma=ANCHO_PLATAFORMA,
        min_saltos=MIN_SALTOS,
        max_saltos=MAX_SALTOS,
        min_subidas=MIN_SUBIDAS,
        min_bajadas=MIN_BAJADAS,
        max_subida_fisica=SUBIDA_MAX,
        max_caida_fisica=CAIDA_MAX,
    )

    muestra = muestra_desde_ruta_clasica(
        grafo=grafo,
        ruta=ruta,
        meta=meta,
        min_saltos=MIN_SALTOS,
        min_subidas=MIN_SUBIDAS,
        min_bajadas=MIN_BAJADAS,
    )

    energia = energia_qubo(
        Q,
        offset,
        muestra,
    )

    penalizacion = energia - obj_clasico

    # ----------------------------------------------------------
    # SALIDA
    # ----------------------------------------------------------
    print("=" * 100)
    print("CASO 2 — COMPARACIÓN CP-SAT vs QUBO EQUIVALENTE")
    print("=" * 100)
    print()
    print("INSTANCIA DE PRUEBA")
    print(f"Mapa: {ANCHO} x {ALTO}")
    print(f"L clásico: [{MIN_SALTOS}, {MAX_SALTOS}]")
    print(f"Mínimo subidas: {MIN_SUBIDAS}")
    print(f"Mínimo bajadas: {MIN_BAJADAS}")
    print()

    print("MODELO CLÁSICO CP-SAT")
    print(f"Estado: {clasico['status']}")
    print(f"Tiempo: {clasico['tiempo']:.4f} s")
    print(f"Saltos: {clasico['num_saltos']}")
    print(f"Subidas: {clasico['num_subidas']}")
    print(f"Bajadas: {clasico['num_bajadas']}")
    print(f"Planos: {clasico['num_planos']}")
    print(f"Objetivo vertical: {obj_clasico}")
    print("Ruta:")
    print(" -> ".join(str(p) for p in ruta))
    print()

    print("QUBO EQUIVALENTE")
    print(f"P = {meta['P']}")
    print(f"Cota objetivo = {meta['max_objetivo']}")
    print(f"Variables z: {meta['n_variables_z']}")
    print(f"Variables u: {meta['n_variables_u']}")
    print(f"Slack longitud: {meta['n_slack_longitud']}")
    print(f"Slack subidas: {meta['n_slack_subidas']}")
    print(f"Slack bajadas: {meta['n_slack_bajadas']}")
    print(f"Triples planos: {meta['n_triples_planos']}")
    print(f"Auxiliares triples: {meta['n_aux_triples']}")
    print(f"Auxiliares antiatajo: {meta['n_aux_antiatajo']}")
    print(f"Variables QUBO totales: {meta['n_variables_total']}")
    print(f"Términos QUBO no nulos: {meta['n_terminos_qubo']}")
    print()

    print("COMPROBACIÓN DE EQUIVALENCIA")
    print(f"Objetivo clásico: {obj_clasico}")
    print(f"Energía QUBO total: {energia}")
    print(f"Penalización total: {penalizacion}")
    print(
        "Penalizaciones satisfechas: "
        f"{abs(penalizacion) < 1e-8}"
    )
    print(
        "Energía QUBO = objetivo clásico: "
        f"{abs(energia - obj_clasico) < 1e-8}"
    )

    if abs(penalizacion) > 1e-8:
        raise AssertionError(
            "La solución clásica no produce penalización cero."
        )

    if abs(energia - obj_clasico) > 1e-8:
        raise AssertionError(
            "La energía QUBO no coincide con el objetivo clásico."
        )

    print()
    print("VALIDACIÓN SUPERADA")


def main():
    carpeta = os.path.join(
        RAIZ,
        "cuantico",
        "resultados",
    )
    os.makedirs(
        carpeta,
        exist_ok=True,
    )

    marca = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    ruta_txt = os.path.join(
        carpeta,
        f"comparacion_clasico_qubo_equivalente_"
        f"{ANCHO}x{ALTO}_{marca}.txt",
    )

    original = sys.stdout

    try:
        with open(
            ruta_txt,
            "w",
            encoding="utf-8",
        ) as f:
            sys.stdout = Tee(
                original,
                f,
            )

            ejecutar()

            print()
            print(
                f"Registro guardado en: {ruta_txt}"
            )
    finally:
        sys.stdout = original

    print(
        f"\nTXT generado correctamente: {ruta_txt}"
    )


if __name__ == "__main__":
    main()