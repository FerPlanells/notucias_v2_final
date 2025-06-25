import os
import time
from dotenv import load_dotenv
from newspaper import Article
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

print(f"📄 Ejecutando desde: {os.path.abspath(__file__)}")

# Cargar variables de entorno
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Crear client_secrets.json desde variable de entorno si no existe
if not os.path.exists("client_secrets.json"):
    contenido = os.getenv("CLIENT_SECRETS_JSON")
    if contenido:
        with open("client_secrets.json", "w") as f:
            f.write(contenido)
    else:
        print("⚠️ CLIENT_SECRETS_JSON está vacía o no fue definida.")

# Crear credentials.json desde variable de entorno si no existe
if not os.path.exists("credentials.json"):
    creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds:
        with open("credentials.json", "w") as f:
            f.write(creds)
    else:
        print("⚠️ GOOGLE_CREDENTIALS_JSON está vacía o no fue definida.")

# Autenticación con Google
gauth = GoogleAuth()
gauth.LoadCredentialsFile("credentials.json")

if not gauth.credentials:
    gauth.CommandLineAuth()
    gauth.SaveCredentialsFile("credentials.json")

drive = GoogleDrive(gauth)


# Funciones
def extraer_texto(link):
    try:
        articulo = Article(link)
        articulo.download()
        articulo.parse()
        return articulo.title, articulo.text
    except Exception as e:
        print(f"Error al procesar el artículo: {e}")
        return None, None
def evaluar_relevancia(texto, tema="educación"):
    if not texto:
        return "No"
    prompt = f"""
    Estás analizando si esta noticia es relevante para el tema '{tema}'.
    Respondé solo con 'Sí' o 'No'. Texto: {texto[:2000]}
    """
    try:
        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al evaluar relevancia: {e}")
        return "No"


def resumir(texto):
    prompt = f"""
Quiero que resumas el siguiente artículo utilizando únicamente la información contenida en el texto. No agregues datos externos ni inventes nada.
El resumen debe tener un estilo similar al siguiente: íntimo, reflexivo, sensible, con frases breves y cargadas de sentido. Evitá tecnicismos. *Tiene que sonar humano, sincero y algo melancólico*.
Usá entre 300 y 400 palabras.
Texto a resumir:
{texto[:3000]}
"""
    try:
        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error al generar resumen: {e}")
        return "⚠️ Error al generar el resumen."
from datetime import datetime
def guardar_y_subir_resumen(titulo, resumen, link):
    # Generar nombre único con fecha y hora
    from datetime import datetime
    import os
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nombre_archivo = f"Resumen_{fecha}.txt"
    # Crear archivo temporal
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(f"--- {titulo} --- ({fecha})\n")
        f.write(f"Link original: {link}\n\n")
        f.write(resumen)
        f.write("\n\n")
    print(f"📝 Resumen temporal guardado como {nombre_archivo}")
    
    archivo = drive.CreateFile({'title': nombre_archivo})
    archivo.SetContentFile(nombre_archivo)
    archivo.Upload()# Subir a Drive

    archivo.content = None
    time.sleep(0.5)

    print(f"📤 Archivo subido a Google Drive como {nombre_archivo}")
    # Borrar archivo temporal
    os.remove(nombre_archivo)
    print(f"🗑️ Archivo temporal {nombre_archivo} eliminado.")
    
async def procesar_link(link, context: ContextTypes.DEFAULT_TYPE, chat_id):
    try:
        titulo, texto = extraer_texto(link)
        es_relevante = evaluar_relevancia(texto)
        if es_relevante.lower().startswith("sí"):
            resumen = resumir(texto)
            guardar_y_subir_resumen(titulo, resumen, link)
            await context.bot.send_message(chat_id=chat_id, text="✅ Resumen agregado y subido a Drive.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ La noticia no era relevante y fue descartada.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error al procesar el link: {e}")
# Manejador de mensajes
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.message.text
    chat_id = update.message.chat_id
    if mensaje.startswith("http"):
        await procesar_link(mensaje, context, chat_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text="🚫 Solo acepto links por ahora.")
# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # Escuchar mensajes de texto que no sean comandos
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    print("🤖 Agente corriendo y escuchando en Telegram...")
    app.run_polling()
# ----- DUMMY SERVER PARA RENDER -----
import flask
from threading import Thread

def start_dummy_server():
    app = flask.Flask(__name__)
    
    @app.route('/')
    def home():
        return "Bot funcionando"

    app.run(host='0.0.0.0', port=10000)

Thread(target=start_dummy_server).start()
# ------------------------------------
