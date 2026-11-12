"""
main.py — Project-ito: mueve al personaje por el laberinto SOLO con gestos de la mano.

Ejecutar:   python main.py

Es una MÁQUINA DE ESTADOS. Cada estado (pantalla) define qué gestos tienen efecto:

    MENÚ ──Jugar──> PRUEBA DE GESTOS (solo la 1a vez) ──palma──> JUGANDO ──meta──> ¡GANASTE!
     │  ├─Dificultad──> DIFICULTAD          JUGANDO ──palma──> PAUSA (Continuar/Reiniciar/Menú)
     │  ├─Personaje──> PERSONAJE            JUGANDO ──sin vidas──> ¡PERDISTE!
     │  └─Configuración──> CONFIGURACIÓN
    En los menús: índice arriba/abajo (o izq./der.) = elegir, palma 1 s = confirmar,
    puño 2 s = regresar.   Cuernos 3 s (en cualquier pantalla) = salir del programa.

El teclado NO se usa para nada. La X de la ventana (mouse) queda solo como respaldo.
"""
import time
from enum import Enum

import pygame

import ajustes as AJ
import config as C
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
    CALIBRACION = "Prueba de gestos"
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
    Estado.CALIBRACION: {**{g: "Probar" for g in DIRECCIONALES}, Gesto.PALMA: "Comenzar",
                         Gesto.PUNO: "Menú", Gesto.CUERNOS: "Salir"},
    Estado.JUGANDO: {**{g: "Mover" for g in DIRECCIONALES}, Gesto.PALMA: "Pausar",
                     Gesto.PUNO: "Reiniciar", Gesto.CUERNOS: "Salir"},
    Estado.PAUSA: {**VERTICALES, Gesto.PALMA: "Confirmar", Gesto.PUNO: "Reiniciar",
                   Gesto.CUERNOS: "Salir"},
    Estado.GANASTE: {Gesto.PUNO: "Jugar de nuevo", Gesto.PALMA: "Menú", Gesto.CUERNOS: "Salir"},
    Estado.PERDISTE: {Gesto.PUNO: "Reintentar", Gesto.PALMA: "Menú", Gesto.CUERNOS: "Salir"},
}
NOMBRE_CORTO = {Gesto.PALMA: "Palma", Gesto.PUNO: "Puño", Gesto.CUERNOS: "Cuernos"}
ESTADOS_MENU = {Estado.MENU, Estado.DIFICULTAD, Estado.PERSONAJE, Estado.CONFIG}
OPCIONES_MENU = ["jugar", "dificultad", "personaje", "configuracion", "salir"]
OPCIONES_PAUSA = ["continuar", "reiniciar", "menu"]
FILAS_CONFIG = ["musica", "efectos", "voz", "velocidad", "sonar", "sombrero", "contraste", "regresar"]


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
        self.calibrado = False             # la prueba de gestos solo se muestra la primera vez
        self.flecha, self.t_flecha, self.ya_practico = None, 0.0, False
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
        self.decir("jugar")

    # ------------------------------------------------------------- utilidades
    @property
    def dificultad(self):
        return C.DIFICULTADES[self.aj["dificultad"]]

    def aplicar_ajustes(self):
        self.sonido.ajustar(self.aj["musica"], self.aj["efectos"], self.aj["voz"])
        self.control.ajustar_velocidad(*C.VELOCIDADES[self.aj["velocidad"]])
        self.vista.contraste = self.aj["contraste"]
        self.vista.personaje.con_sombrero = self.aj["sombrero"]

    def decir(self, clave):
        """Voz guía + subtítulo en pantalla (la información nunca depende solo del sonido)."""
        texto = self.sonido.voz(clave)
        self.vista.subtitulo(texto, time.monotonic())

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

    # -------------------------------------------------------------- estados
    def cambiar_estado(self, nuevo, sel=0):
        self.estado = nuevo
        self.sel = sel
        # El gesto que provocó el cambio sigue en la mano: se "bloquea" hasta que el jugador
        # cambie de gesto, para que no dispare otra acción en la nueva pantalla.
        self.gesto_bloqueado = self.control.estable
        musica = {Estado.JUGANDO: "juego", Estado.PAUSA: "juego", Estado.CALIBRACION: "juego",
                  Estado.GANASTE: None, Estado.PERDISTE: None}.get(nuevo, "menu")
        self.sonido.musica(musica)

    def iniciar_partida(self, ahora):
        self.lab.reiniciar()
        self.vista.jugador_reiniciado()
        self.tiempo_jugado = 0.0
        self.vidas = self.dificultad["vidas"]
        self.t_ultimo_choque = -10.0
        self.t_sonar = ahora + 1.0
        self.cambiar_estado(Estado.JUGANDO)

    def volver_menu(self, opcion="jugar"):
        self.cambiar_estado(Estado.MENU, OPCIONES_MENU.index(opcion))
        self.decir(opcion)

    def mover_seleccion(self, gesto, total, eje="vertical"):
        paso = {Gesto.ARRIBA: -1, Gesto.ABAJO: 1, Gesto.IZQUIERDA: -1, Gesto.DERECHA: 1}[gesto]
        self.sel = (self.sel + paso) % total
        self.sonido.efecto("seleccionar")

    # ----------------------------------------------------------- acciones
    def manejar(self, gesto, ahora):
        """Ejecuta la acción del gesto confirmado. Devuelve False si hay que salir."""
        if gesto == Gesto.CUERNOS:
            return False
        e = self.estado
        if e == Estado.MENU:
            if gesto in VERTICALES:
                self.mover_seleccion(gesto, len(OPCIONES_MENU))
                self.decir(OPCIONES_MENU[self.sel])
            elif gesto == Gesto.PALMA:
                self.sonido.efecto("confirmar")
                opcion = OPCIONES_MENU[self.sel]
                if opcion == "jugar":
                    if self.calibrado:
                        self.iniciar_partida(ahora)
                        self.decir("comenzar")
                    else:
                        self.cambiar_estado(Estado.CALIBRACION)
                        self.decir("prueba")
                elif opcion == "dificultad":
                    self.cambiar_estado(Estado.DIFICULTAD, C.ORDEN_DIFICULTADES.index(self.aj["dificultad"]))
                    self.decir(self.aj["dificultad"])
                elif opcion == "personaje":
                    archivos = [a for a, _ in self.personajes]
                    self.cambiar_estado(Estado.PERSONAJE, archivos.index(self.aj["personaje"]))
                    self.decir("elige_personaje")
                elif opcion == "configuracion":
                    self.cambiar_estado(Estado.CONFIG)
                    self.decir(FILAS_CONFIG[0])
                elif opcion == "salir":
                    return False
        elif e == Estado.DIFICULTAD:
            if gesto in HORIZONTALES:
                self.mover_seleccion(gesto, len(C.ORDEN_DIFICULTADES))
                self.decir(C.ORDEN_DIFICULTADES[self.sel])
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
                self.decir(FILAS_CONFIG[self.sel])
            elif gesto in HORIZONTALES:
                self.cambiar_valor(fila, 1 if gesto == Gesto.DERECHA else -1)
            elif gesto == Gesto.PUNO or (gesto == Gesto.PALMA and fila == "regresar"):
                AJ.guardar(self.aj)
                self.sonido.efecto("regresar")
                self.volver_menu("configuracion")
            elif gesto == Gesto.PALMA and fila in ("sombrero", "contraste"):
                self.cambiar_valor(fila, 1)
        elif e == Estado.CALIBRACION:
            if gesto in DIRECCIONALES:
                self.flecha, self.t_flecha, self.ya_practico = gesto.value, ahora, True
                self.sonido.efecto("paso")
            elif gesto == Gesto.PALMA:
                self.calibrado = True
                self.sonido.efecto("confirmar")
                self.iniciar_partida(ahora)
                self.decir("comenzar")
            elif gesto == Gesto.PUNO:
                self.volver_menu("jugar")
        elif e == Estado.JUGANDO:
            if gesto in DIRECCIONALES:
                self.mover_jugador(gesto, ahora)
            elif gesto == Gesto.PALMA:
                self.sonido.efecto("confirmar")
                self.cambiar_estado(Estado.PAUSA)
                self.decir("pausa")
            elif gesto == Gesto.PUNO:
                self.iniciar_partida(ahora)
                self.vista.avisar("Laberinto reiniciado", ahora)
                self.decir("reiniciar")
        elif e == Estado.PAUSA:
            if gesto in VERTICALES:
                self.mover_seleccion(gesto, len(OPCIONES_PAUSA))
                self.decir(OPCIONES_PAUSA[self.sel])
            elif gesto == Gesto.PALMA or gesto == Gesto.PUNO:
                opcion = "reiniciar" if gesto == Gesto.PUNO else OPCIONES_PAUSA[self.sel]
                self.sonido.efecto("confirmar")
                if opcion == "continuar":
                    self.cambiar_estado(Estado.JUGANDO)
                    self.decir("continuar")
                elif opcion == "reiniciar":
                    self.iniciar_partida(ahora)
                    self.vista.avisar("Laberinto reiniciado", ahora)
                    self.decir("reiniciar")
                else:
                    self.volver_menu("jugar")
        elif e in (Estado.GANASTE, Estado.PERDISTE):
            if gesto == Gesto.PUNO:
                self.iniciar_partida(ahora)
                self.decir("comenzar")
            elif gesto == Gesto.PALMA:
                self.volver_menu("jugar")
        return True

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
        elif fila in ("sombrero", "contraste"):
            aj[fila] = not aj[fila]
        else:
            return
        self.aplicar_ajustes()
        self.sonido.efecto("seleccionar")
        if fila == "efectos":
            self.sonido.efecto("paso")      # para escuchar cómo quedó el volumen

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
        if self.vidas is None:
            self.vista.avisar("¡Choque!", ahora)
            return
        if ahora - self.t_ultimo_choque < C.GRACIA_CHOQUE:
            return                               # periodo de gracia: no se pierde otra vida
        self.t_ultimo_choque = ahora
        self.vidas -= 1
        if self.vidas <= 0:
            self.terminar(ganaste=False)
        else:
            self.sonido.efecto("vida_menos")
            self.vista.avisar(f"¡Choque! Te quedan {self.vidas} vida{'s' if self.vidas > 1 else ''}", ahora)
            self.decir(f"vidas_{min(self.vidas, 2)}")

    def terminar(self, ganaste):
        if ganaste:
            clave = self.aj["dificultad"]
            anterior = self.aj["records"].get(clave)
            self.nuevo_record = anterior is None or self.tiempo_jugado < anterior
            if self.nuevo_record:
                self.aj["records"][clave] = round(self.tiempo_jugado, 1)
                AJ.guardar(self.aj)
            self.cambiar_estado(Estado.GANASTE)
            self.sonido.efecto("ganar")
            self.decir("record" if self.nuevo_record and anterior is not None else "ganaste")
        else:
            self.cambiar_estado(Estado.PERDISTE)
            self.sonido.efecto("perder")
            self.decir("perdiste")

    # ------------------------------------------------------- cada fotograma
    def actualizar(self, lectura, dt, ahora):
        """Lógica continua: tiempo, sonar, avisos de mano y sonidos de 'cargando'."""
        if self.estado == Estado.JUGANDO:
            self.tiempo_jugado += dt
            if self.sonar_activo() and ahora >= self.t_sonar:
                fraccion = min(1.0, self.distancia_meta() / self.max_dist)     # 1 = lejos, 0 = cerca
                nivel = min(C.SONAR_NIVELES - 1, int((1 - fraccion) * C.SONAR_NIVELES))
                self.sonido.efecto(f"sonar_{nivel}", volumen=0.7)
                self.t_sonar = ahora + C.SONAR_INTERVALO_CERCA + \
                    (C.SONAR_INTERVALO_LEJOS - C.SONAR_INTERVALO_CERCA) * fraccion
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
        self.detector.detener()
        pygame.quit()

    # ------------------------------------------------------------ dibujo
    def leyenda(self):
        """Filas (gesto, segundos, acción) para el panel de ayuda de la pantalla actual."""
        acciones = ACCIONES[self.estado]
        filas = []
        dur = self.control.duraciones
        if Gesto.ARRIBA in acciones and Gesto.IZQUIERDA in acciones:
            if acciones[Gesto.ARRIBA] == acciones[Gesto.IZQUIERDA]:
                filas.append(("Índice (4 dir.)", dur[Gesto.ARRIBA], acciones[Gesto.ARRIBA]))
            else:
                filas.append(("Índice arriba/abajo", dur[Gesto.ARRIBA], acciones[Gesto.ARRIBA]))
                filas.append(("Índice izq./der.", dur[Gesto.IZQUIERDA], acciones[Gesto.IZQUIERDA]))
        elif Gesto.ARRIBA in acciones:
            filas.append(("Índice arriba/abajo", dur[Gesto.ARRIBA], acciones[Gesto.ARRIBA]))
        elif Gesto.IZQUIERDA in acciones:
            filas.append(("Índice izq./der.", dur[Gesto.IZQUIERDA], acciones[Gesto.IZQUIERDA]))
        for gesto in (Gesto.PALMA, Gesto.PUNO, Gesto.CUERNOS):
            if gesto in acciones:
                filas.append((NOMBRE_CORTO[gesto], dur[gesto], acciones[gesto]))
        return filas

    def info_gesto(self, ahora):
        """(acción, progreso, nota) del gesto estable para la barra de 'sostener'."""
        estable = self.control.estable
        if estable == self.gesto_bloqueado and estable in ACCIONES[self.estado]:
            return None, None, "Cambia de gesto para volver a usarlo"
        accion = ACCIONES[self.estado].get(estable)
        if accion is None:
            return None, None, None
        if estable in DIRECCIONALES and self.estado in (Estado.JUGANDO, Estado.CALIBRACION):
            accion = f"{accion} {estable.value.lower()}"
        return accion, self.control.progreso(ahora), None

    def valor_config(self, fila):
        aj = self.aj
        if fila in ("musica", "efectos", "voz"):
            return int(aj[fila])
        if fila in ("sombrero", "contraste"):
            return "Sí" if aj[fila] else "No"
        if fila == "regresar":
            return None
        return aj[fila]

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
                         "personaje": dict(self.personajes)[self.aj["personaje"]]}.get(clave)
                etiqueta = {"jugar": "JUGAR", "dificultad": "DIFICULTAD", "personaje": "PERSONAJE",
                            "configuracion": "CONFIGURACIÓN", "salir": "SALIR"}[clave]
                opciones.append((etiqueta, valor))
            v.dibujar_menu(opciones, self.sel, prog_sel, lectura, estable, cam, ahora)
        elif e == Estado.DIFICULTAD:
            v.dibujar_dificultad(C.ORDEN_DIFICULTADES, self.sel, prog_sel, self.aj["records"],
                                 lectura, estable, cam)
        elif e == Estado.PERSONAJE:
            v.dibujar_personajes(self.personajes, self.sel, prog_sel, lectura, estable, cam, ahora)
        elif e == Estado.CONFIG:
            nombres = {"musica": "Música", "efectos": "Efectos", "voz": "Voz guía",
                       "velocidad": "Velocidad de gestos", "sonar": "Sonar a la salida",
                       "sombrero": "Sombrero", "contraste": "Alto contraste", "regresar": "Regresar"}
            filas = [(nombres[f], self.valor_config(f)) for f in FILAS_CONFIG]
            v.dibujar_configuracion(filas, self.sel, prog_sel, lectura, estable, cam)
        else:
            v.dibujar_fondo()
            vidas = (self.vidas, self.dificultad["vidas"]) if self.dificultad["vidas"] else None
            v.dibujar_barra_superior(e.value, self.tiempo_jugado, self.dificultad["nombre"],
                                     vidas if e != Estado.CALIBRACION else None)
            datos = dict(lectura=lectura, estable=estable, progreso=progreso, accion=accion, nota=nota,
                         leyenda=self.leyenda(), estado_camara=cam)
            if e == Estado.CALIBRACION:
                flecha = self.flecha if ahora - self.t_flecha < 0.6 else None
                v.dibujar_calibracion(flecha_practica=flecha, ya_practico=self.ya_practico, **datos)
            else:
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
        v.dibujar_subtitulo(ahora)
        v.presentar()


if __name__ == "__main__":
    App().ejecutar()
