"""
tutorial.py — Contenido del tutorial interactivo: qué pide cada paso, qué se lee en voz alta
y qué pista dar cuando el jugador hace otro gesto.

main.py se encarga de la lógica (avanzar cuando el gesto es correcto) y juego.py del dibujo.
"""

NOMBRE_DIRECCION = {"ARRIBA": "arriba", "ABAJO": "abajo", "IZQUIERDA": "a la izquierda",
                    "DERECHA": "a la derecha"}

PASOS = [
    dict(objetivo="POSICION", titulo="Coloca tu mano",
         lineas=["Siéntate frente a la cámara.",
                 "Pon tu mano a unos 40-60 cm",
                 "(más o menos un brazo doblado).",
                 "La palma mira hacia la pantalla.",
                 "Deja la mano en el centro del",
                 "recuadro de la derecha."],
         voz="Paso 1 de 8. Pon tu mano frente a la cámara, a unos cincuenta centímetros, con la palma "
             "mirando hacia la pantalla. Déjala quieta en el centro."),
    dict(objetivo="ARRIBA", titulo="Índice hacia ARRIBA",
         lineas=["El índice es el dedo que está",
                 "junto al pulgar (punta dorada).",
                 "Estira SOLO el índice y apunta",
                 "hacia arriba.",
                 "Dobla los otros dedos, como puño.",
                 "Sostén medio segundo."],
         voz="Paso 2. Estira solo el dedo índice, el que está junto al pulgar, y apunta hacia arriba. "
             "Dobla los demás dedos como si hicieras un puño. Sostén medio segundo."),
    dict(objetivo="ABAJO", titulo="Índice hacia ABAJO",
         lineas=["Gira la muñeca y apunta al",
                 "suelo con el índice.",
                 "Los demás dedos siguen doblados.",
                 "Sostén medio segundo."],
         voz="Paso 3. Ahora apunta hacia abajo con el índice. Los demás dedos siguen doblados."),
    dict(objetivo="IZQUIERDA", titulo="Índice a la IZQUIERDA",
         lineas=["Apunta con el índice hacia tu",
                 "izquierda.",
                 "La pantalla es como un espejo:",
                 "tu izquierda es la izquierda",
                 "de la pantalla."],
         voz="Paso 4. Apunta con el índice hacia tu izquierda. La pantalla funciona como un espejo."),
    dict(objetivo="DERECHA", titulo="Índice a la DERECHA",
         lineas=["Apunta con el índice hacia tu",
                 "derecha.",
                 "Si apuntas en diagonal no pasa",
                 "nada: apunta bien recto."],
         voz="Paso 5. Apunta con el índice hacia tu derecha. Apunta recto, no en diagonal."),
    dict(objetivo="PALMA", titulo="Palma abierta",
         lineas=["Abre toda la mano, con los",
                 "dedos estirados.",
                 "Sostén 1 segundo.",
                 "Sirve para CONFIRMAR en los",
                 "menús y PAUSAR en el juego."],
         voz="Paso 6. Abre toda la mano con los dedos estirados y sostenla un segundo. Sirve para "
             "confirmar en los menús y para pausar el juego."),
    dict(objetivo="PUNO", titulo="Puño",
         lineas=["Cierra la mano en puño.",
                 "Sostén 2 segundos.",
                 "Sirve para REGRESAR en los",
                 "menús y REINICIAR en el juego."],
         voz="Paso 7. Cierra la mano en puño y sostenlo dos segundos. Sirve para regresar en los menús "
             "y para reiniciar el laberinto."),
    dict(objetivo="CUERNOS", titulo="Cuernos",
         lineas=["Estira el índice y el meñique;",
                 "dobla el medio y el anular.",
                 "Sostén 3 segundos.",
                 "Sirve para SALIR del juego.",
                 "(Aquí solo practicas, no sale.)"],
         voz="Paso 8. Estira el índice y el meñique, y dobla el medio y el anular. Sostén tres segundos. "
             "Sirve para salir del juego, pero aquí solo practicas."),
    dict(objetivo="FIN", titulo="¡Listo, vaquero!",
         lineas=["Ya conoces todos los gestos.",
                 "",
                 "Palma 1 s: jugar",
                 "Puño 2 s: menú principal",
                 "",
                 "Puedes repetir el tutorial",
                 "desde el menú cuando quieras."],
         voz="¡Listo! Ya conoces todos los gestos. Abre la palma para jugar, o haz puño para volver al menú."),
]

DIRECCIONES = ("ARRIBA", "ABAJO", "IZQUIERDA", "DERECHA")


def pista(objetivo, gesto, mano_centrada):
    """
    Consejo para el jugador según lo que la cámara está viendo (`gesto`, texto del Gesto) y lo
    que pide el paso (`objetivo`). Devuelve None si va bien.
    """
    if objetivo == "FIN":
        return None
    if gesto == "SIN_MANO":
        return "No veo tu mano: ponla frente a la cámara."
    if objetivo == "POSICION":
        return None if mano_centrada else "Lleva tu mano al centro del recuadro."
    if gesto == objetivo:
        return None
    if objetivo in DIRECCIONES:
        if gesto in DIRECCIONES:
            return f"Ese es otro lado: apunta {NOMBRE_DIRECCION[objetivo]}."
        if gesto == "PALMA":
            return "Dobla los demás dedos: deja estirado solo el índice."
        if gesto == "PUNO":
            return "Bien el puño; ahora estira el dedo índice."
        if gesto == "CUERNOS":
            return "Dobla también el meñique: solo el índice estirado."
        return f"Casi: estira bien el índice, apunta recto {NOMBRE_DIRECCION[objetivo]}."
    if objetivo == "PALMA":
        return "Abre toda la mano y estira los cuatro dedos."
    if objetivo == "PUNO":
        return "Cierra todos los dedos."
    if objetivo == "CUERNOS":
        return "Solo índice y meñique estirados; medio y anular doblados."
    return None
