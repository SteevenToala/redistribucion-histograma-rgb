"""
Punto de Entrada de la Versión de Escritorio (PDI Desktop)
==========================================================
Configuración de Histogramas (Contraste) por Espectro RGB.
Desarrollado con Tkinter, Matplotlib, Pillow y NumPy.
"""

import sys
import os
import tkinter as tk

DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
if DIR_ACTUAL not in sys.path:
    sys.path.insert(0, DIR_ACTUAL)

from interfaz import AplicacionHistogramasDesktop


def main():
    root = tk.Tk()
    app = AplicacionHistogramasDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
