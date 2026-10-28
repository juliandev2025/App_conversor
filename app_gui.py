"""
app_gui.py
Interfaz Gráfica de Escritorio (Desktop App) para App_conversor.
Permite seleccionar cronogramas PDF, ver el resumen financiero al instante
y generar el PDF ejecutivo con el formato oficial idéntico a PLANTILLA.pdf.
"""

# ==========================================
# 1. IMPORTACIÓN DE LIBRERÍAS DEL SISTEMA Y GUI
# ==========================================
import os           # Para interactuar con rutas de archivos, carpetas y abrir documentos en el SO.
import sys          # Para capturar parámetros enviados por consola (ej. 'python app_gui.py archivo.pdf').
import subprocess   # Para ejecutar comandos del sistema (ej. abrir el Explorador de archivos de Windows).
import tkinter as tk  # Librería nativa estándar de interfaces de ventanas en Python.
from tkinter import ttk, filedialog, messagebox  # Widgets modernos (ttk), selector de archivos y ventanas de alerta.

# Importa el motor que contiene la lógica de extracción, análisis financiero y compilación del PDF.
import conversor_core


# ==========================================
# 2. CLASE PRINCIPAL DE LA INTERFAZ DE USUARIO
# ==========================================
class AppConversorGUI:
    def __init__(self, root):
        """
        Constructor principal: inicializa la ventana base, define dimensiones,
        colores de fondo y ejecuta la construcción gráfica de los elementos.
        """
        self.root = root
        self.root.title("App Conversor - Estado de Cuenta Ejecutivo")
        
        # Dimensiones iniciales y límites mínimos para que la ventana no se deforme al redimensionar
        self.root.geometry("640x580")
        self.root.minsize(580, 520)
        self.root.configure(bg="#f8fafc")  # Fondo gris neutro claro moderno (estilo Tailwind/Slate)

        # Variables internas de estado de la aplicación
        self.selected_file = None   # Almacenará la ruta del archivo PDF que el usuario seleccione.
        self.generated_pdf = None   # Almacenará la ruta del nuevo PDF ejecutivo generado con éxito.

        # Métodos de inicialización visual
        self._create_styles()
        self._build_ui()

    # ----------------------------------------------------
    # CONFIGURACIÓN VISUAL Y TEMAS
    # ----------------------------------------------------
    def _create_styles(self):
        """
        Personaliza los estilos de los controles modernos (ttk) usando el motor de temas 'clam'
        para definir colores corporativos, bordes y comportamientos al interactuar (hover/disabled).
        """
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configuración tipográfica general del sistema
        self.style.configure(".", font=("Segoe UI", 9))
        self.style.configure("TFrame", background="#f8fafc")
        self.style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)

        # Botón principal (Acción de Convertir): Color azul corporativo #0052cc
        self.style.configure("Primary.TButton",
                             font=("Segoe UI", 10, "bold"),
                             background="#0052cc",
                             foreground="#ffffff",
                             padding=8)
        # Cambio de tono al pasar el mouse por encima (active) o si está deshabilitado (disabled)
        self.style.map("Primary.TButton",
                       background=[("active", "#0041a8"), ("disabled", "#94a3b8")])

        # Botón secundario: Tono oscuro pizarra #0f172a
        self.style.configure("Secondary.TButton",
                             font=("Segoe UI", 9, "bold"),
                             background="#0f172a",
                             foreground="#ffffff",
                             padding=6)
        self.style.map("Secondary.TButton",
                       background=[("active", "#1e293b"), ("disabled", "#cbd5e1")])

    # ----------------------------------------------------
    # CONSTRUCCIÓN DE LA ESTRUCTURA GRÁFICA (LAYOUT)
    # ----------------------------------------------------
    def _build_ui(self):
        """
        Dibuja los 4 bloques principales de la interfaz:
        1. Encabezado institucional azul superior.
        2. Bloque de selección de archivo PDF.
        3. Bloque de previsualización de datos extraídos y KPIs.
        4. Opciones de conversión, barra de progreso y acciones finales.
        """
        # --- ENCABEZADO SUPERIOR AZUL ---
        header = tk.Frame(self.root, bg="#0052cc", height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)  # Evita que el contenedor colapse al tamaño de sus etiquetas internas

        # Título principal de la aplicación
        title_lbl = tk.Label(header, text="📄 App Conversor de Cronogramas",
                             font=("Segoe UI", 14, "bold"), bg="#0052cc", fg="#ffffff")
        title_lbl.pack(anchor="w", padx=20, pady=(12, 2))

        # Subtítulo descriptivo en tono azul suave
        sub_lbl = tk.Label(header, text="Generador de Reportes Ejecutivos Oficiales (Formato Plantilla)",
                           font=("Segoe UI", 8), bg="#0052cc", fg="#bfdbfe")
        sub_lbl.pack(anchor="w", padx=20)

        # --- CONTENEDOR CENTRAL BLANCO/GRIS ---
        main_frame = tk.Frame(self.root, bg="#f8fafc", padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- BLOQUE 1: SELECTOR DE ARCHIVO PDF ---
        file_box = tk.LabelFrame(main_frame, text=" 1. Seleccionar Cronograma PDF ",
                                 font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a",
                                 padx=15, pady=12, relief="solid", bd=1)
        file_box.pack(fill=tk.X, pady=(0, 12))

        row1 = tk.Frame(file_box, bg="#ffffff")
        row1.pack(fill=tk.X)

        # Campo de texto que muestra la ruta del archivo seleccionado
        self.file_entry = tk.Entry(row1, font=("Segoe UI", 9), relief="solid", bd=1, bg="#f8fafc")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))

        # Botón para abrir la ventana de exploración de carpetas de Windows
        browse_btn = ttk.Button(row1, text="Examinar...", command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT)

        # --- BLOQUE 2: RESUMEN FINANCIERO DETECTADO ---
        self.summary_box = tk.LabelFrame(main_frame, text=" 2. Datos Detectados del Cliente ",
                                         font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a",
                                         padx=15, pady=10, relief="solid", bd=1)
        self.summary_box.pack(fill=tk.X, pady=(0, 12))

        # Etiquetas dinámicas donde se inyectan los datos tras leer el PDF
        self.lbl_cliente = tk.Label(self.summary_box, text="Cliente: —", font=("Segoe UI", 9), bg="#ffffff", anchor="w")
        self.lbl_cliente.pack(fill=tk.X, pady=2)

        self.lbl_contrato = tk.Label(self.summary_box, text="Contrato: —  |  Identificación: —", font=("Segoe UI", 9), bg="#ffffff", anchor="w")
        self.lbl_contrato.pack(fill=tk.X, pady=2)

        self.lbl_kpis = tk.Label(self.summary_box, text="Estado: Selecciona un archivo PDF para comenzar.", font=("Segoe UI", 9, "italic"), fg="#64748b", bg="#ffffff", anchor="w")
        self.lbl_kpis.pack(fill=tk.X, pady=4)

        # --- BLOQUE 3: BOTÓN DE ACCIÓN Y OPCIONES ---
        action_box = tk.Frame(main_frame, bg="#f8fafc")
        action_box.pack(fill=tk.X, pady=(0, 10))

        # Casilla de verificación: si está activa, el PDF se abre en pantalla automáticamente al terminar
        self.auto_open_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(action_box, text="Abrir el PDF automáticamente al finalizar la generación",
                             variable=self.auto_open_var, font=("Segoe UI", 8), bg="#f8fafc", activebackground="#f8fafc")
        chk.pack(anchor="w", pady=(0, 8))

        # Botón principal de conversión que desencadena el proceso completo
        self.convert_btn = ttk.Button(action_box, text="🚀 Convertir y Generar PDF Oficial",
                                      style="Primary.TButton", command=self.convert_file)
        self.convert_btn.pack(fill=tk.X, ipady=3)

        # --- BLOQUE 4: BARRA DE ESTADO Y ACCIONES POSTERIORES ---
        self.result_box = tk.Frame(main_frame, bg="#f8fafc")
        self.result_box.pack(fill=tk.X, pady=(10, 0))

        # Mensaje de retroalimentación en tiempo real para el usuario
        self.status_lbl = tk.Label(self.result_box, text="Listo para procesar.", font=("Segoe UI", 8),
                                   fg="#475569", bg="#f8fafc", anchor="w")
        self.status_lbl.pack(fill=tk.X, pady=(0, 6))

        btn_row = tk.Frame(self.result_box, bg="#f8fafc")
        btn_row.pack(fill=tk.X)

        # Botón para volver a abrir el PDF generado (inicia deshabilitado hasta que se cree uno)
        self.open_pdf_btn = ttk.Button(btn_row, text="📄 Abrir PDF Generado", command=self.open_pdf, state=tk.DISABLED)
        self.open_pdf_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Botón para abrir la carpeta donde se guardó el resultado (inicia deshabilitado)
        self.open_folder_btn = ttk.Button(btn_row, text="📁 Abrir Carpeta", command=self.open_folder, state=tk.DISABLED)
        self.open_folder_btn.pack(side=tk.LEFT)

    # ----------------------------------------------------
    # MÉTODOS DE MANEJO DE EVENTOS Y PROCESAMIENTO
    # ----------------------------------------------------
    def browse_file(self):
        """
        Abre el explorador de Windows para que el usuario elija un archivo PDF.
        Si selecciona uno, actualiza la caja de texto y lanza la previsualización inmediata.
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
        para pintar el resumen en pantalla (Cliente, Cédula, Contrato, si tiene mora o no).
        """
        try:
            self.status_lbl.config(text="Analizando estructura del archivo...", fg="#0284c7")
            self.root.update_idletasks()  # Fuerza a Tkinter a repintar la ventana inmediatamente

            # 1. Extrae los campos de texto del PDF crudo (expresiones regulares + tablas)
            data = conversor_core.extract_cronograma_data(pdf_path)
            # 2. Evalúa las reglas financieras (fechas vs corte, cuotas cicladas, pagos y moras)
            analysis = conversor_core.analyze_and_classify_movements(data)

            # Inyecta los datos del cliente en las etiquetas del bloque 2
            self.lbl_cliente.config(text=f"Cliente: {data['nombre']}", font=("Segoe UI", 9, "bold"), fg="#0f172a")
            self.lbl_contrato.config(text=f"Contrato: {data['contrato']}  |  C.C: {data['identificacion']}  |  Saldo Actual: {data['saldo_actual']}")
            
            # Formatea el estado de mora: rojo si debe cuotas pasadas, verde si está al día
            mora_txt = f"{analysis['mora_count']} Cuota(s) en Mora" if analysis['mora_count'] > 0 else "Al día (Sin Mora)"
            mora_color = "#dc2626" if analysis['mora_count'] > 0 else "#16a34a"
            
            # Construye el texto consolidado con los indicadores clave (KPIs)
            kpi_summary = (
                f"Cuotas Cicladas: {analysis['cicladas_count']}  |  "
                f"Pagos: {analysis['pagos_count']} ({analysis['total_pagado_str']})  |  "
                f"{mora_txt}"
            )
            self.lbl_kpis.config(text=kpi_summary, font=("Segoe UI", 9, "bold"), fg=mora_color)
            self.status_lbl.config(text="Archivo válido. Haz clic en 'Convertir' para generar el PDF.", fg="#16a34a")

        except Exception as e:
            # Si el PDF no es un cronograma válido o está dañado, reporta el aviso en rojo
            self.status_lbl.config(text=f"Aviso: {str(e)}", fg="#dc2626")

    def convert_file(self):
        """
        Proceso de conversión principal:
        - Valida la existencia del archivo de entrada.
        - Define la ruta de salida con el prefijo 'Reporte_Ejecutivo_'.
        - Invoca el motor de renderizado HTML -> PDF.
        - Habilita botones secundarios y abre el PDF automáticamente si está marcado el check.
        """
        path = self.file_entry.get().strip()
        # Validación de seguridad: que el archivo exista en el disco
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Por favor selecciona un archivo PDF de cronograma existente.")
            return

        try:
            self.status_lbl.config(text="Generando PDF en formato oficial idéntico a PLANTILLA...", fg="#0052cc")
            self.convert_btn.config(state=tk.DISABLED)  # Deshabilita el botón para evitar doble clic accidental
            self.root.update_idletasks()

            # Construye el nombre del archivo de salida en el mismo directorio del original
            dir_name = os.path.dirname(os.path.abspath(path))
            base_name = os.path.splitext(os.path.basename(path))[0]
            out_pdf = os.path.join(dir_name, f"Reporte_Ejecutivo_{base_name}.pdf")

            # Ejecuta la extracción, generación del HTML paginado y compilación vectorial en PDF
            pdf_path, html_code, data, analysis = conversor_core.procesar_cronograma(path, out_pdf)
            self.generated_pdf = pdf_path

            # Actualiza el estado a completado y reactiva los controles
            self.status_lbl.config(text=f"✅ ¡PDF generado con éxito!: {os.path.basename(pdf_path)}", fg="#16a34a", font=("Segoe UI", 8, "bold"))
            self.open_pdf_btn.config(state=tk.NORMAL)
            self.open_folder_btn.config(state=tk.NORMAL)
            self.convert_btn.config(state=tk.NORMAL)

            # Si la casilla de auto-apertura está seleccionada, abre el PDF en el visor del sistema
            if self.auto_open_var.get():
                self.open_pdf()

            # Notificación emergente de éxito con ruta de almacenamiento
            messagebox.showinfo("Éxito", f"Reporte PDF generado exitosamente:\n\n{os.path.basename(pdf_path)}\n\nUbicación:\n{dir_name}")

        except Exception as e:
            # En caso de fallo, reactiva el botón y muestra la ventana de error
            self.convert_btn.config(state=tk.NORMAL)
            self.status_lbl.config(text=f"Error: {str(e)}", fg="#dc2626")
            messagebox.showerror("Error al procesar", f"Ocurrió un error al procesar el archivo:\n\n{str(e)}")

    def open_pdf(self):
        """
        Abre el archivo PDF recién generado en el lector predeterminado del sistema (Acrobat, Edge, etc.).
        """
        if self.generated_pdf and os.path.exists(self.generated_pdf):
            try:
                os.startfile(self.generated_pdf)  # Método nativo de Windows para ejecutar el archivo con su app asociada
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def open_folder(self):
        """
        Abre la carpeta contenedora en el Explorador de archivos de Windows.
        """
        if self.generated_pdf and os.path.exists(self.generated_pdf):
            folder = os.path.dirname(os.path.abspath(self.generated_pdf))
            try:
                subprocess.run(["explorer", folder])  # Ejecuta explorer.exe en la ruta indicada
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")


# ==========================================
# 3. PUNTO DE ENTRADA (MAIN)
# ==========================================
def main():
    """
    Función de arranque: instancia la ventana de Tkinter y revisa si se le pasó
    un archivo PDF como parámetro al ejecutar el script desde consola o archivo por lotes (.bat).
    """
    root = tk.Tk()
    app = AppConversorGUI(root)
    
    # Si se arrastró un PDF sobre el .bat o se pasó por terminal (ej. python app_gui.py archivo.pdf),
    # lo carga y analiza automáticamente sin necesidad de dar clic en 'Examinar'
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        app.selected_file = sys.argv[1]
        app.file_entry.insert(0, sys.argv[1])
        app._load_file_preview(sys.argv[1])
        
    root.mainloop()  # Bucle principal que mantiene la ventana abierta a la espera de eventos

if __name__ == "__main__":
    main()