import os
import time
import tempfile
import subprocess
from pathlib import Path

import requests
import win32print


BASE_URL = "https://wa.jupconnect.net"
ADMIN_PASSWORD = "admin123"
CHECK_SECONDS = 4

# Déjalo vacío para usar la impresora predeterminada.
# Si quieres forzar Epson, pon exactamente el nombre de Windows.
PRINTER_NAME = ""


def get_default_printer():
    if PRINTER_NAME.strip():
        return PRINTER_NAME.strip()
    return win32print.GetDefaultPrinter()


def download_pdf(session, pdf_url, order_id):
    url = BASE_URL + pdf_url
    out = Path(tempfile.gettempdir()) / f"abastos_nota_{order_id}.pdf"

    r = session.get(url, timeout=30)
    r.raise_for_status()

    out.write_bytes(r.content)
    return out


def print_pdf(path):
    printer = get_default_printer()
    print(f"Imprimiendo en: {printer}")
    print(f"Archivo: {path}")

    # Usa el visor PDF predeterminado de Windows.
    # Importante: debe existir una app PDF instalada que soporte el verbo print.
    os.startfile(str(path), "print")


def main():
    print("===================================")
    print(" Abastos JBot - Agente de impresión")
    print("===================================")
    print(f"Servidor: {BASE_URL}")
    print(f"Intervalo: {CHECK_SECONDS}s")
    print(f"Impresora: {get_default_printer()}")
    print("")
    print("Deja esta ventana abierta.")
    print("")

    session = requests.Session()

    while True:
        try:
            r = session.get(f"{BASE_URL}/admin/impresion/siguiente", timeout=20)
            r.raise_for_status()
            data = r.json()

            if not data.get("ok"):
                print("Respuesta no OK:", data)
                time.sleep(CHECK_SECONDS)
                continue

            if data.get("printing_enabled") is False:
                print("Impresión automática desactivada en panel.")
                time.sleep(CHECK_SECONDS)
                continue

            job = data.get("job")
            if not job:
                time.sleep(CHECK_SECONDS)
                continue

            order_id = job["order_id"]
            folio = job["folio"]
            pdf_url = job["pdf_url"]

            print(f"Nuevo trabajo: pedido {order_id}, folio {folio}")

            pdf_path = download_pdf(session, pdf_url, order_id)
            print_pdf(pdf_path)

            # Espera breve para que Windows mande el trabajo a cola.
            time.sleep(8)

            mark = session.post(f"{BASE_URL}/admin/impresion/{order_id}/impreso", timeout=20)
            print("Marcado como impreso:", mark.status_code)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
