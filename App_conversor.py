"""
App_conversor.py
Punto de entrada principal para la aplicación "App_conversor".

Uso:
  1. Doble clic o sin argumentos:
     Abre la interfaz gráfica de escritorio (GUI).
  2. Por línea de comandos:
     python App_conversor.py <archivo_cronograma.pdf>
  3. Procesamiento por lote:
     python App_conversor.py --batch [carpeta]
  4. Modo Web:
     python App_conversor.py --web
"""

import os
import sys
import glob
import subprocess
import conversor_core

def process_single_file(pdf_path, output_pdf=None, open_when_done=False, generar_imagen=False, generar_txt=False):
    if not os.path.exists(pdf_path):
        print(f"❌ Error: El archivo '{pdf_path}' no existe.")
        return None

    print(f"\n📄 Procesando cronograma: {os.path.basename(pdf_path)}")
    try:
        if not output_pdf:
            output_pdf = os.path.dirname(os.path.abspath(pdf_path))

        res = conversor_core.procesar_cronograma(
            pdf_path, output_pdf,
            generar_imagen=generar_imagen,
            generar_txt=generar_txt,
            imagen_dpi=200
        )
        pdf_path_res = res.pdf_path
        data = res.data
        analysis = res.analysis

        print(f"   👤 Cliente: {data['nombre']}")
        print(f"   🔢 Contrato: {data['contrato']} | Cédula: {data['identificacion']}")
        print(f"   📊 Cuotas Cicladas: {analysis['cicladas_count']} | Pagos: {analysis['pagos_count']} ({analysis['total_pagado_str']})")
        
        if analysis['mora_count'] > 0:
            print(f"   ⚠️  MORA: {analysis['mora_count']} cuota(s) atrasada(s) | Saldo vencido: {data['saldo_actual']}")
        else:
            print(f"   ✅ AL DÍA: 0 cuotas atrasadas | Saldo exigible: {data['saldo_actual']}")

        print(f"   🎯 PDF generado con éxito: {pdf_path_res}")
        if res.imagenes:
            for img in res.imagenes:
                print(f"   🖼️  Imagen HD generada: {img}")
        if res.txt_path:
            print(f"   📝 TXT generado: {res.txt_path}")

        if open_when_done:
            os.startfile(pdf_path_res)

        return pdf_path_res
    except Exception as e:
        print(f"❌ Error procesando {pdf_path}: {e}")
        return None

def process_batch(target_dir=".", generar_imagen=False, generar_txt=False):
    search_pattern = os.path.join(target_dir, "*cronograma*.pdf")
    found_files = glob.glob(search_pattern)
    if not found_files:
        # Search all pdfs
        found_files = [f for f in glob.glob(os.path.join(target_dir, "*.pdf")) if "reporte" not in f.lower() and "plantilla" not in f.lower()]

    if not found_files:
        print(f"No se encontraron cronogramas PDF en '{target_dir}'.")
        return

    print(f"🚀 Iniciando conversión por lote ({len(found_files)} archivos encontrados)...")
    success_count = 0
    for f in found_files:
        res = process_single_file(f, open_when_done=False, generar_imagen=generar_imagen, generar_txt=generar_txt)
        if res:
            success_count += 1

    print(f"\n🏁 Proceso por lote finalizado: {success_count}/{len(found_files)} archivos convertidos con éxito.")

def main():
    if len(sys.argv) == 1:
        # Sin argumentos: Abrir Interfaz Gráfica
        print("Iniciando Interfaz Gráfica de App_conversor...")
        try:
            import app_gui
            app_gui.main()
        except Exception as e:
            print(f"No se pudo iniciar la interfaz gráfica: {e}")
            print("Ejecuta 'python App_conversor.py <archivo.pdf>' para modo consola.")
    elif sys.argv[1] == "--web":
        # Iniciar modo Web con Streamlit
        python_exe = sys.executable
        subprocess.run([python_exe, "-m", "streamlit", "run", "app_web.py"])
    elif sys.argv[1] == "--batch":
        folder = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "."
        gen_img = "--img" in sys.argv or "--all" in sys.argv
        gen_txt = "--txt" in sys.argv or "--all" in sys.argv
        process_batch(folder, generar_imagen=gen_img, generar_txt=gen_txt)
    elif sys.argv[1] in ["-h", "--help", "/?"]:
        print(__doc__)
    else:
        # Archivo específico
        pdf_file = sys.argv[1]
        gen_img = "--img" in sys.argv or "--all" in sys.argv
        gen_txt = "--txt" in sys.argv or "--all" in sys.argv
        process_single_file(pdf_file, open_when_done=True, generar_imagen=gen_img, generar_txt=gen_txt)

if __name__ == "__main__":
    main()
