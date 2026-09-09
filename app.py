import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from data_loader import load_po_data, load_philips_data, load_config_data, DATA_DIR, DEFAULT_ODOO_DB, DEFAULT_ODOO_USER, DEFAULT_ODOO_PASS

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ---------------------------------------------------------
st.set_page_config(
    page_title="MONSTRUO MÁSTER: Control Total de Compras & Proyectos",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main .block-container { padding-top: 1.2rem; max-width: 98% !important; }
    .kpi-card {
        background: #ffffff; padding: 14px 18px; border-radius: 8px;
        border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .kpi-title { font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 1.45rem; color: #0f172a; font-weight: 700; margin-top: 4px; }
    .alert-box-red {
        background-color: #fef2f2; border-left: 5px solid #ef4444;
        padding: 12px 16px; border-radius: 6px; margin-bottom: 12px; color: #991b1b;
    }
    .alert-box-yellow {
        background-color: #fffbeb; border-left: 5px solid #f59e0b;
        padding: 12px 16px; border-radius: 6px; margin-bottom: 12px; color: #92400e;
    }
    .admin-badge {
        background-color: #dcfce7; color: #166534; padding: 6px 12px;
        border-radius: 6px; font-weight: bold; font-size: 0.85rem;
        display: inline-block; margin-bottom: 10px; text-align: center; width: 100%;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 18px; border-radius: 6px; background-color: #f1f5f9; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #0284c7 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CONSTANTES DE ADMINISTRACIÓN Y ARCHIVOS
# ---------------------------------------------------------
ADMIN_USER = "admin"
ADMIN_PASSWORD = "compras2026*"
METADATA_FILE = os.path.join(DATA_DIR, "last_update.txt")

def get_safe_len(df):
    return len(df) if df is not None and not df.empty else 0

def get_safe_nunique(df, col):
    if df is not None and not df.empty and col in df.columns:
        return df[col].nunique()
    return 0

def save_uploaded_file(uploaded_file, target_filename):
    path = os.path.join(DATA_DIR, target_filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    now_str = datetime.now().strftime("%d/%m/%Y a las %H:%M hrs")
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(now_str)
        
    st.cache_data.clear()

@st.cache_data(ttl=60)
def cargar_todo(odoo_db=None, odoo_user=None, odoo_pass=None):
    return load_po_data(odoo_db, odoo_user, odoo_pass), load_philips_data(), load_config_data()

# ---------------------------------------------------------
# BARRA LATERAL (CENTRO DE CONTROL)
# ---------------------------------------------------------
st.sidebar.title("🎛️ Centro de Control")

# Session state de Odoo
if 'odoo_db' not in st.session_state: st.session_state['odoo_db'] = DEFAULT_ODOO_DB
if 'odoo_user' not in st.session_state: st.session_state['odoo_user'] = DEFAULT_ODOO_USER
if 'odoo_pass' not in st.session_state: st.session_state['odoo_pass'] = DEFAULT_ODOO_PASS

# 1. BOTÓN DE SINCRONIZACIÓN EN VIVO DESDE LA NUBE
if st.sidebar.button("🔄 Sincronizar Todo en Vivo desde la Nube", type="primary", use_container_width=True):
    st.cache_data.clear()
    now_str = datetime.now().strftime("%d/%m/%Y a las %H:%M hrs")
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        f.write(now_str + " (Sincronizado en Vivo desde Odoo API + Google Sheets)")
    st.sidebar.success("✅ Nube Sincronizada en Vivo")
    st.rerun()

st.sidebar.markdown("---")

# 2. ACCESO ADMINISTRADOR
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

if not st.session_state['is_admin']:
    with st.sidebar.popover("🔐 Acceso Administrador", use_container_width=True):
        st.subheader("Iniciar Sesión de Admin")
        user_input = st.text_input("Usuario", key="admin_user_login")
        pass_input = st.text_input("Contraseña", type="password", key="admin_pass_login")
        
        if st.button("Ingresar", type="primary", use_container_width=True):
            if user_input == ADMIN_USER and pass_input == ADMIN_PASSWORD:
                st.session_state['is_admin'] = True
                st.success("Sesión iniciada")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
else:
    st.sidebar.markdown('<div class="admin-badge">🔑 MODALIDAD ADMIN ACTIVA</div>', unsafe_allow_html=True)
    
    with st.sidebar.expander("🔌 Conexión API Odoo (Credenciales)", expanded=False):
        st.caption("Credenciales preconfiguradas:")
        db_in = st.text_input("Base de Datos", value=st.session_state['odoo_db'])
        user_in = st.text_input("Usuario / Correo", value=st.session_state['odoo_user'])
        pass_in = st.text_input("Contraseña / API Key", type="password", value=st.session_state['odoo_pass'])
        
        if st.button("Guardar Credenciales", use_container_width=True):
            st.session_state['odoo_db'] = db_in
            st.session_state['odoo_user'] = user_in
            st.session_state['odoo_pass'] = pass_in
            st.cache_data.clear()
            st.success("✅ Datos guardados")
            st.rerun()

    with st.sidebar.expander("📤 Cargar / Publicar Reportes Excel Manuales", expanded=False):
        st.caption("Respaldo manual de archivos Excel:")
        file_po = st.file_uploader("1. Compras Generales (purchase.order)", type=["xlsx", "xls"], key="up_po")
        if file_po and st.button("💾 Publicar Compras", type="primary", use_container_width=True):
            save_uploaded_file(file_po, "Orden de compra (purchase.order).xlsx")
            st.success("✅ Compras actualizado")
            st.rerun()
            
        file_phil = st.file_uploader("2. Seguimiento Philips", type=["xlsx", "xls"], key="up_phil")
        if file_phil and st.button("💾 Publicar Philips", type="primary", use_container_width=True):
            save_uploaded_file(file_phil, "Seguimiento Philips _ MPC - Ordenes de compra_2.xlsx")
            st.success("✅ Philips actualizado")
            st.rerun()

        file_cfg = st.file_uploader("3. Configuraciones 2026", type=["xlsx", "xls"], key="up_cfg")
        if file_cfg and st.button("💾 Publicar Configuraciones", type="primary", use_container_width=True):
            save_uploaded_file(file_cfg, "PENDIENTES _ CONFIGURACIONES 2026_2.xlsx")
            st.success("✅ Configuraciones actualizado")
            st.rerun()

    if st.sidebar.button("Salir de Modo Admin", use_container_width=True):
        st.session_state['is_admin'] = False
        st.rerun()

st.sidebar.markdown("---")

if os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        last_update = f.read()
    st.sidebar.info(f"🕒 **Última Actualización:**\n{last_update}")

# Cargar Datos en Vivo
df_po, df_philips, df_config = cargar_todo(st.session_state['odoo_db'], st.session_state['odoo_user'], st.session_state['odoo_pass'])

# ---------------------------------------------------------
# FILTROS DE SEGMENTACIÓN (PÚBLICOS)
# ---------------------------------------------------------
st.sidebar.subheader("🔍 Filtros de Segmentación")

if not df_po.empty:
    tipo_prov_opts = list(df_po['Tipo_Proveedor'].unique()) if 'Tipo_Proveedor' in df_po.columns else []
    comprador_opts = list(df_po['Comprador'].unique()) if 'Comprador' in df_po.columns else []

    tipo_prov_sel = st.sidebar.multiselect("Origen de Proveedor", options=tipo_prov_opts, default=tipo_prov_opts)
    comprador_sel = st.sidebar.multiselect("Comprador", options=comprador_opts, default=comprador_opts)

    df_po_filtered = df_po[
        (df_po['Tipo_Proveedor'].isin(tipo_prov_sel)) &
        (df_po['Comprador'].isin(comprador_sel))
    ]
else:
    df_po_filtered = df_po

# ---------------------------------------------------------
# HEADER Y METRICAS CONSOLIDADAS GLOBAL
# ---------------------------------------------------------
st.title("🏢 MONSTRUO DE CONTROL TOTAL: Compras, Importaciones & Proyectos")
st.caption("Consola unificada con sincronización automática de Odoo y Google Sheets.")

if not df_po_filtered.empty and 'Referencia de la orden' in df_po_filtered.columns:
    ordenes_unicas = df_po_filtered.groupby('Referencia de la orden').first().reset_index()
    monto_total = ordenes_unicas['Total_MXN'].sum() if 'Total_MXN' in ordenes_unicas.columns else 0
    vencidas_cnt = len(ordenes_unicas[ordenes_unicas['Semaforo'] == '🔴 Vencido']) if 'Semaforo' in ordenes_unicas.columns else 0
    
    imp_unicas = ordenes_unicas[ordenes_unicas['Tipo_Proveedor'].str.contains("Importación", na=False)]
    imp_cnt = len(imp_unicas)
    imp_criticas = len(imp_unicas[imp_unicas['Semaforo_Importacion'].str.contains("CRÍTICO", na=False)]) if 'Semaforo_Importacion' in imp_unicas.columns else 0
else:
    ordenes_unicas = pd.DataFrame()
    imp_unicas = pd.DataFrame()
    monto_total = 0
    vencidas_cnt = 0
    imp_cnt = 0
    imp_criticas = 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(f'<div class="kpi-card"><div class="kpi-title">Gasto Total Compras</div><div class="kpi-value">${monto_total:,.0f} <span style="font-size:0.75rem;">MXN</span></div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-card"><div class="kpi-title">🔴 Entregas Vencidas</div><div class="kpi-value" style="color:#dc2626;">{vencidas_cnt:,}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-card"><div class="kpi-title">🚢 OCs Importación</div><div class="kpi-value" style="color:#0284c7;">{imp_cnt:,}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-card"><div class="kpi-title">🚨 Import. Críticas</div><div class="kpi-value" style="color:#b91c1c;">{imp_criticas:,}</div></div>', unsafe_allow_html=True)
k5.markdown(f'<div class="kpi-card"><div class="kpi-title">Proyectos Activos</div><div class="kpi-value">{get_safe_nunique(df_config, "Proyecto_Nombre")}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

COLS_PO_SHOW = ['Referencia de la orden', 'Empresa', 'Estado', 'Semaforo', 'Tipo_Proveedor', 'Proveedor', 'Producto', 'Cantidad', 'Moneda', 'Total', 'Total_MXN', 'Comprador', 'Fecha_Limite']

def render_detalle_por_empresa(df_base, prefix_key="gen"):
    if df_base.empty:
        st.info("Sin registros disponibles.")
        return

    empresas_list = list(df_base['Empresa'].unique()) if 'Empresa' in df_base.columns else []
    
    st.markdown("### 🏢 Selecciona una Empresa para ver el Detalle de sus Órdenes de Compra:")
    
    tab_titles = ["🏢 TODAS LAS EMPRESAS (" + str(df_base['Referencia de la orden'].nunique()) + " OCs)"] + [f"🏢 {emp} ({df_base[df_base['Empresa']==emp]['Referencia de la orden'].nunique()} OCs)" for emp in empresas_list]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        st.markdown("#### 📋 Detalle Consolidado de Todas las Empresas")
        c_f1, c_f2 = st.columns([2, 1])
        with c_f1:
            q_search = st.text_input("🔍 Buscar por OC, Proveedor o Producto:", "", key=f"{prefix_key}_search_all")
        with c_f2:
            sem_filter = st.selectbox("Filtrar por Semáforo:", ["TODOS"] + list(df_base['Semaforo'].unique()), key=f"{prefix_key}_sem_all")

        df_view = df_base.copy()
        if q_search:
            cond = df_view['Referencia de la orden'].astype(str).str.contains(q_search, case=False, na=False) | \
                   df_view['Proveedor'].astype(str).str.contains(q_search, case=False, na=False) | \
                   df_view['Producto'].astype(str).str.contains(q_search, case=False, na=False)
            df_view = df_view[cond]
        if sem_filter != "TODOS":
            df_view = df_view[df_view['Semaforo'] == sem_filter]

        cols_curr = [c for c in COLS_PO_SHOW if c in df_view.columns]
        st.dataframe(df_view[cols_curr], use_container_width=True)

    for idx, emp_name in enumerate(empresas_list):
        with tabs[idx + 1]:
            st.markdown(f"#### 📋 Detalle de Órdenes de Compra de: **{emp_name}**")
            df_emp = df_base[df_base['Empresa'] == emp_name].copy()

            m_emp = df_emp['Total_MXN'].sum()
            cnt_emp = df_emp['Referencia de la orden'].nunique()
            venc_emp = len(df_emp[df_emp['Semaforo'] == '🔴 Vencido'])
            imp_emp = len(df_emp[df_emp['Tipo_Proveedor'].str.contains('Importación', na=False)])

            e1, e2, e3, e4 = st.columns(4)
            e1.markdown(f'<div class="kpi-card"><div class="kpi-title">Monto Total ({emp_name})</div><div class="kpi-value">${m_emp:,.0f} MXN</div></div>', unsafe_allow_html=True)
            e2.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Órdenes</div><div class="kpi-value">{cnt_emp:,}</div></div>', unsafe_allow_html=True)
            e3.markdown(f'<div class="kpi-card"><div class="kpi-title">🔴 Órdenes Vencidas</div><div class="kpi-value" style="color:#dc2626;">{venc_emp:,}</div></div>', unsafe_allow_html=True)
            e4.markdown(f'<div class="kpi-card"><div class="kpi-title">🚢 Importación</div><div class="kpi-value" style="color:#0284c7;">{imp_emp:,}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            cf1, cf2 = st.columns([2, 1])
            with cf1:
                q_emp = st.text_input(f"🔍 Buscar en {emp_name}:", "", key=f"{prefix_key}_search_{idx}")
            with cf2:
                s_emp = st.selectbox(f"Semáforo en {emp_name}:", ["TODOS"] + list(df_emp['Semaforo'].unique()), key=f"{prefix_key}_sem_{idx}")

            if q_emp:
                cond_e = df_emp['Referencia de la orden'].astype(str).str.contains(q_emp, case=False, na=False) | \
                         df_emp['Proveedor'].astype(str).str.contains(q_emp, case=False, na=False) | \
                         df_emp['Producto'].astype(str).str.contains(q_emp, case=False, na=False)
                df_emp = df_emp[cond_e]
            if s_emp != "TODOS":
                df_emp = df_emp[df_emp['Semaforo'] == s_emp]

            cols_curr = [c for c in COLS_PO_SHOW if c in df_emp.columns]
            st.dataframe(df_emp[cols_curr], use_container_width=True)

# ---------------------------------------------------------
# PESTAÑAS PÚBLICAS DEL DASHBOARD
# ---------------------------------------------------------
t1, t2, t3, t4, t5 = st.tabs([
    "📊 1. Control General por Empresas (Odoo POs)",
    "🚢 2. Control de Importaciones & Aduanas",
    "💙 3. Tracking Especial Philips",
    "⚙️ 4. Pendientes & Configuraciones 2026",
    "🔀 5. Matriz Cruzada & Auditoría Unificada"
])

# TAB 1: ODOO POS
with t1:
    if df_po_filtered.empty:
        st.info("💡 Sin datos de Compras. Presiona 'Sincronizar Todo en Vivo' en el menú lateral.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Semáforo General de Entregas")
            if not ordenes_unicas.empty and 'Semaforo' in ordenes_unicas.columns:
                df_sem = ordenes_unicas['Semaforo'].value_counts().reset_index()
                df_sem.columns = ['Semaforo', 'Cantidad']
                fig_sem = px.pie(df_sem, names='Semaforo', values='Cantidad', hole=0.45, color='Semaforo',
                                 color_discrete_map={"🔴 Vencido": "#ef4444", "🟡 Próximo a Vencer (<=7 días)": "#f59e0b", "🟢 A Tiempo": "#10b981", "⚪ Sin Fecha": "#94a3b8", "⚪ Inactivo / Creado": "#cbd5e1"})
                st.plotly_chart(fig_sem, use_container_width=True)
        with c2:
            st.subheader("Top 10 Proveedores por Monto de Compra")
            if 'Proveedor' in df_po_filtered.columns and 'Total_MXN' in df_po_filtered.columns:
                df_prov = df_po_filtered.groupby('Proveedor')['Total_MXN'].sum().reset_index().sort_values('Total_MXN', ascending=False).head(10)
                fig_prov = px.bar(df_prov, x='Total_MXN', y='Proveedor', orientation='h', text_auto='.2s', color='Total_MXN', color_continuous_scale='Blues')
                st.plotly_chart(fig_prov, use_container_width=True)

        st.markdown("---")
        render_detalle_por_empresa(df_po_filtered, prefix_key="tab1")

# TAB 2: IMPORTACIONES
with t2:
    st.subheader("🚢 Control Especial de Importaciones, Aduanas & Alertas de Acción")
    if imp_unicas.empty:
        st.info("No hay órdenes de compra de importación seleccionadas.")
    else:
        st.markdown("### 📢 Avisos de Acción Inmediata para Compras")
        criticas_df = imp_unicas[imp_unicas['Semaforo_Importacion'].str.contains("CRÍTICO", na=False)]
        urgentes_df = imp_unicas[imp_unicas['Semaforo_Importacion'].str.contains("URGENTE", na=False)]
        
        if not criticas_df.empty:
            st.markdown(f"""
                <div class="alert-box-red">
                    <strong>🚨 ALERTA CRÍTICA DE ADUANA / DOCUMENTACIÓN ({len(criticas_df)} Órdenes Vencidas):</strong><br>
                    Existen órdenes de compra internacionales cuya fecha límite expiró. 
                    <strong>Acciones requeridas:</strong> Contactar al fabricante/agente aduanal, solicitar estatus del despacho aduanal y verificar la entrega de Pedimentos y Cartas de Fabricación.
                </div>
            """, unsafe_allow_html=True)

        if not urgentes_df.empty:
            st.markdown(f"""
                <div class="alert-box-yellow">
                    <strong>⚠️ AVISO DE VENCIMIENTO PRÓXIMO ({len(urgentes_df)} Órdenes por vencer en ≤7 días):</strong><br>
                    <strong>Acciones requeridas:</strong> Exigir al proveedor la Factura Ciega, Confirmación de Embarque y coordinar el ingreso a Almacén 11.
                </div>
            """, unsafe_allow_html=True)

        ci1, ci2 = st.columns(2)
        with ci1:
            st.subheader("Semáforo de Importaciones")
            df_imp_sem = imp_unicas['Semaforo_Importacion'].value_counts().reset_index()
            df_imp_sem.columns = ['Estatus_Import', 'Cantidad']
            map_colors_imp = {
                "🚨 CRÍTICO: Vencido (Atraso Aduana/Doc)": "#dc2626",
                "⚠️ URGENTE: Vence ≤7 días (Solicitar Pedimento)": "#f59e0b",
                "🟡 PRECAUCIÓN: Próximo 8-15 días (Validar Doc)": "#eab308",
                "🟢 EN TIEMPO (>15 días)": "#16a34a",
                "⚪ Inactivo / Creado": "#cbd5e1"
            }
            fig_imp_sem = px.bar(df_imp_sem, x='Estatus_Import', y='Cantidad', color='Estatus_Import',
                                 color_discrete_map=map_colors_imp, text_auto=True)
            fig_imp_sem.update_layout(showlegend=False, xaxis_title="", yaxis_title="Órdenes")
            st.plotly_chart(fig_imp_sem, use_container_width=True)

        with ci2:
            st.subheader("Gasto por Proveedor Extranjero")
            df_prov_imp = imp_unicas.groupby('Proveedor')['Total_MXN'].sum().reset_index().sort_values('Total_MXN', ascending=True)
            fig_prov_imp = px.bar(df_prov_imp, x='Total_MXN', y='Proveedor', orientation='h', text_auto='.2s', color='Total_MXN', color_continuous_scale='Reds')
            st.plotly_chart(fig_prov_imp, use_container_width=True)

        st.markdown("---")
        df_imp_all = df_po_filtered[df_po_filtered['Tipo_Proveedor'].str.contains("Importación", na=False)]
        render_detalle_por_empresa(df_imp_all, prefix_key="tab2_imp")

# TAB 3: PHILIPS
with t3:
    st.subheader("💙 Control y Seguimiento de Órdenes Philips")
    if df_philips.empty:
        st.info("💡 Sin datos de Philips.")
    else:
        p1, p2 = st.columns(2)
        with p1:
            st.subheader("Estatus de Órdenes Philips")
            df_p_est = df_philips['Estatus'].value_counts().reset_index()
            df_p_est.columns = ['Estatus', 'Cantidad']
            fig_p = px.bar(df_p_est, x='Estatus', y='Cantidad', color='Estatus', text_auto=True)
            st.plotly_chart(fig_p, use_container_width=True)
        with p2:
            st.subheader("Registros por Hoja / Sección")
            df_p_hoja = df_philips['Origen_Hoja'].value_counts().reset_index() if 'Origen_Hoja' in df_philips.columns else pd.DataFrame()
            if not df_p_hoja.empty:
                df_p_hoja.columns = ['Hoja', 'Cantidad']
                fig_p2 = px.pie(df_p_hoja, names='Hoja', values='Cantidad', hole=0.4)
                st.plotly_chart(fig_p2, use_container_width=True)

        st.subheader("Detalle Completo de Registros Philips")
        st.dataframe(df_philips, use_container_width=True)

# TAB 4: CONFIGURACIONES
with t4:
    st.subheader("⚙️ Pendientes & Configuraciones de Proyectos 2026")
    if df_config.empty:
        st.info("💡 Sin datos de Configuraciones.")
    else:
        cfg1, cfg2 = st.columns(2)
        with cfg1:
            st.subheader("Distribución por Estatus en Almacén / Entrega")
            if 'Estatus' in df_config.columns:
                df_c_est = df_config['Estatus'].value_counts().head(10).reset_index()
                df_c_est.columns = ['Estatus', 'Cantidad']
                fig_c1 = px.bar(df_c_est, x='Cantidad', y='Estatus', orientation='h', text_auto=True, color='Cantidad', color_continuous_scale='Greens')
                st.plotly_chart(fig_c1, use_container_width=True)
        with cfg2:
            st.subheader("Volumen de Ítems por Proyecto")
            if 'Proyecto_Nombre' in df_config.columns:
                df_c_proj = df_config['Proyecto_Nombre'].value_counts().head(10).reset_index()
                df_c_proj.columns = ['Proyecto', 'Cantidad']
                fig_c2 = px.bar(df_c_proj, x='Proyecto', y='Cantidad', text_auto=True, color='Cantidad')
                st.plotly_chart(fig_c2, use_container_width=True)

        st.subheader("Buscador de Equipos por Proyecto")
        proyectos_lista = ["TODOS"] + list(df_config['Proyecto_Nombre'].unique()) if 'Proyecto_Nombre' in df_config.columns else ["TODOS"]
        proj_sel = st.selectbox("Seleccionar Proyecto:", proyectos_lista)
        df_cfg_view = df_config if proj_sel == "TODOS" or 'Proyecto_Nombre' not in df_config.columns else df_config[df_config['Proyecto_Nombre'] == proj_sel]
        st.dataframe(df_cfg_view, use_container_width=True)

# TAB 5: MATRIZ CRUZADA & AUDITORÍA
with t5:
    st.subheader("🔀 Matriz Cruzada & Auditoría Operativa Unificada")
    st.markdown("Busca cualquier **Orden de Compra**, **Proyecto** o **Equipo** para ver su estatus simultáneo:")
    
    query = st.text_input("🔍 Ingresa número de OC (ej. MAN01120, MPC05458) o Nombre de Proyecto:", "")
    if query:
        st.markdown("### 1. Coincidencias en Órdenes de Compra (Odoo):")
        if not df_po.empty and 'Referencia de la orden' in df_po.columns:
            m_po = df_po[df_po['Referencia de la orden'].astype(str).str.contains(query, case=False, na=False)]
            cols_show = [c for c in COLS_PO_SHOW if c in m_po.columns]
            st.dataframe(m_po[cols_show], use_container_width=True)
            
        st.markdown("### 2. Coincidencias en Tracking Philips:")
        if not df_philips.empty:
            cond_phil = pd.Series(False, index=df_philips.index)
            if 'Orden_Compra' in df_philips.columns:
                cond_phil |= df_philips['Orden_Compra'].astype(str).str.contains(query, case=False, na=False)
            if 'Proyecto' in df_philips.columns:
                cond_phil |= df_philips['Proyecto'].astype(str).str.contains(query, case=False, na=False)
            st.dataframe(df_philips[cond_phil], use_container_width=True)
            
        st.markdown("### 3. Coincidencias en Configuraciones 2026:")
        if not df_config.empty:
            cond_cfg = pd.Series(False, index=df_config.index)
            if 'Orden_Compra' in df_config.columns:
                cond_cfg |= df_config['Orden_Compra'].astype(str).str.contains(query, case=False, na=False)
            if 'Proyecto_Nombre' in df_config.columns:
                cond_cfg |= df_config['Proyecto_Nombre'].astype(str).str.contains(query, case=False, na=False)
            st.dataframe(df_config[cond_cfg], use_container_width=True)