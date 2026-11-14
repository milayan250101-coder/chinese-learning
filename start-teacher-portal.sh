#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_LOG="/tmp/chinese-learning-backend.log"
TEACHER_LOG="/tmp/chinese-learning-teacher-portal.log"
LOCK_FILE="/tmp/chinese-learning-start.lock"

# 防止多个自动启动任务同时运行
command -v flock >/dev/null 2>&1 || {
    echo "错误：系统没有 flock，无法保证启动互斥。"
    exit 1
}

exec 9>"$LOCK_FILE"
flock 9

wait_http() {
    local url="$1"
    local i
    for i in $(seq 1 60); do
        if curl -fsS "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

port_used() {
    ss -ltn "sport = :$1" | grep -q LISTEN
}

echo "========== Chinese Learning 自动启动 =========="

# 后端
if curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1; then
    echo "后端 8000：已正常运行，不重复启动。"
elif port_used 8000; then
    echo "错误：8000 被占用，但不是正常响应的后端。"
    exit 1
else
    echo "正在启动后端..."
    cd "$ROOT_DIR"

    nohup "$ROOT_DIR/.venv/bin/python" -m uvicorn \
        backend.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        > "$BACKEND_LOG" 2>&1 < /dev/null &

    if ! wait_http http://127.0.0.1:8000/; then
        echo "后端启动失败，请查看 $BACKEND_LOG"
        exit 1
    fi
    echo "后端 8000：启动成功。"
fi

# 教师端：只允许 5173
if curl -fsS http://127.0.0.1:5173/teacher.html >/dev/null 2>&1; then
    echo "教师端 5173：已正常运行，不重复启动。"
elif port_used 5173; then
    echo "错误：5173 被占用，但教师端入口无法访问。"
    exit 1
else
    echo "正在启动教师端..."
    nohup npm --prefix "$ROOT_DIR/teacher-portal" run dev -- --strictPort \
        > "$TEACHER_LOG" 2>&1 < /dev/null &

    if ! wait_http http://127.0.0.1:5173/teacher.html; then
        echo "教师端启动失败，请查看 $TEACHER_LOG"
        exit 1
    fi
    echo "教师端 5173：启动成功。"
fi

echo "========== 两项服务检查完成 =========="
