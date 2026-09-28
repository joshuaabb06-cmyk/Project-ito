"""
main.py — Project-ito: mueve al personaje por el laberinto SOLO con gestos de la mano.

Ejecutar:   python main.py

Es una MÁQUINA DE ESTADOS: en cada momento el juego está en uno de estos estados, y cada
estado define qué gestos tienen efecto:

    CALIBRACIÓN --(palma 1 s)--> JUGANDO --(llega a la meta)--> ¡GANASTE!
                                   |  ^                             |
                         (palma 1 s)  (palma 1 s)          (puño 2 s: jugar de nuevo)
                                   v  |
                                  PAUSA
    Puño 2 s (jugando / pausa) = reiniciar.   Cuernos 3 s (en cualquier estado) = salir.

El teclado NO se usa para nada. La X de la ventana (mouse) queda solo como respaldo.
"""
import time
from enum import Enum

import pygame

import config as C
from control import DURACIONES, ControlGestos
from gestos import DIRECCIONALES, DetectorGestos, Gesto
from juego import Vista
from laberinto import Laberinto


class Estado(Enum):
    CALIBRACION = "Calibración"
    JUGANDO = "Jugando"
    PAUSA = "Pausa"
    GANASTE = "¡Ganaste!"


# Qué hace cada gesto en cada estado. Si un gesto no aparece, en ese estado no hace nada.
ACCIONES = {
    Estado.CALIBRACION: {**{g: "Probar" for g in DIRECCIONALES},
                         Gesto.PALMA: "Comenzar", Gesto.CUERNOS: "Salir"},
    Estado.JUGANDO: {**{g: "Mover" for g in DIRECCIONALES},
                     Gesto.PALMA: "Pausar", Gesto.PUNO: "Reiniciar", Gesto.CUERNOS: "Salir"},
    Estado.PAUSA: {Gesto.PALMA: "Reanudar", Gesto.PUNO: "Reiniciar", Gesto.CUERNOS: "Salir"},
    Estado.GANASTE: {Gesto.PUNO: "Jugar de nuevo", Gesto.CUERNOS: "Salir"},
}
NOMBRE_CORTO = {Gesto.PALMA: "Palma abierta", Gesto.PUNO: "Puño", Gesto.CUERNOS: "Cuernos"}


def leyenda(estado):
    """Filas (gesto, segundos, acción) para el panel de ayuda del estado actual."""
    acciones = ACCIONES[estado]
    filas = []
    if Gesto.ARRIBA in acciones:
        filas.append(("Índice ↑ ↓ ← →", C.TIEMPO_MOVER, acciones[Gesto.ARRIBA]))
    for gesto in (Gesto.PALMA, Gesto.PUNO, Gesto.CUERNOS):
        if gesto in acciones:
            filas.append((NOMBRE_CORTO[gesto], DURACIONES[gesto], acciones[gesto]))
    return filas


class App:
    def __init__(self):
        self.lab = Laberinto(C.LABERINTO, C.INICIO, C.META, C.PASO)
        self.vista = Vista(self.lab)
        self.detector = DetectorGestos()
        self.detector.iniciar()
        self.control = ControlGestos()
        self.estado = Estado.CALIBRACION
        self.tiempo_jugado = 0.0
        self.gesto_bloqueado = None       # gesto que causó el último cambio de estado
        self.flecha, self.t_flecha = None, 0.0   # flecha de práctica en la calibración
        self.ya_practico = False

    # -------------------------------------------------------------- estados
    def cambiar_estado(self, nuevo):
        self.estado = nuevo
        # El gesto que provocó el cambio (p. ej. la palma que inició el juego) sigue en la mano:
        # se "bloquea" hasta que el usuario cambie de gesto, para que no parezca que va a
        # disparar otra acción en la nueva pantalla.
        self.gesto_bloqueado = self.control.estable

    def reiniciar_partida(self, ahora):
        self.lab.reiniciar()
        self.vista.jugador_reiniciado()
        self.tiempo_jugado = 0.0
        self.vista.avisar("Laberinto reiniciado", ahora)
        self.cambiar_estado(Estado.JUGANDO)

    def manejar(self, gesto, ahora):
        """Ejecuta la acción del gesto confirmado. Devuelve False si hay que salir."""
        if gesto == Gesto.CUERNOS:
            return False
        if self.estado == Estado.CALIBRACION:
            if gesto in DIRECCIONALES:
                self.flecha, self.t_flecha, self.ya_practico = gesto.value, ahora, True
            elif gesto == Gesto.PALMA:
                self.cambiar_estado(Estado.JUGANDO)
        elif self.estado == Estado.JUGANDO:
            if gesto in DIRECCIONALES:
                if self.lab.mover(gesto.value):
                    self.vista.jugador_movido(ahora)
                    if self.lab.gano:
                        self.cambiar_estado(Estado.GANASTE)
                else:
                    self.vista.jugador_choco(ahora)
            elif gesto == Gesto.PALMA:
                self.cambiar_estado(Estado.PAUSA)
            elif gesto == Gesto.PUNO:
                self.reiniciar_partida(ahora)
        elif self.estado == Estado.PAUSA:
            if gesto == Gesto.PALMA:
                self.cambiar_estado(Estado.JUGANDO)
            elif gesto == Gesto.PUNO:
                self.reiniciar_partida(ahora)
        elif self.estado == Estado.GANASTE and gesto == Gesto.PUNO:
            self.reiniciar_partida(ahora)
        return True

    # ------------------------------------------------------------ bucle
    def ejecutar(self):
        reloj = pygame.time.Clock()
        corriendo = True
        while corriendo:
            dt = reloj.tick(C.FPS) / 1000
            ahora = time.monotonic()

            # Eventos de la ventana: SOLO se atiende cerrar con la X (el teclado se ignora).
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    corriendo = False

            # 1) Leer el último gesto y pasarlo por el anti-rebote.
            lectura = self.detector.leer()
            disparado = self.control.actualizar(lectura, ahora)
            if self.control.estable != self.gesto_bloqueado:
                self.gesto_bloqueado = None
            # 2) Ejecutar la acción si el gesto tiene efecto en el estado actual.
            if (disparado and self.detector.estado == "ok" and disparado in ACCIONES[self.estado]
                    and disparado != self.gesto_bloqueado):
                corriendo = self.manejar(disparado, ahora) and corriendo
            if self.estado == Estado.JUGANDO:
                self.tiempo_jugado += dt
            # 3) Dibujar.
            self.dibujar(lectura, ahora)

        self.detector.detener()
        pygame.quit()

    # ------------------------------------------------------------ dibujo
    def info_gesto(self):
        """(acción, progreso, nota) del gesto estable para la barra de 'sostener'."""
        estable = self.control.estable
        if estable == self.gesto_bloqueado and estable in ACCIONES[self.estado]:
            return None, None, "Cambia de gesto para volver a usarlo"
        accion = ACCIONES[self.estado].get(estable)
        if accion is None:
            return None, None, None
        if estable in DIRECCIONALES:
            accion = f"{accion} {estable.value.lower()}"
        return accion, self.control.progreso(), None

    def dibujar(self, lectura, ahora):
        v = self.vista
        if self.detector.estado == "error":
            v.dibujar_error(self.detector.error)
            v.presentar()
            return
        accion, progreso, nota = self.info_gesto()
        datos = dict(lectura=lectura, estable=self.control.estable, progreso=progreso,
                     accion=accion, nota=nota, leyenda=leyenda(self.estado),
                     estado_camara=self.detector.estado)
        v.dibujar_fondo()
        v.dibujar_barra_superior(self.estado.value, self.tiempo_jugado)
        if self.estado == Estado.CALIBRACION:
            flecha = self.flecha if ahora - self.t_flecha < 0.6 else None
            v.dibujar_calibracion(flecha_practica=flecha, ya_practico=self.ya_practico, **datos)
        else:
            v.dibujar_laberinto(ahora)
            v.dibujar_personaje(ahora)
            v.dibujar_aviso(ahora)
            v.dibujar_panel_juego(**datos)
            m, s = divmod(int(self.tiempo_jugado), 60)
            # Las instrucciones salen de la leyenda, así siempre coinciden con config.py.
            ayuda = [f"{g}  {t:g} s: {a.lower()}" for g, t, a in leyenda(self.estado)]
            if self.estado == Estado.PAUSA:
                v.dibujar_mensaje("Pausa", ayuda)
            elif self.estado == Estado.GANASTE:
                v.dibujar_mensaje("¡Ganaste!", [f"{self.lab.movimientos} movimientos en {m:02d}:{s:02d}",
                                                f"Choques contra paredes: {self.lab.choques}", ""]
                                  + ayuda, C.COLOR_META)
        v.presentar()


if __name__ == "__main__":
    App().ejecutar()
