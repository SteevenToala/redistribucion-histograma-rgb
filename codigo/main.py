import os
import tkinter as tk
from tkinter import filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from PIL import Image


def abrir_dialogo_archivo():
    """Abre un explorador de archivos nativo para importar una imagen."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    ruta = filedialog.askopenfilename(
        title="Seleccionar Imagen para Procesar",
        filetypes=[
            ("Archivos de Imagen", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff"),
            ("Todos los archivos", "*.*")
        ]
    )
    root.destroy()
    return ruta


def guardar_dialogo_archivo():
    """Abre un explorador de archivos nativo para exportar la imagen resultante."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    ruta = filedialog.asksaveasfilename(
        title="Exportar Imagen Modificada",
        defaultextension=".png",
        filetypes=[
            ("Imagen PNG (*.png)", "*.png"),
            ("Imagen JPEG (*.jpg)", "*.jpg"),
            ("Todos los archivos", "*.*")
        ]
    )
    root.destroy()
    return ruta


def calcular_lut_ecualizacion(canal):
    """
    Calcula de forma manual y canónica la Look-Up Table (LUT) de ecualización por CDF:
    1. Conteo de frecuencias discretas (histograma).
    2. Función de probabilidad acumulada (CDF).
    3. Normalización con CDF_min para estirar de 0 a 255.
    """
    alto, ancho = canal.shape
    total_pixeles = alto * ancho

    # 1. Conteo de frecuencias (histograma)
    conteo = np.bincount(canal.ravel(), minlength=256).astype(np.float64)

    # 2. Probabilidad acumulada (CDF)
    prob_acumulada = np.cumsum(conteo) / total_pixeles

    # 3. Primer nivel con píxeles presentes en la imagen
    niveles_activos = np.where(conteo > 0)[0]
    if len(niveles_activos) == 0:
        return np.arange(256, dtype=np.uint8)

    cdf_min = prob_acumulada[niveles_activos[0]]
    rango_util = 1.0 - cdf_min if (1.0 - cdf_min) > 0 else 1.0

    # 4. Tabla de correspondencia directa (LUT)
    lut_eq = np.zeros(256, dtype=np.uint8)
    for k in range(256):
        if k >= niveles_activos[0]:
            nueva_intensidad = ((prob_acumulada[k] - cdf_min) / rango_util) * 255.0
            lut_eq[k] = np.uint8(np.clip(np.round(nueva_intensidad), 0, 255))
        else:
            lut_eq[k] = 0

    return lut_eq


def generar_lut_canal(desplazamiento, contraste, gamma, usar_ecualizacion, lut_eq_base):
    """
    Operaciones de punto canónicas en PDI (Procesamiento Digital de Imágenes):
    1. Base: Identidad original o Ecualización por CDF (según botón de acción).
    2. Desplazamiento (Brillo): traslada el histograma a la izquierda o derecha.
    3. Estiramiento (Contraste): ensancha o comprime el ancho del histograma alrededor de 128.
    4. Curvatura Gamma (Ley de Potencias): deforma la curva alterando los tonos medios.
    """
    if usar_ecualizacion:
        r_base = lut_eq_base.astype(np.float64)
    else:
        r_base = np.arange(256, dtype=np.float64)

    # 1. Contraste (estiramiento del histograma) y Desplazamiento (traslación horizontal)
    v1 = contraste * (r_base - 128.0) + 128.0 + desplazamiento

    # 2. Curvatura Gamma no lineal sobre tonos medios
    v_norm = np.clip(v1 / 255.0, 0.0, 1.0)
    gamma_seguro = max(gamma, 0.05)
    v2 = 255.0 * (v_norm ** (1.0 / gamma_seguro))

    return np.clip(np.round(v2), 0, 255).astype(np.uint8)


def main():
    # 1. Cargar la imagen inicial predeterminada
    carpeta_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_imagen = os.path.join(carpeta_actual, 'images.jpg')
    if not os.path.exists(ruta_imagen):
        ruta_imagen = os.path.join(carpeta_actual, 'tu_imagen.jpg')

    imagen_pil = Image.open(ruta_imagen).convert('RGB')
    matriz_original = np.array(imagen_pil)

    # Estructura central de datos para permitir recarga dinámica al importar
    datos = {
        'matriz': matriz_original,
        'canal_r': matriz_original[:, :, 0],
        'canal_g': matriz_original[:, :, 1],
        'canal_b': matriz_original[:, :, 2],
        'lut_eq_r': None,
        'lut_eq_g': None,
        'lut_eq_b': None,
        'hist_r_orig': None,
        'hist_g_orig': None,
        'hist_b_orig': None,
        'ecualizado': False,
        'cache_resultado': matriz_original.copy()
    }

    def recalcular_bases():
        datos['lut_eq_r'] = calcular_lut_ecualizacion(datos['canal_r'])
        datos['lut_eq_g'] = calcular_lut_ecualizacion(datos['canal_g'])
        datos['lut_eq_b'] = calcular_lut_ecualizacion(datos['canal_b'])
        datos['hist_r_orig'] = np.bincount(datos['canal_r'].ravel(), minlength=256)
        datos['hist_g_orig'] = np.bincount(datos['canal_g'].ravel(), minlength=256)
        datos['hist_b_orig'] = np.bincount(datos['canal_b'].ravel(), minlength=256)

    recalcular_bases()

    # 2. Configurar la ventana interactiva
    figura = plt.figure(figsize=(15.5, 9.8))
    figura.canvas.manager.set_window_title('Ecualizador y Modificador Canónico de Histogramas RGB')

    eje_x = np.arange(256)

    # --- ZONA SUPERIOR: Imágenes lado a lado (Original vs Resultante) ---
    ax_img_orig = figura.add_axes([0.05, 0.54, 0.43, 0.41])
    visor_img_orig = ax_img_orig.imshow(datos['matriz'])
    titulo_orig = ax_img_orig.set_title(f'Imagen Original ({datos["matriz"].shape[1]}x{datos["matriz"].shape[0]} px)', fontsize=11, fontweight='bold', pad=8)
    ax_img_orig.axis('off')

    ax_img_mod = figura.add_axes([0.52, 0.54, 0.43, 0.41])
    visor_img_mod = ax_img_mod.imshow(datos['matriz'].copy())
    titulo_mod = ax_img_mod.set_title('Imagen Resultante: [Original sin Modificaciones]', fontsize=11, fontweight='bold', pad=8)
    ax_img_mod.axis('off')

    # --- ZONA MEDIA: Histogramas de los 3 Espectros ---
    # Espectro Rojo
    ax_hist_r = figura.add_axes([0.05, 0.22, 0.27, 0.23])
    linea_orig_r = ax_hist_r.step(eje_x, datos['hist_r_orig'], where='mid', color='#78909C', linestyle='--', linewidth=1.1, label='Original', zorder=2)[0]
    barras_r = ax_hist_r.bar(eje_x, datos['hist_r_orig'].copy(), width=1.0, color='#E53935', alpha=0.75, label='Actual', zorder=3)
    ax_hist_r.set_xlim(0, 255)
    ax_hist_r.set_ylim(0, datos['hist_r_orig'].max() * 1.15)
    ax_hist_r.legend(loc='upper right', fontsize=8)
    ax_hist_r.grid(True, linestyle=':', alpha=0.4)

    # Espectro Verde
    ax_hist_g = figura.add_axes([0.365, 0.22, 0.27, 0.23])
    linea_orig_g = ax_hist_g.step(eje_x, datos['hist_g_orig'], where='mid', color='#78909C', linestyle='--', linewidth=1.1, label='Original', zorder=2)[0]
    barras_g = ax_hist_g.bar(eje_x, datos['hist_g_orig'].copy(), width=1.0, color='#43A047', alpha=0.75, label='Actual', zorder=3)
    ax_hist_g.set_xlim(0, 255)
    ax_hist_g.set_ylim(0, datos['hist_g_orig'].max() * 1.15)
    ax_hist_g.legend(loc='upper right', fontsize=8)
    ax_hist_g.grid(True, linestyle=':', alpha=0.4)

    # Espectro Azul
    ax_hist_b = figura.add_axes([0.68, 0.22, 0.27, 0.23])
    linea_orig_b = ax_hist_b.step(eje_x, datos['hist_b_orig'], where='mid', color='#78909C', linestyle='--', linewidth=1.1, label='Original', zorder=2)[0]
    barras_b = ax_hist_b.bar(eje_x, datos['hist_b_orig'].copy(), width=1.0, color='#1E88E5', alpha=0.75, label='Actual', zorder=3)
    ax_hist_b.set_xlim(0, 255)
    ax_hist_b.set_ylim(0, datos['hist_b_orig'].max() * 1.15)
    ax_hist_b.legend(loc='upper right', fontsize=8)
    ax_hist_b.grid(True, linestyle=':', alpha=0.4)

    # --- ZONA INFERIOR-MEDIA: Sliders debajo de cada histograma ---
    w_slider = 0.205
    h_slider = 0.017
    x_r = 0.115
    x_g = 0.430
    x_b = 0.745

    # Fila 1: Desplazamiento (Brillo / Offset)
    ax_brillo_r = figura.add_axes([x_r, 0.165, w_slider, h_slider])
    ax_brillo_g = figura.add_axes([x_g, 0.165, w_slider, h_slider])
    ax_brillo_b = figura.add_axes([x_b, 0.165, w_slider, h_slider])

    slider_brillo_r = Slider(ax_brillo_r, 'Desplazamiento', -120.0, 120.0, valinit=0.0, valstep=1.0, color='#EF5350')
    slider_brillo_g = Slider(ax_brillo_g, 'Desplazamiento', -120.0, 120.0, valinit=0.0, valstep=1.0, color='#66BB6A')
    slider_brillo_b = Slider(ax_brillo_b, 'Desplazamiento', -120.0, 120.0, valinit=0.0, valstep=1.0, color='#42A5F5')

    # Fila 2: Contraste (Estiramiento de la base)
    ax_cont_r = figura.add_axes([x_r, 0.133, w_slider, h_slider])
    ax_cont_g = figura.add_axes([x_g, 0.133, w_slider, h_slider])
    ax_cont_b = figura.add_axes([x_b, 0.133, w_slider, h_slider])

    slider_cont_r = Slider(ax_cont_r, 'Contraste (x)', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#EF5350')
    slider_cont_g = Slider(ax_cont_g, 'Contraste (x)', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#66BB6A')
    slider_cont_b = Slider(ax_cont_b, 'Contraste (x)', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#42A5F5')

    # Fila 3: Gamma (Curvatura de tonos medios)
    ax_gamma_r = figura.add_axes([x_r, 0.101, w_slider, h_slider])
    ax_gamma_g = figura.add_axes([x_g, 0.101, w_slider, h_slider])
    ax_gamma_b = figura.add_axes([x_b, 0.101, w_slider, h_slider])

    slider_gamma_r = Slider(ax_gamma_r, 'Gamma (γ)', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#EF5350')
    slider_gamma_g = Slider(ax_gamma_g, 'Gamma (γ)', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#66BB6A')
    slider_gamma_b = Slider(ax_gamma_b, 'Gamma (γ)', 0.2, 3.0, valinit=1.0, valstep=0.05, color='#42A5F5')

    # --- ZONA INFERIOR: Botonera de Acciones (Importar, Modo Ecualización, Reset, Exportar) ---
    ax_btn_importar = figura.add_axes([0.06, 0.024, 0.20, 0.040])
    btn_importar = Button(ax_btn_importar, 'Importar Imagen', color='#E1F5FE', hovercolor='#B3E5FC')

    ax_btn_eq = figura.add_axes([0.28, 0.024, 0.27, 0.040])
    btn_eq = Button(ax_btn_eq, 'Modo Ecualizacion CDF: OFF', color='#ECEFF1', hovercolor='#CFD8DC')

    ax_btn_reset = figura.add_axes([0.57, 0.024, 0.20, 0.040])
    btn_reset = Button(ax_btn_reset, 'Restablecer Todo', color='#ECEFF1', hovercolor='#CFD8DC')

    ax_btn_exportar = figura.add_axes([0.79, 0.024, 0.16, 0.040])
    btn_exportar = Button(ax_btn_exportar, 'Exportar Imagen', color='#E8F5E9', hovercolor='#C8E6C9')

    def actualizar_aspecto_boton_eq():
        """Actualiza el color y texto del botón de ecualización para que el usuario SIEMPRE sepa su estado."""
        if datos['ecualizado']:
            btn_eq.color = '#00897B'
            btn_eq.hovercolor = '#00796B'
            btn_eq.label.set_text('[ACTIVO] Ecualizacion CDF: ON')
            btn_eq.label.set_color('#FFFFFF')
            btn_eq.label.set_fontweight('bold')
            ax_btn_eq.set_facecolor('#00897B')
        else:
            btn_eq.color = '#ECEFF1'
            btn_eq.hovercolor = '#CFD8DC'
            btn_eq.label.set_text('Modo Ecualizacion CDF: OFF')
            btn_eq.label.set_color('#37474F')
            btn_eq.label.set_fontweight('normal')
            ax_btn_eq.set_facecolor('#ECEFF1')

    # --- ACTUALIZACIÓN DINÁMICA DE HISTOGRAMAS EN TIEMPO REAL ---
    def actualizar(_=None):
        # 1. Construir las Look-Up Tables canónicas
        lut_r = generar_lut_canal(slider_brillo_r.val, slider_cont_r.val, slider_gamma_r.val,
                                  datos['ecualizado'], datos['lut_eq_r'])
        lut_g = generar_lut_canal(slider_brillo_g.val, slider_cont_g.val, slider_gamma_g.val,
                                  datos['ecualizado'], datos['lut_eq_g'])
        lut_b = generar_lut_canal(slider_brillo_b.val, slider_cont_b.val, slider_gamma_b.val,
                                  datos['ecualizado'], datos['lut_eq_b'])

        # 2. Aplicar mapeo determinista por canal
        canal_r_mod = lut_r[datos['canal_r']]
        canal_g_mod = lut_g[datos['canal_g']]
        canal_b_mod = lut_b[datos['canal_b']]

        # 3. Ensamblar imagen resultante RGB
        img_resultado = np.stack([canal_r_mod, canal_g_mod, canal_b_mod], axis=2)
        visor_img_mod.set_data(img_resultado)
        datos['cache_resultado'] = img_resultado

        # 4. Calcular los nuevos histogramas reales
        hist_r_mod = np.bincount(canal_r_mod.ravel(), minlength=256)
        hist_g_mod = np.bincount(canal_g_mod.ravel(), minlength=256)
        hist_b_mod = np.bincount(canal_b_mod.ravel(), minlength=256)

        # 5. Actualizar la altura de las barras
        for barra, conteo in zip(barras_r, hist_r_mod):
            barra.set_height(conteo)
        for barra, conteo in zip(barras_g, hist_g_mod):
            barra.set_height(conteo)
        for barra, conteo in zip(barras_b, hist_b_mod):
            barra.set_height(conteo)

        # 6. Autoescala dinámica del eje Y para que el histograma NUNCA se recorte ni se aplaste
        def calcular_limite_y(hist_mod, hist_orig):
            pico_interior = np.max(hist_mod[1:255]) if len(hist_mod) > 2 else hist_mod.max()
            base_max = max(pico_interior, hist_orig.max())
            pico_extremos = max(hist_mod[0], hist_mod[255])
            if pico_extremos > 3 * base_max:
                return base_max * 1.35
            return max(base_max, pico_extremos) * 1.15

        ax_hist_r.set_ylim(0, calcular_limite_y(hist_r_mod, datos['hist_r_orig']))
        ax_hist_g.set_ylim(0, calcular_limite_y(hist_g_mod, datos['hist_g_orig']))
        ax_hist_b.set_ylim(0, calcular_limite_y(hist_b_mod, datos['hist_b_orig']))

        # Detectar si hay ajustes manuales activos
        hay_ajustes_r = (slider_brillo_r.val != 0.0) or (slider_cont_r.val != 1.0) or (slider_gamma_r.val != 1.0)
        hay_ajustes_g = (slider_brillo_g.val != 0.0) or (slider_cont_g.val != 1.0) or (slider_gamma_g.val != 1.0)
        hay_ajustes_b = (slider_brillo_b.val != 0.0) or (slider_cont_b.val != 1.0) or (slider_gamma_b.val != 1.0)

        tag_r = ' [MOD]' if hay_ajustes_r else ''
        tag_g = ' [MOD]' if hay_ajustes_g else ''
        tag_b = ' [MOD]' if hay_ajustes_b else ''

        # 7. Títulos con métricas estadísticas numéricas actualizadas en vivo
        ax_hist_r.set_title(f'Rojo{tag_r} | Media (μ): {canal_r_mod.mean():.1f} | Desv (σ): {canal_r_mod.std():.1f}',
                            fontsize=9, fontweight='bold', color='#B71C1C')
        ax_hist_g.set_title(f'Verde{tag_g} | Media (μ): {canal_g_mod.mean():.1f} | Desv (σ): {canal_g_mod.std():.1f}',
                            fontsize=9, fontweight='bold', color='#1B5E20')
        ax_hist_b.set_title(f'Azul{tag_b} | Media (μ): {canal_b_mod.mean():.1f} | Desv (σ): {canal_b_mod.std():.1f}',
                            fontsize=9, fontweight='bold', color='#0D47A1')

        # Título dinámico de la imagen resultante
        if datos['ecualizado']:
            if hay_ajustes_r or hay_ajustes_g or hay_ajustes_b:
                titulo_mod.set_text('Imagen Resultante: [Base Ecualizada por CDF + Ajustes]')
                titulo_mod.set_color('#00695C')
            else:
                titulo_mod.set_text('Imagen Resultante: [Base Ecualizada por CDF al 100%]')
                titulo_mod.set_color('#00695C')
        else:
            if hay_ajustes_r or hay_ajustes_g or hay_ajustes_b:
                titulo_mod.set_text('Imagen Resultante: [Base Original + Ajustes Manuales]')
                titulo_mod.set_color('#C2185B')
            else:
                titulo_mod.set_text('Imagen Resultante: [Original sin Modificaciones]')
                titulo_mod.set_color('#263238')

        actualizar_aspecto_boton_eq()
        figura.canvas.draw_idle()

    # Conectar los 9 sliders al evento de actualización en vivo
    for sld in [slider_brillo_r, slider_brillo_g, slider_brillo_b,
                slider_cont_r, slider_cont_g, slider_cont_b,
                slider_gamma_r, slider_gamma_g, slider_gamma_b]:
        sld.on_changed(actualizar)

    # --- MANEJADORES DE EVENTOS DE BOTONES ---
    def accion_importar(event):
        ruta_seleccionada = abrir_dialogo_archivo()
        if not ruta_seleccionada or not os.path.exists(ruta_seleccionada):
            return
        try:
            nueva_pil = Image.open(ruta_seleccionada).convert('RGB')
            nueva_matriz = np.array(nueva_pil)

            datos['matriz'] = nueva_matriz
            datos['canal_r'] = nueva_matriz[:, :, 0]
            datos['canal_g'] = nueva_matriz[:, :, 1]
            datos['canal_b'] = nueva_matriz[:, :, 2]
            datos['ecualizado'] = False

            recalcular_bases()

            # Actualizar visualizador original
            visor_img_orig.set_data(nueva_matriz)
            visor_img_orig.set_extent((0, nueva_matriz.shape[1], nueva_matriz.shape[0], 0))
            ax_img_orig.set_xlim(0, nueva_matriz.shape[1])
            ax_img_orig.set_ylim(nueva_matriz.shape[0], 0)
            titulo_orig.set_text(f'Imagen Original ({nueva_matriz.shape[1]}x{nueva_matriz.shape[0]} px)')

            # Actualizar visualizador modificado
            visor_img_mod.set_extent((0, nueva_matriz.shape[1], nueva_matriz.shape[0], 0))
            ax_img_mod.set_xlim(0, nueva_matriz.shape[1])
            ax_img_mod.set_ylim(nueva_matriz.shape[0], 0)

            # Actualizar líneas de referencia de los histogramas
            linea_orig_r.set_ydata(datos['hist_r_orig'])
            linea_orig_g.set_ydata(datos['hist_g_orig'])
            linea_orig_b.set_ydata(datos['hist_b_orig'])

            # Resetear sliders
            for sld in [slider_brillo_r, slider_brillo_g, slider_brillo_b]:
                sld.set_val(0.0)
            for sld in [slider_cont_r, slider_cont_g, slider_cont_b]:
                sld.set_val(1.0)
            for sld in [slider_gamma_r, slider_gamma_g, slider_gamma_b]:
                sld.set_val(1.0)

            btn_exportar.label.set_text('Exportar Imagen')
            actualizar()
        except Exception as err:
            print("Error al cargar la imagen seleccionada:", err)

    def accion_exportar(event):
        ruta_destino = guardar_dialogo_archivo()
        if not ruta_destino:
            return
        try:
            img_exportar = Image.fromarray(datos['cache_resultado'])
            img_exportar.save(ruta_destino)
            btn_exportar.label.set_text('[OK] Exportada')
            figura.canvas.draw_idle()
        except Exception as err:
            print("Error al exportar la imagen:", err)

    def accion_reset(event):
        datos['ecualizado'] = False
        for sld in [slider_brillo_r, slider_brillo_g, slider_brillo_b]:
            sld.set_val(0.0)
        for sld in [slider_cont_r, slider_cont_g, slider_cont_b]:
            sld.set_val(1.0)
        for sld in [slider_gamma_r, slider_gamma_g, slider_gamma_b]:
            sld.set_val(1.0)
        btn_exportar.label.set_text('Exportar Imagen')
        actualizar()

    def accion_toggle_ecualizar(event):
        datos['ecualizado'] = not datos['ecualizado']
        actualizar()

    btn_importar.on_clicked(accion_importar)
    btn_eq.on_clicked(accion_toggle_ecualizar)
    btn_reset.on_clicked(accion_reset)
    btn_exportar.on_clicked(accion_exportar)

    # Estado inicial
    actualizar()

    plt.show()


if __name__ == '__main__':
    main()
