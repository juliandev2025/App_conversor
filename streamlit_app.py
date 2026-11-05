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
    /* 1. Fondo Atmosférico Ultra-Oscuro con Orbes Calcite de la GPU */
    .stApp {
        background-color: #0d0e11 !important;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(15, 17, 22, 0.95) 0%, #0d0e11 100%) !important;
        color: #e2dcd7 !important; /* Texto principal claro y cálido */
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        position: relative;
        overflow-x: hidden;
    }

    /* Capa de orbes difuminados de fondo */
    .stApp::before {
        content: "";
        position: absolute;
        top: -10%; left: -10%; width: 120%; height: 120%;
        background: 
            /* Orbe Naranja Encendido Superior Izquierdo */
            radial-gradient(circle at 5% 25%, rgba(253, 123, 65, 0.14) 0%, transparent 45%),
            /* Orbe Melocotón Suave Inferior Izquierdo */
            radial-gradient(circle at 10% 80%, rgba(237, 191, 155, 0.1) 0%, transparent 42%),
            /* Orbe Gris/Acero Superior Derecho (Bajo contraste) */
            radial-gradient(circle at 85% 20%, rgba(60, 64, 68, 0.15) 0%, transparent 40%),
            /* Orbe Cobre Tierra Inferior Derecho (Ambiental) */
            radial-gradient(circle at 90% 75%, rgba(195, 86, 39, 0.12) 0%, transparent 45%);
        pointer-events: none;
        z-index: 0;
        filter: blur(100px); /* Desenfoque extremo para suavizar los orbes */
    }

    /* Evitar que Streamlit tape el efecto de los orbes */
    .stApp > div {
        position: relative;
        z-index: 1;
    }

    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; }

    /* 2. Área de Carga - Cristal Ahumado con Alta Refracción */
    div[data-testid="stFileUploader"] {
        background: rgba(18, 20, 26, 0.45) !important;
        backdrop-filter: blur(35px) saturate(140%);
        -webkit-backdrop-filter: blur(35px) saturate(140%);
        border: 1px solid rgba(255, 255, 255, 0.02) !important;
        border-top: 1px solid rgba(237, 191, 155, 0.18) !important; /* Bisel melocotón sutil */
        border-left: 1px solid rgba(237, 191, 155, 0.08) !important;
        border-radius: 24px !important;
        padding: 2.2rem !important;
        box-shadow: 
            0 40px 80px rgba(0, 0, 0, 0.65), 
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
        transition: all 0.3s ease;
    }
    div[data-testid="stFileUploader"]:hover {
        background: rgba(18, 20, 26, 0.55) !important;
        border-top: 1px solid rgba(237, 191, 155, 0.28) !important;
    }
    div[data-testid="stFileUploader"] p { color: #8a8c90 !important; }

    /* 3. Barra de Identidad del Cliente (Ahumado Oscuro) */
    .client-badge-bar {
        background: rgba(10, 12, 16, 0.6) !important;
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.01) !important;
        border-top: 1px solid rgba(237, 191, 155, 0.12) !important;
        border-radius: 14px !important;
        padding: 14px 20px !important;
        margin: 1.5rem 0 !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.45) !important;
    }
    .client-name { 
        color: #e2dcd7 !important; 
        font-weight: 800 !important; /* Más jerarquía visual */
        font-size: 1.15rem !important; 
        letter-spacing: 0.02em !important;
    }
    .client-meta { 
        color: #9f9da2 !important; /* Gris suave de excelente contraste */
        font-size: 0.85rem !important;
    }

    /* 4. Tarjetas KPI Premium con Reflejos y Bordes de Acento */
    .kpi-grid-card {
        background: rgba(18, 20, 26, 0.35) !important;
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.01) !important;
        border-top: 1px solid rgba(237, 191, 155, 0.1) !important;
        border-radius: 18px !important;
        padding: 16px 18px !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 110px !important;
        box-shadow: 0 25px 45px rgba(0, 0, 0, 0.5) !important;
        position: relative;
        overflow: hidden;
    }
    
    /* Reflejo biselado de cristal */
    .kpi-grid-card::before {
        content: '';
        position: absolute;
        top: 0; left: -150%; width: 80%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.04), transparent);
        transform: skewX(-25deg);
        pointer-events: none;
    }

    /* Bordes inferiores de acento */
    .kpi-cicladas { border-bottom: 3.5px solid #a0a2a6 !important; } /* Gris apagado */
    .kpi-pagos { border-bottom: 3.5px solid #b08c6a !important; }    /* Melocotón suave */
    .kpi-mora { border-bottom: 3.5px solid #c8521a; }     /* Naranja Calcite en mora */
    .kpi-saldo { border-bottom: 3.5px solid #c8521a; }    /* Naranja Calcite en saldo */

    /* Tipografías y Datos de las Tarjetas */
    .kpi-title { font-size: 11px; font-weight: 600; color: #8a8c90; letter-spacing: 0.05em; text-transform: uppercase; }
    .kpi-value-blue  { font-size: 26px; font-weight: 700; color: #e2dcd7; margin: 4px 0; }
    .kpi-value-green { font-size: 26px; font-weight: 700; color: #edbf9b; margin: 4px 0; }
    .kpi-value-red   { font-size: 26px; font-weight: 700; color: #fd7b41; margin: 4px 0; }
    .kpi-value-pink  { font-size: 26px; font-weight: 700; color: #fd7b41; margin: 4px 0; }
    
    /* Ajustes de contraste para legibilidad de letras pequeñas */
    .kpi-footer { font-size: 11px; color: #9f9da2 !important; }

    /* 5. Botones de Descarga en Acero/Cobre */
    div.stDownloadButton > button {
        background: rgba(18, 20, 26, 0.6) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.02) !important;
        border-top: 1px solid rgba(237, 191, 155, 0.15) !important;
        border-radius: 50px !important;
        color: #be8a68 !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.6rem !important;
        box-shadow: 
            0 12px 24px rgba(0, 0, 0, 0.35), 
            inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
        transition: all 0.2s ease !important;
    }
    div.stDownloadButton > button:hover {
        background: #c8521a !important; /* Glow y color naranja encendido */
        border-color: #c8521a !important;
        color: #ffffff !important;
        transform: translateY(-2px);
        box-shadow: 0 16px 32px rgba(200, 82, 26, 0.35) !important;
    }

    /* 6. Vista del visor de reportes - Fundido sutil (Previene corte tosco) */
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

        # Sección del cliente
        st.divider()
        st.subheader(f"👤 Cliente: {data['nombre']} (Contrato: {data['contrato']})")

        # Fila de métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card-cicladas">
                <div class="metric-lbl">Cuotas Cicladas</div>
                <div class="metric-val-blue">{analysis['cicladas_count']}</div>
                <div class="metric-sub">Vencidas a la fecha</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card-pagos">
                <div class="metric-lbl">Pagos Aplicados</div>
                <div class="metric-val-green">{analysis['pagos_count']}</div>
                <div class="metric-sub">Total: {analysis['total_pagado_str']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            card_class = "metric-card-mora" if analysis['mora_count'] > 0 else "metric-card-ok"
            val_class = "metric-val-red" if analysis['mora_count'] > 0 else "metric-val-green"
            st.markdown(f"""
            <div class="{card_class}">
                <div class="metric-lbl">Cuotas Atrasadas</div>
                <div class="{val_class}">{analysis['mora_count']}</div>
                <div class="metric-sub">{analysis['mora_subtitle']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            card_class = "metric-card-mora" if analysis['mora_count'] > 0 else "metric-card-ok"
            val_class = "metric-val-red" if analysis['mora_count'] > 0 else "metric-val-green"
            st.markdown(f"""
            <div class="{card_class}">
                <div class="metric-lbl">Saldo Actual</div>
                <div class="{val_class}">{data['saldo_actual']}</div>
                <div class="metric-sub">Antes de: {data['pagar_antes_de']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")
        # Fila de botones de descarga principales
        report_base = conversor_core.build_report_basename(data)
        col_btn_pdf, col_btn_img = st.columns(2)

        with col_btn_pdf:
            st.download_button(
                label="📥 Descargar PDF",
                data=pdf_bytes,
                file_name=f"{report_base}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

        with col_btn_img:
            if image_bytes_list:
                img_data = image_bytes_list[0][1]
                st.download_button(
                    label="🖼️ Descargar Imagen",
                    data=img_data,
                    file_name=f"{report_base}.png",
                    mime="image/png",
                    use_container_width=True
                )

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
