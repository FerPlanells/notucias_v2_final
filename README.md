# Agente de Noticias con Telegram, OpenAI y Google Drive

Este es un agente automatizado que recibe links de noticias vía un bot de Telegram, evalúa si son relevantes para un tema específico (por defecto, *educación*), genera un resumen con estilo humano y reflexivo usando GPT, y guarda automáticamente ese resumen en Google Drive.

---

## ¿Cómo funciona?

1. Enviás un link de una noticia al bot de Telegram.
2. El bot extrae el texto de la página usando `newspaper3k`.
3. Evalúa si la noticia es relevante al tema.
4. Si lo es, genera un resumen usando `gpt-3.5-turbo`.
5. Guarda el resumen como archivo `.txt` en Google Drive.
6. Te responde por Telegram si lo subió o descartó.

---

## Tecnologías utilizadas

- [Python](https://www.python.org/)
- [Telegram Bot API](https://core.telegram.org/bots)
- [OpenAI API](https://platform.openai.com/)
- [Google Drive API (PyDrive2)](https://github.com/iterative/PyDrive2)
- [newspaper3k](https://github.com/codelucas/newspaper)
- [Render](https://render.com/) (para ejecución en la nube)

---

## Instalación local

1. Cloná el repositorio:
   ```bash
   git clone https://github.com/FerPlanells/agente-noticias-telegram.git
   cd agente-noticias-telegram
