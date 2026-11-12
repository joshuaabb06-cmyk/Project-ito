"""
gestos.py — Cámara + MediaPipe HandLandmarker + clasificación de gestos.

Funciona en un HILO aparte: mientras Pygame dibuja a 60 FPS, este hilo lee la cámara,
detecta la mano y guarda la "última lectura". Así el juego nunca se congela esperando
a la cámara, y si la cámara falla se reintenta sola sin cerrar el programa.

Puntos (landmarks) de MediaPipe que usamos:
    0 = muñeca
    5, 6, 8   = índice  (nudillo, articulación media, punta)
    9, 10, 12 = medio
    13, 14, 16 = anular
    17, 18, 20 = meñique
"""
import math
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

import config as C


class Gesto(str, Enum):
    SIN_MANO = "SIN_MANO"      # no hay mano frente a la cámara
    NINGUNO = "NINGUNO"        # hay mano, pero no es un gesto reconocido
    ARRIBA = "ARRIBA"
    ABAJO = "ABAJO"
    IZQUIERDA = "IZQUIERDA"
    DERECHA = "DERECHA"
    PALMA = "PALMA"            # 4 dedos extendidos: iniciar / pausar / reanudar
    PUNO = "PUNO"              # ningún dedo extendido: reiniciar
    CUERNOS = "CUERNOS"        # índice + meñique: salir


DIRECCIONALES = {Gesto.ARRIBA, Gesto.ABAJO, Gesto.IZQUIERDA, Gesto.DERECHA}

# Texto que se muestra en pantalla para cada gesto.
NOMBRES = {
    Gesto.SIN_MANO: "Sin mano",
    Gesto.NINGUNO: "Gesto no reconocido",
    Gesto.ARRIBA: "Índice arriba",
    Gesto.ABAJO: "Índice abajo",
    Gesto.IZQUIERDA: "Índice izquierda",
    Gesto.DERECHA: "Índice derecha",
    Gesto.PALMA: "Palma abierta",
    Gesto.PUNO: "Puño",
    Gesto.CUERNOS: "Cuernos",
}

# Dedos que se evalúan (el pulgar se IGNORA a propósito: es el que MediaPipe detecta peor
# y la gente lo mueve sin querer al apuntar). Cada uno: (punta, articulación media).
DEDOS = {"indice": (8, 6), "medio": (12, 10), "anular": (16, 14), "menique": (20, 18)}

# Conexiones entre puntos para dibujar el "esqueleto" de la mano.
CONEXIONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10),
              (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17),
              (17, 18), (18, 19), (19, 20)]


# ============================================================================
# CLASIFICACIÓN (funciones puras: fáciles de probar sin cámara)
# ============================================================================
def dedos_extendidos(mundo):
    """
    Decide qué dedos están extendidos usando los landmarks 3D "world" (en metros,
    centrados en la mano). Compara:  distancia(muñeca, punta) / distancia(muñeca, art. media).
    Dedo recto -> la punta queda MÁS lejos de la muñeca (≈1.35). Doblado -> más cerca (<1.0).
    Al usar distancias 3D, funciona sin importar si la mano apunta arriba, abajo o de lado.
    """
    muneca = np.array(mundo[0])
    resultado = {}
    for nombre, (punta, media) in DEDOS.items():
        d_punta = np.linalg.norm(np.array(mundo[punta]) - muneca)
        d_media = np.linalg.norm(np.array(mundo[media]) - muneca)
        resultado[nombre] = d_punta / max(d_media, 1e-6) > C.UMBRAL_DEDO_EXTENDIDO
    return resultado


def direccion_indice(puntos_px):
    """
    Ángulo (grados) del vector nudillo(5) -> punta(8) del índice en la imagen.
    0° = derecha, 90° = arriba, 180° = izquierda, -90° = abajo.
    Devuelve (gesto, ángulo). El gesto es NINGUNO si apunta en diagonal (zona muerta)
    o si el dedo se ve muy corto (apuntando hacia la cámara).
    """
    x5, y5 = puntos_px[5]
    x8, y8 = puntos_px[8]
    x0, y0 = puntos_px[0]
    largo = math.hypot(x8 - x5, y8 - y5)
    palma = math.hypot(x5 - x0, y5 - y0)
    angulo = math.degrees(math.atan2(-(y8 - y5), x8 - x5))  # "-" porque en imagen y crece hacia abajo
    if largo < C.LARGO_MINIMO_INDICE * max(palma, 1e-6):
        return Gesto.NINGUNO, angulo
    for gesto, eje in ((Gesto.DERECHA, 0), (Gesto.ARRIBA, 90), (Gesto.IZQUIERDA, 180),
                       (Gesto.ABAJO, -90)):
        diferencia = abs((angulo - eje + 180) % 360 - 180)   # distancia angular (0-180)
        if diferencia <= C.TOLERANCIA_ANGULO:
            return gesto, angulo
    return Gesto.NINGUNO, angulo


def clasificar(puntos_px, mundo):
    """Combina qué dedos están extendidos + dirección del índice -> Gesto."""
    d = dedos_extendidos(mundo)
    i, m, a, p = d["indice"], d["medio"], d["anular"], d["menique"]
    angulo = None
    if i and m and a and p:
        gesto = Gesto.PALMA
    elif not (i or m or a or p):
        gesto = Gesto.PUNO
    elif i and p and not (m or a):
        gesto = Gesto.CUERNOS
    elif i and not (m or a or p):
        gesto, angulo = direccion_indice(puntos_px)
    else:
        gesto = Gesto.NINGUNO
    return gesto, d, angulo


# ============================================================================
# LECTURA: lo que el hilo de la cámara entrega al juego
# ============================================================================
@dataclass
class Lectura:
    id: int = 0                          # aumenta con cada fotograma procesado
    t: float = 0.0                       # momento (time.monotonic) en que se procesó
    frame: np.ndarray | None = None      # imagen BGR con la mano dibujada
    gesto: Gesto = Gesto.SIN_MANO        # gesto "crudo" de este fotograma
    dedos: dict = field(default_factory=dict)
    angulo: float | None = None
    fps: float = 0.0
    centro: tuple | None = None          # centro de la palma (x, y) de 0 a 1 en el encuadre.
                                         # El juego NO muestra la cámara: con este dato dibuja un
                                         # puntito para que el jugador sepa si su mano está centrada.


# ============================================================================
# DETECTOR (hilo de cámara + MediaPipe)
# ============================================================================
class DetectorGestos:
    def __init__(self):
        self._lock = threading.Lock()
        self._lectura = Lectura()
        self._activo = False
        self._hilo = None
        self.estado = "iniciando"   # "iniciando" | "ok" | "error"
        self.error = ""             # mensaje para mostrar en pantalla si estado == "error"

    # ------------------------------------------------------------ API pública
    def iniciar(self):
        self._activo = True
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def detener(self):
        self._activo = False
        if self._hilo:
            self._hilo.join(timeout=2)

    def leer(self):
        """Devuelve la lectura más reciente (se llama desde el juego en cada cuadro)."""
        with self._lock:
            return self._lectura

    # --------------------------------------------------------- hilo de fondo
    def _fallar(self, mensaje):
        self.estado, self.error = "error", mensaje
        print(f"[Cámara] {mensaje}")

    def _crear_detector(self):
        if not os.path.exists(C.RUTA_MODELO):
            self._fallar(f"Falta el modelo {C.RUTA_MODELO}. "
                         "Ejecuta:  python descargar_modelo.py")
            return None
        opciones = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=C.RUTA_MODELO),
            running_mode=vision.RunningMode.VIDEO,       # usa el cuadro anterior para seguir la mano
            num_hands=1,
            min_hand_detection_confidence=C.CONFIANZA_DETECCION,
            min_hand_presence_confidence=C.CONFIANZA_PRESENCIA,
            min_tracking_confidence=C.CONFIANZA_SEGUIMIENTO,
        )
        try:
            return vision.HandLandmarker.create_from_options(opciones)
        except Exception as e:
            self._fallar(f"No se pudo cargar el modelo de MediaPipe: {e}")
            return None

    @staticmethod
    def _abrir_camara():
        # Backend de captura (ver CAMARA_BACKEND en config.py). Solo aplica en Windows.
        backends = {"msmf": cv2.CAP_MSMF, "dshow": cv2.CAP_DSHOW}
        backend = backends.get(C.CAMARA_BACKEND, cv2.CAP_ANY) if sys.platform == "win32" \
            else cv2.CAP_ANY
        cam = cv2.VideoCapture(C.CAMARA_INDICE, backend)
        if not cam.isOpened():
            cam.release()
            return None
        ok, frame = cam.read()               # algunas cámaras "abren" pero no entregan imagen
        # Solo cambia la resolución si hace falta: con MSMF cada cambio reinicia la cámara (~2.5 s).
        if ok and frame.shape[:2] != (C.CAMARA_ALTO, C.CAMARA_ANCHO):
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, C.CAMARA_ANCHO)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, C.CAMARA_ALTO)
            ok, _ = cam.read()
        if not ok:
            cam.release()
            return None
        return cam

    def _bucle(self):
        detector = self._crear_detector()
        if detector is None:
            return                            # sin modelo no hay nada que hacer (error ya visible)
        cam, fallos, ultimo_ts, contador = None, 0, 0, 0
        t_prev = time.monotonic()
        fps = 0.0
        while self._activo:
            # --- 1) Asegurar que la cámara esté abierta (reintento automático) ---
            if cam is None:
                cam = self._abrir_camara()
                if cam is None:
                    self._fallar(f"No se pudo abrir la cámara (índice {C.CAMARA_INDICE}). "
                                 f"Reintentando cada {C.CAMARA_REINTENTO_S:.0f} s...")
                    time.sleep(C.CAMARA_REINTENTO_S)
                    continue
                self.estado, self.error, fallos = "ok", "", 0

            ok, frame = cam.read()
            if not ok:
                fallos += 1
                if fallos > 30:                  # ~1 s sin imagen: la cámara se desconectó
                    cam.release()
                    cam = None
                    self._fallar("La cámara dejó de responder. Reintentando...")
                    with self._lock:             # que el juego no siga usando un gesto viejo
                        self._lectura = Lectura(id=self._lectura.id + 1, t=time.monotonic())
                time.sleep(0.01)
                continue
            fallos = 0

            # --- 2) Espejo + detección con MediaPipe ---
            if C.CAMARA_ESPEJO:
                frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts = max(int(time.monotonic() * 1000), ultimo_ts + 1)   # debe ser siempre creciente
            ultimo_ts = ts
            resultado = detector.detect_for_video(imagen, ts)

            # --- 3) Clasificación ---
            gesto, dedos, angulo, centro = Gesto.SIN_MANO, {}, None, None
            if resultado.hand_landmarks:
                alto, ancho = frame.shape[:2]
                puntos_px = [(p.x * ancho, p.y * alto) for p in resultado.hand_landmarks[0]]
                mundo = [(p.x, p.y, p.z) for p in resultado.hand_world_landmarks[0]]
                gesto, dedos, angulo = clasificar(puntos_px, mundo)
                palma = [resultado.hand_landmarks[0][i] for i in (0, 5, 9, 13, 17)]
                centro = (sum(p.x for p in palma) / 5, sum(p.y for p in palma) / 5)
                self._dibujar_mano(frame, puntos_px, gesto)

            # --- 4) Publicar la lectura para el juego ---
            ahora = time.monotonic()
            fps = 0.9 * fps + 0.1 * (1.0 / max(ahora - t_prev, 1e-3))
            t_prev = ahora
            contador += 1
            with self._lock:
                self._lectura = Lectura(contador, ahora, frame, gesto, dedos, angulo, fps, centro)

        if cam is not None:
            cam.release()
        detector.close()

    @staticmethod
    def _dibujar_mano(frame, puntos, gesto):
        """Dibuja el esqueleto de la mano y, si es direccional, una flecha sobre el índice."""
        pts = [(int(x), int(y)) for x, y in puntos]
        for a, b in CONEXIONES:
            cv2.line(frame, pts[a], pts[b], (255, 255, 255), 2, cv2.LINE_AA)
        for i, p in enumerate(pts):
            color = (0, 200, 255) if i in (5, 6, 7, 8) else (80, 200, 90)   # índice resaltado
            cv2.circle(frame, p, 5, color, -1, cv2.LINE_AA)
        if gesto in DIRECCIONALES:
            x5, y5 = puntos[5]
            x8, y8 = puntos[8]
            fin = (int(x8 + (x8 - x5) * 0.6), int(y8 + (y8 - y5) * 0.6))
            cv2.arrowedLine(frame, pts[8], fin, (0, 220, 255), 4, cv2.LINE_AA, tipLength=0.4)
