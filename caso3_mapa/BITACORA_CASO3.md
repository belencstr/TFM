# Cuaderno de Bitácora — Caso 3: Generación Procedural de Mapas 2D con Obstáculos, Coherencia Espacial y Gameplay

**Trabajo Fin de Máster en Computación Cuántica**  
**Autor:** Belén Castro  
**Proyecto:** *Generación procedural de contenido mediante optimización cuántica: Estudio exploratorio con formulaciones QUBO en entornos tridimensionales*  
**Entorno de experimentación:** CPU Local (Intel Core), Google OR-Tools CP-SAT v9.8, D-Wave Ocean SDK (`dwave-samplers`), Blender 5.2.0 LTS  
**Fecha de consolidación:** Septiembre de 2026  

---

## Índice de Entradas de Bitácora

1. [Entrada 1: Planteamiento y Salto Cualitativo respecto a los Casos 1 y 2](#entrada-1-planteamiento-y-salto-cualitativo-respecto-a-los-casos-1-y-2)
2. [Entrada 2: Intentos Fallidos y Decisiones Iniciales — La Agregación Trivial de Ising](#entrada-2-intentos-fallidos-y-decisiones-iniciales--la-agregación-trivial-de-ising)
3. [Entrada 3: La Evolución Clásica CP-SAT (v1 → v2 → v3)](#entrada-3-la-evolución-clásica-cp-sat-v1--v2--v3)
4. [Entrada 4: Por qué nace el CP-SAT Core — La Corrección Metodológica 1-a-1](#entrada-4-por-qué-nace-el-cp-sat-core--la-corrección-metodológica-1-a-1)
5. [Entrada 5: Derivación Analítica A Priori de Penalizaciones (P > 82 aristas)](#entrada-5-derivación-analítica-a-priori-de-penalizaciones-p--82-aristas)
6. [Entrada 6: El QUBO Desacoplado (48 variables) y el Fallo de Navegabilidad](#entrada-6-el-qubo-desacoplado-48-variables-y-el-fallo-de-navegabilidad)
7. [Entrada 7: El QUBO Integrado (96 variables) y la Poda de Manhattan](#entrada-7-el-qubo-integrado-96-variables-y-la-poda-de-manhattan)
8. [Entrada 8: Validación Real de Variables q vs. Algoritmos BFS](#entrada-8-validación-real-de-variables-q-vs-algoritmos-bfs)
9. [Entrada 9: Estudio Experimental de Robustez en 20 Semillas y Time To Solution (TTS)](#entrada-9-estudio-experimental-de-robustez-en-20-semillas-y-time-to-solution-tts)
10. [Entrada 10: La Discusión Científica Honesta — Factibilidad vs. Calidad y Componentes Conexas](#entrada-10-la-discusión-científica-honesta--factibilidad-vs-calidad-y-componentes-conexas)
11. [Entrada 11: Pipeline de Visualización 3D en Blender 5.2](#entrada-11-pipeline-de-visualización-3d-en-blender-52)

---

## Entrada 1: Planteamiento y Salto Cualitativo respecto a los Casos 1 y 2

### Contexto del Proyecto
En la primera etapa del TFM abordé problemas con restricciones espaciales progresivas:
- **Caso 1 (Colocación de Monedas):** El escenario venía dado de antemano y era 100% transitable. El solver solo decidía la ubicación óptima de $k=5$ recompensas mediante una formulación clásica de $k$-center / $p$-mediana.
- **Caso 2 (Plataformas con Salto):** Introduje física unidireccional y saltos parabólicos discretos. Aunque el optimizador decidía qué plataformas existían y sus alturas, la progresión era secuencial a lo largo de un único eje horizontal.

### El reto del Caso 3
En el Caso 3 doy el salto más ambicioso del TFM: **generar proceduralmente la propia topología y geometría del mapa desde cero**.
No existe un mapa preestablecido. Para una cuadrícula de $6 \times 8$ ($48$ celdas), el modelo matemático debe determinar simultáneamente:
1. Qué celdas son suelo transitable ($x_c = 1$) y cuáles son muros infranqueables ($x_c = 0$).
2. Que exista un camino transitable continuo desde START $(0, 0)$ hasta GOAL $(5, 7)$.
3. Que los muros no aparezcan dispersos como "ruido blanco" o tablero de ajedrez, sino agrupados en paredes legibles.
4. Que el nivel albergue una distribución de juego estimulante (enemigos y trofeos).

---

## Entrada 2: Intentos Fallidos y Decisiones Iniciales — La Agregación Trivial de Ising

### El fallo del modelo puro sin partición
En las primeras pruebas, formulé un modelo clásico y cuántico simple:
- Minimizar el perímetro de contacto entre suelo y muro: $\min \sum_{(u,v)} |x_u - x_v|$.
- Exigir una cuota global de obstáculos: $\sum_c (1 - x_c) = 20$ (es decir, $28$ suelos transitables de 48 casillas).

**Resultado obtenido:**
El solver agrupó todos los 20 muros en un único bloque sólido pegado a la pared exterior, dejando el resto del mapa como una gran sala vacía.
- Matemáticamente: es el estado fundamental (*ground state*) ferromagnético perfecto, pues minimiza el perímetro.
- Lúdicamente: **es un desastre de diseño de niveles**. El jugador tiene una habitación vacía sin obstáculos ni pasillos interesantes.

### La solución: Partición en 4 Zonas Geométricas
Para forzar la existencia de pasillos y estrechamientos sin fijar celdas a mano, dividí la cuadrícula de $6 \times 8$ en cuatro cuadrantes disjuntos de $3 \times 4$ celdas (12 celdas cada uno):
- **Zona A:** filas $[0..2]$, cols $[0..3]$ (cuadrante superior izquierdo).
- **Zona B:** filas $[0..2]$, cols $[4..7]$ (cuadrante superior derecho).
- **Zona C:** filas $[3..5]$, cols $[0..3]$ (cuadrante inferior izquierdo).
- **Zona D:** filas $[3..5]$, cols $[4..7]$ (cuadrante inferior derecho).

Impuse de forma estricta:
$$\sum_{c \in Z} (1 - x_c) = 5 \iff \sum_{c \in Z} x_c = 7 \quad \forall Z \in \{A, B, C, D\}$$
Esto obliga a repartir $5$ muros en cada cuadrante, garantizando pasillos, quiebros y cobertura en todo el nivel.

---

## Entrada 3: La Evolución Clásica CP-SAT (v1 → v2 → v3)

Para construir la línea base clásica de referencia utilicé Google OR-Tools CP-SAT, iterando a lo largo de tres versiones:

1. **CP-SAT v1 (Línea base simple):**
   - Geometría de suelo y muros balanceada por zonas.
   - Conservación de flujo para la ruta principal START $\to$ GOAL.
   - *Problema:* Las recompensas y enemigos quedaban diseminados sin coherencia de progresión narrativa.

2. **CP-SAT v2 (Primera bifurcación):**
   - Se añadió una rama secundaria de desvío con un enemigo.
   - *Problema:* Una rama ciega que solo contiene un peligro castiga al jugador sin recompensar la exploración, rompiendo la heurística clásica de diseño de videojuegos (*risk vs. reward*).

3. **CP-SAT v3 (Demostrador Final de Gameplay):**
   - Estructura formal de desvío ciego (*dead-end* de exactamente 2 casillas): una casilla de acceso conectada a la ruta con 2 vecinos libres, y una casilla terminal ciega con 1 único vecino libre.
   - En la casilla terminal ciega se coloca una **recompensa secreta** (trofeo de exploración).
   - En la ruta principal: 1 trofeo temprano (pasos 2..4) y 2 enemigos secuenciales (pasos 5..7 y 9..11).
   - Para seleccionar la rama de 2 celdas entre todas las combinaciones posibles, el solver evalúa simultáneamente **116 pares candidatos** mediante restricciones canalizadas.
   - **Resultado:** 238 variables principales + 130 variables auxiliares = **368 variables booleanas totales**. Se resuelve a `OPTIMAL` en 18.26 s con un coste de **22 transiciones** de frontera.

---

## Entrada 4: Por qué nace el CP-SAT Core — La Corrección Metodológica 1-a-1

### El problema de la asimetría
Durante el desarrollo del Caso 3 me di cuenta de un problema metodológico de primer orden:
- El **CP-SAT v3 Completo** resuelve geometría + ruta + rama de exploración (116 pares) + recompensas + enemigos ($368$ variables).
- El **QUBO Integrado** resuelve geometría + ruta ($96$ variables).
- Comparar directamente ambos solvers y concluir algo sobre la eficacia de QUBO frente a CP-SAT **era una comparación asimétrica y científicamente injusta**.

### La decisión: Crear el CP-SAT Core
En lugar de forzar los 116 pares de rama y los elementos de gameplay dentro del QUBO (lo que habría disparado el número de qubits a más de 400 mediante variables de holgura), la decisión limpia y rigurosa fue **desacoplar los dos alcances**:
1. **CP-SAT Completo (Demostrador Final):** Se conserva como el techo visual y lúdico de lo que puede hacer un solver clásico completo (368 variables).
2. **CP-SAT Core:** Se implementó en `caso3_cpsat_core.py` resolviendo **estrictamente el mismo problema que el QUBO integrado**:
   - 48 variables de suelo $x_c$.
   - 48 variables de ruta principal podada $q_{t,c}$.
   - 82 variables auxiliares de frontera $b_{uv} \ge |x_u - x_v|$.
   - Total solver: 96 variables de decisión + 82 auxiliares = **178 variables**.

**Resultado del CP-SAT Core:**
- Estado: `OPTIMAL` demostrado en **2.189 s**.
- Valor objetivo: **20 fronteras** (el óptimo global absoluto del problema core).
- Componentes conexas: 1 única componente.

Ahora sí disponemos de una comparativa científica 1-a-1 incontestable.

---

## Entrada 5: Derivación Analítica A Priori de Penalizaciones (P > 82 aristas)

### La objeción del tribunal en el Caso 1
En el Caso 1, el tutor señaló con razón que fijar multiplicadores de penalización como $P = 12, 15, 30$ parecía una sintonización empírica arbitraria (*ad-hoc*).

### La demostración para el Caso 3
En una cuadrícula $M \times N = 6 \times 8$:
- Cada arista interna horizontal representa un contacto ortogonal entre $(r, c)$ y $(r, c+1)$: $M(N - 1) = 6 \times 7 = 42$.
- Cada arista interna vertical representa un contacto entre $(r, c)$ y $(r+1, c)$: $(M - 1)N = 5 \times 8 = 40$.
- **Número total de aristas:** $|E| = 42 + 40 = 82\text{ aristas}$.

Dado que la función objetivo de fronteras mide la suma de discontinuidades a través de las aristas:
$$F(x) = \sum_{(u, v) \in E} |x_u - x_v|$$
Como cada término $|x_u - x_v| \in \{0, 1\}$, la función objetivo está estrictamente acotada a priori:
$$0 \le F(x) \le 82$$

### Conclusión teórica:
Fijando una penalización conservadora **$P = 100 > 82$**:
- Si una muestra viola una sola restricción de zona o de START/GOAL, su energía se incrementa en al menos $+100$.
- Como el objetivo nunca puede mejorar en más de $82$, **ninguna violación de restricción puede ser compensada energéticamente por una reducción en fronteras**.
- Esta cota es válida a priori y no requiere conocer previamente la solución del CP-SAT.

---

## Entrada 6: El QUBO Desacoplado (48 variables) y el Fallo de Navegabilidad

### Formulación
En `qubo_caso3.py` planteé un modelo de geometría pura:
- $48$ variables binarias $x_c \in \{0, 1\}$.
- Coherencia tipo Ising: $\sum_{(u,v)} (x_u + x_v - 2 x_u x_v)$.
- Penalización de zonas ($P=100$) y START/GOAL.
- Total de acoplamientos cuadráticos: $278$.

### Resultado experimental
- Tiempo medio de muestreo: $0.104\text{ s}$ en CPU (100 reads en Simulated Annealing).
- Cumplimiento de zonas: $100\%$ (las 4 zonas tienen exactamente 5 muros en todas las muestras).
- **Problema crítico de navegabilidad:** Solo el **8.30% ± 2.51%** de las muestras generadas contienen un camino continuo START $\to$ GOAL según BFS.

### La divergencia clave: Mínimo de energía vs. Mejor muestra válida
- **Muestra de mínima energía bruta:** Obtiene un promedio de $31.80 \pm 1.86$ fronteras, pero el mapa queda frecuentemente bloqueado por muros en el centro (inviable).
- **Mejor muestra válida:** Requiere $34.55 \pm 2.13$ fronteras para permitir la ruta BFS de 12 movimientos.
- Conclusión: El modelo desacoplado requiere un filtro clásico a posteriori que descarte más del $91\%$ de las muestras. Su estimación empírica de $TTS_{99}$ en CPU es de **$63.47 \pm 28.29\text{ ms}$**.

---

## Entrada 7: El QUBO Integrado (96 variables) y la Poda de Manhattan

### El reto de la dimensión del espacio
Si definiéramos una variable binaria $q_{t,c}$ por cada paso temporal $t \in [0..12]$ y por cada celda $c$ (48 celdas), tendríamos $13 \times 48 = 624$ variables. Para los procesadores cuánticos actuales (NISQ), este tamaño es prohibitivo.

### Poda mediante Conos de Manhattan
Dado que la distancia mínima Manhattan entre $(0,0)$ y $(5,7)$ es de 12 movimientos (13 celdas), una celda $c$ solo puede ser pisada en el instante $t$ si satisface simultáneamente:
$$\text{dist}(START, c) \le t \quad \land \quad \text{dist}(c, GOAL) \le (12 - t)$$
Al aplicar esta cota, el número de variables de ruta se reduce de 624 a exactamente **48 variables candidatas**.

Sumando las 48 variables de suelo $x_c$, el **QUBO Integrado cuenta con exactamente 96 variables binarias** y $541$ términos cuadráticos.

### Acoplamientos del Hamiltoniano:
1. **Unicidad de paso:** $P \sum_{t=1}^{11} (\sum_c q_{t,c} - 1)^2$.
2. **Continuidad espacial:** Penalización cuadrática $P \cdot q_{t,a} \cdot q_{t+1,b}$ para celdas no contiguas.
3. **Compatibilidad con el terreno (la ruta solo pisa suelo):**
   $$P \cdot q_{t,c} (1 - x_c) = P \cdot q_{t,c} - P \cdot q_{t,c} \cdot x_c$$
   Este término cúbico aparente se reduce lineal-cuadrático de forma exacta gracias a que $q_{t,c}$ y $x_c$ son booleanas.

---

## Entrada 8: Validación Real de Variables q vs. Algoritmos BFS

### La trampa del "98% navegable"
En versiones preliminares, el solver extraía la matriz de suelo $x$, ejecutaba un BFS clásico y, si existía camino, declaraba la muestra "navegable".
Esto era un error conceptual: **un BFS sobre $x$ demuestra que la geometría tiene camino, pero no demuestra que el optimizador cuántico haya satisfecho las variables de ruta $q$**.

### Implementación de `validar_ruta_qubo()`
En `simulated_annealing_caso3.py` construí un validador formal que comprueba directamente el tensor cuántico $q_{t,c}$:
1. **Unicidad:** Exactamente un $q_{t,c} = 1$ para cada $t \in [1..11]$.
2. **Continuidad:** Las posiciones seleccionadas en pasos consecutivos $t$ y $t+1$ son vecinas ortogonales directas en la cuadrícula.
3. **Compatibilidad:** Para toda posición visitada por la ruta, $x_c = 1$ (no pisa muros).

Con esta validación rigurosa, el QUBO Integrado demuestra que el **93.60% ± 2.35%** de las muestras generadas satisfacen formalmente todas las restricciones cuánticas sin atajos ni violaciones.

---

## Entrada 9: Estudio Experimental de Robustez en 20 Semillas y Time To Solution (TTS)

Para garantizar la máxima comparabilidad científica, ejecuté exactamente las mismas 20 semillas aleatorias independientes ($1000 + 37i$), 100 reads, 1500 sweeps y penalización teórica $P = 100.0$ en ambos modelos QUBO:

### Comparativa Estadística Homogénea (20 Semillas):
- **Tasa media de éxito dura:**
  * QUBO Desacoplado: $8.30\% \pm 2.51\%$ (filtro clásico BFS).
  * QUBO Integrado: **$93.60\% \pm 2.35\%$** (validación de variables cuánticas $q$).
- **Estimación empírica de Time To Solution en CPU ($TTS_{99}$):**
  * QUBO Desacoplado: $63.47 \pm 28.29\text{ ms}$.
  * QUBO Integrado: **$4.39 \pm 0.60\text{ ms}$** (¡reducción de más de un orden de magnitud!).
- **Fronteras en la mejor solución válida:**
  * QUBO Desacoplado: $34.55 \pm 2.13$ transiciones.
  * QUBO Integrado: $29.25 \pm 2.14$ transiciones.
- **Fronteras en la muestra de menor energía:**
  * QUBO Desacoplado: $31.80 \pm 1.86$ transiciones (inviable / bloqueada en la mayoría de semillas).
- **Semillas con ≥1 muestra válida:**
  * 100% de las semillas (20/20) en ambos modelos QUBO.
- **Restricción de zonas en la solución válida:**
  * En la mejor solución válida: satisfecha estrictamente (5 muros por zona) en ambos modelos por definición de validez.
- **Componentes conexas de suelo (métrica de calidad):**
  * QUBO Desacoplado: $CC \in \{1, 2, 3, 4\}$ (1 a 4 componentes; ej. semilla 1000 tiene 1 y semilla 1666 tiene 4).
  * QUBO Integrado: $CC \in [1, 3]$ (1 a 3 componentes; ~50% de las semillas alcanzan 1 única componente).
- **Tiempo medio de muestreo en CPU:**
  * QUBO Desacoplado: $0.104\text{ s}$ por 100 reads.
  * QUBO Integrado: $0.209\text{ s}$ por 100 reads.

*Nota de rigor sobre el TTS:* Este valor corresponde a una **estimación empírica de TTS en CPU clásica** mediante Simulated Annealing, calculada como $t_{\text{read}} \frac{\ln(1 - 0.99)}{\ln(1 - p_{\text{éxito}})}$. No debe confundirse con el tiempo de ciclo físico de un procesador cuántico (QPU).

---

## Entrada 10: La Discusión Científica Honesta — Factibilidad vs. Calidad y Componentes Conexas

### 1. El mito de la "velocidad" (CP-SAT vs. SA)
- **CP-SAT Core:** Devuelve estado `OPTIMAL`, certificando la optimalidad para la formulación considerada (20 fronteras en 2.189 s).
- **Simulated Annealing:** Muestrea estocásticamente 100 lecturas en 0.205 s sobre un paisaje de energía rugoso, obteniendo soluciones viables de $29.25 \pm 2.14$ fronteras de media.
- **Conclusión:** No existe un "speedup" formal de SA sobre CP-SAT. Son dos esquemas con garantías diferentes: exacto-exhaustivo frente a estocástico-aproximado.

### 2. El trade-off real de la formulación cuántica
El salto del modelo desacoplado al integrado produce un cambio radical en la dinámica del sistema:
- El modelo desacoplado ($48$ vars) encuentra mapas con fronteras de 34.55 en válidos, pero el $91.7\%$ son inviables (caminos bloqueados).
- El modelo integrado ($96$ vars) fuerza la viabilidad al $93.60\%$, pero al restringir tan severamente el paisaje de energía, el muestreador se estabiliza en estados metaestables con un promedio de $29.25$ fronteras (a 9 transiciones del óptimo global clásico de 20).
- **Este resultado es mucho más valioso y defendible ante el tribunal que intentar forzar artificialmente que SA alcance 20.**

### 3. Componentes conexas como métrica de calidad
En las 20 semillas de evaluación estadística:
- **QUBO Desacoplado:** Las mejores soluciones válidas oscilan en $CC \in \{1, 2, 3, 4\}$ (de 1 a 4 componentes conexas de suelo; por ejemplo, la semilla 1000 genera una única componente conexa transitable, mientras que la 1666 llega a cuatro).
- **QUBO Integrado:** Las mejores soluciones se mantienen estrictamente en $CC \in [1, 3]$ (1 a 3 componentes; de hecho, cerca del 50% de las semillas presentan 1 única componente conexa perfecta).
- La muestra del QUBO integrado exportada a Blender presenta $3$ componentes conexas de suelo:
  * La componente principal contiene las 13 celdas (12 movimientos) de la ruta START $\to$ GOAL.
  * Existen dos pequeñas bolsas aisladas de suelo desconectadas.
- **¿Invalida esto el mapa?** No. La condición de navegabilidad START $\to$ GOAL definida para el experimento queda plenamente garantizada por las variables $q$ y el BFS.
- **Interpretación metodológica reforzada:** La conectividad global de todo el suelo es una métrica de **calidad arquitectónica**, no parte de la factibilidad dura del problema de ruta. Forzar la conectividad global de todas las celdas transitables en el Hamiltoniano requeriría variables y restricciones auxiliares adicionales —por ejemplo mediante formulaciones de flujo multicommodity o estructuras potenciales—, aumentando drásticamente el tamaño y la densidad del QUBO. Por ello se mantiene formalmente como métrica de calidad y no como restricción dura.

---

## Entrada 11: Pipeline de Visualización 3D en Blender 5.2

### Diagnóstico de la Vista Gris en Blender
Al cargar los primeros scripts en Blender 5.2, la vista 3D se mostraba en gris plano sin iluminación ni color.
- **Causa:** Blender arranca por defecto en modo *Solid View*, que desactiva los shaders procedurales y la iluminación calculada.
- **Solución implementada:**
  1. El script `visualizar_caso3_blender.py` fuerza automáticamente el modo `MATERIAL` (*Material Preview*) al pulsar *Run Script*.
  2. Además, asigna `diffuse_color` básico a cada material, garantizando que incluso en modo *Solid* cada objeto se distinga por su color característico.

### Creación de Texturas y Modelos 3D Reales
Sustituí las mallas geométricas primitivas por activos 3D completos:
- **Muros de piedra:** Shader procedural con combinación *Voronoi* y *Noise Texture* conectado al canal de *Bump Mapping 3D*, simulando sillería de cantería con micro-rugosidad y biselado físico en las aristas.
- **Suelo de pizarra:** Losas modulares de $2.0 \times 2.0\text{ m}$ con juntas de mortero de $8\text{ cm}$ y rugosidad irregular.
- **Props de juego (Demostrador CP-SAT):** Criaturas demoníacas completas, cofres del tesoro dorados y altar secreto con orbe de amatista.

### Pies de figura académicos rigurosos:
- **Figura 2:** *Ejemplo del nivel completo generado mediante CP-SAT, incluyendo obstáculos, ruta principal, dos enemigos, una recompensa sobre la ruta y una recompensa adicional situada al final de una rama secundaria.*
- **Figura 3:** *Ejemplo de una solución válida del modelo QUBO integrado obtenida mediante Simulated Annealing. La visualización representa la geometría generada y la ruta q de 12 movimientos entre START y GOAL; los elementos adicionales de gameplay no forman parte del modelo QUBO core.*

---

## Entrada 12: Demostrador QUBO Completo — Nivel con Gameplay y Rama en 117 Variables

Para comprobar la expresividad completa del paradigma QUBO frente al demostrador clásico, construí la formulación extendida [`qubo_caso3_completo.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/formulacion/qubo_caso3_completo.py):

### 1. Variables y Acoplamientos Cuadráticos Puros (Grado 2)
- **Geometría base:** 48 variables $x_c$ (Ising ferromagnético + 5 muros/zona).
- **Ruta principal:** 48 variables $q_{t, c}$ (ruta START $\to$ GOAL de 12 pasos codificada mediante penalizaciones Hamiltonianas cuadráticas).
- **Gameplay en ruta (9 variables de progreso):**
  * Recompensa: $r_t$ en $t \in [2..4]$ (3 vars).
  * Enemigo 1: $e_{1, t}$ en $t \in [5..7]$ (3 vars).
  * Enemigo 2: $e_{2, t}$ en $t \in [9..11]$ (3 vars).
  * No consecutividad: penalización cuadrática pura $r_4 \cdot e_{1, 5} = 0$. Al estructurarse en ventanas separadas, la mayor parte de la separación queda implícita en la topología temporal.
- **Rama secundaria de 2 celdas (12 variables de patrón $b_k$):**
  * **Catálogo geométrico predeterminado:** 12 tripletes ordenados $(u, a, b)$ seleccionados exclusivamente bajo criterios espaciales a priori (divergencia ortogonal hacia bordes y bolsas de la cuadrícula, sin sesgo derivado de soluciones clásicas previas).
  * **Variante restringida respecto a CP-SAT:** Frente al espacio combinatorio de 116 pares de CP-SAT v3, el catálogo de 12 patrones evita la explosión cuadrática de unicidad $\binom{116}{2} = 6.670$ acoplamientos, manteniendo el término en $\binom{12}{2} = 66$ acoplamientos.
  * **Conexión con ruta y condición teórica para $P=100$:** El término de conexión $b_k \left(1 - \sum_{t \in T(u)} q_{t, u}\right)$ es rigurosamente no negativo aquí porque, gracias a la poda por conos de Manhattan y a que la ruta tiene la longitud mínima estricta (12 pasos), cada celda candidata $u$ solo puede aparecer en a lo sumo un único paso temporal $t$. Por ende, la suma es como máximo 1 y la expresión se comporta como una penalización binaria simple con mínimo cero, preservando la validez de la cota $P=100 > 82$.
  * Apertura de suelo: $b_k (1 - x_a) = 0$, $b_k (1 - x_b) = 0$.
  * Callejón sin salida estricto (*dead-end*): penalización $b_k x_w$ para vecinos no autorizados de $a$ y $b$.
  * Recompensa secreta ubicada automáticamente en $b$.

### 2. Resultados Experimentales con Simulated Annealing

#### A. Ejecución Representativa Individual (Semilla 42, 100 reads, 1500 sweeps)
- **Dimensiones del modelo:** 117 variables binarias y 719 términos cuadráticos.
- **Tasa de éxito / Nivel válido completo:** **$52.0\%$** (52/100 reads satisfacen estrictamente el 100% de restricciones duras: balance zonal, START/GOAL, ruta $q$ continua, 2 enemigos, 2 recompensas, rama acoplada y callejón sin salida estricto).
- **Time To Solution ($TTS_{99}$):** **$19.76\text{ ms}$** (tiempo total de muestreo: $0.282\text{ s}$).
- **Solución representativa:** Obtiene **29 fronteras** de transición Ising, seleccionando el patrón geométrico #0 en el borde sudoeste ($u=(3, 0) \to a=(4, 0) \to b=(5, 0)$) con cofre en *dead-end*.

#### B. Estudio Riguroso de Robustez Estadística (20 Semillas × 100 Reads × 1500 Sweeps)
Ejecutado con el script [`robustez_sa_caso3_completo.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/robustez_sa_caso3_completo.py) bajo idéntico protocolo que el modelo desacoplado y el integrado:
- **Semillas con ≥1 solución válida:** **$100.0\%$ (20/20 semillas)**.
- **Tasa de éxito media:** **$54.35 \pm 4.17\%$** (todas las semillas oscilan en el rango $46\% \text{--} 62\%$).
- **Time To Solution ($TTS_{99}$) medio:** **$19.47 \pm 5.06\text{ ms}$** en CPU clásica.
- **Fronteras en solución válida:** **$29.85 \pm 1.65$** (consistente con el modelo integrado de 96 vars, que obtiene $29.25$).
- **Componentes conexas de suelo:** Rango $[1, 3]$ (media de $1.65$; el $50\%$ de las semillas logra 1 única componente conexa perfecta).
- **Diversidad morfológica de ramas:** El solucionador estocástico no se polariza en una única rama trivial, sino que selecciona dinámicamente diferentes patrones del catálogo según la topología de muros circundante (patrones #0, #2, #5, #6, #7, #9 y #10).

### 3. Visualización 3D en Blender 5.2 y Rigor Semántico en Exportación
- **Rigor semántico en la exportación:** El exportador [`exportar_qubo_completo_blender()`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/ejecutar_sa_caso3_completo.py) ejecuta explícitamente el algoritmo BFS clásico (`bfs_camino_minimo`) sobre las celdas abiertas resultantes, registrando con total fidelidad `bfs_path_length`, el camino más corto `bfs_shortest_path` y la trayectoria validada `validated_main_path` (extraída de $q$).
- **Archivos generados:**
  * JSON de nivel: [`caso3_nivel_blender_qubo_full_6x8.json`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/resultados/caso3_nivel_blender_qubo_full_6x8.json).
  * Escena 3D: [`caso3_nivel_blender_qubo_full_6x8.blend`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/resultados/caso3_nivel_blender_qubo_full_6x8.blend).
  * Render en alta definición (1920×1080): [`caso3_blender_qubo_full_render_6x8.png`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/figuras/caso3_blender_qubo_full_render_6x8.png).

### 4. Conclusión Epistemológica: La Progresión Conceptual del Caso 3
El Caso 3 culmina con la tabla comparativa más sólida de todo el proyecto, donde los tres modelos QUBO se comparan bajo exactamente el mismo protocolo estocástico:

| Modelo | Variables | Qué incorpora | $p_{\text{éxito}}$ (20 semillas) | $TTS_{99}$ medio | Fronteras Ising |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **QUBO desacoplado** | 48 | Geometría Ising + BFS ext. | $8.30 \pm 2.51\%$ | $63.47 \pm 28.29\text{ ms}$ | $34.55 \pm 2.13$ |
| **QUBO integrado** | 96 | Geometría + Ruta START $\to$ GOAL | $93.60 \pm 2.35\%$ | $4.39 \pm 0.69\text{ ms}$ | $29.25 \pm 2.14$ |
| **QUBO Full** | 117 | Geom + Ruta + Gameplay + Rama | $54.35 \pm 4.17\%$ | $19.47 \pm 5.06\text{ ms}$ | $29.85 \pm 1.65$ |

$$\mathbf{48} \quad\longrightarrow\quad \mathbf{96} \quad\longrightarrow\quad \mathbf{117}$$

*Reflexión académica de cierre:* **Aumentar la expresividad en una formulación QUBO no es gratuito; cada nueva propiedad de diseño introduce variables y acoplamientos cuadráticos, por lo que es necesario decidir qué libertad del generador merece mantenerse y cuál conviene podar geométricamente.** Demostrar esta progresión valida la madurez científica del trabajo.

---

## Resumen Ejecutivo de Archivos Clave del Caso 3

| Archivo | Función en el Proyecto |
| :--- | :--- |
| [`caso3_cpsat_v3.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/clasico/caso3_cpsat_v3.py) | Demostrador clásico completo con rama de exploración (116 pares) y gameplay (368 vars). |
| [`caso3_cpsat_core.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/clasico/caso3_cpsat_core.py) | Modelo clásico base: geometría + ruta (96 vars decisión, 178 vars solver, óptimo 20 fronteras). |
| [`qubo_caso3.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/formulacion/qubo_caso3.py) | Formulación QUBO desacoplada (48 vars, $P=100$, 8.30% de éxito). |
| [`qubo_caso3_integrado.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/formulacion/qubo_caso3_integrado.py) | Formulación QUBO integrada con conos de Manhattan (96 vars, $P=100$, 93.6% de éxito). |
| [`qubo_caso3_completo.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/formulacion/qubo_caso3_completo.py) | Formulación QUBO extendida con gameplay y rama secundaria de exploración (117 vars). |
| [`ejecutar_sa_caso3_completo.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/ejecutar_sa_caso3_completo.py) | Solver SA individual y exportador de nivel completo con BFS real a Blender. |
| [`robustez_sa_caso3_completo.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/robustez_sa_caso3_completo.py) | Estudio de robustez estadística con 20 semillas del QUBO Completo de 117 variables. |
| [`simulated_annealing_caso3.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/solvers/simulated_annealing_caso3.py) | Sampler SA con `validar_ruta_qubo()`, $TTS_{99}$ y seguimiento de mínima energía vs válida. |
| [`robustez_sa_caso3_integrado.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/robustez_sa_caso3_integrado.py) | Estudio de robustez estadística con 20 semillas aleatorias del QUBO Integrado. |
| [`comparar_desacoplado_vs_integrado.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/comparar_desacoplado_vs_integrado.py) | Benchmark comparativo de 4 vías que genera el informe tabular consolidado. |
| [`visualizar_caso3_blender.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/visualizacion/visualizar_caso3_blender.py) | Pipeline de renderizado 3D en Blender 5.2 con materiales procedurales y props completos. |
| [`generar_memoria_caso3.py`](file:///c:/Users/BCP/Desktop/TFM/caso3_mapa/experimentos/generar_memoria_caso3.py) | Generador automatizado del capítulo del TFM en formato Word con figuras incrustadas. |
| [`TFM-caso3_actualizado.docx`](file:///c:/Users/BCP/Desktop/TFM/TFM-caso3_actualizado.docx) | Memoria oficial completa del Caso 3 (4.85 MB) con todas las tablas, fórmulas y figuras. |
