---
description: Escribe el handoff a disco antes de una pausa larga, para poder hacer /clear sin perder el hilo
argument-hint: [nombre-del-archivo]
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/nombre-pausa.py:*), Bash(${CLAUDE_PLUGIN_ROOT}/scripts/poda-handoffs.py:*)
---

NOMBRE PEDIDO: $ARGUMENTS
NOMBRE POR CONVERSACIÓN: !`${CLAUDE_PLUGIN_ROOT}/scripts/nombre-pausa.py`
PODA: !`${CLAUDE_PLUGIN_ROOT}/scripts/poda-handoffs.py --antes`

Voy a hacer una pausa larga. Escribe el handoff donde ya viva este hilo: `NOMBRE POR CONVERSACIÓN` trae la ruta entera, con carpeta propia si el hilo la tiene (`OPTIMIZACION/…`) y sin ella si vive en la raíz del directorio de trabajo.

**Nombre del archivo.** Resuélvelo tú, sin preguntarme, con esta prioridad:

1. Si `NOMBRE PEDIDO` trae texto, ese manda: normalízalo (espacios → `-`, fuera `/` y `\`), añádele la fecha de hoy en `-AAAA-MM-DD` si no la trae ya, cierra con `.md` y escríbelo **en la carpeta que traiga `NOMBRE POR CONVERSACIÓN`**, de inmediato. El nombre pedido es un nombre, no una ruta: la carpeta no la eliges tú. No consultes nada más.
   `DESCONOCIDO` **no es una carpeta**: es la señal de que no se pudo identificar la sesión. Si eso es lo que vino, escribe en el directorio de trabajo y no crees ninguna carpeta con ese nombre.
2. Si `NOMBRE PEDIDO` viene vacío, usa `NOMBRE POR CONVERSACIÓN` tal cual, que ya viene normalizado y con su carpeta.
3. Solo si además `NOMBRE POR CONVERSACIÓN` es `DESCONOCIDO`, elige tú un nombre corto sacado del tema del hilo, escríbelo en el directorio de trabajo y dime cuál elegiste **y que el hilo no se pudo identificar**: sin título no hay emparejamiento, así que la poda no hará nada y el próximo `/lee` no sabrá que este handoff es de este hilo. Para que lo sepa, la primera línea del archivo importa más que nunca.

El nombre lleva la fecha, así que pausar el mismo día reescribe el archivo del día y pausar otro día crea uno nuevo. Si el archivo de hoy ya existe, reescríbelo entero con el estado actual. **No toques a mano ningún otro `.md` del directorio ni de sus subcarpetas**, y en particular no borres los de días anteriores: `/lee` los lista con su fecha para que el usuario elija cuál retomar, y de recortarlos se encarga la poda.

**Primera línea del archivo.** Un `# ` con el título de la conversación, tal cual, aunque el nombre del archivo sea otro. `/lee` empareja el hilo por ahí cuando el nombre no lo delata: los handoffs viejos se llamaban todos `ESTADO.md` y solo su encabezado dice de qué van.

Contenido, en este orden y sin relleno:

1. **Decidido** — las decisiones que ya no hay que volver a discutir, una línea cada una.
2. **Tocado** — archivos modificados o creados, con ruta relativa y qué se les hizo.
3. **A medias** — lo que quedó incompleto y en qué punto exacto se cortó.
4. **Siguiente paso** — una sola frase imperativa. No una lista.
5. **No repetir** — caminos ya descartados y por qué, para no volver a explorarlos.

Reglas:

- Máximo ~2k tokens. Si no cabe, corta contexto histórico, nunca el siguiente paso.
- Escribe números y rutas, no adjetivos. "el parser de XML falla con CDATA anidado en `src/ecf/parse.ts:88`", no "hay un problema con el parser".
- Es un archivo para leer en frío mañana, sin esta conversación. Si una frase solo se entiende habiendo estado aquí, reescríbela.

**Poda.** Ya está hecha: es la línea `PODA` de arriba, que corrió antes de que escribieras. Dejó el handoff de hoy y uno anterior de este hilo, y el que escribas ahora completa los dos. No la ejecutes otra vez: tu única llamada es la que escribe el archivo.

Al terminar, dime en una línea el nombre del archivo escrito y que ejecute `/clear`, y nada más.
