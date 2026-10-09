import os
import re
import smtplib
import json
import feedparser
import anthropic
from pathlib import Path
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

FEEDS = [
    {"nombre": "Reuters Business",
        "url": "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US"},
    {"nombre": "Yahoo Finance",    "url": "https://finance.yahoo.com/news/rssindex"},
    {"nombre": "Expansión México", "url": "https://expansion.mx/rss"},
    {"nombre": "Investing España", "url": "https://es.investing.com/rss/news.rss"},
]


def crear_carpetas():
    for carpeta in ["data/raw", "data/processed", "logs", "config"]:
        Path(carpeta).mkdir(parents=True, exist_ok=True)


def recolectar_titulares():
    titulos = []
    for feed in FEEDS:
        resultado = feedparser.parse(feed["url"])
        contador = 0
        for entrada in resultado.entries:
            if contador >= 5:
                break
            titulo = entrada.get("title", "").strip()
            if titulo:
                titulos.append(
                    f"[{feed['nombre']}] {titulo} | URL: {entrada.get('link', 'No disponible')}"
                )
                contador += 1
    return titulos


def cargar_preferencias() -> str:
    """Lee preferencias.json y construye un párrafo de personalización para el prompt."""
    ruta = Path(__file__).parent / "preferencias.json"
    if not ruta.exists():
        return ""
    prefs = json.loads(ruta.read_text(encoding="utf-8"))
    temas = prefs.get("temas", {})
    priorizar = [t for t, s in temas.items() if s >= 2]
    evitar = [t for t, s in temas.items() if s < 0]
    especificos = prefs.get("temas_especificos", "").strip()
    parrafo = "\nUser preferences to consider when selecting news:\n"
    if priorizar:
        parrafo += f"- Prioritize topics: {', '.join(priorizar)}\n"
    if evitar:
        parrafo += f"- Avoid topics: {', '.join(evitar)}\n"
    if especificos:
        parrafo += f"- Specific interests: {especificos}\n"
    return parrafo


def analizar_con_claude(titulos):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    noticias_texto = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titulos))

    preferencias = cargar_preferencias()
    prompt = f"""You are a senior financial analyst. I am providing you with a list of headlines from various sources (Reuters Business, Yahoo Finance, Expansión México, and Investing España) right below. You must analyze the entire list provided, regardless of the source, and do not filter by source.

{noticias_texto}
{preferencias}
Your task:
1. Select the 8 most relevant news for a finance professional interested in global markets, political situations, the economy, and stock markets.
2. For each selected news item, write a summary of exactly 2 sentences: the first explains the fact, the second explains its financial implication.
3. If the headline is in English, write the summary in English. If it is in Spanish, write it in Spanish.
4. Include the exact URL of the news item you are summarizing.
5. Respond ONLY with the 8 numbered news items, without any introduction or additional text.

Response format:
1. [Headline]
   Summary: [Sentence 1. Sentence 2.]
   URL: [Link]
"""

    respuesta = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return respuesta.content[0].text


def texto_a_html(texto):
    texto = texto.replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;")
    texto = re.sub(
        r'URL:\s*(https?://\S+)',
        r'URL: <a href="\1" target="_blank">\1</a>',
        texto,
    )
    texto = re.sub(r"^(\d+\.\s.+)$", r"<b>\1</b>", texto, flags=re.MULTILINE)
    return texto.replace("\n", "<br>\n")


def enviar_email(texto_analisis):
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    asunto = f"Daily Financial News - {date.today().strftime('%Y-%m-%d')}"

    cuerpo_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #222;">
    <h2 style="color: #1a1a2e;">Daily Financial News — {date.today().strftime('%B %d, %Y')}</h2>
    <hr>
    <p>{texto_a_html(texto_analisis)}</p>
    <hr>
    <p>📋 <strong>¿Qué temas te interesaron hoy?</strong> — 
    <a href="{os.getenv('GOOGLE_FORM_URL', '')}" target="_blank">Responder en 20 segundos →</a></p>
    <hr>
    <p style="font-size: 11px; color: #888;">Generado automáticamente gracias a News Agent</p>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = gmail_user
    msg["To"] = gmail_user

    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(gmail_user, gmail_password)
        servidor.sendmail(gmail_user, gmail_user, msg.as_string())

    print(f"Email enviado correctamente a {gmail_user}")


if __name__ == "__main__":
    load_dotenv()
    crear_carpetas()
    titulos = recolectar_titulares()
    analisis = analizar_con_claude(titulos)
    enviar_email(analisis)
