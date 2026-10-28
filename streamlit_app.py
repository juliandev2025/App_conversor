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

st.set_page_config(
    page_title="App Conversor - Estado de Cuenta",
    page_icon="📄",
    layout="wide"
)

# Estilos CSS ejecutivos para la interfaz web
st.markdown("""
<style>
    .main-title {
        font-size: 26px;
        font-weight: 800;
        color: #0052cc;
        margin-bottom: 2px;
    }
    .sub-title {
        font-size: 14px;
        color: #475569;
        margin-bottom: 20px;
    }
    .metric-card-cicladas {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-card-pagos {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-card-mora {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-card-ok {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-val-blue { font-size: 26px; font-weight: 800; color: #0284c7; }
    .metric-val-green { font-size: 26px; font-weight: 800; color: #16a34a; }
    .metric-val-red { font-size: 26px; font-weight: 800; color: #dc2626; }
    .metric-lbl { font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; }
    .metric-sub { font-size: 11px; color: #64748b; margin-top: 3px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📄 App Conversor de Cronogramas</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Convierte cronogramas del CRM en Estados de Cuenta Ejecutivos detallados (PDF Oficial, Imagen PNG y TXT).</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Sube uno o varios archivos PDF de Cronograma (`cronograma_*.pdf`)",
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
        # Fila de botones de descarga
        st.write("#### 💾 Opciones de Descarga")
        cols_btn = st.columns(max(3, 2 + len(image_bytes_list)))

        with cols_btn[0]:
            st.download_button(
                label="📥 Descargar PDF Oficial",
                data=pdf_bytes,
                file_name=f"Reporte_Ejecutivo_{data['contrato']}_{data['identificacion']}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        with cols_btn[1]:
            if txt_content:
                st.download_button(
                    label="📝 Descargar TXT",
                    data=txt_content.encode("utf-8-sig"),
                    file_name=f"Reporte_Ejecutivo_{data['contrato']}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

        for idx, (img_name, img_data) in enumerate(image_bytes_list):
            if idx + 2 < len(cols_btn):
                with cols_btn[idx + 2]:
                    label_p = f"🖼️ Descargar Imagen (Pág. {idx+1})" if len(image_bytes_list) > 1 else "🖼️ Descargar Imagen HD"
                    st.download_button(
                        label=label_p,
                        data=img_data,
                        file_name=f"Reporte_Ejecutivo_{data['contrato']}_pag_{idx+1}.png",
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
