@echo off
chcp 65001 >nul
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python
    echo 请确保Python已安装且已添加到系统PATH
    pause
    exit /b 1
)
python filter.py
if errorlevel 1 pause
