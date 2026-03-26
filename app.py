import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="SARDTECH Cloud", page_icon="🚀", layout="wide")

@st.cache_resource
def init_connection():
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

# --- 3. FUNCIONES DE DATOS ---
def cargar_backlog():
    res = supabase.table("backlog").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty and 'giro' in df.columns:
        df['Tier'] = df['giro'].apply(asignar_tier)
    return df

# --- 4. INTERFAZ Y ENCABEZADO ---
st.markdown('<div style="font-size:42px;font-weight:800;color:#0f3057;">🚀 SARDTECH CLOUD</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:20px;color:#008891;">Inteligencia Comercial en Tiempo Real</div><hr>', unsafe_allow_html=True)

st.sidebar.header("🎛️ Centro de Comando")
usuario = st.sidebar.selectbox("👤 Operador (SDR):", ["SDR 1 - Ana", "SDR 2 - Juan", "SDR 3 - Carlos", "Director"])

df_backlog = cargar_backlog()

tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🏃‍♂️ Operación", "🗄️ Backlog"])

# ==========================================
# PESTAÑA 1: ANALYTICS (DASHBOARD)
# ==========================================
with tab1:
    st.subheader("📈 Dashboard de Resultados en Tiempo Real")
    
    # Consultar la tabla de 'logs' en Supabase
    res_logs = supabase.table("logs").select("*").execute()
    df_logs = pd.DataFrame(res_logs.data)
    
    if df_logs.empty:
        st.info("📭 Aún no hay suficientes datos. ¡Ve a la pestaña 'Operación', registra un par de llamadas o demos y regresa aquí!")
    else:
        # Métricas Clave (KPIs)
        total_interacciones = len(df_logs)
        citas_sql = len(df_logs[df_logs['resultado'] == 'Cita Agendada (SQL)'])
        tasa_exito = (citas_sql / total_interacciones) * 100 if total_interacciones > 0 else 0
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Interacciones", total_interacciones, "Llamadas, demos, etc.")
        kpi2.metric("Citas Agendadas (SQL)", citas_sql, "Prospectos calificados")
        kpi3.metric("Tasa de Éxito", f"{tasa_exito:.1f}%")
        
        st.divider()
        
        # Gráficas visuales
        graf1, graf2 = st.columns(2)
        
        with graf1:
            st.markdown("##### 👥 Productividad por SDR")
            productividad = df_logs['autor_sdr'].value_counts()
            st.bar_chart(productividad)
            
        with graf2:
            st.markdown("##### 🎯 Estatus del Pipeline")
            estatus = df_logs['resultado'].value_counts()
            st.bar_chart(estatus)

# ==========================================
# PESTAÑA 2: OPERACIÓN (CAPTURA DE DATOS)
# ==========================================
with tab2:
    st.subheader("Registro de Actividad")
    es_nueva = st.checkbox("➕ Prospecto Nuevo")
    
    placeholder_mensaje = st.empty()
    
    with st.form("registro_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            lista_empresas = df_backlog['empresa'].tolist() if not df_backlog.empty else [""]
            
            empresa = st.text_input("Empresa") if es_nueva else st.selectbox("Seleccionar Empresa", lista_empresas, index=None, placeholder="Elige una empresa...")
            accion = st.selectbox("Acción", ["Llamada", "LinkedIn", "Demo", "Follow-up"], index=None, placeholder="Elige una acción...")
            resultado = st.selectbox("Estatus", ["Sin Respuesta", "Interés", "Cita Agendada (SQL)", "Rechazado"], index=None, placeholder="Elige el estatus...")
        
        with col_b:
            giro = st.selectbox("Giro", ["Fintech", "Banco", "Retail", "Otro"], index=None, placeholder="Elige el giro...") if es_nueva else ""
            notas = st.text_input("Notas")
            prox = st.date_input("Siguiente Contacto", value=datetime.date.today() + datetime.timedelta(days=2))
        
        guardar = st.form_submit_button("Guardar en Nube ☁️")
        
        if guardar:
            if not empresa or not accion or not resultado:
                st.warning("⚠️ Por favor selecciona una Empresa, Acción y Estatus antes de guardar.")
            else:
                giro_final = giro if es_nueva else (df_backlog[df_backlog['empresa']==empresa]['giro'].values[0] if not df_backlog.empty else "Otro")
                data = {
                    "empresa": empresa,
                    "accion": accion,
                    "resultado": resultado,
                    "notas": notas,
                    "proximo_contacto": str(prox),
                    "autor_sdr": usuario,
                    "giro": giro_final
                }
                
                # Guardar en logs
                supabase.table("logs").insert(data).execute()
                
                # Guardar en backlog si es nueva
                if es_nueva:
                    supabase.table("backlog").insert({"empresa": empresa, "giro": giro_final}).execute()
                
                placeholder_mensaje.success(f"✅ ¡El registro de {empresa} se guardó con éxito!")

# ==========================================
# PESTAÑA 3: BACKLOG (BASE MAESTRA)
# ==========================================
with tab3:
    st.subheader("Base Maestra")
    busqueda = st.text_input("🔍 Buscar empresa en el Backlog:")
    df_mostrar = df_backlog.copy()
    if busqueda and not df_mostrar.empty:
        df_mostrar = df_mostrar[df_mostrar['empresa'].astype(str).str.contains(busqueda, case=False, na=False)]
    st.dataframe(df_mostrar, use_container_width=True)
