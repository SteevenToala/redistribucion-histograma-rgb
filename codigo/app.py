"""
=============================================================================
PROCESAMIENTO DIGITAL DE IMÁGENES - INTELIGENCIA ARTIFICIAL
Aplicación Web: Ecualizador de Espectro RGB y Modificación de Histogramas
Backend: Flask (Python) | Frontend: Alpine.js + CSS Moderno + Canvas 60 FPS
=============================================================================
"""

import os
import sys
import base64
import webbrowser
import threading
import time
import socket
import numpy as np
import cv2
from flask import Flask, render_template, request, jsonify

DIR_CODIGO = os.path.dirname(os.path.abspath(__file__))
if DIR_CODIGO not in sys.path:
    sys.path.insert(0, DIR_CODIGO)

import transformaciones as pdi

app = Flask(__name__, template_folder=os.path.join(DIR_CODIGO, "templates"))
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

# =============================================================================
# GESTIÓN DE IMÁGENES Y ESTADO GLOBAL
# =============================================================================
def buscar_imagen_defecto():
    """Busca la imagen de muestra en carpetas candidatas."""
    candidatos = [
        os.path.join(DIR_CODIGO, "imagenes", "images.jpg"),
        os.path.join(DIR_CODIGO, "images.jpg"),
        os.path.join(os.path.dirname(DIR_CODIGO), "imagenes", "images.jpg"),
        os.path.join(DIR_CODIGO, "imagenes", "tu_imagen.jpg"),
        os.path.join(DIR_CODIGO, "tu_imagen.jpg")
    ]
    for ruta in candidatos:
        if os.path.exists(ruta):
            img = cv2.imread(ruta)
            if img is not None:
                return img
    # Sintética si no se encuentra
    synth = np.zeros((400, 500, 3), dtype=np.uint8)
    cv2.circle(synth, (250, 200), 120, (60, 180, 255), -1)
    return synth


IMAGEN_ORIGINAL = buscar_imagen_defecto()


def array_a_base64_jpg(img_bgr: np.ndarray, calidad: int = 88) -> str:
    """Convierte matriz NumPy BGR a data URI base64 JPEG."""
    _, buffer = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, calidad])
    return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"


def obtener_histogramas_rgb(img_rgb: np.ndarray):
    """Calcula los histogramas de 256 niveles para cada canal."""
    return {
        "r": np.bincount(img_rgb[:, :, 0].ravel(), minlength=256).tolist(),
        "g": np.bincount(img_rgb[:, :, 1].ravel(), minlength=256).tolist(),
        "b": np.bincount(img_rgb[:, :, 2].ravel(), minlength=256).tolist()
    }


# =============================================================================
# RUTAS Y ENDPOINTS FLASK
# =============================================================================
@app.route("/")
def index():
    return render_template("index.html")


IMAGEN_RESULTADO_ACTUAL = None


@app.route("/api/estado", methods=["GET"])
def api_estado():
    global IMAGEN_ORIGINAL
    img_rgb = cv2.cvtColor(IMAGEN_ORIGINAL, cv2.COLOR_BGR2RGB)
    stats_orig = {
        "r": {"media": round(float(np.mean(img_rgb[:, :, 0])), 1), "desv": round(float(np.std(img_rgb[:, :, 0])), 1)},
        "g": {"media": round(float(np.mean(img_rgb[:, :, 1])), 1), "desv": round(float(np.std(img_rgb[:, :, 1])), 1)},
        "b": {"media": round(float(np.mean(img_rgb[:, :, 2])), 1), "desv": round(float(np.std(img_rgb[:, :, 2])), 1)}
    }
    return jsonify({
        "success": True,
        "image_orig": array_a_base64_jpg(IMAGEN_ORIGINAL),
        "hist_orig": obtener_histogramas_rgb(img_rgb),
        "stats_orig": stats_orig,
        "width": IMAGEN_ORIGINAL.shape[1],
        "height": IMAGEN_ORIGINAL.shape[0]
    })


@app.route("/api/cargar-ejemplo", methods=["POST"])
def api_cargar_ejemplo():
    global IMAGEN_ORIGINAL
    IMAGEN_ORIGINAL = buscar_imagen_defecto()
    img_rgb = cv2.cvtColor(IMAGEN_ORIGINAL, cv2.COLOR_BGR2RGB)
    stats_orig = {
        "r": {"media": round(float(np.mean(img_rgb[:, :, 0])), 1), "desv": round(float(np.std(img_rgb[:, :, 0])), 1)},
        "g": {"media": round(float(np.mean(img_rgb[:, :, 1])), 1), "desv": round(float(np.std(img_rgb[:, :, 1])), 1)},
        "b": {"media": round(float(np.mean(img_rgb[:, :, 2])), 1), "desv": round(float(np.std(img_rgb[:, :, 2])), 1)}
    }
    return jsonify({
        "success": True,
        "image_orig": array_a_base64_jpg(IMAGEN_ORIGINAL),
        "hist_orig": obtener_histogramas_rgb(img_rgb),
        "stats_orig": stats_orig
    })


@app.route("/api/subir-imagen", methods=["POST"])
def api_subir_imagen():
    global IMAGEN_ORIGINAL
    if 'archivo' not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400
    archivo = request.files['archivo']
    file_bytes = np.frombuffer(archivo.read(), np.uint8)
    img_dec = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img_dec is None:
        return jsonify({"error": "Archivo no válido como imagen"}), 400
    IMAGEN_ORIGINAL = img_dec
    img_rgb = cv2.cvtColor(IMAGEN_ORIGINAL, cv2.COLOR_BGR2RGB)
    stats_orig = {
        "r": {"media": round(float(np.mean(img_rgb[:, :, 0])), 1), "desv": round(float(np.std(img_rgb[:, :, 0])), 1)},
        "g": {"media": round(float(np.mean(img_rgb[:, :, 1])), 1), "desv": round(float(np.std(img_rgb[:, :, 1])), 1)},
        "b": {"media": round(float(np.mean(img_rgb[:, :, 2])), 1), "desv": round(float(np.std(img_rgb[:, :, 2])), 1)}
    }
    return jsonify({
        "success": True,
        "image_orig": array_a_base64_jpg(IMAGEN_ORIGINAL),
        "hist_orig": obtener_histogramas_rgb(img_rgb),
        "stats_orig": stats_orig
    })


@app.route("/api/procesar", methods=["POST"])
def api_procesar():
    global IMAGEN_ORIGINAL, IMAGEN_RESULTADO_ACTUAL
    t0 = time.perf_counter()
    data = request.json or {}

    if IMAGEN_ORIGINAL is None:
        return jsonify({"error": "No hay imagen cargada"}), 400

    img_rgb = cv2.cvtColor(IMAGEN_ORIGINAL, cv2.COLOR_BGR2RGB)
    modo_canal = data.get("modo_canal", "global")

    canales = [img_rgb[:, :, 0], img_rgb[:, :, 1], img_rgb[:, :, 2]]
    canales_out = []
    nombres_canales = ["r", "g", "b"]

    for i, c_nombre in enumerate(nombres_canales):
        cfg = data["params_global"] if modo_canal == "global" else data.get(f"params_{c_nombre}", {})

        modo_base = cfg.get("modo", "cdf")
        clip = float(cfg.get("clip", 1.0))
        cont = float(cfg.get("contraste", 1.0))
        gamma = float(cfg.get("gamma", 1.0))
        curva_s = float(cfg.get("curva_s", 0.0))
        r_min = float(cfg.get("r_min", 0.0))
        r_max = float(cfg.get("r_max", 255.0))
        fuerza = float(cfg.get("fuerza", 1.0))

        # 1. Transformación de partida (CDF, Gaussiana, Rayleigh, Negativo)
        lut_base = pdi.calcular_lut_base(canales[i], modo=modo_base, clip_factor=clip)

        # 2. Look-Up Table compuesta de redistribución (Ventana de Niveles, Contraste, Sigmoide, Gamma)
        lut_final = pdi.generar_lut_espectro(
            contraste=cont,
            gamma=gamma,
            curva_s=curva_s,
            r_min=r_min,
            r_max=r_max,
            fuerza_eq=fuerza,
            lut_modo_base=lut_base
        )

        canales_out.append(lut_final[canales[i]])

    img_out_rgb = np.dstack(canales_out)
    img_out_bgr = cv2.cvtColor(img_out_rgb, cv2.COLOR_RGB2BGR)
    IMAGEN_RESULTADO_ACTUAL = img_out_bgr

    stats_res = {
        "r": {"media": round(float(np.mean(img_out_rgb[:, :, 0])), 1), "desv": round(float(np.std(img_out_rgb[:, :, 0])), 1)},
        "g": {"media": round(float(np.mean(img_out_rgb[:, :, 1])), 1), "desv": round(float(np.std(img_out_rgb[:, :, 1])), 1)},
        "b": {"media": round(float(np.mean(img_out_rgb[:, :, 2])), 1), "desv": round(float(np.std(img_out_rgb[:, :, 2])), 1)}
    }

    tiempo_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    return jsonify({
        "success": True,
        "image_res": array_a_base64_jpg(img_out_bgr),
        "hist_res": obtener_histogramas_rgb(img_out_rgb),
        "stats_res": stats_res,
        "tiempo_ms": tiempo_ms
    })


@app.route("/api/guardar-servidor", methods=["POST"])
def api_guardar_servidor():
    global IMAGEN_RESULTADO_ACTUAL
    if IMAGEN_RESULTADO_ACTUAL is None:
        return jsonify({"error": "No hay imagen procesada"}), 400
    dir_resultados = os.path.join(DIR_CODIGO, "resultados")
    os.makedirs(dir_resultados, exist_ok=True)
    nombre = "resultado_espectro_rgb.png"
    ruta_guardar = os.path.join(dir_resultados, nombre)
    cv2.imwrite(ruta_guardar, IMAGEN_RESULTADO_ACTUAL)
    return jsonify({
        "success": True,
        "filename": nombre,
        "path": ruta_guardar,
        "msg": f"Guardado con éxito en codigo/resultados/{nombre}"
    })


# =============================================================================
# INICIALIZACIÓN Y APERTURA DE NAVEGADOR
# =============================================================================
def buscar_puerto_libre(puerto_base=5050):
    for p in range(puerto_base, puerto_base + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return puerto_base


def abrir_navegador(puerto):
    webbrowser.open_new_tab(f"http://127.0.0.1:{puerto}")


if __name__ == "__main__":
    puerto = buscar_puerto_libre(5050)
    print("=" * 65)
    print("  MODIFICACION Y REDISTRIBUCION DE HISTOGRAMAS RGB - FLASK (PDI)")
    print(f"  Interfaz disponible en: http://127.0.0.1:{puerto}")
    print("=" * 65)

    threading.Timer(1.2, abrir_navegador, args=[puerto]).start()
    app.run(host="127.0.0.1", port=puerto, debug=False)
