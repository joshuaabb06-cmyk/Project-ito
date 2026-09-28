# Project-ito

Juego de laberinto controlado **solo con gestos de la mano**, detectados con la cámara
(MediaPipe + OpenCV) y dibujado con Pygame. Durante la ejecución **no se usa el teclado para nada**:
ni para mover, iniciar, pausar, reiniciar o salir.

El laberinto es el de la imagen `Laberinto IHC.jpeg` (8×8 casillas), convertido a una matriz
de 0 (camino) y 1 (pared).

---

## Requisitos

- Windows 10/11 con cámara web.
- **Python 3.14** (probado con 3.14.0). MediaPipe 1.0.1 ya tiene versión para 3.14.
- Internet **solo la primera vez** (para instalar paquetes y descargar el modelo de la mano).

> **Nota sobre Pygame:** el paquete `pygame` clásico no tiene versión para Python 3.14, así que usamos
> **`pygame-ce`** (la versión comunitaria). En el código se sigue escribiendo `import pygame`.

## Instalación (una sola vez)

En PowerShell, dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe descargar_modelo.py
```

`descargar_modelo.py` baja `assets/modelos/hand_landmarker.task` (~8 MB). MediaPipe 1.x ya no trae
el modelo incluido. Después el juego funciona **sin internet**.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe main.py              # el juego completo
.\.venv\Scripts\python.exe demo_automatica.py   # etapa 1: el laberinto se resuelve solo (sin cámara)
.\.venv\Scripts\python.exe prueba_gestos.py     # etapa 2: solo la detección de gestos (para calibrar)
```

(Si activas el entorno con `.\.venv\Scripts\Activate.ps1`, basta con `python main.py`. Si PowerShell
bloquea el script de activación, usa la forma de arriba, que no necesita activar nada.)

---

## Gestos

| Gesto | Sostener | Acción |
|---|---|---|
| ☝️ **Índice apuntando** ↑ ↓ ← → (demás dedos doblados) | 0.5 s | Avanza **una casilla** en esa dirección. Si lo sigues sosteniendo, avanza otra cada 0.5 s. |
| ✋ **Palma abierta** (4 dedos extendidos) | 1 s | Calibración → **iniciar**. En el juego → **pausar / reanudar**. |
| ✊ **Puño** | 2 s | **Reiniciar** el laberinto (en juego, pausa o en "¡Ganaste!"). |
| 🤘 **Cuernos** (índice + meñique) | 3 s | **Salir** del programa (funciona en cualquier pantalla). |

- El **pulgar se ignora** en todos los gestos: es el dedo que MediaPipe detecta peor.
- Si apuntas en **diagonal**, no pasa nada (zona muerta de ±30° alrededor de cada eje). Así se evita
  un movimiento equivocado.
- La cámara funciona como **espejo**: si apuntas a tu derecha, el personaje va a la derecha.
- Los gestos de control (palma, puño, cuernos) se disparan **una sola vez**. Para repetirlos hay que
  cambiar de gesto o bajar la mano.
- En el panel derecho siempre se ve qué gesto se reconoce, una **barra de carga** con lo que va a
  pasar al completarse y la lista de gestos que funcionan en esa pantalla.

## Pantallas

1. **Calibración:** cámara grande con los puntos de la mano, "Mano detectada / NO detectada", qué
   dedos se ven extendidos y una lista de pasos. Puedes practicar las 4 direcciones (aparece una
   flecha amarilla). Con palma abierta 1 s empieza el juego.
2. **Juego:** laberinto + cámara pequeña en la esquina con la mano dibujada y el gesto en texto.
3. **Pausa** y **¡Ganaste!** (con movimientos, tiempo y choques).
4. **Error de cámara / modelo:** si la cámara no abre o se desconecta, aparece un mensaje y se
   **reintenta sola cada 3 s**. No hace falta reiniciar el programa.

La X de la ventana (con el mouse) queda como salida de emergencia.

---

## Estructura

```
Proyect-ito/
├── main.py              # Punto de entrada: máquina de estados (calibración, juego, pausa, ganaste)
├── config.py            # TODOS los parámetros ajustables + la matriz del laberinto
├── gestos.py            # Hilo de cámara + MediaPipe HandLandmarker + clasificación de gestos
├── control.py           # Anti-rebote: votación entre fotogramas y temporizadores de "sostener"
├── laberinto.py         # Lógica pura: matriz, colisiones, meta, BFS
├── juego.py             # Todo el dibujo con Pygame (laberinto, personaje, panel, pantallas)
├── demo_automatica.py   # Etapa 1: demo sin cámara ni teclado
├── prueba_gestos.py     # Etapa 2: ventana de prueba de gestos
├── descargar_modelo.py  # Descarga el modelo de MediaPipe
├── assets/
│   ├── personaje.png    # Personaje (el dinosaurio de la imagen). Si lo borras, se dibuja uno de respaldo
│   └── modelos/hand_landmarker.task
├── Laberinto IHC.jpeg   # Imagen original del laberinto
└── requirements.txt
```

## Configuración (`config.py`)

| Parámetro | Para qué |
|---|---|
| `CAMARA_INDICE` | 0 = cámara integrada; 1, 2… para webcams USB |
| `CAMARA_BACKEND` | `"msmf"` (30 FPS en pruebas) o `"dshow"` (abre más rápido, pero dio 10 FPS) |
| `TIEMPO_MOVER`, `TIEMPO_REPETICION`, `REPETIR_MOVIMIENTO` | Anti-rebote del movimiento |
| `TIEMPO_INICIAR_PAUSAR`, `TIEMPO_REINICIAR`, `TIEMPO_SALIR` | Cuánto sostener cada gesto de control |
| `UMBRAL_DEDO_EXTENDIDO` | Súbelo si detecta dedos "extendidos" que están doblados; bájalo en el caso contrario |
| `TOLERANCIA_ANGULO` | Tamaño de la zona aceptada para cada dirección (grados) |
| `VENTANA_VOTACION`, `VOTOS_MINIMOS` | Filtro de parpadeos |
| `LABERINTO`, `INICIO`, `META`, `PASO` | El laberinto y cómo se avanza |
| `TAMANO_CASILLA`, `GROSOR_PARED`, `PANTALLA_COMPLETA` | Tamaño en pantalla (`True` para el proyector) |

### ¿Cómo se representa el laberinto?

La imagen tiene 8×8 casillas con paredes **delgadas**. Se convierte a una matriz de 17×17
(2·8+1). Las posiciones **impares** son casillas y las **pares** son las paredes (1) o huecos (0)
entre casillas. Por eso `PASO = 2`: cada movimiento avanza de una casilla a la siguiente y **revisa
la posición intermedia**. Si ahí hay un 1, es un choque. La ruta más corta tiene 46 casillas.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| "No se pudo abrir la cámara" | Cierra Zoom/Teams/la app Cámara. Si tienes varias cámaras, prueba `CAMARA_INDICE = 1`. |
| Tarda unos segundos en ver la cámara | Normal con `msmf` (~4 s). Con `"dshow"` abre más rápido pero da menos FPS. |
| "Falta el modelo de MediaPipe" | Ejecuta `descargar_modelo.py` (necesita internet). |
| No detecta bien la mano | Buena luz de frente (no una ventana detrás), mano a 40-60 cm, palma hacia la cámara. |
| Confunde gestos | Abre `prueba_gestos.py`: muestra qué dedos ve extendidos y el ángulo del índice. Ajusta `UMBRAL_DEDO_EXTENDIDO`. |

### Lista para el día de la presentación

- [ ] Modelo descargado (`assets/modelos/hand_landmarker.task` existe).
- [ ] Probar la cámara y la luz del salón con `prueba_gestos.py`.
- [ ] Fondo detrás de la mano sin otras manos o personas cerca.
- [ ] `PANTALLA_COMPLETA = True` si se proyecta.
- [ ] Cerrar apps que usen la cámara.
