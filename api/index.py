"""
api/index.py
Servidor Web Flask y función Serverless para despliegue en Vercel.
Permite procesar cronogramas vía web, visualizar el reporte y descargar el PDF oficial.
"""

import os
import sys
import io
import tempfile
from flask import Flask, request, jsonify, render_template_string, send_file, Response

# Asegurar que conversor_core sea importable desde la raíz del proyecto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import conversor_core

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
        .btn-print { background: var(--primary); color: #ffffff; }
        .btn-print:hover { background: var(--primary-dark); }
        .btn-pdf { background: #0f172a; color: #ffffff; }
        .btn-pdf:hover { background: #1e293b; }
        .btn-html { background: #ffffff; color: var(--slate-700); border: 1px solid #cbd5e1; }
        .btn-html:hover { background: var(--slate-50); }
        .btn-reset { background: transparent; color: var(--slate-500); border: 1px solid transparent; }
        .btn-reset:hover { color: var(--slate-900); }

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
            <div class="brand-logo">📄</div>
            <div>
                <div class="brand-title">App Conversor de Cronogramas</div>
                <div class="brand-sub">Estado de Cuenta Ejecutivo - Formato Institucional</div>
            </div>
        </div>
        <span class="badge-cloud">⚡ Vercel Cloud Ready</span>
    </header>

    <main>
        <!-- Card para Subir Archivo -->
        <div class="upload-card" id="dropZone" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon">📂</div>
            <div class="upload-title">Arrastra aquí el cronograma PDF descargado del CRM</div>
            <div class="upload-hint">O haz clic para seleccionar el archivo (<code>cronograma_*.pdf</code>)</div>
            <button class="btn-select" type="button">Seleccionar archivo PDF</button>
            <input type="file" id="fileInput" accept=".pdf" onchange="handleFileSelect(event)">
        </div>

        <div id="loading">
            <div class="spinner-ring"></div>
            <div>Analizando cuotas, pagos y generando reporte oficial...</div>
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
                <button class="btn-action btn-print" onclick="printReport()">
                    🖨️ Imprimir / Guardar como PDF
                </button>
                <button class="btn-action btn-pdf" onclick="downloadServerPdf()">
                    📥 Descargar PDF (ReportLab)
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
        let currentPdfBytes = null;

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

        function printReport() {
            const frame = document.getElementById('previewFrame');
            if (frame && frame.contentWindow) {
                frame.contentWindow.focus();
                frame.contentWindow.print();
            }
        }

        async function downloadServerPdf() {
            if (!currentContract) return;
            window.location.href = `/api/download_pdf?contract=${encodeURIComponent(currentContract)}`;
        }

        function downloadHtml() {
            if (!currentHtml) return;
            const blob = new Blob([currentHtml], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Reporte_Ejecutivo_${currentContract}.html`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
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
    return render_template_string(HTML_INTERFACE)

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

        # Guardar en caché rápida para descarga directa
        contract_key = data.get("contrato", "reporte")
        LAST_PROCESSED[contract_key] = {
            "pdf_bytes": pdf_buffer.getvalue(),
            "data": data,
            "filename": f"Reporte_Ejecutivo_{contract_key}.pdf"
        }

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
            "html": html_content
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download_pdf", methods=["GET"])
def download_pdf():
    contract_key = request.args.get("contract", "reporte")
    item = LAST_PROCESSED.get(contract_key)
    if not item:
        return "El archivo no se encuentra en memoria. Por favor vuelve a procesar el cronograma.", 404

    return send_file(
        io.BytesIO(item["pdf_bytes"]),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=item["filename"]
    )

# Para ejecución local con 'python api/index.py'
if __name__ == "__main__":
    print("Iniciando servidor local en http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
