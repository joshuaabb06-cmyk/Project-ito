"""
sonido.py — Música, efectos y voz guía con pygame.mixer.

Todos los sonidos son ORIGINALES: la música y los efectos se generan con código
(generar_sonidos.py) y la voz con la voz de Windows (generar_voces.py) o grabada por el equipo.
Así no hay problemas de derechos de autor.

Si la computadora no tiene salida de audio, o faltan archivos, el juego sigue funcionando
sin sonido (nunca se cierra por esto).
"""
import os

import pygame

import config as C

EXTENSIONES = (".wav", ".ogg", ".mp3")

# Debe llamarse ANTES de pygame.init() (que hace juego.Vista) para usar un búfer chico (poco retraso).
pygame.mixer.pre_init(44100, -16, 2, 512)

# Texto de cada frase de la voz guía. También se usa como subtítulo en pantalla.
FRASES = {
    "jugar": "Jugar", "dificultad": "Dificultad", "personaje": "Personaje",
    "configuracion": "Configuración", "salir": "Salir", "regresar": "Regresar",
    "explorador": "Explorador", "sheriff": "Sheriff", "forajido": "Forajido",
    "noche": "Noche sin luna",
    "musica": "Música", "efectos": "Efectos", "voz": "Voz guía",
    "velocidad": "Velocidad de gestos", "sonar": "Sonar a la salida", "sombrero": "Sombrero",
    "contraste": "Alto contraste",
    "prueba": "Prueba tus gestos. Abre la palma para comenzar",
    "comenzar": "¡A jugar!", "pausa": "Pausa", "continuar": "Continuar",
    "reiniciar": "Reiniciar", "menu": "Menú principal",
    "vidas_2": "Te quedan dos vidas", "vidas_1": "Te queda una vida",
    "perdiste": "Perdiste", "ganaste": "¡Ganaste!", "record": "¡Nuevo récord!",
    "sin_mano": "No veo tu mano", "elige_personaje": "Elige tu personaje",
}


class Sonido:
    def __init__(self):
        self.activo = False
        self.efectos, self.voces = {}, {}
        self.vol_musica = self.vol_efectos = self.vol_voz = 1.0
        self._musica_actual = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)                 # el canal 0 queda solo para la voz:
            self.canal_voz = pygame.mixer.Channel(0)     # una frase nueva corta la anterior
            self.activo = True
        except pygame.error as e:
            print(f"[Sonido] Sin audio ({e}). El juego sigue sin sonido.")
            return
        self.efectos = self._cargar_carpeta(C.CARPETA_SONIDOS, excluir=("musica_",))
        self.voces = self._cargar_carpeta(C.CARPETA_VOCES)
        if not self.efectos:
            print("[Sonido] No hay efectos. Ejecuta:  python generar_sonidos.py")
        if not self.voces:
            print("[Sonido] No hay voces. Ejecuta:  python generar_voces.py  (o graben las suyas)")

    @staticmethod
    def _cargar_carpeta(carpeta, excluir=()):
        sonidos = {}
        if not os.path.isdir(carpeta):
            return sonidos
        for archivo in sorted(os.listdir(carpeta)):
            nombre, ext = os.path.splitext(archivo)
            if ext.lower() not in EXTENSIONES or nombre.startswith(excluir):
                continue
            try:
                sonidos[nombre] = pygame.mixer.Sound(os.path.join(carpeta, archivo))
            except pygame.error as e:
                print(f"[Sonido] No se pudo cargar {archivo}: {e}")
        return sonidos

    # ------------------------------------------------------------- volúmenes
    def ajustar(self, musica, efectos, voz):
        """Volúmenes separados (0-100) para música, efectos y voz."""
        self.vol_musica, self.vol_efectos, self.vol_voz = musica / 100, efectos / 100, voz / 100
        if self.activo:
            pygame.mixer.music.set_volume(self.vol_musica)

    # ----------------------------------------------------------------- música
    def musica(self, nombre):
        """Pone en bucle assets/sonidos/musica_<nombre>.wav (None = silencio)."""
        if not self.activo or nombre == self._musica_actual:
            return
        self._musica_actual = nombre
        if nombre is None:
            pygame.mixer.music.fadeout(600)
            return
        for ext in EXTENSIONES:
            ruta = os.path.join(C.CARPETA_SONIDOS, f"musica_{nombre}{ext}")
            if os.path.exists(ruta):
                try:
                    pygame.mixer.music.load(ruta)
                    pygame.mixer.music.set_volume(self.vol_musica)
                    pygame.mixer.music.play(-1, fade_ms=800)
                except pygame.error as e:
                    print(f"[Sonido] No se pudo reproducir {ruta}: {e}")
                return

    # ---------------------------------------------------------------- efectos
    def efecto(self, nombre, paneo=0.0, volumen=1.0):
        """
        Reproduce un efecto. `paneo` va de -1 (solo bocina izquierda) a 1 (solo derecha):
        así un choque contra la pared izquierda se oye a la izquierda.
        """
        sonido = self.efectos.get(nombre)
        if not self.activo or sonido is None or self.vol_efectos <= 0:
            return
        canal = sonido.play()
        if canal:
            v = self.vol_efectos * volumen
            izq = v * min(1.0, 1 - paneo)
            der = v * min(1.0, 1 + paneo)
            canal.set_volume(izq, der)

    # -------------------------------------------------------------------- voz
    def voz(self, clave):
        """Dice una frase (si existe el audio). Devuelve el texto para mostrarlo como subtítulo."""
        texto = FRASES.get(clave, clave)
        sonido = self.voces.get(clave)
        if self.activo and sonido is not None and self.vol_voz > 0:
            self.canal_voz.stop()
            self.canal_voz.set_volume(self.vol_voz)
            self.canal_voz.play(sonido)
        return texto
