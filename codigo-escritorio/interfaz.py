"""
Interfaz Gráfica de Escritorio (Tkinter + Matplotlib + Pillow)
==============================================================
Proyecto: Configuración de Histogramas (Contraste) - PDI
Permite cargar imágenes RGB, descomponer en sus espectros,
presentar histogramas discretos, manipular contrastes mediante
Plateau Histogram Equalization y visualizar imágenes e histogramas
modificados en tiempo real.
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

import transformaciones as pdi
import utils

DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))


class AplicacionHistogramasDesktop:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Configuración de Histogramas (Contraste) - PDI Escritorio")
        self.root.geometry("1380x880")
        self.root.minsize(1100, 720)
        try:
            self.root.state('zoomed')  # Maximizar en Windows
        except Exception:
            pass

        # Estado de imagen y procesamiento
        self.img_original_rgb = None
        self.img_modificada_rgb = None
        self.histogramas = None
        self.estadisticas = None
        self.canales_espectros = None

        # Variables de control de contraste (deslizadores 0 a 100)
        self.redist_r = tk.IntVar(value=60)
        self.redist_g = tk.IntVar(value=35)
        self.redist_b = tk.IntVar(value=0)

        # Variables de visualización
        self.zoom_rango = tk.StringVar(value="todo")   # 'todo', 'sombras', 'medios', 'luces'
        self.escala_y = tk.StringVar(value="lineal")   # 'lineal', 'log'
        self.modo_color_espectros = tk.StringVar(value="color") # 'color', 'gris'

        # Metadatos dinámicos
        self.info_dimensiones = tk.StringVar(value="Sin imagen")
        self.info_tiempo_ms = tk.StringVar(value="0.00 ms")
        self.info_pixeles_r = tk.StringVar(value="0 px transferidos")
        self.info_pixeles_g = tk.StringVar(value="0 px transferidos")
        self.info_pixeles_b = tk.StringVar(value="0 px transferidos")

        # Referencias de imágenes PhotoImage para evitar garbage collection
        self.photo_orig = None
        self.photo_mod = None
        self.photo_esp_r = None
        self.photo_esp_g = None
        self.photo_esp_b = None

        # Referencias de botones pill para sincronizar estilo activo
        self.btn_pills_zoom = {}
        self.btn_pills_escala = {}

        # Construir estilo e interfaz
        self._configurar_estilos()
        self._construir_interfaz()

        # Cargar imagen de muestra inicial
        self.root.after(100, self._cargar_imagen_defecto)

    def _configurar_estilos(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        # Paleta moderna
        self.colores = {
            'bg_app': '#f1f5f9',
            'bg_card': '#ffffff',
            'border': '#cbd5e1',
            'text': '#0f172a',
            'text_muted': '#475569',
            'blue': '#2563eb',
            'red': '#dc2626',
            'green': '#16a34a'
        }
        self.root.configure(bg=self.colores['bg_app'])

        self.style.configure('TFrame', background=self.colores['bg_app'])
        self.style.configure('Card.TFrame', background=self.colores['bg_card'])
        self.style.configure('TNotebook', background=self.colores['bg_app'], borderwidth=0)
        self.style.configure('TNotebook.Tab', font=('Segoe UI', 9, 'bold'), padding=(12, 6))

    def _construir_interfaz(self):
        # 1. ENCABEZADO SUPERIOR
        header = tk.Frame(self.root, bg="#ffffff", height=48, highlightbackground="#cbd5e1", highlightthickness=1)
        header.pack(fill=tk.X, padx=8, pady=(6, 4))
        header.pack_propagate(False)

        brand_frame = tk.Frame(header, bg="#ffffff")
        brand_frame.pack(side=tk.LEFT, padx=12, pady=6)

        lbl_icono = tk.Label(brand_frame, text="📊", font=('Segoe UI', 14), bg="#ffffff")
        lbl_icono.pack(side=tk.LEFT, padx=(0, 6))

        lbl_titulo = tk.Label(brand_frame, text="Configuración de Histogramas (Contraste) - PDI",
                              font=('Segoe UI', 11, 'bold'), fg="#0f172a", bg="#ffffff")
        lbl_titulo.pack(side=tk.LEFT)

        lbl_badge_dim = tk.Label(brand_frame, textvariable=self.info_dimensiones,
                                 font=('Consolas', 9, 'bold'), fg="#2563eb", bg="#eff6ff",
                                 padx=8, pady=1, relief="solid", bd=1)
        lbl_badge_dim.pack(side=tk.LEFT, padx=10)

        lbl_sub = tk.Label(header, text="Inteligencia Artificial • Procesamiento Digital de Imágenes",
                           font=('Segoe UI', 8, 'italic'), fg="#64748b", bg="#ffffff")
        lbl_sub.pack(side=tk.LEFT, padx=10)

        badge_tiempo = tk.Label(header, textvariable=self.info_tiempo_ms,
                                font=('Consolas', 9, 'bold'), fg="#15803d", bg="#dcfce7",
                                padx=8, pady=2, relief="solid", bd=1)
        badge_tiempo.pack(side=tk.RIGHT, padx=12)

        # 2. CUERPO PRINCIPAL (Split: Izquierda Controles / Derecha Visualización)
        cuerpo = tk.Frame(self.root, bg=self.colores['bg_app'])
        cuerpo.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        # PANEL IZQUIERDO: CONTROLES
        panel_ctrl = tk.Frame(cuerpo, bg="#ffffff", width=340, highlightbackground="#cbd5e1", highlightthickness=1)
        panel_ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        panel_ctrl.pack_propagate(False)

        self._construir_panel_controles(panel_ctrl)

        # PANEL DERECHO: NOTEBOOK CON PESTAÑAS
        self.notebook = ttk.Notebook(cuerpo)
        self.notebook.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Pestaña 1: Visor General e Histogramas
        self.tab_general = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_general, text="  🖼️ Visor General e Histogramas  ")
        self._construir_tab_general(self.tab_general)

        # Pestaña 2: Descomposición de Espectros
        self.tab_espectros = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_espectros, text="  🌈 Descomposición Espectral (R, G, B)  ")
        self._construir_tab_espectros(self.tab_espectros)

        # Pestaña 3: Conservación de Masa y Métricas
        self.tab_metricas = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_metricas, text="  📈 Métricas y Conservación de Masa  ")
        self._construir_tab_metricas(self.tab_metricas)

    def _construir_panel_controles(self, parent):
        # Título de sección de acciones
        lbl_acc = tk.Label(parent, text="Acciones de Imagen", font=('Segoe UI', 9, 'bold'),
                           bg="#ffffff", fg="#0f172a")
        lbl_acc.pack(anchor="w", padx=12, pady=(10, 4))

        # Botones principales
        btn_frame = tk.Frame(parent, bg="#ffffff")
        btn_frame.pack(fill=tk.X, padx=10, pady=2)

        btn_cargar = tk.Button(btn_frame, text="📁 Cargar Imagen...", font=('Segoe UI', 9, 'bold'),
                               bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
                               relief="flat", cursor="hand2", padx=8, pady=4, command=self._accion_cargar_imagen)
        btn_cargar.pack(fill=tk.X, pady=2)

        btn_defecto = tk.Button(btn_frame, text="🔄 Imagen de Muestra", font=('Segoe UI', 8),
                                bg="#f1f5f9", fg="#334155", relief="groove", bd=1,
                                cursor="hand2", command=self._cargar_imagen_defecto)
        btn_defecto.pack(fill=tk.X, pady=2)

        btn_reset = tk.Button(btn_frame, text="↺ Restablecer Deslizadores (0%)", font=('Segoe UI', 8),
                              bg="#f1f5f9", fg="#334155", relief="groove", bd=1,
                              cursor="hand2", command=self._accion_resetear_sliders)
        btn_reset.pack(fill=tk.X, pady=2)

        btn_guardar = tk.Button(btn_frame, text="💾 Guardar Imagen Modificada", font=('Segoe UI', 8, 'bold'),
                                bg="#16a34a", fg="#ffffff", activebackground="#15803d", activeforeground="#ffffff",
                                relief="flat", cursor="hand2", command=self._accion_guardar_resultado)
        btn_guardar.pack(fill=tk.X, pady=(2, 6))

        # Separador
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=6)

        # SLIDERS DE REDISTRIBUCIÓN POR ESPECTRO (R, G, B)
        lbl_redist = tk.Label(parent, text="Manipulación de Contraste (PHE)",
                              font=('Segoe UI', 9, 'bold'), bg="#ffffff", fg="#0f172a")
        lbl_redist.pack(anchor="w", padx=12, pady=(4, 2))

        # Slider Rojo
        box_r = tk.LabelFrame(parent, text=" Espectro Rojo (R) ", font=('Segoe UI', 8, 'bold'),
                              fg="#dc2626", bg="#ffffff", bd=1, padx=6, pady=4)
        box_r.pack(fill=tk.X, padx=10, pady=3)

        info_r_frame = tk.Frame(box_r, bg="#ffffff")
        info_r_frame.pack(fill=tk.X)
        self.lbl_val_r = tk.Label(info_r_frame, text="60%", font=('Consolas', 9, 'bold'),
                                  fg="#dc2626", bg="#fef2f2", padx=4)
        self.lbl_val_r.pack(side=tk.RIGHT)
        tk.Label(info_r_frame, textvariable=self.info_pixeles_r, font=('Consolas', 7),
                 fg="#64748b", bg="#ffffff").pack(side=tk.LEFT)

        scale_r = tk.Scale(box_r, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.redist_r,
                           showvalue=False, bg="#ffffff", troughcolor="#cbd5e1", activebackground="#dc2626",
                           command=lambda v: self._al_mover_slider('r', v))
        scale_r.pack(fill=tk.X)

        # Slider Verde
        box_g = tk.LabelFrame(parent, text=" Espectro Verde (G) ", font=('Segoe UI', 8, 'bold'),
                              fg="#16a34a", bg="#ffffff", bd=1, padx=6, pady=4)
        box_g.pack(fill=tk.X, padx=10, pady=3)

        info_g_frame = tk.Frame(box_g, bg="#ffffff")
        info_g_frame.pack(fill=tk.X)
        self.lbl_val_g = tk.Label(info_g_frame, text="35%", font=('Consolas', 9, 'bold'),
                                  fg="#16a34a", bg="#f0fdf4", padx=4)
        self.lbl_val_g.pack(side=tk.RIGHT)
        tk.Label(info_g_frame, textvariable=self.info_pixeles_g, font=('Consolas', 7),
                 fg="#64748b", bg="#ffffff").pack(side=tk.LEFT)

        scale_g = tk.Scale(box_g, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.redist_g,
                           showvalue=False, bg="#ffffff", troughcolor="#cbd5e1", activebackground="#16a34a",
                           command=lambda v: self._al_mover_slider('g', v))
        scale_g.pack(fill=tk.X)

        # Slider Azul
        box_b = tk.LabelFrame(parent, text=" Espectro Azul (B) ", font=('Segoe UI', 8, 'bold'),
                              fg="#2563eb", bg="#ffffff", bd=1, padx=6, pady=4)
        box_b.pack(fill=tk.X, padx=10, pady=3)

        info_b_frame = tk.Frame(box_b, bg="#ffffff")
        info_b_frame.pack(fill=tk.X)
        self.lbl_val_b = tk.Label(info_b_frame, text="0%", font=('Consolas', 9, 'bold'),
                                  fg="#2563eb", bg="#eff6ff", padx=4)
        self.lbl_val_b.pack(side=tk.RIGHT)
        tk.Label(info_b_frame, textvariable=self.info_pixeles_b, font=('Consolas', 7),
                 fg="#64748b", bg="#ffffff").pack(side=tk.LEFT)

        scale_b = tk.Scale(box_b, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.redist_b,
                           showvalue=False, bg="#ffffff", troughcolor="#cbd5e1", activebackground="#2563eb",
                           command=lambda v: self._al_mover_slider('b', v))
        scale_b.pack(fill=tk.X)

        # Separador
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=6)

        # OPCIONES DE VISUALIZACIÓN DE HISTOGRAMAS
        lbl_vis = tk.Label(parent, text="Opciones de Gráficos", font=('Segoe UI', 9, 'bold'),
                           bg="#ffffff", fg="#0f172a")
        lbl_vis.pack(anchor="w", padx=12, pady=(2, 2))

        # Escala Y
        f_esc = tk.Frame(parent, bg="#ffffff")
        f_esc.pack(fill=tk.X, padx=12, pady=2)
        tk.Label(f_esc, text="Escala Eje Y:", font=('Segoe UI', 8, 'bold'),
                 bg="#ffffff", fg="#334155").pack(side=tk.LEFT)
        for val, txt in [("lineal", "Lineal"), ("log", "Logarítmica")]:
            rb = tk.Radiobutton(f_esc, text=txt, value=val, variable=self.escala_y,
                                font=('Segoe UI', 8), bg="#ffffff", activebackground="#ffffff",
                                command=lambda: self.set_escala(self.escala_y.get()))
            rb.pack(side=tk.LEFT, padx=4)

        # Zoom / Rango de Bins
        f_zoom = tk.Frame(parent, bg="#ffffff")
        f_zoom.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(f_zoom, text="Zoom Bins:", font=('Segoe UI', 8, 'bold'),
                 bg="#ffffff", fg="#334155").pack(side=tk.LEFT)
        self.cmb_zoom = ttk.Combobox(f_zoom, textvariable=self.zoom_rango,
                                     values=["todo", "sombras", "medios", "luces"],
                                     state="readonly", width=12, font=('Segoe UI', 8))
        self.cmb_zoom.pack(side=tk.RIGHT)
        self.cmb_zoom.bind("<<ComboboxSelected>>", lambda e: self.set_zoom_preset(self.zoom_rango.get()))

        # Tip Explicativo
        tip_frame = tk.Frame(parent, bg="#eff6ff", bd=1, relief="solid")
        tip_frame.pack(fill=tk.X, padx=10, pady=(10, 6))
        tk.Label(tip_frame, text="💡 Conservación Estricta de Masa:\nCada píxel recortado de los picos se\nredistribuye a los 256 niveles uniformemente.",
                 font=('Segoe UI', 7), fg="#1e40af", bg="#eff6ff", justify=tk.LEFT, padx=6, pady=6).pack()

    def _construir_tab_general(self, parent):
        # Contenedor vertical: Arriba las imágenes comparativas, Medio toolbar zoom, Abajo los 6 histogramas
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=5)  # Imágenes
        parent.rowconfigure(1, weight=0)  # Barra de herramientas Zoom y Escala
        parent.rowconfigure(2, weight=6)  # Histogramas

        # FILA 0: VISORES COMPARATIVOS DE IMÁGENES
        frame_visores = tk.Frame(parent, bg=self.colores['bg_app'])
        frame_visores.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 2))
        frame_visores.columnconfigure(0, weight=1)
        frame_visores.columnconfigure(1, weight=1)
        frame_visores.rowconfigure(0, weight=1)

        # Tarjeta Imagen Original
        card_orig = tk.LabelFrame(frame_visores, text=" Imagen Original (RGB) ",
                                  font=('Segoe UI', 9, 'bold'), bg="#ffffff", bd=1)
        card_orig.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)
        self.lbl_canvas_orig = tk.Label(card_orig, bg="#0f172a")
        self.lbl_canvas_orig.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tarjeta Imagen Modificada
        card_mod = tk.LabelFrame(frame_visores, text=" Imagen Modificada (Contraste Redistribuido) ",
                                 font=('Segoe UI', 9, 'bold'), bg="#ffffff", bd=1)
        card_mod.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)
        self.lbl_canvas_mod = tk.Label(card_mod, bg="#0f172a")
        self.lbl_canvas_mod.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # FILA 1: BARRA DE HERRAMIENTAS (Zoom de Inspección y Escala Eje Y)
        toolbar_bar = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", highlightbackground="#cbd5e1", padx=8, pady=3)
        toolbar_bar.grid(row=1, column=0, sticky="ew", padx=4, pady=2)

        # 1. Grupo Zoom de Inspección (Izquierda)
        f_zoom_group = tk.Frame(toolbar_bar, bg="#ffffff")
        f_zoom_group.pack(side=tk.LEFT, padx=(0, 6))

        lbl_zoom_title = tk.Label(f_zoom_group, text="Zoom de Inspección:", font=('Segoe UI', 9, 'bold'),
                                  bg="#ffffff", fg="#0f172a")
        lbl_zoom_title.pack(side=tk.LEFT, padx=(0, 6))

        # Contenedor de Pills de Zoom
        pill_container = tk.Frame(f_zoom_group, bg="#f1f5f9", bd=1, relief="solid", highlightbackground="#e2e8f0", padx=2, pady=2)
        pill_container.pack(side=tk.LEFT, padx=(0, 6))

        opciones_zoom = [
            ("todo", "Todo (0–255)"),
            ("sombras", "Sombras (0–85)"),
            ("medios", "Medios (85–170)"),
            ("luces", "Luces (170–255)")
        ]

        self.btn_pills_zoom = {}
        for clave, texto in opciones_zoom:
            btn = tk.Button(pill_container, text=texto, font=('Segoe UI', 8),
                            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
                            activebackground="#ffffff", activeforeground="#2563eb",
                            command=lambda c=clave: self.set_zoom_preset(c))
            btn.pack(side=tk.LEFT, padx=1)
            self.btn_pills_zoom[clave] = btn

        # Botón Restaurar Zoom
        btn_restaurar = tk.Button(f_zoom_group, text="↺ Restaurar Zoom", font=('Segoe UI', 8),
                                  bg="#f8fafc", fg="#0f172a", relief="solid", bd=1,
                                  padx=8, pady=2, cursor="hand2", activebackground="#e2e8f0",
                                  command=lambda: self.set_zoom_preset("todo"))
        btn_restaurar.pack(side=tk.LEFT, padx=2)

        # 2. Escala Eje Y (Derecha)
        f_escala_group = tk.Frame(toolbar_bar, bg="#ffffff")
        f_escala_group.pack(side=tk.RIGHT, padx=(6, 0))

        pill_esc_container = tk.Frame(f_escala_group, bg="#f1f5f9", bd=1, relief="solid", highlightbackground="#e2e8f0", padx=2, pady=2)
        pill_esc_container.pack(side=tk.RIGHT)

        opciones_escala = [("lineal", "Lineal"), ("log", "Log-Y")]

        self.btn_pills_escala = {}
        for clave, texto in opciones_escala:
            btn = tk.Button(pill_esc_container, text=texto, font=('Segoe UI', 8),
                            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
                            activebackground="#ffffff", activeforeground="#2563eb",
                            command=lambda c=clave: self.set_escala(c))
            btn.pack(side=tk.LEFT, padx=1)
            self.btn_pills_escala[clave] = btn

        lbl_esc_title = tk.Label(f_escala_group, text="Escala Eje Y:", font=('Segoe UI', 9, 'bold'),
                                 bg="#ffffff", fg="#0f172a")
        lbl_esc_title.pack(side=tk.RIGHT, padx=(0, 6))

        # 3. Hint en el centro
        lbl_hint = tk.Label(toolbar_bar, text="💡 Recorte y redistribución uniforme de picos • Bins discretos [0, 255]",
                            font=('Segoe UI', 8, 'italic'), bg="#ffffff", fg="#64748b")
        lbl_hint.pack(side=tk.LEFT, padx=10)

        # FILA 2: BANCO DE 6 HISTOGRAMAS DISCRETOS (Matplotlib Canvas)
        frame_hist = tk.LabelFrame(parent, text=" Banco de 6 Histogramas Discretos por Espectro Cromático ",
                                   font=('Segoe UI', 9, 'bold'), bg="#ffffff", bd=1)
        frame_hist.grid(row=2, column=0, sticky="nsew", padx=4, pady=(2, 4))

        # Figura Matplotlib: 2 filas x 3 columnas
        self.fig_hist = Figure(figsize=(10, 4.2), dpi=95, facecolor="#ffffff")
        self.fig_hist.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.12, wspace=0.22, hspace=0.38)
        self.axs = self.fig_hist.subplots(2, 3)

        self.canvas_hist = FigureCanvasTkAgg(self.fig_hist, master=frame_hist)
        self.canvas_hist.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Inicializar estilos activos en los pills
        self._actualizar_estilo_pills_zoom()
        self._actualizar_estilo_pills_escala()

    def _construir_tab_espectros(self, parent):
        # Muestra visualmente la descomposición en los 3 canales
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(0, weight=1)

        # Espectro Rojo
        card_r = tk.LabelFrame(parent, text=" Espectro Rojo (Canal R) ",
                               font=('Segoe UI', 9, 'bold'), fg="#dc2626", bg="#ffffff", bd=1)
        card_r.grid(row=0, column=0, sticky="nsew", padx=4, pady=6)
        self.lbl_esp_r = tk.Label(card_r, bg="#1e1e1e")
        self.lbl_esp_r.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Espectro Verde
        card_g = tk.LabelFrame(parent, text=" Espectro Verde (Canal G) ",
                               font=('Segoe UI', 9, 'bold'), fg="#16a34a", bg="#ffffff", bd=1)
        card_g.grid(row=0, column=1, sticky="nsew", padx=4, pady=6)
        self.lbl_esp_g = tk.Label(card_g, bg="#1e1e1e")
        self.lbl_esp_g.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Espectro Azul
        card_b = tk.LabelFrame(parent, text=" Espectro Azul (Canal B) ",
                               font=('Segoe UI', 9, 'bold'), fg="#2563eb", bg="#ffffff", bd=1)
        card_b.grid(row=0, column=2, sticky="nsew", padx=4, pady=6)
        self.lbl_esp_b = tk.Label(card_b, bg="#1e1e1e")
        self.lbl_esp_b.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _construir_tab_metricas(self, parent):
        # Muestra tabla y verificación de conservación de masa
        frame_tabla = tk.Frame(parent, bg="#ffffff", padx=14, pady=12, bd=1, relief="solid")
        frame_tabla.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        tk.Label(frame_tabla, text="Evaluación Cuantitativa y Conservación de Masa de Píxeles",
                 font=('Segoe UI', 11, 'bold'), bg="#ffffff", fg="#0f172a").pack(anchor="w", pady=(0, 6))

        tk.Label(frame_tabla,
                 text="El teorema de conservación garantiza que la suma de frecuencias modificadas es idéntica a la masa original: ∑ H_mod = ∑ H_orig = M × N",
                 font=('Segoe UI', 8, 'italic'), bg="#ffffff", fg="#64748b").pack(anchor="w", pady=(0, 10))

        columnas = ("canal", "media_orig", "desv_orig", "media_mod", "desv_mod", "exceso_px", "pico_max", "masa_total", "estado")
        self.tree_metricas = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=6)

        titulos = {
            "canal": "Espectro",
            "media_orig": "μ Original",
            "desv_orig": "σ Original",
            "media_mod": "μ Modificado",
            "desv_mod": "σ Modificado",
            "exceso_px": "Exceso Transferido (E)",
            "pico_max": "Pico Máx Inicial",
            "masa_total": "Masa Total (px)",
            "estado": "Conservación"
        }
        for col, txt in titulos.items():
            self.tree_metricas.heading(col, text=txt)
            self.tree_metricas.column(col, anchor="center", width=120)

        self.tree_metricas.pack(fill=tk.X, pady=6)

        # Marco con resumen teórico de variables
        box_teoria = tk.LabelFrame(frame_tabla, text=" Fórmulas Matemáticas Implementadas en Tiempo Real ",
                                  font=('Segoe UI', 9, 'bold'), bg="#ffffff", fg="#334155", padx=10, pady=8)
        box_teoria.pack(fill=tk.BOTH, expand=True, pady=10)

        texto_teoria = (
            "1. Media Uniforme Teórica:     H_bar = N_total / 256\n"
            "2. Umbral Dinámico de Meseta:  U(f) = H_max - f × (H_max - H_bar)\n"
            "3. Píxeles Excedentes:         E = ∑ max(H_orig[k] - U(f), 0)\n"
            "4. Redistribución Homogénea:   H_mod[k] = min(H_orig[k], U(f)) + (E / 256)\n"
            "5. Conservación de Masa:       ∑ H_mod[k] = (N_total - E) + 256 × (E / 256) = N_total  (Sin pérdidas ni adiciones)\n"
            "6. Tabla de Consulta (LUT):    LUT[k] = clip( (1 - f) × k + f × T_eq(k), 0, 255 )"
        )
        tk.Label(box_teoria, text=texto_teoria, font=('Consolas', 9), bg="#ffffff", fg="#0f172a", justify=tk.LEFT).pack(anchor="w")

    # =========================================================================
    # LÓGICA DE CARGA Y PROCESAMIENTO
    # =========================================================================

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
            # Crear sintética si no se encuentra
            sintetica = np.zeros((450, 682, 3), dtype=np.uint8)
            sintetica[:, :] = (180, 120, 80)
            self._establecer_imagen_original(sintetica)

    def _accion_cargar_imagen(self):
        tipos = [
            ("Archivos de Imagen", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("JPEG", "*.jpg *.jpeg"),
            ("PNG", "*.png"),
            ("Todos los archivos", "*.*")
        ]
        ruta = filedialog.askopenfilename(title="Seleccionar Imagen RGB", filetypes=tipos)
        if ruta:
            try:
                self._cargar_imagen_desde_ruta(ruta)
            except Exception as e:
                messagebox.showerror("Error al cargar imagen", f"No se pudo cargar la imagen:\n{e}")

    def _cargar_imagen_desde_ruta(self, ruta: str):
        img_rgb = utils.cargar_imagen_rgb(ruta)
        self._establecer_imagen_original(img_rgb)

    def _establecer_imagen_original(self, img_rgb: np.ndarray):
        self.img_original_rgb = img_rgb
        alto, ancho = img_rgb.shape[:2]
        total_px = ancho * alto
        self.info_dimensiones.set(f"{ancho} × {alto} px ({total_px:,} px)")
        self._ejecutar_procesamiento()

    def _al_mover_slider(self, canal, valor):
        v = int(valor)
        if canal == 'r':
            self.lbl_val_r.config(text=f"{v}%")
        elif canal == 'g':
            self.lbl_val_g.config(text=f"{v}%")
        elif canal == 'b':
            self.lbl_val_b.config(text=f"{v}%")
        self._ejecutar_procesamiento()

    def _accion_resetear_sliders(self):
        self.redist_r.set(0)
        self.redist_g.set(0)
        self.redist_b.set(0)
        self.lbl_val_r.config(text="0%")
        self.lbl_val_g.config(text="0%")
        self.lbl_val_b.config(text="0%")
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

        # Actualizar labels de píxeles transferidos
        self.info_tiempo_ms.set(f"{tiempo_ms:.2f} ms")
        self.info_pixeles_r.set(f"{stats['exceso']['r']:,} px transferidos")
        self.info_pixeles_g.set(f"{stats['exceso']['g']:,} px transferidos")
        self.info_pixeles_b.set(f"{stats['exceso']['b']:,} px transferidos")

        # Refrescar visualizaciones
        self._actualizar_visores_imagenes()
        self._actualizar_histogramas_en_pantalla()
        self._actualizar_tab_espectros()
        self._actualizar_tabla_metricas()

    def _actualizar_visores_imagenes(self):
        # Obtener dimensiones disponibles para escalar
        max_w = max(200, self.lbl_canvas_orig.winfo_width())
        max_h = max(180, self.lbl_canvas_orig.winfo_height())
        if max_w <= 1 or max_h <= 1:
            max_w, max_h = 480, 260

        # Imagen original
        self.photo_orig, _, _ = utils.numpy_a_photoimage(self.img_original_rgb, max_w, max_h)
        if self.photo_orig:
            self.lbl_canvas_orig.config(image=self.photo_orig)

        # Imagen modificada
        self.photo_mod, _, _ = utils.numpy_a_photoimage(self.img_modificada_rgb, max_w, max_h)
        if self.photo_mod:
            self.lbl_canvas_mod.config(image=self.photo_mod)

    def set_zoom_preset(self, preset: str):
        """Ajusta el rango de inspección del histograma y actualiza visualmente los botones pill."""
        self.zoom_rango.set(preset)
        if hasattr(self, 'cmb_zoom'):
            self.cmb_zoom.set(preset)
        self._actualizar_estilo_pills_zoom()
        self._actualizar_histogramas_en_pantalla()

    def _actualizar_estilo_pills_zoom(self):
        activo = self.zoom_rango.get()
        for clave, btn in self.btn_pills_zoom.items():
            if clave == activo:
                btn.config(bg="#ffffff", fg="#2563eb", font=('Segoe UI', 8, 'bold'), relief="solid", bd=1)
            else:
                btn.config(bg="#f1f5f9", fg="#334155", font=('Segoe UI', 8), relief="flat", bd=0)

    def set_escala(self, escala: str):
        """Ajusta la escala del eje Y (lineal o logarítmica) y actualiza visualmente los botones pill."""
        self.escala_y.set(escala)
        self._actualizar_estilo_pills_escala()
        self._actualizar_histogramas_en_pantalla()

    def _actualizar_estilo_pills_escala(self):
        activo = self.escala_y.get()
        for clave, btn in self.btn_pills_escala.items():
            if clave == activo:
                btn.config(bg="#ffffff", fg="#2563eb", font=('Segoe UI', 8, 'bold'), relief="solid", bd=1)
            else:
                btn.config(bg="#f1f5f9", fg="#334155", font=('Segoe UI', 8), relief="flat", bd=0)

    def _actualizar_histogramas_en_pantalla(self):
        if self.histogramas is None:
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
        canales = ['r', 'g', 'b']
        colores_hex = ['#dc2626', '#16a34a', '#2563eb']
        nombres = ['Rojo', 'Verde', 'Azul']

        bins_x = np.arange(256)
        bins_mask = (bins_x >= b_min) & (bins_x <= b_max)
        x_indices = bins_x[bins_mask]

        for col_idx, k in enumerate(canales):
            color = colores_hex[col_idx]
            nombre = nombres[col_idx]

            # Fila 0: Original
            ax_orig = self.axs[0, col_idx]
            ax_orig.clear()
            h_orig = self.histogramas['orig'][k][bins_mask]
            ax_orig.bar(x_indices, h_orig, color=color, width=1.0, alpha=0.85)

            mu_o, sig_o = self.estadisticas['orig'][k]
            ax_orig.set_title(f"{nombre} [ORIGINAL]  μ:{mu_o} | σ:{sig_o}",
                              fontsize=8, fontweight='bold', color=color, pad=3)
            ax_orig.set_xlim(b_min, b_max)
            ax_orig.grid(True, linestyle=":", alpha=0.5)
            ax_orig.tick_params(labelsize=7)
            if es_log:
                ax_orig.set_yscale('log')

            # Fila 1: Modificado
            ax_mod = self.axs[1, col_idx]
            ax_mod.clear()
            h_mod = self.histogramas['mod'][k][bins_mask]
            ax_mod.bar(x_indices, h_mod, color=color, width=1.0, alpha=0.85)

            # Línea guía de umbral si hay redistribución activa
            umb = self.estadisticas['umbrales'][k]
            if (k == 'r' and self.redist_r.get() > 0) or \
               (k == 'g' and self.redist_g.get() > 0) or \
               (k == 'b' and self.redist_b.get() > 0):
                ax_mod.axhline(y=umb, color="#f59e0b", linestyle="--", linewidth=1.2, label="Umbral U")

            mu_m, sig_m = self.estadisticas['mod'][k]
            ax_mod.set_title(f"{nombre} [MODIFICADO]  μ:{mu_m} | σ:{sig_m}",
                             fontsize=8, fontweight='bold', color=color, pad=3)
            ax_mod.set_xlim(b_min, b_max)
            ax_mod.grid(True, linestyle=":", alpha=0.5)
            ax_mod.tick_params(labelsize=7)
            if es_log:
                ax_mod.set_yscale('log')

        self.fig_hist.tight_layout()
        self.canvas_hist.draw_idle()

    def _actualizar_tab_espectros(self):
        if self.canales_espectros is None:
            return

        max_w = max(180, self.lbl_esp_r.winfo_width())
        max_h = max(180, self.lbl_esp_r.winfo_height())
        if max_w <= 1 or max_h <= 1:
            max_w, max_h = 360, 320

        # Espectro Rojo en color rojo
        c_r = self.canales_espectros['mod']['r']
        rgb_r = pdi.generar_vista_espectro_color(c_r, 'r')
        self.photo_esp_r, _, _ = utils.numpy_a_photoimage(rgb_r, max_w, max_h)
        if self.photo_esp_r:
            self.lbl_esp_r.config(image=self.photo_esp_r)

        # Espectro Verde en color verde
        c_g = self.canales_espectros['mod']['g']
        rgb_g = pdi.generar_vista_espectro_color(c_g, 'g')
        self.photo_esp_g, _, _ = utils.numpy_a_photoimage(rgb_g, max_w, max_h)
        if self.photo_esp_g:
            self.lbl_esp_g.config(image=self.photo_esp_g)

        # Espectro Azul en color azul
        c_b = self.canales_espectros['mod']['b']
        rgb_b = pdi.generar_vista_espectro_color(c_b, 'b')
        self.photo_esp_b, _, _ = utils.numpy_a_photoimage(rgb_b, max_w, max_h)
        if self.photo_esp_b:
            self.lbl_esp_b.config(image=self.photo_esp_b)

    def _actualizar_tabla_metricas(self):
        if self.estadisticas is None:
            return

        for item in self.tree_metricas.get_children():
            self.tree_metricas.delete(item)

        total_px = self.img_original_rgb.shape[0] * self.img_original_rgb.shape[1]
        canales = [
            ("Rojo (R)", 'r'),
            ("Verde (G)", 'g'),
            ("Azul (B)", 'b')
        ]

        for nombre, k in canales:
            mu_o, sig_o = self.estadisticas['orig'][k]
            mu_m, sig_m = self.estadisticas['mod'][k]
            exc = self.estadisticas['exceso'][k]
            pico_max = int(np.max(self.histogramas['orig'][k]))
            masa_mod = int(np.round(np.sum(self.histogramas['mod'][k])))

            estado = "✅ Exacta (0% error)" if masa_mod == total_px else "❌ Discrepancia"

            self.tree_metricas.insert("", tk.END, values=(
                nombre,
                f"{mu_o:.2f}",
                f"{sig_o:.2f}",
                f"{mu_m:.2f}",
                f"{sig_m:.2f}",
                f"{exc:,}",
                f"{pico_max:,}",
                f"{masa_mod:,}",
                estado
            ))

    def _accion_guardar_resultado(self):
        if self.img_modificada_rgb is None:
            messagebox.showwarning("Aviso", "No hay ninguna imagen modificada para guardar.")
            return

        dir_resultados = os.path.join(DIR_ACTUAL, "resultados")
        os.makedirs(dir_resultados, exist_ok=True)
        nombre_defecto = "resultado_contraste_rgb.png"
        ruta_sugerida = os.path.join(dir_resultados, nombre_defecto)

        ruta = filedialog.asksaveasfilename(
            title="Guardar Imagen Procesada",
            initialdir=dir_resultados,
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
