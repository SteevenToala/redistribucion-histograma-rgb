"""
Módulo de Utilidades y Manejo de Imágenes (PDI Escritorio)
===========================================================
Conversión de formatos NumPy <-> PIL <-> ImageTk, redimensionamiento
con preservación de relación de aspecto y persistencia en disco.
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageTk


def cargar_imagen_rgb(ruta_archivo: str) -> np.ndarray:
    """
    Carga una imagen desde el disco y la retorna en formato NumPy RGB (uint8).
    Soporta rutas con caracteres especiales en Windows.
    """
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_archivo}")

    # Lectura robusta con imdecode para evitar fallos por rutas con espacios o tildes
    with open(ruta_archivo, 'rb') as f:
        bytes_datos = np.frombuffer(f.read(), dtype=np.uint8)
        img_bgr = cv2.imdecode(bytes_datos, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise ValueError(f"El archivo no es una imagen digital válida: {ruta_archivo}")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return img_rgb


def guardar_imagen_rgb(img_rgb: np.ndarray, ruta_destino: str) -> bool:
    """
    Guarda una imagen NumPy RGB en disco convirtiéndola adecuadamente a BGR.
    """
    dir_padre = os.path.dirname(ruta_destino)
    if dir_padre:
        os.makedirs(dir_padre, exist_ok=True)

    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    ext = os.path.splitext(ruta_destino)[1]
    if not ext:
        ext = '.png'
        ruta_destino += ext

    exito, buffer = cv2.imencode(ext, img_bgr)
    if exito:
        with open(ruta_destino, 'wb') as f:
            f.write(buffer)
        return True
    return False


def numpy_a_photoimage(matriz_rgb: np.ndarray, max_ancho: int, max_alto: int):
    """
    Escala la matriz NumPy manteniendo la relación de aspecto original
    y retorna un objeto ImageTk.PhotoImage listo para renderizar en Tkinter.
    """
    alto, ancho = matriz_rgb.shape[:2]
    if ancho == 0 or alto == 0:
        return None, 0, 0

    factor_ancho = max_ancho / float(ancho)
    factor_alto = max_alto / float(alto)
    factor = min(factor_ancho, factor_alto, 1.0)  # Evita sobre-escalar si cabe bien

    nuevo_ancho = max(1, int(round(ancho * factor)))
    nuevo_alto = max(1, int(round(alto * factor)))

    img_pil = Image.fromarray(matriz_rgb)
    img_redim = img_pil.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)
    img_tk = ImageTk.PhotoImage(img_redim)
    return img_tk, nuevo_ancho, nuevo_alto
