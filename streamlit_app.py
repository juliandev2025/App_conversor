"""
streamlit_app.py
Punto de entrada oficial para Streamlit Community Cloud.
Despliegue automatico en https://share.streamlit.io / https://*.streamlit.app
Soporta generacion y descarga de PDF Oficial, Imagenes PNG HD y archivo TXT.
"""

import io
import os
import tempfile
import streamlit as st
import conversor_core
try:
    import logo_data
except ImportError:
    logo_data = None

st.set_page_config(
    page_title="App Conversor - Estado de Cuenta",
    page_icon="📄",
    layout="wide"
)

# Estilos CSS ejecutivos para la interfaz web
st.markdown("""
<style>
    /* 1. Fondo Atmosférico Ultra-Oscuro con Orbes Calcite de Alta Luminosidad */
    .stApp {
        background-color: #090a0d !important;
        background-image: 
            radial-gradient(circle at 10% 20%, #101217 0%, #090a0d 100%) !important;
        color: #f0ece9 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        position: relative;
        overflow-x: hidden;
    }

    /* Capa de orbes difuminados de fondo - Alta intensidad y luminosidad */
    .stApp::before {
        content: "";
        position: absolute;
        top: -10%; left: -10%; width: 120%; height: 120%;
        background: 
            /* Orbe 1: Naranja Intenso Encendido Superior Izquierdo */
            radial-gradient(circle at 5% 20%, rgba(255, 115, 45, 0.85) 0%, rgba(245, 90, 25, 0.45) 35%, rgba(245, 90, 25, 0.1) 60%, transparent 75%),
            /* Orbe 2: Halo Blanco/Acero Glacial Superior Derecho */
            radial-gradient(circle at 85% 15%, rgba(185, 205, 225, 0.35) 0%, rgba(140, 160, 180, 0.12) 40%, transparent 65%),
            /* Orbe 3: Melocotón Crema Suave e Iluminado Inferior Izquierdo */
            radial-gradient(circle at 8% 85%, rgba(255, 210, 175, 0.7) 0%, rgba(240, 175, 135, 0.32) 40%, rgba(240, 175, 135, 0.08) 65%, transparent 75%),
            /* Orbe 4: Cobre / Ámbar Encendido Inferior Derecho */
            radial-gradient(circle at 92% 78%, rgba(245, 110, 40, 0.65) 0%, rgba(210, 80, 25, 0.3) 40%, rgba(210, 80, 25, 0.06) 65%, transparent 75%);
        pointer-events: none;
        z-index: 0;
        filter: blur(80px);
    }

    /* Evitar que Streamlit tape el efecto de los orbes */
    .stApp > div {
        position: relative;
        z-index: 1;
    }

    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; }

    /* 2. Área de Carga - Cristal Ahumado con Refracción y Borde Cristalino */
    div[data-testid="stFileUploader"] {
        background: rgba(22, 25, 33, 0.38) !important;
        backdrop-filter: blur(28px) saturate(130%) !important;
        -webkit-backdrop-filter: blur(28px) saturate(130%) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.28) !important;
        border-radius: 26px !important;
        padding: 2.2rem !important;
        box-shadow: 
            0 30px 60px rgba(0, 0, 0, 0.5), 
            inset 0 1px 0 rgba(255, 255, 255, 0.18) !important;
        transition: all 0.3s ease;
    }
    div[data-testid="stFileUploader"]:hover {
        background: rgba(26, 30, 40, 0.48) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.45) !important;
    }
    div[data-testid="stFileUploader"] p { color: #8a8c90 !important; }
    
    /* Botón Browse Files de Streamlit */
    div[data-testid="stFileUploader"] button {
        background: linear-gradient(180deg, #d35922 0%, #b84312 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.35) !important;
        border-radius: 50px !important;
        font-weight: 600 !important;
        box-shadow: 0 10px 25px rgba(200, 80, 25, 0.38) !important;
    }

    /* 3. Barra de Identidad del Cliente (Ahumado Oscuro con Vidrio Traslúcido) */
    .client-badge-bar {
        background: rgba(22, 25, 33, 0.38) !important;
        backdrop-filter: blur(28px) !important;
        -webkit-backdrop-filter: blur(28px) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.28) !important;
        border-radius: 18px !important;
        padding: 16px 24px !important;
        margin: 1.5rem 0 !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
    }
    .client-name { 
        color: #f0ece9 !important; 
        font-weight: 800 !important;
        font-size: 1.18rem !important; 
        letter-spacing: 0.02em !important;
    }
    .client-meta { 
        color: #a3a1a8 !important;
        font-size: 0.85rem !important;
    }

    /* 4. Tarjetas KPI Premium con Reflejos y Bordes de Acento */
    .kpi-card {
        background: rgba(22, 25, 33, 0.38) !important;
        backdrop-filter: blur(28px) !important;
        -webkit-backdrop-filter: blur(28px) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.28) !important;
        border-radius: 20px !important;
        padding: 18px 20px !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 115px !important;
        box-shadow: 0 25px 45px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.14) !important;
        position: relative;
        overflow: hidden;
    }
    
    /* Tarjeta Pagos Destacada en Melocotón Calcite */
    .kpi-card-pagos-solid {
        background: #efbe98 !important;
        border: 1px solid rgba(255, 255, 255, 0.45) !important;
        border-radius: 20px !important;
        padding: 18px 20px !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 115px !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.5) !important;
    }
    .kpi-card-pagos-solid .kpi-lbl { color: #523e32 !important; }
    .kpi-card-pagos-solid .kpi-val { color: #1c1511 !important; font-size: 28px !important; font-weight: 800 !important; margin: 4px 0; }
    .kpi-card-pagos-solid .kpi-sub { color: #5a463a !important; }

    /* Tipografías y Datos de las Tarjetas */
    .kpi-lbl { font-size: 11px; font-weight: 600; color: #8a8c90; letter-spacing: 0.05em; text-transform: uppercase; }
    .kpi-val-cicladas { font-size: 28px; font-weight: 700; color: #f0ece9; margin: 4px 0; }
    .kpi-val-orange { font-size: 28px; font-weight: 700; color: #fd7b41; margin: 4px 0; }
    .kpi-sub { font-size: 11px; color: #9f9da2 !important; }

    /* 5. Botones de Descarga en Acero/Cobre */
    div.stDownloadButton > button {
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-radius: 50px !important;
        font-weight: 600 !important;
        padding: 0.65rem 1.9rem !important;
        transition: all 0.2s ease !important;
    }
    div.btn-col-pdf div.stDownloadButton > button {
        background: linear-gradient(180deg, #d35922 0%, #b84312 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.22) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.4) !important;
        color: #ffffff !important;
        box-shadow: 0 12px 28px rgba(200, 80, 25, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    }
    div.btn-col-pdf div.stDownloadButton > button:hover {
        background: linear-gradient(180deg, #e4662d 0%, #c44a16 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 16px 34px rgba(230, 90, 30, 0.55) !important;
    }
    div.btn-col-img div.stDownloadButton > button {
        background: rgba(30, 34, 44, 0.45) !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
        color: #f0ece9 !important;
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    }
    div.btn-col-img div.stDownloadButton > button:hover {
        background: rgba(38, 44, 58, 0.6) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        color: #ffffff !important;
        transform: translateY(-2px);
    }

    /* 6. Vista del visor de reportes */
    div.report-container {
        box-shadow: 0 -15px 40px rgba(10, 13, 22, 0.9);
        border-top: 1px solid rgba(237, 191, 155, 0.05);
        border-radius: 24px 24px 0px 0px;
        background-color: #ffffff;
        padding-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Encabezado con Logo oficial KrediYA
col_logo, col_title = st.columns([1.2, 4.8])
with col_logo:
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "krediya_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    elif logo_data:
        st.image(logo_data.get_krediya_logo_bytes(), use_container_width=True)
with col_title:
    st.markdown('<div class="main-title">App Conversor de Cronogramas</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Arrastra el cronograma generado por Admin (`cronograma_*.pdf`)",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()

        with st.spinner(f"Procesando {uploaded_file.name}..."):
            data = conversor_core.extract_cronograma_data(file_bytes)
            analysis = conversor_core.analyze_and_classify_movements(data)
            html_content = conversor_core.render_html_report(data, analysis)

            # Generar PDF en temporal
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                tmp_pdf_path = tmp_pdf.name

            image_bytes_list = []
            txt_content = ""
            try:
                pdf_path = conversor_core.convert_html_to_pdf(
                    html_content, tmp_pdf_path, data=data, analysis=analysis
                )
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                # Generar imágenes PNG de alta calidad (200 DPI)
                try:
                    img_paths = conversor_core.convert_pdf_to_images(pdf_path, dpi=200)
                    for ip in img_paths:
                        with open(ip, "rb") as imf:
                            image_bytes_list.append((os.path.basename(ip), imf.read()))
                        try: os.remove(ip)
                        except: pass
                except Exception:
                    pass

                # Generar archivo TXT
                tmp_txt_path = tmp_pdf_path + ".txt"
                try:
                    conversor_core.generate_txt_report(data, analysis, tmp_txt_path)
                    with open(tmp_txt_path, "r", encoding="utf-8-sig") as tf:
                        txt_content = tf.read()
                finally:
                    if os.path.exists(tmp_txt_path):
                        try: os.remove(tmp_txt_path)
                        except: pass

            finally:
                if os.path.exists(tmp_pdf_path):
                    try: os.remove(tmp_pdf_path)
                    except: pass

        # Barra de Identidad del Cliente estilo Glassmorphism
        st.markdown(f"""
        <div class="client-badge-bar">
            <div class="client-name">{data['nombre']}</div>
            <div class="client-meta">Contrato: {data['contrato']} | Cédula: {data['identificacion']} | Saldo Pendiente: {data['saldo_actual']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Fila de métricas estilo Glassmorphism
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-lbl">Cuotas Cicladas</div>
                <div class="kpi-val-cicladas">{analysis['cicladas_count']}</div>
                <div class="kpi-sub">Vencidas a la fecha</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="kpi-card-pagos-solid">
                <div class="kpi-lbl">Pagos Aplicados</div>
                <div class="kpi-val">{analysis['pagos_count']}</div>
                <div class="kpi-sub">Total: {analysis['total_pagado_str']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-lbl">Cuotas Atrasadas</div>
                <div class="kpi-val-orange">{analysis['mora_count']}</div>
                <div class="kpi-sub">{analysis['mora_subtitle']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-lbl">Saldo Actual</div>
                <div class="kpi-val-orange">{data['saldo_actual']}</div>
                <div class="kpi-sub">Antes de: {data['pagar_antes_de']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")
        # Fila de botones de descarga principales
        report_base = conversor_core.build_report_basename(data)
        col_btn_pdf, col_btn_img = st.columns(2)

        with col_btn_pdf:
            st.markdown('<div class="btn-col-pdf">', unsafe_allow_html=True)
            st.download_button(
                label="📥 Descargar PDF",
                data=pdf_bytes,
                file_name=f"{report_base}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with col_btn_img:
            st.markdown('<div class="btn-col-img">', unsafe_allow_html=True)
            if image_bytes_list:
                img_data = image_bytes_list[0][1]
                st.download_button(
                    label="🖼️ Descargar Imagen",
                    data=img_data,
                    file_name=f"{report_base}.png",
                    mime="image/png",
                    use_container_width=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

        # Vista rápida del archivo TXT
        if txt_content:
            with st.expander("📝 Ver Resumen en Texto Plano (TXT)", expanded=False):
                st.code(txt_content, language="text")

        # Previsualización embebida del HTML
        st.write("### 👁️ Vista Previa del Documento Oficial")
        st.components.v1.html(html_content, height=1150, scrolling=True)

else:
    st.info("👆 Para iniciar, arrastra o selecciona uno o varios cronogramas generados por tu plataforma (`cronograma_*.pdf`).")
    st.write("### 💡 ¿Cómo funciona la App?")
    st.markdown("""
    1. **Sube el cronograma** exportado del CRM (`cronograma_*.pdf`).
    2. **La aplicación analiza automáticamente**:
       - **Cuotas Cicladas**: Cuotas con fecha de vencimiento cumplida a la fecha de consulta.
       - **Pagos Aplicados**: Pagos verificados por monto acumulado.
       - **Cuotas Atrasadas**: Cuotas en mora pendiente.
       - **Cuotas Por Ciclar**: Cuotas futuras programadas en el calendario.
    3. **Descarga el formato que prefieras**:
       - **PDF Oficial**: Idéntico a la plantilla ejecutiva.
       - **Imagen PNG HD**: 200 DPI lista para compartir por WhatsApp o redes.
       - **Archivo TXT**: Texto formateado y limpio para copiar directamente a correos o chats de soporte.
    """)
