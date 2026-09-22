@echo off
chcp 65001 >nul
echo ===========================================
echo  ATUALIZAR DASHBOARD CERA
echo ===========================================
echo.

REM Verificar se Python esta disponivel
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Instale o Python em: https://python.org
    pause
    exit /b 1
)

echo [1/3] Python encontrado
echo [2/3] Navegando para pasta do dashboard...
echo.

cd /d "C:\Users\PC\Documents\Dashboards\CERA"
python update_dashboard.py

echo.
echo ===========================================
echo  PROCESSO CONCLUIDO
echo ===========================================
echo.
echo Se o push falou, configure o remote do GitHub:
echo   git remote add origin https://github.com/SEU-USUARIO/dashboard-cera-criativos.git
echo   git push -u origin master
echo.
pause
