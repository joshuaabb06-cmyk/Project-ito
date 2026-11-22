# Project-ito

Juego de laberinto controlado **solo con gestos de la mano**, detectados con la cámara
(MediaPipe + OpenCV) y dibujado con Pygame. Durante la ejecución **no se usa el teclado para nada**:
ni para mover, iniciar, pausar, reiniciar o salir.

El laberinto es el de la imagen `Laberinto IHC.jpeg` (8×8 casillas), convertido a una matriz
de 0 (camino) y 1 (pared). Tiene **tema vaquero** (cercas de madera, desierto y estrella de sheriff),
menú inicial, 4 dificultades, selección de personaje, música, efectos y voz guía.

**La cámara nunca se muestra en pantalla**: solo se usa para detectar la mano. En su lugar se ve un
ícono del gesto detectado y un puntito que indica dónde está la mano dentro del encuadre.

---

## Requisitos

- Windows 10/11 con cámara web.
- **Python 3.14** (probado con 3.14.0). MediaPipe 1.0.1 ya tiene versión para 3.14.
- Internet **solo la primera vez** (para instalar paquetes y descargar el modelo de la mano).

> **Nota sobre Pygame:** el paquete `pygame` clásico no tiene versión para Python 3.14, así que usamos
> **`pygame-ce`** (la versión comunitaria). En el código se sigue escribiendo `import pygame`.

## Instalación (una sola vez)

En PowerShell, dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe descargar_modelo.py
```

`descargar_modelo.py` baja `assets/modelos/hand_landmarker.task` (~8 MB). MediaPipe 1.x ya no trae
el modelo incluido. Después el juego funciona **sin internet**.

### Voz y sonido

- **Lector de voz (tipo TalkBack):** el juego lee en voz alta cada pantalla, opción, valor,
  descripción y aviso (vidas, choques, pistas del tutorial) con la **voz de Windows en vivo**, sin
  internet y sin pasos extra. Mientras habla, la música baja de volumen. Se puede apagar en
  **Configuración → Lector de voz**. Todo lo que dice también sale como **subtítulo**.
- Si la voz de Windows no arranca, se usan los audios de `assets/voces/` como respaldo
  (`generar_voces.py` los crea, o graben los suyos con los nombres de `assets/voces/LEEME.txt`).
- Si la voz se oye en inglés: instala una voz en español en Windows (Configuración > Hora e idioma >
  Voz > Agregar voces > Español).
- **Música y efectos** se generan con código (`generar_sonidos.py`, con numpy): son 100% originales,
  así que no hay problemas de derechos de autor. Ya vienen generados en `assets/sonidos/`.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe main.py              # el juego completo
.\.venv\Scripts\python.exe demo_automatica.py   # etapa 1: el laberinto se resuelve solo (sin cámara)
.\.venv\Scripts\python.exe prueba_gestos.py     # etapa 2: solo la detección de gestos (para calibrar)
```

(Si activas el entorno con `.\.venv\Scripts\Activate.ps1`, basta con `python main.py`. Si PowerShell
bloquea el script de activación, usa la forma de arriba, que no necesita activar nada.)

---

## Gestos

| Gesto | Sostener | En el juego | En los menús |
|---|---|---|---|
| **Dedo índice** (el que está junto al pulgar) apuntando ↑ ↓ ← →, demás dedos doblados | 0.5 s | Avanza **una casilla**. Si lo sostienes, avanza otra cada 0.5 s | Mover la selección / cambiar un valor |
| **Palma abierta** (4 dedos extendidos) | 1 s | **Pausar** | **Confirmar** |
| **Puño** | 2 s | **Reiniciar** | **Regresar** (y guardar) |
| **Cuernos** (índice + meñique) | 3 s | **Salir** del programa | **Salir** del programa |

- El **pulgar se ignora** en todos los gestos: es el dedo que MediaPipe detecta peor.
- Si apuntas en **diagonal**, no pasa nada (zona muerta de ±30° alrededor de cada eje).
- La cámara funciona como **espejo**: si apuntas a tu derecha, el personaje va a la derecha.
- Los gestos de control (palma, puño, cuernos) se disparan **una sola vez**. Para repetirlos hay que
  cambiar de gesto o bajar la mano. Mientras se sostienen suena un "tic" que sube de tono.
- La velocidad de los gestos se puede cambiar en **Configuración** (Lento / Normal / Rápido).

## Pantallas

1. **Menú inicial:** Jugar, Tutorial, Dificultad, Personaje, Configuración y Salir.
   **Tutorial** (se abre solo la primera vez que juegas y se puede repetir desde el menú):
   8 pasos guiados con voz: cómo colocar la mano frente a la cámara (dibujo con la distancia),
   índice arriba / abajo / izquierda / derecha, palma, puño y cuernos. Cada paso muestra **"ASÍ:"**
   (dibujo del gesto correcto) y **"TÚ:"** (lo que la cámara ve ahora, con ✓ o ✗) y da pistas
   concretas ("dobla los demás dedos: deja solo el índice"). Puño 2 s salta el tutorial.
2. **Dificultad** (la ruta del laberinto es la misma; cambian las reglas):

   | Nivel | Reglas |
   |---|---|
   | Explorador | Nunca pierdes. Huellas marcan los siguientes 3 pasos de la ruta más corta |
   | Sheriff | 3 vidas. Cada choque quita una |
   | Forajido | 1 vida: si chocas, pierdes |
   | Noche sin luna | Solo ves alrededor del personaje (farol). Un sonar te guía. 3 vidas |

   Después de un choque hay **1 s de gracia** sin perder otra vida, y **mantener** una dirección
   hasta topar con la cerca no cuenta como choque (solo cuenta si intentas el movimiento a propósito).
   Se guarda el **récord** de tiempo de cada dificultad.
3. **Personaje:** cada PNG con fondo transparente que pongan en `assets/personajes/` aparece solo.
   El sombrero vaquero se coloca automáticamente en la parte más alta de la imagen (se puede apagar).
4. **Configuración:** lector de voz sí/no, volumen de voz, música y efectos por separado, velocidad de gestos, sonar
   (solo de noche / siempre / nunca), sombrero y alto contraste. Se guarda en `ajustes_usuario.json`.
5. **Íconos de gestos:** las direcciones se muestran con una **mano apuntando con el índice**
   (con la punta dorada) en el panel, las leyendas y el pie de los menús.
6. **Juego:** laberinto + panel "TU MANO" con el gesto detectado, barra de carga, encuadre y gestos
   disponibles. **Pausa** (Continuar / Reiniciar / Menú), **¡Ganaste!** y **¡Perdiste!**
7. **Error de cámara / modelo:** se **reintenta sola cada 3 s**.

La X de la ventana (con el mouse) queda como salida de emergencia.

### Sonido

- Música en bucle para el menú y para el juego (estilo western: guitarra y silbido).
- Efectos: pasos, choque contra la cerca (se oye del lado de la pared), vida perdida, ganar, perder
  y sonidos de menú.
- **Sonar:** un "bip" más rápido y más agudo mientras más cerca estás de la salida. Tiene su
  equivalente visual en el panel (barra "cercanía a la salida").

---

## Estructura

```
Proyect-ito/
├── main.py              # Punto de entrada: máquina de estados (menús, dificultad, juego, pausa...)
├── config.py            # TODOS los parámetros ajustables + la matriz del laberinto
├── gestos.py            # Hilo de cámara + MediaPipe HandLandmarker + clasificación de gestos
├── control.py           # Anti-rebote: votación entre fotogramas y temporizadores de "sostener"
├── laberinto.py         # Lógica pura: matriz, colisiones, meta, BFS
├── juego.py             # Todo el dibujo con Pygame (menús, laberinto, personaje, panel, pantallas)
├── tema.py              # Piezas del tema vaquero (madera, cactus, sombrero, íconos de gestos)
├── sonido.py            # Música, efectos, paneo y voz guía (pygame.mixer)
├── voz.py               # Lector de voz en vivo con la voz de Windows (System.Speech)
├── tutorial.py          # Pasos, textos y pistas del tutorial
├── ajustes.py           # Guarda/carga ajustes_usuario.json (volúmenes, dificultad, récords...)
├── generar_sonidos.py   # Crea la música y los efectos con código (numpy)
├── generar_voces.py     # (Opcional) audios de respaldo de la voz guía
├── demo_automatica.py   # Etapa 1: demo sin cámara ni teclado
├── prueba_gestos.py     # Etapa 2: ventana de prueba de gestos
├── descargar_modelo.py  # Descarga el modelo de MediaPipe
├── assets/
│   ├── personajes/      # Un PNG por personaje (si está vacía, se dibuja un dino de respaldo)
│   ├── fuentes/         # Rye-Regular.ttf (fuente western, licencia SIL OFL)
│   ├── sonidos/         # Música y efectos generados
│   ├── voces/           # Voz guía (generada o grabada por el equipo)
│   └── modelos/hand_landmarker.task
├── Laberinto IHC.jpeg   # Imagen original del laberinto
└── requirements.txt
```

## Configuración (`config.py`)

| Parámetro | Para qué |
|---|---|
| `CAMARA_INDICE` | 0 = cámara integrada; 1, 2… para webcams USB |
| `CAMARA_BACKEND` | `"msmf"` (30 FPS en pruebas) o `"dshow"` (abre más rápido, pero dio 10 FPS) |
| `TIEMPO_MOVER`, `TIEMPO_REPETICION`, `REPETIR_MOVIMIENTO` | Anti-rebote del movimiento |
| `TIEMPO_INICIAR_PAUSAR`, `TIEMPO_REINICIAR`, `TIEMPO_SALIR` | Cuánto sostener cada gesto de control |
| `UMBRAL_DEDO_EXTENDIDO` | Súbelo si detecta dedos "extendidos" que están doblados; bájalo en el caso contrario |
| `TOLERANCIA_ANGULO` | Tamaño de la zona aceptada para cada dirección (grados) |
| `VENTANA_VOTACION`, `VOTOS_MINIMOS` | Filtro de parpadeos |
| `LABERINTO`, `INICIO`, `META`, `PASO` | El laberinto y cómo se avanza |
| `TAMANO_CASILLA`, `GROSOR_PARED`, `PANTALLA_COMPLETA` | Tamaño en pantalla (`True` para el proyector) |
| `DIFICULTADES`, `GRACIA_CHOQUE`, `RADIO_NIEBLA`, `PASOS_PISTA` | Reglas de cada nivel |
| `VELOCIDADES` | Tiempos de Lento / Normal / Rápido |
| `SONAR_*` | Ritmo del sonar |
| `COLOR_*` | Paleta del tema vaquero y del alto contraste |

### ¿Cómo se representa el laberinto?

La imagen tiene 8×8 casillas con paredes **delgadas**. Se convierte a una matriz de 17×17
(2·8+1). Las posiciones **impares** son casillas y las **pares** son las paredes (1) o huecos (0)
entre casillas. Por eso `PASO = 2`: cada movimiento avanza de una casilla a la siguiente y **revisa
la posición intermedia**. Si ahí hay un 1, es un choque. La ruta más corta tiene 46 casillas.

---

## Derechos de autor

- **Música y efectos:** generados con código por el equipo (`generar_sonidos.py`).
- **Voz:** sintetizada con la voz de Windows o grabada por el equipo.
- **Fuente Rye:** SIL Open Font License 1.1 (`assets/fuentes/OFL-Rye.txt`); se puede incluir libremente.
- **Gráficos del tema** (madera, cactus, sombrero, estrella, íconos de mano): dibujados con figuras de Pygame.
- **Personajes:** usen solo dibujos propios o con licencia libre.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| "No se pudo abrir la cámara" | Cierra Zoom/Teams/la app Cámara. Si tienes varias cámaras, prueba `CAMARA_INDICE = 1`. |
| Tarda unos segundos en ver la cámara | Normal con `msmf` (~4 s). Con `"dshow"` abre más rápido pero da menos FPS. |
| "Falta el modelo de MediaPipe" | Ejecuta `descargar_modelo.py` (necesita internet). |
| No detecta bien la mano | Buena luz de frente (no una ventana detrás), mano a 40-60 cm, palma hacia la cámara. |
| No se oye nada | Revisa el volumen en Configuración y en Windows. Si faltan efectos, ejecuta `generar_sonidos.py`. |
| No se oye la voz | Revisa que **Lector de voz** esté en "Sí" y lee la consola: debe decir `[Voz] Lector de voz listo`. Si dice otra cosa, cópiala y revísenla. |
| La voz se oye en inglés | Instala una voz en español (Configuración de Windows > Hora e idioma > Voz). |
| Confunde gestos | Abre `prueba_gestos.py`: muestra qué dedos ve extendidos y el ángulo del índice. Ajusta `UMBRAL_DEDO_EXTENDIDO`. |

### Lista para el día de la presentación

- [ ] Modelo descargado (`assets/modelos/hand_landmarker.task` existe).
- [ ] Probar la cámara y la luz del salón con `prueba_gestos.py`.
- [ ] Fondo detrás de la mano sin otras manos o personas cerca.
- [ ] `PANTALLA_COMPLETA = True` si se proyecta.
- [ ] Cerrar apps que usen la cámara.
- [ ] Bocinas conectadas y, al abrir el juego, la consola dice `[Voz] Lector de voz listo`.
