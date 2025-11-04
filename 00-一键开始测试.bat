@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 一键IP测试自动化脚本
echo ========================================
echo.
echo 检查Python环境...
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python
    echo 请确保Python已安装且已添加到系统PATH
    echo.
    pause
    exit /b 1
)
echo 正在启动脚本...
echo.
python one_click_automation.py
if errorlevel 1 (
    echo.
    echo 脚本执行出错，请检查错误信息
    echo.
    pause
    exit /b 1
)
pause
