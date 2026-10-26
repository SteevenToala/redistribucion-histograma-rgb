# Configuración de Histogramas (Contraste) - Versión de Escritorio

Aplicación nativa de escritorio para **Procesamiento Digital de Imágenes (PDI)** desarrollada en Python con **Tkinter**, **Matplotlib**, **Pillow**, **OpenCV** y **NumPy**, basada en la misma arquitectura visual y de librerías empleada en proyectos como *Filtro AI*.

---

## 🚀 Requisitos

Instalar las librerías necesarias (si no las tienes instaladas):

```bash
pip install numpy opencv-python pillow matplotlib
```

*(Nota: `tkinter` viene preinstalado de forma estándar con Python en Windows).*

---

## 💻 Ejecución

Para iniciar la aplicación de escritorio:

```powershell
cd codigo-escritorio
python main.py
```

---

## 🎯 Características Principales

1. **Carga y Visualización RGB:**
   * Carga imágenes locales en cualquier formato estándar (`.jpg`, `.png`, `.bmp`, `.webp`) mediante cuadro de diálogo nativo o botón de muestra rápida.
   * Detección dinámica y visualización inmediata de dimensiones ($W \times H$ px) y conteo total de píxeles ($M \times N$).

2. **Descomposición Espectral:**
   * Descompone la imagen tridimensional en sus tres espectros cromáticos independientes: **Rojo ($R$)**, **Verde ($G$)** y **Azul ($B$)**.
   * Pestaña dedicada para inspeccionar visualmente cada canal de forma aislada.

3. **Banco de 6 Histogramas Discretos en 3 Columnas:**
   * Renderizado en plano cartesiano mediante **Matplotlib embebido en Tkinter**.
   * Fila superior: 3 histogramas originales de referencia fija.
   * Fila inferior: 3 histogramas modificados en tiempo real con línea guía de corte de umbral ($U$).
   * Estadísticas en vivo de media muestral ($\mu$) y desviación estándar ($\sigma$) por espectro.

4. **Manipulación de Contraste con Conservación de Masa:**
   * Deslizadores individuales de **0% a 100%** para cada canal cromático.
   * Algoritmo canónico de **Ecualización de Histograma por Meseta (Plateau Histogram Equalization - PHE)** y recorte de picos.
   * Contador en tiempo real de los píxeles transferidos ($E$).

5. **Herramientas de Inspección Analítica:**
   * Selector de escala vertical en el eje $Y$: **Lineal** y **Logarítmica** ($\log$).
   * Zoom de casilleros / bins: **Todo (0–255)**, **Sombras (0–85)**, **Medios (85–170)** y **Luces (170–255)**.

6. **Pestaña de Conservación de Masa:**
   * Tabla cuantitativa que corrobora que $\sum H_{\text{mod}} = \sum H_{\text{orig}} = M \times N$, demostrando que no existen pérdidas ni artefactos espurios.

7. **Persistencia:**
   * Botón para exportar y guardar la imagen modificada resultante en formato PNG o JPG con alta fidelidad.
