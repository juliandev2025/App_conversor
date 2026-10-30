# App_conversor: Generador de Reportes Ejecutivos de Estado de Cuenta

Programa especializado para el equipo de soporte a tiendas y clientes. Transforma automáticamente cualquier cronograma en PDF descargado del CRM (KrediYA / plataforma de gestión) en un **Reporte Ejecutivo de Estado de Cuenta e Historial**, estructurado, claro y con el estilo exacto de la **PLANTILLA oficial de control interno**.

---

## ¿Qué soluciona esta App?

En los cronogramas nativos del CRM, los clientes y las tiendas suelen confundirse al ver cuotas futuras, intentos de pago rechazados y cuotas vencidas mezcladas en una sola tabla. 

**App_conversor** analiza y clasifica automáticamente cada movimiento:
1. **Cuotas Cicladas**: Identifica cuáles cuotas ya cumplieron su fecha de vencimiento a la fecha de consulta.
2. **Pagos Aplicados**: Suma y verifica todos los abonos efectivos aprobados, mostrando el saldo en `$0.00` y el check `✔ Verificado`.
3. **Cuotas Atrasadas (Mora)**: Detecta con exactitud si existe alguna cuota ciclada pendiente de pago, indicando su número de cuota, saldo vencido y fecha límite de pago. Si el cliente está al día, lo destaca en verde como libre de mora.
4. **Cuotas por Ciclar (Futuras)**: Separa las cuotas pendientes hasta fin de contrato con la etiqueta `Por Ciclar`.
5. **Intentos de Pago Rechazados**: Identifica pagos declinados o fallidos sin alterar el saldo contable, permitiendo explicar al cliente cuándo falló su intento.
6. **Recuadro Oficial de REVISIÓN DE SOPORTE**: Redacta una conclusión ejecutiva automática que el agente de soporte puede leer o copiar directamente en la respuesta al cliente o a la tienda.

---

## Formas de Uso

Tienes **3 formas sencillas** de utilizar la aplicación según tu preferencia:

### Opción 1: Aplicación de Escritorio (Recomendada)
Haz doble clic en:
👉 `INICIAR_APP_ESCRITORIO.bat`
- Se abrirá una ventana nativa de Windows.
- Haz clic en **"Examinar..."** y selecciona tu archivo `cronograma_*.pdf`.
- Verás al instante el nombre del cliente, cédula, contrato y estado general.
- Haz clic en **"Convertir y Generar PDF"**.
- El PDF se abrirá automáticamente en tu lector de PDF predeterminado.

### Opción 2: Aplicación Web Interactiva
Haz doble clic en:
👉 `INICIAR_APP_WEB.bat`
- Se abrirá en tu navegador (Edge, Chrome, etc.).
- Arrastra uno o varios cronogramas PDF.
- Podrás ver las tarjetas de métricas en tiempo real, previsualizar el reporte completo y descargarlo con el botón **"📥 Descargar Reporte PDF Ejecutivo"**.

### Opción 3: Despliegue en la Nube con Vercel
La aplicación está 100% configurada y lista para desplegarse gratis en Vercel:
1. Ve a [vercel.com](https://vercel.com) e inicia sesión con tu cuenta de GitHub.
2. Haz clic en **"Add New Project"** e importa el repositorio `juliandev2025/App_conversor`.
3. Vercel detectará automáticamente `vercel.json` y la función serverless de Python en `api/index.py`.
4. Haz clic en **"Deploy"**. En 1 minuto tendrás tu aplicación en línea con URL pública accesible desde cualquier dispositivo o tienda.

### Opción 4: Línea de Comandos / Procesamiento por Lote
Para usuarios avanzados o integración directa:
```bash
# Convertir un cronograma específico:
python App_conversor.py cronograma_1122125712_1793206285714.pdf

# Convertir todos los cronogramas de una carpeta a la vez:
python App_conversor.py --batch .
```

---

## Estructura y Fidelidad de Diseño (Igual a PLANTILLA)

El PDF generado cuenta con:
- **Encabezado superior**: Título en azul `#0052cc`, metadatos a la derecha y línea divisoria azul.
- **Tarjeta de Información del Cliente**: Cliente, Cédula, Contrato y Saldo pendiente en azul.
- **4 Tarjetas de Indicadores (KPIs)**:
  - *Cuotas Cicladas* (borde azul)
  - *Pagos Aplicados* (borde verde)
  - *Cuotas Atrasadas* (verde si está al día, rojo si tiene mora)
  - *Saldo Actual* (monto a pagar antes de la fecha límite)
- **Barra de Convenciones**: Etiquetas de color con punto indicador para Cuota Ciclada, Pago Efectivo, Saldo en Mora y Cuota Futura.
- **Tabla Detallada Paginada**:
  - Encabezados oscuros (`#0f172a`) con tipografía blanca.
  - Columnas numéricas (*Monto*, *Monto Aplicado*, *Saldo Cuota*) alineadas a la derecha.
  - Fecha centrada.
  - Insignias tipo *badge* redondeadas para `CICLADA`, `PAGO`, `FUTURA` y `RECHAZO`.
  - Paginación inteligente (Parte 1 en Página 1, Parte 2 en Página 2) sin hojas en blanco sobrantes.
- **Cuadro "REVISIÓN DE SOPORTE"**: Con borde lateral rojo y redacción personalizada para el caso exacto de cada cliente.
- **Pie de página oficial**: *Sistema de Soporte IT | Documento de Control Interno | Página X de Y*.

---

## Archivos del Proyecto

- `App_conversor.py`: Archivo principal / lanzador unificado (CLI, GUI, Batch, Web).
- `conversor_core.py`: Motor de extracción con `pdfplumber`, reglas financieras y generador HTML/PDF.
- `app_gui.py`: Interfaz de escritorio moderna en Tkinter.
- `app_web.py`: Interfaz web interactiva en Streamlit.
- `INICIAR_APP_ESCRITORIO.bat`: Acceso directo para escritorio.
- `INICIAR_APP_WEB.bat`: Acceso directo para web.
