"""
voz.py — Lector de voz en vivo (tipo TalkBack) con la voz de Windows.

Abre UNA sola vez un proceso de PowerShell que carga System.Speech (incluido en Windows,
sin internet) y se queda esperando frases. Cada vez que el juego llama a `decir(texto)`
le manda la frase por su entrada estándar y Windows la lee en voz alta al momento.
Así se puede leer CUALQUIER texto (opciones, valores, descripciones, vidas, tiempos...),
no solo frases grabadas de antemano.

Si no es Windows, o PowerShell falla, `disponible` queda en False y el juego usa los audios
de assets/voces/ como respaldo.
"""
import base64
import subprocess
import sys
import threading

# Script de PowerShell: elige una voz en español y lee cada línea que recibe.
#   "#vol N"  -> volumen 0-100      "#vel N" -> velocidad -10..10      "#callar" -> detener
_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$entrada = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding($false)))
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToDefaultAudioDevice()
$v = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'es*' } | Select-Object -First 1
if ($v) { $s.SelectVoice($v.VoiceInfo.Name); Write-Output ('LISTA ' + $v.VoiceInfo.Name) }
else { Write-Output ('LISTA-SIN-ESPANOL ' + $s.Voice.Name) }
$s.Rate = 1
while ($true) {
    $l = $entrada.ReadLine()
    if ($l -eq $null) { break }
    if ($l.StartsWith('#vol ')) { $s.Volume = [int]$l.Substring(5); continue }
    if ($l.StartsWith('#vel ')) { $s.Rate = [int]$l.Substring(5); continue }
    $s.SpeakAsyncCancelAll()
    if ($l -eq '#callar' -or $l.Length -eq 0) { continue }
    [void]$s.SpeakAsync($l)
}
"""


class VozSistema:
    def __init__(self):
        self.disponible = False      # True cuando PowerShell confirmó que la voz está lista
        self.nombre_voz = ""
        self.en_espanol = False
        self._proc = None
        self._lock = threading.Lock()
        if sys.platform != "win32":
            return
        try:
            codificado = base64.b64encode(_SCRIPT.encode("utf-16-le")).decode("ascii")
            self._proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-EncodedCommand", codificado],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, ValueError) as e:
            print(f"[Voz] No se pudo iniciar la voz de Windows: {e}")
            return
        threading.Thread(target=self._leer_salida, daemon=True).start()
        threading.Thread(target=self._leer_errores, daemon=True).start()

    def _leer_salida(self):
        for linea in self._proc.stdout:
            texto = linea.decode("utf-8", "replace").strip()
            if texto.startswith("LISTA"):
                self.en_espanol = not texto.startswith("LISTA-SIN-ESPANOL")
                self.nombre_voz = texto.split(" ", 1)[1] if " " in texto else ""
                self.disponible = True
                print(f"[Voz] Lector de voz listo: {self.nombre_voz}")
                if not self.en_espanol:
                    print("[Voz] AVISO: no hay voz en español instalada. Instálala en Configuración de "
                          "Windows > Hora e idioma > Voz > Agregar voces > Español.")

    def _leer_errores(self):
        for linea in self._proc.stderr:
            texto = linea.decode("utf-8", "replace").strip()
            if texto:
                print(f"[Voz] PowerShell: {texto}")

    def _enviar(self, linea):
        if not self._proc or self._proc.poll() is not None:
            self.disponible = False
            return
        try:
            with self._lock:
                self._proc.stdin.write((linea.replace("\n", " ").replace("\r", " ") + "\n").encode("utf-8"))
                self._proc.stdin.flush()
        except (OSError, ValueError):
            self.disponible = False

    def decir(self, texto):
        """Lee `texto` en voz alta. Interrumpe lo que se estaba diciendo."""
        if self.disponible and texto:
            self._enviar(texto)

    def callar(self):
        if self.disponible:
            self._enviar("#callar")

    def volumen(self, valor):
        """0-100."""
        if self._proc:
            self._enviar(f"#vol {int(max(0, min(100, valor)))}")

    def cerrar(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                self._proc.kill()
