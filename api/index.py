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
            --bg-dark: #0d0e11;
            --text-main: #e2dcd7;
            --text-muted: #9f9da2;
            --text-dim: #8a8c90;
            --accent-orange: #fd7b41;
            --accent-peach: #edbf9b;
            --accent-copper: #c8521a;
            --accent-steel: #a0a2a6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #0d0e11;
            background-image: radial-gradient(circle at 10% 20%, rgba(15, 17, 22, 0.95) 0%, #0d0e11 100%);
            background-attachment: fixed;
            color: #e2dcd7;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        /* ── Orbes Calcite de la GPU Difuminados ── */
        .ambient-orbs-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            overflow: hidden;
            z-index: 0;
        }
        .orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.95;
            mix-blend-mode: screen;
            animation-iteration-count: infinite;
            animation-direction: alternate;
            animation-timing-function: ease-in-out;
        }
        /* Orbe 1: Naranja Intenso Encendido Superior Izquierdo */
        .orb-1 {
            width: 620px;
            height: 620px;
            top: -6%;
            left: -12%;
            background: radial-gradient(circle, rgba(255, 115, 45, 0.9) 0%, rgba(245, 90, 25, 0.5) 40%, rgba(245, 90, 25, 0.12) 65%, transparent 75%);
            animation: orbFloat1 20s infinite alternate;
        }
        /* Orbe 2: Halo Blanco/Acero Glacial Superior Derecho */
        .orb-2 {
            width: 480px;
            height: 480px;
            top: 5%;
            right: 8%;
            background: radial-gradient(circle, rgba(185, 205, 225, 0.45) 0%, rgba(140, 160, 180, 0.18) 45%, transparent 72%);
            animation: orbFloat2 24s infinite alternate;
        }
        /* Orbe 3: Melocotón Crema Suave e Iluminado Inferior Izquierdo */
        .orb-3 {
            width: 600px;
            height: 600px;
            bottom: -8%;
            left: -6%;
            background: radial-gradient(circle, rgba(255, 210, 175, 0.75) 0%, rgba(240, 175, 135, 0.38) 45%, rgba(240, 175, 135, 0.08) 68%, transparent 78%);
            animation: orbFloat3 22s infinite alternate;
        }
        /* Orbe 4: Cobre / Ámbar Encendido Inferior Derecho */
        .orb-4 {
            width: 640px;
            height: 640px;
            bottom: -2%;
            right: -8%;
            background: radial-gradient(circle, rgba(245, 110, 40, 0.75) 0%, rgba(210, 80, 25, 0.35) 45%, rgba(210, 80, 25, 0.08) 68%, transparent 78%);
            animation: orbFloat4 18s infinite alternate;
        }

        @keyframes orbFloat1 {
            0% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(50px, 40px) scale(1.06); }
            100% { transform: translate(-30px, 50px) scale(0.95); }
        }
        @keyframes orbFloat2 {
            0% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(-60px, 45px) scale(1.1); }
            100% { transform: translate(-30px, -40px) scale(0.92); }
        }
        @keyframes orbFloat3 {
            0% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(55px, -45px) scale(1.05); }
            100% { transform: translate(30px, 25px) scale(0.95); }
        }
        @keyframes orbFloat4 {
            0% { transform: translate(0, 0) scale(0.95); }
            100% { transform: translate(-35px, 30px) scale(1.08); }
        }

        /* ── Header ── */
        header {
            position: relative;
            z-index: 10;
            background: rgba(13, 14, 17, 0.65);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            border-top: 1px solid rgba(237, 191, 155, 0.08);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
            padding: 16px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-logo-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 4px 12px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
        }
        .brand-logo {
            width: 38px;
            height: 38px;
            background: #c8521a;
            color: #ffffff;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: 800;
        }
        .brand-title {
            font-size: 18px;
            font-weight: 800;
            color: #e2dcd7;
            letter-spacing: -0.01em;
        }
        
        main {
            max-width: 1100px;
            margin: 32px auto;
            padding: 0 20px;
            width: 100%;
            flex: 1;
            position: relative;
            z-index: 2;
        }

        /* ── Card para Subir Archivo - Cristal Ahumado con Bisel Melocotón ── */
        .upload-card {
            background: rgba(22, 25, 33, 0.38);
            backdrop-filter: blur(28px) saturate(130%);
            -webkit-backdrop-filter: blur(28px) saturate(130%);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-top: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 26px;
            padding: 48px 28px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.18);
            position: relative;
            overflow: hidden;
        }
        .upload-card:hover, .upload-card.dragover {
            background: rgba(26, 30, 40, 0.48);
            border-color: rgba(255, 255, 255, 0.25);
            border-top: 1px solid rgba(255, 255, 255, 0.45);
            transform: translateY(-2px);
        }
        .upload-icon {
            font-size: 48px;
            margin-bottom: 12px;
            filter: drop-shadow(0 4px 15px rgba(0, 0, 0, 0.5));
        }
        .upload-title {
            font-size: 18px;
            font-weight: 700;
            color: #e2dcd7;
            margin-bottom: 6px;
        }
        .upload-hint {
            font-size: 13px;
            color: #8a8c90;
            margin-bottom: 18px;
        }
        .upload-hint code {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 3px 8px;
            border-radius: 6px;
            color: #e2dcd7;
            font-size: 12px;
        }
        .btn-select {
            background: linear-gradient(180deg, #d35922 0%, #b84312 100%);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-top: 1px solid rgba(255, 255, 255, 0.35);
            padding: 11px 28px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 50px;
            cursor: pointer;
            display: inline-block;
            transition: all 0.25s ease;
            box-shadow: 0 10px 25px rgba(200, 80, 25, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }
        .btn-select:hover {
            background: linear-gradient(180deg, #e4662d 0%, #c44a16 100%);
            transform: translateY(-2px);
            box-shadow: 0 14px 30px rgba(230, 90, 30, 0.5);
        }
        #fileInput { display: none; }

        /* ── Spinner ── */
        #loading {
            display: none;
            margin: 28px 0;
            text-align: center;
            font-size: 14px;
            color: #fd7b41;
            font-weight: 600;
        }
        .spinner-ring {
            display: inline-block;
            width: 34px;
            height: 34px;
            border: 3px solid rgba(253, 123, 65, 0.2);
            border-radius: 50%;
            border-top-color: #fd7b41;
            animation: spin 0.8s linear infinite;
            margin-bottom: 12px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ── Área de Resultados ── */
        #resultsArea {
            display: none;
            margin-top: 26px;
        }

        /* 3. Barra de Identidad del Cliente (Ahumado Oscuro) */
        .client-banner {
            background: rgba(22, 25, 33, 0.38);
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-top: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 18px;
            padding: 16px 24px;
            margin-bottom: 18px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.12);
        }
        .client-meta h3 {
            font-size: 1.15rem;
            font-weight: 800;
            color: #e2dcd7;
            letter-spacing: 0.02em;
            margin-bottom: 4px;
        }
        .client-meta p {
            font-size: 0.85rem;
            color: #9f9da2;
        }

        /* 4. Tarjetas KPI Premium con Reflejos y Bordes de Acento */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 20px;
        }
        .kpi-item {
            background: rgba(22, 25, 33, 0.38);
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-top: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 20px;
            padding: 18px 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 115px;
            box-shadow: 0 25px 45px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.14);
            position: relative;
            overflow: hidden;
            transition: transform 0.2s ease;
        }
        .kpi-item:hover {
            transform: translateY(-2px);
        }
        .kpi-item.pagos {
            background: #efbe98;
            border: 1px solid rgba(255, 255, 255, 0.45);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.5);
        }
        .kpi-item.pagos .kpi-title { color: #523e32 !important; }
        .kpi-item.pagos .kpi-val { color: #1c1511 !important; }
        .kpi-item.pagos .kpi-sub { color: #5a463a !important; }
        
        .kpi-val.red { color: #fd7b41 !important; }

        .kpi-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #8a8c90;
            margin-bottom: 4px;
        }
        .kpi-val {
            font-size: 26px;
            font-weight: 700;
            line-height: 1.1;
            margin: 4px 0;
        }
        .kpi-val.blue {
            color: #e2dcd7;
        }
        .kpi-val.green {
            color: #edbf9b;
        }
        .kpi-val.red {
            color: #fd7b41;
        }
        .kpi-sub {
            font-size: 11px;
            color: #9f9da2;
            margin-top: 5px;
        }

        /* 5. Botones de Descarga en Acero/Cobre */
        .action-bar {
            display: flex;
            gap: 14px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            align-items: center;
        }
        .btn-action {
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 50px;
            font-weight: 600;
            font-size: 13px;
            padding: 0.65rem 1.9rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
            transition: all 0.2s ease;
        }
        .btn-download-pdf {
            background: linear-gradient(180deg, #d35922 0%, #b84312 100%);
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-top: 1px solid rgba(255, 255, 255, 0.4);
            color: #ffffff;
            box-shadow: 0 12px 28px rgba(200, 80, 25, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.25);
        }
        .btn-download-pdf:hover {
            background: linear-gradient(180deg, #e4662d 0%, #c44a16 100%);
            transform: translateY(-2px);
            box-shadow: 0 16px 34px rgba(230, 90, 30, 0.55);
        }
        .btn-download-img {
            background: rgba(30, 34, 44, 0.45);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-top: 1px solid rgba(255, 255, 255, 0.3);
            color: #f0ece9;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15);
        }
        .btn-download-img:hover {
            background: rgba(38, 44, 58, 0.6);
            border-color: rgba(255, 255, 255, 0.3);
            color: #ffffff;
            transform: translateY(-2px);
        }

        /* 6. Vista del visor de reportes - Fundido sutil */
        .preview-box {
            box-shadow: 0 -15px 40px rgba(10, 13, 22, 0.9);
            border-top: 1px solid rgba(237, 191, 155, 0.05);
            border-radius: 24px 24px 0px 0px;
            background-color: #ffffff;
            overflow: hidden;
            padding-top: 5px;
        }
        iframe#previewFrame {
            width: 100%;
            height: 900px;
            border: none;
            display: block;
            background: #ffffff;
        }

        footer {
            position: relative;
            z-index: 10;
            text-align: center;
            padding: 20px;
            font-size: 12px;
            color: #8a8c90;
            border-top: 1px solid rgba(255, 255, 255, 0.03);
            background: rgba(10, 12, 16, 0.6);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
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
    <!-- Orbes de Iluminación Ambientales (Liquid Glass Premium) -->
    <div class="ambient-orbs-container" aria-hidden="true">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
        <div class="orb orb-4"></div>
    </div>

    <header>
        <div class="brand">
            {% if logo_uri %}
            <div class="brand-logo-card">
                <img src="{{ logo_uri }}" alt="KrediYA" style="height: 32px; width: auto; object-fit: contain;">
            </div>
            <div style="border-left: 1px solid rgba(255, 255, 255, 0.12); padding-left: 16px;">
            {% else %}
            <div class="brand-logo">📄</div>
            <div>
            {% endif %}
                <div class="brand-title">App Conversor de Cronogramas</div>
            </div>
        </div>
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
                <button class="btn-action btn-download-pdf" onclick="downloadServerPdf()">
                    📥 Descargar PDF
                </button>
                <button class="btn-action btn-download-img" id="btnDlImg" onclick="downloadServerImage(0)">
                    🖼️ Descargar Imagen
                </button>
            </div>

            <div class="preview-box">
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
    rendered = render_template_string(HTML_INTERFACE, logo_uri=KREDIYA_LOGO_DATA_URI)
    resp = Response(rendered, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

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
