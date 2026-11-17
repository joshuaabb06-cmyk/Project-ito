"""
juego.py — Todo lo que se DIBUJA con Pygame (tema vaquero): menús, laberinto, personaje,
barra superior, panel lateral del gesto y pantallas de mensaje.

No contiene reglas del juego ni detección de gestos: solo recibe datos y los pinta.
IMPORTANTE: la cámara nunca se muestra. En su lugar se dibuja un ícono del gesto detectado
y un puntito que indica dónde está la mano dentro del encuadre.
"""
import glob
import math
import os
import random

import pygame

import config as C
import tema as T


# ============================================================================
# PERSONAJES
# ============================================================================
def lista_personajes():
    """
    Busca las imágenes PNG de assets/personajes/. Devuelve [(archivo, nombre_bonito), ...].
    Si la carpeta está vacía se usa el dino dibujado con figuras (archivo = None).
    """
    rutas = sorted(glob.glob(os.path.join(C.CARPETA_PERSONAJES, "*.png")))
    personajes = []
    for ruta in rutas:
        nombre = os.path.splitext(os.path.basename(ruta))[0].replace("_", " ").replace("-", " ")
        personajes.append((os.path.basename(ruta), nombre.capitalize()))
    return personajes or [(None, "Dino (dibujo)")]


def cargar_imagen_personaje(archivo, tam):
    """Carga y escala (manteniendo proporción) un personaje. None si no existe o falla."""
    if not archivo:
        return None
    ruta = os.path.join(C.CARPETA_PERSONAJES, archivo)
    try:
        img = pygame.image.load(ruta).convert_alpha()
    except (pygame.error, FileNotFoundError) as e:
        print(f"[Personaje] No se pudo cargar {ruta} ({e}): se usa el dibujo de respaldo.")
        return None
    escala = tam / max(img.get_width(), img.get_height())
    return pygame.transform.smoothscale(
        img, (max(1, int(img.get_width() * escala)), max(1, int(img.get_height() * escala))))


def punto_cabeza(img):
    """
    Busca la parte MÁS ALTA del personaje (su cabeza) mirando los píxeles no transparentes.
    Ahí se coloca el sombrero, así funciona con cualquier personaje que agreguen.
    Devuelve (x, y) relativo a la imagen.
    """
    mascara = pygame.mask.from_surface(img, 60)
    ancho, alto = img.get_size()
    for y in range(alto):
        xs = [x for x in range(ancho) if mascara.get_at((x, y))]
        if xs:
            # Promedia las columnas ocupadas en una franja de unos píxeles para centrar el sombrero.
            franja = [x for yy in range(y, min(alto, y + max(3, alto // 12)))
                      for x in range(ancho) if mascara.get_at((x, yy))]
            return (sum(franja) // len(franja), y)
    return (ancho // 2, 0)


def dibujar_dino_respaldo(sup, cx, cy, tam, mirando_izquierda=False):
    """Dinosaurio sencillo hecho con figuras (por si no hay ninguna imagen)."""
    s = tam / 2
    d = -1 if mirando_izquierda else 1
    verde, oscuro = (95, 190, 80), (50, 120, 45)
    pygame.draw.polygon(sup, oscuro, [(cx - d * s * 0.3, cy + s * 0.1), (cx - d * s * 0.95, cy + s * 0.55),
                                      (cx - d * s * 0.3, cy + s * 0.55)])
    pygame.draw.ellipse(sup, verde, (cx - s * 0.55, cy - s * 0.2, s * 1.1, s * 0.95))
    pygame.draw.circle(sup, verde, (int(cx + d * s * 0.35), int(cy - s * 0.4)), int(s * 0.42))
    for i in range(3):
        bx = cx - d * s * (0.3 - i * 0.25)
        pygame.draw.polygon(sup, oscuro, [(bx - s * 0.1, cy - s * 0.15 - i * s * 0.12),
                                          (bx, cy - s * 0.4 - i * s * 0.12),
                                          (bx + s * 0.1, cy - s * 0.15 - i * s * 0.12)])
    ox, oy = int(cx + d * s * 0.5), int(cy - s * 0.5)
    pygame.draw.circle(sup, (255, 255, 255), (ox, oy), int(s * 0.14))
    pygame.draw.circle(sup, (20, 20, 20), (ox + d * 2, oy), int(s * 0.07))
    for dx in (-0.25, 0.2):
        pygame.draw.rect(sup, oscuro, (cx + dx * s - s * 0.1, cy + s * 0.6, s * 0.2, s * 0.3), border_radius=3)


class Personaje:
    """Imagen del personaje + sombrero opcional + animación al moverse de casilla."""

    def __init__(self, archivo, tam, con_sombrero=True):
        self.tam = tam
        self.con_sombrero = con_sombrero
        self.mirando_izquierda = False
        self.origen = self.objetivo = (0.0, 0.0)
        self.t_inicio = 0.0
        self.cambiar(archivo)

    def cambiar(self, archivo):
        self.archivo = archivo
        self.imagen = cargar_imagen_personaje(archivo, self.tam)
        if self.imagen:
            volteada = pygame.transform.flip(self.imagen, True, False)
            self._imgs = {False: self.imagen, True: volteada}
            self._cabezas = {False: punto_cabeza(self.imagen), True: punto_cabeza(volteada)}

    def colocar(self, centro):
        self.origen = self.objetivo = centro
        self.t_inicio = 0.0

    def ir_a(self, centro, ahora):
        if centro[0] < self.objetivo[0]:
            self.mirando_izquierda = True
        elif centro[0] > self.objetivo[0]:
            self.mirando_izquierda = False
        self.origen = self.posicion(ahora)
        self.objetivo = centro
        self.t_inicio = ahora

    def posicion(self, ahora):
        t = min(1.0, (ahora - self.t_inicio) / C.DURACION_ANIMACION) if C.DURACION_ANIMACION else 1
        t = 1 - (1 - t) ** 3
        return (self.origen[0] + (self.objetivo[0] - self.origen[0]) * t,
                self.origen[1] + (self.objetivo[1] - self.origen[1]) * t)

    def dibujar_en(self, sup, centro, izquierda=None):
        """Dibuja el personaje en `centro` (se usa también en el menú, a otro tamaño)."""
        izq = self.mirando_izquierda if izquierda is None else izquierda
        cx, cy = int(centro[0]), int(centro[1])
        if self.imagen:
            img = self._imgs[izq]
            r = img.get_rect(center=(cx, cy))
            sup.blit(img, r)
            hx, hy = self._cabezas[izq]
            cabeza = (r.x + hx, r.y + hy)
        else:
            dibujar_dino_respaldo(sup, cx, cy, self.tam, izq)
            cabeza = (cx + (-1 if izq else 1) * int(self.tam * 0.17), cy - int(self.tam * 0.41))
        if self.con_sombrero:
            T.sombrero(sup, cabeza[0], cabeza[1] + int(self.tam * 0.06), int(self.tam * 0.55))

    def dibujar(self, sup, ahora):
        self.dibujar_en(sup, self.posicion(ahora))


# ============================================================================
# VISTA PRINCIPAL
# ============================================================================
class Vista:
    """Ventana del juego. Calcula el acomodo en pantalla y dibuja cada elemento."""

    def __init__(self, laberinto, titulo="Project-ito", personaje=None, sombrero=True):
        pygame.init()
        pygame.display.set_caption(titulo)
        self.lab = laberinto
        self.contraste = False

        # --- Tamaño de cada fila/columna de la matriz (pares = paredes delgadas) ---------
        def medida(i):
            if C.PASO == 2:
                return C.TAMANO_CASILLA if i % 2 == 1 else C.GROSOR_PARED
            return C.TAMANO_CASILLA

        self.anchos = [medida(c) for c in range(laberinto.columnas)]
        self.altos = [medida(f) for f in range(laberinto.filas)]
        self.x0 = [sum(self.anchos[:c]) for c in range(laberinto.columnas)]
        self.y0 = [sum(self.altos[:f]) for f in range(laberinto.filas)]
        ancho_lab, alto_lab = sum(self.anchos), sum(self.altos)

        espacio_etiquetas = 80         # lugar para los letreros ENTRADA / SALIDA a los lados
        self.rect_lab = pygame.Rect(C.MARGEN + espacio_etiquetas, C.ALTO_BARRA_SUPERIOR + C.MARGEN,
                                    ancho_lab, alto_lab)
        x_panel = self.rect_lab.right + espacio_etiquetas
        ancho = x_panel + C.ANCHO_PANEL
        alto = max(self.rect_lab.bottom + C.MARGEN, 720)
        self.rect_panel = pygame.Rect(x_panel, C.ALTO_BARRA_SUPERIOR,
                                      C.ANCHO_PANEL - C.MARGEN, alto - C.ALTO_BARRA_SUPERIOR)
        banderas = pygame.SCALED | (pygame.FULLSCREEN if C.PANTALLA_COMPLETA else 0)
        self.pantalla = pygame.display.set_mode((ancho, alto), banderas)
        self.ancho, self.alto = ancho, alto

        # Fuentes: Rye (western) para títulos, Segoe UI para texto normal.
        self.f_logo = T.fuente_titulo(76)
        self.f_grande = T.fuente_titulo(52)
        self.f_titulo = T.fuente_titulo(26)
        self.f_boton = T.fuente_titulo(28)
        self.f_letrero = T.fuente_titulo(13)
        self.f_media = T.fuente_texto(22, True)
        self.f_normal = T.fuente_texto(19)
        self.f_chica = T.fuente_texto(16)
        self.f_chica_n = T.fuente_texto(16, True)

        self._escenario = T.escenario(ancho, alto)
        self._lab_cache = {}
        self.personaje = Personaje(personaje, int(C.TAMANO_CASILLA * 0.8), sombrero)
        self.personaje.colocar(self.centro(laberinto.jugador))
        self.t_choque = -10.0
        self.dir_choque = None
        self._aviso = ("", -10.0)
        self._subtitulo = ("", -10.0)
        self._niebla = None

    # ------------------------------------------------------------ coordenadas
    def rect_celda(self, fila, col):
        return pygame.Rect(self.rect_lab.x + self.x0[col], self.rect_lab.y + self.y0[fila],
                           self.anchos[col], self.altos[fila])

    def centro(self, pos):
        r = self.rect_celda(*pos)
        return (float(r.centerx), float(r.centery))

    # ------------------------------------------------------- eventos visuales
    def jugador_movido(self, ahora):
        self.personaje.ir_a(self.centro(self.lab.jugador), ahora)

    def jugador_choco(self, ahora, direccion=None):
        self.t_choque = ahora
        self.dir_choque = direccion

    def jugador_reiniciado(self):
        self.personaje.colocar(self.centro(self.lab.jugador))
        self.personaje.mirando_izquierda = False

    def avisar(self, txt, ahora):
        """Mensaje breve sobre el laberinto (p. ej. '¡Choque! Te quedan 2 vidas')."""
        self._aviso = (txt, ahora)

    def subtitulo(self, txt, ahora):
        """Subtítulo de lo que dice la voz guía (para quien no escucha bien o sin bocinas)."""
        self._subtitulo = (txt, ahora)

    # ------------------------------------------------------------ utilidades
    def texto(self, txt, fuente, color, pos, ancla="topleft", sombra=None):
        return T.texto(self.pantalla, txt, fuente, color, pos, ancla, sombra)

    def barra(self, rect, progreso, color=None):
        pygame.draw.rect(self.pantalla, C.COLOR_MADERA_OSCURA, rect, border_radius=rect.height // 2)
        if progreso:
            lleno = rect.copy()
            lleno.width = max(rect.height, int(rect.width * min(1.0, progreso)))
            pygame.draw.rect(self.pantalla, color or C.COLOR_META, lleno, border_radius=rect.height // 2)

    def dibujar_fondo(self):
        self.pantalla.blit(self._escenario, (0, 0))

    @staticmethod
    def presentar():
        pygame.display.flip()

    # ============================================================ BARRA SUPERIOR
    def dibujar_barra_superior(self, estado, segundos, dificultad=None, vidas=None):
        T.tabla(self.pantalla, pygame.Rect(0, 0, self.ancho, C.ALTO_BARRA_SUPERIOR), borde=False)
        pygame.draw.line(self.pantalla, C.COLOR_MADERA_OSCURA, (0, C.ALTO_BARRA_SUPERIOR - 1),
                         (self.ancho, C.ALTO_BARRA_SUPERIOR - 1), 3)
        cy = C.ALTO_BARRA_SUPERIOR // 2
        self.texto("Project-ito", self.f_titulo, C.COLOR_TEXTO, (C.MARGEN, cy), "midleft")
        m, s = divmod(int(segundos), 60)
        x = self.ancho - C.MARGEN
        for item in (f"Pasos {self.lab.movimientos}", f"Tiempo {m:02d}:{s:02d}"):
            x = self.texto(item, self.f_media, C.COLOR_TEXTO_SUAVE, (x, cy), "midright").left - 26
        if vidas is not None:
            actuales, total = vidas
            x = T.vidas(self.pantalla, x, cy, actuales, total, 10)
            x = self.texto(f"Vidas {actuales}", self.f_media, C.COLOR_TEXTO_SUAVE, (x - 2, cy),
                           "midright").left - 26
        etiqueta = f"{dificultad}  ·  {estado}" if dificultad else estado
        self.texto(etiqueta, self.f_media, C.COLOR_TEXTO_SUAVE, (x, cy), "midright")

    # ============================================================== LABERINTO
    def _colores_lab(self):
        if self.contraste:
            return C.COLOR_CONTRASTE_CAMINO, C.COLOR_CONTRASTE_PARED
        return C.COLOR_CAMINO, C.COLOR_PARED

    def _superficie_laberinto(self):
        """Parte fija del laberinto (piso, paredes, marco y letreros). Se dibuja una sola vez."""
        clave = self.contraste
        if clave in self._lab_cache:
            return self._lab_cache[clave]
        sup = pygame.Surface((self.ancho, self.alto), pygame.SRCALPHA)
        camino, pared = self._colores_lab()
        pygame.draw.rect(sup, C.COLOR_MADERA_OSCURA if not self.contraste else (0, 0, 0),
                         self.rect_lab.inflate(26, 26), border_radius=8)
        pygame.draw.rect(sup, camino, self.rect_lab)
        aberturas = self._aberturas()
        for (f, c), _ in aberturas:        # que los huecos de entrada/salida atraviesen el marco
            r = self.rect_celda(f, c)
            if c in (0, self.lab.columnas - 1):
                r = r.inflate(30, 0).move(-15 if c == 0 else 15, 0)
            else:
                r = r.inflate(0, 30).move(0, -15 if f == 0 else 15)
            pygame.draw.rect(sup, camino, r)
        if not self.contraste:              # granitos de arena en el piso
            rnd = random.Random(7)
            for f in range(1, self.lab.filas, 2):
                for c in range(1, self.lab.columnas, 2):
                    r = self.rect_celda(f, c)
                    for _ in range(5):
                        pygame.draw.circle(sup, C.COLOR_CAMINO_GRANO, (rnd.randint(r.x + 4, r.right - 4),
                                                                       rnd.randint(r.y + 4, r.bottom - 4)),
                                           rnd.randint(1, 3))
        for f in range(self.lab.filas):
            for c in range(self.lab.columnas):
                if self.lab.matriz[f][c] == 1:
                    pygame.draw.rect(sup, pared, self.rect_celda(f, c))
        if not self.contraste:              # vetas de madera: las paredes parecen cercas
            for f in range(self.lab.filas):
                for c in range(self.lab.columnas):
                    if self.lab.matriz[f][c] != 1:
                        continue
                    r = self.rect_celda(f, c)
                    if r.width > r.height:
                        pygame.draw.line(sup, C.COLOR_PARED_LUZ, (r.x, r.y + 2), (r.right - 1, r.y + 2), 2)
                    elif r.height > r.width:
                        pygame.draw.line(sup, C.COLOR_PARED_LUZ, (r.x + 2, r.y), (r.x + 2, r.bottom - 1), 2)
                    else:
                        pygame.draw.rect(sup, C.COLOR_MADERA_OSCURA, r.inflate(2, 2))
        for (f, c), es_salida in aberturas:
            self._letrero_abertura(sup, f, c, "SALIDA" if es_salida else "ENTRADA")
        self._lab_cache[clave] = sup
        return sup

    def _aberturas(self):
        """Huecos del borde: [((fila, col), es_salida), ...]."""
        res = []
        for f in range(self.lab.filas):
            for c in range(self.lab.columnas):
                borde = f in (0, self.lab.filas - 1) or c in (0, self.lab.columnas - 1)
                if borde and self.lab.matriz[f][c] == 0:
                    dist = lambda p: abs(p[0] - f) + abs(p[1] - c)
                    res.append(((f, c), dist(self.lab.meta) < dist(self.lab.inicio)))
        return res

    def _letrero_abertura(self, sup, f, c, txt):
        r = self.rect_celda(f, c)
        ancho = self.f_letrero.size(txt)[0] + 14
        rect = pygame.Rect(0, 0, ancho, 26)
        if c == 0:
            rect.midright = (r.left - 12, r.centery - 30)
        elif c == self.lab.columnas - 1:
            rect.midleft = (r.right + 10, r.centery + 34)
        elif f == 0:
            rect.midbottom = (r.centerx, r.top - 16)
        else:
            rect.midtop = (r.centerx, r.bottom + 16)
        T.letrero(sup, rect, txt, self.f_letrero)

    def dibujar_laberinto(self, ahora, pista=None):
        """Laberinto + meta. `pista` = lista de casillas a marcar con huellas (Explorador)."""
        self.pantalla.blit(self._superficie_laberinto(), (0, 0))
        if pista:
            self._dibujar_pista(pista)
        cx, cy = self.centro(self.lab.meta)
        brillo = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(brillo, (255, 226, 130, int(150 + 60 * math.sin(ahora * 4))), (35, 35), 30)
        self.pantalla.blit(brillo, (cx - 35, cy - 35))
        T.estrella_sheriff(self.pantalla, (cx, cy), C.TAMANO_CASILLA * (0.33 + 0.03 * math.sin(ahora * 5)))
        # Choque: marco rojo + sacudida hacia la pared (no solo color: también aviso de texto y sonido).
        if ahora - self.t_choque < 0.35:
            pygame.draw.rect(self.pantalla, C.COLOR_ALERTA, self.rect_lab.inflate(14, 14), 6, border_radius=6)

    def _dibujar_pista(self, pista):
        previa = self.lab.jugador
        for i, celda in enumerate(pista):
            (f0, c0), (f1, c1) = previa, celda
            angulo = math.degrees(math.atan2(f1 - f0, c1 - c0))
            alfa = max(60, 200 - i * 50)
            capa = pygame.Surface((40, 40), pygame.SRCALPHA)
            T.huella(capa, (20, 20), angulo, (*C.COLOR_MADERA_VETA, alfa))
            cx, cy = self.centro(celda)
            self.pantalla.blit(capa, (cx - 20, cy - 20))
            previa = celda

    def dibujar_personaje(self, ahora):
        pos = self.personaje.posicion(ahora)
        # Sacudida breve al chocar, hacia la pared contra la que se chocó.
        t = ahora - self.t_choque
        if t < 0.25 and self.dir_choque:
            df, dc = {"ARRIBA": (-1, 0), "ABAJO": (1, 0), "IZQUIERDA": (0, -1), "DERECHA": (0, 1)}[self.dir_choque]
            k = math.sin(t / 0.25 * math.pi) * 7
            pos = (pos[0] + dc * k, pos[1] + df * k)
        self.personaje.dibujar_en(self.pantalla, pos)

    def dibujar_niebla(self, ahora):
        """Modo 'Noche sin luna': todo oscuro excepto un círculo de luz alrededor del personaje."""
        radio = int(C.RADIO_NIEBLA * (C.TAMANO_CASILLA + C.GROSOR_PARED))
        if self._niebla is None:
            tam = self.rect_lab.width * 2 + radio * 2
            self._niebla = pygame.Surface((tam, tam), pygame.SRCALPHA)
            self._niebla.fill((*C.COLOR_NOCHE, 246))
            c = tam // 2
            for r in range(radio + 40, 0, -2):          # borde suave de la luz
                alfa = 0 if r < radio - 40 else int(246 * (r - (radio - 40)) / 80)
                pygame.draw.circle(self._niebla, (*C.COLOR_NOCHE, min(246, alfa)), (c, c), r)
        px, py = self.personaje.posicion(ahora)
        mitad = self._niebla.get_width() // 2
        self.pantalla.set_clip(self.rect_lab)
        self.pantalla.blit(self._niebla, (px - mitad, py - mitad))
        self.pantalla.set_clip(None)
        brillo = 5 + int(1.5 * math.sin(ahora * 9))     # el farol titila un poquito
        pygame.draw.circle(self.pantalla, (255, 200, 90), (int(px + 22), int(py + 12)), brillo)

    def dibujar_aviso(self, ahora):
        txt, t = self._aviso
        if txt and ahora - t < 1.6:
            img = self.f_media.render(txt, True, C.COLOR_TINTA)
            r = img.get_rect(center=(self.rect_lab.centerx, self.rect_lab.y + 34))
            pygame.draw.rect(self.pantalla, C.COLOR_META, r.inflate(28, 12), border_radius=8)
            pygame.draw.rect(self.pantalla, C.COLOR_MADERA_OSCURA, r.inflate(28, 12), 3, border_radius=8)
            self.pantalla.blit(img, r)

    def dibujar_subtitulo(self, ahora):
        txt, t = self._subtitulo
        if txt and ahora - t < 1.8:
            img = self.f_media.render(f"«{txt}»", True, (255, 255, 255))
            r = img.get_rect(midbottom=(self.ancho // 2, self.alto - 48))
            caja = pygame.Surface(r.inflate(26, 12).size, pygame.SRCALPHA)
            caja.fill((0, 0, 0, 185))
            self.pantalla.blit(caja, r.inflate(26, 12))
            self.pantalla.blit(img, r)

    # =========================================================== PANEL DE GESTO
    def indicador_mano(self, rect, lectura, estado_camara):
        """
        Recuadro que representa el encuadre de la cámara (sin mostrar la imagen). Un punto
        marca dónde está la palma. Devuelve (texto_estado, color).
        """
        pygame.draw.rect(self.pantalla, C.COLOR_PERGAMINO, rect, border_radius=6)
        pygame.draw.rect(self.pantalla, C.COLOR_MADERA_OSCURA, rect, 3, border_radius=6)
        zona = rect.inflate(-rect.width * 0.4, -rect.height * 0.36)       # zona "ideal" al centro
        pygame.draw.rect(self.pantalla, (225, 205, 165), zona, 2, border_radius=4)
        if estado_camara != "ok":
            self.texto("...", self.f_media, C.COLOR_TINTA, rect.center, "center")
            return ("Iniciando cámara..." if estado_camara == "iniciando" else "Sin cámara",
                    C.COLOR_TEXTO_SUAVE)
        if lectura.centro is None or lectura.gesto.value == "SIN_MANO":
            self.texto("?", self.f_titulo, C.COLOR_ALERTA, rect.center, "center")
            return "No veo tu mano", C.COLOR_ALERTA
        x = rect.x + 6 + (rect.width - 12) * min(1, max(0, lectura.centro[0]))
        y = rect.y + 6 + (rect.height - 12) * min(1, max(0, lectura.centro[1]))
        dentro = zona.collidepoint(x, y)
        pygame.draw.circle(self.pantalla, C.COLOR_ACENTO if dentro else C.COLOR_META, (int(x), int(y)), 8)
        pygame.draw.circle(self.pantalla, C.COLOR_TINTA, (int(x), int(y)), 8, 2)
        if dentro:
            return "Mano detectada", C.COLOR_ACENTO
        return "Lleva tu mano al centro", C.COLOR_META

    def _bloque_gesto(self, x, y, ancho, estable, progreso, accion, nota, radio=60):
        """Ícono grande del gesto + nombre + barra de 'sostener'. Devuelve la y final."""
        from gestos import NOMBRES     # import local: juego.py no depende de la cámara para la demo
        activo = accion is not None or estable.value not in ("SIN_MANO", "NINGUNO")
        cx = x + ancho // 2
        T.icono_gesto(self.pantalla, estable.value, (cx, y + radio), radio, activo)
        if progreso is not None and accion and progreso > 0.01:   # anillo de progreso (como reloj)
            rect = pygame.Rect(0, 0, radio * 2 + 14, radio * 2 + 14)
            rect.center = (cx, y + radio)
            p = min(1.0, progreso)
            pygame.draw.arc(self.pantalla, C.COLOR_ACENTO if p >= 1 else C.COLOR_META, rect,
                            math.pi / 2 - 2 * math.pi * p, math.pi / 2, 6)
        y += radio * 2 + 12
        self.texto(NOMBRES[estable], self.f_media, C.COLOR_TEXTO, (cx, y), "midtop")
        y += 32
        if nota:
            self.texto(nota, self.f_chica, C.COLOR_TEXTO_SUAVE, (cx, y), "midtop")
        elif accion and progreso is not None:
            lleno = progreso >= 1.0
            etiqueta = f"{accion}: ¡listo!" if lleno else f"Sostén para: {accion}"
            self.texto(etiqueta, self.f_chica, C.COLOR_ACENTO if lleno else C.COLOR_TEXTO, (cx, y), "midtop")
            self.barra(pygame.Rect(x, y + 24, ancho, 12), progreso, C.COLOR_ACENTO if lleno else C.COLOR_META)
        elif estable.value not in ("SIN_MANO", "NINGUNO"):
            self.texto("(sin efecto aquí)", self.f_chica, C.COLOR_TEXTO_SUAVE, (cx, y), "midtop")
        return y + 44

    def _leyenda(self, x, y, ancho, filas):
        self.texto("Gestos", self.f_chica_n, C.COLOR_TEXTO_SUAVE, (x, y))
        for i, (gesto, tiempo, accion) in enumerate(filas):
            yy = y + 24 + i * 25
            self.texto(f"{gesto}  {tiempo:g} s", self.f_chica, C.COLOR_TEXTO, (x, yy))
            self.texto(accion, self.f_chica, C.COLOR_META, (x + ancho, yy), "topright")

    def dibujar_panel_juego(self, lectura, estable, progreso, accion, nota, leyenda, estado_camara,
                            vidas=None, sonar=None):
        """Panel derecho: ícono del gesto, indicador de mano, vidas/sonar y gestos disponibles."""
        panel = self.rect_panel.inflate(0, -2 * C.MARGEN)
        T.tabla(self.pantalla, panel)
        x, ancho = panel.x + 18, panel.width - 36
        self.texto("TU MANO", self.f_titulo, C.COLOR_TEXTO, (panel.centerx, panel.y + 12), "midtop",
                   sombra=C.COLOR_MADERA_OSCURA)
        y = self._bloque_gesto(x, panel.y + 52, ancho, estable, progreso, accion, nota)
        rect_ind = pygame.Rect(x, y, 104, 78)
        estado_txt, color = self.indicador_mano(rect_ind, lectura, estado_camara)
        self.texto(estado_txt, self.f_chica_n, color, (rect_ind.right + 12, rect_ind.y + 14))
        self.texto("Encuadre de la cámara", self.f_chica, C.COLOR_TEXTO_SUAVE,
                   (rect_ind.right + 12, rect_ind.y + 40))
        y = rect_ind.bottom + 14
        if sonar is not None:                    # equivalente visual del sonar (no solo sonido)
            self.texto("Sonar: cercanía a la salida", self.f_chica, C.COLOR_TEXTO_SUAVE, (x, y))
            self.barra(pygame.Rect(x, y + 22, ancho, 10), sonar, C.COLOR_META)
            y += 44
        self._leyenda(x, y, ancho, leyenda)
        self.texto(f"Cámara: {lectura.fps:.0f} FPS", self.f_chica, C.COLOR_TEXTO_SUAVE,
                   (x, panel.bottom - 28))

    def dibujar_panel_demo(self, lineas):
        """Panel lateral de la demo automática (sin cámara)."""
        panel = self.rect_panel.inflate(0, -2 * C.MARGEN)
        T.tabla(self.pantalla, panel)
        x, y = panel.x + 18, panel.y + 18
        self.texto("DEMO AUTOMÁTICA", self.f_titulo, C.COLOR_META, (x, y))
        for i, linea in enumerate(lineas):
            self.texto(linea, self.f_normal, C.COLOR_TEXTO, (x, y + 50 + i * 30))

    # ============================================================== MENSAJES
    def dibujar_mensaje(self, titulo, lineas=(), color=None, opciones=None, seleccion=0, progreso=None):
        """Tabla de madera sobre el laberinto: Pausa, ¡Ganaste!, ¡Perdiste!."""
        velo = pygame.Surface(self.rect_lab.size, pygame.SRCALPHA)
        velo.fill((30, 14, 4, 170))
        self.pantalla.blit(velo, self.rect_lab)
        opciones = opciones or []
        alto = 110 + len(lineas) * 30 + len(opciones) * 58
        caja = pygame.Rect(0, 0, self.rect_lab.width - 70, alto)
        caja.center = self.rect_lab.center
        T.tabla(self.pantalla, caja)
        y = caja.y + 22
        self.texto(titulo, self.f_grande, color or C.COLOR_TEXTO, (caja.centerx, y), "midtop",
                   sombra=C.COLOR_MADERA_OSCURA)
        y += 76
        for linea in lineas:
            self.texto(linea, self.f_normal, C.COLOR_TEXTO, (caja.centerx, y), "midtop")
            y += 30
        y += 6
        for i, op in enumerate(opciones):
            r = pygame.Rect(0, 0, 300, 48)
            r.midtop = (caja.centerx, y)
            self._boton(r, op, i == seleccion, progreso if i == seleccion else None)
            y += 58

    def _boton(self, rect, etiqueta, seleccionado, progreso=None, valor=None):
        T.tabla(self.pantalla, rect, claro=seleccionado)
        if seleccionado:
            pygame.draw.rect(self.pantalla, C.COLOR_META, rect.inflate(8, 8), 4, border_radius=8)
            T.estrella_sheriff(self.pantalla, (rect.x - 26, rect.centery), 14)
        f = self.f_boton if rect.height >= 56 else self.f_titulo
        if valor:
            self.texto(etiqueta, f, C.COLOR_TEXTO, (rect.x + 24, rect.centery), "midleft")
            self.texto(valor, self.f_chica_n, C.COLOR_TEXTO_SUAVE, (rect.right - 20, rect.centery), "midright")
        else:
            self.texto(etiqueta, f, C.COLOR_TEXTO, rect.center, "center")
        if progreso:
            self.barra(pygame.Rect(rect.x + 14, rect.bottom - 11, rect.width - 28, 6), progreso)

    # ========================================================= PANTALLAS DE MENÚ
    def _pie(self, partes):
        self.texto("    ·    ".join(partes), self.f_chica_n, C.COLOR_TINTA, (C.MARGEN + 8, self.alto - 22),
                   "midleft")

    def _mini_mano(self, lectura, estable, estado_camara):
        """Esquina inferior derecha de los menús: ícono del gesto + encuadre (sin cámara)."""
        caja = pygame.Rect(self.ancho - 262, self.alto - 196, 244, 170)
        T.tabla(self.pantalla, caja)
        activo = estable.value not in ("SIN_MANO", "NINGUNO")
        T.icono_gesto(self.pantalla, estable.value, (caja.x + 62, caja.y + 70), 46, activo)
        ind = pygame.Rect(caja.x + 124, caja.y + 30, 100, 76)
        estado_txt, color = self.indicador_mano(ind, lectura, estado_camara)
        self.texto(estado_txt, self.f_chica_n, color, (caja.centerx, caja.bottom - 26), "center")

    def _cabecera(self, titulo, subtitulo=None):
        self.texto(titulo, self.f_grande, C.COLOR_TEXTO, (self.ancho // 2, 46), "midtop", sombra=C.COLOR_TINTA)
        if subtitulo:
            self.texto(subtitulo, self.f_normal, C.COLOR_TINTA, (self.ancho // 2, 116), "midtop")

    def dibujar_menu(self, opciones, seleccion, progreso, lectura, estable, estado_camara, ahora):
        """Pantalla de inicio. `opciones` = [(etiqueta, valor_o_None), ...]."""
        self.dibujar_fondo()
        T.cactus(self.pantalla, 80, 690, 1.3)
        T.cactus(self.pantalla, self.ancho - 70, 500, 0.8)
        self.texto("PROJECT-ITO", self.f_logo, C.COLOR_TEXTO, (self.ancho // 2, 34), "midtop",
                   sombra=C.COLOR_TINTA)
        self.texto("~ El Laberinto del Desierto ~", self.f_titulo, C.COLOR_TINTA, (self.ancho // 2, 128), "midtop")
        # Personaje grande a la izquierda, "respirando".
        grande = getattr(self, "_personaje_menu", None)
        if grande is None or grande.archivo != self.personaje.archivo or \
                grande.con_sombrero != self.personaje.con_sombrero:
            grande = self._personaje_menu = Personaje(self.personaje.archivo, 190, self.personaje.con_sombrero)
        grande.dibujar_en(self.pantalla, (215, 440 + 6 * math.sin(ahora * 2)), izquierda=False)
        for i, (etiqueta, valor) in enumerate(opciones):
            r = pygame.Rect(0, 0, 400, 60)
            r.midtop = (self.ancho // 2, 196 + i * 82)
            self._boton(r, etiqueta, i == seleccion, progreso if i == seleccion else None, valor)
        self._mini_mano(lectura, estable, estado_camara)
        self._pie(["Índice arriba/abajo: elegir", "Palma 1 s: confirmar", "Cuernos 3 s: salir"])

    def dibujar_dificultad(self, claves, seleccion, progreso, records, lectura, estable, estado_camara):
        self.dibujar_fondo()
        self._cabecera("ELIGE TU DIFICULTAD", "La ruta del laberinto es la misma; cambian las reglas")
        w, h, gap = 240, 340, 22
        x0 = (self.ancho - (4 * w + 3 * gap)) // 2
        for i, clave in enumerate(claves):
            d = C.DIFICULTADES[clave]
            r = pygame.Rect(x0 + i * (w + gap), 170, w, h)
            sel = i == seleccion
            T.tabla(self.pantalla, r, claro=sel)
            if sel:
                pygame.draw.rect(self.pantalla, C.COLOR_META, r.inflate(10, 10), 4, border_radius=8)
            self.texto(d["nombre"], self.f_titulo, C.COLOR_TEXTO, (r.centerx, r.y + 22), "midtop")
            if d["vidas"] is None:
                self.texto("Vidas: infinitas", self.f_chica_n, C.COLOR_TEXTO, (r.centerx, r.y + 70), "midtop")
            else:
                total = d["vidas"]
                for k in range(total):
                    T.corazon(self.pantalla, (int(r.centerx + (k - (total - 1) / 2) * 30), r.y + 80), 11,
                              C.COLOR_ALERTA)
            y = r.y + 112
            for linea in d["descripcion"]:
                self.texto(linea, self.f_chica, C.COLOR_TEXTO_SUAVE, (r.x + 18, y))
                y += 25
            rec = records.get(clave)
            rec_txt = f"Récord: {int(rec) // 60:02d}:{int(rec) % 60:02d}" if rec else "Récord: —"
            self.texto(rec_txt, self.f_chica_n, C.COLOR_META, (r.centerx, r.bottom - 34), "midtop")
            if sel and progreso:
                self.barra(pygame.Rect(r.x, r.bottom + 14, r.width, 10), progreso)
        self._mini_mano(lectura, estable, estado_camara)
        self._pie(["Índice izq./der.: elegir", "Palma 1 s: confirmar", "Puño 2 s: regresar"])

    def dibujar_personajes(self, personajes, seleccion, progreso, lectura, estable, estado_camara, ahora):
        self.dibujar_fondo()
        self._cabecera("ELIGE PERSONAJE", f"{seleccion + 1} de {len(personajes)}   ·   "
                                          "Agreguen más PNG en assets/personajes")
        caja = pygame.Rect(0, 0, 340, 340)
        caja.center = (self.ancho // 2 - 60, 360)
        T.tabla(self.pantalla, caja, claro=True)
        pygame.draw.rect(self.pantalla, C.COLOR_META, caja.inflate(10, 10), 4, border_radius=8)
        archivo, nombre = personajes[seleccion]
        vista = getattr(self, "_personaje_vista", None)
        if vista is None or vista.archivo != archivo or vista.con_sombrero != self.personaje.con_sombrero:
            vista = self._personaje_vista = Personaje(archivo, 220, self.personaje.con_sombrero)
        vista.dibujar_en(self.pantalla, (caja.centerx, caja.centery + 20 + 5 * math.sin(ahora * 2)), False)
        self.texto(nombre, self.f_grande, C.COLOR_TEXTO, (caja.centerx, caja.bottom + 18), "midtop",
                   sombra=C.COLOR_TINTA)
        if len(personajes) > 1:
            T.flecha(self.pantalla, (caja.left - 60, caja.centery), "IZQUIERDA", 36, C.COLOR_META, C.COLOR_TINTA)
            T.flecha(self.pantalla, (caja.right + 60, caja.centery), "DERECHA", 36, C.COLOR_META, C.COLOR_TINTA)
        if progreso:
            self.barra(pygame.Rect(caja.x, caja.bottom + 86, caja.width, 10), progreso)
        self._mini_mano(lectura, estable, estado_camara)
        self._pie(["Índice izq./der.: cambiar", "Palma 1 s: elegir", "Puño 2 s: regresar"])

    def dibujar_configuracion(self, filas, seleccion, progreso, lectura, estable, estado_camara):
        """`filas` = [(nombre, valor), ...]. valor: int 0-100 (barra), texto (opción) o None (botón)."""
        self.dibujar_fondo()
        caja = pygame.Rect(60, 140, 760, 70 + len(filas) * 56)
        self.texto("CONFIGURACIÓN", self.f_grande, C.COLOR_TEXTO, (caja.centerx, 46), "midtop", sombra=C.COLOR_TINTA)
        T.tabla(self.pantalla, caja)
        for i, (nombre, valor) in enumerate(filas):
            y = caja.y + 34 + i * 56
            sel = i == seleccion
            if sel:
                hl = pygame.Rect(caja.x + 16, y - 6, caja.width - 32, 48)
                pygame.draw.rect(self.pantalla, C.COLOR_MADERA_CLARA, hl, border_radius=6)
                pygame.draw.rect(self.pantalla, C.COLOR_META, hl, 3, border_radius=6)
                if progreso and valor is None:
                    self.barra(pygame.Rect(hl.x + 10, hl.bottom - 9, hl.width - 20, 5), progreso)
            self.texto(nombre, self.f_titulo, C.COLOR_TEXTO, (caja.x + 40, y + 18), "midleft")
            if isinstance(valor, int):
                r = pygame.Rect(caja.x + 400, y + 12, 240, 12)
                self.barra(r, valor / 100)
                pygame.draw.circle(self.pantalla, C.COLOR_META, (r.x + int(r.width * valor / 100), r.centery), 11)
                pygame.draw.circle(self.pantalla, C.COLOR_MADERA_OSCURA,
                                   (r.x + int(r.width * valor / 100), r.centery), 11, 2)
                self.texto(f"{valor}%", self.f_media, C.COLOR_TEXTO, (caja.right - 36, y + 18), "midright")
            elif valor is not None:
                self.texto(f"<   {valor}   >", self.f_media, C.COLOR_TEXTO, (caja.x + 560, y + 18), "center")
        self._mini_mano(lectura, estable, estado_camara)
        self._pie(["Índice arriba/abajo: elegir", "Índice izq./der.: cambiar", "Puño 2 s: guardar y regresar"])

    # ============================================================ CALIBRACIÓN
    def dibujar_calibracion(self, lectura, estable, progreso, accion, nota, leyenda, estado_camara,
                            flecha_practica, ya_practico):
        """Prueba de gestos antes de jugar. Sin cámara: ícono grande + encuadre + dedos."""
        zona = pygame.Rect(C.MARGEN + 20, C.ALTO_BARRA_SUPERIOR + C.MARGEN,
                           self.rect_panel.x - 2 * C.MARGEN - 40, self.rect_lab.height)
        T.tabla(self.pantalla, zona)
        self.texto("Prueba tus gestos", self.f_grande, C.COLOR_TEXTO, (zona.centerx, zona.y + 18), "midtop",
                   sombra=C.COLOR_MADERA_OSCURA)
        self.texto("Pon tu mano frente a la cámara, a unos 40-60 cm, y apunta con el índice.",
                   self.f_normal, C.COLOR_TEXTO_SUAVE, (zona.centerx, zona.y + 90), "midtop")
        centro_icono = (zona.centerx, zona.y + 250)
        T.icono_gesto(self.pantalla, (flecha_practica or estable.value), centro_icono, 120,
                      estable.value not in ("SIN_MANO", "NINGUNO") or bool(flecha_practica))
        if flecha_practica:
            pygame.draw.circle(self.pantalla, C.COLOR_ACENTO, centro_icono, 128, 6)
        from gestos import NOMBRES
        self.texto(NOMBRES[estable], self.f_titulo, C.COLOR_TEXTO, (zona.centerx, zona.y + 384), "midtop")
        # Encuadre + estado de cada dedo.
        ind = pygame.Rect(zona.x + 40, zona.bottom - 150, 160, 120)
        estado_txt, color = self.indicador_mano(ind, lectura, estado_camara)
        self.texto(estado_txt, self.f_media, color, (ind.right + 24, ind.y + 6))
        mano = lectura.gesto.value != "SIN_MANO" and estado_camara == "ok"
        x = ind.right + 24
        for nombre, clave in (("Índice", "indice"), ("Medio", "medio"), ("Anular", "anular"),
                              ("Meñique", "menique")):
            ext = lectura.dedos.get(clave) if mano else None
            col = C.COLOR_ACENTO if ext else (C.COLOR_APAGADO if ext is None else C.COLOR_ALERTA)
            pygame.draw.circle(self.pantalla, col, (x + 8, ind.y + 66), 8)
            r = self.texto(nombre, self.f_chica, C.COLOR_TEXTO, (x + 22, ind.y + 56))
            x = r.right + 18
        self.texto("Verde = dedo extendido", self.f_chica, C.COLOR_TEXTO_SUAVE, (ind.right + 24, ind.y + 92))

        panel = self.rect_panel.inflate(0, -2 * C.MARGEN)
        T.tabla(self.pantalla, panel)
        px, ancho = panel.x + 18, panel.width - 36
        pasos = [("1. Cámara lista", estado_camara == "ok"), ("2. Mano detectada", mano),
                 ("3. Apunta con el índice", ya_practico), ("4. Palma 1 s para jugar", False)]
        for i, (txt, hecho) in enumerate(pasos):
            yy = panel.y + 18 + i * 32
            pygame.draw.circle(self.pantalla, C.COLOR_ACENTO if hecho else C.COLOR_APAGADO, (px + 8, yy + 13),
                               8, 0 if hecho else 2)
            self.texto(txt, self.f_normal, C.COLOR_ACENTO if hecho else C.COLOR_TEXTO, (px + 26, yy))
        y = panel.y + 160
        self.texto("Acción", self.f_chica_n, C.COLOR_TEXTO_SUAVE, (px, y))
        if nota:
            self.texto(nota, self.f_chica, C.COLOR_TEXTO_SUAVE, (px, y + 24))
        elif accion and progreso is not None:
            self.texto(f"Sostén para: {accion}", self.f_normal, C.COLOR_TEXTO, (px, y + 22))
            self.barra(pygame.Rect(px, y + 52, ancho, 12), progreso,
                       C.COLOR_ACENTO if progreso >= 1 else C.COLOR_META)
        self._leyenda(px, panel.y + 250, ancho, leyenda)

    # ================================================================= ERROR
    def dibujar_error(self, mensaje):
        self.dibujar_fondo()
        caja = pygame.Rect(0, 0, self.ancho - 120, 330)
        caja.center = (self.ancho // 2, self.alto // 2)
        T.tabla(self.pantalla, caja)
        titulo = "Falta el modelo de MediaPipe" if "modelo" in mensaje else "Problema con la cámara"
        self.texto(titulo, self.f_grande, C.COLOR_META, (caja.centerx, caja.y + 30), "midtop",
                   sombra=C.COLOR_MADERA_OSCURA)
        self.texto(mensaje, self.f_normal, C.COLOR_TEXTO, (caja.centerx, caja.y + 120), "midtop")
        for i, linea in enumerate(["• Revisa que la cámara esté conectada y que ninguna otra app "
                                   "(Zoom, Teams, Cámara) la esté usando.",
                                   "• Si tienes varias cámaras, cambia CAMARA_INDICE en config.py.",
                                   "• Cerrar: botón X de la ventana."]):
            self.texto(linea, self.f_chica, C.COLOR_TEXTO_SUAVE, (caja.centerx, caja.y + 180 + i * 28), "midtop")
