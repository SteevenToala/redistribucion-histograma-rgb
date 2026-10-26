"""
Interfaz Gráfica de Escritorio (PDI Desktop)
=============================================
Configuración y Redistribución de Histogramas RGB.
Arquitectura unificada en pantalla completa (sin duplicidad de controles),
con 3 columnas por espectro cromático (R, G, B), banco de 6 histogramas,
rectángulos discretos bien definidos, indicador numérico de picos máximos,
inspector interactivo de píxeles por nivel al pasar el mouse (hover),
zoom de inspección por casilleros y tabla completa de frecuencias 0–255.
"""

import os
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
from PIL import Image, ImageTk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter, MaxNLocator

import transformaciones as pdi
import utils

DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))


def _formatear_miles(valor: float) -> str:
    """Formatea números con punto como separador de miles (ej. 585.185)."""
    return f"{int(round(valor)):,}".replace(",", ".")


class AplicacionHistogramasDesktop:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Modificación y Redistribución de Histogramas RGB - PDI")
        self.root.geometry("1400x900")
        self.root.minsize(1120, 720)
        try:
            self.root.state('zoomed')  # Maximizar en Windows
        except Exception:
            pass

        # Paleta visual moderna
        self.colores = {
            'bg_app': '#f8fafc',
            'bg_card': '#ffffff',
            'border': '#e2e8f0',
            'border_dark': '#cbd5e1',
            'text_main': '#0f172a',
            'text_muted': '#64748b',
            'red': '#dc2626',
            'red_edge': '#991b1b',
            'red_border': '#fca5a5',
            'red_trough': '#fee2e2',
            'green': '#16a34a',
            'green_edge': '#166534',
            'green_border': '#86efac',
            'green_trough': '#dcfce7',
            'blue': '#2563eb',
            'blue_edge': '#1e40af',
            'blue_border': '#93c5fd',
            'blue_trough': '#eff6ff'
        }
        self.root.configure(bg=self.colores['bg_app'])

        # Estado de la imagen y datos
        self.img_original_rgb = None
        self.img_modificada_rgb = None
        self.histogramas = None
        self.estadisticas = None
        self.canales_espectros = None

        # Variables de control de contraste (deslizadores 0% a 100%)
        self.redist_r = tk.IntVar(value=60)
        self.redist_g = tk.IntVar(value=35)
        self.redist_b = tk.IntVar(value=0)

        # Variables de visualización
        self.zoom_rango = tk.StringVar(value="todo")   # 'todo', 'sombras', 'medios', 'luces'
        self.escala_y = tk.StringVar(value="lineal")   # 'lineal', 'log'

        # Variables de etiquetas informativas
        self.info_dimensiones = tk.StringVar(value="Cargando...")
        self.info_tiempo_ms = tk.StringVar(value="0.0 ms")
        self.info_px_r = tk.StringVar(value="0 px transferidos")
        self.info_px_g = tk.StringVar(value="0 px transferidos")
        self.info_px_b = tk.StringVar(value="0 px transferidos")

        # Inspector interactivo de píxeles al pasar el cursor (Hover)
        self.texto_hint_default = "💡 Mueve el cursor sobre las barras para ver el nivel de intensidad y conteo de píxeles"
        self.info_inspector = tk.StringVar(value=self.texto_hint_default)

        # Referencias de botones pill para activar/desactivar estilos
        self.btn_pills_zoom = {}
        self.btn_pills_escala = {}

        # Referencias de imágenes PhotoImage para evitar garbage collection
        self.photo_orig = None
        self.photo_mod = None
        self._resize_timer = None

        # Construir la interfaz completa
        self._configurar_estilos_ttk()
        self._construir_interfaz()

        # Cargar imagen inicial tras mostrar la ventana
        self.root.after(100, self._cargar_imagen_defecto)

    def _configurar_estilos_ttk(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        self.style.configure('TFrame', background=self.colores['bg_app'])

    def _construir_interfaz(self):
        # Contenedor raíz con márgenes
        contenedor_principal = tk.Frame(self.root, bg=self.colores['bg_app'])
        contenedor_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        contenedor_principal.columnconfigure(0, weight=1)
        contenedor_principal.rowconfigure(0, weight=0)  # Encabezado (fijo)
        contenedor_principal.rowconfigure(1, weight=3)  # Visores de Imágenes (flexible)
        contenedor_principal.rowconfigure(2, weight=0)  # Barra de Zoom y Escala (fijo)
        contenedor_principal.rowconfigure(3, weight=5)  # 3 Columnas de Histogramas (flexible)

        # 1. ENCABEZADO SUPERIOR
        self._construir_encabezado(contenedor_principal)

        # 2. FILA DE IMÁGENES (Original vs Modificada)
        self._construir_fila_imagenes(contenedor_principal)

        # 3. BARRA DE HERRAMIENTAS (Zoom de Inspección, Inspector en Vivo y Escala Y)
        self._construir_toolbar_zoom(contenedor_principal)

        # 4. FILA DE 3 COLUMNAS DE ESPECTRO (R, G, B con histogramas y sliders integrados)
        self._construir_columnas_espectro(contenedor_principal)

    # =========================================================================
    # 1. ENCABEZADO SUPERIOR
    # =========================================================================
    def _construir_encabezado(self, parent):
        header = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid",
                          highlightbackground=self.colores['border'], highlightthickness=1)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        # --- LADO IZQUIERDO: Título, Icono y Badge de Dimensiones ---
        left_box = tk.Frame(header, bg="#ffffff")
        left_box.pack(side=tk.LEFT, padx=12, pady=6)

        # Icono de la aplicación
        lbl_icono = tk.Label(left_box, text="📊", font=('Segoe UI', 15), bg="#ffffff")
        lbl_icono.pack(side=tk.LEFT, padx=(0, 8))

        # Textos de título y badge
        title_box = tk.Frame(left_box, bg="#ffffff")
        title_box.pack(side=tk.LEFT)

        row_title = tk.Frame(title_box, bg="#ffffff")
        row_title.pack(anchor="w")

        lbl_titulo = tk.Label(row_title, text="Modificación y Redistribución de Histogramas RGB",
                              font=('Segoe UI', 11, 'bold'), fg=self.colores['text_main'], bg="#ffffff")
        lbl_titulo.pack(side=tk.LEFT)

        lbl_badge_dim = tk.Label(row_title, textvariable=self.info_dimensiones,
                                 font=('Segoe UI', 8, 'bold'), fg="#2563eb", bg="#eff6ff",
                                 padx=8, pady=1, relief="solid", bd=1, highlightbackground="#bfdbfe")
        lbl_badge_dim.pack(side=tk.LEFT, padx=10)

        lbl_sub = tk.Label(title_box, text="Inteligencia Artificial • Procesamiento Digital de Imágenes (PDI)",
                           font=('Segoe UI', 8), fg=self.colores['text_muted'], bg="#ffffff")
        lbl_sub.pack(anchor="w", pady=(1, 0))

        # --- LADO DERECHO: Botones de Acción Globales ---
        right_box = tk.Frame(header, bg="#ffffff")
        right_box.pack(side=tk.RIGHT, padx=12, pady=6)

        # Botón Cargar Imagen
        btn_cargar = tk.Button(right_box, text="📁 Cargar Imagen", font=('Segoe UI', 9, 'bold'),
                               bg="#ffffff", fg=self.colores['text_main'],
                               relief="solid", bd=1, highlightbackground=self.colores['border_dark'],
                               cursor="hand2", padx=10, pady=3,
                               activebackground="#f1f5f9", command=self._accion_cargar_imagen)
        btn_cargar.pack(side=tk.LEFT, padx=3)

        # Botón Restablecer Todo (0%)
        btn_reset = tk.Button(right_box, text="🔄 Restablecer Todo (0%)", font=('Segoe UI', 9),
                              bg="#ffffff", fg=self.colores['text_main'],
                              relief="solid", bd=1, highlightbackground=self.colores['border_dark'],
                              cursor="hand2", padx=9, pady=3,
                              activebackground="#f1f5f9", command=self._accion_resetear_sliders)
        btn_reset.pack(side=tk.LEFT, padx=3)

        # Botón Ver Tabla 0-255 (Píxeles por Nivel)
        btn_tabla_bins = tk.Button(right_box, text="🔢 Píxeles por Nivel (0–255)", font=('Segoe UI', 8, 'bold'),
                                   bg="#eff6ff", fg="#2563eb", relief="solid", bd=1,
                                   highlightbackground="#bfdbfe", cursor="hand2", padx=8, pady=3,
                                   activebackground="#dbeafe", command=self._mostrar_modal_tabla_niveles)
        btn_tabla_bins.pack(side=tk.LEFT, padx=3)

        # Botón Modal de Métricas / Conservación de Masa
        btn_metricas = tk.Button(right_box, text="📈 Conservación / Masa", font=('Segoe UI', 8),
                                 bg="#f8fafc", fg=self.colores['text_muted'],
                                 relief="solid", bd=1, highlightbackground=self.colores['border'],
                                 cursor="hand2", padx=8, pady=3,
                                 activebackground="#f1f5f9", command=self._mostrar_modal_metricas)
        btn_metricas.pack(side=tk.LEFT, padx=3)

        # Botón Guardar en Resultados
        btn_guardar = tk.Button(right_box, text="💾 Guardar en Resultados", font=('Segoe UI', 9, 'bold'),
                                bg="#2563eb", fg="#ffffff", relief="flat", bd=0,
                                cursor="hand2", padx=12, pady=4,
                                activebackground="#1d4ed8", activeforeground="#ffffff",
                                command=self._accion_guardar_resultado)
        btn_guardar.pack(side=tk.LEFT, padx=(3, 0))

    # =========================================================================
    # 2. FILA DE IMÁGENES COMPARATIVAS
    # =========================================================================
    def _construir_fila_imagenes(self, parent):
        frame_imgs = tk.Frame(parent, bg=self.colores['bg_app'])
        frame_imgs.grid(row=1, column=0, sticky="nsew", pady=(0, 6))

        frame_imgs.columnconfigure(0, weight=1)
        frame_imgs.columnconfigure(1, weight=1)
        frame_imgs.rowconfigure(0, weight=1)

        # --- Tarjeta 1: Imagen Original ---
        self.card_orig = tk.Frame(frame_imgs, bg="#ffffff", bd=1, relief="solid",
                                  highlightbackground=self.colores['border'], highlightthickness=1)
        self.card_orig.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Badge flotante superior izquierdo
        badge_orig = tk.Label(self.card_orig, text="Imagen Original", font=('Segoe UI', 8, 'bold'),
                              fg="#475569", bg="#f1f5f9", padx=8, pady=2, relief="solid", bd=1)
        badge_orig.place(x=8, y=8)

        # Visor de la imagen original
        self.lbl_canvas_orig = tk.Label(self.card_orig, bg="#ffffff")
        self.lbl_canvas_orig.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # --- Tarjeta 2: Imagen Modificada ---
        self.card_mod = tk.Frame(frame_imgs, bg="#ffffff", bd=1, relief="solid",
                                 highlightbackground=self.colores['border'], highlightthickness=1)
        self.card_mod.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Badge flotante superior izquierdo
        badge_mod = tk.Label(self.card_mod, text="Imagen Modificada (Redistribuida)", font=('Segoe UI', 8, 'bold'),
                             fg="#475569", bg="#f1f5f9", padx=8, pady=2, relief="solid", bd=1)
        badge_mod.place(x=8, y=8)

        # Badge de rendimiento / latencia en la esquina inferior derecha
        badge_perf = tk.Label(self.card_mod, textvariable=self.info_tiempo_ms,
                              font=('Consolas', 8, 'bold'), fg="#15803d", bg="#dcfce7",
                              padx=8, pady=2, relief="solid", bd=1)
        badge_perf.place(relx=1.0, rely=1.0, x=-8, y=-8, anchor="se")

        # Visor de la imagen modificada
        self.lbl_canvas_mod = tk.Label(self.card_mod, bg="#ffffff")
        self.lbl_canvas_mod.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Evento de cambio de tamaño para re-escalar fluidamente
        self.card_orig.bind("<Configure>", self._al_redimensionar_cards)

    def _al_redimensionar_cards(self, event=None):
        if self._resize_timer is not None:
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(80, self._actualizar_visores_imagenes)

    # =========================================================================
    # 3. BARRA DE HERRAMIENTAS (ZOOM, INSPECTOR HOVER Y ESCALA Y)
    # =========================================================================
    def _construir_toolbar_zoom(self, parent):
        toolbar = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid",
                           highlightbackground=self.colores['border'], highlightthickness=1, padx=8, pady=3)
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        # --- LADO IZQUIERDO: Zoom de Inspección ---
        f_zoom = tk.Frame(toolbar, bg="#ffffff")
        f_zoom.pack(side=tk.LEFT)

        lbl_zoom = tk.Label(f_zoom, text="Zoom de Inspección:", font=('Segoe UI', 9, 'bold'),
                            bg="#ffffff", fg=self.colores['text_main'])
        lbl_zoom.pack(side=tk.LEFT, padx=(0, 6))

        # Contenedor de Pills de Zoom
        pill_box = tk.Frame(f_zoom, bg="#f1f5f9", bd=1, relief="solid", highlightbackground="#e2e8f0", padx=2, pady=2)
        pill_box.pack(side=tk.LEFT, padx=(0, 6))

        opciones_zoom = [
            ("todo", "Todo (0–255)"),
            ("sombras", "Sombras (0–85)"),
            ("medios", "Medios (85–170)"),
            ("luces", "Luces (170–255)")
        ]
        self.btn_pills_zoom = {}
        for clave, texto in opciones_zoom:
            btn = tk.Button(pill_box, text=texto, font=('Segoe UI', 8),
                            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
                            activebackground="#ffffff", activeforeground="#2563eb",
                            command=lambda c=clave: self.set_zoom_preset(c))
            btn.pack(side=tk.LEFT, padx=1)
            self.btn_pills_zoom[clave] = btn

        # Botón Restaurar Zoom
        btn_rest = tk.Button(f_zoom, text="↺ Restaurar Zoom", font=('Segoe UI', 8),
                             bg="#f8fafc", fg=self.colores['text_main'], relief="solid", bd=1,
                             padx=8, pady=2, cursor="hand2", activebackground="#e2e8f0",
                             command=lambda: self.set_zoom_preset("todo"))
        btn_rest.pack(side=tk.LEFT, padx=2)

        # --- CENTRO: Inspector Dinámico de Píxeles al pasar el mouse (Hover) ---
        self.lbl_inspector = tk.Label(toolbar, textvariable=self.info_inspector,
                                      font=('Segoe UI', 8, 'bold'), fg="#1e40af", bg="#eff6ff",
                                      padx=10, pady=2, relief="solid", bd=1, highlightbackground="#bfdbfe")
        self.lbl_inspector.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)

        # --- LADO DERECHO: Escala Eje Y ---
        f_esc = tk.Frame(toolbar, bg="#ffffff")
        f_esc.pack(side=tk.RIGHT)

        pill_esc = tk.Frame(f_esc, bg="#f1f5f9", bd=1, relief="solid", highlightbackground="#e2e8f0", padx=2, pady=2)
        pill_esc.pack(side=tk.RIGHT)

        opciones_esc = [("lineal", "Lineal"), ("log", "Log-Y")]
        self.btn_pills_escala = {}
        for clave, texto in opciones_esc:
            btn = tk.Button(pill_esc, text=texto, font=('Segoe UI', 8),
                            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
                            activebackground="#ffffff", activeforeground="#2563eb",
                            command=lambda c=clave: self.set_escala(c))
            btn.pack(side=tk.LEFT, padx=1)
            self.btn_pills_escala[clave] = btn

        lbl_esc = tk.Label(f_esc, text="Escala Eje Y:", font=('Segoe UI', 9, 'bold'),
                           bg="#ffffff", fg=self.colores['text_main'])
        lbl_esc.pack(side=tk.RIGHT, padx=(0, 6))

        # Estilo inicial de los pills
        self._actualizar_estilo_pills_zoom()
        self._actualizar_estilo_pills_escala()

    def set_zoom_preset(self, preset: str):
        self.zoom_rango.set(preset)
        self._actualizar_estilo_pills_zoom()
        self._actualizar_graficos_histogramas()

    def _actualizar_estilo_pills_zoom(self):
        activo = self.zoom_rango.get()
        for clave, btn in self.btn_pills_zoom.items():
            if clave == activo:
                btn.config(bg="#ffffff", fg="#2563eb", font=('Segoe UI', 8, 'bold'), relief="solid", bd=1)
            else:
                btn.config(bg="#f1f5f9", fg="#334155", font=('Segoe UI', 8), relief="flat", bd=0)

    def set_escala(self, escala: str):
        self.escala_y.set(escala)
        self._actualizar_estilo_pills_escala()
        self._actualizar_graficos_histogramas()

    def _actualizar_estilo_pills_escala(self):
        activo = self.escala_y.get()
        for clave, btn in self.btn_pills_escala.items():
            if clave == activo:
                btn.config(bg="#ffffff", fg="#2563eb", font=('Segoe UI', 8, 'bold'), relief="solid", bd=1)
            else:
                btn.config(bg="#f1f5f9", fg="#334155", font=('Segoe UI', 8), relief="flat", bd=0)

    # =========================================================================
    # 4. FILA DE 3 COLUMNAS DE ESPECTRO (R, G, B)
    # =========================================================================
    def _construir_columnas_espectro(self, parent):
        frame_espectros = tk.Frame(parent, bg=self.colores['bg_app'])
        frame_espectros.grid(row=3, column=0, sticky="nsew")

        frame_espectros.columnconfigure(0, weight=1)
        frame_espectros.columnconfigure(1, weight=1)
        frame_espectros.columnconfigure(2, weight=1)
        frame_espectros.rowconfigure(0, weight=1)

        # COLUMNA ROJO (R)
        self._construir_columna_canal(
            parent=frame_espectros, col_idx=0, canal='r', nombre="Rojo",
            color_hex=self.colores['red'], border_hex=self.colores['red_border'],
            trough_hex=self.colores['red_trough'], variable_slider=self.redist_r,
            variable_px=self.info_px_r
        )

        # COLUMNA VERDE (G)
        self._construir_columna_canal(
            parent=frame_espectros, col_idx=1, canal='g', nombre="Verde",
            color_hex=self.colores['green'], border_hex=self.colores['green_border'],
            trough_hex=self.colores['green_trough'], variable_slider=self.redist_g,
            variable_px=self.info_px_g
        )

        # COLUMNA AZUL (B)
        self._construir_columna_canal(
            parent=frame_espectros, col_idx=2, canal='b', nombre="Azul",
            color_hex=self.colores['blue'], border_hex=self.colores['blue_border'],
            trough_hex=self.colores['blue_trough'], variable_slider=self.redist_b,
            variable_px=self.info_px_b
        )

    def _construir_columna_canal(self, parent, col_idx, canal, nombre,
                                color_hex, border_hex, trough_hex, variable_slider, variable_px):
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid",
                        highlightbackground=border_hex, highlightthickness=1.5)
        card.grid(row=0, column=col_idx, sticky="nsew", padx=3, pady=2)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)  # Matplotlib Canvas (Original + Modificado)
        card.rowconfigure(1, weight=0)  # Controles de Slider en el pie de la columna

        # Figura Matplotlib con 2 subplots (Fila 0: Original, Fila 1: Modificado)
        fig = Figure(figsize=(3.9, 3.1), dpi=90, facecolor="#ffffff")
        fig.subplots_adjust(left=0.15, right=0.96, top=0.90, bottom=0.13, hspace=0.48)
        ax_orig, ax_mod = fig.subplots(2, 1)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Conectar eventos de mouse para el Inspector en Vivo (Hover interactivo)
        canvas.mpl_connect('motion_notify_event',
                           lambda event, c=canal, n=nombre: self._al_mover_mouse_en_grafico(event, c, n))
        canvas.mpl_connect('axes_leave_event', self._al_salir_mouse_de_grafico)

        # Pie de la columna: Slider de control y contadores
        footer = tk.Frame(card, bg="#ffffff", padx=8, pady=4)
        footer.grid(row=1, column=0, sticky="ew")

        # Fila superior del footer: Label 'Redistribución de Picos' | px transferidos | %
        f_info = tk.Frame(footer, bg="#ffffff")
        f_info.pack(fill=tk.X, pady=(0, 2))

        lbl_nombre_ctrl = tk.Label(f_info, text="Redistribución de Picos",
                                   font=('Segoe UI', 8, 'bold'), fg=self.colores['text_main'], bg="#ffffff")
        lbl_nombre_ctrl.pack(side=tk.LEFT)

        lbl_pct = tk.Label(f_info, text=f"{variable_slider.get()}%",
                           font=('Consolas', 9, 'bold'), fg=color_hex, bg="#ffffff")
        lbl_pct.pack(side=tk.RIGHT)

        lbl_px = tk.Label(f_info, textvariable=variable_px,
                          font=('Consolas', 8), fg=self.colores['text_muted'], bg="#ffffff")
        lbl_px.pack(side=tk.RIGHT, padx=6)

        # Fila inferior del footer: Deslizador horizontal nativo
        scale = tk.Scale(
            footer, from_=0, to=100, orient=tk.HORIZONTAL, variable=variable_slider,
            showvalue=False, bg="#ffffff", troughcolor=trough_hex,
            activebackground=color_hex, highlightthickness=0, bd=1, relief="flat",
            command=lambda v, c=canal, l=lbl_pct: self._al_mover_slider(c, v, l)
        )
        scale.pack(fill=tk.X)

        # Guardar referencias en diccionarios de la clase
        if not hasattr(self, 'figuras_canales'):
            self.figuras_canales = {}
            self.axes_canales = {}
            self.canvases_canales = {}
            self.labels_pct_canales = {}

        self.figuras_canales[canal] = fig
        self.axes_canales[canal] = (ax_orig, ax_mod)
        self.canvases_canales[canal] = canvas
        self.labels_pct_canales[canal] = lbl_pct

    # =========================================================================
    # LÓGICA DE PROCESAMIENTO Y EVENTOS
    # =========================================================================
    def _al_mover_slider(self, canal, valor, lbl_pct):
        lbl_pct.config(text=f"{int(valor)}%")
        self._ejecutar_procesamiento()

    def _accion_resetear_sliders(self):
        self.redist_r.set(0)
        self.redist_g.set(0)
        self.redist_b.set(0)
        for k, lbl in self.labels_pct_canales.items():
            lbl.config(text="0%")
        self._ejecutar_procesamiento()

    def _cargar_imagen_defecto(self):
        candidatos = [
            os.path.join(DIR_ACTUAL, "imagenes", "images.jpg"),
            os.path.join(DIR_ACTUAL, "images.jpg"),
            os.path.join(os.path.dirname(DIR_ACTUAL), "codigo", "imagenes", "images.jpg"),
            os.path.join(os.path.dirname(DIR_ACTUAL), "informe", "imagenes", "imagen_original.jpg")
        ]
        ruta_encontrada = None
        for c in candidatos:
            if os.path.exists(c):
                ruta_encontrada = c
                break

        if ruta_encontrada:
            self._cargar_imagen_desde_ruta(ruta_encontrada)
        else:
            sintetica = np.zeros((450, 682, 3), dtype=np.uint8)
            sintetica[:, :] = (180, 120, 80)
            self._establecer_imagen_original(sintetica)

    def _accion_cargar_imagen(self):
        tipos = [
            ("Archivos de Imagen", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("JPEG", "*.jpg *.jpeg"),
            ("PNG", "*.png"),
            ("Todos", "*.*")
        ]
        ruta = filedialog.askopenfilename(title="Seleccionar Imagen RGB", filetypes=tipos)
        if ruta:
            try:
                self._cargar_imagen_desde_ruta(ruta)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{e}")

    def _cargar_imagen_desde_ruta(self, ruta: str):
        img_rgb = utils.cargar_imagen_rgb(ruta)
        self._establecer_imagen_original(img_rgb)

    def _establecer_imagen_original(self, img_rgb: np.ndarray):
        self.img_original_rgb = img_rgb
        alto, ancho = img_rgb.shape[:2]
        self.info_dimensiones.set(f"{ancho} × {alto} px")
        self._ejecutar_procesamiento()

    def _ejecutar_procesamiento(self):
        if self.img_original_rgb is None:
            return

        t0 = time.perf_counter()
        f_r = self.redist_r.get() / 100.0
        f_g = self.redist_g.get() / 100.0
        f_b = self.redist_b.get() / 100.0

        img_out, hists, stats, espectros = pdi.procesar_imagen_rgb_completa(
            self.img_original_rgb, f_r, f_g, f_b
        )
        tiempo_ms = (time.perf_counter() - t0) * 1000.0

        self.img_modificada_rgb = img_out
        self.histogramas = hists
        self.estadisticas = stats
        self.canales_espectros = espectros

        # Actualizar labels de latencia y píxeles transferidos
        self.info_tiempo_ms.set(f"{tiempo_ms:.1f} ms")
        self.info_px_r.set(f"{_formatear_miles(stats['exceso']['r'])} px transferidos")
        self.info_px_g.set(f"{_formatear_miles(stats['exceso']['g'])} px transferidos")
        self.info_px_b.set(f"{_formatear_miles(stats['exceso']['b'])} px transferidos")

        # Refrescar imágenes e histogramas
        self._actualizar_visores_imagenes()
        self._actualizar_graficos_histogramas()

    def _actualizar_visores_imagenes(self):
        if self.img_original_rgb is None or self.img_modificada_rgb is None:
            return

        max_w = max(180, self.card_orig.winfo_width() - 16)
        max_h = max(140, self.card_orig.winfo_height() - 20)
        if max_w <= 10 or max_h <= 10:
            max_w, max_h = 560, 220

        # Imagen original
        self.photo_orig, _, _ = utils.numpy_a_photoimage(self.img_original_rgb, max_w, max_h)
        if self.photo_orig:
            self.lbl_canvas_orig.config(image=self.photo_orig)

        # Imagen modificada
        self.photo_mod, _, _ = utils.numpy_a_photoimage(self.img_modificada_rgb, max_w, max_h)
        if self.photo_mod:
            self.lbl_canvas_mod.config(image=self.photo_mod)

    # =========================================================================
    # RENDERIZADO DETALLADO DE HISTOGRAMAS CON RECTÁNGULOS VISIBLES
    # =========================================================================
    def _actualizar_graficos_histogramas(self):
        if self.histogramas is None or not hasattr(self, 'axes_canales'):
            return

        # Rango de bins según zoom
        zoom = self.zoom_rango.get()
        if zoom == "sombras":
            b_min, b_max = 0, 85
        elif zoom == "medios":
            b_min, b_max = 85, 170
        elif zoom == "luces":
            b_min, b_max = 170, 255
        else:
            b_min, b_max = 0, 255

        es_log = (self.escala_y.get() == "log")
        canales_info = [
            ('r', "Rojo", self.colores['red'], self.colores['red_edge'], self.colores['red_border'], self.redist_r.get()),
            ('g', "Verde", self.colores['green'], self.colores['green_edge'], self.colores['green_border'], self.redist_g.get()),
            ('b', "Azul", self.colores['blue'], self.colores['blue_edge'], self.colores['blue_border'], self.redist_b.get())
        ]

        bins_x = np.arange(256)
        bins_mask = (bins_x >= b_min) & (bins_x <= b_max)
        x_indices = bins_x[bins_mask]

        # Ancho de barra con espacio entre rectángulos para que sean columnas individuales visibles
        w_barra = 0.82 if len(x_indices) > 100 else 0.72

        for canal, nombre, color, color_edge, border_card, pct in canales_info:
            ax_orig, ax_mod = self.axes_canales[canal]
            canvas = self.canvases_canales[canal]

            h_orig = self.histogramas['orig'][canal][bins_mask]
            h_mod = self.histogramas['mod'][canal][bins_mask]

            max_orig = float(np.max(h_orig)) if len(h_orig) > 0 else 100.0
            max_orig = max(100.0, max_orig)
            max_mod = float(np.max(h_mod)) if len(h_mod) > 0 else 100.0
            max_mod = max(100.0, max_mod)

            # Función de formateo adaptativo inteligente para el eje Y
            def crear_fmt_y(max_v):
                def fmt_fn(x, pos):
                    if x <= 0:
                        return "0"
                    elif max_v < 4000:
                        return f"{int(round(x)):,}".replace(",", ".")
                    elif x >= 1000:
                        val_k = x / 1000.0
                        if val_k >= 10 or val_k.is_integer():
                            return f"{int(round(val_k))}k"
                        return f"{val_k:.1f}k"
                    return f"{int(round(x))}"
                return FuncFormatter(fmt_fn)

            # -------------------------------------------------------------
            # 1. Gráfico Histograma Original (Arriba)
            # -------------------------------------------------------------
            ax_orig.clear()
            # Rectángulos discretos con bordes definidos y ancho menor a 1.0
            ax_orig.bar(x_indices, h_orig, color=color, edgecolor=color_edge,
                        linewidth=0.5, width=w_barra, alpha=0.92)

            mu_o, sig_o = self.estadisticas['orig'][canal]
            ax_orig.set_title(f"{nombre} [ORIGINAL]", loc='left', fontsize=8, fontweight='bold', color=color, pad=4)
            ax_orig.set_title(f"μ: {mu_o}  |  σ: {sig_o}", loc='right', fontsize=8, fontweight='bold', color=color, pad=4)

            ax_orig.set_xlim(b_min - 0.5, b_max + 0.5)
            ax_orig.set_xticks([t for t in [0, 50, 100, 150, 200, 255] if b_min <= t <= b_max])
            ax_orig.grid(True, linestyle=":", alpha=0.5)
            ax_orig.tick_params(labelsize=7)

            if es_log:
                ax_orig.set_yscale('log')
            else:
                ax_orig.set_ylim(0, max_orig * 1.16)
                ax_orig.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
                ax_orig.yaxis.set_major_formatter(crear_fmt_y(max_orig))

            # Badge del Pico Máximo (Indica con total claridad "a dónde llega")
            ax_orig.text(0.03, 0.90, f"Pico: {_formatear_miles(max_orig)} px",
                         transform=ax_orig.transAxes, ha='left', va='top', fontsize=6.8, fontweight='bold',
                         color=color, bbox=dict(boxstyle='round,pad=0.25', facecolor='#ffffff', edgecolor=border_card, alpha=0.95))

            # Badge identificador de Original
            ax_orig.text(0.96, 0.90, "■ Orig", transform=ax_orig.transAxes, ha='right', va='top',
                         fontsize=6.5, color='#475569',
                         bbox=dict(boxstyle='square,pad=0.2', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.9))

            # -------------------------------------------------------------
            # 2. Gráfico Histograma Modificado (Abajo)
            # -------------------------------------------------------------
            ax_mod.clear()
            # Rectángulos discretos con bordes definidos y ancho menor a 1.0
            ax_mod.bar(x_indices, h_mod, color=color, edgecolor=color_edge,
                       linewidth=0.5, width=w_barra, alpha=0.92)

            # Línea guía de umbral dinámico de meseta U(f)
            umb = self.estadisticas['umbrales'][canal]
            if pct > 0:
                ax_mod.axhline(y=umb, color="#f59e0b", linestyle="--", linewidth=1.2)

            mu_m, sig_m = self.estadisticas['mod'][canal]
            ax_mod.set_title(f"{nombre} [MODIFICADO]", loc='left', fontsize=8, fontweight='bold', color=color, pad=4)
            ax_mod.set_title(f"μ: {mu_m}  |  σ: {sig_m}", loc='right', fontsize=8, fontweight='bold', color=color, pad=4)

            ax_mod.set_xlim(b_min - 0.5, b_max + 0.5)
            ax_mod.set_xticks([t for t in [0, 50, 100, 150, 200, 255] if b_min <= t <= b_max])
            ax_mod.grid(True, linestyle=":", alpha=0.5)
            ax_mod.tick_params(labelsize=7)

            if es_log:
                ax_mod.set_yscale('log')
            else:
                ax_mod.set_ylim(0, max_mod * 1.16)
                ax_mod.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
                ax_mod.yaxis.set_major_formatter(crear_fmt_y(max_mod))

            # Badge del Pico Máximo
            ax_mod.text(0.03, 0.90, f"Pico: {_formatear_miles(max_mod)} px",
                         transform=ax_mod.transAxes, ha='left', va='top', fontsize=6.8, fontweight='bold',
                         color=color, bbox=dict(boxstyle='round,pad=0.25', facecolor='#ffffff', edgecolor=border_card, alpha=0.95))

            # Badge identificador de Modificado
            ax_mod.text(0.96, 0.90, "■ Mod", transform=ax_mod.transAxes, ha='right', va='top',
                        fontsize=6.5, color='#475569',
                        bbox=dict(boxstyle='square,pad=0.2', facecolor='#ffffff', edgecolor='#cbd5e1', alpha=0.9))

            canvas.draw_idle()

    # =========================================================================
    # INSPECTOR INTERACTIVO AL PASAR EL CURSOR (HOVER DE PÍXELES POR NIVEL)
    # =========================================================================
    def _al_mover_mouse_en_grafico(self, event, canal, nombre_canal):
        if event.inaxes is None or event.xdata is None or self.histogramas is None or self.img_original_rgb is None:
            return

        k = int(round(event.xdata))
        if 0 <= k <= 255:
            px_o = int(self.histogramas['orig'][canal][k])
            px_m = int(self.histogramas['mod'][canal][k])
            total_px = self.img_original_rgb.shape[0] * self.img_original_rgb.shape[1]
            pct_o = (px_o / total_px) * 100.0
            pct_m = (px_m / total_px) * 100.0

            diff = px_m - px_o
            signo = f"+{_formatear_miles(diff)}" if diff > 0 else _formatear_miles(diff)

            texto = (
                f"🎯 Nivel de Intensidad: {k} [{nombre_canal}]  ➜  "
                f"Original: {_formatear_miles(px_o)} px ({pct_o:.2f}%)   |   "
                f"Modificado: {_formatear_miles(px_m)} px ({pct_m:.2f}%)   |   "
                f"Variación: {signo} px"
            )
            self.info_inspector.set(texto)
            self.lbl_inspector.config(bg="#fef3c7", fg="#92400e")  # Resaltar en ámbar activo

    def _al_salir_mouse_de_grafico(self, event):
        self.info_inspector.set(self.texto_hint_default)
        self.lbl_inspector.config(bg="#eff6ff", fg="#1e40af")

    # =========================================================================
    # MODAL 1: TABLA COMPLETA DE PÍXELES POR NIVEL DE INTENSIDAD (0 A 255)
    # =========================================================================
    def _mostrar_modal_tabla_niveles(self):
        if self.histogramas is None or self.img_original_rgb is None:
            messagebox.showinfo("Aviso", "Primero cargue una imagen para consultar los niveles.")
            return

        modal = tk.Toplevel(self.root)
        modal.title("Conteo Exacto de Píxeles por Nivel de Intensidad (0 a 255)")
        modal.geometry("920x540")
        modal.configure(bg="#ffffff")
        modal.grab_set()

        frame_top = tk.Frame(modal, bg="#ffffff", padx=16, pady=10)
        frame_top.pack(fill=tk.X)

        tk.Label(frame_top, text="Distribución de Frecuencias Absolutas por Nivel de Intensidad Discreta [0, 255]",
                 font=('Segoe UI', 11, 'bold'), bg="#ffffff", fg=self.colores['text_main']).pack(anchor="w")

        # Buscador / Filtro de niveles
        f_buscar = tk.Frame(frame_top, bg="#ffffff")
        f_buscar.pack(anchor="w", pady=(6, 0))

        tk.Label(f_buscar, text="🔍 Filtrar Nivel:", font=('Segoe UI', 9, 'bold'), bg="#ffffff", fg="#334155").pack(side=tk.LEFT)
        var_filtro = tk.StringVar()
        entry_filtro = tk.Entry(f_buscar, textvariable=var_filtro, font=('Segoe UI', 9), width=10, relief="solid", bd=1)
        entry_filtro.pack(side=tk.LEFT, padx=6)
        tk.Label(f_buscar, text="(Escribe un número 0–255 para buscar directamente)", font=('Segoe UI', 8, 'italic'),
                 bg="#ffffff", fg="#64748b").pack(side=tk.LEFT)

        # Marco con Treeview y Scrollbar
        frame_tabla = tk.Frame(modal, bg="#ffffff", padx=16, pady=6)
        frame_tabla.pack(fill=tk.BOTH, expand=True)

        cols = ("nivel", "r_orig", "r_mod", "g_orig", "g_mod", "b_orig", "b_mod")
        tree = ttk.Treeview(frame_tabla, columns=cols, show="headings", height=16)

        titulos = {
            "nivel": "Nivel (k)",
            "r_orig": "🔴 Rojo Orig (px)",
            "r_mod": "🔴 Rojo Mod (px)",
            "g_orig": "🟢 Verde Orig (px)",
            "g_mod": "🟢 Verde Mod (px)",
            "b_orig": "🔵 Azul Orig (px)",
            "b_mod": "🔵 Azul Mod (px)"
        }
        for c, t in titulos.items():
            tree.heading(c, text=t)
            tree.column(c, anchor="center", width=120)

        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Cargar los 256 niveles
        def llenar_tabla(filtro=""):
            for item in tree.get_children():
                tree.delete(item)
            f_str = filtro.strip()
            for k in range(256):
                if f_str and f_str not in str(k):
                    continue
                r_o = _formatear_miles(self.histogramas['orig']['r'][k])
                r_m = _formatear_miles(self.histogramas['mod']['r'][k])
                g_o = _formatear_miles(self.histogramas['orig']['g'][k])
                g_m = _formatear_miles(self.histogramas['mod']['g'][k])
                b_o = _formatear_miles(self.histogramas['orig']['b'][k])
                b_m = _formatear_miles(self.histogramas['mod']['b'][k])
                tree.insert("", tk.END, values=(k, r_o, r_m, g_o, g_m, b_o, b_m))

        llenar_tabla()
        var_filtro.trace_add("write", lambda *args: llenar_tabla(var_filtro.get()))

    # =========================================================================
    # MODAL 2: EVALUACIÓN CUANTITATIVA Y CONSERVACIÓN DE MASA
    # =========================================================================
    def _mostrar_modal_metricas(self):
        if self.estadisticas is None:
            messagebox.showinfo("Aviso", "Primero cargue una imagen para ver las métricas.")
            return

        modal = tk.Toplevel(self.root)
        modal.title("Evaluación Cuantitativa y Conservación de Masa de Píxeles")
        modal.geometry("860x420")
        modal.configure(bg="#ffffff")
        modal.grab_set()

        frame = tk.Frame(modal, bg="#ffffff", padx=16, pady=14)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Teorema de Conservación de Masa de Píxeles (PHE)",
                 font=('Segoe UI', 11, 'bold'), bg="#ffffff", fg=self.colores['text_main']).pack(anchor="w")

        tk.Label(frame, text="Garantiza que la suma de frecuencias modificadas es idéntica a la masa original: ∑ H_mod = ∑ H_orig = M × N",
                 font=('Segoe UI', 8, 'italic'), bg="#ffffff", fg=self.colores['text_muted']).pack(anchor="w", pady=(2, 10))

        columnas = ("canal", "media_orig", "desv_orig", "media_mod", "desv_mod", "exceso", "pico_max", "masa_mod", "estado")
        tree = ttk.Treeview(frame, columns=columnas, show="headings", height=5)

        titulos = {
            "canal": "Espectro",
            "media_orig": "μ Orig",
            "desv_orig": "σ Orig",
            "media_mod": "μ Mod",
            "desv_mod": "σ Mod",
            "exceso": "Exceso Transferido (E)",
            "pico_max": "Pico Máx",
            "masa_mod": "Masa Total",
            "estado": "Conservación"
        }
        for c, t in titulos.items():
            tree.heading(c, text=t)
            tree.column(c, anchor="center", width=95)

        total_px = self.img_original_rgb.shape[0] * self.img_original_rgb.shape[1]
        for nom, k in [("Rojo (R)", 'r'), ("Verde (G)", 'g'), ("Azul (B)", 'b')]:
            mu_o, sig_o = self.estadisticas['orig'][k]
            mu_m, sig_m = self.estadisticas['mod'][k]
            exc = self.estadisticas['exceso'][k]
            pico = int(np.max(self.histogramas['orig'][k]))
            masa = int(np.round(np.sum(self.histogramas['mod'][k])))
            estado = "✅ Exacta (0% error)" if masa == total_px else "❌ Discrepancia"

            tree.insert("", tk.END, values=(
                nom, f"{mu_o:.2f}", f"{sig_o:.2f}", f"{mu_m:.2f}", f"{sig_m:.2f}",
                _formatear_miles(exc), _formatear_miles(pico), _formatear_miles(masa), estado
            ))
        tree.pack(fill=tk.X, pady=8)

        # Fórmulas
        box_f = tk.LabelFrame(frame, text=" Fórmulas Matemáticas Implementadas ",
                              font=('Segoe UI', 8, 'bold'), bg="#ffffff", fg="#334155", padx=8, pady=6)
        box_f.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        formulas = (
            "1. Media Uniforme Teórica:     H_bar = N_total / 256\n"
            "2. Umbral Dinámico de Meseta:  U(f) = H_max - f × (H_max - H_bar)\n"
            "3. Píxeles Excedentes:         E = ∑ max(H_orig[k] - U(f), 0)\n"
            "4. Redistribución Homogénea:   H_mod[k] = min(H_orig[k], U(f)) + (E / 256)\n"
            "5. Conservación de Masa:       ∑ H_mod[k] = (N_total - E) + 256 × (E / 256) = N_total"
        )
        tk.Label(box_f, text=formulas, font=('Consolas', 8), bg="#ffffff", fg="#0f172a", justify=tk.LEFT).pack(anchor="w")

    def _accion_guardar_resultado(self):
        if self.img_modificada_rgb is None:
            messagebox.showwarning("Aviso", "No hay ninguna imagen modificada para guardar.")
            return

        dir_res = os.path.join(DIR_ACTUAL, "resultados")
        os.makedirs(dir_res, exist_ok=True)
        nombre_defecto = "resultado_contraste_rgb.png"

        ruta = filedialog.asksaveasfilename(
            title="Guardar Imagen Procesada",
            initialdir=dir_res,
            initialfile=nombre_defecto,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("Todos", "*.*")]
        )
        if ruta:
            try:
                exito = utils.guardar_imagen_rgb(self.img_modificada_rgb, ruta)
                if exito:
                    messagebox.showinfo("Éxito", f"Imagen guardada correctamente en:\n{ruta}")
                else:
                    messagebox.showerror("Error", "No se pudo codificar la imagen para guardar.")
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al guardar:\n{e}")
