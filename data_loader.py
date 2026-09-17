import os
import glob
import pandas as pd

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

IMPORT_KEYWORDS = [
    'at-os', 'merivaara', 'respironics', 'rimsa', 'givas', 'vassilli', 'cmr', 
    'heartstream', 'healing resources', 'dell', 'simad', 'italray', 
    'opt surgisystems', 'schiller'
]

def clasificar_proveedor(nombre_proveedor):
    if pd.isna(nombre_proveedor):
        return "🇲🇽 Nacional"
    nombre_clean = str(nombre_proveedor).lower()
    for kw in IMPORT_KEYWORDS:
        if kw in nombre_clean:
            return "🚢 Importación (Requiere Doc)"
    return "🇲🇽 Nacional"

def calcular_semaforo(row, fecha_referencia):
    if pd.isna(row.get('Fecha_Limite')):
        return "⚪ Sin Fecha"
    if str(row.get('Estado')) in ['Cancelado', 'Bloqueado']:
        return "⚪ Inactivo / Creado"
        
    dias_diferencia = (row['Fecha_Limite'].date() - fecha_referencia).days
    if dias_diferencia < 0:
        return "🔴 Vencido"
    elif 0 <= dias_diferencia <= 7:
        return "🟡 Próximo a Vencer (<=7 días)"
    else:
        return "🟢 A Tiempo"

def find_file(possible_names):
    for name in possible_names:
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            return path
        if os.path.exists(name):
            return name
    return None

def load_po_data(filepath=None):
    if filepath is None:
        filepath = find_file([
            "Orden de compra (purchase.order).xlsx", 
            "Orden de compra (purchase.order)_2.xlsx", 
            "purchase.order.xlsx"
        ])
    
    if not filepath or not os.path.exists(filepath):
        return pd.DataFrame()

    try:
        df = pd.read_excel(filepath)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    if 'Referencia de la orden' in df.columns and 'Total' in df.columns:
        df = df.dropna(subset=['Referencia de la orden', 'Total'], how='all')

    df['Referencia de la orden'] = df['Referencia de la orden'].ffill() if 'Referencia de la orden' in df.columns else 'Sin Ref'
    df['Comprador'] = df['Comprador'].ffill().fillna('Sin Asignar') if 'Comprador' in df.columns else 'Sin Asignar'
    df['Empresa'] = df['Empresa'].ffill().fillna('Sin Empresa') if 'Empresa' in df.columns else 'Sin Empresa'
    df['Proveedor'] = df['Proveedor'].ffill().fillna('Sin Proveedor') if 'Proveedor' in df.columns else 'Sin Proveedor'
    df['Estado'] = df['Estado'].fillna('Sin Estado') if 'Estado' in df.columns else 'Sin Estado'
    df['Moneda'] = df['Moneda'].fillna('MXN') if 'Moneda' in df.columns else 'MXN'
    
    tasas = {'MXN': 1.0, 'USD': 17.50, 'EUR': 19.00, 'GBP': 22.00}
    df['Total'] = pd.to_numeric(df['Total'] if 'Total' in df.columns else 0, errors='coerce').fillna(0)
    df['Total_MXN'] = df.apply(lambda r: r['Total'] * tasas.get(str(r['Moneda']).upper(), 1.0), axis=1)
    
    df['Producto'] = df['Producto'].fillna('Sin Especificar') if 'Producto' in df.columns else 'Sin Especificar'
    cant_col = 'Producto/Cantidad de material' if 'Producto/Cantidad de material' in df.columns else 'Cantidad'
    df['Cantidad'] = pd.to_numeric(df[cant_col] if cant_col in df.columns else 1, errors='coerce').fillna(1)
    
    df['Tipo_Proveedor'] = df['Proveedor'].apply(clasificar_proveedor)
    fecha_col = 'Fecha límite de la orden' if 'Fecha límite de la orden' in df.columns else 'Fecha'
    df['Fecha_Limite'] = pd.to_datetime(df[fecha_col] if fecha_col in df.columns else None, errors='coerce')
    
    fecha_ref = pd.to_datetime('2026-09-08').date()
    df['Semaforo'] = df.apply(lambda r: calcular_semaforo(r, fecha_ref), axis=1)
    return df

def load_philips_data(filepath=None):
    if filepath is None:
        filepath = find_file([
            "Seguimiento Philips _ MPC - Ordenes de compra_2.xlsx", 
            "Seguimiento Philips _ MPC - Ordenes de compra_3.xlsx", 
            "Seguimiento Philips _ MPC - Ordenes de compra.xlsx"
        ])
        
    if not filepath or not os.path.exists(filepath):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(filepath)
    except Exception:
        return pd.DataFrame()

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
    
    for col in df_all.columns:
        c_str = str(col).strip()
        if 'Orden' in c_str or 'OC' in c_str: df_all.rename(columns={col: 'Orden_Compra'}, inplace=True)
        elif 'Estatus' in c_str or 'Situación' in c_str: df_all.rename(columns={col: 'Estatus'}, inplace=True)
        elif 'Proyecto' in c_str: df_all.rename(columns={col: 'Proyecto'}, inplace=True)
        elif 'Descripción' in c_str: df_all.rename(columns={col: 'Descripcion'}, inplace=True)
        elif 'Cantidad' in c_str: df_all.rename(columns={col: 'Cantidad'}, inplace=True)
        elif 'Empresa' in c_str: df_all.rename(columns={col: 'Empresa'}, inplace=True)

    if 'Estatus' not in df_all.columns: df_all['Estatus'] = 'Sin Estatus'
    else: df_all['Estatus'] = df_all['Estatus'].fillna('Sin Estatus').astype(str)
    
    if 'Orden_Compra' not in df_all.columns: df_all['Orden_Compra'] = 'Sin OC'
    else: df_all['Orden_Compra'] = df_all['Orden_Compra'].fillna('Sin OC').astype(str)
    
    if 'Proyecto' not in df_all.columns: df_all['Proyecto'] = 'Sin Proyecto'
    else: df_all['Proyecto'] = df_all['Proyecto'].fillna('Sin Proyecto').astype(str)
    
    return df_all

def load_config_data(filepath=None):
    if filepath is None:
        filepath = find_file([
            "PENDIENTES _ CONFIGURACIONES 2026_2.xlsx", 
            "PENDIENTES _ CONFIGURACIONES 2026_3.xlsx", 
            "PENDIENTES _ CONFIGURACIONES 2026.xlsx"
        ])

    if not filepath or not os.path.exists(filepath):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(filepath)
    except Exception:
        return pd.DataFrame()

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
    if 'Estatus' in df_all.columns:
        df_all['Estatus'] = df_all['Estatus'].fillna('PENDIENTES / SIN ESTATUS').astype(str)
    else:
        df_all['Estatus'] = 'PENDIENTES / SIN ESTATUS'
        
    if 'Proyecto_Nombre' not in df_all.columns:
        df_all['Proyecto_Nombre'] = 'General'

    return df_all