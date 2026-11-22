"""
main.py — Project-ito: mueve al personaje por el laberinto SOLO con gestos de la mano.

Ejecutar:   python main.py

Es una MÁQUINA DE ESTADOS. Cada estado (pantalla) define qué gestos tienen efecto:

    MENÚ ──Jugar──> TUTORIAL (solo la 1a vez) ──palma──> JUGANDO ──meta──> ¡GANASTE!
     │  ├─Tutorial──> TUTORIAL              JUGANDO ──palma──> PAUSA (Continuar/Reiniciar/Menú)
     │  ├─Dificultad──> DIFICULTAD          JUGANDO ──sin vidas──> ¡PERDISTE!
     │  ├─Personaje──> PERSONAJE
     │  └─Configuración──> CONFIGURACIÓN
    En los menús: índice arriba/abajo (o izq./der.) = elegir, palma 1 s = confirmar,
    puño 2 s = regresar.   Cuernos 3 s (en cualquier pantalla menos el tutorial) = salir.

Lector de voz (tipo TalkBack): cada pantalla, opción, valor y evento se lee en voz alta
(sonido.hablar) y además aparece como subtítulo.

El teclado NO se usa para nada. La X de la ventana (mouse) queda solo como respaldo.
"""
import time
from enum import Enum

import pygame

import ajustes as AJ
import config as C
import tutorial as TUT
from control import ControlGestos
from gestos import DIRECCIONALES, DetectorGestos, Gesto
from juego import Vista, lista_personajes
from laberinto import Laberinto
from sonido import Sonido


class Estado(Enum):
    MENU = "Menú"
    DIFICULTAD = "Dificultad"
    PERSONAJE = "Personaje"
    CONFIG = "Configuración"
    TUTORIAL = "Tutorial"
    JUGANDO = "Jugando"
    PAUSA = "Pausa"
    GANASTE = "¡Ganaste!"
    PERDISTE = "¡Perdiste!"


VERTICALES = {Gesto.ARRIBA: "Elegir", Gesto.ABAJO: "Elegir"}
HORIZONTALES = {Gesto.IZQUIERDA: "Elegir", Gesto.DERECHA: "Elegir"}

# Qué hace cada gesto en cada estado. Si un gesto no aparece, en ese estado no hace nada.
ACCIONES = {
    Estado.MENU: {**VERTICALES, Gesto.PALMA: "Confirmar", Gesto.CUERNOS: "Salir"},
    Estado.DIFICULTAD: {**HORIZONTALES, Gesto.PALMA: "Confirmar", Gesto.PUNO: "Regresar",
                        Gesto.CUERNOS: "Salir"},
    Estado.PERSONAJE: {**HORIZONTALES, Gesto.PALMA: "Elegir", Gesto.PUNO: "Regresar",
                       Gesto.CUERNOS: "Salir"},
    Estado.CONFIG: {**VERTICALES, Gesto.IZQUIERDA: "Cambiar", Gesto.DERECHA: "Cambiar",
                    Gesto.PALMA: "Confirmar", Gesto.PUNO: "Regresar", Gesto.CUERNOS: "Salir"},
    # En el tutorial todos los gestos se pueden practicar (incluso cuernos: aquí NO sale).
    Estado.TUTORIAL: {**{g: "Practicar" for g in DIRECCIONALES}, Gesto.PALMA: "Practicar",
                      Gesto.PUNO: "Practicar", Gesto.CUERNOS: "Practicar"},
    Estado.JUGANDO: {**{g: "Mover" for g in DIRECCIONALES}, Gesto.PALMA: "Pausar",
                     Gesto.PUNO: "Reiniciar", Gesto.CUERNOS: "Salir"},
    Estado.PAUSA: {**VERTICALES, Gesto.PALMA: "Confirmar", Gesto.PUNO: "Reiniciar",
                   Gesto.CUERNOS: "Salir"},
    Estado.GANASTE: {Gesto.PUNO: "Jugar de nuevo", Gesto.PALMA: "Menú", Gesto.CUERNOS: "Salir"},
    Estado.PERDISTE: {Gesto.PUNO: "Reintentar", Gesto.PALMA: "Menú", Gesto.CUERNOS: "Salir"},
}
NOMBRE_CORTO = {Gesto.PALMA: "Palma", Gesto.PUNO: "Puño", Gesto.CUERNOS: "Cuernos"}
OPCIONES_MENU = ["jugar", "tutorial", "dificultad", "personaje", "configuracion", "salir"]
ETIQUETAS_MENU = {"jugar": "JUGAR", "tutorial": "TUTORIAL", "dificultad": "DIFICULTAD",
                  "personaje": "PERSONAJE", "configuracion": "CONFIGURACIÓN", "salir": "SALIR"}
OPCIONES_PAUSA = ["continuar", "reiniciar", "menu"]
NOMBRES_PAUSA = {"continuar": "Continuar", "reiniciar": "Reiniciar", "menu": "Menú principal"}
FILAS_CONFIG = ["lector", "voz", "musica", "efectos", "velocidad", "sonar", "sombrero", "contraste",
                "regresar"]
NOMBRES_CONFIG = {"lector": "Lector de voz", "voz": "Volumen de voz", "musica": "Música",
                  "efectos": "Efectos", "velocidad": "Velocidad de gestos", "sonar": "Sonar a la salida",
                  "sombrero": "Sombrero", "contraste": "Alto contraste", "regresar": "Regresar"}
AYUDA_MENU = "Apunta con el dedo índice arriba o abajo para elegir y abre la palma un segundo para confirmar."


class App:
    def __init__(self, detector=None):
        self.aj = AJ.cargar()
        self.personajes = lista_personajes()
        archivos = [a for a, _ in self.personajes]
        if self.aj["personaje"] not in archivos:
            self.aj["personaje"] = archivos[0]
        self.lab = Laberinto(C.LABERINTO, C.INICIO, C.META, C.PASO)
        self.sonido = Sonido()
        self.vista = Vista(self.lab, personaje=self.aj["personaje"], sombrero=self.aj["sombrero"])
        self.detector = detector or DetectorGestos()
        self.detector.iniciar()
        self.control = ControlGestos()
        self.aplicar_ajustes()

        self.estado = Estado.MENU
        self.sel = 0                       # opción seleccionada en la pantalla actual
        self.gesto_bloqueado = None        # gesto que causó el último cambio de pantalla
        self.tiempo_jugado = 0.0
        self.vidas = None
        self.t_ultimo_choque = -10.0
        self.nuevo_record = False
        self.t_sin_mano = None             # desde cuándo no se ve la mano (para avisar por voz)
        self.aviso_sin_mano = False
        self.t_sonar = 0.0
        self._dist_cache = {}
        self.max_dist = len(self.lab.resolver()) or 1
        self._prog_previo = 0.0
        # Tutorial
        self.tut_paso = 0
        self.tut_t_exito = None            # cuándo se logró el paso actual (para pasar al siguiente)
        self.tut_t_pos = None              # desde cuándo la mano está centrada (paso 1)
        self.tut_origen = "menu"           # a dónde ir al terminar: "menu" o "jugar"
        self.tut_pista = None
        self.tut_t_pista = 0.0             # desde cuándo se muestra la pista actual
        self.tut_t_pista_dicha = -10.0     # última vez que se leyó una pista en voz alta
        # La voz de Windows tarda 1-2 s en arrancar: la bienvenida se lee en cuanto esté lista.
        self._bienvenida_pendiente = True
        self._t_inicio = time.monotonic()
        self.vista.subtitulo("Bienvenido a Project-ito", self._t_inicio)

    # ------------------------------------------------------------- utilidades
    @property
    def dificultad(self):
        return C.DIFICULTADES[self.aj["dificultad"]]

    def aplicar_ajustes(self):
        self.sonido.ajustar(self.aj["musica"], self.aj["efectos"], self.aj["voz"], self.aj["lector"])
        self.control.ajustar_velocidad(*C.VELOCIDADES[self.aj["velocidad"]])
        self.vista.contraste = self.aj["contraste"]
        self.vista.personaje.con_sombrero = self.aj["sombrero"]

    def hablar(self, texto, subtitulo=None, clave=None):
        """
        Lector de voz: lee `texto` y muestra un subtítulo (la información nunca depende solo
        del sonido). `clave` = audio grabado de respaldo en assets/voces/ si no hay voz de Windows.
        """
        self.sonido.hablar(texto, clave)
        self.vista.subtitulo(subtitulo or texto, time.monotonic())

    def decir(self, clave):
        """Frase corta conocida (sonido.FRASES)."""
        from sonido import FRASES
        self.hablar(FRASES.get(clave, clave), clave=clave)

    def sonar_activo(self):
        modo = self.aj["sonar"]
        return modo == "Siempre" or (modo == "Solo de noche" and self.dificultad["niebla"])

    def distancia_meta(self):
        """Pasos que faltan a la salida por la ruta más corta (se guarda para no recalcular)."""
        pos = self.lab.jugador
        if pos not in self._dist_cache:
            ruta = self.lab.resolver(pos)
            self._dist_cache[pos] = len(ruta) if ruta is not None else self.max_dist
        return self._dist_cache[pos]

    def pista(self):
        """Siguientes casillas de la ruta más corta (huellas del modo Explorador)."""
        if not self.dificultad["pista"]:
            return None
        ruta = self.lab.resolver(self.lab.jugador) or []
        celdas, pos = [], self.lab.jugador
        for direccion in ruta[:C.PASOS_PISTA]:
            pos = self.lab.destino(pos, direccion)
            celdas.append(pos)
        return celdas

    @staticmethod
    def tiempo_hablado(segundos):
        m, s = divmod(int(segundos), 60)
        if m:
            return f"{m} minuto{'s' if m != 1 else ''} y {s} segundo{'s' if s != 1 else ''}"
        return f"{s} segundo{'s' if s != 1 else ''}"

    # ------------------------------------------------- textos del lector de voz
    def texto_opcion_menu(self, i):
        clave = OPCIONES_MENU[i]
        return {"jugar": "Jugar",
                "tutorial": "Tutorial: aprende los gestos",
                "dificultad": f"Dificultad. Actual: {self.dificultad['nombre']}",
                "personaje": f"Personaje. Actual: {dict(self.personajes)[self.aj['personaje']]}",
                "configuracion": "Configuración: volumen, voz y más",
                "salir": "Salir del juego"}[clave]

    def texto_dificultad(self, i):
        clave = C.ORDEN_DIFICULTADES[i]
        d = C.DIFICULTADES[clave]
        rec = self.aj["records"].get(clave)
        record = f" Récord: {self.tiempo_hablado(rec)}." if rec else ""
        return f"{d['nombre']}. {' '.join(d['descripcion'])}{record}"

    def texto_config(self, fila):
        valor = self.valor_config(fila)
        if fila == "regresar":
            return "Regresar. Abre la palma para guardar y volver al menú."
        if isinstance(valor, int):
            valor = f"{valor} por ciento"
        return f"{NOMBRES_CONFIG[fila]}: {valor}"

    def anunciar_pantalla(self):
        """Lo que el lector dice al entrar a cada pantalla."""
        e = self.estado
        if e == Estado.MENU:
            self.hablar(f"Menú principal. {self.texto_opcion_menu(self.sel)}. {AYUDA_MENU}",
                        self.texto_opcion_menu(self.sel))
        elif e == Estado.DIFICULTAD:
            self.hablar(f"Elige tu dificultad con el índice a la izquierda o a la derecha. "
                        f"{self.texto_dificultad(self.sel)}", self.dificultad_nombre(self.sel))
        elif e == Estado.PERSONAJE:
            archivo, nombre = self.personajes[self.sel]
            self.hablar(f"Elige personaje con el índice a la izquierda o a la derecha. {nombre}, "
                        f"{self.sel + 1} de {len(self.personajes)}.", nombre)
        elif e == Estado.CONFIG:
            self.hablar(f"Configuración. Índice arriba o abajo para elegir, izquierda o derecha para "
                        f"cambiar, puño para guardar y regresar. {self.texto_config(FILAS_CONFIG[self.sel])}",
                        self.texto_config(FILAS_CONFIG[self.sel]))

    @staticmethod
    def dificultad_nombre(i):
        return C.DIFICULTADES[C.ORDEN_DIFICULTADES[i]]["nombre"]

    # -------------------------------------------------------------- estados
    def cambiar_estado(self, nuevo, sel=0, anunciar=True):
        self.estado = nuevo
        self.sel = sel
        # El gesto que provocó el cambio sigue en la mano: se "bloquea" hasta que el jugador
        # cambie de gesto, para que no dispare otra acción en la nueva pantalla.
        self.gesto_bloqueado = self.control.estable
        musica = {Estado.JUGANDO: "juego", Estado.PAUSA: "juego", Estado.TUTORIAL: "menu",
                  Estado.GANASTE: None, Estado.PERDISTE: None}.get(nuevo, "menu")
        self.sonido.musica(musica)
        if anunciar:
            self.anunciar_pantalla()

    def iniciar_partida(self, ahora):
        self.lab.reiniciar()
        self.vista.jugador_reiniciado()
        self.tiempo_jugado = 0.0
        self.vidas = self.dificultad["vidas"]
        self.t_ultimo_choque = -10.0
        self.t_sonar = ahora + 1.0
        self.cambiar_estado(Estado.JUGANDO, anunciar=False)
        vidas = "Vidas infinitas" if self.vidas is None else f"{self.vidas} vida{'s' if self.vidas > 1 else ''}"
        extra = " Está oscuro: guíate con el sonar." if self.dificultad["niebla"] else ""
        self.hablar(f"¡A jugar! {self.dificultad['nombre']}, {vidas}. Llega a la estrella de sheriff, "
                    f"arriba a la derecha.{extra}", "¡A jugar!")

    def volver_menu(self, opcion="jugar"):
        self.cambiar_estado(Estado.MENU, OPCIONES_MENU.index(opcion))

    def iniciar_tutorial(self, origen):
        self.tut_paso, self.tut_t_exito, self.tut_t_pos, self.tut_origen = 0, None, None, origen
        self.tut_pista, self.tut_t_pista = None, time.monotonic()
        self.cambiar_estado(Estado.TUTORIAL, anunciar=False)
        self.hablar("Tutorial. " + TUT.PASOS[0]["voz"], TUT.PASOS[0]["titulo"])

    def terminar_tutorial(self, ahora, jugar):
        self.aj["tutorial_visto"] = True
        AJ.guardar(self.aj)
        if jugar:
            self.iniciar_partida(ahora)
        else:
            self.volver_menu("tutorial" if self.tut_origen == "menu" else "jugar")

    def mover_seleccion(self, gesto, total):
        paso = {Gesto.ARRIBA: -1, Gesto.ABAJO: 1, Gesto.IZQUIERDA: -1, Gesto.DERECHA: 1}[gesto]
        self.sel = (self.sel + paso) % total
        self.sonido.efecto("seleccionar")

    # ----------------------------------------------------------- acciones
    def manejar(self, gesto, ahora):
        """Ejecuta la acción del gesto confirmado. Devuelve False si hay que salir."""
        e = self.estado
        if e == Estado.TUTORIAL:              # va primero: en el tutorial los cuernos NO salen
            self.manejar_tutorial(gesto, ahora)
            return True
        if gesto == Gesto.CUERNOS:
            return False
        if e == Estado.MENU:
            if gesto in VERTICALES:
                self.mover_seleccion(gesto, len(OPCIONES_MENU))
                self.hablar(self.texto_opcion_menu(self.sel))
            elif gesto == Gesto.PALMA:
                self.sonido.efecto("confirmar")
                opcion = OPCIONES_MENU[self.sel]
                if opcion == "jugar":
                    if self.aj["tutorial_visto"]:
                        self.iniciar_partida(ahora)
                    else:
                        self.iniciar_tutorial("jugar")
                elif opcion == "tutorial":
                    self.iniciar_tutorial("menu")
                elif opcion == "dificultad":
                    self.cambiar_estado(Estado.DIFICULTAD, C.ORDEN_DIFICULTADES.index(self.aj["dificultad"]))
                elif opcion == "personaje":
                    archivos = [a for a, _ in self.personajes]
                    self.cambiar_estado(Estado.PERSONAJE, archivos.index(self.aj["personaje"]))
                elif opcion == "configuracion":
                    self.cambiar_estado(Estado.CONFIG)
                elif opcion == "salir":
                    return False
        elif e == Estado.DIFICULTAD:
            if gesto in HORIZONTALES:
                self.mover_seleccion(gesto, len(C.ORDEN_DIFICULTADES))
                self.hablar(self.texto_dificultad(self.sel), self.dificultad_nombre(self.sel))
            elif gesto == Gesto.PALMA:
                self.aj["dificultad"] = C.ORDEN_DIFICULTADES[self.sel]
                AJ.guardar(self.aj)
                self.sonido.efecto("confirmar")
                self.volver_menu("jugar")
            elif gesto == Gesto.PUNO:
                self.sonido.efecto("regresar")
                self.volver_menu("dificultad")
        elif e == Estado.PERSONAJE:
            if gesto in HORIZONTALES and len(self.personajes) > 1:
                self.mover_seleccion(gesto, len(self.personajes))
                nombre = self.personajes[self.sel][1]
                self.hablar(f"{nombre}, {self.sel + 1} de {len(self.personajes)}", nombre)
            elif gesto == Gesto.PALMA:
                self.aj["personaje"] = self.personajes[self.sel][0]
                self.vista.personaje.cambiar(self.aj["personaje"])
                AJ.guardar(self.aj)
                self.sonido.efecto("confirmar")
                self.volver_menu("jugar")
            elif gesto == Gesto.PUNO:
                self.sonido.efecto("regresar")
                self.volver_menu("personaje")
        elif e == Estado.CONFIG:
            fila = FILAS_CONFIG[self.sel]
            if gesto in VERTICALES:
                self.mover_seleccion(gesto, len(FILAS_CONFIG))
                self.hablar(self.texto_config(FILAS_CONFIG[self.sel]))
            elif gesto in HORIZONTALES:
                self.cambiar_valor(fila, 1 if gesto == Gesto.DERECHA else -1)
            elif gesto == Gesto.PUNO or (gesto == Gesto.PALMA and fila == "regresar"):
                AJ.guardar(self.aj)
                self.sonido.efecto("regresar")
                self.volver_menu("configuracion")
            elif gesto == Gesto.PALMA and fila in ("lector", "sombrero", "contraste"):
                self.cambiar_valor(fila, 1)
        elif e == Estado.JUGANDO:
            if gesto in DIRECCIONALES:
                self.mover_jugador(gesto, ahora)
            elif gesto == Gesto.PALMA:
                self.sonido.efecto("confirmar")
                self.cambiar_estado(Estado.PAUSA, anunciar=False)
                self.hablar("Pausa. Continuar. Índice arriba o abajo para elegir, palma para confirmar.",
                            "Pausa")
            elif gesto == Gesto.PUNO:
                self.iniciar_partida(ahora)
                self.vista.avisar("Laberinto reiniciado", ahora)
        elif e == Estado.PAUSA:
            if gesto in VERTICALES:
                self.mover_seleccion(gesto, len(OPCIONES_PAUSA))
                self.hablar(NOMBRES_PAUSA[OPCIONES_PAUSA[self.sel]])
            elif gesto == Gesto.PALMA or gesto == Gesto.PUNO:
                opcion = "reiniciar" if gesto == Gesto.PUNO else OPCIONES_PAUSA[self.sel]
                self.sonido.efecto("confirmar")
                if opcion == "continuar":
                    self.cambiar_estado(Estado.JUGANDO, anunciar=False)
                    self.decir("continuar")
                elif opcion == "reiniciar":
                    self.iniciar_partida(ahora)
                    self.vista.avisar("Laberinto reiniciado", ahora)
                else:
                    self.volver_menu("jugar")
        elif e in (Estado.GANASTE, Estado.PERDISTE):
            if gesto == Gesto.PUNO:
                self.iniciar_partida(ahora)
            elif gesto == Gesto.PALMA:
                self.volver_menu("jugar")
        return True

    def manejar_tutorial(self, gesto, ahora):
        paso = TUT.PASOS[self.tut_paso]
        objetivo = paso["objetivo"]
        if self.tut_t_exito is not None:
            return                                   # ya lo logró: esperando el siguiente paso
        if objetivo == "FIN":
            if gesto == Gesto.PALMA:
                self.sonido.efecto("confirmar")
                self.terminar_tutorial(ahora, jugar=True)
            elif gesto == Gesto.PUNO:
                self.sonido.efecto("regresar")
                self.terminar_tutorial(ahora, jugar=False)
            return
        if gesto.value == objetivo:
            self.tut_t_exito = ahora
            self.sonido.efecto("confirmar")
            self.hablar("¡Muy bien!")
        elif gesto == Gesto.PUNO:                    # puño 2 s = saltar el tutorial
            self.sonido.efecto("regresar")
            self.hablar("Tutorial saltado.")
            self.terminar_tutorial(ahora, jugar=self.tut_origen == "jugar")
        elif objetivo != "POSICION":
            pista = TUT.pista(objetivo, gesto.value, True)
            if pista:
                self.sonido.efecto("regresar", volumen=0.6)
                self.hablar(pista)
                self.tut_t_pista_dicha = ahora

    def cambiar_valor(self, fila, paso):
        aj = self.aj
        if fila in ("musica", "efectos", "voz"):
            aj[fila] = max(0, min(100, aj[fila] + 10 * paso))
        elif fila == "velocidad":
            opciones = list(C.VELOCIDADES)
            aj[fila] = opciones[(opciones.index(aj[fila]) + paso) % len(opciones)]
        elif fila == "sonar":
            opciones = AJ.OPCIONES_SONAR
            aj[fila] = opciones[(opciones.index(aj[fila]) + paso) % len(opciones)]
        elif fila in ("lector", "sombrero", "contraste"):
            aj[fila] = not aj[fila]
        else:
            return
        self.aplicar_ajustes()
        self.sonido.efecto("seleccionar")
        if fila == "efectos":
            self.sonido.efecto("paso")      # para escuchar cómo quedó el volumen
        if fila == "lector" and not aj[fila]:
            self.vista.subtitulo("Lector de voz: No", time.monotonic())
        else:
            self.hablar(self.texto_config(fila))

    def mover_jugador(self, gesto, ahora):
        direccion = gesto.value
        if self.lab.destino(self.lab.jugador, direccion) is None and self.control.repetido:
            # Mantener la dirección y llegar a una pared NO cuenta como choque: solo cuenta
            # cuando el jugador intenta el movimiento a propósito (evita perder vidas injustamente).
            return
        if self.lab.mover(direccion):
            self.vista.jugador_movido(ahora)
            self.sonido.efecto("paso", volumen=0.8)
            if self.lab.gano:
                self.terminar(ganaste=True)
            return
        # --- Choque ---
        paneo = {"IZQUIERDA": -0.8, "DERECHA": 0.8}.get(direccion, 0.0)
        self.sonido.efecto("choque", paneo)
        self.vista.jugador_choco(ahora, direccion)
        lado = {"ARRIBA": "arriba", "ABAJO": "abajo", "IZQUIERDA": "a la izquierda",
                "DERECHA": "a la derecha"}[direccion]
        if self.vidas is None:
            self.vista.avisar("¡Choque!", ahora)
            self.hablar(f"Pared {lado}", "¡Choque!")
            return
        if ahora - self.t_ultimo_choque < C.GRACIA_CHOQUE:
            return                               # periodo de gracia: no se pierde otra vida
        self.t_ultimo_choque = ahora
        self.vidas -= 1
        if self.vidas <= 0:
            self.terminar(ganaste=False)
        else:
            self.sonido.efecto("vida_menos")
            quedan = f"Te queda{'n' if self.vidas > 1 else ''} {self.vidas} vida{'s' if self.vidas > 1 else ''}"
            self.vista.avisar(f"¡Choque! {quedan}", ahora)
            self.hablar(f"Pared {lado}. {quedan}", quedan, clave=f"vidas_{min(self.vidas, 2)}")

    def terminar(self, ganaste):
        if ganaste:
            clave = self.aj["dificultad"]
            anterior = self.aj["records"].get(clave)
            self.nuevo_record = anterior is None or self.tiempo_jugado < anterior
            if self.nuevo_record:
                self.aj["records"][clave] = round(self.tiempo_jugado, 1)
                AJ.guardar(self.aj)
            self.cambiar_estado(Estado.GANASTE, anunciar=False)
            self.sonido.efecto("ganar")
            record = " ¡Nuevo récord!" if self.nuevo_record else ""
            self.hablar(f"¡Ganaste! {self.lab.movimientos} pasos en {self.tiempo_hablado(self.tiempo_jugado)}."
                        f"{record} Puño para jugar de nuevo, palma para el menú.", "¡Ganaste!", clave="ganaste")
        else:
            self.cambiar_estado(Estado.PERDISTE, anunciar=False)
            self.sonido.efecto("perder")
            self.hablar(f"Perdiste. Te quedaste a {self.distancia_meta()} pasos de la salida. "
                        "Puño para reintentar, palma para el menú.", "Perdiste", clave="perdiste")

    # ------------------------------------------------------- cada fotograma
    def actualizar(self, lectura, dt, ahora):
        """Lógica continua: tiempo, sonar, tutorial, avisos de mano y sonidos de 'cargando'."""
        self.sonido.actualizar()
        if self._bienvenida_pendiente and (self.sonido.tts.disponible or ahora - self._t_inicio > 4):
            self._bienvenida_pendiente = False
            if self.estado == Estado.MENU:
                self.hablar(f"Bienvenido a Project-ito, el laberinto del desierto. {AYUDA_MENU} "
                            f"{self.texto_opcion_menu(self.sel)}.", "Bienvenido a Project-ito", clave="jugar")
        if self.estado == Estado.JUGANDO:
            self.tiempo_jugado += dt
            if self.sonar_activo() and ahora >= self.t_sonar:
                fraccion = min(1.0, self.distancia_meta() / self.max_dist)     # 1 = lejos, 0 = cerca
                nivel = min(C.SONAR_NIVELES - 1, int((1 - fraccion) * C.SONAR_NIVELES))
                self.sonido.efecto(f"sonar_{nivel}", volumen=0.7)
                self.t_sonar = ahora + C.SONAR_INTERVALO_CERCA + \
                    (C.SONAR_INTERVALO_LEJOS - C.SONAR_INTERVALO_CERCA) * fraccion
        if self.estado == Estado.TUTORIAL:
            self.actualizar_tutorial(lectura, ahora)
        # Avisar por voz si la mano se pierde más de 2 s mientras juegas.
        sin_mano = self.detector.estado == "ok" and self.control.estable == Gesto.SIN_MANO
        if sin_mano:
            self.t_sin_mano = self.t_sin_mano or ahora
            if self.estado == Estado.JUGANDO and not self.aviso_sin_mano and ahora - self.t_sin_mano > 2:
                self.aviso_sin_mano = True
                self.decir("sin_mano")
        else:
            self.t_sin_mano, self.aviso_sin_mano = None, False
        # "Tic" que sube de tono mientras sostienes palma / puño / cuernos (retroalimentación sonora).
        estable = self.control.estable
        prog = self.control.progreso(ahora) or 0.0
        if estable in (Gesto.PALMA, Gesto.PUNO, Gesto.CUERNOS) and estable in ACCIONES[self.estado] \
                and estable != self.gesto_bloqueado:
            for i, umbral in enumerate((0.34, 0.67)):
                if self._prog_previo < umbral <= prog:
                    self.sonido.efecto(f"carga_{i + 1}", volumen=0.6)
        self._prog_previo = prog

    def mano_centrada(self, lectura):
        c = lectura.centro
        return (c is not None and self.control.estable != Gesto.SIN_MANO
                and 0.2 <= c[0] <= 0.8 and 0.18 <= c[1] <= 0.82)

    def actualizar_tutorial(self, lectura, ahora):
        paso = TUT.PASOS[self.tut_paso]
        objetivo = paso["objetivo"]
        # Después de "¡Muy bien!" se pasa solo al siguiente paso.
        if self.tut_t_exito is not None:
            if ahora - self.tut_t_exito > 1.5:
                self.tut_paso += 1
                self.tut_t_exito, self.tut_t_pos = None, None
                self.gesto_bloqueado = self.control.estable     # el gesto anterior no cuenta
                nuevo = TUT.PASOS[self.tut_paso]
                if nuevo["objetivo"] == "FIN":
                    self.aj["tutorial_visto"] = True
                    AJ.guardar(self.aj)
                self.hablar(nuevo["voz"], nuevo["titulo"])
                self.tut_pista, self.tut_t_pista = None, ahora
            return
        # Paso 1: la mano debe quedarse centrada 1.5 s.
        if objetivo == "POSICION" and self.detector.estado == "ok":
            if self.mano_centrada(lectura):
                self.tut_t_pos = self.tut_t_pos or ahora
                if ahora - self.tut_t_pos >= 1.5:
                    self.tut_t_exito = ahora
                    self.sonido.efecto("confirmar")
                    self.hablar("¡Muy bien!")
            else:
                self.tut_t_pos = None
        # Pista: si la misma pista sigue 3 s, se lee en voz alta (máximo cada 5 s).
        pista = TUT.pista(objetivo, self.control.estable.value, self.mano_centrada(lectura))
        if pista != self.tut_pista:
            self.tut_pista, self.tut_t_pista = pista, ahora
        elif pista and ahora - self.tut_t_pista > 3 and ahora - self.tut_t_pista_dicha > 5:
            self.tut_t_pista_dicha = ahora
            self.hablar(pista)

    def ejecutar(self):
        reloj = pygame.time.Clock()
        corriendo = True
        while corriendo:
            dt = reloj.tick(C.FPS) / 1000
            ahora = time.monotonic()
            for evento in pygame.event.get():          # solo la X de la ventana; el teclado se ignora
                if evento.type == pygame.QUIT:
                    corriendo = False

            lectura = self.detector.leer()
            disparado = self.control.actualizar(lectura, ahora)
            if self.control.estable != self.gesto_bloqueado:
                self.gesto_bloqueado = None
            if (disparado and self.detector.estado == "ok" and disparado in ACCIONES[self.estado]
                    and disparado != self.gesto_bloqueado):
                corriendo = self.manejar(disparado, ahora) and corriendo
            self.actualizar(lectura, dt, ahora)
            self.dibujar(lectura, ahora)

        AJ.guardar(self.aj)
        self.sonido.cerrar()
        self.detector.detener()
        pygame.quit()

    # ------------------------------------------------------------ dibujo
    def leyenda(self):
        """Filas (ícono, gesto, segundos, acción) para el panel de ayuda de la pantalla actual."""
        acciones = ACCIONES[self.estado]
        filas = []
        dur = self.control.duraciones
        if Gesto.ARRIBA in acciones and Gesto.IZQUIERDA in acciones:
            if acciones[Gesto.ARRIBA] == acciones[Gesto.IZQUIERDA]:
                filas.append(("INDICE", "Dedo índice", dur[Gesto.ARRIBA], acciones[Gesto.ARRIBA]))
            else:
                filas.append(("VERTICAL", "Índice arriba/abajo", dur[Gesto.ARRIBA], acciones[Gesto.ARRIBA]))
                filas.append(("HORIZONTAL", "Índice izq./der.", dur[Gesto.IZQUIERDA], acciones[Gesto.IZQUIERDA]))
        elif Gesto.ARRIBA in acciones:
            filas.append(("VERTICAL", "Índice arriba/abajo", dur[Gesto.ARRIBA], acciones[Gesto.ARRIBA]))
        elif Gesto.IZQUIERDA in acciones:
            filas.append(("HORIZONTAL", "Índice izq./der.", dur[Gesto.IZQUIERDA], acciones[Gesto.IZQUIERDA]))
        for gesto in (Gesto.PALMA, Gesto.PUNO, Gesto.CUERNOS):
            if gesto in acciones:
                filas.append((gesto.value, NOMBRE_CORTO[gesto], dur[gesto], acciones[gesto]))
        return filas

    def info_gesto(self, ahora):
        """(acción, progreso, nota) del gesto estable para la barra de 'sostener'."""
        estable = self.control.estable
        if estable == self.gesto_bloqueado and estable in ACCIONES[self.estado]:
            return None, None, "Cambia de gesto para volver a usarlo"
        accion = ACCIONES[self.estado].get(estable)
        if accion is None:
            return None, None, None
        if estable in DIRECCIONALES and self.estado == Estado.JUGANDO:
            accion = f"{accion} {estable.value.lower()}"
        return accion, self.control.progreso(ahora), None

    def valor_config(self, fila):
        aj = self.aj
        if fila in ("musica", "efectos", "voz"):
            return int(aj[fila])
        if fila in ("lector", "sombrero", "contraste"):
            return "Sí" if aj[fila] else "No"
        if fila == "regresar":
            return None
        return aj[fila]

    def dibujar_tutorial(self, lectura, ahora, progreso):
        paso = TUT.PASOS[self.tut_paso]
        objetivo = paso["objetivo"]
        estable = self.control.estable
        exito = self.tut_t_exito is not None
        accion = None
        if objetivo == "POSICION":
            progreso = min(1.0, (ahora - self.tut_t_pos) / 1.5) if self.tut_t_pos else None
            if self.tut_t_pos:
                accion = "Así, no te muevas..."
        elif objetivo == "FIN":
            progreso = progreso if estable in (Gesto.PALMA, Gesto.PUNO) else None
            accion = {Gesto.PALMA: "Abriendo el juego...", Gesto.PUNO: "Volviendo al menú..."}.get(estable)
        elif estable.value == objetivo:
            accion = "¡Eso es! Sostén..."
        elif estable == Gesto.PUNO:
            accion = "Sostén el puño para saltar el tutorial"
        else:
            progreso = None
        pista = None if exito else self.tut_pista
        self.vista.dibujar_tutorial(self.tut_paso, TUT.PASOS, exito, progreso, pista, lectura, estable,
                                    self.detector.estado, ahora, accion)

    def dibujar(self, lectura, ahora):
        v = self.vista
        if self.detector.estado == "error":
            v.dibujar_error(self.detector.error)
            v.presentar()
            return
        accion, progreso, nota = self.info_gesto(ahora)
        estable, cam = self.control.estable, self.detector.estado
        prog_sel = progreso if estable == Gesto.PALMA and accion else None   # barra bajo la opción
        e = self.estado
        if e == Estado.MENU:
            opciones = []
            for clave in OPCIONES_MENU:
                valor = {"dificultad": self.dificultad["nombre"],
                         "personaje": dict(self.personajes)[self.aj["personaje"]],
                         "tutorial": "Aprende los gestos"}.get(clave)
                opciones.append((ETIQUETAS_MENU[clave], valor))
            v.dibujar_menu(opciones, self.sel, prog_sel, lectura, estable, cam, ahora)
        elif e == Estado.DIFICULTAD:
            v.dibujar_dificultad(C.ORDEN_DIFICULTADES, self.sel, prog_sel, self.aj["records"],
                                 lectura, estable, cam)
        elif e == Estado.PERSONAJE:
            v.dibujar_personajes(self.personajes, self.sel, prog_sel, lectura, estable, cam, ahora)
        elif e == Estado.CONFIG:
            filas = [(NOMBRES_CONFIG[f], self.valor_config(f)) for f in FILAS_CONFIG]
            v.dibujar_configuracion(filas, self.sel, prog_sel, lectura, estable, cam)
        else:
            v.dibujar_fondo()
            vidas = (self.vidas, self.dificultad["vidas"]) if self.dificultad["vidas"] else None
            v.dibujar_barra_superior(e.value, self.tiempo_jugado, self.dificultad["nombre"],
                                     vidas if e != Estado.TUTORIAL else None)
            if e == Estado.TUTORIAL:
                self.dibujar_tutorial(lectura, ahora, progreso)
            else:
                datos = dict(lectura=lectura, estable=estable, progreso=progreso, accion=accion, nota=nota,
                             leyenda=self.leyenda(), estado_camara=cam)
                v.dibujar_laberinto(ahora, self.pista() if e == Estado.JUGANDO else None)
                v.dibujar_personaje(ahora)
                if self.dificultad["niebla"] and e in (Estado.JUGANDO, Estado.PAUSA):
                    v.dibujar_niebla(ahora)
                v.dibujar_aviso(ahora)
                sonar = 1 - min(1.0, self.distancia_meta() / self.max_dist) if self.sonar_activo() else None
                v.dibujar_panel_juego(vidas=vidas, sonar=sonar, **datos)
                m, s = divmod(int(self.tiempo_jugado), 60)
                if e == Estado.PAUSA:
                    v.dibujar_mensaje("Pausa", ["Índice arriba/abajo: elegir  ·  Palma: confirmar"],
                                      opciones=["Continuar", "Reiniciar", "Menú principal"],
                                      seleccion=self.sel, progreso=prog_sel)
                elif e == Estado.GANASTE:
                    lineas = [f"{self.dificultad['nombre']}: {self.lab.movimientos} pasos en {m:02d}:{s:02d}",
                              f"Choques contra la cerca: {self.lab.choques}"]
                    if self.nuevo_record:
                        lineas.append("¡Nuevo récord en esta dificultad!")
                    lineas += ["", "Puño 2 s: jugar de nuevo   ·   Palma 1 s: menú"]
                    v.dibujar_mensaje("¡Ganaste!", lineas, C.COLOR_META)
                elif e == Estado.PERDISTE:
                    v.dibujar_mensaje("¡Perdiste!", [f"Llegaste a {self.distancia_meta()} pasos de la salida",
                                                     f"Tiempo: {m:02d}:{s:02d}", "",
                                                     "Puño 2 s: reintentar   ·   Palma 1 s: menú"],
                                      C.COLOR_ALERTA)
        v.subtitulo_arriba = e == Estado.TUTORIAL
        v.dibujar_subtitulo(ahora)
        v.presentar()


if __name__ == "__main__":
    App().ejecutar()
