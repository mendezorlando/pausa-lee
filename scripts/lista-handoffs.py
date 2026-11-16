#!/usr/bin/env python3
"""Lista los handoffs de /pausa que hay en el directorio de trabajo,
o abre directamente el de este hilo si el titulo lo identifica.

Un .md cuenta como handoff si lleva al menos 4 de las 5 secciones que
escribe /pausa. Se aceptan numeradas ("## 1. Decidido") y sin numerar
("## Decidido"), porque el esquema viejo las numeraba.

No imprime el contenido de ningun archivo: solo el nombre, ya montado en
la instruccion lista para copiar y pegar. Ordena del mas reciente al mas
viejo. Sale siempre con 0.
"""
import os, re, glob, unicodedata, importlib.util
from datetime import datetime

NOMBRE_PAUSA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nombre-pausa.py")
UMBRAL = 0.6       # solapamiento minimo titulo <-> nombre o H1
CASI_EXACTO = 0.9  # con una sola palabra especifica en comun, exige casi identidad
# Palabras que casan por casualidad: no cuentan como prueba de parentesco.
VAGAS = {"analisis", "estado", "notas", "sesion", "proyecto", "trabajo",
         "resumen", "auditoria", "informe"}
VACIAS = {"del", "las", "los", "por", "para", "con", "que", "una", "uno",
          "sus", "este", "esta", "sobre", "entre"}


SIN_TITULO = ("the conversation title is not written yet; on the first message "
              "of a session it arrives a few seconds later")
SIN_SESION = ("the session could not be identified, so there is no title to "
              "match against")
# Distinguirlos importa: SIN_TITULO se arregla repitiendo y SIN_SESION no, y
# hasta el 26/08/2026 el segundo salía en casos que eran el primero.


def titulo_y_motivo():
    """(titulo, motivo), reusando nombre-pausa.py. Sobrevive a /clear: la
    sesion nueva hereda el titulo (a veces reformulado).

    El motivo solo se rellena cuando el titulo sale vacio, y distingue las
    dos causas: el primer turno, que se arregla repitiendo, y la sesion no
    identificable, que no. Antes las dos se veian igual —una lista larga sin
    explicacion— y se leian como si el emparejador se hubiera vuelto loco.
    """
    try:
        spec = importlib.util.spec_from_file_location("nombre_pausa", NOMBRE_PAUSA)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sid = m.sesion()
        if not sid:
            return "", SIN_SESION
        ruta = m.transcript(sid)
        if not ruta:
            # Sabemos quiénes somos; el transcript aún no está escrito. Es el
            # primer turno, no una sesión sin identificar.
            return "", SIN_TITULO
        t = m.titulo(ruta)
        return (t, "") if t else ("", SIN_TITULO)
    except Exception:
        return "", SIN_SESION


def titulo_actual():
    """Solo el titulo. Lo usa poda-handoffs.py, que con "" no poda nada."""
    return titulo_y_motivo()[0]


def palabras(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", s)
            if len(w) > 2 and w not in VACIAS and not w.isdigit()}


def del_hilo(t, rutas, h1s):
    # Devuelve la lista de handoffs de este hilo, del mejor al peor.
    """El handoff de ESTE hilo, o None si no hay uno claro.

    Tras /clear el titulo puede venir reformulado ("Sistema de reservas del hotel" -> "Analisis del sistema de reservas del hotel"), asi que no vale
    comparar por igualdad: se mide solapamiento contenido en el mas corto.
    Se puntua contra el nombre del archivo y contra el H1, y manda el mejor
    de los dos. Exige dos palabras especificas en comun (o una sola si el
    resto del titulo coincide casi entero), para que "Estado" o "Auditoria"
    a secas no emparejen hilos ajenos. Ante empate, lista: equivocarse de
    hilo cuesta mas que una pregunta. Si sale mas de uno se listan todos:
    con la fecha en el nombre, un hilo pausado varios dias tiene un handoff
    por dia y elegir cual retomar es del usuario, no del emparejador.

    Renombrar la conversacion afloja el emparejamiento en proporcion a lo
    que se pierda del titulo; no hay identificador de hilo por debajo al
    que recurrir, porque el sessionId cambia con /clear y el bridgeSessionId
    tambien. El siguiente /pausa reescribe el nombre y lo resincroniza."""
    tw = palabras(t)
    if len(tw) < 2:
        return []
    puntuados = []
    for r in rutas:
        mejor = 0.0
        for cand in (os.path.splitext(os.path.basename(r))[0], h1s.get(r, "")):
            pw = palabras(cand)
            if not pw:
                continue
            comunes = tw & pw
            esp = len(comunes - VAGAS)
            if esp < 1:
                continue
            s = len(comunes) / min(len(tw), len(pw))
            # Una sola palabra especifica solo vale si por lo demas son
            # el mismo titulo: "Auditoria de tokens" si, "Auditoria de
            # seguridad" no.
            if esp < 2 and s < CASI_EXACTO:
                continue
            mejor = max(mejor, s)
        if mejor >= UMBRAL:
            puntuados.append((mejor, r))
    puntuados.sort(reverse=True)
    return [r for _, r in puntuados]



SECCIONES = ("Decidido", "Tocado", "A medias", "Siguiente paso", "No repetir")
CABECERA = re.compile(
    r"^#{1,3}\s*(?:\d+[.)]\s*)?(" + "|".join(SECCIONES) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)
H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
MINIMO = 4     # de 5, para tolerar un handoff recortado
MAX = 20       # techo de la lista, por si el directorio se llena


EXCLUIDOS = {"papelera"}      # lo retirado por la poda no vuelve a listarse
NIVELES = ("*.md", "*/*.md")  # el directorio y un nivel de subcarpetas


def candidatos():
    """Los .md del directorio y de un nivel de subcarpetas.

    Un hilo puede mudarse a su propia carpeta arrastrando sus handoffs
    (`OPTIMIZACION/`, por ejemplo); sin esto /lee dejaria de verlos. Lo que
    impide que cualquier .md suelto de una subcarpeta se cuele como handoff
    no es esta funcion, es el filtro de secciones de analiza().
    """
    vistos = set()
    for patron in NIVELES:
        for r in glob.glob(patron):
            if os.path.dirname(r).lower() not in EXCLUIDOS:
                vistos.add(r)
    return sorted(vistos)


def analiza(ruta):
    """(es_handoff, titulo_del_documento), leyendo el archivo una sola vez.

    El H1 importa tanto como el nombre: los handoffs viejos se llamaban
    todos `ESTADO.md` y el nombre no dice de que hilo son, pero su primera
    linea si — `# ESTADO — Sistema de Reservas del Hotel`."""
    try:
        if os.path.getsize(ruta) > 2_000_000:
            return False, ""
        with open(ruta, errors="replace") as f:
            txt = f.read()
    except Exception:
        return False, ""
    ok = len({m.group(1).lower() for m in CABECERA.finditer(txt)}) >= MINIMO
    m = H1.search(txt)
    return ok, (m.group(1) if m else "")


def mtime(ruta):
    """0.0 si el archivo ya no esta. Se usa para ordenar y para fechar: un
    .md puede desaparecer entre candidatos() y aqui, y un getmtime pelado
    tumbaba el script entero -- dejando a /lee sin linea HANDOFFS:."""
    try:
        return os.path.getmtime(ruta)
    except OSError:
        return 0.0


def fecha(ruta):
    t = mtime(ruta)
    return datetime.fromtimestamp(t).strftime("%d/%m/%Y %H:%M") if t else "sin fecha"


def linea(ruta, atras=0):
    # La coletilla cuenta lo que sigue en la carpeta y ya no se lista. Va
    # detras de la fecha a proposito: la linea se copia y se pega como prompt,
    # y la fecha es justo donde el usuario ya corta al pegarla.
    cola = (f" (+{atras} anterior{'es' if atras > 1 else ''} en la carpeta)"
            if atras else "")
    return f"Lee {ruta} y continúa desde el siguiente paso. — {fecha(ruta)}{cola}"


def clave(r, h1s):
    """El hilo de un handoff: su H1, o su nombre si no lo tiene."""
    return h1s.get(r) or os.path.basename(r)


def uno_por_hilo(rutas, h1s):
    """(el mas reciente de cada hilo, cuantos deja detras por hilo).

    Lo viejo no se borra ni se esconde: sigue en la carpeta, se abre por su
    nombre y la poda lo archiva a su ritmo. Solo sale del LISTADO, que es lo
    unico que cuesta tokens. Medido el 26/08/2026: cada linea son 120
    caracteres ~ 55 tok que se releen en cada turno posterior (48 de mediana),
    y las dos lineas viejas del hilo de Auditoria eran ~5,2k por sesion que
    nadie abrio jamas -- cero lecturas de un handoff ya superado en 24
    sesiones. Ademas tres lineas del mismo hilo bloqueaban la rama que abre
    sola, que exige len(del_hilo_) == 1: la poda castigaba al hilo mas activo.
    """
    vistos, nuevos, atras = set(), [], {}
    for r in rutas:            # ya llega del mas reciente al mas viejo
        k = clave(r, h1s)
        if k in vistos:
            atras[k] = atras.get(k, 0) + 1
        else:
            vistos.add(k)
            nuevos.append(r)
    return nuevos, atras


def agrupa(rutas, h1s):
    """[(nombre_del_hilo, [rutas])], hilos por su handoff mas reciente.

    Solo para cuando no se ha podido emparejar: en el primer mensaje de una
    sesion eso pasa siempre, y una lista plana de seis handoffs de tres hilos
    se lee como un revoltijo. Agrupada es un menu, y el nombre del hilo es
    ademas la palabra que sirve para `/lee <palabra>`.

    Agrupa por el H1 del documento, que es lo que dice de que hilo es; si no
    lo tiene, cada archivo va suelto bajo su propio nombre. No reordena
    dentro del grupo: siguen del mas reciente al mas viejo.
    """
    grupos = {}
    for r in rutas:
        grupos.setdefault(clave(r, h1s), []).append(r)
    if len(grupos) < 2:
        return [("", list(rutas))]   # un solo hilo: la cabecera no aporta
    return list(grupos.items())      # dict conserva el orden de insercion


# Las instrucciones viven aqui y no en lee.md porque lee.md se inyecta ENTERO
# en cada /lee -- las cinco ramas, cuando solo una aplica -- y se queda en el
# transcript releyendose en cada llamada posterior. Medido el 26/08/2026: /lee
# se teclea el primero y le quedan 48 turnos de mediana por delante (media 69,
# maximo 413). Emitir solo la rama que disparo es el mismo texto util pagado
# una vez en vez de cinco veces por turno.
# La literalidad se dice UNA vez y se reparte. `varios` la llevaba y `sueltos`
# no, y `sueltos` es la rama que dispara en CADA primer mensaje con mas de un
# hilo: sin clausula el modelo maqueta la lista -- vinetas, backticks,
# encabezados -- y de paso tira el "Lee ... y continua desde el siguiente
# paso.", que es justo lo que hace la linea pegable como prompt siguiente.
# Observado el 26/08/2026 en dos sesiones, con dos maquetados distintos, o sea
# que faltaba la instruccion, no sobraba modelo. Compartida para que las ramas
# no vuelvan a separarse.
LITERAL = ("exactly as they come, whole and one per line, no comments and no "
           "reordering: each line is the prompt the user will copy")

INSTR = {
    "cero": "No handoffs here: say so in one line and stop.",
    "fallo": "The search FAILED. Say that, not that there are no handoffs: they are not the same.",
    "uno": "Open it by the path exactly as given, folder included. In three lines at most, tell the user where things stand, then keep working from its «Siguiente paso» section without asking for confirmation.",
    "uno_titulo": "Name the file in those three lines: it was chosen by the conversation title, so a wrong thread shows at once.",
    "unico": "It is the only handoff in the folder and its thread could not be verified. Open it unless this conversation's history says it is about something else; if it does, do not open it: say so in one line and stop.",
    "ajeno": "The only handoff in the folder is NOT from this thread: the conversation title, which is written, says so. Do not open it and do not summarize it; say so in one line and stop, unless the user asks you to open it anyway.",
    "varios": f"Print those lines {LITERAL}. Do not open any file: the user chooses.",
    "sueltos": f"The dash lines group by thread; print them {LITERAL}. Which thread you are could not be determined, but this conversation's history does say, and that is the one thing this listing cannot see. If it tells you WITHOUT DOUBT: print only its group and what you base that on, and if a single line is left, open it. If you do not know (clean session, no history): print them all and choose none — guessing ends in the handoff of another thread.",
}


def instruye(*claves):
    print()
    print(" ".join(INSTR[k] for k in claves))


def main():
    datos = {}
    for f in candidatos():
        ok, h1 = analiza(f)
        if ok:
            datos[f] = h1
    todos = sorted(datos, key=mtime, reverse=True)
    hallados, atras = uno_por_hilo(todos, datos)

    def pinta(r):
        return linea(r, atras.get(clave(r, datos), 0))

    motivo = ""
    ajeno = False
    # Esto era `if len(hallados) > 1`, y con UN solo handoff el titulo ni se
    # miraba: /lee abria el unico que hubiera aunque fuera de otro hilo. En un
    # hilo nuevo, todavia sin handoff propio, eso entrega el ajeno en silencio
    # -- el mismo pecado que el respaldo de transcript() que se retiro el
    # 26/08/2026. Y con una carpeta por hilo, el reparto que se esta valorando,
    # seria el caso normal y no el raro. Ahora el titulo se consulta siempre.
    if hallados:
        t, motivo = titulo_y_motivo()
        del_hilo_ = del_hilo(t, hallados, datos) if t else []
        if t and not del_hilo_:
            ajeno = True
            motivo = (f"the title is «{t}» and matches none of these; this "
                      "thread probably has no handoff yet")
        if len(del_hilo_) == 1:
            print("HANDOFFS: 1")
            print(pinta(del_hilo_[0]))
            print(f"(chosen by the conversation title, «{t}»; "
                  f"there were {len(todos)} in the directory)")
            instruye("uno", "uno_titulo")
            return
        if len(del_hilo_) > 1:
            # Del mismo hilo ya no puede haber dos: uno_por_hilo() dejo solo
            # el mas reciente de cada uno. Llegar aqui significa que el titulo
            # casa con HILOS distintos -- dos hilos de facturacion comparten dos
            # palabras y se salvan por una decima --, y ahi elegir es del
            # usuario: equivocarse de hilo cuesta mas que una pregunta.
            enorden = [r for r in hallados if r in del_hilo_]
            print(f"HANDOFFS: {len(enorden)}")
            for r in enorden:
                print(pinta(r))
            print(f"({len(enorden)} different threads match «{t}», newest "
                  f"first; there were {len(todos)} in the directory)")
            instruye("varios")
            return

    print(f"HANDOFFS: {len(hallados)}")
    for cab, grupo in agrupa(hallados[:MAX], datos):
        if cab:
            print(f"— {cab}")
        for p in grupo:
            print(pinta(p))
    if len(hallados) > MAX:
        print(f"… and {len(hallados) - MAX} more, not listed.")
    if motivo:
        # Sin esta linea, una lista de hilos mezclados parece una averia del
        # emparejador. Es lo contrario: es el emparejador negandose a adivinar.
        reintenta = (" Run /lee again next turn and only yours will come out."
                     if motivo == SIN_TITULO else "")
        print(f"(not matched by thread: {motivo}.{reintenta})")
        if len(hallados) != 1:
            instruye("sueltos")
        elif ajeno:
            instruye("ajeno")
        else:
            instruye("unico", "uno")
        return
    # Sin motivo y con handoffs no se llega aqui: si el titulo emparejo se
    # volvio antes, y si no emparejo hay motivo. El sesgo del respaldo es no
    # abrir: listar de mas cuesta una pregunta, abrir de mas cuesta el hilo.
    instruye("cero" if not hallados else "varios")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # lee.md ordena actuar "segun el numero que dice HANDOFFS:, y nada
        # mas". Sin esa linea el comando se queda sin instruccion y hace
        # cualquier cosa, que es la peor forma de fallar. Siempre un numero.
        print("HANDOFFS: 0")
        print(f"(could not list: {type(e).__name__}; this does not mean there "
              "are no handoffs here, it means the search failed)")
        print()
        print(INSTR["fallo"])
