"""
conversor_core.py
Motor de extracción, análisis financiero y generación de Reporte PDF Ejecutivo.
Formato idéntico a PLANTILLA.pdf. Compatible con Windows y entornos Serverless (Vercel).
"""

import io
import os
import re
import shutil
import subprocess
from datetime import datetime
import pdfplumber

# Imports para ReportLab (fallback universal sin navegador)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

def parse_currency(val_str):
    if not val_str:
        return 0.0
    cleaned = re.sub(r"[^\d.,]", "", val_str)
    if not cleaned:
        return 0.0
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(".") > cleaned.rfind(","):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except:
        return 0.0

def format_currency(val):
    return f"${val:,.2f}"

def parse_date(d_str):
    if not d_str:
        return None
    cl = d_str.split()[0].replace(',', '').strip()
    p = cl.split('/')
    if len(p) == 3:
        try:
            d, m, y = int(p[0]), int(p[1]), int(p[2])
            if y < 100:
                y += 2000
            return datetime(y, m, d)
        except:
            return None
    return None

def extract_cronograma_data(pdf_path_or_bytes):
    """Extrae texto, campos principales y filas de tabla del cronograma PDF."""
    data = {
        "fecha_consulta": "",
        "identificacion": "N/A",
        "nombre": "N/A",
        "contrato": "N/A",
        "saldo_pendiente": "$0.00",
        "saldo_actual": "$0.00",
        "proximo_pago": "$0.00",
        "pagar_antes_de": "N/A",
        "filas": []
    }

    if isinstance(pdf_path_or_bytes, bytes):
        pdf_file = io.BytesIO(pdf_path_or_bytes)
    else:
        pdf_file = pdf_path_or_bytes

    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    clean = [c.strip() if c else "" for c in row]
                    if not clean or clean[0].lower() in ["concepto", "tipo", ""]:
                        continue
                    if len(clean) >= 5 and any(k in clean[0] for k in ["Cuota", "Pago", "Intento"]):
                        data["filas"].append(clean)

    # Expresiones regulares para metadatos
    m_id = re.search(r"Identificaci[oó]n:\s*([0-9]+)", full_text, re.IGNORECASE)
    if m_id: data["identificacion"] = m_id.group(1).strip()

    m_nom = re.search(r"Nombre:\s*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?)(?=\s+Saldo\s*actual|\s+Contrato|\r|\n|$)", full_text, re.IGNORECASE)
    if m_nom: data["nombre"] = m_nom.group(1).strip()

    m_con = re.search(r"Contrato\s*(?:No\.?)?:?\s*([a-zA-Z0-9]+)", full_text, re.IGNORECASE)
    if m_con: data["contrato"] = m_con.group(1).strip()

    m_spend = re.search(r"Saldo\s*pendiente(?:\s*hasta\s*fin\s*de\s*contrato)?:?\s*(\$[\s\d\.,]+)", full_text, re.IGNORECASE)
    if m_spend: data["saldo_pendiente"] = m_spend.group(1).strip()

    m_sact = re.search(r"Saldo\s*actual:?\s*(\$[\s\d\.,]+)", full_text, re.IGNORECASE)
    if m_sact: data["saldo_actual"] = m_sact.group(1).strip()

    m_prox = re.search(r"Pr[oó]ximo\s*pago:?\s*(\$[\s\d\.,]+)", full_text, re.IGNORECASE)
    if m_prox: data["proximo_pago"] = m_prox.group(1).strip()

    m_antes = re.search(r"Pagar\s*antes\s*de:?\s*([0-9/\-\s:,apmAPM]+)", full_text, re.IGNORECASE)
    if m_antes: data["pagar_antes_de"] = m_antes.group(1).strip()

    m_fcons = re.search(r"Fecha\s*de\s*consulta:?\s*([0-9/\-\s:,apmAPM]+)", full_text, re.IGNORECASE)
    if m_fcons: data["fecha_consulta"] = m_fcons.group(1).strip()

    return data

def analyze_and_classify_movements(data):
    """Clasifica detalladamente cada cuota y pago, calculando mora y totales."""
    f_cons = parse_date(data["fecha_consulta"]) or datetime.now()

    pagos_verificados = []
    for r in data["filas"]:
        concepto = r[0]
        status = r[5] if len(r) > 5 else ""
        if "Pago" in concepto:
            if "Verificado" in status or "VERIFICADO" in status:
                pagos_verificados.append(r)

    total_pagos_verificados = len(pagos_verificados)

    classified = []
    cicladas_count = 0
    mora_cuotas = []
    total_pagado = 0.0
    cuota_num = 0

    for r in data["filas"]:
        concepto = r[0]
        fecha_str = r[1]
        monto = r[2]
        monto_apl = r[3]
        saldo = r[4]
        status_raw = r[5] if len(r) > 5 else ""
        motivo = r[6] if len(r) > 6 else ""

        d_cuota = parse_date(fecha_str)

        if "Pago" in concepto:
            if "Verificado" in status_raw or "VERIFICADO" in status_raw:
                tipo = "PAGO"
                desc = "Pago Realizado"
                estado_txt = "✔ Verificado"
                monto_val = parse_currency(monto)
                total_pagado += monto_val
                disp_monto = monto if (monto.startswith("-") or "$-" in monto) else f"-{monto}"
                disp_apl = monto_apl if (monto_apl.startswith("-") or "$-" in monto_apl) else f"-{monto_apl}"
                classified.append({
                    "tipo": tipo,
                    "concepto": desc,
                    "fecha": fecha_str,
                    "monto": disp_monto,
                    "monto_apl": disp_apl,
                    "saldo": "$0.00",
                    "estado": estado_txt,
                    "row_type": "pago"
                })
            else:
                tipo = "RECHAZO"
                desc = "Intento de Pago"
                det = f"Rechazado ({motivo})" if motivo else "Rechazado iniciado"
                classified.append({
                    "tipo": tipo,
                    "concepto": desc,
                    "fecha": fecha_str,
                    "monto": monto,
                    "monto_apl": "$0.00",
                    "saldo": saldo,
                    "estado": det,
                    "row_type": "rechazo"
                })
        elif "Cuota" in concepto:
            cuota_num += 1
            es_ciclada = (d_cuota is not None and d_cuota <= f_cons) or ("*" in concepto)
            clean_concepto = concepto.replace("*", "").strip()

            if es_ciclada:
                cicladas_count += 1
                if cuota_num <= total_pagos_verificados:
                    tipo = "CICLADA"
                    estado_txt = "Registrada"
                    row_type = "ciclada_pagada"
                    classified.append({
                        "tipo": tipo,
                        "concepto": clean_concepto,
                        "fecha": fecha_str,
                        "monto": monto,
                        "monto_apl": monto_apl,
                        "saldo": monto,
                        "estado": estado_txt,
                        "row_type": row_type
                    })
                else:
                    tipo = "CICLADA"
                    estado_txt = "Pendiente / Mora"
                    row_type = "ciclada_mora"
                    mora_cuotas.append(clean_concepto)
                    classified.append({
                        "tipo": tipo,
                        "concepto": clean_concepto,
                        "fecha": fecha_str,
                        "monto": monto,
                        "monto_apl": monto_apl,
                        "saldo": monto,
                        "estado": estado_txt,
                        "row_type": row_type
                    })
            else:
                tipo = "FUTURA"
                estado_txt = "Por Ciclar"
                row_type = "futura"
                classified.append({
                    "tipo": tipo,
                    "concepto": clean_concepto,
                    "fecha": fecha_str,
                    "monto": monto,
                    "monto_apl": monto_apl,
                    "saldo": saldo,
                    "estado": estado_txt,
                    "row_type": row_type
                })

    mora_count = len(mora_cuotas)
    total_pagado_str = format_currency(total_pagado)

    # Construcción narrativa de "Revisión de Soporte"
    f_cons_str = data["fecha_consulta"].split(",")[0].strip() if data["fecha_consulta"] else "la fecha"
    
    if mora_count > 0:
        if mora_count == 1:
            mora_subtitle = f"Mora Pendiente ({mora_cuotas[0]})"
            mora_lista_str = f"La **{mora_cuotas[0]}**"
        else:
            mora_subtitle = f"Mora Pendiente ({', '.join(mora_cuotas)})"
            mora_lista_str = f"Las **{', '.join(mora_cuotas[:-1])} y {mora_cuotas[-1]}**"
        
        cubiertas_txt = f" (cubriendo las Cuotas 1 a {total_pagos_verificados})" if total_pagos_verificados > 0 else ""
        revision_texto = (
            f"A la fecha de consulta ({f_cons_str}), han ciclado {cicladas_count} cuotas (Cuota 1 a Cuota {cicladas_count}). "
            f"El cliente registra {total_pagos_verificados} pago(s) verificado(s) por un total de **{total_pagado_str}**{cubiertas_txt}. "
            f"{mora_lista_str} se encuentra(n) pendiente(s), lo que genera **{mora_count} cuota(s) atrasada(s) en mora** "
            f"con un saldo vencido de **{data['saldo_actual']}** a pagar antes del {data['pagar_antes_de']}."
        )
    else:
        mora_subtitle = "Sin mora pendiente (Al día)"
        if cicladas_count > 0:
            revision_texto = (
                f"A la fecha de consulta ({f_cons_str}), han ciclado {cicladas_count} cuotas (Cuota 1 a Cuota {cicladas_count}). "
                f"El cliente registra {total_pagos_verificados} pagos verificados por un total de **{total_pagado_str}**, "
                f"cubriendo satisfactoriamente la totalidad de las cuotas cicladas a la fecha. "
                f"El crédito se encuentra **completamente al día (0 cuotas atrasadas)** con un saldo exigible de **{data['saldo_actual']}**. "
                f"El saldo pendiente total hasta fin de contrato es de **{data['saldo_pendiente']}**, con próximo vencimiento programado para el {data['pagar_antes_de']} "
                f"por valor de **{data['proximo_pago']}**."
            )
        else:
            revision_texto = (
                f"A la fecha de consulta ({f_cons_str}), el crédito no presenta cuotas cicladas aún. "
                f"Todas las cuotas se encuentran por ciclar. El crédito se encuentra **al día** con saldo actual de **$0.00**. "
                f"El primer vencimiento está programado para el {data['pagar_antes_de']} por un valor de **{data['proximo_pago']}**."
            )

    return {
        "cicladas_count": cicladas_count,
        "pagos_count": total_pagos_verificados,
        "total_pagado_str": total_pagado_str,
        "mora_count": mora_count,
        "mora_subtitle": mora_subtitle,
        "revision_texto": revision_texto,
        "classified": classified
    }

def render_html_report(data, analysis):
    """Genera el código HTML con estilos idénticos al formato de PLANTILLA.pdf."""
    cicladas_count = analysis["cicladas_count"]
    pagos_count = analysis["pagos_count"]
    total_pagado_str = analysis["total_pagado_str"]
    mora_count = analysis["mora_count"]
    mora_subtitle = analysis["mora_subtitle"]
    revision_texto = analysis["revision_texto"]
    classified = analysis["classified"]

    total_movs = len(classified)
    split_p1 = min(13, total_movs)
    p1_rows = classified[:split_p1]
    p2_rows = classified[split_p1:]
    num_pages = 2 if len(p2_rows) > 0 else 1

    def render_rows(rows_subset):
        html_rows = []
        for r in rows_subset:
            if r["tipo"] == "CICLADA":
                badge = '<span class="badge badge-ciclada">CICLADA</span>'
            elif r["tipo"] == "PAGO":
                badge = '<span class="badge badge-pago">PAGO</span>'
            elif r["tipo"] == "FUTURA":
                badge = '<span class="badge badge-futura">FUTURA</span>'
            else:
                badge = '<span class="badge badge-rechazo">RECHAZO</span>'

            if r["row_type"] == "pago":
                col_monto = 'color: #16a34a;'
                col_apl = 'color: #16a34a;'
                col_saldo = 'color: #16a34a; font-weight: 700;'
                col_est = 'color: #16a34a; font-weight: 700;'
            elif r["row_type"] == "ciclada_mora":
                col_monto = 'color: #0f172a;'
                col_apl = 'color: #0f172a;'
                col_saldo = 'color: #dc2626; font-weight: 700;'
                col_est = 'color: #dc2626; font-weight: 700;'
            elif r["row_type"] == "futura":
                col_monto = 'color: #0f172a;'
                col_apl = 'color: #0f172a;'
                col_saldo = 'color: #0f172a;'
                col_est = 'color: #64748b;'
            elif r["row_type"] == "rechazo":
                col_monto = 'color: #64748b;'
                col_apl = 'color: #64748b;'
                col_saldo = 'color: #64748b;'
                col_est = 'color: #dc2626; font-size: 6.5pt;'
            else:
                col_monto = 'color: #0f172a;'
                col_apl = 'color: #0f172a;'
                col_saldo = 'color: #0f172a;'
                col_est = 'color: #0f172a;'

            html_rows.append(f"""
                <tr>
                    <td style="width: 10%; text-align: left;">{badge}</td>
                    <td style="width: 18%; font-weight: 600; text-align: left;">{r['concepto']}</td>
                    <td style="width: 12%; color: #334155; text-align: center;">{r['fecha']}</td>
                    <td style="width: 15%; text-align: right; {col_monto}">{r['monto']}</td>
                    <td style="width: 15%; text-align: right; {col_apl}">{r['monto_apl']}</td>
                    <td style="width: 15%; text-align: right; {col_saldo}">{r['saldo']}</td>
                    <td style="width: 15%; text-align: left; {col_est}">{r['estado']}</td>
                </tr>
            """)
        return "".join(html_rows)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte de Estado de Cuenta - {data['contrato']}</title>
<style>
    @page {{
        size: A4 portrait;
        margin: 0;
    }}
    * {{
        box-sizing: border-box;
        -webkit-font-smoothing: antialiased;
    }}
    body {{
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #0f172a;
        background-color: #ffffff;
        font-size: 8pt;
    }}
    .sheet {{
        width: 210mm;
        height: 297mm;
        padding: 16mm 18mm 14mm 18mm;
        position: relative;
        page-break-after: always;
        overflow: hidden;
        background: #ffffff;
    }}
    
    /* HEADER TOP */
    .header-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        padding-bottom: 6px;
        border-bottom: 2px solid #0052cc;
        margin-bottom: 12px;
    }}
    .header-title {{
        font-size: 13pt;
        font-weight: 800;
        color: #0052cc;
        letter-spacing: -0.2px;
        margin: 0;
    }}
    .header-meta {{
        text-align: right;
    }}
    .header-meta .title-sub {{
        font-size: 10pt;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 2px;
    }}
    .header-meta .date-sub {{
        font-size: 7.5pt;
        color: #64748b;
    }}

    /* CLIENT INFO CARD */
    .client-card {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 8px 14px;
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
    }}
    .client-item {{
        display: flex;
        flex-direction: column;
    }}
    .client-label {{
        font-size: 6.8pt;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 2px;
    }}
    .client-val {{
        font-size: 8.5pt;
        font-weight: 700;
        color: #0f172a;
    }}
    .client-val-blue {{
        font-size: 9pt;
        font-weight: 800;
        color: #0052cc;
    }}

    /* 4 KPI CARDS */
    .kpi-row {{
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
    }}
    .kpi-card {{
        flex: 1;
        border-radius: 6px;
        padding: 8px 10px;
        display: flex;
        flex-direction: column;
    }}
    .kpi-card-cicladas {{
        background: #eff6ff;
        border: 1px solid #bfdbfe;
    }}
    .kpi-card-pagos {{
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
    }}
    .kpi-card-mora {{
        background: #fef2f2;
        border: 1px solid #fecaca;
    }}
    .kpi-card-saldo {{
        background: #fef2f2;
        border: 1px solid #fecaca;
    }}
    .kpi-card-ok {{
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
    }}
    .kpi-label {{
        font-size: 6.8pt;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        margin-bottom: 2px;
    }}
    .kpi-num-blue {{
        font-size: 13pt;
        font-weight: 800;
        color: #0284c7;
        line-height: 1.1;
    }}
    .kpi-num-green {{
        font-size: 13pt;
        font-weight: 800;
        color: #16a34a;
        line-height: 1.1;
    }}
    .kpi-num-red {{
        font-size: 13pt;
        font-weight: 800;
        color: #dc2626;
        line-height: 1.1;
    }}
    .kpi-sub {{
        font-size: 6.5pt;
        color: #64748b;
        margin-top: 3px;
    }}

    /* CONVENCIONES */
    .conv-box {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 5px;
        padding: 5px 12px;
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 6.8pt;
        color: #334155;
        margin-bottom: 12px;
    }}
    .conv-title {{
        font-weight: 700;
        color: #1e293b;
    }}
    .conv-item {{
        display: flex;
        align-items: center;
        gap: 5px;
    }}
    .conv-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }}

    /* SECTION TITLE BAR */
    .section-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
        padding: 0 2px;
    }}
    .section-title {{
        font-size: 8pt;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.1px;
    }}
    .section-sub {{
        font-size: 7pt;
        color: #64748b;
    }}

    /* TABLE */
    table.data-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 6.8pt;
    }}
    table.data-table thead tr {{
        background: #0f172a;
    }}
    table.data-table thead th {{
        color: #ffffff;
        font-size: 6.8pt;
        font-weight: 700;
        padding: 5px 6px;
        letter-spacing: 0.2px;
    }}
    table.data-table thead th:first-child {{
        border-top-left-radius: 4px;
    }}
    table.data-table thead th:last-child {{
        border-top-right-radius: 4px;
    }}
    table.data-table tbody tr {{
        border-bottom: 1px solid #f1f5f9;
    }}
    table.data-table tbody tr:nth-child(even) {{
        background: #f8fafc;
    }}
    table.data-table tbody td {{
        padding: 4.2px 6px;
        vertical-align: middle;
    }}

    /* BADGES */
    .badge {{
        display: inline-block;
        padding: 1.5px 6px;
        border-radius: 10px;
        font-size: 6pt;
        font-weight: 800;
        letter-spacing: 0.2px;
        text-align: center;
    }}
    .badge-ciclada {{
        background: #e0f2fe;
        color: #0284c7;
    }}
    .badge-pago {{
        background: #dcfce7;
        color: #16a34a;
    }}
    .badge-futura {{
        background: #e0f2fe;
        color: #0284c7;
    }}
    .badge-rechazo {{
        background: #fee2e2;
        color: #dc2626;
    }}

    /* REVISIÓN DE SOPORTE */
    .revision-box {{
        background: #fff1f2;
        border-left: 3.5px solid #dc2626;
        border-radius: 4px;
        padding: 9px 12px;
        margin-top: 14px;
    }}
    .revision-title {{
        font-size: 8pt;
        font-weight: 800;
        color: #be123c;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.2px;
    }}
    .revision-body {{
        font-size: 7.2pt;
        line-height: 1.45;
        color: #334155;
    }}
    .revision-body b, .revision-body strong {{
        color: #0f172a;
    }}

    /* FOOTER */
    .page-footer {{
        position: absolute;
        bottom: 8mm;
        left: 18mm;
        right: 18mm;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        border-top: 1px solid #cbd5e1;
        padding-top: 4px;
        font-size: 6.8pt;
        color: #64748b;
    }}
</style>
</head>
<body>

    <!-- PÁGINA 1 -->
    <div class="sheet">
        <div class="header-top">
            <h1 class="header-title">REPORTE DE ESTADO DE CUENTA</h1>
            <div class="header-meta">
                <div class="title-sub">ESTADO DE CUENTA E HISTORIAL</div>
                <div class="date-sub">Fecha de consulta: {data['fecha_consulta']}</div>
            </div>
        </div>

        <div class="client-card">
            <div class="client-item" style="flex: 1.6;">
                <span class="client-label">CLIENTE</span>
                <span class="client-val">{data['nombre']}</span>
            </div>
            <div class="client-item" style="flex: 1;">
                <span class="client-label">IDENTIFICACIÓN</span>
                <span class="client-val">{data['identificacion']}</span>
            </div>
            <div class="client-item" style="flex: 0.9;">
                <span class="client-label">CONTRATO NO.</span>
                <span class="client-val">{data['contrato']}</span>
            </div>
            <div class="client-item" style="flex: 1.1; text-align: right;">
                <span class="client-label">SALDO PENDIENTE</span>
                <span class="client-val-blue">{data['saldo_pendiente']}</span>
            </div>
        </div>

        <div class="kpi-row">
            <div class="kpi-card kpi-card-cicladas">
                <span class="kpi-label">CUOTAS CICLADAS</span>
                <span class="kpi-num-blue">{cicladas_count}</span>
                <span class="kpi-sub">Vencidas a la fecha</span>
            </div>
            <div class="kpi-card kpi-card-pagos">
                <span class="kpi-label">PAGOS APLICADOS</span>
                <span class="kpi-num-green">{pagos_count}</span>
                <span class="kpi-sub">Total: {total_pagado_str}</span>
            </div>
            <div class="kpi-card {'kpi-card-mora' if mora_count > 0 else 'kpi-card-ok'}">
                <span class="kpi-label">CUOTAS ATRASADAS</span>
                <span class="{'kpi-num-red' if mora_count > 0 else 'kpi-num-green'}">{mora_count}</span>
                <span class="kpi-sub">{mora_subtitle}</span>
            </div>
            <div class="kpi-card {'kpi-card-saldo' if mora_count > 0 else 'kpi-card-ok'}">
                <span class="kpi-label">SALDO ACTUAL</span>
                <span class="{'kpi-num-red' if mora_count > 0 else 'kpi-num-green'}">{data['saldo_actual']}</span>
                <span class="kpi-sub">Pagar antes de: {data['pagar_antes_de']}</span>
            </div>
        </div>

        <div class="conv-box">
            <span class="conv-title">Convenciones:</span>
            <div class="conv-item"><span class="conv-dot" style="background: #0284c7;"></span> Cuota Ciclada</div>
            <div class="conv-item"><span class="conv-dot" style="background: #16a34a;"></span> Pago Efectivo Verificado</div>
            <div class="conv-item"><span class="conv-dot" style="background: #dc2626;"></span> Saldo en Mora</div>
            <div class="conv-item"><span class="conv-dot" style="background: #94a3b8;"></span> Cuota Futura</div>
        </div>

        <div class="section-bar">
            <span class="section-title">HISTORIAL DETALLADO DE MOVIMIENTOS (PARTE 1: MOVIMIENTOS 1 AL {len(p1_rows)})</span>
            <span class="section-sub">Orden original del calendario</span>
        </div>

        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 10%; text-align: left;">TIPO</th>
                    <th style="width: 18%; text-align: left;">CONCEPTO</th>
                    <th style="width: 12%; text-align: center;">FECHA</th>
                    <th style="width: 15%; text-align: right;">MONTO</th>
                    <th style="width: 15%; text-align: right;">MONTO APLICADO</th>
                    <th style="width: 15%; text-align: right;">SALDO CUOTA</th>
                    <th style="width: 15%; text-align: left;">ESTADO / DETALLE</th>
                </tr>
            </thead>
            <tbody>
                {render_rows(p1_rows)}
            </tbody>
        </table>

        <div class="page-footer">
            <span>Página 1 de {num_pages}</span>
        </div>
    </div>

    <!-- PÁGINA 2 (si hay movimientos restantes) -->
    {"<div class='sheet'>" if num_pages > 1 else ""}
    {f'''
        <div class="header-top">
            <h1 class="header-title" style="font-size: 11pt;">REPORTE DE ESTADO DE CUENTA</h1>
            <div class="header-meta">
                <div class="title-sub" style="font-size: 8.5pt; font-weight: 700; color: #475569;">
                    Contrato No: <b style="color: #0f172a;">{data['contrato']}</b> | Cliente: <b style="color: #0f172a;">{data['nombre']}</b>
                </div>
            </div>
        </div>

        <div class="section-bar" style="margin-top: 6px;">
            <span class="section-title">HISTORIAL DETALLADO DE MOVIMIENTOS (PARTE 2: MOVIMIENTOS {len(p1_rows) + 1} AL {total_movs})</span>
            <span class="section-sub">Orden original del calendario</span>
        </div>

        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 10%; text-align: left;">TIPO</th>
                    <th style="width: 18%; text-align: left;">CONCEPTO</th>
                    <th style="width: 12%; text-align: center;">FECHA</th>
                    <th style="width: 15%; text-align: right;">MONTO</th>
                    <th style="width: 15%; text-align: right;">MONTO APLICADO</th>
                    <th style="width: 15%; text-align: right;">SALDO CUOTA</th>
                    <th style="width: 15%; text-align: left;">ESTADO / DETALLE</th>
                </tr>
            </thead>
            <tbody>
                {render_rows(p2_rows)}
            </tbody>
        </table>

        <div class="revision-box">
            <div class="revision-title">REVISIÓN DE SOPORTE</div>
            <div class="revision-body">{revision_texto}</div>
        </div>

        <div class="page-footer">
            <span>Página 2 de 2</span>
        </div>
    </div>''' if num_pages > 1 else ""}

</body>
</html>
"""
    return html

# ----------------- GENERADOR REPORTLAB (FALLBACK UNIVERSAL) -----------------

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748b"))
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(14*mm, 12*mm, A4[0] - 14*mm, 12*mm)
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(A4[0] - 14*mm, 8*mm, page_text)
        self.restoreState()

def generate_pdf_reportlab(data, analysis, output_pdf_path):
    """Generador universal en memoria o archivo usando ReportLab (100% puro Python)."""
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=14*mm,
        topMargin=10*mm,
        bottomMargin=15*mm
    )

    styles = getSampleStyleSheet()
    
    h_title = ParagraphStyle('HTitle', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#0052cc'))
    h_sub = ParagraphStyle('HSub', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.HexColor('#0f172a'), alignment=2)
    h_date = ParagraphStyle('HDate', fontName='Helvetica', fontSize=7, leading=9, textColor=colors.HexColor('#64748b'), alignment=2)

    lbl_style = ParagraphStyle('Lbl', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#64748b'))
    val_style = ParagraphStyle('Val', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#0f172a'))
    val_blue = ParagraphStyle('ValB', fontName='Helvetica-Bold', fontSize=8.5, leading=10, textColor=colors.HexColor('#0052cc'), alignment=2)
    lbl_right = ParagraphStyle('LblR', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#64748b'), alignment=2)

    kpi_lbl = ParagraphStyle('KLbl', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#475569'))
    kpi_num_b = ParagraphStyle('KNb', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#0284c7'))
    kpi_num_g = ParagraphStyle('KNg', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#16a34a'))
    kpi_num_r = ParagraphStyle('KNr', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#dc2626'))
    kpi_sub = ParagraphStyle('KSub', fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#64748b'))

    sec_title = ParagraphStyle('SecT', fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.HexColor('#0f172a'))
    sec_sub = ParagraphStyle('SecS', fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#64748b'), alignment=2)

    th_l = ParagraphStyle('ThL', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.white)
    th_c = ParagraphStyle('ThC', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.white, alignment=1)
    th_r = ParagraphStyle('ThR', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.white, alignment=2)

    td_l = ParagraphStyle('TdL', fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#0f172a'))
    td_b = ParagraphStyle('TdB', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#0f172a'))
    td_c = ParagraphStyle('TdC', fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#334155'), alignment=1)
    td_r = ParagraphStyle('TdR', fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#0f172a'), alignment=2)
    td_r_g = ParagraphStyle('TdRG', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#16a34a'), alignment=2)
    td_r_r = ParagraphStyle('TdRR', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#dc2626'), alignment=2)
    td_est_g = ParagraphStyle('TdEstG', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#16a34a'))
    td_est_r = ParagraphStyle('TdEstR', fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.HexColor('#dc2626'))
    td_est_gry = ParagraphStyle('TdEstGry', fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#64748b'))

    story = []

    # 1. Header Top
    header_table = Table([
        [Paragraph("REPORTE DE ESTADO DE CUENTA", h_title),
         [Paragraph("ESTADO DE CUENTA E HISTORIAL", h_sub),
          Paragraph(f"Fecha de consulta: {data['fecha_consulta']}", h_date)]]
    ], colWidths=[280, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#0052cc')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 2. Client Card
    c_table = Table([
        [
            [Paragraph("CLIENTE", lbl_style), Paragraph(data['nombre'], val_style)],
            [Paragraph("IDENTIFICACIÓN", lbl_style), Paragraph(data['identificacion'], val_style)],
            [Paragraph("CONTRATO NO.", lbl_style), Paragraph(data['contrato'], val_style)],
            [Paragraph("SALDO PENDIENTE", lbl_right), Paragraph(data['saldo_pendiente'], val_blue)]
        ]
    ], colWidths=[180, 110, 100, 130])
    c_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(c_table)
    story.append(Spacer(1, 8))

    # 3. KPI Cards
    mora_c = analysis['mora_count']
    kpi_table = Table([
        [
            [Paragraph("CUOTAS CICLADAS", kpi_lbl), Paragraph(str(analysis['cicladas_count']), kpi_num_b), Paragraph("Vencidas a la fecha", kpi_sub)],
            [Paragraph("PAGOS APLICADOS", kpi_lbl), Paragraph(str(analysis['pagos_count']), kpi_num_g), Paragraph(f"Total: {analysis['total_pagado_str']}", kpi_sub)],
            [Paragraph("CUOTAS ATRASADAS", kpi_lbl), Paragraph(str(mora_c), kpi_num_r if mora_c>0 else kpi_num_g), Paragraph(analysis['mora_subtitle'], kpi_sub)],
            [Paragraph("SALDO ACTUAL", kpi_lbl), Paragraph(data['saldo_actual'], kpi_num_r if mora_c>0 else kpi_num_g), Paragraph(f"Antes de: {data['pagar_antes_de']}", kpi_sub)]
        ]
    ], colWidths=[130, 130, 130, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#eff6ff')),
        ('BOX', (0,0), (0,0), 0.5, colors.HexColor('#bfdbfe')),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#f0fdf4')),
        ('BOX', (1,0), (1,0), 0.5, colors.HexColor('#bbf7d0')),
        ('BACKGROUND', (2,0), (2,0), colors.HexColor('#fef2f2' if mora_c>0 else '#f0fdf4')),
        ('BOX', (2,0), (2,0), 0.5, colors.HexColor('#fecaca' if mora_c>0 else '#bbf7d0')),
        ('BACKGROUND', (3,0), (3,0), colors.HexColor('#fef2f2' if mora_c>0 else '#f0fdf4')),
        ('BOX', (3,0), (3,0), 0.5, colors.HexColor('#fecaca' if mora_c>0 else '#bbf7d0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 8))

    # 4. Convenciones
    conv_table = Table([
        [
            Paragraph("<b>Convenciones:</b>", ParagraphStyle('ConvB', fontName='Helvetica-Bold', fontSize=6.5, textColor=colors.HexColor('#1e293b'))),
            Paragraph("● Cuota Ciclada", ParagraphStyle('C1', fontName='Helvetica', fontSize=6.5, textColor=colors.HexColor('#0284c7'))),
            Paragraph("● Pago Efectivo Verificado", ParagraphStyle('C2', fontName='Helvetica', fontSize=6.5, textColor=colors.HexColor('#16a34a'))),
            Paragraph("● Saldo en Mora", ParagraphStyle('C3', fontName='Helvetica', fontSize=6.5, textColor=colors.HexColor('#dc2626'))),
            Paragraph("● Cuota Futura", ParagraphStyle('C4', fontName='Helvetica', fontSize=6.5, textColor=colors.HexColor('#64748b')))
        ]
    ], colWidths=[70, 100, 130, 90, 130])
    conv_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(conv_table)
    story.append(Spacer(1, 8))

    classified = analysis['classified']
    split_p1 = min(13, len(classified))
    p1_rows = classified[:split_p1]
    p2_rows = classified[split_p1:]

    def build_tbl_data(rows_subset):
        t_data = [[
            Paragraph("TIPO", th_l),
            Paragraph("CONCEPTO", th_l),
            Paragraph("FECHA", th_c),
            Paragraph("MONTO", th_r),
            Paragraph("MONTO APLICADO", th_r),
            Paragraph("SALDO CUOTA", th_r),
            Paragraph("ESTADO / DETALLE", th_l),
        ]]
        for r in rows_subset:
            tp = r['tipo']
            b_col = '#0284c7' if tp in ['CICLADA', 'FUTURA'] else '#16a34a' if tp == 'PAGO' else '#dc2626'
            badge_p = Paragraph(f"<b>{tp}</b>", ParagraphStyle('BgP', fontName='Helvetica-Bold', fontSize=6, textColor=colors.HexColor(b_col)))

            if r['row_type'] == 'pago':
                m_style = td_r_g
                s_style = td_r_g
                est_style = td_est_g
            elif r['row_type'] == 'ciclada_mora':
                m_style = td_r
                s_style = td_r_r
                est_style = td_est_r
            elif r['row_type'] == 'futura':
                m_style = td_r
                s_style = td_r
                est_style = td_est_gry
            elif r['row_type'] == 'rechazo':
                m_style = td_r
                s_style = td_r
                est_style = td_est_r
            else:
                m_style = td_r
                s_style = td_r
                est_style = td_l

            t_data.append([
                badge_p,
                Paragraph(r['concepto'], td_b),
                Paragraph(r['fecha'], td_c),
                Paragraph(r['monto'], m_style),
                Paragraph(r['monto_apl'], m_style),
                Paragraph(r['saldo'], s_style),
                Paragraph(r['estado'], est_style),
            ])
        return t_data

    sec1 = Table([
        [Paragraph(f"HISTORIAL DETALLADO DE MOVIMIENTOS (PARTE 1: MOVIMIENTOS 1 AL {len(p1_rows)})", sec_title),
         Paragraph("Orden original del calendario", sec_sub)]
    ], colWidths=[350, 170])
    sec1.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM')
    ]))
    story.append(sec1)
    story.append(Spacer(1, 2))

    col_w = [52, 94, 62, 78, 78, 78, 78]
    dt1 = Table(build_tbl_data(p1_rows), colWidths=col_w)
    dt1_styles = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
    ]
    for i in range(1, len(p1_rows)+1):
        if i % 2 == 0:
            dt1_styles.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#f8fafc')))
    dt1.setStyle(TableStyle(dt1_styles))
    story.append(dt1)

    if p2_rows:
        story.append(PageBreak())
        
        h2 = Table([
            [Paragraph("REPORTE DE ESTADO DE CUENTA", ParagraphStyle('H2T', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0052cc'))),
             Paragraph(f"Contrato No: <b>{data['contrato']}</b> | Cliente: <b>{data['nombre']}</b>", ParagraphStyle('H2Sub', fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor('#475569'), alignment=2))]
        ], colWidths=[240, 280])
        h2.setStyle(TableStyle([
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#0052cc')),
        ]))
        story.append(h2)
        story.append(Spacer(1, 6))

        sec2 = Table([
            [Paragraph(f"HISTORIAL DETALLADO DE MOVIMIENTOS (PARTE 2: MOVIMIENTOS {len(p1_rows)+1} AL {len(classified)})", sec_title),
             Paragraph("Orden original del calendario", sec_sub)]
        ], colWidths=[350, 170])
        sec2.setStyle(TableStyle([
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM')
        ]))
        story.append(sec2)
        story.append(Spacer(1, 2))

        dt2 = Table(build_tbl_data(p2_rows), colWidths=col_w)
        dt2_styles = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ]
        for i in range(1, len(p2_rows)+1):
            if i % 2 == 0:
                dt2_styles.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#f8fafc')))
        dt2.setStyle(TableStyle(dt2_styles))
        story.append(dt2)
        story.append(Spacer(1, 10))

        clean_rev = analysis['revision_texto'].replace('**', '')
        rev_table = Table([
            [
                Paragraph("<b>REVISIÓN DE SOPORTE</b>", ParagraphStyle('RevT', fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#be123c'))),
            ],
            [
                Paragraph(clean_rev, ParagraphStyle('RevB', fontName='Helvetica', fontSize=7, leading=10, textColor=colors.HexColor('#334155')))
            ]
        ], colWidths=[520])
        rev_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fff1f2')),
            ('LINELEFT', (0,0), (-1,-1), 3, colors.HexColor('#dc2626')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(rev_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_pdf_path

def convert_html_to_pdf(html_content, output_pdf_path, data=None, analysis=None):
    """
    Convierte a PDF.
    Si Edge/Chrome está disponible (Windows local), usa Chromium headless.
    Si no está disponible (Linux en Vercel Serverless), usa ReportLab de forma transparente.
    """
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    ]
    browser_exe = None
    for p in edge_paths:
        if os.path.exists(p):
            browser_exe = p
            break
            
    if not browser_exe:
        for cmd_name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge"]:
            found = shutil.which(cmd_name)
            if found:
                browser_exe = found
                break

    # Si encontramos un navegador Chromium, lo usamos
    if browser_exe:
        temp_html = output_pdf_path + ".temp.html"
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        abs_html = os.path.abspath(temp_html)
        abs_pdf = os.path.abspath(output_pdf_path)

        cmd = [
            browser_exe,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={abs_pdf}",
            abs_html
        ]
        try:
            subprocess.run(cmd, check=True)
            return abs_pdf
        finally:
            if os.path.exists(temp_html):
                try: os.remove(temp_html)
                except: pass

    # Fallback automático para Vercel Serverless (sin navegador instalado)
    if data and analysis:
        return generate_pdf_reportlab(data, analysis, output_pdf_path)
    else:
        raise RuntimeError("No se encontró navegador Chromium ni datos estructurados para ReportLab.")

def procesar_cronograma(pdf_input, output_pdf_path=None):
    """
    Función principal de alto nivel.
    Recibe la ruta del PDF de cronograma o sus bytes,
    genera el PDF del Reporte Ejecutivo y retorna (pdf_path, html_content, data, analysis).
    """
    data = extract_cronograma_data(pdf_input)
    analysis = analyze_and_classify_movements(data)
    html_code = render_html_report(data, analysis)

    if not output_pdf_path:
        contrato = data.get("contrato") or "reporte"
        output_pdf_path = f"Reporte_Estado_Cuenta_{contrato}.pdf"

    pdf_path = convert_html_to_pdf(html_code, output_pdf_path, data=data, analysis=analysis)
    return pdf_path, html_code, data, analysis
