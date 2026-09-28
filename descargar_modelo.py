"""
descargar_modelo.py — Descarga (una sola vez) el modelo de MediaPipe para detectar manos.

MediaPipe 1.x ya no incluye el modelo dentro de la librería: la API "HandLandmarker"
necesita el archivo hand_landmarker.task (~8 MB). Ejecuta esto con internet ANTES de la
presentación; después el juego funciona sin conexión.

    python descargar_modelo.py
"""
import os
import sys
import urllib.request

import config as C


def descargar(forzar=False):
    if os.path.exists(C.RUTA_MODELO) and not forzar:
        print(f"El modelo ya existe en {C.RUTA_MODELO} ✔")
        return True
    os.makedirs(os.path.dirname(C.RUTA_MODELO), exist_ok=True)
    temporal = C.RUTA_MODELO + ".descargando"
    print(f"Descargando modelo desde:\n  {C.URL_MODELO}")
    try:
        urllib.request.urlretrieve(C.URL_MODELO, temporal)
        os.replace(temporal, C.RUTA_MODELO)      # solo queda el archivo si terminó bien
    except Exception as e:
        print(f"ERROR al descargar el modelo: {e}\n¿Tienes conexión a internet?")
        if os.path.exists(temporal):
            os.remove(temporal)
        return False
    print(f"Listo: {C.RUTA_MODELO} ({os.path.getsize(C.RUTA_MODELO) / 1e6:.1f} MB) ✔")
    return True


if __name__ == "__main__":
    sys.exit(0 if descargar(forzar="--forzar" in sys.argv) else 1)
