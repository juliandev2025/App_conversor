"""
api/index.py
Servidor Web Flask y función Serverless para despliegue en Vercel.
Permite procesar cronogramas vía web, visualizar el reporte y descargar el PDF oficial.
"""

import os
import sys
import io
import tempfile
import base64
from flask import Flask, request, jsonify, render_template_string, send_file, Response

# Asegurar que conversor_core sea importable desde la raíz del proyecto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import conversor_core
try:
    import logo_data
    KREDIYA_LOGO_DATA_URI = logo_data.KREDIYA_LOGO_DATA_URI
except Exception:
    KREDIYA_LOGO_DATA_URI = ""

app = Flask(__name__)

# Plantilla HTML moderna para la interfaz web de Vercel
HTML_INTERFACE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Conversor - Estado de Cuenta Ejecutivo</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        :root {
            --primary: #0052cc;
            --primary-dark: #0747a6;
            --success: #16a34a;
            --danger: #dc2626;
            --slate-900: #0f172a;
            --slate-700: #334155;
            --slate-500: #64748b;
            --slate-200: #e2e8f0;
            --slate-100: #f1f5f9;
            --slate-50: #f8fafc;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f1f5f9;
            color: var(--slate-900);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: #ffffff;
            border-bottom: 1px solid var(--slate-200);
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-logo {
            width: 36px;
            height: 36px;
            background: var(--primary);
            color: #ffffff;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: 800;
        }
        .brand-title {
            font-size: 17px;
            font-weight: 800;
            color: var(--slate-900);
            line-height: 1.2;
        }
        .brand-sub {
            font-size: 12px;
            color: var(--slate-500);
            font-weight: 500;
        }
        .badge-cloud {
            background: #e0f2fe;
            color: #0284c7;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 20px;
        }
        
        main {
            max-width: 1080px;
            margin: 24px auto;
            padding: 0 16px;
            width: 100%;
            flex: 1;
        }

        /* Upload Card */
        .upload-card {
            background: #ffffff;
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
            padding: 36px 24px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .upload-card:hover, .upload-card.dragover {
            border-color: var(--primary);
            background: #f8fafc;
        }
        .upload-icon {
            font-size: 44px;
            margin-bottom: 10px;
        }
        .upload-title {
            font-size: 16px;
            font-weight: 700;
            color: var(--slate-900);
            margin-bottom: 4px;
        }
        .upload-hint {
            font-size: 13px;
            color: var(--slate-500);
            margin-bottom: 14px;
        }
        .btn-select {
            background: var(--primary);
            color: #ffffff;
            border: none;
            padding: 9px 18px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            display: inline-block;
            transition: background 0.2s;
        }
        .btn-select:hover { background: var(--primary-dark); }
        #fileInput { display: none; }

        /* Spinner */
        #loading {
            display: none;
            margin: 20px 0;
            text-align: center;
            font-size: 14px;
            color: var(--primary);
            font-weight: 600;
        }
        .spinner-ring {
            display: inline-block;
            width: 28px;
            height: 28px;
            border: 3px solid rgba(0,82,204,0.2);
            border-radius: 50%;
            border-top-color: var(--primary);
            animation: spin 0.8s linear infinite;
            margin-bottom: 8px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Results Area */
        #resultsArea {
            display: none;
            margin-top: 24px;
        }

        .client-banner {
            background: #ffffff;
            border: 1px solid var(--slate-200);
            border-radius: 8px;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
        }
        .client-meta h3 { font-size: 16px; font-weight: 800; color: var(--slate-900); }
        .client-meta p { font-size: 13px; color: var(--slate-500); }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }
        .kpi-item {
            border-radius: 8px;
            padding: 12px 14px;
        }
        .kpi-item.cicladas { background: #eff6ff; border: 1px solid #bfdbfe; }
        .kpi-item.pagos { background: #f0fdf4; border: 1px solid #bbf7d0; }
        .kpi-item.mora { background: #fef2f2; border: 1px solid #fecaca; }
        .kpi-item.ok { background: #f0fdf4; border: 1px solid #bbf7d0; }
        .kpi-title { font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--slate-700); margin-bottom: 2px; }
        .kpi-val { font-size: 22px; font-weight: 800; line-height: 1.1; }
        .kpi-val.blue { color: #0284c7; }
        .kpi-val.green { color: var(--success); }
        .kpi-val.red { color: var(--danger); }
        .kpi-sub { font-size: 11px; color: var(--slate-500); margin-top: 4px; }

        .action-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
            flex-wrap: wrap;
            align-items: center;
        }
        .btn-action {
            padding: 10px 16px;
            font-size: 13px;
            font-weight: 700;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
            transition: all 0.2s;
        }
        .btn-open-pdf { background: #0052cc; color: #ffffff; }
        .btn-open-pdf:hover { background: #0041a8; }
        .btn-open-img { background: #7c3aed; color: #ffffff; }
        .btn-open-img:hover { background: #6d28d9; }
        .btn-download-pdf { background: #0f172a; color: #ffffff; }
        .btn-download-pdf:hover { background: #1e293b; }
        .btn-download-img { background: #16a34a; color: #ffffff; }
        .btn-download-img:hover { background: #15803d; }
        .btn-download-txt { background: #475569; color: #ffffff; }
        .btn-download-txt:hover { background: #334155; }
        .btn-reset { background: transparent; color: var(--slate-500); border: 1px solid var(--slate-200); }
        .btn-reset:hover { color: var(--slate-900); background: #ffffff; }

        .options-bar {
            background: #ffffff;
            border: 1px solid var(--slate-200);
            border-radius: 8px;
            padding: 12px 18px;
            margin-bottom: 16px;
            display: flex;
            gap: 24px;
            align-items: center;
            flex-wrap: wrap;
        }
        .chk-option {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 600;
            color: var(--slate-700);
            cursor: pointer;
        }
        .chk-option input[type="checkbox"] {
            width: 17px;
            height: 17px;
            cursor: pointer;
            accent-color: var(--primary);
        }

        .preview-box {
            background: #ffffff;
            border: 1px solid var(--slate-200);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        .preview-header {
            background: var(--slate-50);
            border-bottom: 1px solid var(--slate-200);
            padding: 10px 16px;
            font-size: 12px;
            font-weight: 700;
            color: var(--slate-700);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        iframe#previewFrame {
            width: 100%;
            height: 900px;
            border: none;
            display: block;
            background: #ffffff;
        }

        footer {
            text-align: center;
            padding: 16px;
            font-size: 12px;
            color: var(--slate-500);
            border-top: 1px solid var(--slate-200);
            background: #ffffff;
            margin-top: auto;
        }

        @media (max-width: 768px) {
            .kpi-grid { grid-template-columns: 1fr 1fr; }
            .client-banner { flex-direction: column; align-items: flex-start; gap: 8px; }
            iframe#previewFrame { height: 600px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            {% if logo_uri %}
            <img src="{{ logo_uri }}" alt="KrediYA" style="height: 38px; width: auto; object-fit: contain; margin-right: 14px;">
            <div style="border-left: 1px solid var(--slate-200); padding-left: 16px;">
            {% else %}
            <div class="brand-logo">📄</div>
            <div>
            {% endif %}
                <div class="brand-title">App Conversor de Cronogramas</div>
            </div>
        </div>
        <span class="badge-cloud">⚡ Vercel Cloud Ready</span>
    </header>

    <main>
        <!-- Card para Subir Archivo -->
        <div class="upload-card" id="dropZone" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon">📂</div>
            <div class="upload-title">Arrastra el cronograma generado por Admin</div>
            <div class="upload-hint">O haz clic para seleccionar el archivo (<code>cronograma_*.pdf</code>)</div>
            <button class="btn-select" type="button">Seleccionar archivo PDF</button>
            <input type="file" id="fileInput" accept=".pdf" onchange="handleFileSelect(event)">
        </div>

        <div id="loading">
            <div class="spinner-ring"></div>
            <div>Analizando cuotas, pagos y generando reporte oficial en PDF e Imagen HD...</div>
        </div>

        <!-- Área de Resultados -->
        <div id="resultsArea">
            <div class="client-banner">
                <div class="client-meta">
                    <h3 id="resNombre">Cliente</h3>
                    <p id="resSub">Contrato: — | Cédula: — | Saldo Pendiente: —</p>
                </div>
            </div>

            <div class="kpi-grid">
                <div class="kpi-item cicladas">
                    <div class="kpi-title">Cuotas Cicladas</div>
                    <div class="kpi-val blue" id="kpiCicladas">0</div>
                    <div class="kpi-sub">Vencidas a la fecha</div>
                </div>
                <div class="kpi-item pagos">
                    <div class="kpi-title">Pagos Aplicados</div>
                    <div class="kpi-val green" id="kpiPagos">0</div>
                    <div class="kpi-sub" id="kpiPagosSub">Total: $0.00</div>
                </div>
                <div class="kpi-item" id="cardMora">
                    <div class="kpi-title">Cuotas Atrasadas</div>
                    <div class="kpi-val" id="kpiMora">0</div>
                    <div class="kpi-sub" id="kpiMoraSub">Sin mora</div>
                </div>
                <div class="kpi-item" id="cardSaldo">
                    <div class="kpi-title">Saldo Actual</div>
                    <div class="kpi-val" id="kpiSaldo">$0.00</div>
                    <div class="kpi-sub" id="kpiSaldoSub">Pagar antes de: —</div>
                </div>
            </div>

            <div class="action-bar">
                <button class="btn-action btn-open-pdf" onclick="openPdfNewTab()" title="Abre el PDF en una nueva pestaña del navegador">
                    📄 Abrir PDF (Nueva Pestaña)
                </button>
                <button class="btn-action btn-open-img" onclick="openImageNewTab(0)" title="Abre la Imagen HD en una nueva pestaña del navegador">
                    🖼️ Abrir Imagen HD (Nueva Pestaña)
                </button>
                <button class="btn-action btn-download-pdf" onclick="downloadServerPdf()">
                    📥 Descargar PDF
                </button>
                <button class="btn-action btn-download-img" id="btnDlImg" onclick="downloadServerImage(0)">
                    🖼️ Descargar Imagen
                </button>
                <button class="btn-action btn-download-txt" onclick="downloadServerTxt()">
                    📝 Descargar TXT
                </button>
                <button class="btn-action btn-html" onclick="downloadHtml()">
                    🌐 Descargar HTML
                </button>
                <button class="btn-action btn-reset" onclick="resetApp()">
                    🔄 Convertir otro
                </button>
            </div>

            <div class="preview-box">
                <div class="preview-header">
                    <span>👁️ Vista Previa del Reporte Oficial (Formato idéntico a Plantilla)</span>
                    <span style="font-size: 11px; color: var(--slate-500);">Documento vectorial de alta fidelidad</span>
                </div>
                <iframe id="previewFrame"></iframe>
            </div>
        </div>
    </main>

    <footer>
        Sistema de Soporte a Tiendas y Clientes &bull; Desplegado en Vercel
    </footer>

    <script>
        let currentHtml = "";
        let currentContract = "reporte";
        let currentPdfBase64 = null;
        let currentImagesBase64 = [];
        let currentTxt = "";
        let currentBasename = "Reporte_Ejecutivo";

        if (window.pdfjsLib) {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }

        function b64toBlob(b64Data, contentType) {
            const byteCharacters = atob(b64Data);
            const byteArrays = [];
            for (let offset = 0; offset < byteCharacters.length; offset += 512) {
                const slice = byteCharacters.slice(offset, offset + 512);
                const byteNumbers = new Array(slice.length);
                for (let i = 0; i < slice.length; i++) {
                    byteNumbers[i] = slice.charCodeAt(i);
                }
                byteArrays.push(new Uint8Array(byteNumbers));
            }
            return new Blob(byteArrays, { type: contentType });
        }

        function triggerDownload(blob, filename) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 1500);
        }

        async function getOrRenderImageBlob(pageIdx = 0) {
            // 1. Si el servidor ya devolvió la imagen generada en PNG
            if (currentImagesBase64 && currentImagesBase64.length > pageIdx) {
                return b64toBlob(currentImagesBase64[pageIdx], 'image/png');
            }
            // 2. Fallback: renderizar en el navegador con PDF.js en 200 DPI a partir del PDF vectorial
            if (currentPdfBase64 && window.pdfjsLib) {
                try {
                    const rawData = atob(currentPdfBase64);
                    const uint8Array = new Uint8Array(rawData.length);
                    for (let i = 0; i < rawData.length; i++) {
                        uint8Array[i] = rawData.charCodeAt(i);
                    }
                    const loadingTask = pdfjsLib.getDocument({ data: uint8Array });
                    const pdf = await loadingTask.promise;
                    const targetPage = Math.min(pageIdx + 1, pdf.numPages);
                    const page = await pdf.getPage(targetPage);
                    const viewport = page.getViewport({ scale: 200 / 72 }); // 200 DPI
                    const canvas = document.createElement('canvas');
                    const context = canvas.getContext('2d');
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    await page.render({ canvasContext: context, viewport: viewport }).promise;
                    return new Promise((resolve) => {
                        canvas.toBlob((blob) => resolve(blob), 'image/png');
                    });
                } catch (e) {
                    console.error("Error renderizando con pdf.js:", e);
                }
            }
            return null;
        }

        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        });
        ['dragleave', 'drop'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); });
        });
        dropZone.addEventListener('drop', (e) => {
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                processFile(e.dataTransfer.files[0]);
            }
        });

        function handleFileSelect(e) {
            if (e.target.files && e.target.files.length > 0) {
                processFile(e.target.files[0]);
            }
        }

        async function processFile(file) {
            if (!file.name.endsWith('.pdf')) {
                alert("Por favor selecciona un archivo PDF de cronograma válido.");
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('resultsArea').style.display = 'none';

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/api/convert', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.error || "Error al procesar el archivo");
                }

                const res = await response.json();
                currentHtml = res.html;
                currentContract = res.data.contrato || "reporte";
                currentPdfBase64 = res.pdf_base64 || null;
                currentImagesBase64 = res.images_base64 || [];
                currentTxt = res.txt_content || "";
                currentBasename = res.basename || `Reporte_Ejecutivo_${currentContract}`;

                // Actualizar interfaz
                document.getElementById('resNombre').textContent = res.data.nombre;
                document.getElementById('resSub').textContent = 
                    `Contrato: ${res.data.contrato} | Cédula: ${res.data.identificacion} | Saldo Pendiente: ${res.data.saldo_pendiente}`;

                document.getElementById('kpiCicladas').textContent = res.analysis.cicladas_count;
                document.getElementById('kpiPagos').textContent = res.analysis.pagos_count;
                document.getElementById('kpiPagosSub').textContent = `Total: ${res.analysis.total_pagado_str}`;

                const moraCount = res.analysis.mora_count;
                const cardMora = document.getElementById('cardMora');
                const kpiMora = document.getElementById('kpiMora');
                const cardSaldo = document.getElementById('cardSaldo');
                const kpiSaldo = document.getElementById('kpiSaldo');

                if (moraCount > 0) {
                    cardMora.className = 'kpi-item mora';
                    kpiMora.className = 'kpi-val red';
                    cardSaldo.className = 'kpi-item mora';
                    kpiSaldo.className = 'kpi-val red';
                } else {
                    cardMora.className = 'kpi-item ok';
                    kpiMora.className = 'kpi-val green';
                    cardSaldo.className = 'kpi-item ok';
                    kpiSaldo.className = 'kpi-val green';
                }

                kpiMora.textContent = moraCount;
                document.getElementById('kpiMoraSub').textContent = res.analysis.mora_subtitle;

                kpiSaldo.textContent = res.data.saldo_actual;
                document.getElementById('kpiSaldoSub').textContent = `Pagar antes de: ${res.data.pagar_antes_de}`;

                // Cargar iframe
                const frame = document.getElementById('previewFrame');
                frame.srcdoc = currentHtml;

                document.getElementById('loading').style.display = 'none';
                document.getElementById('resultsArea').style.display = 'block';

            } catch (err) {
                document.getElementById('loading').style.display = 'none';
                alert("Error: " + err.message);
            }
        }

        function openPdfNewTab() {
            if (currentPdfBase64) {
                const blob = b64toBlob(currentPdfBase64, 'application/pdf');
                const url = URL.createObjectURL(blob);
                window.open(url, '_blank');
            } else if (currentContract) {
                window.open(`/api/view_pdf?contract=${encodeURIComponent(currentContract)}`, '_blank');
            }
        }

        async function openImageNewTab(page = 0) {
            const blob = await getOrRenderImageBlob(page);
            if (blob) {
                const url = URL.createObjectURL(blob);
                window.open(url, '_blank');
            } else if (currentContract) {
                window.open(`/api/view_image?contract=${encodeURIComponent(currentContract)}&page=${page}`, '_blank');
            } else {
                alert("No se pudo generar la imagen para visualización.");
            }
        }

        function downloadServerPdf() {
            if (currentPdfBase64) {
                const blob = b64toBlob(currentPdfBase64, 'application/pdf');
                triggerDownload(blob, `${currentBasename}.pdf`);
            } else if (currentContract) {
                window.location.href = `/api/download_pdf?contract=${encodeURIComponent(currentContract)}`;
            }
        }

        async function downloadServerImage(page = 0) {
            const btn = document.getElementById('btnDlImg');
            const originalText = btn ? btn.textContent : '';
            if (btn) btn.textContent = '⏳ Preparando imagen...';
            try {
                const blob = await getOrRenderImageBlob(page);
                if (blob) {
                    triggerDownload(blob, `${currentBasename}_pagina_${page + 1}.png`);
                } else if (currentContract) {
                    window.location.href = `/api/download_image?contract=${encodeURIComponent(currentContract)}&page=${page}`;
                } else {
                    alert("No se pudo generar la imagen.");
                }
            } finally {
                if (btn) btn.textContent = originalText;
            }
        }

        function downloadServerTxt() {
            if (currentTxt) {
                const blob = new Blob([currentTxt], { type: 'text/plain;charset=utf-8' });
                triggerDownload(blob, `${currentBasename}.txt`);
            } else if (currentContract) {
                window.location.href = `/api/download_txt?contract=${encodeURIComponent(currentContract)}`;
            }
        }

        function downloadHtml() {
            if (!currentHtml) return;
            const blob = new Blob([currentHtml], { type: 'text/html' });
            triggerDownload(blob, `${currentBasename}.html`);
        }

        function resetApp() {
            document.getElementById('fileInput').value = "";
            document.getElementById('resultsArea').style.display = 'none';
            document.getElementById('dropZone').style.display = 'block';
        }
    </script>
</body>
</html>
"""

# Almacén en memoria temporal para la sesión de descarga
LAST_PROCESSED = {}

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_INTERFACE, logo_uri=KREDIYA_LOGO_DATA_URI)

@app.route("/api/convert", methods=["POST"])
def convert_cronograma():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    try:
        file_bytes = file.read()
        data = conversor_core.extract_cronograma_data(file_bytes)
        analysis = conversor_core.analyze_and_classify_movements(data)
        html_content = conversor_core.render_html_report(data, analysis)

        # Generar PDF en buffer de memoria con ReportLab (independiente de navegadores)
        pdf_buffer = io.BytesIO()
        conversor_core.generate_pdf_reportlab(data, analysis, pdf_buffer)
        pdf_buffer.seek(0)
        pdf_bytes = pdf_buffer.getvalue()

        # Guardar en caché rápida para descarga directa con nombre institucional
        contract_key = data.get("contrato", "reporte")
        report_base = conversor_core.build_report_basename(data)

        # Generar imágenes PNG en memoria (200 DPI) con pypdfium2 si está disponible
        images_list = []
        filenames_images = []
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(pdf_bytes)
            for idx, page in enumerate(doc):
                img_buf = io.BytesIO()
                page.render(scale=200/72).to_pil().save(img_buf, format="PNG")
                images_list.append(img_buf.getvalue())
                filenames_images.append(f"{report_base}_pagina_{idx+1}.png")
            doc.close()
        except Exception as e_img:
            print("Aviso al generar imágenes:", e_img)

        # Generar texto plano
        txt_content = conversor_core.generate_txt_report(data, analysis)

        # Convertir a base64 para entrega instantánea al cliente (sin roundtrips ni pérdida de memoria)
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
        images_b64 = [base64.b64encode(img).decode("ascii") for img in images_list]

        # Guardar en caché de memoria
        LAST_PROCESSED[contract_key] = {
            "pdf_bytes": pdf_bytes,
            "data": data,
            "filename_pdf": f"{report_base}.pdf",
            "images": images_list,
            "filename_images": filenames_images,
            "txt_content": txt_content,
            "filename_txt": f"{report_base}.txt"
        }

        # Guardar también en disco temporal /tmp para que sobreviva en entornos serverless
        try:
            tmp_dir = tempfile.gettempdir()
            with open(os.path.join(tmp_dir, f"{contract_key}.pdf"), "wb") as f:
                f.write(pdf_bytes)
            with open(os.path.join(tmp_dir, f"{contract_key}_base.txt"), "w", encoding="utf-8") as f:
                f.write(report_base)
            for idx, img in enumerate(images_list):
                with open(os.path.join(tmp_dir, f"{contract_key}_img_{idx}.png"), "wb") as f:
                    f.write(img)
            with open(os.path.join(tmp_dir, f"{contract_key}.txt"), "w", encoding="utf-8-sig") as f:
                f.write(txt_content)
        except Exception as e_tmp:
            print("Aviso al escribir en /tmp:", e_tmp)

        return jsonify({
            "success": True,
            "data": data,
            "analysis": {
                "cicladas_count": analysis["cicladas_count"],
                "pagos_count": analysis["pagos_count"],
                "total_pagado_str": analysis["total_pagado_str"],
                "mora_count": analysis["mora_count"],
                "mora_subtitle": analysis["mora_subtitle"],
                "revision_texto": analysis["revision_texto"]
            },
            "html": html_content,
            "basename": report_base,
            "pdf_base64": pdf_b64,
            "images_base64": images_b64,
            "txt_content": txt_content,
            "num_images": len(images_list)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/view_pdf", methods=["GET"])
def view_pdf():
    contract_key = request.args.get("contract", "reporte")
    item = LAST_PROCESSED.get(contract_key)
    pdf_bytes = item["pdf_bytes"] if item and "pdf_bytes" in item else None
    filename_pdf = item["filename_pdf"] if item and "filename_pdf" in item else f"Reporte_Ejecutivo_{contract_key}.pdf"
    
    if not pdf_bytes:
        tmp_pdf = os.path.join(tempfile.gettempdir(), f"{contract_key}.pdf")
        if os.path.exists(tmp_pdf):
            with open(tmp_pdf, "rb") as f:
                pdf_bytes = f.read()
            tmp_base = os.path.join(tempfile.gettempdir(), f"{contract_key}_base.txt")
            if os.path.exists(tmp_base):
                with open(tmp_base, "r", encoding="utf-8") as f:
                    filename_pdf = f"{f.read().strip()}.pdf"

    if not pdf_bytes:
        return "El archivo no se encuentra en memoria. Por favor vuelve a procesar el cronograma.", 404

    resp = Response(pdf_bytes, mimetype="application/pdf")
    resp.headers["Content-Disposition"] = f'inline; filename="{filename_pdf}"'
    return resp

@app.route("/api/view_image", methods=["GET"])
def view_image():
    contract_key = request.args.get("contract", "reporte")
    page_idx = int(request.args.get("page", 0))
    item = LAST_PROCESSED.get(contract_key)
    
    img_bytes = None
    filename_img = f"Reporte_Ejecutivo_{contract_key}_pagina_{page_idx+1}.png"
    if item and "images" in item and item["images"]:
        idx = min(page_idx, len(item["images"]) - 1)
        img_bytes = item["images"][idx]
        if "filename_images" in item and idx < len(item["filename_images"]):
            filename_img = item["filename_images"][idx]
            
    if not img_bytes:
        tmp_img = os.path.join(tempfile.gettempdir(), f"{contract_key}_img_{page_idx}.png")
        if os.path.exists(tmp_img):
            with open(tmp_img, "rb") as f:
                img_bytes = f.read()

    if not img_bytes:
        # Intentar generar imagen al vuelo a partir del PDF
        pdf_bytes = item["pdf_bytes"] if item and "pdf_bytes" in item else None
        if not pdf_bytes:
            tmp_pdf = os.path.join(tempfile.gettempdir(), f"{contract_key}.pdf")
            if os.path.exists(tmp_pdf):
                with open(tmp_pdf, "rb") as f:
                    pdf_bytes = f.read()
        if pdf_bytes:
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(pdf_bytes)
                if len(doc) > 0:
                    idx = min(page_idx, len(doc) - 1)
                    img_buf = io.BytesIO()
                    doc[idx].render(scale=200/72).to_pil().save(img_buf, format="PNG")
                    img_bytes = img_buf.getvalue()
                doc.close()
            except Exception as e_reg:
                print("Error regenerando imagen:", e_reg)

    if not img_bytes:
        return "No hay imagen disponible.", 404

    resp = Response(img_bytes, mimetype="image/png")
    resp.headers["Content-Disposition"] = f'inline; filename="{filename_img}"'
    return resp

@app.route("/api/download_pdf", methods=["GET"])
def download_pdf():
    contract_key = request.args.get("contract", "reporte")
    item = LAST_PROCESSED.get(contract_key)
    pdf_bytes = item["pdf_bytes"] if item and "pdf_bytes" in item else None
    filename_pdf = item["filename_pdf"] if item and "filename_pdf" in item else f"Reporte_Ejecutivo_{contract_key}.pdf"
    
    if not pdf_bytes:
        tmp_pdf = os.path.join(tempfile.gettempdir(), f"{contract_key}.pdf")
        if os.path.exists(tmp_pdf):
            with open(tmp_pdf, "rb") as f:
                pdf_bytes = f.read()
            tmp_base = os.path.join(tempfile.gettempdir(), f"{contract_key}_base.txt")
            if os.path.exists(tmp_base):
                with open(tmp_base, "r", encoding="utf-8") as f:
                    filename_pdf = f"{f.read().strip()}.pdf"

    if not pdf_bytes:
        return "El archivo no se encuentra en memoria. Por favor vuelve a procesar el cronograma.", 404

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename_pdf
    )

@app.route("/api/download_image", methods=["GET"])
def download_image():
    contract_key = request.args.get("contract", "reporte")
    page_idx = int(request.args.get("page", 0))
    item = LAST_PROCESSED.get(contract_key)
    
    img_bytes = None
    filename_img = f"Reporte_Ejecutivo_{contract_key}_pagina_{page_idx+1}.png"
    if item and "images" in item and item["images"]:
        idx = min(page_idx, len(item["images"]) - 1)
        img_bytes = item["images"][idx]
        if "filename_images" in item and idx < len(item["filename_images"]):
            filename_img = item["filename_images"][idx]
            
    if not img_bytes:
        tmp_img = os.path.join(tempfile.gettempdir(), f"{contract_key}_img_{page_idx}.png")
        if os.path.exists(tmp_img):
            with open(tmp_img, "rb") as f:
                img_bytes = f.read()

    if not img_bytes:
        pdf_bytes = item["pdf_bytes"] if item and "pdf_bytes" in item else None
        if not pdf_bytes:
            tmp_pdf = os.path.join(tempfile.gettempdir(), f"{contract_key}.pdf")
            if os.path.exists(tmp_pdf):
                with open(tmp_pdf, "rb") as f:
                    pdf_bytes = f.read()
        if pdf_bytes:
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(pdf_bytes)
                if len(doc) > 0:
                    idx = min(page_idx, len(doc) - 1)
                    img_buf = io.BytesIO()
                    doc[idx].render(scale=200/72).to_pil().save(img_buf, format="PNG")
                    img_bytes = img_buf.getvalue()
                doc.close()
            except Exception as e_reg:
                print("Error regenerando imagen:", e_reg)

    if not img_bytes:
        return "No hay imagen disponible.", 404

    return send_file(
        io.BytesIO(img_bytes),
        mimetype="image/png",
        as_attachment=True,
        download_name=filename_img
    )

@app.route("/api/download_txt", methods=["GET"])
def download_txt():
    contract_key = request.args.get("contract", "reporte")
    item = LAST_PROCESSED.get(contract_key)
    txt_content = item["txt_content"] if item and "txt_content" in item else None
    filename_txt = item["filename_txt"] if item and "filename_txt" in item else f"Reporte_Ejecutivo_{contract_key}.txt"

    if not txt_content:
        tmp_txt = os.path.join(tempfile.gettempdir(), f"{contract_key}.txt")
        if os.path.exists(tmp_txt):
            with open(tmp_txt, "r", encoding="utf-8-sig") as f:
                txt_content = f.read()
            tmp_base = os.path.join(tempfile.gettempdir(), f"{contract_key}_base.txt")
            if os.path.exists(tmp_base):
                with open(tmp_base, "r", encoding="utf-8") as f:
                    filename_txt = f"{f.read().strip()}.txt"

    if not txt_content:
        return "No hay archivo TXT disponible.", 404

    return send_file(
        io.BytesIO(txt_content.encode("utf-8-sig")),
        mimetype="text/plain",
        as_attachment=True,
        download_name=filename_txt
    )

# Para ejecución local con 'python api/index.py'
if __name__ == "__main__":
    print("Iniciando servidor local en http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
