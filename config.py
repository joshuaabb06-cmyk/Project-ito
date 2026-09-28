"""
config.py — Configuración central de Project-ito.

Todo lo que quieras ajustar (cámara, tiempos de los gestos, umbrales, tamaños,
colores o el propio laberinto) está aquí, para no tener que tocar el resto del código.
"""

# ---------------------------------------------------------------------------
# CÁMARA
# ---------------------------------------------------------------------------
CAMARA_INDICE = 0          # 0 = cámara integrada. Prueba 1, 2... si usas una webcam USB.
CAMARA_ANCHO = 640         # Resolución solicitada a la cámara (px)
CAMARA_ALTO = 480
CAMARA_BACKEND = "msmf"    # Windows: "msmf" (en pruebas dio 30 FPS, tarda ~3 s en abrir) o
                           # "dshow" (abre rápido, pero dio solo 10 FPS). Otros sistemas: "auto".
CAMARA_ESPEJO = True      # Voltea la imagen como espejo: tu izquierda = izquierda en pantalla
CAMARA_REINTENTO_S = 3.0   # Si la cámara falla, cada cuántos segundos se vuelve a intentar abrir

# ---------------------------------------------------------------------------
# MEDIAPIPE (modelo de detección de manos)
# ---------------------------------------------------------------------------
RUTA_MODELO = "assets/modelos/hand_landmarker.task"
URL_MODELO = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
              "hand_landmarker/float16/latest/hand_landmarker.task")
CONFIANZA_DETECCION = 0.6   # Qué tan seguro debe estar MediaPipe de que hay una mano (0-1)
CONFIANZA_PRESENCIA = 0.5
CONFIANZA_SEGUIMIENTO = 0.5

# ---------------------------------------------------------------------------
# CLASIFICACIÓN DE GESTOS (umbrales geométricos)
# ---------------------------------------------------------------------------
# Un dedo se considera EXTENDIDO si:  distancia(muñeca, punta) / distancia(muñeca, nudillo medio)
# es mayor que este valor. Dedo recto ≈ 1.3-1.4, dedo doblado < 1.0.
UMBRAL_DEDO_EXTENDIDO = 1.15
# Ángulo máximo (grados) entre el dedo índice y un eje (arriba/abajo/izq/der) para aceptar
# la dirección. Si apuntas en diagonal (fuera de esta tolerancia) NO se mueve: zona muerta.
TOLERANCIA_ANGULO = 30
# Largo mínimo del índice (relativo al tamaño de la palma) para confiar en su dirección.
# Evita lecturas erráticas cuando apuntas directamente a la cámara.
LARGO_MINIMO_INDICE = 0.45

# ---------------------------------------------------------------------------
# ANTI-REBOTE (tiempos, en segundos)
# ---------------------------------------------------------------------------
VENTANA_VOTACION = 5        # Fotogramas recientes que "votan" por el gesto (filtro de parpadeos)
VOTOS_MINIMOS = 3           # Votos necesarios para aceptar un gesto como estable
TIEMPO_MOVER = 0.5          # Sostener la dirección este tiempo = 1 casilla
REPETIR_MOVIMIENTO = True   # Si sigues sosteniendo la dirección, ¿avanza otra casilla?
TIEMPO_REPETICION = 0.5     # Cada cuánto se repite el movimiento al sostener
TIEMPO_INICIAR_PAUSAR = 1.0 # Palma abierta: iniciar / pausar / reanudar
TIEMPO_REINICIAR = 2.0      # Puño: reiniciar
TIEMPO_SALIR = 3.0          # Cuernos (índice + meñique): salir del programa

# ---------------------------------------------------------------------------
# LABERINTO
# ---------------------------------------------------------------------------
# Matriz obtenida de la imagen "Laberinto IHC.jpeg" (8x8 casillas -> matriz 17x17).
#   0 = camino, 1 = pared.
#   Posiciones IMPARES (fila y columna) = casillas donde puede estar el personaje.
#   Posiciones PARES = paredes delgadas (o huecos) entre casillas y esquinas.
# La entrada es el hueco de la fila 7 (izquierda) y la salida el de la fila 1 (derecha).
LABERINTO = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],  # <- salida (derecha)
    [1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1],
    [1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1],
    [0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1],  # <- entrada (izquierda)
    [1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1],
    [1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1],
    [1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1],
    [1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]
INICIO = (7, 1)    # (fila, columna): primera casilla junto a la entrada
META = (1, 15)     # última casilla junto a la salida
PASO = 2           # Posiciones de la matriz que avanza el personaje por movimiento
                   # (2 = de una casilla a la siguiente, saltando la pared/hueco de en medio)

# ---------------------------------------------------------------------------
# VENTANA Y DIBUJO
# ---------------------------------------------------------------------------
TAMANO_CASILLA = 64        # Tamaño (px) de cada casilla del laberinto
GROSOR_PARED = 10          # Grosor (px) de las paredes delgadas
MARGEN = 24                # Margen alrededor del laberinto
ALTO_BARRA_SUPERIOR = 56   # Barra de título / estado
ANCHO_PANEL = 360          # Panel derecho (cámara + gesto actual + ayuda)
PANTALLA_COMPLETA = False  # True para la presentación en el proyector
FPS = 60
DURACION_ANIMACION = 0.15  # Segundos que tarda el personaje en deslizarse a la siguiente casilla

RUTA_PERSONAJE = "assets/personaje.png"   # Si no existe se dibuja un personaje de respaldo

# Colores (R, G, B) — inspirados en la imagen original
COLOR_FONDO = (22, 27, 44)
COLOR_PANEL = (32, 39, 61)
COLOR_CAMINO = (159, 195, 230)
COLOR_PARED = (10, 10, 12)
COLOR_META = (255, 205, 60)
COLOR_TEXTO = (240, 244, 250)
COLOR_TEXTO_SUAVE = (160, 170, 195)
COLOR_ACENTO = (90, 200, 120)
COLOR_ALERTA = (235, 90, 90)

# ---------------------------------------------------------------------------
# DEMO AUTOMÁTICA (etapa 1, sin cámara)
# ---------------------------------------------------------------------------
DEMO_PAUSA_ENTRE_PASOS = 0.35   # Segundos entre movimientos automáticos
