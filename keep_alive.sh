#!/bin/bash
# 九章量化局看板守护脚本
DASHBOARD_DIR="/app/data/所有对话/主对话/joke-quant-bureau/dashboard"
LOG="/tmp/joke-quant-server.log"

if ! ss -tlnp | grep -q ':7860 '; then
    echo "[$(date)] 重启dashboard_server..." >> "$LOG"
    cd "$DASHBOARD_DIR" && python3 dashboard_server.py >> "$LOG" 2>&1 &
    sleep 2
    if ss -tlnp | grep -q ':7860 '; then
        echo "[$(date)] 启动成功 PID=$(pgrep -f dashboard_server)" >> "$LOG"
    else
        echo "[$(date)] 启动失败" >> "$LOG"
    fi
fi

# 隧道守护
if ! pgrep -f "cloudflared.*7860" > /dev/null; then
    echo "[$(date)] 重启7860隧道..." >> "$LOG"
    nohup cloudflared tunnel --url http://localhost:7860 > /tmp/cf-tunnel-7860.log 2>&1 &
fi
