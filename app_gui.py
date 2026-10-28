"""
app_gui.py
Interfaz Grafica de Escritorio (Desktop App) para App_conversor.
Permite seleccionar cronogramas PDF, ver el resumen financiero al instante
y generar el PDF ejecutivo con el formato oficial identico a PLANTILLA.pdf.
Soporta exportacion adicional a imagen PNG de alta calidad y archivo TXT.
"""

# ==========================================
# 1. IMPORTACION DE LIBRERIAS DEL SISTEMA Y GUI
# ==========================================
import os           # Para interactuar con rutas de archivos, carpetas y abrir documentos en el SO.
import sys          # Para capturar parametros enviados por consola (ej. 'python app_gui.py archivo.pdf').
import subprocess   # Para ejecutar comandos del sistema (ej. abrir el Explorador de archivos de Windows).
import tkinter as tk  # Libreria nativa estandar de interfaces de ventanas en Python.
from tkinter import ttk, filedialog, messagebox  # Widgets modernos (ttk), selector de archivos y ventanas de alerta.

# Importa el motor que contiene la logica de extraccion, analisis financiero y compilacion del PDF.
import conversor_core
try:
    import logo_data
    from PIL import Image, ImageTk
except ImportError:
    logo_data = None


# ==========================================
# 2. CLASE PRINCIPAL DE LA INTERFAZ DE USUARIO
# ==========================================
class AppConversorGUI:
    def __init__(self, root):
        """
        Constructor principal: inicializa la ventana base, define dimensiones,
        colores de fondo y ejecuta la construccion grafica de los elementos.
        """
        self.root = root
        self.root.title("KrediYA - App Conversor de Cronogramas")

        # Icono de la ventana
        self.icon_tk = None
        self.logo_tk = None
        if logo_data:
            try:
                self.icon_tk = ImageTk.PhotoImage(logo_data.get_krediya_logo_pil())
                self.root.iconphoto(False, self.icon_tk)
            except Exception:
                pass

        # Dimensiones iniciales y limites minimos para que la ventana no se deforme al redimensionar
        self.root.geometry("680x680")
        self.root.minsize(620, 600)
        self.root.configure(bg="#f8fafc")  # Fondo gris neutro claro moderno

        # Variables internas de estado de la aplicacion
        self.selected_file  = None   # Ruta del archivo PDF seleccionado.
        self.generated_pdf  = None   # Ruta del PDF ejecutivo generado.
        self.generated_images = []   # Lista de rutas de imagenes PNG generadas.
        self.generated_txt  = None   # Ruta del archivo TXT generado.

        # Metodos de inicializacion visual
        self._create_styles()
        self._build_ui()

    # ----------------------------------------------------
    # CONFIGURACION VISUAL Y TEMAS
    # ----------------------------------------------------
    def _create_styles(self):
        """
        Personaliza los estilos de los controles modernos (ttk) usando el motor de temas 'clam'
        para definir colores corporativos, bordes y comportamientos al interactuar.
        """
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configuracion tipografica general del sistema
        self.style.configure(".", font=("Segoe UI", 9))
        self.style.configure("TFrame", background="#f8fafc")
        self.style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)

        # Boton principal (Accion de Convertir): Color azul corporativo #0052cc
        self.style.configure("Primary.TButton",
                             font=("Segoe UI", 10, "bold"),
                             background="#0052cc",
                             foreground="#ffffff",
                             padding=8)
        self.style.map("Primary.TButton",
                       background=[("active", "#0041a8"), ("disabled", "#94a3b8")])

        # Boton secundario: Tono oscuro pizarra #0f172a
        self.style.configure("Secondary.TButton",
                             font=("Segoe UI", 9, "bold"),
                             background="#0f172a",
                             foreground="#ffffff",
                             padding=6)
        self.style.map("Secondary.TButton",
                       background=[("active", "#1e293b"), ("disabled", "#cbd5e1")])

    # ----------------------------------------------------
    # CONSTRUCCION DE LA ESTRUCTURA GRAFICA (LAYOUT)
    # ----------------------------------------------------
    def _build_ui(self):
        """
        Dibuja los bloques principales de la interfaz:
        1. Encabezado institucional azul superior.
        2. Bloque de seleccion de archivo PDF.
        3. Bloque de previsualizacion de datos extraidos y KPIs.
        4. Opciones de exportacion (PDF + imagen + TXT).
        5. Barra de estado y acciones finales.
        """
        # --- ENCABEZADO SUPERIOR CON LOGO KREDIYA ---
        header = tk.Frame(self.root, bg="#ffffff", height=78, relief="solid", bd=1)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Cargar logo de KrediYA a la izquierda
        if logo_data:
            try:
                logo_pil = logo_data.get_krediya_logo_pil()
                w, h = logo_pil.size
                new_h = 38
                new_w = int(w * (new_h / h))
                logo_resized = logo_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
                self.logo_tk = ImageTk.PhotoImage(logo_resized)

                logo_lbl = tk.Label(header, image=self.logo_tk, bg="#ffffff")
                logo_lbl.pack(side=tk.LEFT, padx=(20, 14), pady=12)

                # Divisor vertical elegante
                sep = tk.Frame(header, bg="#cbd5e1", width=1, height=40)
                sep.pack(side=tk.LEFT, fill=tk.Y, pady=18, padx=(0, 14))
            except Exception:
                self.logo_tk = None

        text_frame = tk.Frame(header, bg="#ffffff")
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=14)

        title_lbl = tk.Label(text_frame, text="App Conversor de Cronogramas",
                             font=("Segoe UI", 13, "bold"), bg="#ffffff", fg="#0f172a")
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(text_frame, text="Estado de Cuenta Ejecutivo - Formato Institucional",
                           font=("Segoe UI", 8), bg="#ffffff", fg="#64748b")
        sub_lbl.pack(anchor="w")

        # --- CONTENEDOR CENTRAL ---
        main_frame = tk.Frame(self.root, bg="#f8fafc", padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- BLOQUE 1: SELECTOR DE ARCHIVO PDF ---
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

        # --- BLOQUE 2: RESUMEN FINANCIERO DETECTADO ---
        self.summary_box = tk.LabelFrame(main_frame, text=" 2. Datos Detectados del Cliente ",
                                         font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a",
                                         padx=15, pady=10, relief="solid", bd=1)
        self.summary_box.pack(fill=tk.X, pady=(0, 12))

        self.lbl_cliente = tk.Label(self.summary_box, text="Cliente: \u2014", font=("Segoe UI", 9), bg="#ffffff", anchor="w")
        self.lbl_cliente.pack(fill=tk.X, pady=2)

        self.lbl_contrato = tk.Label(self.summary_box, text="Contrato: \u2014  |  Identificacion: \u2014",
                                     font=("Segoe UI", 9), bg="#ffffff", anchor="w")
        self.lbl_contrato.pack(fill=tk.X, pady=2)

        self.lbl_kpis = tk.Label(self.summary_box, text="Estado: Selecciona un archivo PDF para comenzar.",
                                 font=("Segoe UI", 9, "italic"), fg="#64748b", bg="#ffffff", anchor="w")
        self.lbl_kpis.pack(fill=tk.X, pady=4)

        # --- BLOQUE 3: OPCIONES DE EXPORTACION ---
        action_box = tk.Frame(main_frame, bg="#f8fafc")
        action_box.pack(fill=tk.X, pady=(0, 10))

        # Auto-apertura del PDF al terminar
        self.auto_open_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(action_box,
                             text="Abrir el PDF automaticamente al finalizar la generacion",
                             variable=self.auto_open_var,
                             font=("Segoe UI", 8), bg="#f8fafc", activebackground="#f8fafc")
        chk.pack(anchor="w", pady=(0, 4))

        # Sub-panel de exportaciones adicionales
        export_frame = tk.LabelFrame(action_box, text=" Exportar adicionalmente: ",
                                     font=("Segoe UI", 8, "bold"), bg="#f8fafc", fg="#334155",
                                     padx=12, pady=8, relief="solid", bd=1)
        export_frame.pack(fill=tk.X, pady=(0, 8))

        self.export_img_var = tk.BooleanVar(value=False)
        chk_img = tk.Checkbutton(
            export_frame,
            text="Imagen PNG de alta calidad (200 DPI) \u2014 misma presentacion visual que el PDF",
            variable=self.export_img_var,
            font=("Segoe UI", 8), bg="#f8fafc", activebackground="#f8fafc"
        )
        chk_img.pack(anchor="w", pady=(0, 2))

        self.export_txt_var = tk.BooleanVar(value=False)
        chk_txt = tk.Checkbutton(
            export_frame,
            text="Archivo de texto plano (.txt) \u2014 resumen legible para copiar o enviar por chat",
            variable=self.export_txt_var,
            font=("Segoe UI", 8), bg="#f8fafc", activebackground="#f8fafc"
        )
        chk_txt.pack(anchor="w")

        # Boton principal de conversion
        self.convert_btn = ttk.Button(action_box, text="  Convertir y Generar Reporte",
                                       style="Primary.TButton", command=self.convert_file)
        self.convert_btn.pack(fill=tk.X, ipady=3)

        # --- BLOQUE 4: BARRA DE ESTADO Y ACCIONES POSTERIORES ---
        self.result_box = tk.Frame(main_frame, bg="#f8fafc")
        self.result_box.pack(fill=tk.X, pady=(10, 0))

        self.status_lbl = tk.Label(self.result_box, text="Listo para procesar.",
                                   font=("Segoe UI", 8), fg="#475569", bg="#f8fafc", anchor="w")
        self.status_lbl.pack(fill=tk.X, pady=(0, 6))

        btn_row = tk.Frame(self.result_box, bg="#f8fafc")
        btn_row.pack(fill=tk.X)

        self.open_pdf_btn = ttk.Button(btn_row, text="  Abrir PDF Generado",
                                       command=self.open_pdf, state=tk.DISABLED)
        self.open_pdf_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_img_btn = ttk.Button(btn_row, text="  Ver Imagen",
                                       command=self.open_image, state=tk.DISABLED)
        self.open_img_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_txt_btn = ttk.Button(btn_row, text="  Ver TXT",
                                       command=self.open_txt, state=tk.DISABLED)
        self.open_txt_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_folder_btn = ttk.Button(btn_row, text="  Abrir Carpeta",
                                          command=self.open_folder, state=tk.DISABLED)
        self.open_folder_btn.pack(side=tk.LEFT)

    # ----------------------------------------------------
    # METODOS DE MANEJO DE EVENTOS Y PROCESAMIENTO
    # ----------------------------------------------------
    def browse_file(self):
        """
        Abre el explorador de Windows para que el usuario elija un archivo PDF.
        Si selecciona uno, actualiza la caja de texto y lanza la previsualizacion inmediata.
        """
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
        """
        Lee el PDF en segundo plano usando 'conversor_core', extrae metadatos y clasifica cuotas
        para pintar el resumen en pantalla (Cliente, Cedula, Contrato, mora).
        """
        try:
            self.status_lbl.config(text="Analizando estructura del archivo...", fg="#0284c7")
            self.root.update_idletasks()

            data     = conversor_core.extract_cronograma_data(pdf_path)
            analysis = conversor_core.analyze_and_classify_movements(data)

            self.lbl_cliente.config(
                text=f"Cliente: {data['nombre']}",
                font=("Segoe UI", 9, "bold"), fg="#0f172a"
            )
            self.lbl_contrato.config(
                text=f"Contrato: {data['contrato']}  |  C.C: {data['identificacion']}  |  Saldo Actual: {data['saldo_actual']}"
            )

            mora_txt   = f"{analysis['mora_count']} Cuota(s) en Mora" if analysis['mora_count'] > 0 else "Al dia (Sin Mora)"
            mora_color = "#dc2626" if analysis['mora_count'] > 0 else "#16a34a"
            kpi_summary = (
                f"Cuotas Cicladas: {analysis['cicladas_count']}  |  "
                f"Pagos: {analysis['pagos_count']} ({analysis['total_pagado_str']})  |  "
                f"{mora_txt}"
            )
            self.lbl_kpis.config(text=kpi_summary, font=("Segoe UI", 9, "bold"), fg=mora_color)
            self.status_lbl.config(
                text="Archivo valido. Configura las opciones y haz clic en 'Convertir'.", fg="#16a34a"
            )
        except Exception as e:
            self.status_lbl.config(text=f"Aviso: {str(e)}", fg="#dc2626")

    def convert_file(self):
        """
        Proceso de conversion principal:
        - Valida el archivo.
        - Llama a procesar_cronograma con las opciones elegidas.
        - Habilita botones de apertura segun los archivos generados.
        """
        path = self.file_entry.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Por favor selecciona un archivo PDF de cronograma existente.")
            return

        try:
            gen_img = self.export_img_var.get()
            gen_txt = self.export_txt_var.get()

            extras = []
            if gen_img: extras.append("imagen PNG")
            if gen_txt: extras.append("TXT")
            extra_str = f" + {', '.join(extras)}" if extras else ""
            self.status_lbl.config(
                text=f"Generando PDF{extra_str} en formato oficial...", fg="#0052cc"
            )
            self.convert_btn.config(state=tk.DISABLED)
            self.root.update_idletasks()

            dir_name  = os.path.dirname(os.path.abspath(path))
            base_name = os.path.splitext(os.path.basename(path))[0]
            out_pdf   = os.path.join(dir_name, f"Reporte_Ejecutivo_{base_name}.pdf")

            # Llamada al motor con opciones de exportacion
            resultado = conversor_core.procesar_cronograma(
                path, out_pdf,
                generar_imagen=gen_img,
                generar_txt=gen_txt,
                imagen_dpi=200
            )

            self.generated_pdf    = resultado["pdf_path"]
            self.generated_images = resultado.get("imagenes", [])
            self.generated_txt    = resultado.get("txt_path")

            # Construir mensaje de resumen de archivos creados
            archivos_creados = [f"PDF: {os.path.basename(self.generated_pdf)}"]
            if self.generated_images:
                for img in self.generated_images:
                    archivos_creados.append(f"IMG: {os.path.basename(img)}")
            if self.generated_txt:
                archivos_creados.append(f"TXT: {os.path.basename(self.generated_txt)}")

            img_err = resultado.get("imagen_error")
            if img_err:
                archivos_creados.append(f"[!] Error imagen: {img_err}")

            self.status_lbl.config(
                text=f"Generado: {' | '.join(archivos_creados)}",
                fg="#16a34a", font=("Segoe UI", 8, "bold")
            )
            self.open_pdf_btn.config(state=tk.NORMAL)
            self.open_folder_btn.config(state=tk.NORMAL)

            if self.generated_images:
                self.open_img_btn.config(state=tk.NORMAL)
            if self.generated_txt:
                self.open_txt_btn.config(state=tk.NORMAL)

            self.convert_btn.config(state=tk.NORMAL)

            if self.auto_open_var.get():
                self.open_pdf()

            messagebox.showinfo(
                "Exito",
                "Archivos generados exitosamente:\n\n" +
                "\n".join(archivos_creados) +
                f"\n\nUbicacion:\n{dir_name}"
            )

        except Exception as e:
            self.convert_btn.config(state=tk.NORMAL)
            self.status_lbl.config(text=f"Error: {str(e)}", fg="#dc2626")
            messagebox.showerror("Error al procesar", f"Ocurrio un error al procesar el archivo:\n\n{str(e)}")

    def open_pdf(self):
        """Abre el PDF en el visor predeterminado del sistema."""
        if self.generated_pdf and os.path.exists(self.generated_pdf):
            try:
                os.startfile(self.generated_pdf)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def open_image(self):
        """Abre la(s) imagen(es) PNG generadas en el visor predeterminado del sistema."""
        if self.generated_images:
            for img_path in self.generated_images:
                if os.path.exists(img_path):
                    try:
                        os.startfile(img_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo abrir la imagen: {e}")
        else:
            messagebox.showinfo("Info", "No se genero imagen. Marca la opcion antes de convertir.")

    def open_txt(self):
        """Abre el archivo TXT en el editor de texto predeterminado del sistema."""
        if self.generated_txt and os.path.exists(self.generated_txt):
            try:
                os.startfile(self.generated_txt)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el TXT: {e}")
        else:
            messagebox.showinfo("Info", "No se genero TXT. Marca la opcion antes de convertir.")

    def open_folder(self):
        """Abre la carpeta contenedora en el Explorador de Windows."""
        if self.generated_pdf and os.path.exists(self.generated_pdf):
            folder = os.path.dirname(os.path.abspath(self.generated_pdf))
            try:
                subprocess.run(["explorer", folder])
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")


# ==========================================
# 3. PUNTO DE ENTRADA (MAIN)
# ==========================================
def main():
    """
    Funcion de arranque: instancia la ventana de Tkinter y revisa si se le paso
    un archivo PDF como parametro al ejecutar el script desde consola o archivo .bat.
    """
    root = tk.Tk()
    app = AppConversorGUI(root)

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        app.selected_file = sys.argv[1]
        app.file_entry.insert(0, sys.argv[1])
        app._load_file_preview(sys.argv[1])

    root.mainloop()


if __name__ == "__main__":
    main()
