"""
app_gui.py
Interfaz Gráfica de Escritorio (Desktop App) para App_conversor.
Permite seleccionar cronogramas PDF, ver el resumen financiero al instante
y generar el PDF ejecutivo con el formato oficial idéntico a PLANTILLA.pdf.
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import conversor_core

class AppConversorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("App Conversor - Estado de Cuenta Ejecutivo")
        self.root.geometry("640x580")
        self.root.minsize(580, 520)
        self.root.configure(bg="#f8fafc")

        self.selected_file = None
        self.generated_pdf = None

        self._create_styles()
        self._build_ui()

    def _create_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configuración de estilos
        self.style.configure(".", font=("Segoe UI", 9))
        self.style.configure("TFrame", background="#f8fafc")
        self.style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)

        self.style.configure("Primary.TButton",
                             font=("Segoe UI", 10, "bold"),
                             background="#0052cc",
                             foreground="#ffffff",
                             padding=8)
        self.style.map("Primary.TButton",
                       background=[("active", "#0041a8"), ("disabled", "#94a3b8")])

        self.style.configure("Secondary.TButton",
                             font=("Segoe UI", 9, "bold"),
                             background="#0f172a",
                             foreground="#ffffff",
                             padding=6)
        self.style.map("Secondary.TButton",
                       background=[("active", "#1e293b"), ("disabled", "#cbd5e1")])

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg="#0052cc", height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title_lbl = tk.Label(header, text="📄 App Conversor de Cronogramas",
                             font=("Segoe UI", 14, "bold"), bg="#0052cc", fg="#ffffff")
        title_lbl.pack(anchor="w", padx=20, pady=(12, 2))

        sub_lbl = tk.Label(header, text="Generador de Reportes Ejecutivos Oficiales (Formato Plantilla)",
                           font=("Segoe UI", 8), bg="#0052cc", fg="#bfdbfe")
        sub_lbl.pack(anchor="w", padx=20)

        # Contenedor principal
        main_frame = tk.Frame(self.root, bg="#f8fafc", padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Selector de archivo
        file_box = tk.LabelFrame(main_frame, text=" 1. Seleccionar Cronograma PDF ",
                                 font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a",
                                 padx=15, pady=12, relief="solid", bd=1)
        file_box.pack(fill=tk.X, pady=(0, 12))

        row1 = tk.Frame(file_box, bg="#ffffff")
        row1.pack(fill=tk.X)

        self.file_entry = tk.Entry(row1, font=("Segoe UI", 9), relief="solid", bd=1, bg="#f8fafc")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))

        browse_btn = ttk.Button(row1, text="Examinar...", command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT)

        # 2. Resumen detectado
        self.summary_box = tk.LabelFrame(main_frame, text=" 2. Datos Detectados del Cliente ",
                                         font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a",
                                         padx=15, pady=10, relief="solid", bd=1)
        self.summary_box.pack(fill=tk.X, pady=(0, 12))

        self.lbl_cliente = tk.Label(self.summary_box, text="Cliente: —", font=("Segoe UI", 9), bg="#ffffff", anchor="w")
        self.lbl_cliente.pack(fill=tk.X, pady=2)

        self.lbl_contrato = tk.Label(self.summary_box, text="Contrato: —  |  Identificación: —", font=("Segoe UI", 9), bg="#ffffff", anchor="w")
        self.lbl_contrato.pack(fill=tk.X, pady=2)

        self.lbl_kpis = tk.Label(self.summary_box, text="Estado: Selecciona un archivo PDF para comenzar.", font=("Segoe UI", 9, "italic"), fg="#64748b", bg="#ffffff", anchor="w")
        self.lbl_kpis.pack(fill=tk.X, pady=4)

        # 3. Opciones y botón de acción
        action_box = tk.Frame(main_frame, bg="#f8fafc")
        action_box.pack(fill=tk.X, pady=(0, 10))

        self.auto_open_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(action_box, text="Abrir el PDF automáticamente al finalizar la generación",
                             variable=self.auto_open_var, font=("Segoe UI", 8), bg="#f8fafc", activebackground="#f8fafc")
        chk.pack(anchor="w", pady=(0, 8))

        self.convert_btn = ttk.Button(action_box, text="🚀 Convertir y Generar PDF Oficial",
                                      style="Primary.TButton", command=self.convert_file)
        self.convert_btn.pack(fill=tk.X, ipady=3)

        # 4. Estado y Acciones posteriores
        self.result_box = tk.Frame(main_frame, bg="#f8fafc")
        self.result_box.pack(fill=tk.X, pady=(10, 0))

        self.status_lbl = tk.Label(self.result_box, text="Listo para procesar.", font=("Segoe UI", 8),
                                   fg="#475569", bg="#f8fafc", anchor="w")
        self.status_lbl.pack(fill=tk.X, pady=(0, 6))

        btn_row = tk.Frame(self.result_box, bg="#f8fafc")
        btn_row.pack(fill=tk.X)

        self.open_pdf_btn = ttk.Button(btn_row, text="📄 Abrir PDF Generado", command=self.open_pdf, state=tk.DISABLED)
        self.open_pdf_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.open_folder_btn = ttk.Button(btn_row, text="📁 Abrir Carpeta", command=self.open_folder, state=tk.DISABLED)
        self.open_folder_btn.pack(side=tk.LEFT)

    def browse_file(self):
        f = filedialog.askopenfilename(
            title="Seleccionar Cronograma PDF",
            filetypes=[("Archivos PDF (*.pdf)", "*.pdf"), ("Todos los archivos", "*.*")],
            initialdir=os.getcwd()
        )
        if f:
            self.selected_file = f
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, f)
            self._load_file_preview(f)

    def _load_file_preview(self, pdf_path):
        try:
            self.status_lbl.config(text="Analizando estructura del archivo...", fg="#0284c7")
            self.root.update_idletasks()
            data = conversor_core.extract_cronograma_data(pdf_path)
            analysis = conversor_core.analyze_and_classify_movements(data)

            self.lbl_cliente.config(text=f"Cliente: {data['nombre']}", font=("Segoe UI", 9, "bold"), fg="#0f172a")
            self.lbl_contrato.config(text=f"Contrato: {data['contrato']}  |  C.C: {data['identificacion']}  |  Saldo Actual: {data['saldo_actual']}")
            
            mora_txt = f"{analysis['mora_count']} Cuota(s) en Mora" if analysis['mora_count'] > 0 else "Al día (Sin Mora)"
            mora_color = "#dc2626" if analysis['mora_count'] > 0 else "#16a34a"
            
            kpi_summary = (
                f"Cuotas Cicladas: {analysis['cicladas_count']}  |  "
                f"Pagos: {analysis['pagos_count']} ({analysis['total_pagado_str']})  |  "
                f"{mora_txt}"
            )
            self.lbl_kpis.config(text=kpi_summary, font=("Segoe UI", 9, "bold"), fg=mora_color)
            self.status_lbl.config(text="Archivo válido. Haz clic en 'Convertir' para generar el PDF.", fg="#16a34a")
        except Exception as e:
            self.status_lbl.config(text=f"Aviso: {str(e)}", fg="#dc2626")

    def convert_file(self):
        path = self.file_entry.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Por favor selecciona un archivo PDF de cronograma existente.")
            return

        try:
            self.status_lbl.config(text="Generando PDF en formato oficial idéntico a PLANTILLA...", fg="#0052cc")
            self.convert_btn.config(state=tk.DISABLED)
            self.root.update_idletasks()

            dir_name = os.path.dirname(os.path.abspath(path))
            base_name = os.path.splitext(os.path.basename(path))[0]
            out_pdf = os.path.join(dir_name, f"Reporte_Ejecutivo_{base_name}.pdf")

            pdf_path, html_code, data, analysis = conversor_core.procesar_cronograma(path, out_pdf)
            self.generated_pdf = pdf_path

            self.status_lbl.config(text=f"✅ ¡PDF generado con éxito!: {os.path.basename(pdf_path)}", fg="#16a34a", font=("Segoe UI", 8, "bold"))
            self.open_pdf_btn.config(state=tk.NORMAL)
            self.open_folder_btn.config(state=tk.NORMAL)
            self.convert_btn.config(state=tk.NORMAL)

            if self.auto_open_var.get():
                self.open_pdf()

            messagebox.showinfo("Éxito", f"Reporte PDF generado exitosamente:\n\n{os.path.basename(pdf_path)}\n\nUbicación:\n{dir_name}")

        except Exception as e:
            self.convert_btn.config(state=tk.NORMAL)
            self.status_lbl.config(text=f"Error: {str(e)}", fg="#dc2626")
            messagebox.showerror("Error al procesar", f"Ocurrió un error al procesar el archivo:\n\n{str(e)}")

    def open_pdf(self):
        if self.generated_pdf and os.path.exists(self.generated_pdf):
            try:
                os.startfile(self.generated_pdf)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def open_folder(self):
        if self.generated_pdf and os.path.exists(self.generated_pdf):
            folder = os.path.dirname(os.path.abspath(self.generated_pdf))
            try:
                subprocess.run(["explorer", folder])
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

def main():
    root = tk.Tk()
    app = AppConversorGUI(root)
    # Si se pasó un archivo por argumento de línea de comandos, cargarlo directamente
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        app.selected_file = sys.argv[1]
        app.file_entry.insert(0, sys.argv[1])
        app._load_file_preview(sys.argv[1])
    root.mainloop()

if __name__ == "__main__":
    main()
