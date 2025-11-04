#!/bin/bash

echo ""
echo "========================================"
echo "一键IP测试自动化脚本"
echo "========================================"
echo ""
echo "正在启动脚本..."
echo ""

# Try to use venv python first, fallback to system python
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python one_click_automation.py
else
    python3 one_click_automation.py
fi
