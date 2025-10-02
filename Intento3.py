import streamlit as st
import json
import os
from datetime import datetime
from io import BytesIO
from PIL import Image

# --------------------------
# Config y archivo de datos
# --------------------------
DATA_FILE = "DATOS USUARIOS.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(new_entry):
    data = load_data()
    data.append(new_entry)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

st.set_page_config(page_title="Registro USTA", page_icon="🐉🤖", layout="centered")

# --------------------------
# Estados en session_state
# --------------------------
if "form_enviado" not in st.session_state:
    st.session_state.form_enviado = False
if "abrir_camara" not in st.session_state:
    st.session_state.abrir_camara = False
if "foto_bytes" not in st.session_state:
    st.session_state.foto_bytes = None
if "foto_descargada" not in st.session_state:
    st.session_state.foto_descargada = False
if "interes_uni_actual" not in st.session_state:  
    st.session_state.interes_uni_actual = "Sí"

# --------------------------
# FORMULARIO 
# --------------------------
st.title("🐉🤖 Registro con el Dragón y Pepper - USTA")
st.markdown("Llena tus datos para que la universidad pueda contactarte.")


interes_uni = st.radio("¿Quieres ingresar a la Universidad Santo Tomás?", ["Sí", "No"])

with st.form("form_registro", clear_on_submit=True):
    nombre = st.text_input("Nombre completo")
    celular = st.text_input("Número de celular")
    correo = st.text_input("Correo electrónico")

    carrera = None
    periodo = None

    
    if interes_uni == "Sí":
        carrera = st.selectbox(
            "¿Qué ingeniería te gustaría estudiar?",
            ["Ingeniería Electrónica", "Ingeniería de Sistemas", "Ingeniería Mecánica", "Ingeniería Industrial"]
        )

        periodo = st.selectbox(
            "Periodo académico de interés",
            ["2025-2", "2026-1", "2026-2", "2027-1", "2027-2"]
        )

    submitted = st.form_submit_button("Enviar datos")
    if submitted:
        if nombre and celular and correo:
            new_entry = {
                "nombre": nombre,
                "celular": celular,
                "correo": correo,
                "interes_uni": interes_uni,
                "carrera": carrera,
                "periodo": periodo,
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_data(new_entry)
            st.session_state.form_enviado = True
            st.success("✅ Tus datos han sido guardados. Ahora puedes tomarte la foto 📸.")
        else:
            st.error("⚠️ Por favor llena los campos obligatorios (nombre, celular, correo).")


st.divider()

# --------------------------
# BLOQUE DE FOTO 
# --------------------------
if st.session_state.form_enviado:
    st.subheader("📸 Foto con Pepper y el Dragón")

    # Si la foto ya fue descargada, reiniciar todo
    if st.session_state.foto_descargada:
        st.session_state.foto_bytes = None
        st.session_state.abrir_camara = False
        st.session_state.foto_descargada = False
        st.success("🎉 ¡Proceso completado! Puedes llenar otro formulario si lo deseas.")
        st.balloons()
    
    elif not st.session_state.abrir_camara and st.session_state.foto_bytes is None:
        if st.button("Tomar foto"):
            st.session_state.abrir_camara = True
            st.rerun()

    elif st.session_state.abrir_camara:
        camara = st.camera_input("Haz clic para tomar tu foto")
        if camara is not None and st.session_state.foto_bytes is None:
            try:
                foto_b = camara.getvalue()
            except Exception:
                foto_b = camara.read()
            st.session_state.foto_bytes = foto_b
            st.session_state.abrir_camara = False
            st.rerun()

    elif st.session_state.foto_bytes is not None:
        img = Image.open(BytesIO(st.session_state.foto_bytes))
        st.image(img, caption="Tu foto con Pepper y el Dragón", use_container_width=True)

        buf = BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="⬇️ Descargar foto",
                data=png_bytes,
                file_name=f"Mi Foto Con PEPER y DRAGON{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png",
                use_container_width=True
            )
        
        with col2:
            if st.button("✅ Finalizar", use_container_width=True):
                st.session_state.foto_descargada = True
                st.rerun()
        
        st.info("💡 **Recomendación:** Usa el botón 'Descargar y Finalizar' para asegurar que se cierre la vista de la foto.")
