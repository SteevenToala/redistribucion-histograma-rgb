import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from PIL import Image


def redistribuir_canal(canal_color):
    """
    Funcion para redistribuir el histograma de un canal individual (Rojo, Verde o Azul)
    expandiendo las frecuencias en todo el rango [0, 255]:
    conteo de frecuencias -> probabilidad acumulada -> tabla de conversion (LUT).
    """
    alto_imagen, ancho_imagen = canal_color.shape
    total_pixeles = alto_imagen * ancho_imagen

    # 1. Contar frecuencias de cada nivel de intensidad (del tono mas oscuro 0 al mas claro 255)
    # Creamos un arreglo de 256 casilleros vacios (uno para cada nivel de intensidad)
    conteo_intensidades = np.zeros(256, dtype=np.float64)
    for fila in range(alto_imagen):
        for columna in range(ancho_imagen):
            nivel_intensidad_pixel = canal_color[fila, columna]
            conteo_intensidades[nivel_intensidad_pixel] += 1.0

    # 2. Calcular la probabilidad acumulada (del tono mas oscuro al mas claro)
    probabilidad_acumulada = np.zeros(256, dtype=np.float64)
    suma_acumulada = 0.0
    for nivel_intensidad in range(256):
        probabilidad_este_nivel = conteo_intensidades[nivel_intensidad] / total_pixeles
        suma_acumulada += probabilidad_este_nivel
        probabilidad_acumulada[nivel_intensidad] = suma_acumulada

    # 3. Encontrar el nivel mas oscuro que realmente existe en la foto (intensidad mayor a 0)
    niveles_con_pixeles = np.where(conteo_intensidades > 0)[0]
    if len(niveles_con_pixeles) == 0:
        return canal_color.copy()

    prob_acumulada_minima = probabilidad_acumulada[niveles_con_pixeles[0]]
    rango_probabilidad_util = 1.0 - prob_acumulada_minima if (1.0 - prob_acumulada_minima) > 0 else 1.0

    # 4. Crear la tabla de conversion directa (LUT = Look-Up Table)
    # Mapea: "intensidad anterior" -> "nueva intensidad estirada de 0 (oscuro) a 255 (claro)"
    tabla_conversion_intensidad = np.zeros(256, dtype=np.uint8)
    for nivel_intensidad in niveles_con_pixeles:
        nueva_intensidad_calculada = ((probabilidad_acumulada[nivel_intensidad] - prob_acumulada_minima) / rango_probabilidad_util) * 255.0
        tabla_conversion_intensidad[nivel_intensidad] = np.uint8(np.round(nueva_intensidad_calculada))

    # 5. Asignar los nuevos niveles de intensidad a cada pixel de la imagen
    canal_redistribuido = np.zeros((alto_imagen, ancho_imagen), dtype=np.uint8)
    for fila in range(alto_imagen):
        for columna in range(ancho_imagen):
            canal_redistribuido[fila, columna] = tabla_conversion_intensidad[canal_color[fila, columna]]

    return canal_redistribuido


def aplicar_nivel_ajuste(canal_original, canal_redistribuido, porcentaje_ajuste_decimal):
    """
    Mezcla ponderada entre el canal original y el canal redistribuido segun el slider:
    porcentaje_ajuste_decimal = 0.0 -> 0% (imagen original sin cambios)
    porcentaje_ajuste_decimal = 1.0 -> 100% (redistribucion completa)
    """
    if porcentaje_ajuste_decimal <= 0.0:
        return canal_original.copy()
    if porcentaje_ajuste_decimal >= 1.0:
        return canal_redistribuido.copy()

    # Formula de mezcla: (1 - ajuste) * original + ajuste * redistribuido
    mezcla_pixeles = ((1.0 - porcentaje_ajuste_decimal) * canal_original.astype(np.float64) +
                      porcentaje_ajuste_decimal * canal_redistribuido.astype(np.float64))

    return np.clip(np.round(mezcla_pixeles), 0, 255).astype(np.uint8)


def main():
    # 1. Cargar la imagen a procesar
    ruta_imagen = os.path.join(os.path.dirname(__file__), 'images.jpg')
    imagen_cargada = Image.open(ruta_imagen).convert('RGB')
    matriz_imagen = np.array(imagen_cargada)

    # 2. Separar los tres canales de color: Rojo (R), Verde (G) y Azul (B)
    canal_rojo = matriz_imagen[:, :, 0]
    canal_verde = matriz_imagen[:, :, 1]
    canal_azul = matriz_imagen[:, :, 2]

    # 3. Precalcular la redistribucion para cada canal de color (al 100%)
    rojo_redistribuido = redistribuir_canal(canal_rojo)
    verde_redistribuido = redistribuir_canal(canal_verde)
    azul_redistribuido = redistribuir_canal(canal_azul)

    # Histogramas originales (sirven como referencia fija en los graficos)
    hist_rojo_original = np.bincount(canal_rojo.ravel(), minlength=256)
    hist_verde_original = np.bincount(canal_verde.ravel(), minlength=256)
    hist_azul_original = np.bincount(canal_azul.ravel(), minlength=256)

    # Histogramas redistribuidos al 100% (para fijar la escala vertical maxima de los ejes)
    hist_rojo_redistribuido = np.bincount(rojo_redistribuido.ravel(), minlength=256)
    hist_verde_redistribuido = np.bincount(verde_redistribuido.ravel(), minlength=256)
    hist_azul_redistribuido = np.bincount(azul_redistribuido.ravel(), minlength=256)

    # 4. Crear la ventana interactiva
    figura = plt.figure(figsize=(14, 9))
    figura.canvas.manager.set_window_title('Ajuste y Redistribución de Histogramas RGB')

    # Distribucion visual: Fila 1 para Histogramas/Sliders, Fila 2 para Imagenes
    rejilla = figura.add_gridspec(2, 6, height_ratios=[1, 1.25], hspace=0.45, wspace=0.25)
    niveles_intensidad_eje = np.arange(256)

    # --- Subgrafico Histograma Canal Rojo ---
    eje_hist_rojo = figura.add_subplot(rejilla[0, 0:2])
    eje_hist_rojo.step(niveles_intensidad_eje, hist_rojo_original, where='mid', color='#455A64', linewidth=1.2, linestyle='--', label='Original', zorder=4)
    eje_hist_rojo.fill_between(niveles_intensidad_eje, hist_rojo_original, step='mid', color='#CFD8DC', alpha=0.35, zorder=2)
    barras_rojo = eje_hist_rojo.bar(niveles_intensidad_eje, hist_rojo_original.copy(), width=1.0, color='#E53935', alpha=0.75, label='Actual', zorder=3)
    eje_hist_rojo.set_xlim(0, 255)
    eje_hist_rojo.set_ylim(0, max(hist_rojo_original.max(), hist_rojo_redistribuido.max()) * 1.08)
    eje_hist_rojo.legend(fontsize=8, loc='upper right')
    eje_hist_rojo.grid(True, linestyle=':', alpha=0.4)

    # --- Subgrafico Histograma Canal Verde ---
    eje_hist_verde = figura.add_subplot(rejilla[0, 2:4])
    eje_hist_verde.step(niveles_intensidad_eje, hist_verde_original, where='mid', color='#455A64', linewidth=1.2, linestyle='--', label='Original', zorder=4)
    eje_hist_verde.fill_between(niveles_intensidad_eje, hist_verde_original, step='mid', color='#CFD8DC', alpha=0.35, zorder=2)
    barras_verde = eje_hist_verde.bar(niveles_intensidad_eje, hist_verde_original.copy(), width=1.0, color='#43A047', alpha=0.75, label='Actual', zorder=3)
    eje_hist_verde.set_xlim(0, 255)
    eje_hist_verde.set_ylim(0, max(hist_verde_original.max(), hist_verde_redistribuido.max()) * 1.08)
    eje_hist_verde.legend(fontsize=8, loc='upper right')
    eje_hist_verde.grid(True, linestyle=':', alpha=0.4)

    # --- Subgrafico Histograma Canal Azul ---
    eje_hist_azul = figura.add_subplot(rejilla[0, 4:6])
    eje_hist_azul.step(niveles_intensidad_eje, hist_azul_original, where='mid', color='#455A64', linewidth=1.2, linestyle='--', label='Original', zorder=4)
    eje_hist_azul.fill_between(niveles_intensidad_eje, hist_azul_original, step='mid', color='#CFD8DC', alpha=0.35, zorder=2)
    barras_azul = eje_hist_azul.bar(niveles_intensidad_eje, hist_azul_original.copy(), width=1.0, color='#1E88E5', alpha=0.75, label='Actual', zorder=3)
    eje_hist_azul.set_xlim(0, 255)
    eje_hist_azul.set_ylim(0, max(hist_azul_original.max(), hist_azul_redistribuido.max()) * 1.08)
    eje_hist_azul.legend(fontsize=8, loc='upper right')
    eje_hist_azul.grid(True, linestyle=':', alpha=0.4)

    # Sliders de control interactivo debajo de cada histograma
    posicion_rojo = eje_hist_rojo.get_position()
    posicion_verde = eje_hist_verde.get_position()
    posicion_azul = eje_hist_azul.get_position()

    eje_slider_rojo = plt.axes([posicion_rojo.x0, posicion_rojo.y0 - 0.055, posicion_rojo.width, 0.024])
    eje_slider_verde = plt.axes([posicion_verde.x0, posicion_verde.y0 - 0.055, posicion_verde.width, 0.024])
    eje_slider_azul = plt.axes([posicion_azul.x0, posicion_azul.y0 - 0.055, posicion_azul.width, 0.024])

    slider_rojo = Slider(eje_slider_rojo, 'Rojo (%)', 0.0, 100.0, valinit=0.0, valstep=1.0)
    slider_verde = Slider(eje_slider_verde, 'Verde (%)', 0.0, 100.0, valinit=0.0, valstep=1.0)
    slider_azul = Slider(eje_slider_azul, 'Azul (%)', 0.0, 100.0, valinit=0.0, valstep=1.0)

    # Botones inferiores de accion rapida
    eje_boton_reiniciar = plt.axes([0.31, 0.012, 0.17, 0.030])
    boton_reiniciar = Button(eje_boton_reiniciar, 'Reiniciar (0%)', color='#ECEFF1', hovercolor='#CFD8DC')

    eje_boton_redistribuir = plt.axes([0.51, 0.012, 0.18, 0.030])
    boton_redistribuir = Button(eje_boton_redistribuir, 'Redistribuir (100%)', color='#E0F2F1', hovercolor='#B2DFDB')

    # Fila 2: Visualizacion de la Imagen Original vs Imagen Resultante
    eje_imagen_original = figura.add_subplot(rejilla[1, 0:3])
    eje_imagen_original.imshow(matriz_imagen)
    eje_imagen_original.set_title('Imagen Original', fontsize=11, fontweight='bold')
    eje_imagen_original.axis('off')

    eje_imagen_resultado = figura.add_subplot(rejilla[1, 3:6])
    visor_imagen_resultado = eje_imagen_resultado.imshow(matriz_imagen.copy())
    titulo_resultado = eje_imagen_resultado.set_title('Imagen Resultante (0%)', fontsize=11, fontweight='bold')
    eje_imagen_resultado.axis('off')

    # 5. Funcion que actualiza la imagen y los histogramas en tiempo real
    def actualizar(_=None):
        # Convertimos los valores de los sliders (0 a 100%) a decimal (0.0 a 1.0)
        ajuste_rojo = slider_rojo.val / 100.0
        ajuste_verde = slider_verde.val / 100.0
        ajuste_azul = slider_azul.val / 100.0

        # Aplicamos la formula de mezcla a cada canal de color de forma independiente
        canal_rojo_actual = aplicar_nivel_ajuste(canal_rojo, rojo_redistribuido, ajuste_rojo)
        canal_verde_actual = aplicar_nivel_ajuste(canal_verde, verde_redistribuido, ajuste_verde)
        canal_azul_actual = aplicar_nivel_ajuste(canal_azul, azul_redistribuido, ajuste_azul)

        # Unimos los 3 canales actualizados para formar la imagen RGB completa
        imagen_rgb_actual = np.stack([canal_rojo_actual, canal_verde_actual, canal_azul_actual], axis=2)
        visor_imagen_resultado.set_data(imagen_rgb_actual)

        # Actualizar titulo segun los sliders
        if ajuste_rojo == 0.0 and ajuste_verde == 0.0 and ajuste_azul == 0.0:
            titulo_resultado.set_text('Imagen Original (0%)')
        elif ajuste_rojo == 1.0 and ajuste_verde == 1.0 and ajuste_azul == 1.0:
            titulo_resultado.set_text('Imagen Redistribuida (100%)')
        else:
            titulo_resultado.set_text(f'Imagen Ajustada (Rojo: {int(slider_rojo.val)}% | Verde: {int(slider_verde.val)}% | Azul: {int(slider_azul.val)}%)')

        # Recalcular conteo de intensidades para los histogramas actuales
        hist_rojo_actual = np.bincount(canal_rojo_actual.ravel(), minlength=256)
        hist_verde_actual = np.bincount(canal_verde_actual.ravel(), minlength=256)
        hist_azul_actual = np.bincount(canal_azul_actual.ravel(), minlength=256)

        # Actualizar alturas de las barras en los graficos
        for barra, conteo in zip(barras_rojo, hist_rojo_actual):
            barra.set_height(conteo)
        for barra, conteo in zip(barras_verde, hist_verde_actual):
            barra.set_height(conteo)
        for barra, conteo in zip(barras_azul, hist_azul_actual):
            barra.set_height(conteo)

        # Titulos de los histogramas con media y desviacion estandar
        eje_hist_rojo.set_title(f'Rojo | {int(slider_rojo.val)}% | Media: {canal_rojo_actual.mean():.1f} | Desv: {canal_rojo_actual.std():.1f}', fontsize=9, fontweight='bold')
        eje_hist_verde.set_title(f'Verde | {int(slider_verde.val)}% | Media: {canal_verde_actual.mean():.1f} | Desv: {canal_verde_actual.std():.1f}', fontsize=9, fontweight='bold')
        eje_hist_azul.set_title(f'Azul | {int(slider_azul.val)}% | Media: {canal_azul_actual.mean():.1f} | Desv: {canal_azul_actual.std():.1f}', fontsize=9, fontweight='bold')

        figura.canvas.draw_idle()

    def resetear(event):
        slider_rojo.set_val(0.0)
        slider_verde.set_val(0.0)
        slider_azul.set_val(0.0)

    def redistribuir_todo(event):
        slider_rojo.set_val(100.0)
        slider_verde.set_val(100.0)
        slider_azul.set_val(100.0)

    # Conectar eventos de los sliders y botones
    slider_rojo.on_changed(actualizar)
    slider_verde.on_changed(actualizar)
    slider_azul.on_changed(actualizar)
    boton_reiniciar.on_clicked(resetear)
    boton_redistribuir.on_clicked(redistribuir_todo)

    # Mostrar estado inicial
    actualizar()

    plt.show()


if __name__ == '__main__':
    main()
