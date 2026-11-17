"""
ajustes.py — Guarda y carga la configuración del jugador en ajustes_usuario.json.

Así, volúmenes, velocidad de gestos, dificultad, personaje y récords se recuerdan entre
partidas (una de las recomendaciones básicas de gameaccessibilityguidelines.com).
"""
import json
import os

import config as C

PREDETERMINADOS = {
    "musica": 60,             # volumen 0-100
    "efectos": 80,
    "voz": 90,
    "velocidad": "Normal",    # clave de C.VELOCIDADES
    "sonar": "Solo de noche",  # "Solo de noche" | "Siempre" | "Nunca"
    "sombrero": True,
    "contraste": False,
    "dificultad": "sheriff",
    "personaje": None,        # nombre de archivo en assets/personajes (None = el primero)
    "records": {},            # dificultad -> mejor tiempo en segundos
}
OPCIONES_SONAR = ["Solo de noche", "Siempre", "Nunca"]


def cargar():
    ajustes = dict(PREDETERMINADOS)
    ajustes["records"] = {}
    try:
        with open(C.RUTA_AJUSTES, encoding="utf-8") as f:
            guardados = json.load(f)
        for clave, valor in guardados.items():
            if clave in PREDETERMINADOS:
                ajustes[clave] = valor
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass                       # primera vez o archivo dañado: se usan los predeterminados
    if ajustes["velocidad"] not in C.VELOCIDADES:
        ajustes["velocidad"] = "Normal"
    if ajustes["dificultad"] not in C.DIFICULTADES:
        ajustes["dificultad"] = "sheriff"
    if ajustes["sonar"] not in OPCIONES_SONAR:
        ajustes["sonar"] = "Solo de noche"
    return ajustes


def guardar(ajustes):
    try:
        tmp = C.RUTA_AJUSTES + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ajustes, f, ensure_ascii=False, indent=2)
        os.replace(tmp, C.RUTA_AJUSTES)
    except OSError as e:
        print(f"[Ajustes] No se pudieron guardar: {e}")
