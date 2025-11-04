#!/bin/bash
# -*- coding: utf-8 -*-

echo ""
echo "========================================"
echo "一键IP测试自动化脚本"
echo "========================================"
echo ""
echo "检查Python环境..."
echo ""

# Check for Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "错误：未找到Python"
    echo "请确保Python已安装"
    exit 1
fi

echo "正在启动脚本..."
echo ""

# Try to use venv python first, fallback to system python
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python one_click_automation.py
    EXIT_CODE=$?
else
    python3 one_click_automation.py
    EXIT_CODE=$?
fi

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "脚本执行出错，请检查错误信息"
    exit $EXIT_CODE
fi
