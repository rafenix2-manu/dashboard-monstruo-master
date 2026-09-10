import os
import io
import requests
import xmlrpc.client
import pandas as pd
from datetime import date

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------
# CREDENCIALES OFICIALES Y CONFIGURACIÓN DE ODOO Y SHEETS
# ---------------------------------------------------------
ODOO_URL = "https://dispositivosmedicos2024.odoo.com"
DEFAULT_ODOO_DB = "dispositivosmedicos2024"
DEFAULT_ODOO_USER = "mnf@manprec.com"
DEFAULT_ODOO_PASS = "Manprec2025%"

GOOGLE_SHEET_PHILIPS_ID = "1s7Whvwpvf_5gMXyqtQwSk1NOU3rOFOjrU-P_LsvjnCw"
GOOGLE_SHEET_CONFIG_ID = "1ZhgCW_hCA8dvj2UENKdBupQ9TaK9MWbOFQc6gojALVI"
GOOGLE_SHEET_CARGO_ID = "1xYJ2Rr6PCCGBh78RZHqAWGoHmWgfLxIIIT0KRsq1r8U"

IMPORT_KEYWORDS = [
    'at-os', 'merivaara', 'respironics', 'rimsa', 'givas', 'vassilli', 'cmr',
    'heartstream netherlands', 'healing resources', 'dell marketing',
    'simad', 'italray', 'opt surgisystems', 'schiller americas inc'
]

def clasificar_proveedor(nombre_proveedor):
    if pd.isna(nombre_proveedor):
        return "🇲🇽 Nacional"
    nombre_clean = str(nombre_proveedor).lower().strip()
    if "schiller americas-mexico" in nombre_clean or "schiller americas mexico" in nombre_clean:
        return "🇲🇽 Nacional"
    for kw in IMPORT_KEYWORDS:
        if kw in nombre_clean:
            return "🚢 Importación (Requiere Doc)"
    return "🇲🇽 Nacional"

def calcular_semaforo(row, fecha_referencia):
    if pd.isna(row.get('Fecha_Limite')):
        return "⚪ Sin Fecha"
    if str(row.get('Estado')) in ['Cancelado', 'Bloqueado', 'cancel']:
        return "⚪ Inactivo / Creado"
        
    dias_diferencia = (row['Fecha_Limite'].date() - fecha_referencia).days
    if dias_diferencia < 0:
        return "🔴 Vencido"
    elif 0 <= dias_diferencia <= 7:
        return "🟡 Próximo a Vencer (<=7 días)"
    else:
        return "🟢 A Tiempo"

def calcular_semaforo_importacion(row, fecha_referencia):
    if str(row.get('Tipo_Proveedor')) == "🇲🇽 Nacional":
        return "🇲🇽 Nacional"
    if pd.isna(row.get('Fecha_Limite')):
        return "⚪ Sin Fecha Límite"
    if str(row.get('Estado')) in ['Cancelado', 'Bloqueado', 'cancel']:
        return "⚪ Inactivo / Creado"
        
    dias = (row['Fecha_Limite'].date() - fecha_referencia).days
    if dias < 0:
        return "🚨 CRÍTICO: Vencido (Atraso Aduana/Doc)"
    elif 0 <= dias <= 7:
        return "⚠️ URGENTE: Vence ≤7 días (Solicitar Pedimento)"
    elif 8 <= dias <= 15:
        return "🟡 PRECAUCIÓN: Próximo 8-15 días (Validar Doc)"
    else:
        return "🟢 EN TIEMPO (>15 días)"

def buscar_archivo_local(nombres_posibles):
    for nombre in nombres_posibles:
        ruta_data = os.path.join(DATA_DIR, nombre)
        if os.path.exists(ruta_data):
            return ruta_data
        if os.path.exists(nombre):
            return nombre
    return None

# ---------------------------------------------------------
# 1. CARGA EXCLUSIVA DEL MÓDULO DE COMPRAS ODOO
# ---------------------------------------------------------
def load_po_data(odoo_db=None, odoo_user=None, odoo_password=None):
    db = odoo_db if odoo_db else DEFAULT_ODOO_DB
    user = odoo_user if odoo_user else DEFAULT_ODOO_USER
    password = odoo_password if odoo_password else DEFAULT_ODOO_PASS

    df_live = fetch_odoo_live(db, user, password)
    if df_live is not None and not df_live.empty:
        return df_live

    ruta = buscar_archivo_local([
        "Orden de compra (purchase.order).xlsx",
        "Orden de compra (purchase.order)_2.xlsx",
        "purchase.order.xlsx"
    ])
    if not ruta or not os.path.exists(ruta):
        return pd.DataFrame()

    try:
        df = pd.read_excel(ruta)
        return procesar_df_po(df)
    except Exception:
        return pd.DataFrame()

def fetch_odoo_live(db, user, password):
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = None
        for db_option in [db, "dispositivosmedicos2024", "dispositivosmedicos2024.odoo.com"]:
            try:
                auth_uid = common.authenticate(db_option, user, password, {})
                if auth_uid:
                    uid = auth_uid
                    db = db_option
                    break
            except Exception:
                continue

        if not uid:
            return None

        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        po_domain = [('state', '!=', 'cancel')]
        po_ids = models.execute_kw(db, uid, password, 'purchase.order', 'search', [po_domain])
        
        if not po_ids:
            return None

        po_fields = ['id', 'name', 'partner_id', 'user_id', 'company_id', 'state', 'date_planned', 'amount_total', 'currency_id']
        orders = models.execute_kw(db, uid, password, 'purchase.order', 'read', [po_ids], {'fields': po_fields})
        
        if not orders:
            return None

        po_dict = {}
        for po in orders:
            po_dict[po['id']] = {
                'po_name': str(po.get('name', 'Sin Ref')).strip(),
                'vendor': po['partner_id'][1] if isinstance(po.get('partner_id'), (list, tuple)) else 'Sin Proveedor',
                'buyer': po['user_id'][1] if isinstance(po.get('user_id'), (list, tuple)) else 'Sin Asignar',
                'company': po['company_id'][1] if isinstance(po.get('company_id'), (list, tuple)) else 'Sin Empresa',
                'state': po.get('state', 'draft'),
                'date_planned': po.get('date_planned'),
                'amount_total': po.get('amount_total', 0.0),
                'currency': po['currency_id'][1] if isinstance(po.get('currency_id'), (list, tuple)) else 'MXN'
            }

        line_ids = models.execute_kw(db, uid, password, 'purchase.order.line', 'search', [[('order_id', 'in', po_ids)]])
        if line_ids:
            line_fields = ['order_id', 'product_id', 'name', 'product_qty', 'price_unit', 'price_subtotal', 'date_planned']
            lines = models.execute_kw(db, uid, password, 'purchase.order.line', 'read', [line_ids], {'fields': line_fields})
            
            rows = []
            for line in lines:
                order_tuple = line.get('order_id')
                if not order_tuple or not isinstance(order_tuple, (list, tuple)):
                    continue
                p_id = order_tuple[0]
                po_info = po_dict.get(p_id)
                if not po_info:
                    continue

                prod_tuple = line.get('product_id')
                prod_name = prod_tuple[1] if isinstance(prod_tuple, (list, tuple)) else str(line.get('name', 'Sin Especificar'))

                rows.append({
                    'Referencia de la orden': po_info['po_name'],
                    'Proveedor': po_info['vendor'],
                    'Comprador': po_info['buyer'],
                    'Empresa': po_info['company'],
                    'Estado': po_info['state'],
                    'Fecha límite de la orden': line.get('date_planned') or po_info['date_planned'],
                    'Producto': prod_name,
                    'Cantidad': line.get('product_qty', 1),
                    'Precio Unitario': line.get('price_unit', 0),
                    'Total': line.get('price_subtotal', 0),
                    'Moneda': po_info['currency']
                })
            
            if rows:
                return procesar_df_po(pd.DataFrame(rows))

    except Exception as e:
        print(f"Aviso API Odoo: {e}")
    return None

def procesar_df_po(df_in):
    if df_in.empty:
        return pd.DataFrame()

    df = df_in.copy()

    df['Referencia de la orden'] = df['Referencia de la orden'].ffill().fillna('Sin Ref')
    df['Comprador'] = df['Comprador'].ffill().fillna('Sin Asignar')
    df['Empresa'] = df['Empresa'].ffill().fillna('Sin Empresa')
    df['Proveedor'] = df['Proveedor'].ffill().fillna('Sin Proveedor')
    df['Estado'] = df['Estado'].fillna('Sin Estado')
    df['Moneda'] = df['Moneda'].fillna('MXN')
    df['Producto'] = df['Producto'].fillna('Sin Especificar')

    estado_map = {
        'draft': 'Solicitud de cotización',
        'sent': 'Cotización enviada',
        'to approve': 'Por aprobar',
        'purchase': 'Orden de compra',
        'done': 'Bloqueado / Hecho',
        'cancel': 'Cancelado'
    }
    df['Estado'] = df['Estado'].replace(estado_map)

    tasas = {'MXN': 1.0, 'USD': 17.50, 'EUR': 19.00, 'GBP': 22.00}
    df['Total'] = pd.to_numeric(df['Total'] if 'Total' in df.columns else 0, errors='coerce').fillna(0)
    df['Total_MXN'] = df.apply(lambda r: r['Total'] * tasas.get(str(r['Moneda']).upper(), 1.0), axis=1)
    
    cant_col = 'Producto/Cantidad de material' if 'Producto/Cantidad de material' in df.columns else 'Cantidad'
    df['Cantidad'] = pd.to_numeric(df[cant_col] if cant_col in df.columns else 1, errors='coerce').fillna(1)
    
    df['Tipo_Proveedor'] = df['Proveedor'].apply(clasificar_proveedor)
    fecha_col = 'Fecha límite de la orden' if 'Fecha límite de la orden' in df.columns else 'Fecha'
    df['Fecha_Limite'] = pd.to_datetime(df[fecha_col] if fecha_col in df.columns else None, errors='coerce')
    
    fecha_ref = date(2026, 9, 8)
    df['Semaforo'] = df.apply(lambda r: calcular_semaforo(r, fecha_ref), axis=1)
    df['Semaforo_Importacion'] = df.apply(lambda r: calcular_semaforo_importacion(r, fecha_ref), axis=1)

    return df

# ---------------------------------------------------------
# 2. CARGA DE SEGUIMIENTO PHILIPS
# ---------------------------------------------------------
def load_philips_data():
    url_online = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_PHILIPS_ID}/export?format=xlsx"
    try:
        response = requests.get(url_online, timeout=10)
        if response.status_code == 200:
            xls = pd.ExcelFile(io.BytesIO(response.content))
            return procesar_excel_philips(xls)
    except Exception as e:
        print(f"Aviso Google Sheets Philips: {e}")

    ruta = buscar_archivo_local([
        "Seguimiento Philips _ MPC - Ordenes de compra.xlsx",
        "Seguimiento Philips _ MPC - Ordenes de compra_2.xlsx"
    ])
    if not ruta or not os.path.exists(ruta):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(ruta)
        return procesar_excel_philips(xls)
    except Exception:
        return pd.DataFrame()

def procesar_excel_philips(xls):
    dfs = []
    if 'Hoja 1' in xls.sheet_names:
        df1 = pd.read_excel(xls, sheet_name='Hoja 1', header=2)
        if not df1.empty and 'Empresa' in df1.iloc[0].values:
            df1 = pd.read_excel(xls, sheet_name='Hoja 1', header=3)
        df1['Origen_Hoja'] = 'General Philips'
        dfs.append(df1)
        
    for sheet in xls.sheet_names:
        if sheet in ['Hoja 10', 'Q1 - 2025', 'Hoja 8', 'Hoja 6']:
            h = 1 if sheet in ['Q1 - 2025', 'Hoja 6'] else 0
            df_s = pd.read_excel(xls, sheet_name=sheet, header=h)
            df_s['Origen_Hoja'] = sheet
            dfs.append(df_s)
            
    df_all = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    if df_all.empty:
        return pd.DataFrame()
    
    new_cols = []
    for col in df_all.columns:
        c_str = str(col).strip()
        if 'Orden' in c_str or 'OC' in c_str: new_cols.append('Orden_Compra')
        elif 'Estatus' in c_str or 'Situación' in c_str: new_cols.append('Estatus')
        elif 'Proyecto' in c_str: new_cols.append('Proyecto')
        elif 'Descripción' in c_str: new_cols.append('Descripcion')
        elif 'Cantidad' in c_str: new_cols.append('Cantidad')
        elif 'Empresa' in c_str: new_cols.append('Empresa')
        else: new_cols.append(col)

    df_all.columns = new_cols
    df_all = df_all.loc[:, ~df_all.columns.duplicated(keep='first')]

    if 'Estatus' not in df_all.columns: df_all['Estatus'] = 'Sin Estatus'
    else: df_all['Estatus'] = df_all['Estatus'].fillna('Sin Estatus').astype(str)
    
    if 'Orden_Compra' not in df_all.columns: df_all['Orden_Compra'] = 'Sin OC'
    else: df_all['Orden_Compra'] = df_all['Orden_Compra'].fillna('Sin OC').astype(str)
    
    if 'Proyecto' not in df_all.columns: df_all['Proyecto'] = 'Sin Proyecto'
    else: df_all['Proyecto'] = df_all['Proyecto'].fillna('Sin Proyecto').astype(str)
    
    return df_all

# ---------------------------------------------------------
# 3. CARGA DE CONFIGURACIONES 2026
# ---------------------------------------------------------
def load_config_data():
    url_online = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_CONFIG_ID}/export?format=xlsx"
    try:
        response = requests.get(url_online, timeout=10)
        if response.status_code == 200:
            xls = pd.ExcelFile(io.BytesIO(response.content))
            return procesar_excel_config(xls)
    except Exception as e:
        print(f"Aviso Google Sheets Config: {e}")

    ruta = buscar_archivo_local([
        "PENDIENTES _ CONFIGURACIONES 2026.xlsx",
        "PENDIENTES _ CONFIGURACIONES 2026_2.xlsx"
    ])
    if not ruta or not os.path.exists(ruta):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(ruta)
        return procesar_excel_config(xls)
    except Exception:
        return pd.DataFrame()

def procesar_excel_config(xls):
    project_dfs = []
    for sheet_name in xls.sheet_names:
        if sheet_name in ['DASHBOARD', 'Hoja 30', 'Hoja 31']: continue
        df_s = pd.read_excel(xls, sheet_name=sheet_name)
        if df_s.empty: continue
        
        header_found = None
        if 'DESCRIPCIÓN' in df_s.columns or 'PROVEEDOR' in df_s.columns or 'CANTIDAD' in df_s.columns:
            header_found = 0
        else:
            for h in [1, 2, 3]:
                df_s_h = pd.read_excel(xls, sheet_name=sheet_name, header=h)
                if 'DESCRIPCIÓN' in df_s_h.columns or 'PROVEEDOR' in df_s_h.columns or 'CANTIDAD' in df_s_h.columns:
                    df_s = df_s_h
                    header_found = h
                    break
                    
        if header_found is not None:
            df_s['Proyecto_Nombre'] = sheet_name
            project_dfs.append(df_s)
            
    df_all = pd.concat(project_dfs, ignore_index=True) if project_dfs else pd.DataFrame()
    if df_all.empty:
        return pd.DataFrame()

    col_map = {
        'DESCRIPCIÓN': 'Descripcion', 'CANTIDAD': 'Cantidad', 'PROVEEDOR': 'Proveedor',
        'MARCA': 'Marca', 'MODELO': 'Modelo', 'ESTATUS': 'Estatus', 'COSTO': 'Costo',
        'MONEDA COSTO': 'Moneda', 'PEDIDO': 'Pedido', 'OC': 'Orden_Compra', 'OBSERVACIONES': 'Observaciones'
    }
    df_all.rename(columns=col_map, inplace=True)
    df_all = df_all.loc[:, ~df_all.columns.duplicated(keep='first')]

    if 'Estatus' in df_all.columns:
        df_all['Estatus'] = df_all['Estatus'].fillna('PENDIENTES / SIN ESTATUS').astype(str)
    else:
        df_all['Estatus'] = 'PENDIENTES / SIN ESTATUS'
        
    if 'Proyecto_Nombre' not in df_all.columns:
        df_all['Proyecto_Nombre'] = 'General'

    return df_all

# ---------------------------------------------------------
# 4. CARGA DE SEGUIMIENTO AGENTE ADUANAL (CARGO)
# ---------------------------------------------------------
def load_cargo_data():
    url_online = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_CARGO_ID}/export?format=xlsx"
    try:
        response = requests.get(url_online, timeout=10)
        if response.status_code == 200:
            xls = pd.ExcelFile(io.BytesIO(response.content))
            return procesar_excel_cargo(xls)
    except Exception as e:
        print(f"Aviso Google Sheets CARGO: {e}")

    ruta = buscar_archivo_local([
        "Seguimiento CARGO.xlsx",
        "CARGO.xlsx"
    ])
    if not ruta or not os.path.exists(ruta):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(ruta)
        return procesar_excel_cargo(xls)
    except Exception:
        return pd.DataFrame()

def procesar_excel_cargo(xls):
    dfs = []
    for sheet in xls.sheet_names:
        try:
            df_s = pd.read_excel(xls, sheet_name=sheet)
            if df_s.empty: continue
            
            if not any(c in str(df_s.columns).upper() for c in ['PEDIMENTO', 'ADUANA', 'STATUS', 'ESTATUS', 'REFERENCIA', 'PROVEEDOR', 'OC', 'CONTENEDOR', 'EMBARQUE']):
                for h in [1, 2, 3]:
                    df_h = pd.read_excel(xls, sheet_name=sheet, header=h)
                    if any(c in str(df_h.columns).upper() for c in ['PEDIMENTO', 'ADUANA', 'STATUS', 'ESTATUS', 'REFERENCIA', 'PROVEEDOR', 'OC', 'CONTENEDOR', 'EMBARQUE']):
                        df_s = df_h
                        break
            df_s['Origen_Hoja'] = sheet
            dfs.append(df_s)
        except Exception:
            continue

    df_all = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    if df_all.empty:
        return pd.DataFrame()

    df_all = df_all.dropna(how='all')
    df_all = df_all.loc[:, ~df_all.columns.duplicated(keep='first')]
    return df_all