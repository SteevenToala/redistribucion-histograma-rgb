"""
Módulo de Transformaciones y Procesamiento de Histogramas RGB (PDI)
===================================================================
Implementación canónica y vectorizada del algoritmo de:
1. Descomposición espectral de imágenes tridimensionales RGB.
2. Conteo de histogramas discretos de frecuencias (0 a 255).
3. Manipulación de contraste mediante Ecualización por Meseta
   (Plateau Histogram Equalization - PHE) y Recorte de Picos con
   Redistribución Uniforme de Masa y Conservación Estricta de Píxeles.
4. Síntesis de tablas de consulta (LUT) mediante CDF normalizada.
"""

import numpy as np


def descomponer_espectros(img_rgb: np.ndarray):
    """
    Descompone una imagen RGB (M x N x 3) en sus tres espectros cromáticos independientes.
    Retorna matrices 2D (alto x ancho): canal_r, canal_g, canal_b.
    """
    if img_rgb.ndim != 3 or img_rgb.shape[2] != 3:
        raise ValueError("La imagen debe poseer 3 canales cromáticos (RGB).")
    canal_r = img_rgb[:, :, 0]
    canal_g = img_rgb[:, :, 1]
    canal_b = img_rgb[:, :, 2]
    return canal_r, canal_g, canal_b


def generar_vista_espectro_color(canal_2d: np.ndarray, color_canal: str) -> np.ndarray:
    """
    Genera una representación visual RGB teñida con su color primario:
    - 'r': canal en canal rojo, otros en 0.
    - 'g': canal en canal verde, otros en 0.
    - 'b': canal en canal azul, otros en 0.
    - 'gris': canal replicado en los 3 canales.
    """
    ceros = np.zeros_like(canal_2d)
    if color_canal == 'r':
        return np.dstack([canal_2d, ceros, ceros])
    elif color_canal == 'g':
        return np.dstack([ceros, canal_2d, ceros])
    elif color_canal == 'b':
        return np.dstack([ceros, ceros, canal_2d])
    else:
        return np.dstack([canal_2d, canal_2d, canal_2d])


def calcular_histograma_discreto(canal_2d: np.ndarray) -> np.ndarray:
    """Calcula el vector de 256 frecuencias absolutas discretas."""
    return np.bincount(canal_2d.ravel(), minlength=256).astype(np.float64)


def calcular_estadisticas_canal(canal_2d: np.ndarray):
    """Calcula la media (brillo) y desviación estándar (contraste) del canal."""
    media = float(np.mean(canal_2d))
    desv = float(np.std(canal_2d))
    return round(media, 2), round(desv, 2)


def redistribuir_picos_canal(canal: np.ndarray, factor_redistribucion: float):
    """
    Algoritmo de Ecualización de Histograma por Meseta (PHE) y Recorte de Picos
    con Redistribución Uniforme de Masa (Conservación Estricta de Píxeles):

    Parámetros:
    - canal: Matriz 2D de intensidades discretas en [0, 255].
    - factor_redistribucion: Valor numérico entre 0.0 (0%) y 1.0 (100%).

    Retorna:
    - canal_out: Matriz procesada de salida (mismo tipo uint8 y dimensiones).
    - hist_orig: Histograma discreto original (256 casilleros).
    - hist_mod: Histograma redistribuido resultante (256 casilleros).
    - total_exceso: Cantidad exacta de píxeles transferidos desde los picos.
    - umbral: Nivel de corte dinámico de meseta aplicado.
    """
    total_px = canal.size
    hist_orig = np.bincount(canal.ravel(), minlength=256).astype(np.float64)
    media_bin = total_px / 256.0
    max_bin = float(hist_orig.max())

    factor = float(np.clip(factor_redistribucion, 0.0, 1.0))
    if factor <= 0.0001:
        return canal.copy(), hist_orig, hist_orig.copy(), 0, max_bin

    # 1. Umbral dinámico de meseta U(f) descendente hacia la media teórica
    umbral = max_bin - factor * (max_bin - media_bin)
    exceso = np.maximum(hist_orig - umbral, 0.0)
    total_exceso = float(exceso.sum())

    # 2. Redistribución uniforme de los píxeles de exceso a los 256 niveles (+ E / 256)
    hist_mod = np.minimum(hist_orig, umbral) + (total_exceso / 256.0)

    # 3. Función de distribución acumulada (CDF) normalizada
    prob_acum = np.cumsum(hist_mod) / total_px
    niveles_activos = np.where(hist_mod > 0)[0]
    cdf_min = prob_acum[niveles_activos[0]] if len(niveles_activos) > 0 else 0.0
    rango = 1.0 - cdf_min if (1.0 - cdf_min) > 0 else 1.0

    # 4. Síntesis de Look-Up Table (LUT) de 256 niveles con interpolación lineal continua
    lut_eq = np.clip(np.round(((prob_acum - cdf_min) / rango) * 255.0), 0, 255)
    r_id = np.arange(256, dtype=np.float64)
    lut_final = np.clip(np.round((1.0 - factor) * r_id + factor * lut_eq), 0, 255).astype(np.uint8)

    # 5. Mapeo directo vectorizado O(1)
    canal_out = lut_final[canal]
    return canal_out, hist_orig, hist_mod, int(np.round(total_exceso)), umbral


def procesar_imagen_rgb_completa(img_rgb: np.ndarray, factor_r: float, factor_g: float, factor_b: float):
    """
    Ejecuta el procesamiento desacoplado en los 3 espectros y fusiona el resultado RGB.
    """
    c_r, c_g, c_b = descomponer_espectros(img_rgb)

    c_out_r, h_o_r, h_m_r, exc_r, umb_r = redistribuir_picos_canal(c_r, factor_r)
    c_out_g, h_o_g, h_m_g, exc_g, umb_g = redistribuir_picos_canal(c_g, factor_g)
    c_out_b, h_o_b, h_m_b, exc_b, umb_b = redistribuir_picos_canal(c_b, factor_b)

    img_out_rgb = np.dstack([c_out_r, c_out_g, c_out_b])

    estadisticas = {
        'orig': {
            'r': calcular_estadisticas_canal(c_r),
            'g': calcular_estadisticas_canal(c_g),
            'b': calcular_estadisticas_canal(c_b)
        },
        'mod': {
            'r': calcular_estadisticas_canal(c_out_r),
            'g': calcular_estadisticas_canal(c_out_g),
            'b': calcular_estadisticas_canal(c_out_b)
        },
        'exceso': {'r': exc_r, 'g': exc_g, 'b': exc_b},
        'umbrales': {'r': umb_r, 'g': umb_g, 'b': umb_b}
    }

    histogramas = {
        'orig': {'r': h_o_r, 'g': h_o_g, 'b': h_o_b},
        'mod': {'r': h_m_r, 'g': h_m_g, 'b': h_m_b}
    }

    canales_espectros = {
        'orig': {'r': c_r, 'g': c_g, 'b': c_b},
        'mod': {'r': c_out_r, 'g': c_out_g, 'b': c_out_b}
    }

    return img_out_rgb, histogramas, estadisticas, canales_espectros
