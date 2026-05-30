import json
import gspread
import re
from pathlib import Path
from datetime import datetime
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent

CREDENTIALS_FILE = BASE_DIR / "google_credentials.json"
ULTIMO_PROCESO_FILE = BASE_DIR / "ultimo_proceso.json"
PREFERENCIAS_FILE = BASE_DIR / "preferencias.json"

NOMBRE_SPREADSHEET = "News Agent Respuestas"

# Mapeo de las opciones del formulario a valores numéricos
SCORE_MAP = {
    "not relevant": -1,
    "indifferent":    0,
    "neutral":        1,
    "relevant":       2,
    "very relevant":  3,
}

# Índices de columna (0-based)
COL_TEMAS_INICIO = 1   # primera columna con score de tema
COL_TEMAS_FIN = 14  # última columna con score de tema (inclusive)
COL_TEXTO_LIBRE = 15  # temas, empresas o regiones específicas (texto libre)
COL_RELEVANCIA = 16  # escala 1-5 sobre la relevancia general del briefing


# ---------------------------------------------------------------------------
# Estado — rastrea la última fila procesada para detectar respuestas nuevas
# ---------------------------------------------------------------------------

def cargar_estado() -> dict:
    if ULTIMO_PROCESO_FILE.exists():
        return json.loads(ULTIMO_PROCESO_FILE.read_text(encoding="utf-8"))
    # fila 1 = encabezados; respuestas desde índice 1
    return {"ultima_fila": 1}


def guardar_estado(ultima_fila: int) -> None:
    estado = {
        "ultima_fila": ultima_fila,
        "actualizado": datetime.now().isoformat(),
    }
    ULTIMO_PROCESO_FILE.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Conexión a Google Sheets
# ---------------------------------------------------------------------------

def conectar_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE), scopes=scopes)
    return gspread.authorize(creds)


# ---------------------------------------------------------------------------
# Extracción — lee solo la última respuesta del formulario
# ---------------------------------------------------------------------------

def extraer_preferencias(encabezados: list, fila: list) -> dict:
    """
    Construye el dict de preferencias a partir de una fila de respuesta.
    - encabezados : fila 0 del sheet; cols 1-14 son los nombres de los temas
    - fila        : última fila de datos del sheet

    Estructura resultante:
      temas             → {nombre_tema: score} para cols 1-14
      temas_especificos → texto libre de col 15 (sin procesar)
      relevancia_general → entero 1-5 de col 16
    """
    temas = {}

    # Cols 1-14: convierte el texto de la opción elegida al score numérico
    for i in range(COL_TEMAS_INICIO, COL_TEMAS_FIN + 1):
        if i < len(encabezados) and i < len(fila):
            encabezado = encabezados[i].strip().lower()
            # Extrae solo el texto entre corchetes si existe, si no usa el encabezado completo
            match = re.search(r'\[(.+?)\]', encabezado)
            nombre = match.group(1) if match else encabezado
            valor = fila[i].strip().lower()
            if nombre and valor:
                temas[nombre] = SCORE_MAP.get(valor, 0)

    # Col 15: texto libre con temas, empresas o regiones específicas
    temas_especificos = fila[COL_TEXTO_LIBRE].strip(
    ) if COL_TEXTO_LIBRE < len(fila) else ""

    # Col 16: relevancia general del briefing (escala 1-5)
    relevancia_general = None
    if COL_RELEVANCIA < len(fila):
        raw = fila[COL_RELEVANCIA].strip()
        if raw.isdigit():
            relevancia_general = int(raw)

    return {
        "temas":              temas,
        "temas_especificos":  temas_especificos,
        "relevancia_general": relevancia_general,
        "ultima_actualizacion": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    estado = cargar_estado()
    # primer índice aún no procesado (1-based)
    ultima_fila = estado["ultima_fila"]

    gc = conectar_sheets()
    sheet = gc.open(NOMBRE_SPREADSHEET).sheet1
    filas = sheet.get_all_values()        # lista de listas; índice 0 = encabezados

    # filas posteriores a la última procesada
    nuevas = filas[ultima_fila:]

    if not nuevas:
        return                            # sin respuestas nuevas → salida silenciosa

    encabezados = filas[0]
    # solo la respuesta más reciente importa
    ultima_respuesta = nuevas[-1]

    preferencias = extraer_preferencias(encabezados, ultima_respuesta)

    # Sobreescribe preferencias.json completamente con la última respuesta
    PREFERENCIAS_FILE.write_text(
        json.dumps(preferencias, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    guardar_estado(ultima_fila + len(nuevas))


if __name__ == "__main__":
    main()
