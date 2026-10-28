@echo off
chcp 65001 > nul
title App Conversor - Estado de Cuenta
cd /d "%~dp0"

echo ========================================================
echo        Iniciando App Conversor (Modo Escritorio)
echo ========================================================
echo.

if exist "C:\Users\Julián Felipe\AppData\Local\Python\bin\python.exe" (
    "C:\Users\Julián Felipe\AppData\Local\Python\bin\python.exe" App_conversor.py
) else (
    python App_conversor.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrió un inconveniente al iniciar la aplicación.
    pause
)
