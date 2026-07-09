#!/usr/bin/env bash
# deploy/install_monitoring_wsl.sh
# 在 WSL2 Ubuntu 中安装并启动 Prometheus + Grafana（systemd 服务）
set -e

PROJECT_DIR="/mnt/c/Users/Windows/AppData/Roaming/reasonix/global-workspace/cross-border-agent"
OPT_DIR="/opt/b2c-monitoring"
PROM_VERSION="2.53.1"
GRAFANA_VERSION="10.4.5"

mkdir -p "$OPT_DIR"
cd "$OPT_DIR"

# --- Prometheus ---
if [[ ! -f "$OPT_DIR/prometheus/prometheus" ]]; then
    echo "[INFO] 下载 Prometheus ${PROM_VERSION} ..."
    curl -fsSL -o prometheus.tar.gz "https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/prometheus-${PROM_VERSION}.linux-amd64.tar.gz"
    tar -xzf prometheus.tar.gz
    mv "prometheus-${PROM_VERSION}.linux-amd64" prometheus
    rm prometheus.tar.gz
fi

# 使用项目自带的 prometheus.yml，但将 host.docker.internal 替换为 localhost
cp "${PROJECT_DIR}/deploy/prometheus.yml" "$OPT_DIR/prometheus/prometheus.yml"
sed -i 's/host\.docker\.internal/localhost/g' "$OPT_DIR/prometheus/prometheus.yml"

# --- Grafana ---
if [[ ! -d "$OPT_DIR/grafana" ]]; then
    echo "[INFO] 下载 Grafana ${GRAFANA_VERSION} ..."
    curl -fsSL -o grafana.tar.gz "https://dl.grafana.com/oss/release/grafana-${GRAFANA_VERSION}.linux-amd64.tar.gz"
    tar -xzf grafana.tar.gz
    mv "grafana-v${GRAFANA_VERSION}" grafana
    rm grafana.tar.gz
fi

# 配置 Grafana：数据源 + 看板
mkdir -p "$OPT_DIR/grafana/conf/provisioning/datasources"
mkdir -p "$OPT_DIR/grafana/conf/provisioning/dashboards"
cp "${PROJECT_DIR}/deploy/grafana-datasources.yml" "$OPT_DIR/grafana/conf/provisioning/datasources/datasources.yml"
sed -i 's|http://prometheus:9090|http://localhost:9090|g' "$OPT_DIR/grafana/conf/provisioning/datasources/datasources.yml"
cat > "$OPT_DIR/grafana/conf/provisioning/dashboards/dashboards.yml" <<'EOF'
apiVersion: 1
providers:
  - name: 'b2c-dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /opt/b2c-monitoring/grafana/dashboards
EOF
mkdir -p "$OPT_DIR/grafana/dashboards"
cp "${PROJECT_DIR}/deploy/grafana-dashboards/"*.json "$OPT_DIR/grafana/dashboards/" 2>/dev/null || true

# --- systemd 服务文件 ---
cat > /etc/systemd/system/prometheus.service <<EOF
[Unit]
Description=Prometheus Monitoring
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$OPT_DIR/prometheus
ExecStart=$OPT_DIR/prometheus/prometheus --config.file=$OPT_DIR/prometheus/prometheus.yml --storage.tsdb.path=$OPT_DIR/prometheus/data
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/grafana.service <<EOF
[Unit]
Description=Grafana Dashboards
After=network.target prometheus.service

[Service]
Type=simple
User=root
Environment="GF_PATHS_DATA=$OPT_DIR/grafana/data"
Environment="GF_PATHS_LOGS=$OPT_DIR/grafana/logs"
Environment="GF_PATHS_PLUGINS=$OPT_DIR/grafana/plugins"
Environment="GF_SECURITY_ADMIN_USER=admin"
Environment="GF_SECURITY_ADMIN_PASSWORD=admin"
WorkingDirectory=$OPT_DIR/grafana
ExecStart=$OPT_DIR/grafana/bin/grafana-server -homepath $OPT_DIR/grafana
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prometheus.service
systemctl enable grafana.service
systemctl start prometheus.service
systemctl start grafana.service

echo "[OK] Prometheus + Grafana 已启动"
echo "     Prometheus: http://<wsl-ip>:9090"
echo "     Grafana:    http://<wsl-ip>:3000 (admin/admin)"
