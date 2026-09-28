# Explicación del código de Project-ito

Este documento explica **qué hace cada archivo y cada carpeta** del proyecto y cómo se conectan
entre sí. El `README.md` explica cómo *usar* el juego; este explica cómo *funciona por dentro*.

---

## 1. La idea general en una imagen

El programa es una cadena. Cada archivo hace **una sola cosa** y le pasa el resultado al siguiente:

```
  📷 Cámara
     │  imagen (fotograma)
     ▼
  gestos.py     →  "¿Hay una mano? ¿Qué gesto está haciendo?"      (ej. DERECHA)
     │  gesto "crudo" de ese fotograma
     ▼
  control.py    →  "¿Ese gesto es estable y lo sostuvo el tiempo suficiente?"
     │  evento confirmado (ej. "¡mover a la DERECHA ya!")
     ▼
  main.py       →  "En la pantalla actual, ¿qué significa ese gesto?"
     │  orden (ej. mover al jugador)
     ▼
  laberinto.py  →  "¿Se puede mover ahí o hay pared?"
     │  nueva posición del jugador
     ▼
  juego.py      →  dibuja todo en la ventana
     ▼
  🖥️ Pantalla
```

`config.py` está "a un lado" de la cadena. Todos los archivos leen de ahí los números que se pueden
ajustar: tiempos, umbrales, colores, el laberinto, etc.

**¿Por qué separarlo así?** Para que cada parte se pueda probar sola. Por ejemplo,
`demo_automatica.py` usa el laberinto y el dibujo **sin cámara**, y `prueba_gestos.py` usa la cámara
**sin laberinto**. También es más fácil de explicar y de corregir: si algo falla al detectar la mano,
sabes que el problema está en `gestos.py` y no en el laberinto.

---

## 2. Carpetas

| Carpeta | Qué contiene | ¿La toco? |
|---|---|---|
| `Proyect-ito/` (raíz) | Todos los archivos `.py` del juego, la imagen del laberinto, el README y este documento. | Sí, aquí está todo tu código. |
| `assets/` | Recursos que no son código: la imagen del personaje y el modelo de la mano. | Solo si quieres cambiar el personaje. |
| `assets/modelos/` | `hand_landmarker.task`: el **modelo de inteligencia artificial** de MediaPipe que reconoce manos (~8 MB). Sin él no se detecta la mano. | No. Si se borra, se recupera con `descargar_modelo.py`. |
| `.venv/` | El **entorno virtual**: una copia aislada de Python con las librerías del proyecto (MediaPipe, OpenCV, Pygame…) en las versiones exactas de `requirements.txt`. Así no se mezclan con otros proyectos de tu computadora. | Nunca a mano. Se crea con `python -m venv .venv`. |
| `__pycache__/` | Python la crea solo. Guarda versiones "precompiladas" de los `.py` para que arranquen más rápido. | No. Se puede borrar sin problema; se vuelve a crear. |

---

## 3. Archivos, uno por uno

### 📄 `config.py` — El panel de control

**Qué es:** un archivo solo con variables, sin lógica. Es el único lugar donde deberías cambiar
números.

**Qué contiene:**
- **Cámara:** `CAMARA_INDICE` (qué cámara usar), resolución, `CAMARA_BACKEND` (cómo se comunica
  con la cámara en Windows), `CAMARA_ESPEJO` (voltear la imagen como espejo).
- **MediaPipe:** dónde está el modelo y qué tan seguro debe estar para aceptar una mano.
- **Umbrales de gestos:** `UMBRAL_DEDO_EXTENDIDO` (cuándo un dedo cuenta como "estirado"),
  `TOLERANCIA_ANGULO` (qué tan recto hay que apuntar).
- **Tiempos del anti-rebote:** cuánto sostener cada gesto (0.5 s mover, 1 s palma, 2 s puño,
  3 s cuernos).
- **El laberinto:** la matriz `LABERINTO` de 0 y 1, más `INICIO`, `META` y `PASO`.
- **Dibujo:** tamaño de casilla, grosor de pared, colores, pantalla completa.

**Para defenderlo:** "Separé la configuración del código para poder ajustar el juego a la
iluminación del salón o a otra cámara sin tocar la lógica."

---

### 📄 `laberinto.py` — Las reglas del laberinto (lógica pura)

**Qué es:** el "cerebro" del laberinto. **No dibuja nada y no sabe que existe una cámara.** Solo
guarda dónde está el jugador y decide si un movimiento es válido.

**Qué contiene:**

| Elemento | Qué hace |
|---|---|
| `DIRECCIONES` | Un diccionario que traduce cada dirección a un desplazamiento (fila, columna). Ej. `"ARRIBA": (-1, 0)` significa "una fila menos". Las filas crecen hacia abajo, por eso arriba es -1. |
| `class Laberinto` | El objeto que representa el laberinto y al jugador. |
| `_validar()` | Al crear el laberinto, revisa que las filas midan lo mismo, que el inicio y la meta no estén sobre una pared y que exista solución. Si algo está mal, avisa con un mensaje claro. |
| `reiniciar()` | Regresa al jugador al inicio y pone en cero los movimientos y los choques. |
| `gano` | `True` cuando la posición del jugador es la meta. |
| `es_camino(fila, col)` | `True` si esa posición está dentro de la matriz y vale 0. **Salirse de la matriz cuenta como pared.** |
| `destino(posicion, direccion)` | Calcula a dónde llegarías. **Revisa cada posición intermedia**, no solo la final, para que no se pueda "saltar" una pared delgada. Devuelve la nueva posición, o `None` si chocas. |
| `mover(direccion)` | Intenta mover al jugador. Si puede, suma un movimiento; si no, suma un choque. |
| `resolver()` | Algoritmo **BFS** (búsqueda en anchura) que encuentra la ruta **más corta** hasta la meta. Se usa para comprobar que el laberinto tiene solución y para la demo automática. |

**¿Por qué la matriz es de 17×17 si el laberinto es de 8×8?** La imagen tiene paredes
**delgadas** entre casillas. Para representarlas se usa el formato (2·8+1) × (2·8+1):
- Posiciones **impares** (1, 3, 5…) = las casillas donde puede estar el personaje.
- Posiciones **pares** (0, 2, 4…) = el espacio *entre* casillas: 1 si hay pared, 0 si hay paso.

Por eso `PASO = 2`: moverse una casilla equivale a avanzar 2 posiciones en la matriz, y la posición
de en medio es la que dice si hay pared.

**¿Cómo funciona el BFS?** Empieza en el inicio y explora primero todas las casillas a distancia 1,
luego todas las de distancia 2, y así sucesivamente, como una onda que se expande. La primera vez que
llega a la meta es, por fuerza, el camino más corto. Guarda de dónde vino cada casilla para
reconstruir la ruta al final.

---

### 📄 `gestos.py` — Ver la mano y reconocer el gesto

**Qué es:** la parte de **visión por computadora**. Lee la cámara, usa MediaPipe para encontrar la
mano y decide qué gesto es.

**Conceptos importantes:**
- **Landmarks (puntos de referencia):** MediaPipe no "entiende" gestos. Lo que hace es devolver
  **21 puntos** de la mano (muñeca, nudillos, articulaciones y puntas de cada dedo). Nosotros usamos
  esos puntos para decidir el gesto con geometría.
  ```
  0 = muñeca · 8 = punta del índice · 12 = punta del medio · 16 = punta del anular · 20 = punta del meñique
  6, 10, 14, 18 = articulación media de cada dedo · 5 = nudillo del índice
  ```
- **Hilo (thread):** la cámara se lee en un **hilo aparte**, es decir, en paralelo al juego. Así, si
  la cámara tarda, el juego no se congela: sigue dibujando a 60 FPS y solo toma "la última lectura
  disponible".

**Qué contiene:**

| Elemento | Qué hace |
|---|---|
| `class Gesto` | La lista de gestos posibles: `SIN_MANO`, `NINGUNO`, `ARRIBA`, `ABAJO`, `IZQUIERDA`, `DERECHA`, `PALMA`, `PUNO`, `CUERNOS`. |
| `NOMBRES` | El texto bonito que se muestra en pantalla para cada gesto. |
| `dedos_extendidos(mundo)` | Decide qué dedos están estirados. Compara la distancia **muñeca→punta** con la distancia **muñeca→articulación media**. Con el dedo estirado, la punta queda más lejos (cociente ≈ 1.35); con el dedo doblado, la punta regresa hacia la palma (< 1.0). Usa coordenadas **3D en metros**, así que funciona igual con la mano cerca o lejos y girada hacia cualquier lado. **El pulgar se ignora** porque es el que peor se detecta. |
| `direccion_indice(puntos)` | Calcula el **ángulo** de la línea nudillo→punta del índice. 0° = derecha, 90° = arriba, 180° = izquierda, -90° = abajo. Solo acepta el gesto si está a menos de ±30° de uno de esos ángulos; si apuntas en diagonal devuelve `NINGUNO` (**zona muerta**). |
| `clasificar(...)` | Junta todo: 4 dedos estirados = `PALMA`, ninguno = `PUNO`, índice + meñique = `CUERNOS`, solo el índice = una dirección, cualquier otra cosa = `NINGUNO`. |
| `class Lectura` | El "paquete" que el hilo de la cámara le entrega al juego: la imagen con la mano dibujada, el gesto, qué dedos están estirados, el ángulo y los FPS. |
| `class DetectorGestos` | El hilo de la cámara. Métodos principales: `iniciar()` arranca el hilo; `leer()` devuelve la última lectura; `detener()` lo apaga. |
| `_bucle()` | Lo que hace el hilo sin parar: (1) asegurarse de que la cámara esté abierta y, si no, **reintentar cada 3 s**; (2) leer un fotograma y voltearlo como espejo; (3) pasarlo a MediaPipe; (4) clasificar el gesto; (5) publicar la lectura. |
| `_abrir_camara()` | Abre la cámara y comprueba que realmente entregue imagen. Solo cambia la resolución si hace falta, porque en tu cámara cada cambio tardaba ~2.5 s. |
| `_dibujar_mano()` | Dibuja el "esqueleto" de la mano sobre la imagen, con el índice resaltado y una flecha si estás apuntando. |

**Manejo de errores:** si no hay modelo, la cámara no abre o se desconecta, el detector pasa a
`estado = "error"` con un mensaje. El juego lo muestra en pantalla en lugar de cerrarse.

---

### 📄 `control.py` — El anti-rebote (que no haya movimientos fantasma)

**Qué es:** el filtro entre "lo que MediaPipe ve en un fotograma" y "lo que el juego obedece".
Sin este archivo, un solo fotograma mal detectado movería al personaje.

**Dos capas de protección:**

1. **Votación (`_votar`):** guarda los últimos 5 gestos. Un gesto solo se acepta como "estable" si
   aparece **al menos 3 veces** en esos 5. Si MediaPipe se equivoca en un fotograma suelto, pierde la
   votación y se ignora.
2. **Sostener (`actualizar`):** cuando el gesto estable cambia, arranca un cronómetro. El evento solo
   se **dispara** si el gesto se mantiene el tiempo configurado (0.5 s para moverse). Si cambias de
   gesto antes, el cronómetro vuelve a cero.

**Qué contiene:**

| Elemento | Qué hace |
|---|---|
| `DURACIONES` | Cuánto hay que sostener cada gesto. Los que no aparecen (`NINGUNO`, `SIN_MANO`) nunca disparan nada. |
| `actualizar(lectura)` | Se llama en cada cuadro del juego. Devuelve el gesto **disparado** en ese momento, o `None` si todavía no toca. |
| Repetición | Si sigues apuntando, el movimiento se repite cada 0.5 s (`REPETIR_MOVIMIENTO`). Los gestos de control (palma, puño, cuernos) se disparan **una sola vez**: hay que soltarlos para volver a usarlos. |
| `LECTURA_VIEJA_S` | Seguridad: si la cámara deja de mandar imágenes por más de 0.5 s, se considera que no hay mano. Así el personaje no sigue caminando solo con un gesto "congelado". |
| `progreso()` | Devuelve un número de 0 a 1 que indica cuánto falta para disparar. Es lo que llena la **barra verde** en pantalla. |

---

### 📄 `main.py` — El director del juego (máquina de estados)

**Qué es:** el archivo que se ejecuta (`python main.py`). Une a todos los demás y decide **qué
significa cada gesto según la pantalla en la que estás**.

**Concepto clave: máquina de estados.** El juego siempre está en **uno** de estos estados, y cada
uno reacciona a distintos gestos:

```
 CALIBRACIÓN ──palma──▶ JUGANDO ──llega a la meta──▶ ¡GANASTE!
                          │   ▲                          │
                      palma   palma                 puño (jugar de nuevo)
                          ▼   │                          │
                         PAUSA ◀─────────────────────────┘ (va a JUGANDO)
  Puño en JUGANDO o PAUSA = reiniciar   ·   Cuernos en cualquier estado = salir
```

**Qué contiene:**

| Elemento | Qué hace |
|---|---|
| `class Estado` | Los 4 estados posibles. |
| `ACCIONES` | Una tabla: para cada estado, qué gesto hace qué. Por ejemplo, en `PAUSA` la palma significa "Reanudar" y apuntar no hace nada. **Esta misma tabla** genera la ayuda que se ve en pantalla, así que la ayuda siempre coincide con lo que realmente funciona. |
| `leyenda(estado)` | Convierte `ACCIONES` en las filas de ayuda del panel ("Puño · 2 s → Reiniciar"). |
| `class App` | El juego completo. Crea el laberinto, la ventana, el detector y el control. |
| `ejecutar()` | El **bucle principal**, que se repite 60 veces por segundo: (1) revisa si cerraron la ventana con la X; (2) lee el gesto y lo pasa por `control`; (3) si se disparó un gesto válido para el estado actual, ejecuta la acción; (4) suma tiempo si estás jugando; (5) dibuja. |
| `manejar(gesto)` | Ejecuta la acción: mover, pausar, reiniciar, salir… Si el personaje llega a la meta, cambia a `GANASTE`. |
| `cambiar_estado()` y `gesto_bloqueado` | Cuando la palma inicia el juego, sigues con la palma levantada. Ese gesto se "bloquea" (aparece "Cambia de gesto para volver a usarlo") hasta que lo sueltes, para que no parezca que va a pausar de inmediato. |
| `dibujar()` | Le pide a `juego.py` que dibuje la pantalla que corresponde al estado actual. |

**El teclado:** en el bucle solo se atiende el evento `QUIT` (la X de la ventana). Cualquier tecla
se ignora.

---

### 📄 `juego.py` — Todo lo que se ve (dibujo con Pygame)

**Qué es:** el encargado de **pintar**. No toma decisiones: recibe datos (dónde está el jugador,
qué gesto hay, en qué estado estamos) y los dibuja.

**`class Personaje`:**

| Método | Qué hace |
|---|---|
| `_cargar_imagen()` | Carga `assets/personaje.png` y la escala al tamaño de la casilla. Si no existe o falla, devuelve `None`. |
| `ir_a()` / `posicion()` | Hacen la **animación**: el personaje se desliza a la nueva casilla en 0.15 s, en lugar de "teletransportarse". También lo voltea hacia la izquierda o la derecha según hacia dónde camina. |
| `_dibujar_respaldo()` | Si no hay imagen, dibuja un dinosaurio con círculos, elipses y triángulos de Pygame. |

**`class Vista`** (la ventana):

| Método | Qué dibuja |
|---|---|
| `__init__` | Calcula el tamaño de todo. Las columnas pares se dibujan delgadas (paredes) y las impares anchas (casillas), para que se vea como la imagen original. |
| `dibujar_laberinto()` | El fondo azul, las paredes negras, los letreros ENTRADA/SALIDA, la estrella de la meta y el **destello rojo** cuando chocas. |
| `dibujar_barra_superior()` | El título, el estado, los movimientos y el tiempo. |
| `dibujar_panel_juego()` | El panel derecho durante el juego: **cámara pequeña** con la mano, nombre del gesto, barra de progreso y lista de gestos disponibles. |
| `dibujar_calibracion()` | La pantalla inicial: cámara grande, "Mano detectada / NO detectada", un círculo por dedo (verde = estirado, rojo = doblado), pasos a seguir y una flecha amarilla al practicar direcciones. |
| `superficie_camara()` | Convierte la imagen de OpenCV (formato BGR) a imagen de Pygame (formato RGB). |
| `dibujar_mensaje()` | El recuadro oscuro semitransparente de "Pausa" y "¡Ganaste!". |
| `dibujar_aviso()` | El letrero amarillo temporal, por ejemplo "Laberinto reiniciado". |
| `dibujar_error()` | La pantalla de "Problema con la cámara" o "Falta el modelo". |

---

### 📄 `demo_automatica.py` — Etapa 1: el laberinto sin cámara

**Qué es:** un programa aparte para demostrar que el laberinto y las colisiones funcionan, **sin
cámara ni teclado**.

**Qué hace:**
1. Choca a propósito 3 veces (`CHOQUES_DE_PRUEBA`: arriba, derecha e izquierda desde el inicio) para
   mostrar que las paredes funcionan.
2. Recorre la ruta más corta que calcula el BFS: 46 casillas.
3. Muestra "¡Ganaste!", espera 4 s y vuelve a empezar.

Sirve para la presentación si algo falla con la cámara: demuestra la lógica por separado.

---

### 📄 `prueba_gestos.py` — Etapa 2: los gestos sin el laberinto

**Qué es:** una ventana de diagnóstico. Muestra la cámara con la mano y, en texto:
- **Crudo:** el gesto que detecta cada fotograma.
- **Estable:** el gesto que ganó la votación.
- **Dedos:** cuáles ve estirados (SI/no).
- **Ángulo del índice** y **FPS** de la cámara.
- Una barra que se llena al sostener el gesto.

Sirve para **calibrar**: si algo se confunde, aquí ves por qué y ajustas `config.py`. Se cierra con
cuernos (3 s) o con la X. Los textos van sin acentos porque OpenCV no puede dibujarlos.

---

### 📄 `descargar_modelo.py` — Bajar el modelo de la mano

Descarga `hand_landmarker.task` desde los servidores de Google y lo guarda en `assets/modelos/`.
Primero lo baja con otro nombre y solo lo renombra al terminar, así una descarga interrumpida no deja
un archivo roto. Si el modelo ya existe, no hace nada (con `--forzar` lo vuelve a bajar).

---

### 📄 Otros archivos

| Archivo | Qué es |
|---|---|
| `requirements.txt` | La lista de librerías con **versiones fijas**, para que el proyecto se instale igual en cualquier computadora. Las principales: `mediapipe` (detectar la mano), `opencv-contrib-python` (cámara e imágenes), `pygame-ce` (el juego) y `numpy` (cálculos con los puntos). |
| `README.md` | Guía de **uso**: instalar, ejecutar, gestos, configuración y problemas comunes. |
| `Laberinto IHC.jpeg` | La imagen original del laberinto. De ella salió la matriz de `config.py`: se midió dónde estaban las líneas negras y se revisó el color de cada tramo de pared. |
| `assets/personaje.png` | El dinosaurio recortado de la imagen original, con fondo transparente. |

---

## 4. Recorrido completo: ¿qué pasa cuando apunto a la derecha?

1. **Cámara → `gestos.py`:** el hilo lee un fotograma, lo voltea como espejo y MediaPipe devuelve los
   21 puntos de tu mano.
2. `dedos_extendidos()` ve que solo el índice está estirado. `direccion_indice()` mide el ángulo:
   unos 5°, cerca de 0° → **`DERECHA`**.
3. **`control.py`:** los siguientes fotogramas también dicen `DERECHA`, así que gana la votación (3
   de 5) y arranca el cronómetro. La barra verde se empieza a llenar.
4. Al llegar a **0.5 s**, `actualizar()` devuelve `DERECHA`: el evento se dispara.
5. **`main.py`:** estamos en `JUGANDO`, y en esa tabla `DERECHA` significa "Mover", así que llama a
   `laberinto.mover("DERECHA")`.
6. **`laberinto.py`:** `destino()` revisa la posición de en medio. Si es 0, mueve al jugador 2
   posiciones en la matriz (una casilla). Si es 1, cuenta un choque.
7. **`juego.py`:** si se movió, el dinosaurio se desliza a la nueva casilla; si chocó, el borde
   parpadea en rojo.
8. Si sigues apuntando, cada 0.5 s se repite desde el paso 4.

---

## 5. Glosario rápido

| Término | Significado |
|---|---|
| **MediaPipe** | Librería de Google con modelos de IA ya entrenados. Usamos el que detecta 21 puntos de la mano. |
| **OpenCV** | Librería para abrir la cámara y manipular imágenes. |
| **Pygame** | Librería para hacer videojuegos en 2D: ventana, dibujo y animación. |
| **Landmark** | Cada uno de los 21 puntos que MediaPipe encuentra en la mano. |
| **Fotograma / FPS** | Cada imagen de la cámara / cuántas imágenes por segundo. |
| **Hilo (thread)** | Una tarea que corre en paralelo. La cámara va en su propio hilo para no congelar el juego. |
| **Anti-rebote** | Técnica para ignorar señales falsas o momentáneas; aquí, votación + sostener el gesto. |
| **Zona muerta** | Rango de ángulos (las diagonales) donde a propósito no pasa nada, para evitar errores. |
| **Máquina de estados** | Forma de organizar un programa en "modos" (calibración, juego, pausa…) con reglas claras para pasar de uno a otro. |
| **BFS** | Búsqueda en anchura: algoritmo que encuentra el camino más corto en un laberinto. |
| **Matriz** | Tabla de números (filas × columnas). Aquí, 0 = camino y 1 = pared. |
| **Entorno virtual (.venv)** | Instalación aislada de Python y librerías solo para este proyecto. |

---

## 6. Preguntas que te pueden hacer en la demostración

- **¿Por qué apuntar con el índice y no contar dedos?** Contar dedos confunde 3 con 4 y depende del
  pulgar, que se detecta mal. Apuntar es intuitivo y tiene zona muerta en las diagonales.
- **¿Cómo evitas movimientos accidentales?** Con dos capas: votación entre fotogramas (quita los
  errores sueltos) y sostener el gesto 0.5 s antes de moverse.
- **¿Cómo sabes que un dedo está estirado?** Comparo qué tan lejos está la punta de la muñeca contra
  qué tan lejos está la articulación media. Estirado ≈ 1.35 veces; doblado, menos de 1.
- **¿Qué pasa si se desconecta la cámara?** El programa no se cierra: muestra un aviso y reintenta
  cada 3 s.
- **¿Cómo detectas los choques?** El laberinto es una matriz. Antes de moverse reviso la posición
  intermedia; si es 1, es pared y no me muevo.
- **¿Cómo sabes que el laberinto tiene solución?** Al arrancar se ejecuta un BFS; si no hay camino,
  el programa avisa con un error.
- **¿Por qué la cámara va en un hilo aparte?** MediaPipe tarda ~30 ms por imagen. Si estuviera en el
  mismo ciclo que el dibujo, el juego se vería trabado.
