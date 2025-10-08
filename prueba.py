# app.py
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import os
from datetime import datetime
import io

# Intentos de import para mejores opciones
try:
    import mediapipe as mp
    MP_AVAILABLE = True
except Exception:
    MP_AVAILABLE = False

try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
except Exception:
    REMBG_AVAILABLE = False

st.set_page_config(page_title="Foto con Fondo Mejorado", page_icon="🖼️", layout="centered")

# Carpetas
os.makedirs("fotos_stand", exist_ok=True)
os.makedirs("assets", exist_ok=True)  # coloca aquí assets/fondo.png

# -----------------------
# UTIL: preprocesado para segmentación (reduce tamaño para speed)
# -----------------------
def _resize_for_seg(img_pil, max_side=512):
    w, h = img_pil.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        new_size = (int(w * scale), int(h * scale))
        small = img_pil.resize(new_size, Image.LANCZOS)
    else:
        small = img_pil.copy()
        scale = 1.0
    return small, scale

# -----------------------
# Método 1: MediaPipe Selfie Segmentation
# -----------------------
def _segment_mediapipe(pil_img):
    """Devuelve una máscara float32 (0..1) con la probabilidad de sujeto."""
    if not MP_AVAILABLE:
        raise RuntimeError("MediaPipe no disponible")
    # trabajar con tamaño reducido para velocidad
    small, scale = _resize_for_seg(pil_img, max_side=512)
    img_np = np.array(small.convert("RGB"))
    mp_selfie = mp.solutions.selfie_segmentation
    with mp_selfie.SelfieSegmentation(model_selection=1) as seg:
        results = seg.process(img_np)
        if results.segmentation_mask is None:
            return None, scale
        mask_small = results.segmentation_mask.astype(np.float32)  # valores 0..1
    # reescalar máscara al tamaño original
    mask_full = cv2.resize(mask_small, pil_img.size, interpolation=cv2.INTER_LINEAR)
    return mask_full, scale

# -----------------------
# Método 2: rembg (u2net) - devuelve máscara a partir de salida RGBA
# -----------------------
def _segment_rembg(pil_img):
    if not REMBG_AVAILABLE:
        raise RuntimeError("rembg no disponible")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    input_bytes = buf.getvalue()
    out_bytes = rembg_remove(input_bytes)  # bytes PNG RGBA con alfa
    out_img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
    alpha = np.array(out_img.split()[-1]).astype(np.float32) / 255.0  # 0..1
    return alpha, 1.0

# -----------------------
# Método 3: GrabCut mejorado (fallback)
# -----------------------
def _segment_grabcut(pil_img):
    # Convertir a BGR
    img_rgb = np.array(pil_img.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    H, W = img_bgr.shape[:2]

    # Intentar detectar cara para rect inicial (mejor primer paso)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30,30))
    if len(faces) > 0:
        # escoger la cara más grande
        faces = sorted(faces, key=lambda r: r[2]*r[3], reverse=True)
        x,y,w,h = faces[0]
        # ampliar rect para incluir hombros
        x0 = max(0, x - w//2)
        y0 = max(0, y - h//2)
        x1 = min(W-1, x + w + w//2)
        y1 = min(H-1, y + h + h//2)
        rect = (x0, y0, x1 - x0, y1 - y0)
    else:
        # fallback rect central
        margin_w = int(W * 0.12)
        margin_h = int(H * 0.10)
        rect = (margin_w, margin_h, W - 2*margin_w, H - 2*margin_h)

    mask_gc = np.zeros((H, W), np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(img_bgr, mask_gc, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    except Exception:
        # Si falla, devolver máscara que incluye todo
        return np.ones((H, W), dtype=np.float32), 1.0

    mask2 = np.where((mask_gc == 2) | (mask_gc == 0), 0, 1).astype('uint8')
    # suavizar bordes
    mask_float = cv2.GaussianBlur(mask2.astype(np.float32), (21,21), 0)
    # normalizar 0..1
    if mask_float.max() > 0:
        mask_float = mask_float / mask_float.max()
    return mask_float.astype(np.float32), 1.0

# -----------------------
# Función combi: intenta mediapipe -> rembg -> grabcut
# -----------------------
def aplicar_fondo_mejorado(pil_img, fondo_path="assets/fondo.png", method="auto"):
    """
    Aplica fondo usando el mejor método disponible.
    method in {"auto","mediapipe","rembg","grabcut"}
    """
    if not os.path.exists(fondo_path):
        st.warning("No se encontró el fondo (assets/fondo.png). Se devolverá la imagen original.")
        return pil_img.convert("RGB")

    # elegir método
    prefer = method.lower()
    mask = None
    used = None
    # MEDIAPIPE
    if prefer in ("auto", "mediapipe") and MP_AVAILABLE:
        try:
            mask, _ = _segment_mediapipe(pil_img)
            used = "mediapipe"
        except Exception:
            mask = None
    # REMBG
    if (mask is None) and (prefer in ("auto", "rembg") and REMBG_AVAILABLE):
        try:
            mask, _ = _segment_rembg(pil_img)
            used = "rembg"
        except Exception:
            mask = None
    # GRABCUT fallback
    if mask is None:
        try:
            mask, _ = _segment_grabcut(pil_img)
            used = "grabcut"
        except Exception:
            # como último recurso, máscara completa (no recorte)
            W, H = pil_img.size
            mask = np.ones((H, W), dtype=np.float32)
            used = "none"

    # Asegurar rango 0..1 y tamaño correcto
    if mask is None:
        W,H = pil_img.size
        mask = np.ones((H, W), dtype=np.float32)
    else:
        # si la máscara tiene distinto tamaño, reasignar
        if mask.shape != (pil_img.size[1], pil_img.size[0]):
            mask = cv2.resize(mask, pil_img.size, interpolation=cv2.INTER_LINEAR)

    # suavizamos y limitamos valores
    mask = np.clip(mask, 0.0, 1.0)
    # mejorar borde: aplicar un pequeño blur final y normalizar
    mask = cv2.GaussianBlur(mask, (15,15), 0)
    mask = np.clip(mask, 0.0, 1.0)

    # cargar fondo y redimensionar
    fondo = Image.open(fondo_path).convert("RGB").resize(pil_img.size, Image.LANCZOS)
    fg = np.array(pil_img.convert("RGB")).astype(np.float32)
    bg = np.array(fondo).astype(np.float32)

    alpha = mask[..., None]  # H x W x 1
    comp = (fg * alpha + bg * (1.0 - alpha)).astype(np.uint8)
    final = Image.fromarray(comp)

    # info para debugging
    st.info(f"Fondo aplicado con método: {used}")
    return final

# -----------------------
# Guardar foto
# -----------------------
def guardar_foto(imagen_pil, nombre_base="dragon"):
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_guardado = f"fotos_stand/{nombre_base}_{fecha}.png"
    imagen_pil.save(ruta_guardado, quality=95)
    return ruta_guardado

# -----------------------
# INTERFAZ STREAMLIT
# -----------------------
st.title("📸 Stand: Aplicar Fondo Mejorado")
st.markdown("Tómate una foto y la colocamos sobre `assets/fondo.png`. Opcional: instala `mediapipe` o `rembg` para mejores resultados.")

# Opción para forzar método (útil para pruebas)
metodo = st.selectbox("Método de segmentación (auto = intenta el mejor disponible)", ["auto", "mediapipe", "rembg", "grabcut"])

# Camera
img_file = st.camera_input("Toma tu foto aquí")

if img_file is not None:
    # abrir imagen
    image = Image.open(img_file)
    st.image(image, caption="Original", use_container_width=True)

    # Aplicar fondo mejorado
    with st.spinner("Aplicando fondo..."):
        try:
            final_img = aplicar_fondo_mejorado(image, fondo_path="assets/fondo.png", method=metodo)
            st.image(final_img, caption="Resultado con fondo aplicado", use_container_width=True)
            if st.button("Guardar foto final"):
                ruta = guardar_foto(final_img, nombre_base="dragon")
                st.success(f"Guardado en {ruta}")
        except Exception as e:
            st.error(f"Error aplicando fondo: {e}")
else:
    st.info("Activa tu cámara y tómate una foto para ver el resultado.")
