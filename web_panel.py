# =================================================================
#  web_panel.py
#  Version: 1.0.0
#  Author: MUXSET
#  Description: Web 远程控制面板。
#               提供一个轻量级 Flask Web 服务，支持从手机/浏览器
#               远程查看状态、日志、触发操作。
# =================================================================

import os
import threading
import collections
import time
from flask import Flask, jsonify, request, render_template_string
from logger import logger, LOG_FILE
import config_manager

app = Flask(__name__)

# 全局引用，由 GUI 注入
_gui_app = None

def set_gui_app(gui):
    """由 GUI 启动时调用，注入 GUI 引用以便触发操作。"""
    global _gui_app
    _gui_app = gui

# ============================
# HTML 模板 (响应式设计)
# ============================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TBE+ 阅赞助手 v2.1.0 - 远程面板</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #e0e0e0; min-height: 100vh; padding: 20px;
  }
  .container { max-width: 600px; margin: 0 auto; }
  h1 { text-align: center; font-size: 1.4em; margin-bottom: 20px;
       background: linear-gradient(90deg, #667eea, #764ba2);
       -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  
  /* 统计卡片 */
  .stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px; }
  .stat-card {
    background: rgba(255,255,255,0.08); border-radius: 12px;
    padding: 16px; text-align: center; backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
    transition: transform 0.2s;
  }
  .stat-card:hover { transform: translateY(-2px); }
  .stat-card .title { font-size: 0.8em; color: #999; margin-bottom: 6px; }
  .stat-card .value { font-size: 1.6em; font-weight: 700; }
  .stat-card .value.green { color: #4ade80; }
  .stat-card .value.red { color: #f87171; }
  .stat-card .value.blue { color: #60a5fa; }
  .stat-card .value.orange { color: #fb923c; }
  
  /* 操作按钮 */
  .actions { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 20px; }
  .btn {
    padding: 14px; border: none; border-radius: 10px; font-size: 0.95em;
    font-weight: 600; cursor: pointer; color: white;
    transition: opacity 0.2s, transform 0.1s;
  }
  .btn:active { transform: scale(0.96); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-scan { background: linear-gradient(135deg, #4f46e5, #7c3aed); }
  .btn-sweep { background: linear-gradient(135deg, #0891b2, #06b6d4); }
  .btn-export { background: linear-gradient(135deg, #059669, #10b981); }
  .btn-refresh { background: linear-gradient(135deg, #d97706, #f59e0b); }
  .btn-stop { background: linear-gradient(135deg, #dc2626, #ef4444); grid-column: span 2; }
  
  /* 账号信息 */
  .account-bar {
    background: rgba(255,255,255,0.06); border-radius: 10px;
    padding: 12px 16px; margin-bottom: 16px; display: flex;
    justify-content: space-between; align-items: center;
    border: 1px solid rgba(255,255,255,0.08);
  }
  .account-bar .label { color: #999; font-size: 0.85em; }
  .account-bar .name { font-weight: 600; color: #a78bfa; }
  .account-bar .status { font-size: 0.85em; }
  
  /* 日志区域 */
  .log-section {
    background: rgba(0,0,0,0.3); border-radius: 12px;
    padding: 14px; max-height: 400px; overflow-y: auto;
    font-family: 'Menlo', 'Consolas', monospace; font-size: 0.75em;
    line-height: 1.6; border: 1px solid rgba(255,255,255,0.05);
  }
  .log-section .warn { color: #fb923c; }
  .log-section .err { color: #f87171; }
  .log-section .info { color: #94a3b8; }
  
  .last-update { text-align: center; color: #555; font-size: 0.75em; margin-top: 12px; }
</style>
</head>
<body>
<div class="container">
  <h1>⚡ TBE+ 阅赞助手 远程面板</h1>
  
  <div class="account-bar">
    <div><span class="label">当前账号</span><br><span class="name" id="acc-name">---</span></div>
    <div><span class="status" id="acc-status">---</span></div>
  </div>
  
  <div class="stats">
    <div class="stat-card"><div class="title">📋 本月文章</div><div class="value blue" id="s-total">---</div></div>
    <div class="stat-card"><div class="title">✅ 已点赞</div><div class="value green" id="s-liked">---</div></div>
    <div class="stat-card"><div class="title">🕒 上次扫描</div><div class="value text-[#a78bfa] font-bold" style="color: #a78bfa;" id="s-last-scan">---</div></div>
    <div class="stat-card"><div class="title">🔑 Token</div><div class="value orange" id="s-token">---</div></div>
  </div>
  
  <div class="actions">
    <button class="btn btn-scan" onclick="doAction('scan')">🎯 单次扫描</button>
    <button class="btn btn-sweep" onclick="doAction('sweep')">🔄 月度补漏</button>
    <button class="btn btn-export" onclick="doAction('export')">📊 导出报告</button>
    <button class="btn btn-refresh" onclick="doAction('token')">🔑 刷新Token</button>
    <button class="btn btn-stop" onclick="doAction('stop')">⏹ 停止当前任务</button>
  </div>
  
  <div class="log-section" id="log-box">加载中...</div>
  <div class="last-update" id="last-update"></div>
</div>

<script>
async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const d = await res.json();
    document.getElementById('acc-name').textContent = d.username || '未设置';
    document.getElementById('acc-status').textContent = d.auto_mode ? '🟢 自动模式' : '⚪ 空闲待机';
    document.getElementById('s-total').textContent = d.total || '---';
    document.getElementById('s-liked').textContent = d.liked || '---';
    document.getElementById('s-last-scan').textContent = d.last_scan || '---';
    
    const tokenEl = document.getElementById('s-token');
    tokenEl.textContent = d.token_remaining || '---';
    tokenEl.className = 'value ' + (d.token_color || 'orange');
    
    document.getElementById('last-update').textContent = '更新: ' + new Date().toLocaleTimeString();
  } catch(e) {}
}

async function fetchLogs() {
  try {
    const res = await fetch('/api/logs');
    const d = await res.json();
    const box = document.getElementById('log-box');
    box.innerHTML = d.lines.map(l => {
      let cls = 'info';
      if (l.includes('[WARNING]') || l.includes('⚠️')) cls = 'warn';
      if (l.includes('[ERROR]') || l.includes('❌')) cls = 'err';
      return `<div class="${cls}">${l}</div>`;
    }).join('');
    box.scrollTop = box.scrollHeight;
  } catch(e) {}
}

async function doAction(action) {
  try {
    const res = await fetch('/api/action', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action})
    });
    const d = await res.json();
    if (d.ok) { setTimeout(fetchLogs, 2000); }
  } catch(e) { alert('操作失败'); }
}

fetchStatus();
fetchLogs();
setInterval(fetchStatus, 30000);
setInterval(fetchLogs, 10000);
</script>
</body>
</html>
"""

# ============================
# API 路由
# ============================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    username, _ = config_manager.get_credentials()
    stats = config_manager.get_sweep_stats()
    total = stats.get("total", 0)
    liked = stats.get("liked", 0)
    skipped = stats.get("skipped", 0)
    
    # 计算上次扫描时间
    last_time = stats.get("last_sweep_time", "")
    last_scan = "从未"
    if last_time:
        try:
            from datetime import datetime
            dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - dt
            mins = int(delta.total_seconds() / 60)
            if mins < 1:
                last_scan = "刚刚"
            elif mins < 60:
                last_scan = f"{mins}分钟前"
            elif mins < 1440:
                last_scan = f"{mins // 60}小时前"
            else:
                last_scan = f"{mins // 1440}天前"
        except:
            last_scan = last_time[:10]
    
    # Token 倒计时
    refresh_time = config_manager.get_token_refresh_time()
    _, token_interval = config_manager.get_intervals()
    token_remaining = "未知"
    token_color = "orange"
    if refresh_time > 0:
        remaining_sec = max(0, token_interval * 3600 - (time.time() - refresh_time))
        if remaining_sec <= 0:
            token_remaining = "已过期"
            token_color = "red"
        else:
            h, m = int(remaining_sec // 3600), int((remaining_sec % 3600) // 60)
            token_remaining = f"~{h}h{m:02d}m"
            token_color = "green" if remaining_sec > 1800 else "orange"
    
    auto_mode = _gui_app.auto_mode_running if _gui_app else False
    
    return jsonify({
        "username": username or "",
        "auto_mode": auto_mode,
        "total": total, "liked": skipped + liked,
        "last_scan": last_scan,
        "token_remaining": token_remaining,
        "token_color": token_color,
    })

@app.route('/api/logs')
def api_logs():
    lines = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = list(collections.deque(f, maxlen=100))
            lines = [l.rstrip('\n') for l in lines]
        except:
            pass
    return jsonify({"lines": lines})

@app.route('/api/action', methods=['POST'])
def api_action():
    if not _gui_app:
        return jsonify({"ok": False, "msg": "GUI 未连接"}), 503
    
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    
    try:
        if action == "scan":
            _gui_app.remote_scan_today()
            return jsonify({"ok": True, "msg": "单次扫描已触发"})
        elif action == "sweep":
            _gui_app.remote_scan_month()
            return jsonify({"ok": True, "msg": "月度补漏已触发"})
        elif action == "export":
            _gui_app.after(0, _gui_app.run_export_report_async)
            return jsonify({"ok": True, "msg": "报告导出已触发"})
        elif action == "token":
            threading.Thread(target=_gui_app._run_token_flow, daemon=True).start()
            return jsonify({"ok": True, "msg": "Token 刷新已触发"})
        elif action == "stop":
            _gui_app.scan_stop_event.set()
            return jsonify({"ok": True, "msg": "停止信号已发送"})
        else:
            return jsonify({"ok": False, "msg": f"未知操作: {action}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

# ============================
# 启动函数
# ============================

def start_web_panel(port=5050):
    """在后台线程中启动 Flask Web 面板。"""
    logger.info(f"🌐 [Web面板] 启动中... http://localhost:{port}")
    
    import logging
    # 屏蔽 Flask/Werkzeug 默认请求日志
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    logger.info(f"✅ [Web面板] 已启动！手机访问局域网IP:{port} 即可远程控制。")
    return thread
