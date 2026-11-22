"""
sonido.py — Música, efectos y voz guía con pygame.mixer.

Todos los sonidos son ORIGINALES: la música y los efectos se generan con código
(generar_sonidos.py). La voz guía (lector tipo TalkBack) usa la voz de Windows en vivo
(voz.py); si no está disponible, usa los audios de assets/voces/ como respaldo.
Así no hay problemas de derechos de autor.

Mientras la voz habla, la música baja de volumen para que se entienda bien.

Si la computadora no tiene salida de audio, o faltan archivos, el juego sigue funcionando
sin sonido (nunca se cierra por esto).
"""
import os
import time

import pygame

import config as C
from voz import VozSistema

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
        self.lector = True                 # lector de voz (TalkBack) encendido/apagado
        self._musica_actual = None
        self._fin_voz = 0.0                # hasta cuándo se estima que la voz sigue hablando
        self._musica_baja = False
        self.tts = VozSistema()            # voz de Windows en vivo (puede tardar 1-2 s en estar lista)
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
        self.voces = self._cargar_carpeta(C.CARPETA_VOCES, normalizar=True)
        if not self.efectos:
            print("[Sonido] No hay efectos. Ejecuta:  python generar_sonidos.py")

    @staticmethod
    def _normalizar(sonido, pico=0.95):
        """Sube el volumen de un audio hasta casi el máximo (las voces de Windows salen bajitas)."""
        try:
            import numpy as np
            datos = pygame.sndarray.array(sonido)
            maximo = int(np.abs(datos).max()) or 1
            factor = pico * 32767 / maximo
            if factor > 1.05:
                return pygame.sndarray.make_sound(np.clip(datos * factor, -32767, 32767).astype(datos.dtype))
        except Exception as e:           # numpy o sndarray no disponibles: se deja igual
            print(f"[Sonido] No se pudo normalizar una voz: {e}")
        return sonido

    @staticmethod
    def _cargar_carpeta(carpeta, excluir=(), normalizar=False):
        sonidos = {}
        if not os.path.isdir(carpeta):
            return sonidos
        for archivo in sorted(os.listdir(carpeta)):
            nombre, ext = os.path.splitext(archivo)
            if ext.lower() not in EXTENSIONES or nombre.startswith(excluir):
                continue
            try:
                sonidos[nombre] = pygame.mixer.Sound(os.path.join(carpeta, archivo))
                if normalizar:
                    sonidos[nombre] = Sonido._normalizar(sonidos[nombre])
            except pygame.error as e:
                print(f"[Sonido] No se pudo cargar {archivo}: {e}")
        return sonidos

    # ------------------------------------------------------------- volúmenes
    def ajustar(self, musica, efectos, voz, lector=True):
        """Volúmenes separados (0-100) para música, efectos y voz, y lector encendido o no."""
        self.vol_musica, self.vol_efectos, self.vol_voz = musica / 100, efectos / 100, voz / 100
        if self.lector and not lector:
            self.callar()
        self.lector = lector
        self.tts.volumen(voz)
        if self.activo:
            pygame.mixer.music.set_volume(self.vol_musica * (0.25 if self._musica_baja else 1))

    def actualizar(self):
        """Se llama cada fotograma: regresa la música a su volumen cuando la voz termina."""
        if self._musica_baja and time.monotonic() > self._fin_voz:
            self._musica_baja = False
            if self.activo:
                pygame.mixer.music.set_volume(self.vol_musica)

    def cerrar(self):
        self.tts.cerrar()

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
    @property
    def lector_disponible(self):
        return self.tts.disponible or bool(self.voces)

    def hablar(self, texto, clave=None):
        """
        Lector de voz (TalkBack): lee `texto` en voz alta con la voz de Windows. Si esa voz no
        está disponible y hay un audio grabado para `clave` en assets/voces/, se usa el audio.
        """
        if not self.lector or self.vol_voz <= 0 or not texto:
            return
        if self.tts.disponible:
            self.tts.decir(texto)
            duracion = 0.5 + 0.07 * len(texto)
        elif self.activo and clave in self.voces:
            sonido = self.voces[clave]
            self.canal_voz.stop()
            self.canal_voz.set_volume(min(1.0, self.vol_voz * 1.2))
            self.canal_voz.play(sonido)
            duracion = sonido.get_length() + 0.2
        else:
            return
        # Baja la música mientras se habla, para que la voz se entienda.
        self._fin_voz = time.monotonic() + duracion
        if self.activo and not self._musica_baja:
            self._musica_baja = True
            pygame.mixer.music.set_volume(self.vol_musica * 0.25)

    def callar(self):
        self.tts.callar()
        if self.activo:
            self.canal_voz.stop()

    def voz(self, clave):
        """Compatibilidad: dice una frase conocida de FRASES. Devuelve el texto (subtítulo)."""
        texto = FRASES.get(clave, clave)
        self.hablar(texto, clave)
        return texto
