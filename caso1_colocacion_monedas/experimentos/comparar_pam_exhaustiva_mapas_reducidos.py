"""Compara PAM frente a búsqueda exhaustiva en los tres mapas reducidos.

Cada ejecución guarda automáticamente un TXT en la carpeta `resultados/`.
"""

import os
import sys
import time
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_a_reducido import MAPA_A_REDUCIDO
from mapas.mapa_b_reducido import MAPA_B_REDUCIDO
from mapas.mapa_c_reducido import MAPA_C_REDUCIDO
from modelo.candidatas import obtener_candidatas
from modelo.distancias import construir_matriz_navegable
from modelo.grafo import construir_grafo, resumen_grafo
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo


K = 4


class Tee:
    """Duplica stdout en consola y fichero."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def mapa_con_monedas(mapa, seleccionadas):
    copia = [list(fila) for fila in mapa]
    for candidata in seleccionadas:
        copia[candidata["fila"]][candidata["columna"]] = "o"
    return "\n".join("".join(fila) for fila in copia)


def imprimir_solucion(titulo, solucion, tiempo, mapa):
    print(titulo)
    for candidata in solucion["candidatas"]:
        print(
            f"  {candidata['id']} -> "
            f"(fila={candidata['fila']}, columna={candidata['columna']})"
        )
    print(f"Coste total: {solucion['coste_total']}")
    print(
        "Distancia media a la moneda más cercana: "
        f"{solucion['distancia_media_cobertura']:.4f}"
    )
    print(f"Radio de cobertura: {solucion['radio_cobertura']}")
    print(f"Separación mínima: {solucion['separacion_minima']}")
    print(f"Tiempo: {tiempo:.6f} s")
    print("Mapa resultante (o = moneda):")
    print(mapa_con_monedas(mapa, solucion["candidatas"]))
    print()


def ejecutar_mapa(nombre, mapa):
    candidatas = obtener_candidatas(mapa)
    grafo = construir_grafo(mapa)
    resumen = resumen_grafo(grafo)
    matriz = construir_matriz_navegable(candidatas, grafo)

    inicio = time.perf_counter()
    pam = k_medoids_pam(candidatas, matriz, K)
    tiempo_pam = time.perf_counter() - inicio

    inicio = time.perf_counter()
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    tiempo_exacto = time.perf_counter() - inicio

    gap_abs = pam["coste_total"] - exacta["coste_total"]
    gap_pct = (
        100.0 * gap_abs / exacta["coste_total"]
        if exacta["coste_total"] != 0
        else 0.0
    )

    print("=" * 76)
    print(f"CASO 1 — MAPA REDUCIDO {nombre}")
    print("=" * 76)
    print(f"Dimensiones: {len(mapa)} x {len(mapa[0])}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"Nodos navegables: {resumen['nodos']}")
    print(f"Aristas: {resumen['aristas']}")
    print(f"Grafo conexo: {resumen['conexo']}")
    print(f"k: {K}")
    print("Distancia: navegable (camino mínimo en el grafo)")
    print()

    imprimir_solucion("PAM (BUILD + SWAP)", pam, tiempo_pam, mapa)

    print("BÚSQUEDA EXHAUSTIVA — ÓPTIMO GLOBAL")
    for candidata in exacta["candidatas"]:
        print(
            f"  {candidata['id']} -> "
            f"(fila={candidata['fila']}, columna={candidata['columna']})"
        )
    print(f"Coste óptimo: {exacta['coste_total']}")
    print(f"Combinaciones evaluadas: {exacta['combinaciones_evaluadas']}")
    print(f"Tiempo: {tiempo_exacto:.6f} s")
    print("Mapa óptimo (o = moneda):")
    print(mapa_con_monedas(mapa, exacta["candidatas"]))
    print()

    print("COMPARACIÓN")
    print(f"Gap absoluto PAM: {gap_abs}")
    print(f"Gap porcentual PAM: {gap_pct:.2f}%")
    print(f"PAM alcanza el óptimo: {pam['coste_total'] == exacta['coste_total']}")
    print()

    return {
        "mapa": nombre,
        "candidatas": len(candidatas),
        "pam": pam["coste_total"],
        "optimo": exacta["coste_total"],
        "gap_pct": gap_pct,
        "tiempo_pam": tiempo_pam,
        "tiempo_exacto": tiempo_exacto,
    }


def ejecutar_experimento():
    print("=" * 76)
    print("REGISTRO — PAM VS BÚSQUEDA EXHAUSTIVA")
    print("=" * 76)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Problema: k-medoids / p-median")
    print("Algoritmo clásico: PAM (BUILD + SWAP)")
    print("Referencia exacta: enumeración exhaustiva")
    print(f"k: {K}")
    print()

    resultados = []
    for nombre, mapa in (
        ("A", MAPA_A_REDUCIDO),
        ("B", MAPA_B_REDUCIDO),
        ("C", MAPA_C_REDUCIDO),
    ):
        resultados.append(ejecutar_mapa(nombre, mapa))

    print("=" * 92)
    print("RESUMEN COMPARATIVO")
    print("=" * 92)
    print(
        f"{'Mapa':<8}{'Candidatas':>12}{'PAM':>10}{'Óptimo':>10}"
        f"{'Gap (%)':>12}{'t PAM (s)':>14}{'t exacto (s)':>16}"
    )
    for r in resultados:
        print(
            f"{r['mapa']:<8}{r['candidatas']:>12}{r['pam']:>10}"
            f"{r['optimo']:>10}{r['gap_pct']:>12.2f}"
            f"{r['tiempo_pam']:>14.6f}{r['tiempo_exacto']:>16.6f}"
        )


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"pam_vs_exhaustiva_mapas_reducidos_k{K}_{marca_tiempo}.txt"
    ruta = os.path.join(carpeta_resultados, nombre)

    stdout_original = sys.stdout
    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar_experimento()
            print()
            print("=" * 76)
            print(f"Registro guardado en: {ruta}")
            print("=" * 76)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
