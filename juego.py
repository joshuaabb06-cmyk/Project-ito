"""
juego.py — Todo lo que se DIBUJA con Pygame: laberinto, personaje, barra superior,
panel lateral (cámara + gesto) y pantallas (calibración, pausa, ¡Ganaste!, error).

No contiene reglas del juego ni detección de gestos: solo recibe datos y los pinta.
"""
import math
import os

import pygame

import config as C


def _fuente(tam, negrita=False):
    """Segoe UI en Windows (soporta acentos y flechas); si no existe, la fuente por defecto."""
    return pygame.font.SysFont("segoeui,arial", tam, bold=negrita)


# ============================================================================
# PERSONAJE
# ============================================================================
class Personaje:
    """Carga assets/personaje.png o, si no existe, dibuja uno de respaldo con formas."""

    def __init__(self, tam):
        self.tam = tam
        self.imagen = self._cargar_imagen(tam)
        self.mirando_izquierda = False
        # Animación: el personaje se desliza de `origen` a `objetivo` (en píxeles).
        self.origen = self.objetivo = (0.0, 0.0)
        self.t_inicio = 0.0

    @staticmethod
    def _cargar_imagen(tam):
        if not os.path.exists(C.RUTA_PERSONAJE):
            print(f"[Personaje] No se encontró {C.RUTA_PERSONAJE}: se usa el dibujo de respaldo.")
            return None
        try:
            img = pygame.image.load(C.RUTA_PERSONAJE).convert_alpha()
        except pygame.error as e:
            print(f"[Personaje] No se pudo cargar la imagen ({e}): se usa el dibujo de respaldo.")
            return None
        # Escala manteniendo la proporción para que quepa en la casilla.
        escala = tam / max(img.get_width(), img.get_height())
        return pygame.transform.smoothscale(
            img, (int(img.get_width() * escala), int(img.get_height() * escala)))

    def colocar(self, centro):
        """Pone al personaje en `centro` sin animación (al iniciar o reiniciar)."""
        self.origen = self.objetivo = centro
        self.t_inicio = 0.0

    def ir_a(self, centro, ahora):
        """Inicia la animación hacia `centro` y voltea el sprite según la dirección."""
        if centro[0] < self.objetivo[0]:
            self.mirando_izquierda = True
        elif centro[0] > self.objetivo[0]:
            self.mirando_izquierda = False
        self.origen = self.posicion(ahora)
        self.objetivo = centro
        self.t_inicio = ahora

    def posicion(self, ahora):
        """Posición actual interpolada (movimiento suave con desaceleración)."""
        t = min(1.0, (ahora - self.t_inicio) / C.DURACION_ANIMACION) if C.DURACION_ANIMACION else 1
        t = 1 - (1 - t) ** 3
        return (self.origen[0] + (self.objetivo[0] - self.origen[0]) * t,
                self.origen[1] + (self.objetivo[1] - self.origen[1]) * t)

    def dibujar(self, sup, ahora):
        cx, cy = self.posicion(ahora)
        if self.imagen:
            img = pygame.transform.flip(self.imagen, self.mirando_izquierda, False)
            sup.blit(img, img.get_rect(center=(int(cx), int(cy))))
        else:
            self._dibujar_respaldo(sup, cx, cy)

    def _dibujar_respaldo(self, sup, cx, cy):
        """Dinosaurio sencillo hecho con formas de Pygame."""
        s = self.tam / 2
        d = -1 if self.mirando_izquierda else 1       # hacia dónde mira
        verde, oscuro = (95, 190, 80), (50, 120, 45)
        # Cola (triángulo hacia atrás)
        pygame.draw.polygon(sup, oscuro, [(cx - d * s * 0.3, cy + s * 0.1),
                                          (cx - d * s * 0.95, cy + s * 0.55),
                                          (cx - d * s * 0.3, cy + s * 0.55)])
        # Cuerpo y cabeza
        pygame.draw.ellipse(sup, verde, (cx - s * 0.55, cy - s * 0.2, s * 1.1, s * 0.95))
        pygame.draw.circle(sup, verde, (int(cx + d * s * 0.35), int(cy - s * 0.4)), int(s * 0.42))
        # Púas de la espalda
        for i in range(3):
            bx = cx - d * s * (0.3 - i * 0.25)
            pygame.draw.polygon(sup, oscuro, [(bx - s * 0.1, cy - s * 0.15 - i * s * 0.12),
                                              (bx, cy - s * 0.4 - i * s * 0.12),
                                              (bx + s * 0.1, cy - s * 0.15 - i * s * 0.12)])
        # Ojo
        ox, oy = int(cx + d * s * 0.5), int(cy - s * 0.5)
        pygame.draw.circle(sup, (255, 255, 255), (ox, oy), int(s * 0.14))
        pygame.draw.circle(sup, (20, 20, 20), (ox + d * 2, oy), int(s * 0.07))
        # Patas
        for dx in (-0.25, 0.2):
            pygame.draw.rect(sup, oscuro, (cx + dx * s - s * 0.1, cy + s * 0.6, s * 0.2, s * 0.3),
                             border_radius=3)


# ============================================================================
# VISTA PRINCIPAL
# ============================================================================
class Vista:
    """Ventana del juego. Calcula el acomodo en pantalla y dibuja cada elemento."""

    def __init__(self, laberinto, titulo="Project-ito"):
        pygame.init()
        pygame.display.set_caption(titulo)
        self.lab = laberinto

        # --- Tamaño de cada fila/columna de la matriz --------------------------
        # Con PASO = 2, las posiciones pares son paredes delgadas y las impares casillas
        # (como en la imagen original). Con PASO = 1 todas miden lo mismo (bloques).
        def medida(i):
            if C.PASO == 2:
                return C.TAMANO_CASILLA if i % 2 == 1 else C.GROSOR_PARED
            return C.TAMANO_CASILLA

        self.anchos = [medida(c) for c in range(laberinto.columnas)]
        self.altos = [medida(f) for f in range(laberinto.filas)]
        self.x0 = [sum(self.anchos[:c]) for c in range(laberinto.columnas)]  # borde izq de cada col
        self.y0 = [sum(self.altos[:f]) for f in range(laberinto.filas)]      # borde sup de cada fila
        ancho_lab, alto_lab = sum(self.anchos), sum(self.altos)

        # --- Acomodo general -------------------------------------------------
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

        self.f_titulo = _fuente(30, True)
        self.f_grande = _fuente(56, True)
        self.f_media = _fuente(24, True)
        self.f_normal = _fuente(20)
        self.f_chica = _fuente(16)

        self.personaje = Personaje(int(C.TAMANO_CASILLA * 0.85))
        self.personaje.colocar(self.centro(laberinto.jugador))
        self.t_choque = -10.0          # momento del último choque (para el destello rojo)

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

    def jugador_choco(self, ahora):
        self.t_choque = ahora

    def avisar(self, texto, ahora):
        """Mensaje breve que aparece arriba del laberinto (p. ej. 'Laberinto reiniciado')."""
        self._aviso = (texto, ahora)

    def dibujar_aviso(self, ahora):
        texto, t = getattr(self, "_aviso", ("", -10.0))
        if ahora - t < 1.5:
            r = self.texto(texto, self.f_media, C.COLOR_FONDO,
                           (self.rect_lab.centerx, self.rect_lab.y + 30), "center")
            pygame.draw.rect(self.pantalla, C.COLOR_META, r.inflate(24, 10), border_radius=8)
            self.texto(texto, self.f_media, C.COLOR_FONDO, r.center, "center")

    def jugador_reiniciado(self):
        self.personaje.colocar(self.centro(self.lab.jugador))
        self.personaje.mirando_izquierda = False

    # ------------------------------------------------------------- elementos
    def texto(self, txt, fuente, color, pos, ancla="topleft"):
        img = fuente.render(txt, True, color)
        rect = img.get_rect(**{ancla: pos})
        self.pantalla.blit(img, rect)
        return rect

    def dibujar_fondo(self):
        self.pantalla.fill(C.COLOR_FONDO)

    def dibujar_barra_superior(self, estado, segundos):
        pygame.draw.rect(self.pantalla, C.COLOR_PANEL, (0, 0, self.pantalla.get_width(),
                                                        C.ALTO_BARRA_SUPERIOR))
        self.texto("Project-ito", self.f_titulo, C.COLOR_TEXTO, (C.MARGEN, C.ALTO_BARRA_SUPERIOR // 2),
                   "midleft")
        m, s = divmod(int(segundos), 60)
        info = f"{estado}   ·   Movimientos: {self.lab.movimientos}   ·   Tiempo: {m:02d}:{s:02d}"
        self.texto(info, self.f_normal, C.COLOR_TEXTO_SUAVE,
                   (self.pantalla.get_width() - C.MARGEN, C.ALTO_BARRA_SUPERIOR // 2), "midright")

    def dibujar_laberinto(self, ahora):
        pygame.draw.rect(self.pantalla, C.COLOR_CAMINO, self.rect_lab)
        for f in range(self.lab.filas):
            for c in range(self.lab.columnas):
                if self.lab.matriz[f][c] == 1:
                    pygame.draw.rect(self.pantalla, C.COLOR_PARED, self.rect_celda(f, c))
        self._dibujar_aberturas()
        self._dibujar_meta(ahora)
        # Destello rojo en el borde cuando el personaje choca contra una pared.
        if ahora - self.t_choque < 0.3:
            pygame.draw.rect(self.pantalla, C.COLOR_ALERTA, self.rect_lab.inflate(12, 12), 6,
                             border_radius=4)

    def _dibujar_aberturas(self):
        """Etiqueta ENTRADA / SALIDA en los huecos del borde del laberinto."""
        for f in range(self.lab.filas):
            for c in range(self.lab.columnas):
                borde = f in (0, self.lab.filas - 1) or c in (0, self.lab.columnas - 1)
                if not borde or self.lab.matriz[f][c] != 0:
                    continue
                r = self.rect_celda(f, c)
                dist = lambda p: abs(p[0] - f) + abs(p[1] - c)
                es_salida = dist(self.lab.meta) < dist(self.lab.inicio)
                txt, color = ("SALIDA", C.COLOR_META) if es_salida else ("ENTRADA", C.COLOR_ACENTO)
                if c == 0:
                    self.texto(txt, self.f_chica, color, (r.left - 6, r.centery), "midright")
                elif c == self.lab.columnas - 1:
                    self.texto(txt, self.f_chica, color, (r.right + 6, r.centery), "midleft")
                elif f == 0:
                    self.texto(txt, self.f_chica, color, (r.centerx, r.top - 2), "midbottom")
                else:
                    self.texto(txt, self.f_chica, color, (r.centerx, r.bottom + 2), "midtop")

    def _dibujar_meta(self, ahora):
        """Estrella dorada que late en la casilla meta."""
        cx, cy = self.centro(self.lab.meta)
        radio = C.TAMANO_CASILLA * (0.30 + 0.04 * math.sin(ahora * 5))
        puntos = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = radio if i % 2 == 0 else radio * 0.45
            puntos.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        pygame.draw.polygon(self.pantalla, C.COLOR_META, puntos)
        pygame.draw.polygon(self.pantalla, (180, 130, 20), puntos, 2)

    def dibujar_personaje(self, ahora):
        self.personaje.dibujar(self.pantalla, ahora)

    def dibujar_mensaje(self, titulo, lineas=(), color=None):
        """Recuadro semitransparente sobre el laberinto (pausa, ¡Ganaste!, etc.)."""
        velo = pygame.Surface(self.rect_lab.size, pygame.SRCALPHA)
        velo.fill((10, 14, 28, 190))
        self.pantalla.blit(velo, self.rect_lab)
        cy = self.rect_lab.centery - 30 * len(lineas)
        self.texto(titulo, self.f_grande, color or C.COLOR_TEXTO, (self.rect_lab.centerx, cy), "center")
        for i, linea in enumerate(lineas):
            self.texto(linea, self.f_normal, C.COLOR_TEXTO, (self.rect_lab.centerx, cy + 60 + i * 32),
                       "center")

    def dibujar_panel_demo(self, lineas):
        """Panel lateral de la etapa 1 (sin cámara)."""
        pygame.draw.rect(self.pantalla, C.COLOR_PANEL, self.rect_panel.inflate(0, -2 * C.MARGEN),
                         border_radius=12)
        x, y = self.rect_panel.x + 16, self.rect_panel.y + C.MARGEN + 16
        self.texto("DEMO AUTOMÁTICA", self.f_media, C.COLOR_ACENTO, (x, y))
        for i, linea in enumerate(lineas):
            self.texto(linea, self.f_normal, C.COLOR_TEXTO, (x, y + 50 + i * 30))

    # ================================================================ CÁMARA
    def superficie_camara(self, lectura):
        """Convierte el fotograma de OpenCV (BGR, numpy) en una imagen de Pygame (RGB)."""
        if lectura.frame is None:
            return None
        if getattr(self, "_cam_id", None) != lectura.id:     # solo convierte fotogramas nuevos
            rgb = lectura.frame[:, :, ::-1].copy()            # BGR -> RGB
            alto, ancho = rgb.shape[:2]
            self._cam_sup = pygame.image.frombuffer(rgb.tobytes(), (ancho, alto), "RGB")
            self._cam_id = lectura.id
        return self._cam_sup

    def dibujar_camara(self, lectura, rect, estado_camara, error=""):
        """Dibuja la cámara (con la mano ya marcada por gestos.py) escalada dentro de `rect`."""
        pygame.draw.rect(self.pantalla, (0, 0, 0), rect, border_radius=8)
        sup = self.superficie_camara(lectura) if estado_camara == "ok" else None
        if sup is None:
            msg = "Iniciando cámara..." if estado_camara != "error" else "Sin cámara"
            self.texto(msg, self.f_normal, C.COLOR_TEXTO_SUAVE, rect.center, "center")
            return
        escala = min(rect.width / sup.get_width(), rect.height / sup.get_height())
        img = pygame.transform.smoothscale(sup, (int(sup.get_width() * escala),
                                                 int(sup.get_height() * escala)))
        self.pantalla.blit(img, img.get_rect(center=rect.center))

    def barra(self, rect, progreso, color):
        pygame.draw.rect(self.pantalla, (60, 68, 95), rect, border_radius=rect.height // 2)
        if progreso:
            lleno = rect.copy()
            lleno.width = max(rect.height, int(rect.width * progreso))
            pygame.draw.rect(self.pantalla, color, lleno, border_radius=rect.height // 2)

    def _bloque_gesto(self, x, y, ancho, estable, progreso, accion, nota):
        """Nombre del gesto actual + barra de 'sostener' con la acción que hará."""
        from gestos import NOMBRES   # import local: juego.py no depende de la cámara para la demo
        self.texto("Gesto detectado", self.f_chica, C.COLOR_TEXTO_SUAVE, (x, y))
        color = C.COLOR_ACENTO if accion else C.COLOR_TEXTO
        self.texto(NOMBRES[estable], self.f_media, color, (x, y + 20))
        if nota:
            self.texto(nota, self.f_chica, C.COLOR_TEXTO_SUAVE, (x, y + 56))
        elif accion and progreso is not None:
            lleno = progreso >= 1.0
            etiqueta = f"{accion}: ¡listo!" if lleno else f"Sostén para: {accion}"
            self.texto(etiqueta, self.f_chica, C.COLOR_META if lleno else C.COLOR_TEXTO, (x, y + 56))
            self.barra(pygame.Rect(x, y + 80, ancho, 14), progreso,
                       C.COLOR_META if lleno else C.COLOR_ACENTO)
        elif estable.value not in ("SIN_MANO", "NINGUNO"):
            self.texto("(sin efecto en esta pantalla)", self.f_chica, C.COLOR_TEXTO_SUAVE, (x, y + 56))

    def _leyenda(self, x, y, acciones):
        """Lista de gestos disponibles en la pantalla actual (cambia según el estado)."""
        self.texto("Gestos disponibles", self.f_chica, C.COLOR_TEXTO_SUAVE, (x, y))
        for i, (gesto, tiempo, accion) in enumerate(acciones):
            yy = y + 24 + i * 26
            self.texto(gesto, self.f_chica, C.COLOR_TEXTO, (x, yy))
            self.texto(f"{tiempo:g} s  →  {accion}", self.f_chica, C.COLOR_ACENTO,
                       (x + 125, yy))

    def dibujar_panel_juego(self, lectura, estable, progreso, accion, nota, leyenda, estado_camara):
        """Panel derecho durante el juego: cámara pequeña + gesto + barra + leyenda."""
        panel = self.rect_panel.inflate(0, -2 * C.MARGEN)
        pygame.draw.rect(self.pantalla, C.COLOR_PANEL, panel, border_radius=12)
        x, ancho = panel.x + 14, panel.width - 28
        rect_cam = pygame.Rect(x, panel.y + 14, ancho, int(ancho * 3 / 4))
        self.dibujar_camara(lectura, rect_cam, estado_camara)
        y = rect_cam.bottom + 14
        self._bloque_gesto(x, y, ancho, estable, progreso, accion, nota)
        self._leyenda(x, y + 116, leyenda)
        self.texto(f"Cámara: {lectura.fps:.0f} FPS", self.f_chica, C.COLOR_TEXTO_SUAVE,
                   (x, panel.bottom - 26))

    # ============================================================ CALIBRACIÓN
    def dibujar_calibracion(self, lectura, estable, progreso, accion, nota, leyenda, estado_camara,
                            flecha_practica, ya_practico):
        """
        Pantalla inicial: cámara grande para verificar que la mano se detecta bien,
        qué dedos se ven extendidos y qué gesto se reconoce. Se sale con la palma.
        """
        zona = pygame.Rect(C.MARGEN, C.ALTO_BARRA_SUPERIOR + C.MARGEN,
                           self.rect_panel.x - 2 * C.MARGEN, self.rect_lab.height)
        self.texto("Calibración", self.f_titulo, C.COLOR_TEXTO, (zona.x, zona.y))
        self.texto("Coloca tu mano frente a la cámara, a unos 40-60 cm.", self.f_normal,
                   C.COLOR_TEXTO_SUAVE, (zona.x, zona.y + 42))
        rect_cam = pygame.Rect(zona.x, zona.y + 80, zona.width, int(zona.width * 3 / 4))
        if rect_cam.bottom > zona.bottom - 60:
            rect_cam.height = zona.bottom - 60 - rect_cam.y
        self.dibujar_camara(lectura, rect_cam, estado_camara)

        # Flecha grande al practicar un movimiento (se ilumina al confirmarse el gesto).
        if flecha_practica:
            self._flecha(rect_cam.center, flecha_practica, 70, C.COLOR_META)

        # Estado de cada dedo debajo de la cámara.
        y = rect_cam.bottom + 16
        mano = lectura.gesto.value != "SIN_MANO" and estado_camara == "ok"
        self.texto("Mano detectada" if mano else "Mano NO detectada", self.f_media,
                   C.COLOR_ACENTO if mano else C.COLOR_ALERTA, (zona.x, y))
        x = zona.x + 240
        for nombre, clave in (("Índice", "indice"), ("Medio", "medio"), ("Anular", "anular"),
                              ("Meñique", "menique")):
            ext = lectura.dedos.get(clave) if mano else None
            color = C.COLOR_ACENTO if ext else ((90, 98, 125) if ext is None else C.COLOR_ALERTA)
            pygame.draw.circle(self.pantalla, color, (x + 8, y + 17), 8)
            r = self.texto(nombre, self.f_chica, C.COLOR_TEXTO, (x + 22, y + 6))
            x = r.right + 18

        # Panel derecho: instrucciones + gesto + barra + leyenda.
        panel = self.rect_panel.inflate(0, -2 * C.MARGEN)
        pygame.draw.rect(self.pantalla, C.COLOR_PANEL, panel, border_radius=12)
        px, ancho = panel.x + 14, panel.width - 28
        pasos = [("1. Cámara lista", estado_camara == "ok"),
                 ("2. Mano detectada", mano),
                 ("3. Apunta con el índice (práctica)", ya_practico),
                 ("4. Palma abierta 1 s para jugar", False)]
        for i, (txt, hecho) in enumerate(pasos):
            yy = panel.y + 16 + i * 30
            # Indicador: círculo verde relleno = paso cumplido; contorno gris = pendiente.
            pygame.draw.circle(self.pantalla, C.COLOR_ACENTO if hecho else (90, 98, 125),
                               (px + 7, yy + 15), 7, 0 if hecho else 2)
            self.texto(txt, self.f_normal, C.COLOR_ACENTO if hecho else C.COLOR_TEXTO, (px + 22, yy))
        self._bloque_gesto(px, panel.y + 150, ancho, estable, progreso, accion, nota)
        self._leyenda(px, panel.y + 270, leyenda)
        self.texto(f"Cámara: {lectura.fps:.0f} FPS", self.f_chica, C.COLOR_TEXTO_SUAVE,
                   (px, panel.bottom - 26))

    def _flecha(self, centro, direccion, tam, color):
        """Flecha gruesa apuntando en `direccion` ("ARRIBA", "ABAJO", ...)."""
        cx, cy = centro
        base = [(0, -1), (0.6, -0.1), (0.25, -0.1), (0.25, 0.8), (-0.25, 0.8), (-0.25, -0.1),
                (-0.6, -0.1)]                              # flecha hacia arriba (coordenadas unitarias)
        giro = {"ARRIBA": 0, "DERECHA": 90, "ABAJO": 180, "IZQUIERDA": 270}[direccion]
        a = math.radians(giro)
        puntos = [(cx + tam * (x * math.cos(a) - y * math.sin(a)),
                   cy + tam * (x * math.sin(a) + y * math.cos(a))) for x, y in base]
        pygame.draw.polygon(self.pantalla, color, puntos)
        pygame.draw.polygon(self.pantalla, (0, 0, 0), puntos, 3)

    # ================================================================= ERROR
    def dibujar_error(self, mensaje):
        """Pantalla completa de error (cámara o modelo). El detector reintenta solo."""
        self.pantalla.fill(C.COLOR_FONDO)
        cx, cy = self.pantalla.get_width() // 2, self.pantalla.get_height() // 2
        titulo = "Falta el modelo de MediaPipe" if "modelo" in mensaje else "Problema con la cámara"
        self.texto(titulo, self.f_grande, C.COLOR_ALERTA, (cx, cy - 90), "center")
        self.texto(mensaje, self.f_normal, C.COLOR_TEXTO, (cx, cy), "center")
        for i, linea in enumerate(["• Revisa que la cámara esté conectada y que ninguna otra app "
                                   "(Zoom, Teams, Cámara) la esté usando.",
                                   "• Si tienes varias cámaras, cambia CAMARA_INDICE en config.py.",
                                   "• Cerrar: botón X de la ventana."]):
            self.texto(linea, self.f_chica, C.COLOR_TEXTO_SUAVE, (cx, cy + 50 + i * 26), "center")

    @staticmethod
    def presentar():
        pygame.display.flip()
