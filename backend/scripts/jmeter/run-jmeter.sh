#!/bin/bash
# JMeter 压测运行脚本
# 使用方式：
#   chmod +x run-jmeter.sh
#   ./run-jmeter.sh                    # 默认配置 (localhost:8080, 50并发, 120秒)
#   ./run-jmeter.sh 192.168.1.100 8080 100 300  # 自定义

HOST=${1:-localhost}
PORT=${2:-8080}
THREADS=${3:-50}
DURATION=${4:-120}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JMX="$SCRIPT_DIR/ai-platform-test.jmx"
RESULTS="$SCRIPT_DIR/results.jtl"
REPORT_DIR="$SCRIPT_DIR/reports"

echo "========================================"
echo " AI赋能平台 性能压测"
echo "========================================"
echo " 目标:     http://$HOST:$PORT"
echo " 线程数:   $THREADS"
echo " 持续时间: ${DURATION}s"
echo "----------------------------------------"

# 清理旧结果
rm -f "$RESULTS"
rm -rf "$REPORT_DIR"

# 运行压测
jmeter -n -t "$JMX" \
  -Jhost="$HOST" \
  -Jport="$PORT" \
  -Jthreads="$THREADS" \
  -Jduration="$DURATION" \
  -l "$RESULTS" \
  -e -o "$REPORT_DIR"

echo "========================================"
echo " 测试完成!"
echo " 结果文件: $RESULTS"
echo " 报告目录: $REPORT_DIR"
echo "========================================"
echo ""
echo "关键指标:"
if command -v jq &> /dev/null; then
    jq -r '
        .Overall |
        "  TPS:      \(.throughput) req/s",
        "  平均响应: \(.meanResTime) ms",
        "  P50:      \(.medianResTime) ms",
        "  P90:      \(.pct90ResTime) ms",
        "  P99:      \(.pct99ResTime) ms",
        "  错误率:   \(.errorPct)%"
    ' "$REPORT_DIR/statistics.json" 2>/dev/null
else
    echo "  安装 jq 查看详细统计，或打开 $REPORT_DIR/index.html 查看"
fi
echo ""
