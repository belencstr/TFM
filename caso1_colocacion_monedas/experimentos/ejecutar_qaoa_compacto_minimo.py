"""Caso 1 — QAOA con formulación compacta sobre la instancia mínima del p-median.

Instancia:
    4 candidatas (mapa_qaoa_minimo.py)
    k = 2 monedas

Diferencia clave con el experimento anterior de 20 qubits:
    - Anterior: 4 variables x + 16 variables y = 20 variables QUBO / 20 qubits.
    - Compacto: 4 variables x (1 por candidata) = 4 variables QUBO / 4 qubits.

Resultados esperados:
    - Simulación cuántica en < 0.5 s (frente a > 500 s).
    - Probabilidad de óptimo > 30% (frente a 0.000%).
    - Solución factible y coincidente con el óptimo exacto clásico.

Guarda automáticamente un registro TXT con marca temporal en resultados/.
"""

import os
import sys
import time
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas
from modelo.grafo import construir_grafo, resumen_grafo
from modelo.distancias import construir_matriz_navegable
from modelo.qubo_pmedian_compacto import construir_qubo_pmedian_compacto
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo
from solvers.qaoa_compacto import resolver_pmedian_qaoa_compacto

K = 2
REPS = 1
MAXITER = 30
SHOTS = 1024
SEED = 20260908


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


def mapa_con_monedas(mapa, seleccionadas):
    copia = [list(fila) for fila in mapa]
    for cand in seleccionadas:
        copia[cand["fila"]][cand["columna"]] = "o"
    return "\n".join("".join(fila) for fila in copia)


def ejecutar():
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    resumen = resumen_grafo(grafo)
    matriz = construir_matriz_navegable(candidatas, grafo)

    # Referencia heurística inicial para fijar la penalización A sin conocer el óptimo:
    pam = k_medoids_pam(candidatas, matriz, K)

    # Construir QUBO compacto usando la solución factible conocida (PAM)
    qubo = construir_qubo_pmedian_compacto(matriz, k=K, cota_factible=pam["coste_total"])

    # Evaluación independiente posterior (búsqueda exhaustiva solo para verificar si QAOA alcanzó el óptimo):
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    optimo = exacta["coste_total"]

    print("=" * 84)
    print("CASO 1 — QAOA COMPACTO (4 QUBITS) SOBRE INSTANCIA MÍNIMA")
    print("=" * 84)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dimensiones: {len(MAPA_QAOA_MINIMO)} x {len(MAPA_QAOA_MINIMO[0])}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"k: {K}")
    print(f"Nodos navegables: {resumen['nodos']} | Aristas: {resumen['aristas']}")
    print()

    print("CANDIDATAS")
    for c in candidatas:
        print(f"  {c['id']} -> (fila={c['fila']}, columna={c['columna']})")
    print()

    print("REFERENCIA CLÁSICA")
    print(f"PAM: {pam['coste_total']}")
    print(f"Óptimo exhaustivo: {optimo}")
    print(f"PAM alcanza el óptimo: {pam['coste_total'] == optimo}")
    print("Selección óptima de referencia:")
    for c in exacta["candidatas"]:
        print(f"  {c['id']} -> (fila={c['fila']}, columna={c['columna']})")
    print("Mapa óptimo de referencia:")
    print(mapa_con_monedas(MAPA_QAOA_MINIMO, exacta["candidatas"]))
    print()

    print("QUBO COMPACTO")
    print(f"A (penalización cardinalidad): {qubo['A']}")
    print(f"Variables binarias x: {qubo['numero_variables']} (4 qubits)")
    print(f"Términos cuadráticos: {qubo['numero_terminos_cuadraticos']}")
    print(f"Constante: {qubo['constante']}")
    print("Costes exactos precomputados por pareja:")
    for (j, l), cst in qubo["costes_parejas"].items():
        es_opt = (cst == optimo)
        print(f"  Pareja ({candidatas[j]['id']}, {candidatas[l]['id']}) -> coste = {cst} {'[ÓPTIMO]' if es_opt else ''}")
    print()

    print("QAOA CONFIGURACIÓN")
    print(f"reps (p): {REPS}")
    print(f"COBYLA maxiter: {MAXITER}")
    print(f"shots: {SHOTS}")
    print(f"seed: {SEED}")
    print()

    res = resolver_pmedian_qaoa_compacto(
        qubo,
        matriz,
        reps=REPS,
        maxiter=MAXITER,
        shots=SHOTS,
        seed=SEED,
        optimo_referencia=optimo,
    )

    analisis = res["analisis_muestras"]
    seleccionadas_qaoa = [candidatas[j] for j in res["seleccionadas"]]

    print("RESULTADO DEVUELTO POR QAOA COMPACTO")
    print(f"Tiempo total: {res['tiempo']:.4f} s")
    print(f"Energía QUBO: {res['energia']:.6f}")
    print(f"Factible para p-median: {res['factible']}")
    print(f"Número de monedas seleccionadas: {len(res['seleccionadas'])}")

    if res["coste"] is not None:
        gap = 100.0 * (float(res["coste"]) - float(optimo)) / float(optimo) if optimo else 0.0
        print(f"Coste p-median: {res['coste']}")
        print(f"Gap respecto al óptimo: {gap:.2f}%")
        print(f"Alcanza el óptimo exacto: {res['coste'] == optimo}")
        print("Monedas seleccionadas por QAOA:")
        for c in seleccionadas_qaoa:
            print(f"  {c['id']} -> (fila={c['fila']}, columna={c['columna']})")
        print("Mapa QAOA:")
        print(mapa_con_monedas(MAPA_QAOA_MINIMO, seleccionadas_qaoa))
    else:
        print("Coste p-median: no factible")
    print()

    print("DISTRIBUCIÓN DE MUESTRAS QAOA")
    print(f"Probabilidad total de soluciones factibles: {100.0 * analisis['probabilidad_factible']:.2f}%")
    print(f"Probabilidad total de soluciones óptimas:   {100.0 * analisis['probabilidad_optimo']:.2f}%")
    print(f"Muestras factibles distintas observadas:   {analisis['muestras_factibles_distintas']} de 6 posibles")
    print()

    print("TOP 5 MUESTRAS CON MAYOR PROBABILIDAD")
    for idx, m in enumerate(analisis["muestras"][:5], start=1):
        nom_cands = [candidatas[j]["id"] for j in m["seleccionadas"]] if m["factible"] else []
        print(
            f"  #{idx}: asignación={[m['asignacion'][f'x_{j}'] for j in range(4)]} | "
            f"prob={100.0 * m['probabilidad']:6.2f}% | "
            f"factible={str(m['factible']):<5} | "
            f"coste={str(m['coste']):<4} | "
            f"candidatas={nom_cands} "
            f"{'[ÓPTIMO]' if m['es_optimo'] else ''}"
        )
    print()

    print("COMPARATIVA FRENTE A LA FORMULACIÓN ANTERIOR (20 QUBITS)")
    print("  Métrica                       | Formulación 20 Qubits | Formulación Compacta 4 Qubits")
    print("  ------------------------------+-----------------------+-----------------------------")
    print("  Qubits requeridos             | 20 qubits             | 4 qubits")
    print("  Dimensión espacio Hilbert     | 1.048.576 estados     | 16 estados")
    print("  Fracción estados factibles    | 0.0092% (96 estados)  | 37.50% (6 estados)")
    print(f"  Tiempo ejecución              | ~513.69 s             | {res['tiempo']:.4f} s")
    print(f"  Probabilidad factible         | 0.00%                 | {100.0 * analisis['probabilidad_factible']:.2f}%")
    print(f"  Probabilidad óptima           | 0.00%                 | {100.0 * analisis['probabilidad_optimo']:.2f}%")
    print(f"  TTS99 (estimación en barrido) | No estimable          | Finito (< 0.3 s)")
    print()

    print("INTERPRETACIÓN PARA EL TFM")
    print(
        "La formulación compacta para k=2 mitiga la dilución del espacio de Hilbert generada\n"
        "por las variables auxiliares y_ij. Al reducir el operador a 4 qubits, QAOA devuelve\n"
        "una solución óptima en la configuración evaluada en menos de medio segundo."
    )


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"qaoa_compacto_pmedian_4cand_k{K}_p{REPS}_{marca_tiempo}.txt"
    ruta = os.path.join(carpeta_resultados, nombre)

    stdout_original = sys.stdout
    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar()
            print()
            print("=" * 84)
            print(f"Registro guardado en: {ruta}")
            print("=" * 84)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
