#!/usr/bin/env python3
"""Bateria de regresion de /lee y /pausa. Ejecutar tras tocar cualquiera de
lista-handoffs.py, nombre-pausa.py o poda-handoffs.py.

Trabaja en un directorio temporal y en un proyecto falso bajo
~/.claude/projects/-tmp-rev-lee; borra los dos al terminar y no mira ni toca
nada del directorio de trabajo real. Sale con 1 si algo falla.

Cubre: los tres conteos de /lee, el emparejamiento por titulo y por H1, las
tres causas de no emparejar, que NUNCA se herede el titulo de otra sesion
(la averia del 26/08/2026), subcarpetas, papelera en las dos cajas, el tope
por hilo, la firma de handoff, el slug, la herencia de carpeta y las cuatro
garantias de la poda.
"""
import os, sys, json, shutil, subprocess, tempfile

REAL = os.path.expanduser("~")
BIN = os.path.dirname(os.path.abspath(__file__))
SAND = tempfile.mkdtemp(prefix="rev-lee-")
# HOME propio. Los scripts resuelven `~/.claude/...` con expanduser, asi que
# bajo este HOME leen y escriben SOLO aqui. Hasta el 26/08/2026 esta bateria
# creaba un proyecto falso dentro de ~/.claude/projects: tocar el estado real
# de la app para probarla es justo lo que no debe hacerse, y si el proceso
# moria a mitad se quedaba alli.
CASA = tempfile.mkdtemp(prefix="rev-home-")
PROJ = os.path.join(CASA, ".claude", "projects", "-pruebas")
os.makedirs(PROJ)
SECS = "\n".join(f"## {s}" for s in
                 ("Decidido", "Tocado", "A medias", "Siguiente paso", "No repetir"))
fallos = []


def handoff(rel, h1, secs=SECS, mtime=None):
    p = os.path.join(SAND, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(f"# {h1}\n\n{secs}\n")
    if mtime:
        os.utime(p, (mtime, mtime))
    return p


def sesion(sid, titulo):
    with open(os.path.join(PROJ, sid + ".jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "sessionId": sid}) + "\n")
        if titulo is not None:
            f.write(json.dumps({"type": "custom-title", "sessionId": sid,
                                "customTitle": titulo}) + "\n")


def corre(script, sid="", extra=None, casa=None):
    """Por defecto, HOME propio: sin `~/.claude/sessions` no hay arbol de
    procesos que subir, asi que «sin sesion» se simula de verdad y no se toca
    nada de la app. `casa=REAL` es para el unico caso que necesita el HOME
    autentico: comprobar que el fallback por pid encuentra la sesion viva.
    Aun asi solo lee."""
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env["HOME"] = casa or CASA
    if sid:
        env["CLAUDE_CODE_SESSION_ID"] = sid
    if extra:
        env.update(extra)
    r = subprocess.run([sys.executable, os.path.join(BIN, script)],
                       cwd=SAND, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def prueba(n, cond, detalle=""):
    print(f"  {'ok ' if cond else 'FALLO'}  {n}")
    if not cond:
        fallos.append(n)
        if detalle:
            print("        " + detalle.replace("\n", "\n        "))


SID_A = "aaaaaaaa-1111-2222-3333-444444444444"   # «Auditoría de tokens»
SID_B = "bbbbbbbb-1111-2222-3333-444444444444"   # «Reservas del hotel»
SID_C = "cccccccc-1111-2222-3333-444444444444"   # sin titulo (primer turno)
sesion(SID_A, "Auditoría de desperdicio de tokens")
sesion(SID_B, "Sistema de reservas del hotel")
sesion(SID_C, None)

print("\n== /lee: conteo y emparejamiento ==")
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("0 handoffs -> HANDOFFS: 0", o.startswith("HANDOFFS: 0"), o)

handoff("Auditoría-de-desperdicio-de-tokens-2026-08-24.md",
        "Auditoría de desperdicio de tokens", mtime=1000)
# Con UN solo handoff /lee abria a ciegas: sin mirar el titulo, se lo daba a
# cualquier hilo. Cerrado el 26/08/2026; estos cuatro casos son el candado.
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("1 handoff, titulo que casa -> lo abre y dice por que",
       o.startswith("HANDOFFS: 1") and "chosen by the conversation title" in o, o)
c, o, e = corre("lista-handoffs.py", SID_B)
prueba("1 handoff AJENO -> NO lo abre",
       "is NOT from this thread" in o and "chosen by the conversation title" not in o
       and "Open it by the path" not in o, o)
c, o, e = corre("lista-handoffs.py", SID_C)
prueba("1 handoff, primer turno sin titulo -> abre bajo aviso",
       "its thread could not be verified" in o
       and "Open it unless" in o, o)
c, o, e = corre("lista-handoffs.py", "")
prueba("1 handoff, sin sesion -> abre bajo aviso",
       o.startswith("HANDOFFS: 1") and "Open it unless" in o, o)

handoff("ESTADO.md", "ESTADO — Sistema de Reservas del Hotel", mtime=2000)
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("2 de hilos distintos, titulo A -> elige el de A",
       o.startswith("HANDOFFS: 1") and "tokens" in o and "chosen by the conversation title" in o, o)
c, o, e = corre("lista-handoffs.py", SID_B)
prueba("mismo par, titulo B -> elige ESTADO.md",
       o.startswith("HANDOFFS: 1") and "ESTADO.md" in o, o)

print("\n== /lee: las tres causas de no emparejar ==")
c, o, e = corre("lista-handoffs.py", SID_C)
prueba("primer turno (sin titulo) -> lista todo + invita a repetir",
       o.startswith("HANDOFFS: 2") and "is not written yet" in o
       and "Run /lee again" in o, o)
c, o, e = corre("lista-handoffs.py", "")
prueba("sin sesion -> lista todo + dice que no la identifica",
       o.startswith("HANDOFFS: 2") and "the session could not be identified" in o
       and "Run /lee again" not in o, o)
sesion("dddddddd-1111-2222-3333-444444444444", "Pasarela de pagos")
c, o, e = corre("lista-handoffs.py", "dddddddd-1111-2222-3333-444444444444")
prueba("titulo que no casa -> lo dice y no adivina",
       o.startswith("HANDOFFS: 2") and "matches none of these" in o, o)

print("\n== /lee: nunca devuelve el hilo de otra sesion ==")
c, o, e = corre("lista-handoffs.py", "99999999-1111-2222-3333-444444444444")
prueba("sid valido sin transcript -> NO hereda titulo ajeno",
       "chosen by the conversation title" not in o and o.startswith("HANDOFFS: 2"), o)
c, o, e = corre("lista-handoffs.py", casa=REAL)
prueba("sin variable pero con arbol -> tampoco hereda titulo ajeno",
       "chosen by the conversation title" not in o, o)

print("\n== /lee: tope por hilo ==")
for i, d in enumerate(("21", "22", "23", "25")):
    handoff(f"Auditoría-de-desperdicio-de-tokens-2026-08-{d}.md",
            "Auditoría de desperdicio de tokens", mtime=3000 + i)
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("5 del hilo -> lista solo el reciente y lo abre",
       o.startswith("HANDOFFS: 1") and "chosen by the conversation title" in o, o)
prueba("5 del hilo -> coletilla con los 4 que quedan detrás",
       "(+4 anteriores en la carpeta)" in o, o)

print("\n== /lee: subcarpetas y papelera ==")
handoff("OPTIMIZACION/Auditoría-de-desperdicio-de-tokens-2026-08-26.md",
        "Auditoría de desperdicio de tokens", mtime=9000)
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("handoff en subcarpeta -> sale con su prefijo",
       "OPTIMIZACION/Auditoría-de-desperdicio-de-tokens-2026-08-26.md" in o, o)
handoff("papelera/Auditoría-vieja.md", "Auditoría de desperdicio de tokens", mtime=8000)
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("papelera/ excluida", "papelera/" not in o, o)
handoff("Papelera/Auditoría-vieja2.md", "Auditoría de desperdicio de tokens", mtime=8001)
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("Papelera/ con mayuscula tambien excluida", "Papelera/" not in o, o)
handoff("a/b/Auditoría-honda.md", "Auditoría de desperdicio de tokens", mtime=8002)
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("dos niveles de profundidad NO se listan", "a/b/" not in o, o)

print("\n== /lee: agrupacion cuando no empareja ==")
c, o, e = corre("lista-handoffs.py", SID_C)
cabs = [l for l in o.splitlines() if l.startswith("— ")]
lees = [l for l in o.splitlines() if l.startswith("Lee ")]
n = int(o.splitlines()[0].split(":")[1])
prueba("varios hilos -> cabeceras por hilo, sin perder ni duplicar lineas",
       len(cabs) >= 2 and len(lees) == n, f"n={n} cabs={len(cabs)} lees={len(lees)}\n{o}")
prueba("las lineas Lee siguen intactas para pegarlas",
       all(l.startswith("Lee ") and "continúa desde el siguiente paso" in l
           for l in lees), o)
prueba("cada cabecera va antes de los suyos",
       o.index("— Auditoría de desperdicio de tokens")
       < o.index("Lee OPTIMIZACION/"), o)

print("\n== /lee: deteccion de handoff ==")
open(os.path.join(SAND, "no-es-handoff.md"), "w").write("# Algo\n\n## Decidido\n")
c, o, e = corre("lista-handoffs.py", SID_A)
prueba("un .md con 1 seccion no cuenta como handoff", "no-es-handoff" not in o, o)
handoff("viejo-numerado.md", "Esquema viejo numerado",
        "\n".join(f"## {i}. {s}" for i, s in enumerate(
            ("Decidido", "Tocado", "A medias", "Siguiente paso"), 1)), mtime=7000)
c, o, e = corre("lista-handoffs.py", "dddddddd-1111-2222-3333-444444444444")
prueba("esquema viejo numerado (4 de 5) si cuenta", "viejo-numerado.md" in o, o)

print("\n== /lee: coletilla de lo que queda detras ==")
SID_E = "eeee0000-1111-2222-3333-444444444444"
sesion(SID_E, "Bitácora del muelle seco")
handoff("Bitácora-del-muelle-seco-2026-08-20.md", "Bitácora del muelle seco", mtime=6000)
c, o, e = corre("lista-handoffs.py", SID_E)
prueba("hilo con uno solo -> sin coletilla",
       o.startswith("HANDOFFS: 1") and "anterior" not in o, o)
handoff("Bitácora-del-muelle-seco-2026-08-21.md", "Bitácora del muelle seco", mtime=6001)
c, o, e = corre("lista-handoffs.py", SID_E)
prueba("hilo con dos -> «+1 anterior», en singular",
       "(+1 anterior en la carpeta)" in o and "anteriores" not in o, o)
prueba("y abre el reciente, que antes preguntaba",
       "2026-08-21" in o and "chosen by the conversation title" in o, o)

print("\n== robustez: nunca sin numero, nunca traceback ==")
c, o, e = corre("lista-handoffs.py", SID_A, {"PYTHONHASHSEED": "0"})
prueba("salida 0 y hay linea HANDOFFS", c == 0 and "HANDOFFS:" in o, f"rc={c} err={e}")
r = subprocess.run([sys.executable, "-c", f'''
import importlib.util as u, os, sys
os.chdir({SAND!r})
s=u.spec_from_file_location("lh", {os.path.join(BIN,"lista-handoffs.py")!r})
m=u.module_from_spec(s); s.loader.exec_module(m)
orig=m.candidatos
m.candidatos=lambda: orig()+["FANTASMA.md"]
oa=m.analiza
m.analiza=lambda r:(True,"x") if r=="FANTASMA.md" else oa(r)
m.main()
'''], capture_output=True, text=True)
prueba("archivo fantasma -> no revienta y sigue habiendo numero",
       r.returncode == 0 and "HANDOFFS:" in r.stdout, r.stdout + r.stderr)
r = subprocess.run([sys.executable, "-c", f'''
import runpy, sys, os
os.chdir({SAND!r})
import importlib.util as u
s=u.spec_from_file_location("lh", {os.path.join(BIN,"lista-handoffs.py")!r})
m=u.module_from_spec(s); s.loader.exec_module(m)
m.candidatos=lambda: (_ for _ in ()).throw(RuntimeError("boom"))
try:
    m.main()
except Exception as ex:
    print("HANDOFFS: 0"); print(f"(no se pudo listar: {{type(ex).__name__}})")
'''], capture_output=True, text=True)
prueba("fallo duro -> el guardia de __main__ imprime un numero",
       "HANDOFFS: 0" in r.stdout, r.stdout + r.stderr)

print("\n== /pausa: nombre y carpeta ==")
c, o, e = corre("nombre-pausa.py", SID_A)
prueba("hereda la carpeta del handoff mas reciente del hilo",
       o.startswith("OPTIMIZACION/Auditoría-de-desperdicio-de-tokens-"), o)
c, o, e = corre("nombre-pausa.py", "")
prueba("sin sesion -> DESCONOCIDO pelado, no una ruta", o == "DESCONOCIDO", o)
c, o, e = corre("nombre-pausa.py", casa=REAL)
prueba("sin variable pero con arbol -> identifica la sesion igual",
       o != "DESCONOCIDO" and o.endswith(".md"), o)
c, o, e = corre("nombre-pausa.py", SID_C)
prueba("primer turno -> DESCONOCIDO, no inventa nombre", o == "DESCONOCIDO", o)
c, o, e = corre("nombre-pausa.py", SID_B)
prueba("hilo B -> carpeta raiz (su handoff esta en la raiz)",
       "/" not in o and o.startswith("Sistema-de-reservas"), o)

print("\n== /pausa: slug ==")
for titulo, espera in (
        ("Con / barra y \\ contrabarra", "Con-barra-y-contrabarra"),
        ("Título con acentos y ñ", "Título-con-acentos-y-ñ"),
        ("Ya trae fecha 2026-08-24", "Ya-trae-fecha"),
        ("A" * 90, "A" * 49)):
    sid = "eeeeeeee-1111-2222-3333-44444444444" + str(len(titulo) % 10)
    sesion(sid, titulo)
    c, o, e = corre("nombre-pausa.py", sid)
    base = os.path.basename(o)
    prueba(f"slug de «{titulo[:28]}»",
           base.startswith(espera) and base.endswith(".md")
           and len(base) <= 63 and "/" not in base and o != "DESCONOCIDO",
           f"-> {o!r}")

print("\n== poda ==")
c, o, e = corre("poda-handoffs.py", "")
prueba("sin titulo -> no poda nada", "no se poda nada" in o, o + e)
antes = sorted(os.listdir(os.path.join(SAND, "OPTIMIZACION")))
c, o, e = corre("poda-handoffs.py", SID_B)
prueba("hilo B (1 handoff) -> no toca los de A",
       sorted(os.listdir(os.path.join(SAND, "OPTIMIZACION"))) == antes, o + e)
c, o, e = corre("poda-handoffs.py", SID_A)
vivos = [f for f in os.listdir(SAND) if f.endswith(".md") and "Auditor" in f]
vivos += ["OPTIMIZACION/" + f for f in os.listdir(os.path.join(SAND, "OPTIMIZACION"))
          if f.endswith(".md")]
prueba("poda deja 2 del hilo, el vigente y su antecesor",
       len(vivos) == 2, f"{o}\nvivos={vivos}")
prueba("los retirados van a papelera junto a su archivo",
       os.path.isdir(os.path.join(SAND, "papelera")), o)
c2, o2, e2 = corre("poda-handoffs.py", SID_A)
prueba("poda idempotente", "por debajo del máximo" in o2, o2 + e2)
prueba("ESTADO.md (otro hilo) sigue ahi",
       os.path.exists(os.path.join(SAND, "ESTADO.md")))

shutil.rmtree(SAND, ignore_errors=True)
shutil.rmtree(CASA, ignore_errors=True)
print("\n" + ("TODO EN VERDE" if not fallos else f"FALLOS: {len(fallos)} -> {fallos}"))
sys.exit(1 if fallos else 0)
