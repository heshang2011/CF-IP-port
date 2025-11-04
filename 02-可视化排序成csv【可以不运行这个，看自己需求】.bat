@echo off
chcp 65001 >nul
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python
    echo 请确保Python已安装且已添加到系统PATH
    pause
    exit /b 1
)
python txt_2_csv.py ./06-提取反代了CF的ip及端口.txt ./07-提取反代了CF的ip及端口.csv
if errorlevel 1 pause
