"""
tema.py — Piezas de dibujo del tema VAQUERO (todo hecho con figuras de Pygame, sin imágenes
descargadas, para no tener problemas de derechos de autor).

Aquí solo hay funciones que "pintan" algo en una superficie: tablas de madera, cactus,
estrella de sheriff, sombrero, corazones e íconos de los gestos. juego.py las usa para
armar cada pantalla.
"""
import math
import random

import pygame

import config as C


# ============================================================================
# FUENTES
# ============================================================================
_cache_fuentes = {}


def fuente_titulo(tam):
    """Fuente western 'Rye' (licencia SIL OFL). Si falta el archivo, usa una fuente del sistema."""
    clave = ("rye", tam)
    if clave not in _cache_fuentes:
        try:
            _cache_fuentes[clave] = pygame.font.Font(C.RUTA_FUENTE_TITULOS, tam)
        except (FileNotFoundError, OSError, pygame.error):
            _cache_fuentes[clave] = pygame.font.SysFont("georgia,timesnewroman", tam, bold=True)
    return _cache_fuentes[clave]


def fuente_texto(tam, negrita=False):
    """Segoe UI en Windows (acentos y ñ); si no existe, Arial o la fuente por defecto."""
    clave = ("texto", tam, negrita)
    if clave not in _cache_fuentes:
        _cache_fuentes[clave] = pygame.font.SysFont("segoeui,arial,dejavusans", tam, bold=negrita)
    return _cache_fuentes[clave]


def texto(sup, txt, fuente, color, pos, ancla="topleft", sombra=None):
    """Escribe `txt` y devuelve su rectángulo. `sombra` = color de una sombra desplazada."""
    if sombra:
        img = fuente.render(txt, True, sombra)
        r = img.get_rect(**{ancla: pos})
        sup.blit(img, r.move(2, 3))
    img = fuente.render(txt, True, color)
    r = img.get_rect(**{ancla: pos})
    sup.blit(img, r)
    return r


# ============================================================================
# ESCENARIO
# ============================================================================
def degradado(sup, rect, arriba, abajo):
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        color = [int(arriba[i] + (abajo[i] - arriba[i]) * t) for i in range(3)]
        pygame.draw.line(sup, color, (rect.x, rect.y + y), (rect.right, rect.y + y))


def cactus(sup, x, y, escala=1.0):
    """Saguaro sencillo con dos brazos; (x, y) = base del tronco."""
    s, col = escala, C.COLOR_CACTUS
    w = int(18 * s)
    pygame.draw.rect(sup, col, (x - w // 2, y - int(90 * s), w, int(90 * s)), border_radius=w // 2)
    for bx, by, bw, bh in ((-34, -62, 12, 32), (-34, -36, 26, 12), (22, -74, 12, 36), (8, -48, 26, 12)):
        pygame.draw.rect(sup, col, (x + int(bx * s), y + int(by * s), int(bw * s), int(bh * s)),
                         border_radius=max(2, int(6 * s)))


def escenario(ancho, alto):
    """Fondo del desierto (cielo de atardecer, sol, mesetas, arena y cactus). Se dibuja UNA vez."""
    sup = pygame.Surface((ancho, alto))
    degradado(sup, sup.get_rect(), C.COLOR_CIELO_ARRIBA, C.COLOR_CIELO_ABAJO)
    horizonte = int(alto * 0.65)
    pygame.draw.circle(sup, C.COLOR_SOL, (int(ancho * 0.81), int(alto * 0.32)), 70)
    pygame.draw.polygon(sup, C.COLOR_MESA_1, [
        (0, horizonte), (60, horizonte), (90, horizonte - 90), (260, horizonte - 90),
        (300, horizonte), (int(ancho * 0.45), horizonte), (int(ancho * 0.45), alto), (0, alto)])
    pygame.draw.polygon(sup, C.COLOR_MESA_2, [
        (int(ancho * 0.52), horizonte), (int(ancho * 0.61), horizonte),
        (int(ancho * 0.64), horizonte - 140), (int(ancho * 0.79), horizonte - 140),
        (int(ancho * 0.81), horizonte - 60), (int(ancho * 0.88), horizonte - 60),
        (int(ancho * 0.91), horizonte), (ancho, horizonte), (ancho, alto), (int(ancho * 0.52), alto)])
    pygame.draw.rect(sup, C.COLOR_ARENA, (0, horizonte, ancho, alto - horizonte))
    rnd = random.Random(4)                       # semilla fija: siempre el mismo dibujo
    for _ in range(90):
        pygame.draw.circle(sup, C.COLOR_ARENA_PIEDRA,
                           (rnd.randint(0, ancho), rnd.randint(horizonte + 10, alto)), rnd.randint(1, 3))
    return sup


def tabla(sup, rect, claro=False, borde=True):
    """Tabla de madera con vetas horizontales y clavos en las esquinas."""
    color = C.COLOR_MADERA_CLARA if claro else C.COLOR_MADERA
    pygame.draw.rect(sup, color, rect, border_radius=6)
    for y in range(rect.y + 22, rect.bottom - 4, 22):
        pygame.draw.line(sup, C.COLOR_MADERA_VETA, (rect.x + 4, y), (rect.right - 5, y), 2)
    if rect.width > 30 and rect.height > 24:
        for dx, dy in ((10, 10), (rect.width - 10, 10), (10, rect.height - 10),
                       (rect.width - 10, rect.height - 10)):
            pygame.draw.circle(sup, C.COLOR_MADERA_OSCURA, (rect.x + dx, rect.y + dy), 3)
    if borde:
        pygame.draw.rect(sup, C.COLOR_MADERA_OSCURA, rect, 3, border_radius=6)


def letrero(sup, rect, txt, fuente, poste=True):
    """Letrero de madera clavado en un poste (ENTRADA / SALIDA)."""
    if poste:
        pygame.draw.rect(sup, C.COLOR_MADERA_OSCURA, (rect.centerx - 3, rect.bottom, 6, 30))
    tabla(sup, rect)
    texto(sup, txt, fuente, C.COLOR_TEXTO, rect.center, "center")


# ============================================================================
# OBJETOS
# ============================================================================
def estrella_sheriff(sup, centro, radio, color=None, borde=None):
    """Estrella de 6 picos con bolitas en las puntas (la meta del laberinto)."""
    color, borde = color or C.COLOR_META, borde or C.COLOR_META_OSCURO
    cx, cy = centro
    puntos = []
    for i in range(12):
        a = -math.pi / 2 + i * math.pi / 6
        r = radio if i % 2 == 0 else radio * 0.5
        puntos.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pygame.draw.polygon(sup, color, puntos)
    pygame.draw.polygon(sup, borde, puntos, 2)
    for i in range(6):
        a = -math.pi / 2 + i * math.pi / 3
        pygame.draw.circle(sup, color, (cx + radio * math.cos(a), cy + radio * math.sin(a)),
                           max(2, int(radio * 0.18)))
    pygame.draw.circle(sup, borde, (int(cx), int(cy)), max(3, int(radio * 0.27)), 2)


def sombrero(sup, cx, abajo, ancho):
    """Sombrero vaquero cuyo borde (ala) queda a la altura `abajo`, centrado en `cx`."""
    a = ancho
    alto_ala = max(4, int(a * 0.26))
    ala = pygame.Rect(0, 0, a, alto_ala)
    ala.midbottom = (cx, abajo + alto_ala // 2)
    copa = pygame.Rect(0, 0, int(a * 0.52), int(a * 0.42))
    copa.midbottom = (cx, ala.centery)
    pygame.draw.ellipse(sup, (110, 66, 30), ala)
    r = max(2, int(a * 0.18))
    pygame.draw.rect(sup, (130, 80, 38), copa, border_top_left_radius=r, border_top_right_radius=r)
    pygame.draw.rect(sup, (60, 30, 12), (copa.x, copa.bottom - max(2, int(a * 0.12)), copa.width,
                                         max(2, int(a * 0.08))))
    pygame.draw.ellipse(sup, (70, 40, 16), ala, 2)


def corazon(sup, centro, tam, color):
    x, y = centro
    r = tam
    pygame.draw.circle(sup, color, (x - r // 2, y - r // 4), r // 2 + 1)
    pygame.draw.circle(sup, color, (x + r // 2, y - r // 4), r // 2 + 1)
    pygame.draw.polygon(sup, color, [(x - r, y - r // 6), (x + r, y - r // 6), (x, y + r)])


def vidas(sup, x_derecha, cy, actuales, total, tam=10):
    """Fila de corazones alineada a la derecha. Devuelve la x donde termina (a la izquierda)."""
    x = x_derecha
    for i in reversed(range(total)):
        corazon(sup, (x - tam - 2, cy), tam, C.COLOR_ALERTA if i < actuales else C.COLOR_APAGADO)
        x -= tam * 2 + 8
    return x


def huella(sup, centro, angulo_grados, color):
    """Huella de herradura (para la pista del modo Explorador)."""
    cx, cy = centro
    a = math.radians(angulo_grados)
    for lado in (-1, 1):
        ox = cx + lado * 7 * math.cos(a + math.pi / 2)
        oy = cy + lado * 7 * math.sin(a + math.pi / 2)
        rect = pygame.Rect(0, 0, 9, 12)
        rect.center = (ox, oy)
        pygame.draw.ellipse(sup, color, rect)


def flecha(sup, centro, direccion, tam, color, borde=(0, 0, 0)):
    """Flecha gruesa apuntando en `direccion` ("ARRIBA", "ABAJO", "IZQUIERDA", "DERECHA")."""
    cx, cy = centro
    base = [(0, -1), (0.62, -0.12), (0.26, -0.12), (0.26, 0.8), (-0.26, 0.8), (-0.26, -0.12),
            (-0.62, -0.12)]
    giro = {"ARRIBA": 0, "DERECHA": 90, "ABAJO": 180, "IZQUIERDA": 270}[direccion]
    a = math.radians(giro)
    puntos = [(cx + tam * (x * math.cos(a) - y * math.sin(a)),
               cy + tam * (x * math.sin(a) + y * math.cos(a))) for x, y in base]
    pygame.draw.polygon(sup, color, puntos)
    pygame.draw.polygon(sup, borde, puntos, 3)


# ============================================================================
# ÍCONOS DE GESTOS (sustituyen a la imagen de la cámara)
# ============================================================================
def _mano(sup, cx, cy, s, extendidos, pulgar, relleno, linea):
    """
    Mano vista de frente. `extendidos` = 4 booleanos (índice, medio, anular, meñique).
    `pulgar` = "fuera" (abierto), "cruzado" (sobre los dedos, como en el puño) o None.
    """
    g = max(2, int(s * 0.06))
    palma = pygame.Rect(0, 0, int(s * 0.9), int(s * 0.8))
    palma.midtop = (cx, cy - int(s * 0.05))
    # Dedos: x relativa, altura si está extendido.
    dedos = [(-0.32, 0.72), (-0.11, 0.82), (0.11, 0.76), (0.32, 0.6)]
    for (dx, largo), ext in zip(dedos, extendidos):
        w = int(s * 0.21)
        h = int(s * largo) if ext else int(s * 0.22)
        r = pygame.Rect(0, 0, w, h + int(s * 0.12))
        r.midbottom = (cx + int(dx * s), palma.top + int(s * 0.12))
        pygame.draw.rect(sup, relleno, r, border_radius=w // 2)
        pygame.draw.rect(sup, linea, r, g, border_radius=w // 2)
    if pulgar == "fuera":
        pts = [(palma.left + s * 0.05, palma.top + s * 0.45), (palma.left - s * 0.32, palma.top + s * 0.05),
               (palma.left - s * 0.18, palma.top - s * 0.06), (palma.left + s * 0.12, palma.top + s * 0.25)]
        pygame.draw.polygon(sup, relleno, pts)
        pygame.draw.polygon(sup, linea, pts, g)
    pygame.draw.rect(sup, relleno, palma, border_radius=int(s * 0.22))
    pygame.draw.rect(sup, linea, palma, g, border_radius=int(s * 0.22))
    # Borra la línea entre dedos y palma para que se vean unidos.
    for (dx, _), ext in zip(dedos, extendidos):
        w = int(s * 0.21) - 2 * g
        pygame.draw.rect(sup, relleno, (cx + int(dx * s) - w // 2, palma.top - g, w, 2 * g + 1))
    if pulgar == "cruzado":
        r = pygame.Rect(0, 0, int(s * 0.62), int(s * 0.2))
        r.midleft = (palma.left - int(s * 0.04), palma.top + int(s * 0.3))
        pygame.draw.rect(sup, relleno, r, border_radius=r.height // 2)
        pygame.draw.rect(sup, linea, r, g, border_radius=r.height // 2)


def icono_gesto(sup, gesto, centro, tam, activo=True):
    """
    Dibuja el gesto detectado: flechas para las direcciones y una mano para palma, puño
    y cuernos. `gesto` es el texto del Gesto ("ARRIBA", "PALMA", "SIN_MANO", ...).
    `tam` = radio aproximado del ícono.
    """
    cx, cy = centro
    fondo = C.COLOR_PERGAMINO if activo else (225, 210, 185)
    pygame.draw.circle(sup, fondo, centro, tam)
    pygame.draw.circle(sup, C.COLOR_MADERA_OSCURA, centro, tam, 4)
    tinta, piel = C.COLOR_TINTA, (247, 214, 170)
    s = tam * 0.82
    if gesto in ("ARRIBA", "ABAJO", "IZQUIERDA", "DERECHA"):
        flecha(sup, centro, gesto, tam * 0.62, C.COLOR_META if activo else (210, 180, 120), tinta)
    elif gesto == "PALMA":
        _mano(sup, cx + int(s * 0.08), cy - int(s * 0.02), s, [True] * 4, "fuera", piel, tinta)
    elif gesto == "PUNO":
        _mano(sup, cx + int(s * 0.04), cy - int(s * 0.32), s, [False] * 4, "cruzado", piel, tinta)
    elif gesto == "CUERNOS":
        _mano(sup, cx, cy - int(s * 0.02), s, [True, False, False, True], "cruzado", piel, tinta)
    elif gesto == "NINGUNO":
        # Hay mano, pero no es un gesto conocido: mano gris + signo de interrogación pequeño.
        _mano(sup, cx + int(s * 0.08), cy - int(s * 0.02), s, [True] * 4, "fuera", (220, 205, 185),
              C.COLOR_APAGADO)
        pygame.draw.circle(sup, C.COLOR_META, (cx + int(tam * 0.55), cy - int(tam * 0.5)), int(tam * 0.3))
        pygame.draw.circle(sup, tinta, (cx + int(tam * 0.55), cy - int(tam * 0.5)), int(tam * 0.3), 2)
        texto(sup, "?", fuente_titulo(int(tam * 0.42)), tinta, (cx + int(tam * 0.55), cy - int(tam * 0.48)),
              "center")
    else:
        # SIN_MANO: no se ve ninguna mano.
        texto(sup, "?", fuente_titulo(int(tam * 1.1)), C.COLOR_ALERTA, (cx, cy + int(tam * 0.08)), "center")
