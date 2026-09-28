"""
prueba_gestos.py — ETAPA 2: prueba de la detección de gestos (sin el laberinto).

Muestra la cámara con los puntos de la mano, el gesto crudo (de cada fotograma), el gesto
estable (tras la votación), qué dedos se ven extendidos y la barra de "sostener".
Útil para ajustar los umbrales de config.py con la iluminación del salón.

Salir: gesto CUERNOS (índice + meñique) sostenido 3 s, o la X de la ventana.
(OpenCV no dibuja acentos, por eso los textos de esta ventana van sin tildes.)
"""
import time

import cv2
import numpy as np

from control import ControlGestos
from gestos import DetectorGestos, Gesto

VENTANA = "Project-ito - Prueba de gestos"


def main():
    detector = DetectorGestos()
    detector.iniciar()
    control = ControlGestos()
    ultimo_evento, t_evento = "", 0.0
    cv2.namedWindow(VENTANA)

    while True:
        lectura = detector.leer()
        evento = control.actualizar(lectura)
        if evento:
            ultimo_evento, t_evento = f"DISPARADO: {evento.value}", time.monotonic()
            print(ultimo_evento)
            if evento == Gesto.CUERNOS:
                break

        if lectura.frame is not None and detector.estado == "ok":
            img = lectura.frame.copy()
        else:
            img = np.full((480, 640, 3), 40, np.uint8)   # fondo gris mientras no hay cámara
            cv2.putText(img, detector.error or "Iniciando camara...", (20, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        # Textos informativos
        dedos = " ".join(f"{k[:3]}:{'SI' if v else 'no'}" for k, v in lectura.dedos.items())
        angulo = f"{lectura.angulo:.0f} grados" if lectura.angulo is not None else "-"
        info = [f"Crudo: {lectura.gesto.value}", f"Estable: {control.estable.value}",
                f"Dedos: {dedos or '-'}", f"Angulo indice: {angulo}", f"FPS camara: {lectura.fps:.0f}"]
        for i, t in enumerate(info):
            cv2.putText(img, t, (10, 25 + i * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4,
                        cv2.LINE_AA)
            cv2.putText(img, t, (10, 25 + i * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255),
                        1, cv2.LINE_AA)
        # Barra de progreso de "sostener"
        prog = control.progreso()
        if prog is not None:
            h, w = img.shape[:2]
            cv2.rectangle(img, (10, h - 30), (w - 10, h - 12), (80, 80, 80), -1)
            cv2.rectangle(img, (10, h - 30), (10 + int((w - 20) * prog), h - 12), (90, 200, 120), -1)
        if time.monotonic() - t_evento < 1.0:
            cv2.putText(img, ultimo_evento, (10, img.shape[0] - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow(VENTANA, img)
        cv2.waitKey(1)   # necesario para que OpenCV refresque la ventana (NO se usa el teclado)
        if cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1:   # cerraron con la X
            break

    detector.detener()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
