"""
Módulo de Transformaciones Canónicas y Avanzadas sobre Histogramas (PDI)
========================================================================

Este módulo desacopla la formulación matemática del pipeline visual:
1. Ecualización acumulativa global por CDF.
2. Límite de Picos CLAHE (Clip Limit) para mitigación de fondos uniformes.
3. Especificación de Histograma Canónica (Matching bi-LUT para Gaussiana y Rayleigh).
4. Inversión espectral (Negativo analítico).
5. Curva Sigmoide en 'S' (Contraste simultáneo de sombras y luces).
6. Recorte de rango dinámico de niveles (Windowing / r_min, r_max).
7. Operaciones afines de brillo (desplazamiento) y contraste (estiramiento).
8. Corrección de Medios Tonos (Ley de Potencias / Gamma).
"""

import numpy as np


def generar_distribucion_objetivo(tipo='gaussiana'):
    """
    Genera la función de distribución acumulada (CDF) objetivo normalizada
    para Especificación de Histograma según la teoría de González & Woods.
    """
    x = np.arange(256, dtype=np.float64)
    if tipo == 'gaussiana':
        mu, sigma = 127.5, 42.0
        p = np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    elif tipo == 'rayleigh':
        alpha = 65.0
        p = (x / (alpha ** 2)) * np.exp(-(x ** 2) / (2.0 * (alpha ** 2)))
    else:
        p = np.ones(256, dtype=np.float64)

    p /= p.sum()
    return np.cumsum(p)


def calcular_lut_base(canal, modo='cdf', clip_factor=1.0):
    """
    Calcula la Look-Up Table (LUT) de 256 niveles de la transformación de partida.
    """
    conteo = np.bincount(canal.ravel(), minlength=256).astype(np.float64)

    # 1. Límite de Picos (Clip Limit CLAHE)
    if clip_factor < 0.99:
        media_bin = conteo.mean()
        umbral = media_bin + clip_factor * (conteo.max() - media_bin)
        exceso = np.maximum(conteo - umbral, 0.0)
        conteo = np.minimum(conteo, umbral) + (exceso.sum() / 256.0)

    prob_acumulada = np.cumsum(conteo) / conteo.sum()

    if modo == 'cdf':
        niveles_activos = np.where(conteo > 0)[0]
        if len(niveles_activos) == 0:
            return np.arange(256, dtype=np.uint8)
        cdf_min = prob_acumulada[niveles_activos[0]]
        rango_util = 1.0 - cdf_min if (1.0 - cdf_min) > 0 else 1.0
        nueva = np.zeros(256, dtype=np.float64)
        for k in range(256):
            if k >= niveles_activos[0]:
                nueva[k] = ((prob_acumulada[k] - cdf_min) / rango_util) * 255.0
            else:
                nueva[k] = 0.0
        return np.clip(np.round(nueva), 0, 255).astype(np.uint8)

    elif modo in ['gaussiana', 'rayleigh']:
        cdf_objetivo = generar_distribucion_objetivo(modo)
        lut_match = np.zeros(256, dtype=np.uint8)
        for k in range(256):
            diff = np.abs(cdf_objetivo - prob_acumulada[k])
            lut_match[k] = np.argmin(diff)
        return lut_match

    elif modo == 'negativo':
        return np.arange(255, -1, -1, dtype=np.uint8)

    return np.arange(256, dtype=np.uint8)


def aplicar_curva_sigmoide(v_norm, factor_s):
    """
    Aplica una función logística sigmoide normalizada en [0.0, 1.0] centrada en 0.5.
    """
    if factor_s <= 0.01:
        return v_norm
    k = factor_s * 5.0

    def sig(x):
        return 1.0 / (1.0 + np.exp(-k * (x - 0.5)))

    s0 = sig(0.0)
    s1 = sig(1.0)
    return np.clip((sig(v_norm) - s0) / (s1 - s0), 0.0, 1.0)


def generar_lut_espectro(contraste, gamma, curva_s, r_min, r_max,
                         fuerza_eq, lut_modo_base, desplazamiento=0.0):
    """
    Construye la Look-Up Table (LUT) integrada de 256 niveles para redistribución de histograma.
    El procesamiento no traslada el histograma rígidamente, sino que redistribuye las frecuencias
    mediante estiramiento dinámico (r_min, r_max), contraste (alfa) y curvatura no lineal (gamma).
    """
    r_identidad = np.arange(256, dtype=np.float64)

    # 1. Ponderación por fuerza de ecualización (alpha-blending)
    r_base = (1.0 - fuerza_eq) * r_identidad + fuerza_eq * lut_modo_base.astype(np.float64)

    # 2. Redistribución por ventana de rango dinámico [r_min, r_max] (Estiramiento Canónico)
    if r_max <= r_min:
        r_max = r_min + 1.0
    v_niveles = np.clip((r_base - r_min) / (r_max - r_min) * 255.0, 0.0, 255.0)

    # 3. Estiramiento / Expansión de Contraste respecto al punto medio (sin traslación rígida)
    v_affine = contraste * (v_niveles - 128.0) + 128.0
    v_norm = np.clip(v_affine / 255.0, 0.0, 1.0)

    # 4. Curva Sigmoide en 'S'
    v_sigmoide = aplicar_curva_sigmoide(v_norm, curva_s)

    # 5. Corrección Gamma de medios tonos (Redistribución no lineal de densidades)
    gamma_seguro = max(gamma, 0.05)
    v_gamma = 255.0 * (v_sigmoide ** (1.0 / gamma_seguro))

    return np.clip(np.round(v_gamma), 0, 255).astype(np.uint8)
