import os
import pandas as pd
import plotly.express as px
from data_loader import load_po_data, load_philips_data, load_config_data

print("🚀 Cargando datos para reporte HTML...")
df_po = load_po_data()
df_philips = load_philips_data()
df_config = load_config_data()

# Crear gráficos
fig1 = px.pie(df_po, names='Semaforo', title='Semáforo General de Entregas (Odoo POs)', hole=0.4)
fig2 = px.bar(df_philips['Estatus'].value_counts().reset_index(), x='Estatus', y='count', title='Estatus Órdenes Philips')
fig3 = px.bar(df_config['Estatus'].value_counts().head(10).reset_index(), x='count', y='Estatus', orientation='h', title='Top Estatus Configuraciones 2026')

html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Máster de Compras, Philips & Configuraciones</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
        .kpi-card {{ background: white; padding: 18px; border-radius: 8px; border: 1px solid #dee2e6; text-align: center; margin-bottom: 15px; }}
        .kpi-val {{ font-size: 24px; font-weight: bold; color: #0d6efd; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h2 class="mb-3 text-primary">🏢 Monitor Máster Integrado: Compras, Philips & Proyectos</h2>
        <p class="text-muted">Reporte interactivo autónomo generado el {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M hrs')}</p>
        
        <div class="row">
            <div class="col-md-3"><div class="kpi-card"><div>Total OCs Odoo</div><div class="kpi-val">{len(df_po):,}</div></div></div>
            <div class="col-md-3"><div class="kpi-card"><div>Registros Philips</div><div class="kpi-val">{len(df_philips):,}</div></div></div>
            <div class="col-md-3"><div class="kpi-card"><div>Configuraciones 2026</div><div class="kpi-val">{len(df_config):,}</div></div></div>
            <div class="col-md-3"><div class="kpi-card"><div>Proyectos Activos</div><div class="kpi-val">{df_config['Proyecto_Nombre'].nunique() if not df_config.empty else 0}</div></div></div>
        </div>

        <div class="row mt-4">
            <div class="col-md-4">{fig1.to_html(full_html=False, include_plotlyjs=False)}</div>
            <div class="col-md-4">{fig2.to_html(full_html=False, include_plotlyjs=False)}</div>
            <div class="col-md-4">{fig3.to_html(full_html=False, include_plotlyjs=False)}</div>
        </div>
    </div>
</body>
</html>
"""

with open("dashboard_master.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ ¡Archivo 'dashboard_master.html' generado con éxito! Puedes abrirlo en cualquier navegador.")