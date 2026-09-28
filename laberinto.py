"""
laberinto.py — Lógica pura del laberinto (no dibuja nada ni usa la cámara).

Separar la lógica del dibujo permite probarla sola y reutilizarla: el mismo objeto
lo mueve la demo automática (etapa 1) y los gestos de la mano (juego final).
"""
from collections import deque

# Desplazamiento (fila, columna) de cada dirección.
# Las filas crecen hacia ABAJO, por eso "ARRIBA" resta una fila.
DIRECCIONES = {
    "ARRIBA": (-1, 0),
    "ABAJO": (1, 0),
    "IZQUIERDA": (0, -1),
    "DERECHA": (0, 1),
}


class Laberinto:
    """Laberinto basado en una matriz: 0 = camino, 1 = pared."""

    def __init__(self, matriz, inicio, meta, paso=1):
        self.matriz = matriz
        self.filas = len(matriz)
        self.columnas = len(matriz[0])
        self.inicio = tuple(inicio)
        self.meta = tuple(meta)
        self.paso = paso
        self._validar()
        self.reiniciar()

    def _validar(self):
        """Revisa que la configuración tenga sentido antes de jugar (errores claros)."""
        if any(len(fila) != self.columnas for fila in self.matriz):
            raise ValueError("Todas las filas del laberinto deben tener el mismo largo.")
        if not self.es_camino(*self.inicio):
            raise ValueError(f"El INICIO {self.inicio} está sobre una pared o fuera del laberinto.")
        if not self.es_camino(*self.meta):
            raise ValueError(f"La META {self.meta} está sobre una pared o fuera del laberinto.")
        if self.resolver() is None:
            raise ValueError("El laberinto no tiene solución desde INICIO hasta META.")

    # ------------------------------------------------------------------ estado
    def reiniciar(self):
        """Regresa al personaje al inicio y limpia los contadores."""
        self.jugador = self.inicio
        self.movimientos = 0
        self.choques = 0

    @property
    def gano(self):
        return self.jugador == self.meta

    # --------------------------------------------------------------- colisiones
    def es_camino(self, fila, col):
        """True si (fila, col) está dentro de la matriz y es 0. Fuera de la matriz = pared."""
        return 0 <= fila < self.filas and 0 <= col < self.columnas and self.matriz[fila][col] == 0

    def destino(self, posicion, direccion):
        """
        Calcula a dónde llegaría el personaje desde `posicion` en `direccion`.
        Revisa CADA posición intermedia (no solo la final): así no puede "saltar"
        una pared delgada. Devuelve la nueva posición o None si choca.
        """
        df, dc = DIRECCIONES[direccion]
        fila, col = posicion
        for _ in range(self.paso):
            fila, col = fila + df, col + dc
            if not self.es_camino(fila, col):
                return None
        return (fila, col)

    def mover(self, direccion):
        """Intenta mover al jugador. Devuelve True si se movió, False si chocó con pared."""
        if self.gano:
            return False
        nueva = self.destino(self.jugador, direccion)
        if nueva is None:
            self.choques += 1
            return False
        self.jugador = nueva
        self.movimientos += 1
        return True

    # ------------------------------------------------------------------- BFS
    def resolver(self, desde=None):
        """
        Búsqueda en anchura (BFS): encuentra la ruta MÁS CORTA de `desde` a la meta.
        Devuelve la lista de direcciones (p. ej. ["DERECHA", "ARRIBA", ...]) o None.
        Se usa para validar el laberinto y para la demo automática.
        """
        origen = tuple(desde or self.inicio)
        cola = deque([origen])
        previo = {origen: None}          # posición -> (posición anterior, dirección usada)
        while cola:
            actual = cola.popleft()
            if actual == self.meta:
                break
            for nombre in DIRECCIONES:
                siguiente = self.destino(actual, nombre)
                if siguiente is not None and siguiente not in previo:
                    previo[siguiente] = (actual, nombre)
                    cola.append(siguiente)
        if self.meta not in previo:
            return None
        # Reconstruye la ruta caminando hacia atrás desde la meta.
        ruta, nodo = [], self.meta
        while previo[nodo] is not None:
            nodo, direccion = previo[nodo]
            ruta.append(direccion)
        return ruta[::-1]
