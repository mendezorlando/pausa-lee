#!/usr/bin/env python3
"""Imprime el nombre de archivo del handoff de /pausa, derivado del titulo
de la conversacion actual mas la fecha de hoy: `Titulo-2026-08-24.md`.

La fecha va en el nombre para que un hilo pausado varios dias deje un
handoff por dia en vez de pisar el anterior. Cuando hay varios del mismo
hilo, /lee los lista con su fecha y elige el usuario.

El titulo no esta en el contexto del modelo: vive en el transcript, en
registros `{"type":"custom-title","customTitle":...}` y su gemelo
`ai-title`. La sesion actual se identifica por CLAUDE_CODE_SESSION_ID,
que Claude Code exporta al entorno de Bash.

Sale siempre con 0 e imprime siempre una linea. Si no puede resolver el
titulo imprime DESCONOCIDO, para que el comando decida en vez de escribir
un archivo con nombre inventado.
"""
import os, sys, json, re, glob, time, subprocess, importlib.util
from datetime import datetime

MAX = 49          # 60 menos el sufijo de fecha
FECHA = re.compile(r"-\d{4}-\d{2}-\d{2}$")
RAIZ = os.path.expanduser("~/.claude/projects")
LISTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lista-handoffs.py")
ESPERA = 1.5       # s: tope de espera a que aparezca el .jsonl de la sesion
INTERVALO = 0.05
SESIONES = os.path.expanduser("~/.claude/sessions")
UUID = re.compile(r"[0-9a-fA-F-]{36}")


def slug(s):
    s = s.strip().replace("/", "-").replace("\\", "-")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^\w.\-]", "", s, flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-._")
    if s.lower().endswith(".md"):
        s = s[:-3].strip("-._")
    s = FECHA.sub("", s)   # si el titulo ya trae fecha, no la duplicamos
    return s[:MAX].strip("-._")


def _sid_por_proceso():
    """El sessionId subiendo por el arbol de procesos, o "".

    Claude Code deja `~/.claude/sessions/<pid>.json` con `{sessionId, cwd,
    entrypoint, ...}` desde que arranca el proceso, mucho antes de que exista
    el `.jsonl` de la conversacion. Subimos por NUESTROS padres hasta dar con
    el proceso que nos lanzo, asi que esto identifica, no adivina: por la
    ascendencia solo se llega al Claude propio.

    Hace falta porque `CLAUDE_CODE_SESSION_ID` no siempre llega a la
    inyeccion `!` de un comando. El 26/08/2026 tres `/lee` seguidos desde
    otras conversaciones dieron «no se pudo identificar la sesion» teniendo
    su `.jsonl` en disco: sin variable no habia por donde empezar.
    """
    pid = os.getpid()
    for _ in range(8):
        try:
            with open(os.path.join(SESIONES, f"{pid}.json"), encoding="utf-8") as f:
                sid = json.load(f).get("sessionId")
            if isinstance(sid, str) and UUID.fullmatch(sid):
                return sid
        except Exception:
            pass
        try:
            r = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)],
                               capture_output=True, text=True, timeout=2)
            pid = int(r.stdout.strip())
        except Exception:
            return ""
        if pid <= 1:
            return ""
    return ""


def sesion():
    """El id de ESTA sesion: la variable de entorno si esta, el arbol si no."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    return sid if UUID.fullmatch(sid or "") else _sid_por_proceso()


def transcript(sid=None):
    """El .jsonl de ESTA sesion, o None. Nunca el de otra.

    Aqui habia un respaldo que devolvia el .jsonl mas reciente del proyecto,
    y era una mina. En el primer turno el archivo propio tarda unas decimas
    en aparecer, y el respaldo entregaba entonces el de la sesion ANTERIOR,
    con su titulo. El 26/08/2026 una sesion —«Auditoria de desperdicio de
    tokens»— abrio por eso el handoff de «Sistema de reservas del hotel», sin
    preguntar, porque /lee con HANDOFFS: 1 no pregunta. Un minuto antes
    otra sesion habia resuelto bien: misma entrada, distinto resultado, que es
    exactamente lo que se veia como comportamiento erratico.

    Contra la carrera se espera al archivo, que es cuestion de decimas. Sin
    sesion identificable se devuelve None: /lee lista todo y /pausa escribe
    DESCONOCIDO. Callar es correcto; adivinar el hilo de otro, no.
    """
    sid = sid or sesion()
    if not sid:
        return None
    patron = os.path.join(RAIZ, "*", sid + ".jsonl")
    limite = time.time() + ESPERA
    while True:
        hits = glob.glob(patron)
        if hits:
            return hits[0]
        if time.time() >= limite:
            return None
        time.sleep(INTERVALO)


def titulo(path):
    custom = ai = ""
    with open(path, errors="replace") as f:
        for l in f:
            if '"custom-title"' not in l and '"ai-title"' not in l:
                continue
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("customTitle"):
                custom = d["customTitle"]
            elif d.get("aiTitle"):
                ai = d["aiTitle"]
    return custom or ai


def carpeta(t):
    """La carpeta donde ya vive este hilo, o "" para el directorio de trabajo.

    Un hilo se muda arrastrando sus handoffs: si los suyos estan en
    OPTIMIZACION/, el proximo /pausa escribe ahi tambien. Manda el mas
    reciente del hilo, no el que mejor puntue, porque durante una mudanza
    hay handoffs del mismo hilo en las dos carpetas.

    Reusa el emparejador de lista-handoffs.py para que "mismo hilo"
    signifique lo mismo en /pausa y en /lee. El import va aqui dentro y no
    arriba: lista-handoffs importa a este modulo, y a nivel de modulo se
    morderian la cola.
    """
    try:
        spec = importlib.util.spec_from_file_location("lista_handoffs", LISTA)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        datos = {}
        for f in m.candidatos():
            ok, h1 = m.analiza(f)
            if ok:
                datos[f] = h1
        hilo = m.del_hilo(t, sorted(datos, key=m.mtime, reverse=True), datos)
        return os.path.dirname(max(hilo, key=m.mtime)) if hilo else ""
    except Exception:
        return ""


def main():
    try:
        p = transcript()
        t = titulo(p) if p else ""
        s = slug(t)
    except Exception:
        t = s = ""
    if not s:
        print("DESCONOCIDO")
        return
    hoy = datetime.now().strftime("%Y-%m-%d")
    print(os.path.join(carpeta(t), f"{s}-{hoy}.md"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # La promesa del docstring es "imprime siempre una linea". Si no sale
        # ninguna, /pausa se queda con NOMBRE POR CONVERSACION vacio, que no
        # es DESCONOCIDO ni es una ruta: es la rama que nadie escribio.
        print("DESCONOCIDO")
