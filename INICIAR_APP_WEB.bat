@echo off
chcp 65001 > nul
title App Conversor Web - Estado de Cuenta
cd /d "%~dp0"

echo ========================================================
echo        Iniciando App Conversor (Modo Web)
echo ========================================================
echo Abriendo en tu navegador...
echo.

if exist "C:\Users\Julián Felipe\AppData\Local\Python\bin\python.exe" (
    "C:\Users\Julián Felipe\AppData\Local\Python\bin\python.exe" -m streamlit run app_web.py
) else (
    python -m streamlit run app_web.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrió un inconveniente al iniciar la aplicación web.
    pause
)
