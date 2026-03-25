import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import datetime
import re

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="SARDTECH Cloud", page_icon="🚀", layout="wide")

# Conexión Segura a Supabase (USANDO SECRETOS DE STREAMLIT)
@st.cache_resource
def init_connection():
    # En lugar de escribir la clave aquí, Streamlit la leerá de su bóveda segura
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    return create_client(supabase_url, supabase_key)

supabase = init_connection()

# --- 2. LÓGICA DE NEGOCIO ---
def asignar_tier(giro):
    g = str(giro).lower()
    if 'banco' in g or 'aseguradora' in g: return 'Tier 1 - Ballena'
    if 'caja' in g or 'sofom' in g or 'financiera' in g or 'fintech' in g or 'retail' in g: return 'Tier 2 - Delfín'
    return 'Tier 3 - Pez'

def validar_email(email):
    if not email: return True
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

# --- 3. FUNCIONES DE DATOS (MÓDULO CLOUD) ---
def cargar_backlog():
    res = supabase.table("backlog").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['Tier'] = df['giro'].apply(asignar_tier)
    return df

def cargar_logs():
    res = supabase.table("logs").select("*").execute()
    return pd.DataFrame(res.data)

# --- 4. INTERFAZ (VISTA) ---
st.markdown('<div style="font-size:42px;font-weight:800;color:#0f3057;">🚀 SARDTECH CLOUD</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:20px;color:#008891;">Inteligencia Comercial en Tiempo Real</div><hr>', unsafe_allow_html=True)

# Sidebar de Identidad
st.sidebar.header("🎛️ Centro de Comando")
usuario = st.sidebar.selectbox("👤 Operador (SDR):", ["SDR 1 - Ana", "SDR 2 - Juan", "SDR 3 - Carlos", "Director"])

# Carga de datos
df_backlog = cargar_backlog()
df_logs = cargar_logs()

tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🏃‍♂️ Operación", "🗄️ Backlog"])

with tab2:
    st.subheader("Registro de Actividad")
    es_nueva = st.checkbox("➕ Prospecto Nuevo")
    
    with st.form("registro_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            empresa = st.text_input("Empresa") if es_nueva else st.selectbox("Seleccionar Empresa", df_backlog['empresa'].tolist() if not df_backlog.empty else [""])
            accion = st.selectbox("Acción", ["Llamada", "LinkedIn", "Demo", "Follow-up"])
            resultado = st.selectbox("Estatus", ["Sin Respuesta", "Interés", "Cita Agendada (SQL)", "Rechazado"])
        with col_b:
            giro = st.selectbox("Giro", ["Fintech", "Banco", "Retail", "Otro"]) if es_nueva else ""
            notas = st.text_input("Notas")
            prox = st.date_input("Siguiente Contacto", value=datetime.date.today() + datetime.timedelta(days=2))
        
        if st.form_submit_button("Guardar en Nube ☁️"):
            data = {
                "empresa": empresa,
                "accion": accion,
                "resultado": resultado,
                "notas": notas,
                "proximo_contacto": str(prox),
                "autor_sdr": usuario,
                "giro": giro if es_nueva else (df_backlog[df_backlog['empresa']==empresa]['giro'].values[0] if not df_backlog.empty else "Otro")
            }
            # Insertar en Logs
            supabase.table("logs").insert(data).execute()
            # Si es nueva, insertar en Backlog también
            if es_nueva:
                supabase.table("backlog").insert({"empresa": empresa, "giro": giro}).execute()
            
            st.success("¡Datos sincronizados con Supabase!")
            st.rerun()

with tab3:
    st.subheader("Base Maestra")
    st.dataframe(df_backlog, use_container_width=True)
