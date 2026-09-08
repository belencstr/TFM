# Caso 1 — Colocación de monedas

Versión reiniciada del Caso 1.

## Objetivo actual

Seleccionar `k = 5` posiciones candidatas para distribuir monedas de forma equilibrada sobre las zonas navegables del mapa.

El problema se plantea como **k-center discreto**. Para una solución `S`, el radio de cobertura es:

`R(S) = max_v min_s d(v,s)`

El objetivo es minimizar `R(S)`.

## Algoritmo clásico

Se utiliza **Gonzalez / Farthest-First Traversal** con multiinicio:

1. Se toma una candidata como primer centro.
2. Se añade iterativamente la candidata más alejada de su centro seleccionado más cercano.
3. Se repite hasta seleccionar `k` monedas.
4. Se ejecuta desde todas las candidatas posibles como inicio.
5. Se conserva la solución con menor radio de cobertura.

El objetivo principal es el radio de cobertura. La separación mínima y media se muestran únicamente como métricas descriptivas y como criterios de desempate.

## Estructura relevante

```text
mapas/
  mapa_a.py
  mapa_b.py
  mapa_c.py
modelo/
  candidatas.py
  grafo.py
  distancias.py
solvers/
  gonzalez.py
experimentos/
  ejecutar_gonzalez_tres_mapas.py
```

## Ejecución

Desde la raíz del proyecto:

```bash
python experimentos/ejecutar_gonzalez_tres_mapas.py
```

El script ejecuta el mismo procedimiento en los mapas A, B y C y muestra posiciones seleccionadas, radio de cobertura, separaciones, tiempos y una representación ASCII del resultado.

## Estado de QUBO y QAOA

Tras el estudio clásico de k-center y p-median, se dispone de la formulación cuántica (QUBO/QAOA) sobre la instancia mínima (`mapas/mapa_qaoa_minimo.py`):

1. **Formulación PLI directa (20 qubits)** (`experimentos/ejecutar_qaoa_minimo.py` y `experimentos/qaoa_tts_barrido.py`):
   - Mapeo clásico directo con variables $x_j$ e $y_{ij}$.
   - Espacio de Hilbert de $2^{20} = 1.048.576$ estados; estados factibles: $0,0092\%$.
   - Concluye en $TTS_{99} = \infty$ y $p_{\text{fact}} = 0,00\%$ debido a la hiperdilución del espacio y al mezclador estándar sin restricciones.

2. **Formulación compacta funcional (4 qubits)** (`modelo/qubo_pmedian_compacto.py`, `solvers/qaoa_compacto.py`):
   - Precomputación analítica de costes por pares $C(j, l)$, eliminando las variables auxiliares $y_{ij}$.
   - Reduce a 4 qubits ($16$ estados en el espacio de Hilbert), con un $37,5\%$ de estados factibles.
   - Ejecución en $< 0,3$ s, probabilidad de factibilidad $> 47\%$ y probabilidad óptima $> 16\%$ (alcanzando hasta el $85\%$), con $TTS_{99} < 0,3$ s.

3. **Experimentos reproducibles**:
   - `python experimentos/ejecutar_qaoa_compacto_minimo.py`: Ejecución individual con verificación exhaustiva.
   - `python experimentos/qaoa_compacto_tts_barrido.py`: Barrido sistemático de iteraciones COBYLA y disparos (*shots*) con cálculo de $TTS_{99}$.
   - `python experimentos/comparar_qaoa_20q_vs_4q.py`: Genera informe comparativo y gráfico en `figuras/comparativa_qaoa_20q_vs_4q.png`.

