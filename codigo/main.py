"""
Punto de Entrada Principal del Proyecto (PDI)
=============================================
Redistribución Canónica de Histogramas RGB por Espectro.
Inicia el servidor Flask y abre automáticamente la interfaz interactiva.
"""
import sys
import os
import threading

DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
if DIR_ACTUAL not in sys.path:
    sys.path.insert(0, DIR_ACTUAL)

from app import app, buscar_puerto_libre, abrir_navegador

if __name__ == "__main__":
    puerto = buscar_puerto_libre(5050)
    print("=" * 65)
    print("  REDISTRIBUCIÓN CANÓNICA DE HISTOGRAMAS RGB - FLASK (PDI)")
    print(f"  Interfaz web disponible en: http://127.0.0.1:{puerto}")
    print("=" * 65)
    threading.Timer(1.2, abrir_navegador, args=[puerto]).start()
    app.run(host="127.0.0.1", port=puerto, debug=False)
