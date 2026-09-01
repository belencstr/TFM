"""Ejecuta Gonzalez multiinicio sobre los mapas A, B y C.

Cada ejecución guarda automáticamente un registro TXT en la carpeta
`resultados/`, además de mostrar la salida por consola.
"""

import os
import sys
import time
from datetime import datetime

# Permite ejecutar el script directamente desde la carpeta experimentos.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_a import MAPA_A
from mapas.mapa_b import MAPA_B
from mapas.mapa_c import MAPA_C
from modelo.candidatas import obtener_candidatas
from modelo.distancias import construir_matriz_navegable
from modelo.grafo import construir_grafo, resumen_grafo
from solvers.gonzalez import gonzalez_multiinicio


K = 5


class Tee:
    """Duplica stdout: consola + fichero de resultados."""

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
    """Devuelve una representación ASCII marcando las monedas con 'o'."""
    copia = [list(fila) for fila in mapa]
    for candidata in seleccionadas:
        copia[candidata["fila"]][candidata["columna"]] = "o"
    return "\n".join("".join(fila) for fila in copia)


def ejecutar_mapa(nombre, mapa):
    candidatas = obtener_candidatas(mapa)
    grafo = construir_grafo(mapa)
    resumen = resumen_grafo(grafo)

    inicio_matriz = time.perf_counter()
    matriz = construir_matriz_navegable(candidatas, grafo)
    tiempo_matriz = time.perf_counter() - inicio_matriz

    inicio_solver = time.perf_counter()
    solucion = gonzalez_multiinicio(candidatas, matriz, K)
    tiempo_solver = time.perf_counter() - inicio_solver

    print("=" * 72)
    print(f"CASO 1 — GONZALEZ FARTHEST-FIRST — MAPA {nombre}")
    print("=" * 72)
    print(f"Dimensiones: {len(mapa)} x {len(mapa[0])}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"Nodos navegables: {resumen['nodos']}")
    print(f"Aristas: {resumen['aristas']}")
    print(f"Grafo conexo: {resumen['conexo']}")
    print(f"k: {K}")
    print("Distancia: navegable (camino mínimo en el grafo)")
    print()
    print(f"Mejor inicio: {solucion['id_inicio']}")
    print("Monedas seleccionadas:")
    for candidata in solucion["candidatas"]:
        print(
            f"  {candidata['id']} -> "
            f"(fila={candidata['fila']}, columna={candidata['columna']})"
        )
    print()
    print(f"Radio de cobertura: {solucion['radio_cobertura']}")
    print(f"Separación mínima: {solucion['separacion_minima']}")
    print(f"Separación media: {solucion['separacion_media']:.2f}")
    print(f"Separación total: {solucion['separacion_total']}")
    print(f"Tiempo matriz de distancias: {tiempo_matriz:.4f} s")
    print(f"Tiempo Gonzalez multiinicio: {tiempo_solver:.4f} s")
    print()
    print("Mapa resultante (o = moneda):")
    print(mapa_con_monedas(mapa, solucion["candidatas"]))
    print()

    return {
        "mapa": nombre,
        "candidatas": len(candidatas),
        "radio": solucion["radio_cobertura"],
        "sep_min": solucion["separacion_minima"],
        "sep_media": solucion["separacion_media"],
        "tiempo": tiempo_solver,
    }


def ejecutar_experimento():
    """Ejecuta los tres mapas y muestra el resumen comparativo."""
    resultados = []

    print("=" * 72)
    print("REGISTRO DEL EXPERIMENTO")
    print("=" * 72)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Algoritmo: Gonzalez Farthest-First multiinicio")
    print(f"k: {K}")
    print("Mapas evaluados: A, B y C")
    print()

    for nombre, mapa in (
        ("A", MAPA_A),
        ("B", MAPA_B),
        ("C", MAPA_C),
    ):
        resultados.append(ejecutar_mapa(nombre, mapa))

    print("=" * 72)
    print("RESUMEN COMPARATIVO")
    print("=" * 72)
    print(
        f"{'Mapa':<8}{'Candidatas':>12}{'Radio':>10}"
        f"{'Sep. mín.':>12}{'Sep. media':>14}{'Tiempo (s)':>14}"
    )
    for r in resultados:
        print(
            f"{r['mapa']:<8}{r['candidatas']:>12}{r['radio']:>10}"
            f"{r['sep_min']:>12}{r['sep_media']:>14.2f}{r['tiempo']:>14.4f}"
        )


def main():
    # Los registros se guardan en la raíz del proyecto:
    # caso1_colocacion_monedas/resultados/
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_fichero = f"gonzalez_tres_mapas_k{K}_{marca_tiempo}.txt"
    ruta_resultado = os.path.join(carpeta_resultados, nombre_fichero)

    stdout_original = sys.stdout

    try:
        with open(ruta_resultado, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar_experimento()
            print()
            print("=" * 72)
            print(f"Registro guardado en: {ruta_resultado}")
            print("=" * 72)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta_resultado}")


if __name__ == "__main__":
    main()
