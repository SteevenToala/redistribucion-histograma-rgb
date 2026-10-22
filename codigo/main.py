import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from PIL import Image


def calcular_lut_ecualizacion(canal):
    """
    Calcula de forma manual la Look-Up Table (LUT) de ecualizacion clasica por CDF:
    1. Conteo de frecuencias (histograma discreto).
    2. Probabilidad acumulada (CDF).
    3. Normalizacion con CDF_min para estirar de 0 a 255.
    """
    alto, ancho = canal.shape
    total_pixeles = alto * ancho

    # 1. Conteo de frecuencias por nivel de intensidad
    conteo = np.bincount(canal.ravel(), minlength=256).astype(np.float64)

    # 2. Probabilidad acumulada (CDF)
    prob_acumulada = np.cumsum(conteo) / total_pixeles

    # 3. Primer nivel con pixeles activos
    niveles_activos = np.where(conteo > 0)[0]
    if len(niveles_activos) == 0:
        return np.arange(256, dtype=np.uint8)

    cdf_min = prob_acumulada[niveles_activos[0]]
    rango_util = 1.0 - cdf_min if (1.0 - cdf_min) > 0 else 1.0

    # 4. Construccion de la tabla de mapeo directo (LUT)
    lut_eq = np.zeros(256, dtype=np.uint8)
    for k in range(256):
        if k >= niveles_activos[0]:
            nueva_intensidad = ((prob_acumulada[k] - cdf_min) / rango_util) * 255.0
            lut_eq[k] = np.uint8(np.clip(np.round(nueva_intensidad), 0, 255))
        else:
            lut_eq[k] = 0

    return lut_eq


def calcular_lut_especificacion(canal, tipo_objetivo='gaussiano'):
    """
    Especificacion de Histograma (Gonzalez & Woods):
    Mapea el histograma original a una distribucion objetivo deseada:
    z = G^-1( T(r) )
    Donde T(r) es la CDF del canal y G(z) es la CDF del histograma objetivo.
    """
    total = canal.size
    conteo_orig = np.bincount(canal.ravel(), minlength=256).astype(np.float64)
    cdf_orig = np.cumsum(conteo_orig) / total

    z = np.arange(256, dtype=np.float64)
    if tipo_objetivo == 'gaussiano':
        # Campana simetrica centrada en 128 con dispersion media
        p_deseada = np.exp(-((z - 128.0) ** 2) / (2.0 * (45.0 ** 2)))
    elif tipo_objetivo == 'bimodal':
        # Dos concentraciones: sombras (60) y luces (195) para alto contraste
        p_deseada = (np.exp(-((z - 60.0) ** 2) / (2.0 * (28.0 ** 2))) +
                     np.exp(-((z - 195.0) ** 2) / (2.0 * (28.0 ** 2))))
    else:
        p_deseada = np.ones(256, dtype=np.float64)

    p_deseada = p_deseada / np.sum(p_deseada)
    cdf_deseada = np.cumsum(p_deseada)

    # Inversion de la CDF: buscar para cada r el z tal que G(z) ~ T(r)
    lut_especificacion = np.zeros(256, dtype=np.uint8)
    for r in range(256):
        val_t = cdf_orig[r]
        idx_z = np.argmin(np.abs(cdf_deseada - val_t))
        lut_especificacion[r] = np.uint8(idx_z)

    return lut_especificacion


def generar_lut_canal(brillo, contraste, gamma, ecualizar_pct, lut_eq_base, lut_override=None):
    """
    Genera la LUT combinada para modificar el histograma del canal:
    - brillo: desplazamiento horizontal (offset) [-100, 100].
    - contraste: expansion / compresion alrededor del centro 128 [0.2, 3.0].
    - gamma: curvatura no lineal de medios tonos [0.2, 3.0].
    - ecualizar_pct: porcentaje de mezcla con la ecualizacion uniforme [0.0, 1.0].
    - lut_override: LUT fija opcional si se aplico una especificacion de histograma.
    """
    if lut_override is not None:
        return lut_override.copy()

    # Base de intensidades discretas de entrada [0, 255]
    r = np.arange(256, dtype=np.float64)

    # 1. Contraste y Brillo (desplazamiento y ensanchamiento del histograma)
    # v1 = contraste * (r - 128) + 128 + brillo
    v1 = contraste * (r - 128.0) + 128.0 + brillo

    # 2. Correccion Gamma (curvatura de tonos medios)
    v_norm = np.clip(v1 / 255.0, 0.0, 1.0)
    gamma_seguro = max(gamma, 0.01)
    v2 = 255.0 * (v_norm ** (1.0 / gamma_seguro))

    # 3. Mezcla ponderada con la ecualizacion clasica por CDF
    factor_eq = np.clip(ecualizar_pct, 0.0, 1.0)
    v_final = (1.0 - factor_eq) * v2 + factor_eq * lut_eq_base.astype(np.float64)

    return np.clip(np.round(v_final), 0, 255).astype(np.uint8)


def main():
    # 1. Cargar la imagen base
    carpeta_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_imagen = os.path.join(carpeta_actual, 'images.jpg')
    if not os.path.exists(ruta_imagen):
        ruta_imagen = os.path.join(carpeta_actual, 'tu_imagen.jpg')

    imagen_pil = Image.open(ruta_imagen).convert('RGB')
    matriz_original = np.array(imagen_pil)

    # Separar los tres espectros cromáticos independientes
    canal_rojo = matriz_original[:, :, 0]
    canal_verde = matriz_original[:, :, 1]
    canal_azul = matriz_original[:, :, 2]

    # Precalcular las LUTs de ecualizacion clasica
    lut_eq_rojo = calcular_lut_ecualizacion(canal_rojo)
    lut_eq_verde = calcular_lut_ecualizacion(canal_verde)
    lut_eq_azul = calcular_lut_ecualizacion(canal_azul)

    # Histogramas originales fijos (sirven como contorno de referencia)
    hist_r_orig = np.bincount(canal_rojo.ravel(), minlength=256)
    hist_g_orig = np.bincount(canal_verde.ravel(), minlength=256)
    hist_b_orig = np.bincount(canal_azul.ravel(), minlength=256)

    # Variables de estado para sobreescritura por especificacion
    estado_override = {'rojo': None, 'verde': None, 'azul': None}

    # 2. Configurar la ventana grafica interactiva
    figura = plt.figure(figsize=(15.5, 9.8))
    figura.canvas.manager.set_window_title('Modificador Interactivo de Histogramas RGB por Espectro')

    eje_x = np.arange(256)

    # --- ZONA SUPERIOR: Histogramas de los 3 Espectros ---
    # Espectro Rojo
    ax_hist_r = figura.add_axes([0.05, 0.70, 0.27, 0.23])
    ax_hist_r.step(eje_x, hist_r_orig, where='mid', color='#78909C', linestyle='--', linewidth=1.1, label='Original', zorder=2)
    ax_hist_r.fill_between(eje_x, hist_r_orig, step='mid', color='#CFD8DC', alpha=0.3, zorder=1)
    barras_r = ax_hist_r.bar(eje_x, hist_r_orig.copy(), width=1.0, color='#E53935', alpha=0.75, label='Modificado', zorder=3)
    ax_hist_r.set_xlim(0, 255)
    max_y_r = max(hist_r_orig.max(), np.bincount(lut_eq_rojo[canal_rojo].ravel(), minlength=256).max()) * 1.15
    ax_hist_r.set_ylim(0, max_y_r)
    ax_hist_r.legend(loc='upper right', fontsize=8)
    ax_hist_r.grid(True, linestyle=':', alpha=0.4)

    # Espectro Verde
    ax_hist_g = figura.add_axes([0.365, 0.70, 0.27, 0.23])
    ax_hist_g.step(eje_x, hist_g_orig, where='mid', color='#78909C', linestyle='--', linewidth=1.1, label='Original', zorder=2)
    ax_hist_g.fill_between(eje_x, hist_g_orig, step='mid', color='#CFD8DC', alpha=0.3, zorder=1)
    barras_g = ax_hist_g.bar(eje_x, hist_g_orig.copy(), width=1.0, color='#43A047', alpha=0.75, label='Modificado', zorder=3)
    ax_hist_g.set_xlim(0, 255)
    max_y_g = max(hist_g_orig.max(), np.bincount(lut_eq_verde[canal_verde].ravel(), minlength=256).max()) * 1.15
    ax_hist_g.set_ylim(0, max_y_g)
    ax_hist_g.legend(loc='upper right', fontsize=8)
    ax_hist_g.grid(True, linestyle=':', alpha=0.4)

    # Espectro Azul
    ax_hist_b = figura.add_axes([0.68, 0.70, 0.27, 0.23])
    ax_hist_b.step(eje_x, hist_b_orig, where='mid', color='#78909C', linestyle='--', linewidth=1.1, label='Original', zorder=2)
    ax_hist_b.fill_between(eje_x, hist_b_orig, step='mid', color='#CFD8DC', alpha=0.3, zorder=1)
    barras_b = ax_hist_b.bar(eje_x, hist_b_orig.copy(), width=1.0, color='#1E88E5', alpha=0.75, label='Modificado', zorder=3)
    ax_hist_b.set_xlim(0, 255)
    max_y_b = max(hist_b_orig.max(), np.bincount(lut_eq_azul[canal_azul].ravel(), minlength=256).max()) * 1.15
    ax_hist_b.set_ylim(0, max_y_b)
    ax_hist_b.legend(loc='upper right', fontsize=8)
    ax_hist_b.grid(True, linestyle=':', alpha=0.4)

    # --- ZONA MEDIA: Controles Deslizantes por Espectro ---
    # Dimensiones para sliders
    w_slider = 0.20
    h_slider = 0.016
    x_r = 0.115
    x_g = 0.430
    x_b = 0.745

    # Fila 1: Brillo / Desplazamiento horizontal
    ax_brillo_r = figura.add_axes([x_r, 0.640, w_slider, h_slider])
    ax_brillo_g = figura.add_axes([x_g, 0.640, w_slider, h_slider])
    ax_brillo_b = figura.add_axes([x_b, 0.640, w_slider, h_slider])

    slider_brillo_r = Slider(ax_brillo_r, 'Desplazamiento', -100.0, 100.0, valinit=0.0, valstep=1.0, color='#EF5350')
    slider_brillo_g = Slider(ax_brillo_g, 'Desplazamiento', -100.0, 100.0, valinit=0.0, valstep=1.0, color='#66BB6A')
    slider_brillo_b = Slider(ax_brillo_b, 'Desplazamiento', -100.0, 100.0, valinit=0.0, valstep=1.0, color='#42A5F5')

    # Fila 2: Contraste / Expansion del ancho
    ax_cont_r = figura.add_axes([x_r, 0.612, w_slider, h_slider])
    ax_cont_g = figura.add_axes([x_g, 0.612, w_slider, h_slider])
    ax_cont_b = figura.add_axes([x_b, 0.612, w_slider, h_slider])

    slider_cont_r = Slider(ax_cont_r, 'Contraste / Rango', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#EF5350')
    slider_cont_g = Slider(ax_cont_g, 'Contraste / Rango', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#66BB6A')
    slider_cont_b = Slider(ax_cont_b, 'Contraste / Rango', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#42A5F5')

    # Fila 3: Gamma / Forma de tonos medios
    ax_gamma_r = figura.add_axes([x_r, 0.584, w_slider, h_slider])
    ax_gamma_g = figura.add_axes([x_g, 0.584, w_slider, h_slider])
    ax_gamma_b = figura.add_axes([x_b, 0.584, w_slider, h_slider])

    slider_gamma_r = Slider(ax_gamma_r, 'Curvatura Gamma', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#EF5350')
    slider_gamma_g = Slider(ax_gamma_g, 'Curvatura Gamma', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#66BB6A')
    slider_gamma_b = Slider(ax_gamma_b, 'Curvatura Gamma', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#42A5F5')

    # Fila 4: Ecualizacion CDF uniforme
    ax_eq_r = figura.add_axes([x_r, 0.556, w_slider, h_slider])
    ax_eq_g = figura.add_axes([x_g, 0.556, w_slider, h_slider])
    ax_eq_b = figura.add_axes([x_b, 0.556, w_slider, h_slider])

    slider_eq_r = Slider(ax_eq_r, 'Ecualizar CDF (%)', 0.0, 100.0, valinit=0.0, valstep=1.0, color='#E53935')
    slider_eq_g = Slider(ax_eq_g, 'Ecualizar CDF (%)', 0.0, 100.0, valinit=0.0, valstep=1.0, color='#43A047')
    slider_eq_b = Slider(ax_eq_b, 'Ecualizar CDF (%)', 0.0, 100.0, valinit=0.0, valstep=1.0, color='#1E88E5')

    # --- ZONA INFERIOR: Imagen Original vs Imagen Modificada ---
    ax_img_orig = figura.add_axes([0.05, 0.10, 0.43, 0.41])
    ax_img_orig.imshow(matriz_original)
    ax_img_orig.set_title(f'Imagen Original ({matriz_original.shape[1]}x{matriz_original.shape[0]} px)', fontsize=11, fontweight='bold', pad=8)
    ax_img_orig.axis('off')

    ax_img_mod = figura.add_axes([0.52, 0.10, 0.43, 0.41])
    visor_img_mod = ax_img_mod.imshow(matriz_original.copy())
    titulo_mod = ax_img_mod.set_title('Imagen Modificada Resultante', fontsize=11, fontweight='bold', pad=8)
    ax_img_mod.axis('off')

    # Guardamos la imagen modificada actual para exportar si el usuario lo desea
    cache_resultado = {'imagen': matriz_original.copy()}

    # --- FUNCION PRINCIPAL DE ACTUALIZACION EN TIEMPO REAL ---
    def actualizar(_=None):
        # 1. Generar la LUT para cada canal segun sus controles activos
        lut_r = generar_lut_canal(slider_brillo_r.val, slider_cont_r.val, slider_gamma_r.val,
                                  slider_eq_r.val / 100.0, lut_eq_rojo, estado_override['rojo'])
        lut_g = generar_lut_canal(slider_brillo_g.val, slider_cont_g.val, slider_gamma_g.val,
                                  slider_eq_g.val / 100.0, lut_eq_verde, estado_override['verde'])
        lut_b = generar_lut_canal(slider_brillo_b.val, slider_cont_b.val, slider_gamma_b.val,
                                  slider_eq_b.val / 100.0, lut_eq_azul, estado_override['azul'])

        # 2. Mapear cada canal mediante su Look-Up Table
        canal_r_mod = lut_r[canal_rojo]
        canal_g_mod = lut_g[canal_verde]
        canal_b_mod = lut_b[canal_azul]

        # 3. Ensamblar imagen resultante RGB
        img_resultado = np.stack([canal_r_mod, canal_g_mod, canal_b_mod], axis=2)
        visor_img_mod.set_data(img_resultado)
        cache_resultado['imagen'] = img_resultado

        # 4. Calcular nuevos conteos de frecuencias de los histogramas
        hist_r_mod = np.bincount(canal_r_mod.ravel(), minlength=256)
        hist_g_mod = np.bincount(canal_g_mod.ravel(), minlength=256)
        hist_b_mod = np.bincount(canal_b_mod.ravel(), minlength=256)

        # 5. Actualizar las barras graficas
        for barra, conteo in zip(barras_r, hist_r_mod):
            barra.set_height(conteo)
        for barra, conteo in zip(barras_g, hist_g_mod):
            barra.set_height(conteo)
        for barra, conteo in zip(barras_b, hist_b_mod):
            barra.set_height(conteo)

        # 6. Actualizar titulos con metricas estadisticas en vivo
        ax_hist_r.set_title(f'Espectro Rojo | μ: {canal_r_mod.mean():.1f} | σ: {canal_r_mod.std():.1f} | [{canal_r_mod.min()}, {canal_r_mod.max()}]',
                            fontsize=9, fontweight='bold', color='#B71C1C')
        ax_hist_g.set_title(f'Espectro Verde | μ: {canal_g_mod.mean():.1f} | σ: {canal_g_mod.std():.1f} | [{canal_g_mod.min()}, {canal_g_mod.max()}]',
                            fontsize=9, fontweight='bold', color='#1B5E20')
        ax_hist_b.set_title(f'Espectro Azul | μ: {canal_b_mod.mean():.1f} | σ: {canal_b_mod.std():.1f} | [{canal_b_mod.min()}, {canal_b_mod.max()}]',
                            fontsize=9, fontweight='bold', color='#0D47A1')

        # Refrescar lienzo de Matplotlib
        figura.canvas.draw_idle()

    # Callback para cuando el usuario mueve sliders (limpia sobreescrituras)
    def on_slider_touch(_=None):
        estado_override['rojo'] = None
        estado_override['verde'] = None
        estado_override['azul'] = None
        actualizar()

    for sld in [slider_brillo_r, slider_brillo_g, slider_brillo_b,
                slider_cont_r, slider_cont_g, slider_cont_b,
                slider_gamma_r, slider_gamma_g, slider_gamma_b,
                slider_eq_r, slider_eq_g, slider_eq_b]:
        sld.on_changed(on_slider_touch)

    # --- BOTONES DE ACCION RAPIDA Y ESPECIFICACION DE FORMA ---
    ax_btn_reset = figura.add_axes([0.05, 0.025, 0.16, 0.038])
    btn_reset = Button(ax_btn_reset, 'Restablecer Todo (0)', color='#ECEFF1', hovercolor='#CFD8DC')

    ax_btn_eq = figura.add_axes([0.23, 0.025, 0.17, 0.038])
    btn_eq = Button(ax_btn_eq, 'Ecualizar Todo (100%)', color='#E0F2F1', hovercolor='#B2DFDB')

    ax_btn_gauss = figura.add_axes([0.42, 0.025, 0.18, 0.038])
    btn_gauss = Button(ax_btn_gauss, 'Forma Gaussiana (Campana)', color='#EDE7F6', hovercolor='#D1C4E9')

    ax_btn_bimodal = figura.add_axes([0.62, 0.025, 0.18, 0.038])
    btn_bimodal = Button(ax_btn_bimodal, 'Alto Contraste (Bimodal)', color='#FFF3E0', hovercolor='#FFE0B2')

    ax_btn_save = figura.add_axes([0.82, 0.025, 0.13, 0.038])
    btn_save = Button(ax_btn_save, 'Guardar Resultado', color='#E8F5E9', hovercolor='#C8E6C9')

    def accion_reset(event):
        estado_override['rojo'] = None
        estado_override['verde'] = None
        estado_override['azul'] = None
        for sld in [slider_brillo_r, slider_brillo_g, slider_brillo_b]:
            sld.set_val(0.0)
        for sld in [slider_cont_r, slider_cont_g, slider_cont_b]:
            sld.set_val(1.0)
        for sld in [slider_gamma_r, slider_gamma_g, slider_gamma_b]:
            sld.set_val(1.0)
        for sld in [slider_eq_r, slider_eq_g, slider_eq_b]:
            sld.set_val(0.0)

    def accion_ecualizar(event):
        estado_override['rojo'] = None
        estado_override['verde'] = None
        estado_override['azul'] = None
        for sld in [slider_eq_r, slider_eq_g, slider_eq_b]:
            sld.set_val(100.0)

    def accion_gaussiano(event):
        # Aplica especificacion de forma gaussiana a los 3 espectros
        estado_override['rojo'] = calcular_lut_especificacion(canal_rojo, 'gaussiano')
        estado_override['verde'] = calcular_lut_especificacion(canal_verde, 'gaussiano')
        estado_override['azul'] = calcular_lut_especificacion(canal_azul, 'gaussiano')
        actualizar()

    def accion_bimodal(event):
        # Aplica especificacion de forma bimodal (alto contraste) a los 3 espectros
        estado_override['rojo'] = calcular_lut_especificacion(canal_rojo, 'bimodal')
        estado_override['verde'] = calcular_lut_especificacion(canal_verde, 'bimodal')
        estado_override['azul'] = calcular_lut_especificacion(canal_azul, 'bimodal')
        actualizar()

    def accion_guardar(event):
        salida_img = os.path.join(carpeta_actual, 'resultado_redistribucion.png')
        salida_captura = os.path.join(carpeta_actual, 'resultado_ecualizacion.png')
        # Guardar imagen procesada
        Image.fromarray(cache_resultado['imagen']).save(salida_img)
        # Guardar captura completa de la ventana con graficos e histogramas
        figura.savefig(salida_captura, dpi=180, bbox_inches='tight')
        btn_save.label.set_text('¡Guardado con Éxito!')
        figura.canvas.draw_idle()

    btn_reset.on_clicked(accion_reset)
    btn_eq.on_clicked(accion_ecualizar)
    btn_gauss.on_clicked(accion_gaussiano)
    btn_bimodal.on_clicked(accion_bimodal)
    btn_save.on_clicked(accion_guardar)

    # Inicializar vista con los valores por defecto
    actualizar()

    plt.show()


if __name__ == '__main__':
    main()
