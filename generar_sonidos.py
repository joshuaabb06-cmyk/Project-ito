"""
generar_sonidos.py — Crea TODA la música y los efectos del juego con código (numpy).

Ejecutar una vez:   python generar_sonidos.py
Resultado:          archivos .wav en assets/sonidos/

¿Por qué generarlos? Porque así son 100% originales del equipo: no hay canciones ni efectos
descargados, y por lo tanto no hay problemas de derechos de autor.

Técnicas usadas (todas son síntesis básica de audio):
  * Karplus-Strong: simula una cuerda pulsada (guitarra) con ruido + un filtro con retardo.
  * Senoidales con vibrato: el "silbido" típico de las películas del viejo oeste.
  * Ruido filtrado y senoidales que decaen: golpes de madera, pasos y campanitas.
"""
import os
import wave

import numpy as np

import config as C

SR = 44100                     # muestras por segundo
rng = np.random.default_rng(7)  # semilla fija: siempre se generan los mismos sonidos


def midi(n):
    """Número de nota MIDI -> frecuencia en Hz (69 = La 440 Hz)."""
    return 440.0 * 2 ** ((n - 69) / 12)


def envolvente(n, ataque=0.005, caida=0.05):
    """Sube al inicio y baja al final para evitar 'clics'."""
    env = np.ones(n)
    a, c = min(n, int(ataque * SR)), min(n, int(caida * SR))
    if a:
        env[:a] = np.linspace(0, 1, a)
    if c:
        env[-c:] *= np.linspace(1, 0, c)
    return env


def paso_bajo(x, alfa):
    """Filtro paso bajo de un polo (suaviza / opaca el sonido). alfa cercano a 0 = más opaco."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alfa * (v - acc)
        y[i] = acc
    return y


# ---------------------------------------------------------------- instrumentos
def cuerda(freq, dur, decaimiento=0.996, brillo=0.5):
    """Guitarra pulsada con el algoritmo de Karplus-Strong (procesado por bloques con numpy)."""
    n = int(dur * SR)
    periodo = max(2, int(SR / freq))
    salida = np.zeros(n + periodo + 1)
    salida[:periodo] = rng.uniform(-1, 1, periodo)
    salida[:periodo] = paso_bajo(salida[:periodo], brillo)
    i = periodo
    while i < n + 1:
        fin = min(i + periodo, n + 1)
        bloque = salida[i - periodo:fin - periodo]
        siguiente = salida[i - periodo + 1:fin - periodo + 1]
        salida[i:fin] = decaimiento * 0.5 * (bloque + siguiente)
        i = fin
    return salida[:n] * envolvente(n, 0.001, 0.03)


def silbido(freq, dur, volumen=1.0):
    """Silbido con vibrato (sube y baja un poquito el tono) y un toque de aire."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vibrato = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.25, 0, 1)
    fase = 2 * np.pi * np.cumsum(freq * vibrato) / SR
    onda = np.sin(fase) + 0.12 * np.sin(2 * fase)
    aire = paso_bajo(rng.normal(0, 1, n), 0.25) * 0.04
    return (onda + aire) * envolvente(n, 0.06, 0.12) * volumen


def bloque_madera(dur=0.08, tono=900):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * tono * t) + 0.5 * np.sin(2 * np.pi * tono * 1.6 * t)) * np.exp(-t * 60)


def campana(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    parciales = [(1, 1.0), (2.01, 0.5), (3.02, 0.25), (4.2, 0.12)]
    onda = sum(a * np.sin(2 * np.pi * freq * k * t) for k, a in parciales)
    return onda * np.exp(-t * 7) * envolvente(n, 0.002, 0.02)


def tono(freq, dur, forma="seno", decaer=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    fase = 2 * np.pi * freq * t
    if forma == "cuadrada":
        onda = np.sign(np.sin(fase)) * 0.5
    elif forma == "sierra":
        onda = 2 * ((freq * t) % 1) - 1
    else:
        onda = np.sin(fase)
    if decaer:
        onda *= np.exp(-t * decaer)
    return onda * envolvente(n, 0.004, 0.03)


def barrido(f0, f1, dur, forma="seno"):
    n = int(dur * SR)
    f = np.linspace(f0, f1, n)
    fase = 2 * np.pi * np.cumsum(f) / SR
    onda = np.sin(fase) if forma == "seno" else 2 * ((np.cumsum(f) / SR) % 1) - 1
    return onda * envolvente(n, 0.005, 0.05)


# ---------------------------------------------------------------------- mezcla
def poner(pista, inicio_s, sonido, volumen=1.0):
    """Suma `sonido` a la pista. Lo que se pasa del final se 'enrolla' al inicio (bucle perfecto)."""
    i = int(inicio_s * SR)
    for k in range(0, len(sonido), len(pista)):
        trozo = sonido[k:k + len(pista)]
        a = (i + k) % len(pista)
        fin = min(len(pista), a + len(trozo))
        pista[a:fin] += trozo[:fin - a] * volumen
        resto = len(trozo) - (fin - a)
        if resto > 0:
            pista[:resto] += trozo[fin - a:] * volumen


def eco(pista, retardo_s=0.28, retro=0.3, mezcla=0.25):
    """Eco circular (respeta el bucle): da sensación de espacio abierto."""
    d = int(retardo_s * SR)
    salida = pista.copy()
    eco_buf = np.roll(pista, d) * mezcla
    for _ in range(4):
        salida += eco_buf
        eco_buf = np.roll(eco_buf, d) * retro
    return salida


def guardar(nombre, x, pico=0.8):
    os.makedirs(C.CARPETA_SONIDOS, exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) or 1.0
    datos = (x / m * pico * 32767).astype(np.int16)
    ruta = os.path.join(C.CARPETA_SONIDOS, f"{nombre}.wav")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(datos.tobytes())
    print(f"  {ruta}  ({len(x) / SR:.1f} s)")


# ---------------------------------------------------------------------- música
ACORDES = {"Am": [57, 60, 64, 69], "G": [55, 59, 62, 67], "F": [53, 57, 60, 65],
           "E": [52, 56, 59, 64], "Dm": [50, 57, 62, 65]}
BAJOS = {"Am": 45, "G": 43, "F": 41, "E": 40, "Dm": 38}


def musica_juego():
    """Galope western en La menor, 100 BPM, 8 compases en bucle (~19 s)."""
    bpm = 100
    b = 60 / bpm
    progresion = ["Am", "Am", "G", "Am", "F", "G", "E", "Am"]
    pista = np.zeros(int(len(progresion) * 4 * b * SR))
    for compas, acorde in enumerate(progresion):
        for tiempo in range(4):
            t0 = (compas * 4 + tiempo) * b
            bajo = BAJOS[acorde] + (7 if tiempo % 2 else 0)                # tónica - quinta
            poner(pista, t0, cuerda(midi(bajo), 0.5, 0.993, 0.3), 0.9)
            for k, nota in enumerate(ACORDES[acorde]):                      # rasgueo "chick"
                poner(pista, t0 + b * 0.5 + k * 0.012, cuerda(midi(nota), 0.25, 0.985, 0.6), 0.28)
            poner(pista, t0, bloque_madera(0.06, 700), 0.12)                # galope de caballo
            poner(pista, t0 + b * 0.75, bloque_madera(0.05, 950), 0.08)
    melodia = [(76, 0, 1.5), (74, 1.5, .5), (72, 2, 1), (69, 3, 1), (72, 4, .5), (74, 4.5, .5), (76, 5, 2),
               (79, 8, 1.5), (76, 9.5, .5), (74, 10, 1), (71, 11, 1), (69, 12, 3),
               (72, 16, 1.5), (69, 17.5, .5), (65, 18, 1), (69, 19, 1), (71, 20, .5), (72, 20.5, .5),
               (74, 21, 2), (76, 24, 1.5), (71, 25.5, .5), (68, 26, 1), (71, 27, 1), (69, 28, 3)]
    for nota, inicio, dur in melodia:
        poner(pista, inicio * b, silbido(midi(nota), dur * b * 0.95), 0.32)
    return eco(pista, b * 0.75, 0.25, 0.18)


def musica_menu():
    """Guitarra con arpegios y silbido lento, 80 BPM, 8 compases (~24 s)."""
    bpm = 80
    b = 60 / bpm
    progresion = ["Am", "Dm", "Am", "E", "Am", "Dm", "E", "Am"]
    pista = np.zeros(int(len(progresion) * 4 * b * SR))
    patron = [0, 2, 1, 3, 2, 1, 3, 2]                 # orden de las cuerdas en el arpegio (corcheas)
    for compas, acorde in enumerate(progresion):
        notas = ACORDES[acorde]
        poner(pista, compas * 4 * b, cuerda(midi(BAJOS[acorde]), 2.2, 0.997, 0.3), 0.8)
        for k, idx in enumerate(patron):
            t0 = (compas * 4 + k * 0.5) * b
            poner(pista, t0, cuerda(midi(notas[idx]), 1.0, 0.994, 0.5), 0.35)
    melodia = [(69, 0, 2), (72, 2, 1), (76, 3, 1), (77, 4, 3), (76, 7, 1), (74, 8, 1), (72, 9, 1),
               (69, 10, 2), (71, 12, 2), (68, 14, 2), (69, 16, 2), (72, 18, 1), (76, 19, 1),
               (81, 20, 2), (77, 22, 2), (76, 24, 1), (74, 25, 1), (71, 26, 2), (69, 28, 4)]
    for nota, inicio, dur in melodia:
        poner(pista, inicio * b, silbido(midi(nota), dur * b * 0.95), 0.42)
    return eco(pista, b * 0.5, 0.35, 0.3)


# --------------------------------------------------------------------- efectos
def efectos():
    sonidos = {}
    # Paso: "clop" de bota sobre tierra (golpe grave + ruido opaco muy corto).
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    golpe = np.sin(2 * np.pi * 120 * t) * np.exp(-t * 55)
    tierra = paso_bajo(rng.normal(0, 1, n), 0.15) * np.exp(-t * 70)
    sonidos["paso"] = golpe + tierra * 1.5
    # Choque: golpe seco contra una cerca de madera.
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    madera = (np.sin(2 * np.pi * 170 * t) + 0.7 * np.sin(2 * np.pi * 410 * t) +
              0.3 * np.sin(2 * np.pi * 980 * t)) * np.exp(-t * 26)
    clic = rng.normal(0, 1, n) * np.exp(-t * 250)
    sonidos["choque"] = madera + clic * 0.8
    # Vida perdida: cuerda que "se desafina" hacia abajo.
    sonidos["vida_menos"] = barrido(440, 180, 0.45) * np.exp(-np.arange(int(0.45 * SR)) / SR * 4)
    # Perder: tres notas que bajan (tipo trombón triste).
    perder = np.zeros(int(1.6 * SR))
    for k, nota in enumerate((62, 61, 60)):
        poner(perder, k * 0.35, paso_bajo(tono(midi(nota - 12), 0.34 if k < 2 else 0.9, "sierra"), 0.2), 1)
    sonidos["perder"] = perder
    # Ganar: fanfarria con guitarra + campanita (La mayor).
    ganar = np.zeros(int(2.2 * SR))
    for k, nota in enumerate((57, 61, 64, 69)):
        poner(ganar, k * 0.12, cuerda(midi(nota), 1.6, 0.996, 0.7), 0.6)
        poner(ganar, k * 0.12, tono(midi(nota + 12), 0.18, "cuadrada", 8), 0.25)
    for k, nota in enumerate((69, 73, 76, 81)):
        poner(ganar, 0.6 + k * 0.1, campana(midi(nota + 12), 1.2), 0.25)
    sonidos["ganar"] = ganar
    # Menús: tic al moverse, "espuela" al confirmar, tic grave al regresar.
    sonidos["seleccionar"] = bloque_madera(0.05, 1300)
    espuela = np.zeros(int(0.5 * SR))
    for k in range(5):
        poner(espuela, k * 0.035, campana(3200 + 300 * (k % 2), 0.3), 0.5 - k * 0.07)
    sonidos["confirmar"] = espuela
    sonidos["regresar"] = bloque_madera(0.07, 600)
    # Cargando (mientras sostienes un gesto): dos tics que suben de tono.
    sonidos["carga_1"] = tono(880, 0.06, "seno", 30)
    sonidos["carga_2"] = tono(1175, 0.06, "seno", 30)
    # Sonar: un bip por nivel; más agudo = más cerca de la salida.
    for nivel in range(C.SONAR_NIVELES):
        freq = 520 * 2 ** (nivel / 4)
        bip = campana(freq, 0.25) * 0.7
        bip[:int(0.08 * SR)] += tono(freq, 0.08) * 0.3
        sonidos[f"sonar_{nivel}"] = bip
    return sonidos


if __name__ == "__main__":
    print("Generando música y efectos originales...")
    guardar("musica_menu", musica_menu(), 0.55)
    guardar("musica_juego", musica_juego(), 0.6)
    picos = {"paso": 0.6, "perder": 0.5, "carga_1": 0.5, "carga_2": 0.5}
    for nombre, onda in efectos().items():
        guardar(nombre, onda * envolvente(len(onda), 0.001, 0.02), picos.get(nombre, 0.8))
    print("Listo.")
