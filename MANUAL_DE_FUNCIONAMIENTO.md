# 📘 Manual de Funcionamiento y Documentación Técnica
## App_conversor: Generador de Reportes Ejecutivos de Estado de Cuenta

---

### 1. Introducción y Propósito
El área de **Soporte a Tiendas y Clientes** de plataformas de crédito (como KrediYA) recibe a diario consultas sobre estados de cuenta. Los cronogramas descargados directamente del CRM suelen generar confusión porque:
- Mezclan en una misma tabla las cuotas ya vencidas con las cuotas futuras de meses venideros.
- Registran intentos de pago declinados o fallidos que los clientes confunden con abonos reales.
- No clarifican de forma directa el número de cuotas que faltan por pagar ni el progreso real del crédito.

**App_conversor** automatiza la transformación de esos cronogramas en bruto (`cronograma_*.pdf`) en un **Reporte Ejecutivo de Estado de Cuenta e Historial**, estructurado, estético y con el diseño exacto de la plantilla institucional de control interno.

---

### 2. Arquitectura de Archivos del Sistema

Todos los archivos del aplicativo se encuentran en:
`c:\Users\Julián Felipe\Downloads\Generador\`

| Archivo | Tipo | Responsabilidad / Función |
| :--- | :--- | :--- |
| **`conversor_core.py`** | Motor Principal | Contiene la lógica de extracción con `pdfplumber`, las reglas de negocio financieras, el motor de clasificación y el compilador de HTML a PDF. |
| **`App_conversor.py`** | Lanzador Unificado / CLI | Permite ejecutar la aplicación por consola, en modo por lote (`--batch`) o en modo web (`--web`). Si se ejecuta sin parámetros, abre la interfaz de escritorio. |
| **`app_gui.py`** | Interfaz de Escritorio | Ventana gráfica nativa de Windows (Tkinter) para seleccionar cronogramas con 1 clic y abrir el PDF automáticamente. |
| **`app_web.py`** | Interfaz Web | Panel web interactivo con Streamlit para arrastrar PDFs, ver métricas en tiempo real y previsualizar el documento antes de descargarlo. |
| **`INICIAR_APP_ESCRITORIO.bat`** | Lanzador Windows | Acceso directo para iniciar la interfaz gráfica de escritorio con doble clic. |
| **`INICIAR_APP_WEB.bat`** | Lanzador Windows | Acceso directo para iniciar la versión web en el navegador con doble clic. |
| **`README.md`** | Guía de Inicio Rápido | Instrucciones breves y comandos básicos de uso. |

---

### 3. Flujo de Funcionamiento Paso a Paso

```
[ Cronograma CRM (.pdf) ]
          │
          ▼
1. EXTRACCIÓN (pdfplumber)
   ├─ Extrae metadatos (Cliente, Cédula, Contrato, Saldos, Fechas)
   └─ Extrae filas de la tabla de movimientos
          │
          ▼
2. MOTOR DE REGLAS FINANCIERAS
   ├─ Compara fecha de cuota vs Fecha de Consulta
   ├─ Clasifica: Ciclada / Pagada / Mora / Futura / Rechazo
   ├─ Totaliza pagos verificados
   └─ Redacta la conclusión en "REVISIÓN DE SOPORTE"
          │
          ▼
3. MAQUETACIÓN VISUAL (HTML/CSS Dinámico)
   ├─ Inserta tarjetas de KPI y badges de colores
   ├─ Paginación inteligente (Parte 1: pág 1 | Parte 2: pág 2)
   └─ Pie de página limpio con solo numeración ("Página X de Y")
          │
          ▼
4. GENERACIÓN DE PDF VECTORIAL
   └─ Motor Chromium / Edge Headless (Skia/PDF nativo)
          │
          ▼
[ Reporte_Ejecutivo_*.pdf ] -> Apertura automática / Descarga
```

---

### 4. Lógica de Clasificación Financiera

El motor interno (`conversor_core.py`) procesa cada movimiento bajo las siguientes reglas:

#### A. Identificación de Metadatos
Se detectan mediante expresiones regulares sobre el encabezado:
- **Cliente:** Nombre completo del titular.
- **Identificación:** Cédula / Documento de identidad.
- **Contrato No.:** Identificador alfanumérico del crédito.
- **Fecha de Consulta:** Fecha y hora en la que se generó el cronograma del CRM. Determina el corte de vencimiento.
- **Saldo Pendiente:** Deuda total restante hasta finalizar la última cuota.
- **Saldo Actual:** Valor vencido exigible a la fecha (en mora).
- **Próximo Pago y Pagar Antes De:** Monto y fecha límite de la próxima cuota.

#### B. Clasificación de Cuotas y Pagos
1. **Cuota Ciclada (`CICLADA`):**
   - Una cuota se considera ciclada si su fecha de vencimiento es **menor o igual a la fecha de consulta** (o si el CRM la marca con un asterisco `*`).
   - Si el número de cuota está cubierto por los pagos verificados del cliente, su estado es **`Registrada`**.
   - Si no cuenta con pago que la cubra, su estado cambia automáticamente a **`Pendiente / Mora`** y su valor se resalta en **rojo negrita**.
2. **Pago Verificado (`PAGO`):**
   - Movimientos cuyo concepto incluye "Pago" y su estado en el CRM es **`Verificado`**.
   - Se muestra con la insignia verde `PAGO`, el valor en verde (`-$117,512.00`), saldo en `$0.00` y el check `✔ Verificado`.
   - Suma al total pagado acumulado.
3. **Intentos Rechazados (`RECHAZO`):**
   - Movimientos de pago cuyo estado en el CRM es **`Rechazado`**, **`iniciado`** o **`DECLINED`**.
   - Se muestran con la insignia roja `RECHAZO`, monto aplicado `$0.00` y el motivo de fallo. No descuentan saldo.
4. **Cuotas Futuras (`FUTURA`):**
   - Cuotas con fecha de vencimiento posterior a la fecha de consulta.
   - Llevan la insignia azul `FUTURA`, estado `Por Ciclar` y muestran el saldo acumulado restante.

#### C. Redacción Automatizada de la "Revisión de Soporte"
El sistema redacta dinámicamente un párrafo ejecutivo:
- **Si el cliente tiene cuotas en mora:** Especifica cuántas cuotas están vencidas, cuáles son exactamente (ej. *Cuota 5*), el saldo vencido actual y la fecha límite para pagar.
- **Si el cliente está al día:** Certifica que todas las cuotas cicladas están pagadas con éxito, reporta el saldo exigible en `$0.00`, el total acumulado pagado y la fecha/monto de la próxima cuota programada.

---

### 5. Guía de Uso de las Interfaces

#### Opción 1: Aplicación de Escritorio (`INICIAR_APP_ESCRITORIO.bat`)
1. Haz doble clic sobre `INICIAR_APP_ESCRITORIO.bat`.
2. Se abrirá la ventana gráfica de Windows.
3. Haz clic en **"Examinar..."** y elige el cronograma descargado del CRM.
4. En el panel se previsualizarán los datos del cliente, contrato y estado general.
5. Haz clic en **"🚀 Convertir y Generar PDF Oficial"**.
6. En 1-2 segundos se generará el archivo `Reporte_Ejecutivo_*.pdf` y se abrirá automáticamente en tu lector de PDF predeterminado.

#### Opción 2: Aplicación Web (`INICIAR_APP_WEB.bat`)
1. Haz doble clic sobre `INICIAR_APP_WEB.bat`.
2. Se abrirá una pestaña en tu navegador web.
3. Arrastra uno o varios cronogramas PDF al recuadro de carga.
4. La interfaz generará tarjetas de indicadores en tiempo real y una vista previa interactiva completa del documento.
5. Puedes descargar directamente el archivo final con el botón **"📥 Descargar Reporte PDF Ejecutivo"**.

#### Opción 3: Línea de Comandos (Consola)
Para usuarios que deseen procesar archivos por terminal:
```bash
# Convertir un archivo específico:
python App_conversor.py "cronograma_1122125712_1793206285714.pdf"

# Procesar todos los PDFs de una carpeta por lote:
python App_conversor.py --batch .
```

---

### 6. Anatomía Visual del Reporte Generado

El diseño respeta al 100% las especificaciones de la plantilla oficial:
1. **Cabecera Institucional:** Título en azul `#0052cc`, estado de cuenta y fecha exacta de consulta a la derecha, con barra divisoria azul.
2. **Tarjeta de Cliente:** Caja con fondo `#f8fafc` y bordes redondeados con Cliente, Cédula, Contrato y Saldo Pendiente.
3. **4 Tarjetas de Indicadores (KPIs):**
   - *Cuotas Cicladas:* Fondo azul claro, número grande en `#0284c7`.
   - *Pagos Aplicados:* Fondo verde claro, número en `#16a34a` con total recaudado.
   - *Cuotas Atrasadas:* Verde si está al día (0), rojo si tiene mora.
   - *Saldo Actual:* Exigible inmediato antes de la fecha límite.
4. **Barra de Convenciones:** Muestra el significado de los 4 colores de insignia.
5. **Tabla de Movimientos Paginada:**
   - Cabecera negra `#0f172a` con texto blanco.
   - Columnas numéricas (Monto, Aplicado, Saldo) alineadas a la derecha.
   - Fecha centrada y concepto alineado a la izquierda.
   - Filas alternadas en blanco y gris suave (`#f8fafc`).
   - Distribución inteligente (Parte 1 en Página 1, Parte 2 en Página 2).
6. **Recuadro de Revisión de Soporte:** Caja resaltada con borde lateral que contiene el análisis redactado.
7. **Pie de Página:** Numeración limpia `Página X de Y` alineada a la derecha.

---

### 7. Mantenimiento y Preguntas Frecuentes

- **¿Dónde se guardan los archivos generados?**  
  Se guardan en la misma carpeta donde se encuentra el cronograma original, con el prefijo `Reporte_Ejecutivo_`.
- **¿Qué motor genera el PDF?**  
  Utiliza el motor Chromium (a través de Microsoft Edge o Google Chrome instalados en Windows en modo headless), lo que garantiza gráficos vectoriales nítidos, tipografía Segoe UI / Roboto y cero desconfiguración de estilos.
- **¿Qué pasa si un cliente tiene cuotas rechazadas?**  
  Aparecen en la tabla con la insignia roja `RECHAZO`, demostrando que hubo un intento de pago pero que la pasarela no lo autorizó, evitando confusiones contables.
