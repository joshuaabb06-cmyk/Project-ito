"""
generar_voces.py — Crea los audios de la voz guía con la voz de Windows (sin internet).

Ejecutar una vez:   python generar_voces.py
Resultado:          archivos .wav en assets/voces/  (uno por frase de sonido.FRASES)

¿Quieren usar SUS PROPIAS voces? Graben cada frase (con el celular o la Grabadora de Windows),
guárdenla en assets/voces/ con el MISMO nombre (por ejemplo "jugar.wav", "pausa.mp3") y listo:
el juego usa lo que haya en la carpeta. Este script NO sobreescribe audios que ya existan,
a menos que lo ejecuten con:   python generar_voces.py --forzar

Usa System.Speech (incluido en Windows) a través de PowerShell. Busca una voz en español;
si no hay, avisa cómo instalarla (Configuración > Hora e idioma > Voz).
"""
import os
import subprocess
import sys

import config as C
from sonido import FRASES


def _ps_texto(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    if sys.platform != "win32":
        print("Este script usa la voz de Windows; ejecútalo en Windows.")
        return
    forzar = "--forzar" in sys.argv
    os.makedirs(C.CARPETA_VOCES, exist_ok=True)
    pendientes = {}
    for clave, texto in FRASES.items():
        existe = any(os.path.exists(os.path.join(C.CARPETA_VOCES, clave + ext))
                     for ext in (".wav", ".ogg", ".mp3"))
        if forzar or not existe:
            pendientes[clave] = texto
    if not pendientes:
        print("Todas las voces ya existen (usa --forzar para regenerarlas).")
        return

    lineas = [
        "Add-Type -AssemblyName System.Speech",
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "$v = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'es*' }"
        " | Select-Object -First 1",
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name); Write-Output ('Voz: ' + $v.VoiceInfo.Name) }",
        "else { Write-Output 'AVISO: no hay voz en espanol instalada; se usara la voz por defecto.' }",
        "$s.Rate = 0",
        "$s.Volume = 100",
    ]
    for clave, texto in pendientes.items():
        ruta = os.path.abspath(os.path.join(C.CARPETA_VOCES, clave + ".wav"))
        lineas.append(f"$s.SetOutputToWaveFile({_ps_texto(ruta)}); $s.Speak({_ps_texto(texto)})")
    lineas.append("$s.SetOutputToNull(); $s.Dispose()")
    script = "; ".join(lineas)

    print(f"Generando {len(pendientes)} frases con la voz de Windows...")
    resultado = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(resultado.stdout.strip())
    if resultado.returncode != 0:
        print("Error de PowerShell:\n" + resultado.stderr.strip())
        return
    if "AVISO" in resultado.stdout:
        print("Para una voz en español: Configuración > Hora e idioma > Voz > Agregar voces > Español.\n"
              "Después ejecuta:  python generar_voces.py --forzar")
    print(f"Listo: audios en {C.CARPETA_VOCES}/")


if __name__ == "__main__":
    main()
