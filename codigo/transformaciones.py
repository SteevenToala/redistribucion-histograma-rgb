"""
Módulo de Transformaciones Canónicas sobre Histogramas RGB (PDI)
================================================================

Implementación canónica del algoritmo de Redistribución de Píxeles por Recorte
Uniforme de Picos (Peak Clipping & Mass Redistribution) según la teoría de PDI:
1. Conteo del histograma discreto de frecuencias (0 a 255).
2. Cálculo de la media uniforme teórica y del pico máximo.
3. Determinación del umbral dinámico de corte U a partir del factor (0.0 a 1.0).
4. Extracción del volumen de píxeles excedentes de los picos saturados.
5. Redistribución uniforme de los píxeles excedentes a todos los 256 niveles.
6. Síntesis de la tabla de consulta (LUT) de 256 niveles mediante CDF normalizada.
7. Mapeo determinista de punto O(1) con conservación estricta de masa de píxeles.
"""

import numpy as np


def redistribuir_picos_canal(canal: np.ndarray, factor_redistribucion: float):
    """
    Redistribución canónica de píxeles mediante recorte uniforme de picos:
    
    Parámetros:
    - canal: Matriz 2D (alto x ancho) con niveles de intensidad en [0, 255].
    - factor_redistribucion: Valor numérico entre 0.0 (0%) y 1.0 (100%).
    
    Retorna:
    - canal_out: Matriz con los píxeles redistribuidos (mismo tamaño y tipo).
    - hist_orig: Histograma discreto original (256 bins).
    - hist_mod: Histograma redistribuido resultante (256 bins, masa conservada).
    - total_exceso: Cantidad total de píxeles transferidos de picos hacia los demás niveles.
    """
    total_px = canal.size
    hist_orig = np.bincount(canal.ravel(), minlength=256).astype(np.float64)
    media_bin = total_px / 256.0
    max_bin = float(hist_orig.max())

    factor = float(np.clip(factor_redistribucion, 0.0, 1.0))
    if factor <= 0.001:
        return canal.copy(), hist_orig, hist_orig.copy(), 0

    # 1. Umbral dinámico de corte descendente hacia la media teórica
    umbral = max_bin - factor * (max_bin - media_bin)
    exceso = np.maximum(hist_orig - umbral, 0.0)
    total_exceso = float(exceso.sum())

    # 2. Redistribución uniforme de los píxeles de exceso a los 256 casilleros
    hist_mod = np.minimum(hist_orig, umbral) + (total_exceso / 256.0)

    # 3. Función de distribución acumulada (CDF) del histograma redistribuido
    prob_acum = np.cumsum(hist_mod) / total_px
    niveles_activos = np.where(hist_mod > 0)[0]
    cdf_min = prob_acum[niveles_activos[0]] if len(niveles_activos) > 0 else 0.0
    rango = 1.0 - cdf_min if (1.0 - cdf_min) > 0 else 1.0

    # 4. Síntesis de la Look-Up Table (LUT) de 256 niveles
    lut_eq = np.clip(np.round(((prob_acum - cdf_min) / rango) * 255.0), 0, 255)
    r_id = np.arange(256, dtype=np.float64)
    lut_final = np.clip(np.round((1.0 - factor) * r_id + factor * lut_eq), 0, 255).astype(np.uint8)

    # 5. Mapeo de punto vectorizado en memoria O(1)
    canal_out = lut_final[canal]
    return canal_out, hist_orig, hist_mod, int(np.round(total_exceso))
