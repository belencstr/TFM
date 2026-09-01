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

## Fuera de alcance por ahora

En esta fase no se utilizan restricciones de distancia mínima, penalizaciones de borde, CP-SAT, QUBO ni QAOA. Esos elementos se estudiarán únicamente después de validar que el objetivo clásico representa adecuadamente la distribución deseada.
