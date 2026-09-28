"""
control.py — Anti-rebote: convierte el gesto "crudo" de cada fotograma en EVENTOS confiables.

Dos capas de filtrado:
  1. Votación: el gesto debe ganar la mayoría en los últimos VENTANA_VOTACION fotogramas.
     Elimina parpadeos de 1-2 cuadros (p. ej. MediaPipe confunde un dedo por un instante).
  2. Sostener: el gesto estable debe mantenerse cierto tiempo (0.5 s para mover, 1 s palma,
     2 s puño, 3 s cuernos) antes de disparar el evento. Evita movimientos "fantasma".

Además, los gestos que no son de movimiento se disparan UNA sola vez: hay que cambiar de gesto
(o bajar la mano) para volver a activarlos. Así la palma no pausa y reanuda en bucle.
"""
import time
from collections import Counter, deque

import config as C
from gestos import DIRECCIONALES, Gesto

# Cuánto tiempo hay que sostener cada gesto. Los que no aparecen aquí no disparan nada.
DURACIONES = {
    Gesto.ARRIBA: C.TIEMPO_MOVER,
    Gesto.ABAJO: C.TIEMPO_MOVER,
    Gesto.IZQUIERDA: C.TIEMPO_MOVER,
    Gesto.DERECHA: C.TIEMPO_MOVER,
    Gesto.PALMA: C.TIEMPO_INICIAR_PAUSAR,
    Gesto.PUNO: C.TIEMPO_REINICIAR,
    Gesto.CUERNOS: C.TIEMPO_SALIR,
}

# Si la última lectura de la cámara es más vieja que esto, se considera que no hay mano
# (protege contra un hilo de cámara trabado que dejaría "pegado" un gesto de movimiento).
LECTURA_VIEJA_S = 0.5


class ControlGestos:
    def __init__(self):
        self._votos = deque(maxlen=C.VENTANA_VOTACION)
        self._ultimo_id = -1
        self.estable = Gesto.SIN_MANO   # gesto que pasó la votación
        self._t_inicio = time.monotonic()
        self._disparos = 0              # cuántas veces se disparó el gesto actual

    def _votar(self, gesto):
        """Capa 1: mayoría de votos en la ventana. Sin mayoría clara -> NINGUNO."""
        self._votos.append(gesto)
        ganador, votos = Counter(self._votos).most_common(1)[0]
        return ganador if votos >= C.VOTOS_MINIMOS else Gesto.NINGUNO

    def actualizar(self, lectura, ahora=None):
        """
        Se llama en cada cuadro del juego. Devuelve el Gesto que se DISPARÓ en este cuadro
        (o None si no se disparó nada).
        """
        ahora = time.monotonic() if ahora is None else ahora

        # Solo se vota cuando llega un fotograma NUEVO de la cámara (la cámara va a ~30 FPS,
        # el juego a 60: no queremos contar dos veces el mismo fotograma).
        if lectura.id != self._ultimo_id:
            self._ultimo_id = lectura.id
            nuevo = self._votar(lectura.gesto)
        else:
            nuevo = self.estable
        if ahora - lectura.t > LECTURA_VIEJA_S:
            nuevo = Gesto.SIN_MANO

        # Si cambió el gesto estable, el cronómetro vuelve a cero.
        if nuevo != self.estable:
            self.estable = nuevo
            self._t_inicio = ahora
            self._disparos = 0

        # Capa 2: ¿ya se sostuvo lo suficiente?
        duracion = DURACIONES.get(self.estable)
        if duracion is None:
            return None
        transcurrido = ahora - self._t_inicio
        if self._disparos == 0 and transcurrido >= duracion:
            self._disparos = 1
            return self.estable
        # Repetición: sostener una dirección sigue moviendo cada TIEMPO_REPETICION segundos.
        if (self.estable in DIRECCIONALES and C.REPETIR_MOVIMIENTO and self._disparos >= 1 and
                transcurrido >= duracion + self._disparos * C.TIEMPO_REPETICION):
            self._disparos += 1
            return self.estable
        return None

    def progreso(self, ahora=None):
        """
        Qué tan cerca está el gesto actual de dispararse (0.0 a 1.0), para la barra de carga.
        Devuelve None si el gesto actual no hace nada.
        """
        ahora = time.monotonic() if ahora is None else ahora
        duracion = DURACIONES.get(self.estable)
        if duracion is None:
            return None
        transcurrido = ahora - self._t_inicio
        if self._disparos == 0:
            return min(1.0, transcurrido / duracion)
        if self.estable in DIRECCIONALES and C.REPETIR_MOVIMIENTO:
            siguiente = duracion + self._disparos * C.TIEMPO_REPETICION
            return max(0.0, min(1.0, 1 - (siguiente - transcurrido) / C.TIEMPO_REPETICION))
        return 1.0   # ya se disparó: queda "lleno" hasta que cambies de gesto

    def ya_disparado(self):
        return self._disparos > 0
