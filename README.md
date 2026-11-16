# pausa-lee

Dos comandos para Claude Code que permiten hacer `/clear` sin perder el hilo:

- **`/pausa [nombre]`:** antes de una pausa larga, escribe en el directorio de trabajo un *handoff*, `<título-de-la-conversación>-AAAA-MM-DD.md`. Lleva cinco secciones (Decidido, Tocado, A medias, Siguiente paso y No repetir) y unos 2k tokens como mucho.
- **`/lee [palabra]`:** al volver, encuentra el handoff de este hilo por el título de la conversación, lo abre y sigue desde «Siguiente paso». Si no puede saber de qué hilo es, lista los que hay para que elijas y no adivina.

Por qué existe: la caché de Claude dura una hora. Al volver, el contexto que dejaste vivo se paga entero en cada llamada. Un handoff de 2k tokens retoma el hilo por una fracción.

## Instalación
En una sesión de Claude Code en la terminal:

```
/plugin install pausa-lee --marketplace mendezorlando/pausa-lee
```

Desde la terminal del sistema:

```bash
claude plugin install pausa-lee --marketplace mendezorlando/pausa-lee
```

En la app de escritorio: + junto al cuadro del prompt → Plugins → Add marketplace con `mendezorlando/pausa-lee` → Add plugin.

Los comandos se invocan como `/pausa` y `/lee`. Si otro comando ya usa uno de esos nombres, como `/pausa-lee:pausa` y `/pausa-lee:lee`.

## Cómo funciona
**`scripts/nombre-pausa.py`** saca el nombre del archivo del título de la conversación.
- Identifica la sesión por `CLAUDE_CODE_SESSION_ID`. Si esa variable no está, sube por el árbol de procesos hasta `~/.claude/sessions/<pid>.json`.
- Lee el título (`custom-title` o `ai-title`) en `~/.claude/projects/*/<sesión>.jsonl`.
- Si un hilo ya tiene sus handoffs en una subcarpeta, escribe ahí.
- Si no puede identificar la sesión, escribe `DESCONOCIDO` y no inventa nada.

**`scripts/lista-handoffs.py`** busca los `.md` del directorio y de un nivel de subcarpetas.
- Cuenta como handoff un `.md` que tenga al menos 4 de las 5 secciones.
- Lo empareja con el hilo por el nombre o por el H1, y solo da la instrucción del caso que aplica. Así `/lee` gasta pocos tokens.

**`scripts/poda-handoffs.py`** deja dos handoffs por hilo: el vigente y el anterior.
- Los demás no se borran: pasan a `papelera/`, junto a su archivo.
- Si no se conoce el título, no poda nada.

**`scripts/prueba-handoffs.py`** es la batería de regresión: `python3 scripts/prueba-handoffs.py`. Trabaja en carpetas temporales y con un `HOME` propio.

## Requisitos y límites
- Python 3, sin dependencias. Funciona en macOS y en Linux, porque usa `ps` para subir por el árbol de procesos.
- Lee archivos internos de Claude Code: el transcript `.jsonl` y `~/.claude/sessions`. Si una versión futura cambia ese formato, el emparejamiento puede dejar de funcionar. En ese caso `/lee` lista los handoffs en vez de abrir uno.
- Si renombras la conversación, al emparejador le cuesta más reconocer el hilo. El siguiente `/pausa` lo vuelve a poner al día.

## Licencia
MIT.
