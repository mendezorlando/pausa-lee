#!/usr/bin/env python3
"""Deja como mucho CONSERVA handoffs de este hilo en el directorio de trabajo.

Los sobrantes NO se borran: se mueven a papelera/. Reusa el emparejador de
lista-handoffs.py para que "mismo hilo" signifique exactamente lo mismo en
/pausa y en /lee.

Si el titulo de la conversacion no se puede leer, el hilo no se puede
identificar y entonces no se poda nada. Sale siempre con 0.

Ese freno era ilusorio hasta el 26/08/2026: `transcript()` tenia un respaldo
que, si el .jsonl propio aun no estaba en disco, devolvia el de la sesion
ANTERIOR. El titulo se leia perfectamente -- solo que era el de otro hilo --,
asi que el freno no saltaba y esta poda habria retirado handoffs ajenos.
Arreglado en nombre-pausa.py: sin sesion identificable, no hay titulo.
"""
import os, glob, importlib.util, shutil, sys
from datetime import datetime

LISTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lista-handoffs.py")
# 2 desde el 26/08/2026, a peticion del usuario: el vigente y su antecesor.
# El listado ya solo muestra el mas reciente de cada hilo, asi que el segundo
# no se ve -- se anuncia con "(+1 anterior en la carpeta)" y esta ahi por si
# el ultimo sale mal. El tercero deja de ganarse el sitio: en 24 sesiones no
# hubo NI UNA lectura de un handoff ya superado, y lo que se retira no se
# borra, se archiva en papelera/.
CONSERVA = 2
DESTINO = "papelera"


def modulo():
    spec = importlib.util.spec_from_file_location("lista_handoffs", LISTA)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def libre(destino, nombre):
    base, ext = os.path.splitext(nombre)
    ruta, n = os.path.join(destino, nombre), 2
    while os.path.exists(ruta):
        ruta = os.path.join(destino, f"{base}-{n}{ext}")
        n += 1
    return ruta


def main():
    m = modulo()
    datos = {}
    for f in m.candidatos():
        ok, h1 = m.analiza(f)
        if ok:
            datos[f] = h1
    queda = CONSERVA
    if "--antes" in sys.argv[1:]:
        # /pausa la corre en su preambulo, antes de escribir, y se ahorra una
        # llamada al modelo con todo el contexto. El de hoy se va a reescribir:
        # no cuenta ni se toca. Del resto queda uno; escrito el nuevo, CONSERVA.
        hoy = f"-{datetime.now():%Y-%m-%d}.md"
        datos = {f: h for f, h in datos.items() if not f.endswith(hoy)}
        queda = CONSERVA - 1
    if len(datos) <= queda:
        print("PODA: nada que podar")
        return

    t = m.titulo_actual()
    if not t:
        print("PODA: título desconocido, no se poda nada")
        return

    hilo = m.del_hilo(t, sorted(datos, key=m.mtime, reverse=True), datos)
    if len(hilo) <= queda:
        print(f"PODA: {len(hilo)} de este hilo, por debajo del máximo de {queda}")
        return

    # Del mismo hilo, ordenados por fecha: sobran los mas viejos.
    porfecha = [r for r in sorted(datos, key=m.mtime, reverse=True) if r in hilo]
    sobran = porfecha[queda:]
    movidos = []
    for r in sobran:
        # La papelera va junto al handoff: si el hilo vive en su propia
        # carpeta, sus retirados se quedan dentro de ella.
        destino = os.path.join(os.path.dirname(r), DESTINO)
        os.makedirs(destino, exist_ok=True)
        d = libre(destino, os.path.basename(r))
        shutil.move(r, d)
        movidos.append(f"{r} → {d} ({m.fecha(d)})")
    print(f"PODA: {len(porfecha)} del hilo «{t}»; conservo {queda}, retiro {len(movidos)}")
    for x in movidos:
        print("  " + x)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"PODA: sin efecto ({type(e).__name__})", file=sys.stderr)
