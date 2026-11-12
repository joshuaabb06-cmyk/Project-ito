"""
config.py — Configuración central de Project-ito.

Todo lo que quieras ajustar (cámara, tiempos de los gestos, umbrales, tamaños,
colores, dificultades, sonido o el propio laberinto) está aquí, para no tener que tocar el resto del código.
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

# ---------------------------------------------------------------------------
# PERSONAJES, FUENTES, SONIDO Y AJUSTES
# ---------------------------------------------------------------------------
# Cada imagen PNG (con fondo transparente) que pongan en esta carpeta aparece sola en
# el menú PERSONAJE. El nombre del archivo es el que se muestra (cowboy_rex.png -> "Cowboy rex").
CARPETA_PERSONAJES = "assets/personajes"
RUTA_FUENTE_TITULOS = "assets/fuentes/Rye-Regular.ttf"   # Licencia SIL OFL (ver OFL-Rye.txt)
CARPETA_SONIDOS = "assets/sonidos"   # se generan con: python generar_sonidos.py
CARPETA_VOCES = "assets/voces"       # se generan con: python generar_voces.py (o graben las suyas)
RUTA_AJUSTES = "ajustes_usuario.json"  # volúmenes, dificultad, personaje y récords (se guarda solo)

# ---------------------------------------------------------------------------
# DIFICULTADES (la ruta del laberinto es la misma; solo cambian las reglas)
# ---------------------------------------------------------------------------
#   vidas = None -> nunca pierdes      niebla = solo ves alrededor del personaje
#   pista = huellas que marcan los siguientes pasos de la ruta más corta
DIFICULTADES = {
    "explorador": dict(nombre="Explorador", vidas=None, niebla=False, pista=True,
                       descripcion=["No pierdes nunca.", "Los choques solo", "se cuentan.",
                                    "Huellas te marcan", "el camino."]),
    "sheriff": dict(nombre="Sheriff", vidas=3, niebla=False, pista=False,
                    descripcion=["3 vidas.", "Cada choque quita", "una vida.", "Sin vidas:",
                                 "vuelves a empezar."]),
    "forajido": dict(nombre="Forajido", vidas=1, niebla=False, pista=False,
                     descripcion=["1 sola vida.", "Si chocas, pierdes", "y vuelves a la",
                                  "entrada.", "Récord de tiempo."]),
    "noche": dict(nombre="Noche sin luna", vidas=3, niebla=True, pista=False,
                  descripcion=["Solo ves lo que", "alumbra tu farol.", "El sonar te guía",
                               "a la salida.", "3 vidas."]),
}
ORDEN_DIFICULTADES = ["explorador", "sheriff", "forajido", "noche"]
GRACIA_CHOQUE = 1.0        # Segundos sin perder otra vida después de un choque
RADIO_NIEBLA = 1.6         # Radio de luz del farol (en casillas) en "Noche sin luna"
PASOS_PISTA = 3            # Cuántas huellas de pista se muestran en Explorador

# Velocidad de gestos (Configuración): segundos para confirmar un movimiento y para repetirlo.
VELOCIDADES = {"Lento": (0.8, 0.8), "Normal": (TIEMPO_MOVER, TIEMPO_REPETICION),
               "Rápido": (0.35, 0.4)}

# Sonar: un "bip" que suena más rápido y más agudo mientras más cerca estás de la salida.
SONAR_INTERVALO_LEJOS = 1.6
SONAR_INTERVALO_CERCA = 0.35
SONAR_NIVELES = 6          # cuántos tonos distintos hay (archivos sonar_0 ... sonar_5)

# ---------------------------------------------------------------------------
# COLORES — TEMA VAQUERO (R, G, B)
# ---------------------------------------------------------------------------
COLOR_CIELO_ARRIBA = (247, 160, 87)
COLOR_CIELO_ABAJO = (255, 222, 160)
COLOR_SOL = (255, 238, 190)
COLOR_MESA_1 = (196, 112, 70)
COLOR_MESA_2 = (178, 98, 62)
COLOR_ARENA = (214, 168, 108)
COLOR_ARENA_PIEDRA = (196, 150, 92)
COLOR_CACTUS = (76, 130, 62)

COLOR_MADERA = (120, 72, 38)
COLOR_MADERA_CLARA = (150, 92, 46)
COLOR_MADERA_VETA = (98, 58, 30)
COLOR_MADERA_OSCURA = (64, 36, 18)

COLOR_CAMINO = (236, 205, 150)
COLOR_CAMINO_GRANO = (226, 192, 134)
COLOR_PARED = (92, 52, 26)
COLOR_PARED_LUZ = (150, 94, 48)

COLOR_TEXTO = (255, 244, 222)          # texto claro sobre madera
COLOR_TEXTO_SUAVE = (240, 214, 170)
COLOR_TINTA = (52, 28, 12)             # texto oscuro sobre el cielo / arena
COLOR_PERGAMINO = (250, 236, 205)      # fondo de los íconos de gesto
COLOR_META = (255, 196, 46)            # oro (estrella de sheriff, selección)
COLOR_META_OSCURO = (150, 96, 10)
COLOR_ACENTO = (150, 210, 110)         # verde: mano detectada / acción lista
COLOR_ALERTA = (214, 62, 44)           # rojo: choque, vidas, sin mano
COLOR_NOCHE = (18, 10, 30)             # oscuridad del modo "Noche sin luna"
COLOR_APAGADO = (110, 90, 80)          # corazón vacío / elementos inactivos

# Alto contraste (Configuración): camino blanco y paredes negras.
COLOR_CONTRASTE_CAMINO = (255, 255, 255)
COLOR_CONTRASTE_PARED = (0, 0, 0)

# Nombres antiguos (los usa prueba_gestos.py)
COLOR_FONDO = COLOR_MADERA_OSCURA
COLOR_PANEL = COLOR_MADERA

# ---------------------------------------------------------------------------
# DEMO AUTOMÁTICA (etapa 1, sin cámara)
# ---------------------------------------------------------------------------
DEMO_PAUSA_ENTRE_PASOS = 0.35   # Segundos entre movimientos automáticos
