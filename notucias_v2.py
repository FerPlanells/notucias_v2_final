#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente de Telegram: Resumen de noticias relevantes de educación y subida a Google Drive.
Solucionados algunos errores de tipeo
"""

import os
import time
import logging
from datetime import datetime
from threading import Thread

from dotenv import load_dotenv
from newspaper import Article
from openai import OpenAI
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Carga de variables de entorno
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
CLIENT_SECRETS_JSON = os.getenv("CLIENT_SECRETS_JSON")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# Validar configuraciones
if not BOT_TOKEN:
    logging.error("BOT_TOKEN no definido en el entorno.")
    exit(1)
if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY no definido en el entorno.")
    exit(1)

# Inicializar cliente de OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Asegurar existencia de archivos de credenciales de Google
def _ensure_file(path: str, content_env: str, env_name: str):
    if os.path.exists(path):
        return
    content = os.getenv(content_env)
    if content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"{env_name} generado en {path}")
    else:
        logging.warning(f"{env_name} no definido; se omitirá.")

_ensure_file("client_secrets.json", "CLIENT_SECRETS_JSON", "CLIENT_SECRETS_JSON")
_ensure_file("credentials.json", "GOOGLE_CREDENTIALS_JSON", "GOOGLE_CREDENTIALS_JSON")

# Autenticación y configuración de Google Drive
gauth = GoogleAuth()
gauth.LoadCredentialsFile("credentials.json")
if not gauth.credentials:
    # primera vez: flujo no interactivo por CLI
    gauth.CommandLineAuth()
elif gauth.access_token_expired:
    # renueva usando el refresh token almacenado
    gauth.Refresh()
else:
    # token aún válido
    gauth.Authorize()
gauth.SaveCredentialsFile("credentials.json")

drive = GoogleDrive(gauth)


def extraer_texto(link: str) -> tuple[str, str] | tuple[None, None]:
    """
    Extrae título y texto de un artículo web usando newspaper.
    """
    try:
        articulo = Article(link)
        articulo.download()
        articulo.parse()
        return articulo.title, articulo.text
    except Exception as e:
        logging.error(f"Error al procesar artículo ({link}): {e}")
        return None, None


def evaluar_relevancia(texto: str, tema: str = "educación") -> bool:
    """
    Evalúa si el texto es relevante al tema.
    Retorna True si la respuesta comienza con 'Sí'.
    """
    if not texto:
        return False
    prompt = (
        f"Determina si esta noticia es relevante para el tema '{tema}'. "
        "Responde solo 'Sí' o 'No'.\n"
        f"Texto: {texto[:2000]}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        respuesta = resp.choices[0].message.content.strip()
        return respuesta.lower().startswith("sí")
    except Exception as e:
        logging.error(f"Error al evaluar relevancia: {e}")
        return False


def resumir(texto: str) -> str:
    """
    Genera un resumen con estilo íntimo, reflexivo y melancólico.
    """
    prompt = (
        "Resume el siguiente artículo usando solo información del texto. "
        "No agregues datos externos. "
        "Estilo: íntimo, reflexivo, sensible, frases breves, sin tecnicismos, con tono humano y melancólico. "
        "Tamaño: 300-400 palabras.\n"
        f"{texto[:3000]}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error al generar resumen: {e}")
        return "⚠️ Error al generar el resumen."


def guardar_y_subir_resumen(titulo: str, resumen: str, link: str):
    """
    Guarda el resumen en un archivo temporal, lo sube a Google Drive y lo elimina localmente.
    """
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_archivo = f"Resumen_{fecha}.txt"
    contenido = (
        f"--- {titulo} --- ({fecha})\n"
        f"Link original: {link}\n\n"
        f"{resumen}\n"
    )
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(contenido)
    logging.info(f"Resumen guardado en {nombre_archivo}")

    archivo = drive.CreateFile({'title': nombre_archivo, 'parents': [{'id': GOOGLE_DRIVE_FOLDER_ID}]})
    archivo.SetContentFile(nombre_archivo)
    archivo.Upload()
    logging.info(f"Archivo subido a Google Drive como {nombre_archivo}")

    os.remove(nombre_archivo)
    logging.info(f"Archivo temporal {nombre_archivo} eliminado")


async def procesar_link(link: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """
    Procesa un link: extrae texto, evalúa relevancia, resume y sube si es relevante.
    """
    titulo, texto = extraer_texto(link)
    if not titulo or not texto:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ No se pudo procesar el artículo.")
        return

    if evaluar_relevancia(texto):
        resumen = resumir(texto)
        guardar_y_subir_resumen(titulo, resumen, link)
        await context.bot.send_message(chat_id=chat_id, text="✅ Resumen creado y subido a Drive.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Noticia no relevante; descartada.")


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manejador de mensajes de Telegram: acepta solo links.
    """
    mensaje = update.message.text.strip()
    chat_id = update.effective_chat.id
    if mensaje.startswith("http"):
        await procesar_link(mensaje, context, chat_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text="🚫 Solo acepto links.")


def start_dummy_server(port: int = 10000):
    """
    Inicia un servidor Flask dummy para mantener el bot activo en Render.
    """
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Bot funcionando"

    app.run(host="0.0.0.0", port=port)


def main():
    """
    Punto de entrada para el bot de Telegram y servidor dummy.
    """
    Thread(target=start_dummy_server, daemon=True).start()
    logging.info("Servidor dummy iniciado en el puerto 10000")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    logging.info("Bot de Telegram iniciado y en escucha.")
    app.run_polling()


if __name__ == "__main__":
    main()
