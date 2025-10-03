import streamlit as st
import cv2
import numpy as np
from PIL import Image
import os
from datetime import datetime
import json
import glob
import base64
import shutil

# Configuración de la página para PWA
st.set_page_config(
    page_title="SOFA 2025 - Universidad Santo Tomas",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Crear directorio para almacenar fotos si no existe
os.makedirs("fotos_stand", exist_ok=True)

def verificar_foto(nombre):
    """Verificar si existe una foto para el nombre dado"""
    nombre_limpio = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).rstrip()
    patron = f"fotos_stand/{nombre_limpio}_*.jpg"
    fotos = glob.glob(patron)
    return len(fotos) > 0, fotos[0] if fotos else None

def obtener_ultima_foto(nombre):
    """Obtener la última foto tomada por el usuario"""
    nombre_limpio = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).rstrip()
    patron = f"fotos_stand/{nombre_limpio}_*.jpg"
    fotos = glob.glob(patron)
    if fotos:
        # Ordenar por fecha (el timestamp está en el nombre)
        fotos.sort(key=os.path.getmtime, reverse=True)
        return fotos[0]
    return None

def eliminar_foto(ruta_foto):
    """Eliminar una foto del sistema de archivos"""
    try:
        if os.path.exists(ruta_foto):
            os.remove(ruta_foto)
            return True
    except:
        return False
    return False

def crear_boton_descarga(foto_path, nombre):
    """Crear un botón de descarga para la foto"""
    try:
        with open(foto_path, "rb") as f:
            bytes_data = f.read()
        b64 = base64.b64encode(bytes_data).decode()
        nombre_archivo = f"foto_sofa_{nombre}.jpg"
        
        href = f'<a href="data:image/jpeg;base64,{b64}" download="{nombre_archivo}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-size: 16px; margin: 10px 0;">📸 Descargar tu foto</a>'
        return href
    except:
        return None

def main():
    # CSS para mejorar la apariencia PWA
    st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3rem;
    }
    .camera-container {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin: 20px 0;
    }
    .download-btn {
        background-color: #4CAF50;
        color: white;
        padding: 15px 30px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        border-radius: 10px;
        font-size: 18px;
        margin: 20px 0;
        border: none;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicializar variables de estado en session_state
    if 'foto_tomada' not in st.session_state:
        st.session_state.foto_tomada = False
    if 'foto_filename' not in st.session_state:
        st.session_state.foto_filename = None
    if 'camera_active' not in st.session_state:
        st.session_state.camera_active = False
    if 'foto_procesada' not in st.session_state:
        st.session_state.foto_procesada = False
    if 'mostrar_descarga' not in st.session_state:
        st.session_state.mostrar_descarga = False
    if 'formulario_completado' not in st.session_state:
        st.session_state.formulario_completado = False
    if 'nombre_usuario' not in st.session_state:
        st.session_state.nombre_usuario = ""
    
    # Página de descarga de foto (si ya completó el registro)
    if st.session_state.mostrar_descarga and st.session_state.nombre_usuario:
        mostrar_pagina_descarga()
        return
    
    # Página principal de registro
    mostrar_pagina_registro()

def mostrar_pagina_registro():
    """Mostrar la página principal de registro"""
    st.title("🎓 SOFA 2025 - Universidad Santo Tomas")
    st.subheader("¡Bienvenidos a nuestro stand!")
    
    # Paso 1: Nombre de la persona
    st.markdown("### Paso 1: Información personal")
    nombre = st.text_input("👤 ¿Cuál es tu nombre completo?")
    
    if nombre:
        # Paso 2: Interés en la universidad
        st.markdown("### Paso 2: Interés académico")
        interes_universidad = st.radio(
            "¿Tienes interés en ingresar a estudiar en nuestra universidad?",
            ["Sí, definitivamente", "Estoy considerando", "Tal vez", "No por el momento"]
        )
        
        if interes_universidad:
            # Paso 3: Preguntas adicionales
            st.markdown("### Paso 3: Más información")
            
            carrera_interes = st.selectbox(
                "¿Qué área te interesa más?",
                ["Ingenierías", "Ciencias de la Salud", "Ciencias Sociales", 
                 "Artes y Humanidades", "Administración y Negocios", "Todavía no sé"]
            )
            
            semestre_ingreso = st.selectbox(
                "¿Cuándo te gustaría empezar a estudiar?",
                ["2026-1", "2026-2", "2027-1", "2027-2 o después", "No estoy seguro"]
            )
            
            contacto = st.text_input("📧 ¿Email o teléfono para contactarte? (opcional)")
            
            # Paso 4: Tomar foto
            st.markdown("### Paso 4: ¡Foto en el stand!")
            st.info("Tómate una foto en nuestro stand para participar en sorteos y recordar tu visita")
            
            # Botón para activar/desactivar cámara
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📸 Activar cámara"):
                    st.session_state.camera_active = True
                    st.session_state.foto_procesada = False
            with col2:
                if st.button("❌ Desactivar cámara"):
                    st.session_state.camera_active = False
                    st.session_state.foto_tomada = False
                    st.session_state.foto_filename = None
                    st.session_state.foto_procesada = False
            
            # Mostrar cámara si está activa
            if st.session_state.camera_active and not st.session_state.foto_tomada:
                tomar_foto(nombre)
            
            # Mostrar estado de la foto
            if st.session_state.foto_tomada and st.session_state.foto_filename:
                st.success("✅ Foto tomada exitosamente!")
            
            # Botón para finalizar registro
            if st.button("✅ Finalizar registro"):
                tiene_foto = st.session_state.foto_tomada or verificar_foto(nombre)[0]
                
                if guardar_registro(nombre, interes_universidad, carrera_interes, 
                                  semestre_ingreso, contacto, tiene_foto):
                    st.session_state.nombre_usuario = nombre
                    st.session_state.mostrar_descarga = True
                    st.rerun()

def mostrar_pagina_descarga():
    """Mostrar la página de descarga de foto"""
    st.title("🎓 ¡Gracias por registrarte!")
    st.subheader("Completa nuestro formulario y descarga tu foto de recuerdo")
    
    nombre = st.session_state.nombre_usuario
    foto_path = obtener_ultima_foto(nombre)
    
    if foto_path:
        # Mostrar la foto
        try:
            image = Image.open(foto_path)
            st.image(image, caption="Tu foto en el stand del SOFA 2024", use_container_width=True)
        except:
            st.error("No se pudo cargar la foto")
            foto_path = None
    else:
        st.warning("No se encontró la foto tomada anteriormente")
    
    # Formulario de Google Docs (embed)
    st.markdown("### 📝 Formulario de contacto")
    st.info("Por favor, completa este breve formulario para poder contactarte y enviarte más información")
    
    # Aquí puedes reemplazar con tu propio enlace de Google Forms
    google_form_url = "https://docs.google.com/forms/d/e/1FAIpQLSdGnTlwWkACUOiH0AabH3Mqr7JkNVMqB5YvVryqd2uExEzmiQ/viewform?usp=header"
    
    # Embed del formulario de Google
    st.components.v1.iframe(google_form_url, height=600, scrolling=True)
    
    # Checkbox para confirmar que completó el formulario
    formulario_completado = st.checkbox("✅ He completado el formulario anterior")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Botón para descargar foto después de completar formulario
        if formulario_completado and foto_path:
            st.markdown("### 📸 Descarga tu foto")
            boton_descarga = crear_boton_descarga(foto_path, nombre)
            if boton_descarga:
                st.markdown(boton_descarga, unsafe_allow_html=True)
                
                # Botón para confirmar descarga y eliminar foto
                if st.button("🗑️ Eliminar foto después de descargar"):
                    if eliminar_foto(foto_path):
                        st.success("✅ Foto eliminada del sistema. ¡Gracias!")
                        st.session_state.mostrar_descarga = False
                        st.session_state.formulario_completado = False
                        st.session_state.nombre_usuario = ""
                        st.session_state.foto_tomada = False
                        st.session_state.foto_filename = None
                        st.rerun()
                    else:
                        st.error("❌ Error al eliminar la foto")
    
    with col2:
        # Botón para dar otra respuesta
        if st.button("🔄 Dar otra respuesta"):
            # Eliminar foto actual si existe
            if foto_path:
                eliminar_foto(foto_path)
            
            # Resetear todo el estado
            st.session_state.mostrar_descarga = False
            st.session_state.formulario_completado = False
            st.session_state.nombre_usuario = ""
            st.session_state.foto_tomada = False
            st.session_state.foto_filename = None
            st.session_state.camera_active = False
            st.session_state.foto_procesada = False
            st.rerun()

def tomar_foto(nombre):
    """Función para capturar foto desde la cámara"""
    st.markdown('<div class="camera-container">', unsafe_allow_html=True)
    st.write("📷 Cámara activada - Sonríe para la foto!")
    
    img_file_buffer = st.camera_input("Toma tu foto", key="camera_widget")
    
    if img_file_buffer is not None and not st.session_state.foto_procesada:
        try:
            st.session_state.foto_procesada = True
            image = Image.open(img_file_buffer)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_limpio = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).rstrip()
            foto_filename = f"fotos_stand/{nombre_limpio}_{timestamp}.jpg"
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            image.save(foto_filename, quality=95)
            
            if os.path.exists(foto_filename):
                st.session_state.foto_tomada = True
                st.session_state.foto_filename = foto_filename
                st.success("¡Foto guardada exitosamente!")
                st.image(image, caption="Tu foto en el stand", use_container_width=True)
            else:
                st.error("❌ Error: No se pudo guardar la foto")
                st.session_state.foto_procesada = False
                
        except Exception as e:
            st.error(f"❌ Error al procesar la foto: {e}")
            st.session_state.foto_procesada = False
    
    st.markdown('</div>', unsafe_allow_html=True)

def guardar_registro(nombre, interes, carrera, semestre, contacto, tiene_foto):
    """Función para guardar los datos del registro"""
    registro = {
        "nombre": nombre,
        "interes_universidad": interes,
        "carrera_interes": carrera,
        "semestre_ingreso": semestre,
        "contacto": contacto if contacto else "No proporcionado",
        "tiene_foto": "Sí" if tiene_foto else "No",
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    datos = []
    archivo_json = "registros_sofa.json"
    
    # Crear archivo si no existe
    if not os.path.exists(archivo_json):
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    # Cargar datos existentes
    if os.path.exists(archivo_json):
        try:
            with open(archivo_json, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
                if contenido:
                    datos = json.loads(contenido)
                    # Si el archivo tenía un solo objeto (diccionario), convertirlo a lista
                    if isinstance(datos, dict):
                        datos = [datos]
                else:
                    datos = []
        except json.JSONDecodeError as e:
            st.error(f"Error leyendo el archivo JSON: {e}")
            datos = []
    
    # Agregar nuevo registro
    datos.append(registro)
    
    # Guardar datos actualizados
    try:
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        st.success("✅ Registro guardado correctamente en el archivo JSON")
    except Exception as e:
        st.error(f"❌ Error guardando en archivo JSON: {e}")
    
    # Mostrar resumen
    st.balloons()
    st.markdown("### 📋 Resumen de tu registro:")
    st.write(f"**Nombre:** {registro['nombre']}")
    st.write(f"**Interés en universidad:** {registro['interes_universidad']}")
    st.write(f"**Área de interés:** {registro['carrera_interes']}")
    st.write(f"**Semestre de ingreso:** {registro['semestre_ingreso']}")
    st.write(f"**Contacto:** {registro['contacto']}")
    st.write(f"**Foto tomada:** {registro['tiene_foto']}")
    st.write(f"**Fecha de registro:** {registro['fecha_registro']}")
    
    # Mostrar estadísticas
    st.markdown("---")
    st.info(f"📊 Total de registros guardados: {len(datos)}")
    
    # Botón para ir a la descarga
    st.markdown("---")
    st.success("🎉 ¡Registro completado! Ahora puedes descargar tu foto de recuerdo.")
    
    return True

if __name__ == "__main__":
    main()
