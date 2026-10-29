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
    """
    Clasifica movimientos usando Asociación por Ciclo + Amortización de Rezago (Opción B).

    Fase 1 – Asociación directa por ciclo:
        Cada cuota ciclada que cuente con su pago verificado regular en su ciclo
        (entre su vencimiento y la siguiente cuota) queda cancelada/Registrada.
        Cualquier pago excedente o extemporáneo pasa a la bolsa de rezago.

    Fase 2 – Amortización de mora vieja con pagos sobrantes (Rezago FIFO):
        Los pagos verificados sobrantes (abonos posteriores o excedentes) se aplican
        en estricto orden cronológico ascendente (FIFO) a las cuotas cicladas más
        antiguas que hayan quedado descubiertas (por rechazos, impagos, etc.).

    Fase 3 – Determinación de cuotas pendientes / mora:
        Toda cuota ciclada que no haya sido cubierta ni en Fase 1 ni en Fase 2
        se marca como 'Pendiente / Mora'. Las cuotas futuras a la fecha de consulta
        se mantienen 'Por Ciclar'.
    """
    f_cons = parse_date(data["fecha_consulta"]) or datetime.now()
    saldo_actual_num = parse_currency(data.get("saldo_actual", "$0.00"))
    cliente_al_dia_por_saldo = (saldo_actual_num == 0.0)

    # ── 1. Agrupar filas en estructura de cuotas y sus pagos de ciclo ────────
    cuotas = []
    current_cuota = None
    extra_pagos = []
    total_pagos_verificados = 0
    total_pagado = 0.0

    for r in data["filas"]:
        concepto  = r[0]
        fecha_str = r[1]
        monto     = r[2]
        status    = r[5] if len(r) > 5 else ""

        if "Cuota" in concepto:
            current_cuota = {
                "num":       len(cuotas) + 1,
                "concepto":  concepto.replace("*", "").strip(),
                "fecha_str": fecha_str,
                "fecha":     parse_date(fecha_str),
                "monto":     monto,
                "row":       r,
                "pagos":     [],
            }
            cuotas.append(current_cuota)
        elif "Pago" in concepto:
            if "Verificado" in status or "VERIFICADO" in status:
                monto_val = parse_currency(monto)
                total_pagos_verificados += 1
                total_pagado += monto_val
                pago_obj = {
                    "fecha_str": fecha_str,
                    "fecha":     parse_date(fecha_str),
                    "monto":     monto,
                    "monto_val": monto_val,
                    "row":       r,
                }
                if current_cuota is not None:
                    current_cuota["pagos"].append(pago_obj)
                else:
                    extra_pagos.append(pago_obj)

    # Identificar cuáles cuotas están cicladas a la fecha de consulta
    cicladas = [c for c in cuotas if (c["fecha"] and c["fecha"] <= f_cons) or ("*" in c["row"][0])]
    last_ciclada_num = cicladas[-1]["num"] if cicladas else 0
    cicladas_count   = len(cicladas)

    covered = {c["num"]: False for c in cuotas}
    leftover_pagos = list(extra_pagos)

    # ── FASE 1: Asociación Directa por Ciclo ─────────────────────────────────
    for c in cuotas:
        if c["num"] > last_ciclada_num:
            # Cuotas futuras no cicladas: cualquier pago asociado pasa a bolsa general
            leftover_pagos.extend(c["pagos"])
            continue

        is_last_ciclada = (c["num"] == last_ciclada_num)

        if not is_last_ciclada:
            if len(c["pagos"]) >= 1:
                covered[c["num"]] = True
                leftover_pagos.extend(c["pagos"][1:])
        else:
            # En la última cuota ciclada:
            # Si existen cuotas anteriores descubiertas (en mora), los pagos al cierre
            # son abonos posteriores a las cuotas para amortizar la deuda más antigua
            # por prelación de pagos legal y financiera.
            has_prior_uncovered = any(
                not covered[prior["num"]]
                for prior in cuotas
                if prior["num"] < c["num"] and prior["num"] <= last_ciclada_num
            )
            if has_prior_uncovered:
                leftover_pagos.extend(c["pagos"])
            else:
                if len(c["pagos"]) >= 1:
                    covered[c["num"]] = True
                    leftover_pagos.extend(c["pagos"][1:])

    # ── FASE 2: Amortización de Mora Vieja con Pagos Sobrantes (FIFO) ────────
    leftover_pagos.sort(key=lambda p: p["fecha"] or datetime.min)
    uncovered_cicladas = [c for c in cuotas if c["num"] <= last_ciclada_num and not covered[c["num"]]]
    uncovered_cicladas.sort(key=lambda c: c["num"])

    for pago in leftover_pagos:
        if uncovered_cicladas:
            oldest = uncovered_cicladas.pop(0)
            covered[oldest["num"]] = True

    # Override: si el CRM certifica saldo_actual = $0.00, el crédito está al día
    if cliente_al_dia_por_saldo:
        for c in cuotas:
            if c["num"] <= last_ciclada_num:
                covered[c["num"]] = True

    # ── FASE 3: Clasificación final de movimientos y determinación de mora ───
    classified = []
    mora_cuotas = []
    mora_cuotas_nums = []
    cuota_seq = 0

    for r in data["filas"]:
        concepto  = r[0]
        fecha_str = r[1]
        monto     = r[2]
        monto_apl = r[3]
        saldo     = r[4]
        status_raw = r[5] if len(r) > 5 else ""
        motivo     = r[6] if len(r) > 6 else ""

        if "Pago" in concepto:
            if "Verificado" in status_raw or "VERIFICADO" in status_raw:
                disp_monto = monto if (monto.startswith("-") or "$-" in monto) else f"-{monto}"
                disp_apl   = monto_apl if (monto_apl.startswith("-") or "$-" in monto_apl) else f"-{monto_apl}"
                classified.append({
                    "tipo":      "PAGO",
                    "concepto":  "Pago Realizado",
                    "fecha":     fecha_str,
                    "monto":     disp_monto,
                    "monto_apl": disp_apl,
                    "saldo":     "$0.00",
                    "estado":    "✔ Verificado",
                    "row_type":  "pago"
                })
            else:
                det = f"Rechazado ({motivo})" if motivo else "Rechazado iniciado"
                classified.append({
                    "tipo":      "RECHAZO",
                    "concepto":  "Intento de Pago",
                    "fecha":     fecha_str,
                    "monto":     monto,
                    "monto_apl": "$0.00",
                    "saldo":     saldo,
                    "estado":    det,
                    "row_type":  "rechazo"
                })

        elif "Cuota" in concepto:
            cuota_seq += 1
            clean_concepto = concepto.replace("*", "").strip()
            es_ciclada = (cuota_seq <= last_ciclada_num)

            if es_ciclada:
                if covered.get(cuota_seq, False):
                    classified.append({
                        "tipo":      "CICLADA",
                        "concepto":  clean_concepto,
                        "fecha":     fecha_str,
                        "monto":     monto,
                        "monto_apl": monto_apl,
                        "saldo":     monto,
                        "estado":    "Registrada",
                        "row_type":  "ciclada_pagada"
                    })
                else:
                    mora_cuotas.append(clean_concepto)
                    mora_cuotas_nums.append(cuota_seq)
                    classified.append({
                        "tipo":      "CICLADA",
                        "concepto":  clean_concepto,
                        "fecha":     fecha_str,
                        "monto":     monto,
                        "monto_apl": monto_apl,
                        "saldo":     monto,
                        "estado":    "Pendiente / Mora",
                        "row_type":  "ciclada_mora"
                    })
            else:
                classified.append({
                    "tipo":      "FUTURA",
                    "concepto":  clean_concepto,
                    "fecha":     fecha_str,
                    "monto":     monto,
                    "monto_apl": monto_apl,
                    "saldo":     saldo,
                    "estado":    "Por Ciclar",
                    "row_type":  "futura"
                })

    mora_count = len(mora_cuotas)
    total_pagado_str = format_currency(total_pagado)

    # ── Construcción de la sección "REVISIÓN DE SOPORTE" ──────────────────────
    f_cons_str = data["fecha_consulta"].split(",")[0].strip() if data["fecha_consulta"] else "la fecha"

    if mora_count > 0:
        if mora_count == 1:
            mora_subtitle = f"Mora Pendiente ({mora_cuotas[0]})"
            cuotas_ref = f"la **{mora_cuotas[0]}**"
        else:
            mora_subtitle = f"Mora Pendiente ({', '.join(mora_cuotas)})"
            nums_str = ", ".join(str(n) for n in mora_cuotas_nums[:-1]) + f" y {mora_cuotas_nums[-1]}"
            cuotas_ref = f"las **cuotas {nums_str}**"

        revision_texto = (
            f"A la fecha de consulta ({f_cons_str}), han ciclado {cicladas_count} cuotas "
            f"(Cuota 1 a Cuota {cicladas_count}). "
            f"El cliente registra {total_pagos_verificados} pago(s) verificado(s) por un total de **{total_pagado_str}**. "
            f"Presenta **{mora_count} cuotas pendientes** correspondientes a {cuotas_ref}, "
            f"lo que genera **{mora_count} cuota(s) atrasada(s) en mora** "
            f"con un saldo vencido de **{data['saldo_actual']}** a pagar antes del {data['pagar_antes_de']}."
        )
    else:
        mora_subtitle = "Sin mora pendiente (Al día)"
        if cicladas_count > 0:
            revision_texto = (
                f"A la fecha de consulta ({f_cons_str}), han ciclado {cicladas_count} cuotas "
                f"(Cuota 1 a Cuota {cicladas_count}). "
                f"El cliente registra {total_pagos_verificados} pagos verificados por un total de **{total_pagado_str}**, "
                f"cubriendo satisfactoriamente la totalidad de las cuotas cicladas a la fecha. "
                f"El crédito se encuentra **completamente al día (0 cuotas atrasadas)** con un saldo exigible de **{data['saldo_actual']}**. "
                f"El saldo pendiente total hasta fin de contrato es de **{data['saldo_pendiente']}**, "
                f"con próximo vencimiento programado para el {data['pagar_antes_de']} "
                f"por valor de **{data['proximo_pago']}**."
            )
        else:
            revision_texto = (
                f"A la fecha de consulta ({f_cons_str}), el crédito no presenta cuotas cicladas aún. "
                f"Todas las cuotas se encuentran por ciclar. El crédito se encuentra **al día** con saldo actual de **$0.00**. "
                f"El primer vencimiento está programado para el {data['pagar_antes_de']} por un valor de **{data['proximo_pago']}**."
            )

    return {
        "cicladas_count":   cicladas_count,
        "pagos_count":      total_pagos_verificados,
        "total_pagado_str": total_pagado_str,
        "mora_count":       mora_count,
        "mora_subtitle":    mora_subtitle,
        "revision_texto":   revision_texto,
        "classified":       classified,
        "cuotas_mora":      mora_cuotas_nums,
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
    
    # ── DISTRIBUCIÓN DINÁMICA INTELIGENTE ─────────────────────────────────
    # Si las cuotas y pagos caben en 1 sola hoja (hasta 28 movimientos),
    # no desperdiciar espacio en blanco y mantener todo en 1 sola página.
    if total_movs <= 28:
        split_p1 = total_movs
        p1_rows = classified
        p2_rows = []
        num_pages = 1
        sec1_title = "HISTORIAL DETALLADO DE MOVIMIENTOS"
    else:
        # Si requiere 2 páginas, balancear proporcionalmente para no dejar huecos
        split_p1 = min(24, (total_movs + 1) // 2 + 2)
        p1_rows = classified[:split_p1]
        p2_rows = classified[split_p1:]
        num_pages = 2
        sec1_title = f"HISTORIAL DETALLADO DE MOVIMIENTOS (PARTE 1: MOVIMIENTOS 1 AL {len(p1_rows)})"

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
            <span class="section-title">{sec1_title}</span>
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

        {f'''
        <div class="revision-box">
            <div class="revision-title">REVISIÓN DE SOPORTE</div>
            <div class="revision-body">{revision_texto}</div>
        </div>''' if num_pages == 1 else ""}

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
                    Contrato No: <b style="color: #0f172a;">{data['contrato']}</b> | Cédula: <b style="color: #0f172a;">{data['identificacion']}</b> | Cliente: <b style="color: #0f172a;">{data['nombre']}</b>
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
    total_movs = len(classified)

    # ── DISTRIBUCIÓN DINÁMICA INTELIGENTE ─────────────────────────────────
    # Si las cuotas y pagos caben en 1 sola hoja (hasta 28 movimientos),
    # no desperdiciar espacio en blanco y mantener todo en 1 sola página.
    if total_movs <= 28:
        split_p1 = total_movs
        p1_rows = classified
        p2_rows = []
        sec1_title_text = "HISTORIAL DETALLADO DE MOVIMIENTOS"
    else:
        split_p1 = min(24, (total_movs + 1) // 2 + 2)
        p1_rows = classified[:split_p1]
        p2_rows = classified[split_p1:]
        sec1_title_text = f"HISTORIAL DETALLADO DE MOVIMIENTOS (PARTE 1: MOVIMIENTOS 1 AL {len(p1_rows)})"

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
        [Paragraph(sec1_title_text, sec_title),
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

    # Cuadro de revisión de soporte común
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

    if not p2_rows:
        # 1 SOLA HOJA: Revisión de soporte en la misma página 1
        story.append(Spacer(1, 10))
        story.append(rev_table)
    else:
        # 2 HOJAS: Página 2 con movimientos restantes + revisión de soporte
        story.append(PageBreak())
        
        h2 = Table([
            [Paragraph("REPORTE DE ESTADO DE CUENTA", ParagraphStyle('H2T', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0052cc'))),
             Paragraph(f"Contrato: <b>{data['contrato']}</b> | Cédula: <b>{data['identificacion']}</b> | Cliente: <b>{data['nombre']}</b>", ParagraphStyle('H2Sub', fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor('#475569'), alignment=2))]
        ], colWidths=[200, 320])
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

def convert_pdf_to_images(pdf_path, output_dir=None, dpi=200):
    """
    Convierte cada página del PDF generado en una imagen PNG de alta calidad.
    Usa pypdfium2 (preferido, alta fidelidad) o Pillow como fallback.

    Parámetros:
        pdf_path    : Ruta del PDF a convertir.
        output_dir  : Directorio destino. Si es None, usa el mismo del PDF.
        dpi         : Resolución en DPI (default 200 = alta calidad, 300 = impresión).

    Retorna lista de rutas de las imágenes PNG generadas.
    """
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(pdf_path))

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    generated_images = []

    # --- Intento 1: pypdfium2 (alta fidelidad, igual que Chrome renderiza) ---
    try:
        import pypdfium2 as pdfium
        pdf_doc = pdfium.PdfDocument(pdf_path)
        scale = dpi / 72.0  # pypdfium2 trabaja en puntos (72 dpi base)
        for i, page in enumerate(pdf_doc):
            bitmap = page.render(scale=scale, rotation=0)
            pil_img = bitmap.to_pil()
            img_path = os.path.join(output_dir, f"{base_name}_pagina_{i+1}.png")
            pil_img.save(img_path, "PNG", optimize=False)
            generated_images.append(img_path)
        pdf_doc.close()
        return generated_images
    except ImportError:
        pass
    except Exception:
        pass

    # --- Intento 2: pdf2image (usa poppler) ---
    try:
        from pdf2image import convert_from_path
        pages = convert_from_path(pdf_path, dpi=dpi)
        for i, page_img in enumerate(pages):
            img_path = os.path.join(output_dir, f"{base_name}_pagina_{i+1}.png")
            page_img.save(img_path, "PNG")
            generated_images.append(img_path)
        return generated_images
    except Exception:
        pass

    raise RuntimeError(
        "No se pudo convertir el PDF a imagen. "
        "Asegúrate de tener instalado pypdfium2 (pip install pypdfium2) o pdf2image+poppler."
    )


def generate_txt_report(data, analysis, output_txt_path=None):
    """
    Genera un archivo de texto plano (.txt) con el resumen completo del estado de cuenta,
    con formato legible y estructurado para copiar/pegar o compartir por chat/correo.

    Parámetros:
        data            : Diccionario con metadatos extraídos del cronograma.
        analysis        : Diccionario con el análisis financiero clasificado.
        output_txt_path : Ruta del archivo .txt a crear. Si es None, retorna el string.

    Retorna la ruta del archivo generado o el contenido en string.
    """
    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    sep_doble = "=" * 64
    sep_simple = "-" * 64
    mora_c = analysis['mora_count']

    lines = []
    lines.append(sep_doble)
    lines.append("   REPORTE DE ESTADO DE CUENTA E HISTORIAL")
    lines.append(f"   Generado el: {fecha_gen}")
    lines.append(sep_doble)
    lines.append("")

    # ── DATOS DEL CLIENTE ──────────────────────────────────────
    lines.append("[ DATOS DEL CLIENTE ]")
    lines.append(sep_simple)
    lines.append(f"  Cliente          : {data['nombre']}")
    lines.append(f"  Identificación   : {data['identificacion']}")
    lines.append(f"  Contrato No.     : {data['contrato']}")
    lines.append(f"  Fecha consulta   : {data['fecha_consulta']}")
    lines.append("")

    # ── RESUMEN FINANCIERO (KPIs) ───────────────────────────────
    lines.append("[ RESUMEN FINANCIERO ]")
    lines.append(sep_simple)
    lines.append(f"  Cuotas Cicladas  : {analysis['cicladas_count']}  (vencidas a la fecha)")
    lines.append(f"  Pagos Aplicados  : {analysis['pagos_count']}  - Total pagado: {analysis['total_pagado_str']}")
    estado_mora = f"[ALERTA MORA] {mora_c} CUOTA(S) EN MORA - {analysis['mora_subtitle']}" if mora_c > 0 else "[AL DIA] SIN MORA"
    lines.append(f"  Estado Mora      : {estado_mora}")
    lines.append(f"  Saldo Actual     : {data['saldo_actual']}")
    lines.append(f"  Saldo Pendiente  : {data['saldo_pendiente']}  (total hasta fin de contrato)")
    lines.append(f"  Proximo Pago     : {data['proximo_pago']}  - Pagar antes de: {data['pagar_antes_de']}")
    lines.append("")

    # ── HISTORIAL DETALLADO ─────────────────────────────────────
    lines.append("[ HISTORIAL DETALLADO DE MOVIMIENTOS ]")
    lines.append(sep_simple)
    col_fmt = f"  {{:<10}} {{:<17}} {{:<12}} {{:<16}} {{:<16}} {{:<16}} {{}}"
    lines.append(col_fmt.format("TIPO", "CONCEPTO", "FECHA", "MONTO", "MONTO APLIC.", "SALDO CUOTA", "ESTADO"))
    lines.append("  " + "-" * 110)

    for mov in analysis['classified']:
        tipo     = mov['tipo']
        concepto = mov['concepto'][:16]
        fecha    = mov['fecha']
        monto    = mov['monto'][:15]
        m_apl    = mov['monto_apl'][:15]
        saldo    = mov['saldo'][:15]
        estado   = mov['estado'].replace("✔", "").strip()
        # Indicador visual limpio
        if mov['row_type'] == 'ciclada_mora':
            estado = f"[MORA] {estado}"
        elif mov['row_type'] == 'pago':
            estado = f"[OK] {estado}"
        lines.append(col_fmt.format(tipo, concepto, fecha, monto, m_apl, saldo, estado))

    lines.append("")

    # ── REVISION DE SOPORTE ─────────────────────────────────────
    lines.append("[ REVISION DE SOPORTE ]")
    lines.append(sep_simple)
    # Limpiar markdown (**texto**) para texto plano
    rev_text = analysis['revision_texto'].replace("**", "")
    words = rev_text.split()
    current_line = "  "
    for word in words:
        if len(current_line) + len(word) + 1 > 75:
            lines.append(current_line)
            current_line = "  " + word
        else:
            current_line += (" " if current_line.strip() else "") + word
    if current_line.strip():
        lines.append(current_line)

    lines.append("")
    lines.append(sep_doble)
    lines.append("  Documento generado automaticamente por App Conversor")
    lines.append(sep_doble)

    content = "\n".join(lines)
    if output_txt_path:
        with open(output_txt_path, "w", encoding="utf-8-sig") as f:
            f.write(content)
        return output_txt_path

    return content


class ResultadoProceso(dict):
    """
    Objeto de resultado inteligente que permite acceso como diccionario
    y desempaquetado de tupla retrocompatible (pdf_path, html_code, data, analysis).
    """
    def __iter__(self):
        return iter([self["pdf_path"], self["html_code"], self["data"], self["analysis"]])

    @property
    def pdf_path(self): return self.get("pdf_path")
    @property
    def html_code(self): return self.get("html_code")
    @property
    def data(self): return self.get("data")
    @property
    def analysis(self): return self.get("analysis")
    @property
    def imagenes(self): return self.get("imagenes", [])
    @property
    def txt_path(self): return self.get("txt_path")


def sanitize_filename(text):
    """Limpia caracteres invalidos para nombres de archivo en Windows y Linux."""
    if not text:
        return "NA"
    tildes = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
              'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
              'ñ': 'n', 'Ñ': 'N'}
    for k, v in tildes.items():
        text = text.replace(k, v)
    text = re.sub(r'[^\w\-_.]', '_', text)
    return re.sub(r'_+', '_', text).strip('_')


def build_report_basename(data):
    """
    Construye el nombre base institucional obligatorio con:
    Cédula + Nombre Completo + Contrato
    Ejemplo: Reporte_1122125712_MAYERLI_RUIZ_HERNANDEZ_coyrmfg
    """
    cedula = sanitize_filename(data.get("identificacion", "SIN_CEDULA"))
    nombre = sanitize_filename(data.get("nombre", "CLIENTE")).upper()
    contrato = sanitize_filename(data.get("contrato", "SIN_CONTRATO"))
    return f"Reporte_{cedula}_{nombre}_{contrato}"


def procesar_cronograma(pdf_input, output_pdf_path=None, generar_imagen=False,
                        generar_txt=False, imagen_dpi=200):
    """
    Función principal de alto nivel.
    Recibe la ruta del PDF de cronograma o sus bytes,
    genera el PDF del Reporte Ejecutivo y opcionalmente imagen PNG y TXT.
    Todos los archivos generados llevan en su nombre: Cédula, Nombre Completo y Contrato.

    Parámetros:
        pdf_input        : Ruta al PDF o bytes.
        output_pdf_path  : Ruta o directorio de salida para el PDF (auto si None).
        generar_imagen   : Si True, exporta PNG de alta calidad.
        generar_txt      : Si True, exporta archivo de texto plano.
        imagen_dpi       : Resolución de la imagen (default 200 dpi).

    Retorna ResultadoProceso compatible como diccionario y como tupla
    (pdf_path, html_code, data, analysis).
    """
    if isinstance(pdf_input, dict):
        data = pdf_input
    else:
        data = extract_cronograma_data(pdf_input)
    analysis = analyze_and_classify_movements(data)
    html_code = render_html_report(data, analysis)

    report_basename = build_report_basename(data)

    if not output_pdf_path:
        output_pdf_path = f"{report_basename}.pdf"
    elif os.path.isdir(output_pdf_path):
        output_pdf_path = os.path.join(output_pdf_path, f"{report_basename}.pdf")
    else:
        dir_dest = os.path.dirname(os.path.abspath(output_pdf_path))
        output_pdf_path = os.path.join(dir_dest, f"{report_basename}.pdf")

    pdf_path = convert_html_to_pdf(html_code, output_pdf_path, data=data, analysis=analysis)

    resultado = ResultadoProceso({
        "pdf_path": pdf_path,
        "html_code": html_code,
        "data": data,
        "analysis": analysis,
        "imagenes": [],
        "txt_path": None,
        "basename": report_basename,
    })

    # Exportar imagen PNG de alta calidad
    if generar_imagen:
        try:
            imagenes = convert_pdf_to_images(pdf_path, dpi=imagen_dpi)
            resultado["imagenes"] = imagenes
        except Exception as e:
            resultado["imagen_error"] = str(e)

    # Exportar archivo TXT
    if generar_txt:
        txt_path = os.path.splitext(pdf_path)[0] + ".txt"
        generate_txt_report(data, analysis, txt_path)
        resultado["txt_path"] = txt_path

    return resultado
