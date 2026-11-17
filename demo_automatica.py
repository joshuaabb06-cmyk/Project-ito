"""
demo_automatica.py — ETAPA 1: prueba del laberinto SIN cámara y SIN teclado.

El personaje se mueve solo:
  1. Primero intenta moverse contra paredes a propósito (para demostrar las colisiones).
  2. Después sigue la ruta más corta calculada con BFS hasta la meta.
  3. Muestra "¡Ganaste!" unos segundos y vuelve a empezar.

Para cerrar: botón X de la ventana (con el mouse).
"""
import time

import pygame

import config as C
from juego import Vista, lista_personajes
from laberinto import Laberinto

# Movimientos iniciales que chocan a propósito: la casilla de inicio tiene pared arriba y a la
# derecha, y a la izquierda está la entrada (salir del laberinto también cuenta como choque).
CHOQUES_DE_PRUEBA = ["ARRIBA", "DERECHA", "IZQUIERDA"]


def main():
    lab = Laberinto(C.LABERINTO, C.INICIO, C.META, C.PASO)
    vista = Vista(lab, "Project-ito — Demo automática", personaje=lista_personajes()[0][0])
    reloj = pygame.time.Clock()

    plan = CHOQUES_DE_PRUEBA + lab.resolver()
    indice = 0
    t_ultimo = t_inicio = time.monotonic()
    t_gano = None
    ultimo_evento = "Preparando..."

    corriendo = True
    while corriendo:
        ahora = time.monotonic()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:       # Solo se cierra con la X de la ventana
                corriendo = False

        # --- Lógica: un movimiento automático cada DEMO_PAUSA_ENTRE_PASOS segundos ---
        if not lab.gano and ahora - t_ultimo >= C.DEMO_PAUSA_ENTRE_PASOS and indice < len(plan):
            direccion = plan[indice]
            indice += 1
            t_ultimo = ahora
            if lab.mover(direccion):
                vista.jugador_movido(ahora)
                ultimo_evento = f"Movió: {direccion}"
            else:
                vista.jugador_choco(ahora)
                ultimo_evento = f"¡Choque! ({direccion})"
            if lab.gano:
                t_gano = ahora

        # Tras ganar, espera 4 s y reinicia la demo.
        if t_gano and ahora - t_gano > 4:
            lab.reiniciar()
            vista.jugador_reiniciado()
            indice, t_gano, t_inicio = 0, None, ahora

        # --- Dibujo ---
        vista.dibujar_fondo()
        segundos = (t_gano or ahora) - t_inicio
        vista.dibujar_barra_superior("Demo", segundos)
        vista.dibujar_laberinto(ahora)
        vista.dibujar_personaje(ahora)
        vista.dibujar_panel_demo([
            "Sin cámara ni teclado.",
            "Ruta: BFS (la más corta).",
            f"Paso {min(indice, len(plan))} de {len(plan)}",
            f"Choques: {lab.choques}",
            "",
            ultimo_evento,
            "",
            "Cerrar: botón X de la ventana",
        ])
        if lab.gano:
            vista.dibujar_mensaje("¡Ganaste!", [f"{lab.movimientos} movimientos",
                                                "Reiniciando la demo..."], C.COLOR_META)
        vista.presentar()
        reloj.tick(C.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
