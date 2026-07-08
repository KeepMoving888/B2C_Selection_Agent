# ============================================================
# Dockerfile — 快速体验版：默认启动 Streamlit 前端（示例数据模式）
#
# 使用方式：
#   docker build -t xuanpin-frontend .
#   docker run -p 8501:8501 xuanpin-frontend
#
# 或者一键：
#   docker compose up -d
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（包含 streamlit / plotly）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# Streamlit 健康检查端点
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 非 root 运行
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

EXPOSE 8501

CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
