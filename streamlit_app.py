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
    /* Estilo Liquid Glass Premium & Fondo Dark Blue-Grey */
    .stApp {
        background-color: #0b0f19 !important;
        background-image: 
            radial-gradient(ellipse 90% 60% at 50% -15%, #152238 0%, transparent 80%),
            radial-gradient(circle at 100% 100%, #0d1527 0%, transparent 50%),
            linear-gradient(180deg, #090d16 0%, #0b0f19 50%, #080c14 100%) !important;
        color: #f8fafc !important;
    }
    .main-title {
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
    }
    .sub-title {
        font-size: 14px;
        color: #94a3b8;
        margin-bottom: 20px;
    }
    .metric-card-cicladas {
        background: rgba(14, 165, 233, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        backdrop-filter: blur(20px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    .metric-card-pagos {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(74, 222, 128, 0.25);
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        backdrop-filter: blur(20px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    .metric-card-mora {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(248, 113, 113, 0.35);
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        backdrop-filter: blur(20px);
        box-shadow: 0 10px 25px rgba(239, 68, 68, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    .metric-card-ok {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(74, 222, 128, 0.25);
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        backdrop-filter: blur(20px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    .metric-val-blue { font-size: 26px; font-weight: 800; color: #38bdf8; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4); }
    .metric-val-green { font-size: 26px; font-weight: 800; color: #4ade80; text-shadow: 0 0 15px rgba(74, 222, 128, 0.4); }
    .metric-val-red { font-size: 26px; font-weight: 800; color: #f87171; text-shadow: 0 0 15px rgba(248, 113, 113, 0.4); }
    .metric-lbl { font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-sub { font-size: 11px; color: #64748b; margin-top: 3px; }
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
        # Botones para abrir directamente en nueva pestaña del navegador
        st.write("#### ⚡ Acceso Rápido (Nueva Pestaña del Navegador)")
        open_c1, open_c2 = st.columns(2)
        with open_c1:
            import base64
            b64_pdf = base64.b64encode(pdf_bytes).decode()
            st.markdown(
                f'<a href="data:application/pdf;base64,{b64_pdf}" target="_blank" '
                f'style="display:block;padding:10px 16px;background:#0052cc;color:#ffffff;border-radius:6px;font-weight:700;text-decoration:none;text-align:center;">'
                f'📄 Abrir PDF Oficial en Nueva Pestaña</a>',
                unsafe_allow_html=True
            )
        with open_c2:
            if image_bytes_list:
                import base64
                b64_img = base64.b64encode(image_bytes_list[0][1]).decode()
                st.markdown(
                    f'<a href="data:image/png;base64,{b64_img}" target="_blank" '
                    f'style="display:block;padding:10px 16px;background:#7c3aed;color:#ffffff;border-radius:6px;font-weight:700;text-decoration:none;text-align:center;">'
                    f'🖼️ Abrir Imagen HD en Nueva Pestaña</a>',
                    unsafe_allow_html=True
                )

        st.write("")
        # Fila de botones de descarga
        st.write("#### 💾 Opciones de Descarga")
        report_base = conversor_core.build_report_basename(data)
        cols_btn = st.columns(max(3, 2 + len(image_bytes_list)))

        with cols_btn[0]:
            st.download_button(
                label="📥 Descargar PDF Oficial",
                data=pdf_bytes,
                file_name=f"{report_base}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        with cols_btn[1]:
            if txt_content:
                st.download_button(
                    label="📝 Descargar TXT",
                    data=txt_content.encode("utf-8-sig"),
                    file_name=f"{report_base}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

        for idx, (img_name, img_data) in enumerate(image_bytes_list):
            if idx + 2 < len(cols_btn):
                with cols_btn[idx + 2]:
                    label_p = f"🖼️ Descargar Imagen (Pág. {idx+1})" if len(image_bytes_list) > 1 else "🖼️ Descargar Imagen HD"
                    file_name_img = f"{report_base}_pagina_{idx+1}.png" if len(image_bytes_list) > 1 else f"{report_base}.png"
                    st.download_button(
                        label=label_p,
                        data=img_data,
                        file_name=file_name_img,
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
