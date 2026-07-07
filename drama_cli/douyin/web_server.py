"""抖音短剧工厂 - Web管理后台"""

import json
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from datetime import datetime

from .templates import list_templates, get_template, get_visual_config
from .pipeline import DouyinPipeline, PipelineConfig

app = Flask(__name__, template_folder="templates", static_folder="static")

# 全局状态
pipeline_status = {
    "running": False,
    "progress": 0,
    "stage": "",
    "log": [],
    "result": None,
}

current_pipeline = None


def _get_static_path(filename):
    return Path(__file__).parent / "static" / filename


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/templates")
def api_templates():
    templates = {}
    for name in list_templates():
        t = get_template(name)
        templates[name] = {
            "name": t.name,
            "genre": t.genre,
            "description": t.description,
            "style": t.style,
            "visual_style": t.visual_style,
            "bgm_mood": t.bgm_mood,
            "tags": t.tags,
            "twist_points": t.twist_points,
        }
    return jsonify(templates)


@app.route("/api/status")
def api_status():
    return jsonify(pipeline_status)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    global pipeline_status, current_pipeline

    data = request.json
    topic = data.get("topic", "")
    template_name = data.get("template", "霸道总裁")
    episodes = int(data.get("episodes", 3))
    style = data.get("style", "爽文")
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "https://api.openai.com/v1")

    if not topic:
        return jsonify({"error": "请输入短剧主题"}), 400

    # 加载剧本
    script_path = data.get("script_path", "")
    if script_path:
        script = json.loads(Path(script_path).read_text(encoding="utf-8"))
    else:
        return jsonify({"error": "请提供剧本文件路径"}), 400

    # 配置流水线
    config = PipelineConfig(
        project_name=topic.replace(" ", "_")[:20],
        template_name=template_name,
        topic=topic,
        episodes=episodes,
        style=style,
        ai_api_key=api_key,
        ai_base_url=base_url,
        output_dir=Path.cwd() / "douyin_output" / topic.replace(" ", "_")[:20],
        enable_ken_burns=data.get("ken_burns", True),
        enable_bgm=data.get("bgm", True),
        enable_color_grade=data.get("color_grade", True),
        enable_intro=data.get("intro", True),
        enable_outro=data.get("outro", True),
        enable_transitions=data.get("transitions", True),
        color_preset=data.get("color_preset", "cinematic"),
        bgm_volume=float(data.get("bgm_volume", 0.25)),
    )

    pipeline = DouyinPipeline(config)
    pipeline.set_script(script)

    pipeline_status = {
        "running": True,
        "progress": 0,
        "stage": "初始化",
        "log": [],
        "result": None,
    }

    def _run():
        global pipeline_status
        try:
            pipeline_status["stage"] = "生成场景图"
            pipeline_status["progress"] = 10
            final_path = pipeline.run()
            pipeline_status["result"] = {
                "video": str(final_path),
                "output_dir": str(config.output_dir),
                "title": script.get("title", ""),
                "episodes": len(script.get("episodes", [])),
            }
            pipeline_status["progress"] = 100
            pipeline_status["stage"] = "完成"
        except Exception as e:
            pipeline_status["stage"] = f"错误: {e}"
            pipeline_status["log"].append(str(e))
        finally:
            pipeline_status["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/preview/<path:filepath>")
def api_preview(filepath):
    return send_file(filepath)


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(Path.cwd() / "douyin_output", filename)


def start_server(host="0.0.0.0", port=8888):
    """启动Web服务器"""
    print(f"\n  🎬 抖音短剧工厂 Web 管理后台")
    print(f"  🌐 http://{host}:{port}")
    print(f"  📁 按 Ctrl+C 停止\n")
    app.run(host=host, port=port, debug=False)


# ============================================================
# 内嵌 HTML 模板
# ============================================================

INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DramaCLI Pro · 抖音短剧工厂</title>
<style>
  :root {
    --bg: #0a0a1a;
    --bg2: #12122a;
    --card: #1a1a3e;
    --accent: #e94560;
    --gold: #ffd700;
    --text: #e0e0e0;
    --text2: #8888aa;
    --border: #2a2a4a;
    --success: #00e676;
    --warning: #ffab00;
    --radius: 12px;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }
  /* 背景粒子 */
  .particles {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 0;
  }
  .particle {
    position: absolute; border-radius: 50%;
    animation: float 8s infinite ease-in-out;
  }
  @keyframes float {
    0%, 100% { transform: translateY(0) scale(1); opacity: 0.3; }
    50% { transform: translateY(-60px) scale(1.5); opacity: 0.8; }
  }
  /* 布局 */
  .app {
    position: relative; z-index: 1;
    max-width: 1200px; margin: 0 auto; padding: 20px;
  }
  /* 顶部导航 */
  .navbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 24px; background: var(--bg2);
    border-radius: var(--radius); margin-bottom: 24px;
    border: 1px solid var(--border);
  }
  .logo {
    font-size: 24px; font-weight: bold;
    background: linear-gradient(135deg, var(--gold), var(--accent));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .nav-links { display: flex; gap: 20px; }
  .nav-link {
    color: var(--text2); text-decoration: none; font-size: 14px;
    padding: 8px 16px; border-radius: 6px; transition: all 0.3s;
  }
  .nav-link:hover, .nav-link.active { color: var(--gold); background: var(--card); }
  /* 主布局 */
  .main-grid {
    display: grid; grid-template-columns: 1fr 380px; gap: 24px;
  }
  .left-col { display: flex; flex-direction: column; gap: 24px; }
  /* 卡片 */
  .card {
    background: var(--card); border-radius: var(--radius);
    border: 1px solid var(--border); padding: 24px;
  }
  .card-title {
    font-size: 18px; font-weight: bold; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }
  .card-title .icon { font-size: 20px; }
  /* 表单 */
  .form-group { margin-bottom: 16px; }
  .form-label {
    display: block; font-size: 13px; color: var(--text2);
    margin-bottom: 6px; font-weight: 500;
  }
  .form-input, .form-select, .form-textarea {
    width: 100%; padding: 10px 14px; background: var(--bg);
    border: 1px solid var(--border); border-radius: 8px;
    color: var(--text); font-size: 14px; font-family: inherit;
    transition: border-color 0.3s;
  }
  .form-input:focus, .form-select:focus, .form-textarea:focus {
    outline: none; border-color: var(--accent);
  }
  .form-textarea { resize: vertical; min-height: 80px; }
  .form-select { cursor: pointer; }
  /* 按钮 */
  .btn {
    padding: 12px 28px; border: none; border-radius: 8px;
    font-size: 15px; font-weight: 600; cursor: pointer;
    transition: all 0.3s; font-family: inherit;
  }
  .btn-primary {
    background: linear-gradient(135deg, var(--accent), #c73659);
    color: white; width: 100%;
  }
  .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(233,69,96,0.3); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .btn-sm {
    padding: 6px 14px; font-size: 12px; border-radius: 6px;
    background: var(--border); color: var(--text);
  }
  /* 模板选择 */
  .template-grid {
    display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;
  }
  .template-item {
    padding: 12px 8px; border-radius: 8px; background: var(--bg);
    border: 2px solid var(--border); cursor: pointer; text-align: center;
    transition: all 0.3s; font-size: 13px;
  }
  .template-item:hover { border-color: var(--accent); }
  .template-item.selected {
    border-color: var(--gold); background: rgba(255,215,0,0.1);
  }
  .template-item .t-name { font-weight: bold; color: var(--gold); }
  .template-item .t-genre { font-size: 11px; color: var(--text2); margin-top: 4px; }
  /* 开关 */
  .toggle-group { display: flex; flex-wrap: wrap; gap: 12px; }
  .toggle {
    display: flex; align-items: center; gap: 8px; cursor: pointer;
    padding: 8px 14px; border-radius: 8px; background: var(--bg);
    border: 1px solid var(--border); font-size: 13px; transition: all 0.3s;
  }
  .toggle.active { border-color: var(--accent); background: rgba(233,69,96,0.1); }
  .toggle input { display: none; }
  .toggle-indicator {
    width: 16px; height: 16px; border-radius: 4px;
    background: var(--border); transition: all 0.3s;
  }
  .toggle.active .toggle-indicator { background: var(--accent); }
  /* 进度条 */
  .progress-section { margin-top: 16px; }
  .progress-bar {
    height: 6px; background: var(--border); border-radius: 3px;
    overflow: hidden; margin: 8px 0;
  }
  .progress-fill {
    height: 100%; background: linear-gradient(90deg, var(--accent), var(--gold));
    border-radius: 3px; transition: width 0.5s;
  }
  .progress-text { font-size: 13px; color: var(--text2); }
  /* 右侧面板 */
  .right-col { display: flex; flex-direction: column; gap: 24px; }
  .preview-area {
    aspect-ratio: 9/16; background: var(--bg);
    border-radius: var(--radius); border: 1px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    overflow: hidden; position: relative;
  }
  .preview-area video {
    width: 100%; height: 100%; object-fit: cover;
  }
  .preview-placeholder {
    text-align: center; color: var(--text2);
  }
  .preview-placeholder .icon { font-size: 48px; display: block; margin-bottom: 8px; }
  /* 日志 */
  .log-area {
    max-height: 300px; overflow-y: auto; font-size: 13px;
    background: var(--bg); border-radius: 8px; padding: 12px;
    font-family: 'Consolas', 'Courier New', monospace;
  }
  .log-line { padding: 4px 0; color: var(--text2); }
  .log-line.success { color: var(--success); }
  .log-line.error { color: var(--accent); }
  .log-line.info { color: var(--gold); }
  /* 响应式 */
  @media (max-width: 900px) {
    .main-grid { grid-template-columns: 1fr; }
    .template-grid { grid-template-columns: repeat(3, 1fr); }
  }
</style>
</head>
<body>

<div class="particles" id="particles"></div>

<div class="app">
  <!-- 导航栏 -->
  <nav class="navbar">
    <div class="logo">🎬 DramaCLI Pro</div>
    <div class="nav-links">
      <span class="nav-link active">短剧工厂</span>
      <span class="nav-link">项目管理</span>
      <span class="nav-link">历史记录</span>
      <span class="nav-link">设置</span>
    </div>
  </nav>

  <!-- 主布局 -->
  <div class="main-grid">
    <!-- 左侧 -->
    <div class="left-col">
      <!-- 模板选择 -->
      <div class="card">
        <div class="card-title"><span class="icon">🎭</span> 选择模板</div>
        <div class="template-grid" id="templateGrid"></div>
      </div>

      <!-- 创作配置 -->
      <div class="card">
        <div class="card-title"><span class="icon">✍️</span> 创作配置</div>
        <div class="form-group">
          <label class="form-label">短剧主题</label>
          <input class="form-input" id="topic" placeholder="例如: 霸道总裁爱上我...">
        </div>
        <div class="form-group">
          <label class="form-label">集数</label>
          <input class="form-input" type="number" id="episodes" value="3" min="1" max="10">
        </div>
        <div class="form-group">
          <label class="form-label">AI API Key (可选)</label>
          <input class="form-input" id="apiKey" type="password" placeholder="sk-...">
        </div>
        <div class="form-group">
          <label class="form-label">剧本文件路径</label>
          <input class="form-input" id="scriptPath" placeholder="c:/path/to/script.json">
        </div>
      </div>

      <!-- 效果开关 -->
      <div class="card">
        <div class="card-title"><span class="icon">✨</span> 视频特效</div>
        <div class="toggle-group">
          <label class="toggle active" id="tglKenBurns">
            <input type="checkbox" checked> <span class="toggle-indicator"></span> Ken Burns
          </label>
          <label class="toggle active" id="tglBGM">
            <input type="checkbox" checked> <span class="toggle-indicator"></span> 背景音乐
          </label>
          <label class="toggle active" id="tglColorGrade">
            <input type="checkbox" checked> <span class="toggle-indicator"></span> 电影调色
          </label>
          <label class="toggle active" id="tglIntro">
            <input type="checkbox" checked> <span class="toggle-indicator"></span> 片头
          </label>
          <label class="toggle active" id="tglOutro">
            <input type="checkbox" checked> <span class="toggle-indicator"></span> 片尾
          </label>
          <label class="toggle active" id="tglTransitions">
            <input type="checkbox" checked> <span class="toggle-indicator"></span> 转场
          </label>
        </div>
        <div class="form-group" style="margin-top:16px">
          <label class="form-label">调色预设</label>
          <select class="form-select" id="colorPreset">
            <option value="cinematic">电影级</option>
            <option value="warm">暖色调</option>
            <option value="cool">冷色调</option>
            <option value="vintage">复古</option>
            <option value="noir">黑白</option>
            <option value="drama">戏剧</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">BGM音量</label>
          <input class="form-input" type="range" id="bgmVolume" min="0" max="1" step="0.05" value="0.25">
        </div>
      </div>

      <!-- 生成按钮 -->
      <button class="btn btn-primary" id="btnGenerate" onclick="startGenerate()">
        🚀 一键生成抖音短剧
      </button>

      <!-- 进度 -->
      <div class="progress-section" id="progressSection" style="display:none">
        <div class="progress-text" id="progressLabel">准备中...</div>
        <div class="progress-bar">
          <div class="progress-fill" id="progressFill" style="width:0%"></div>
        </div>
      </div>

      <!-- 日志 -->
      <div class="card" id="logCard" style="display:none">
        <div class="card-title"><span class="icon">📋</span> 运行日志</div>
        <div class="log-area" id="logArea"></div>
      </div>
    </div>

    <!-- 右侧 -->
    <div class="right-col">
      <!-- 预览 -->
      <div class="card">
        <div class="card-title"><span class="icon">📱</span> 实时预览</div>
        <div class="preview-area" id="previewArea">
          <div class="preview-placeholder">
            <span class="icon">🎬</span>
            <p>生成后在此预览</p>
          </div>
        </div>
      </div>

      <!-- 模板信息 -->
      <div class="card" id="templateInfo">
        <div class="card-title"><span class="icon">📖</span> 模板详情</div>
        <div id="templateDetail" style="font-size:14px; color:var(--text2)">
          选择模板查看详情
        </div>
      </div>

      <!-- 结果 -->
      <div class="card" id="resultCard" style="display:none">
        <div class="card-title"><span class="icon">🎉</span> 生成结果</div>
        <div id="resultContent"></div>
      </div>
    </div>
  </div>
</div>

<script>
  // 粒子背景
  (function() {
    const container = document.getElementById('particles');
    for (let i = 0; i < 40; i++) {
      const p = document.createElement('div');
      p.className = 'particle';
      p.style.left = Math.random() * 100 + '%';
      p.style.top = Math.random() * 100 + '%';
      p.style.width = p.style.height = (Math.random() * 4 + 1) + 'px';
      p.style.background = `hsl(${Math.random()*60+240}, 70%, ${Math.random()*40+50}%)`;
      p.style.animationDelay = Math.random() * 8 + 's';
      p.style.animationDuration = Math.random() * 6 + 6 + 's';
      container.appendChild(p);
    }
  })();

  // 模板数据
  let selectedTemplate = '霸道总裁';
  let checkInterval = null;

  // 加载模板
  fetch('/api/templates')
    .then(r => r.json())
    .then(templates => {
      const grid = document.getElementById('templateGrid');
      for (const [name, t] of Object.entries(templates)) {
        const div = document.createElement('div');
        div.className = 'template-item' + (name === selectedTemplate ? ' selected' : '');
        div.innerHTML = `<div class="t-name">${name}</div><div class="t-genre">${t.genre}</div>`;
        div.onclick = () => {
          document.querySelectorAll('.template-item').forEach(e => e.classList.remove('selected'));
          div.classList.add('selected');
          selectedTemplate = name;
          updateTemplateInfo(t);
        };
        grid.appendChild(div);
      }
      updateTemplateInfo(templates[selectedTemplate]);
    });

  function updateTemplateInfo(t) {
    document.getElementById('templateDetail').innerHTML = `
      <p><b>类型:</b> ${t.genre}</p>
      <p><b>风格:</b> ${t.style}</p>
      <p><b>视觉:</b> ${t.visual_style}</p>
      <p><b>BGM:</b> ${t.bgm_mood}</p>
      <p><b>简介:</b> ${t.description}</p>
      <p><b>标签:</b> ${t.tags.join(' ')}</p>
      <p><b>反转点:</b> ${t.twist_points.join(' → ')}</p>
    `;
  }

  // 开关切换
  document.querySelectorAll('.toggle').forEach(el => {
    el.onclick = () => {
      const cb = el.querySelector('input');
      cb.checked = !cb.checked;
      el.classList.toggle('active', cb.checked);
    };
  });

  function startGenerate() {
    const topic = document.getElementById('topic').value.trim();
    const scriptPath = document.getElementById('scriptPath').value.trim();

    if (!topic && !scriptPath) {
      alert('请输入短剧主题或剧本文件路径');
      return;
    }

    const btn = document.getElementById('btnGenerate');
    btn.disabled = true;
    btn.textContent = '⏳ 生成中...';

    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('logCard').style.display = 'block';
    document.getElementById('logArea').innerHTML = '';

    const data = {
      topic: topic,
      template: selectedTemplate,
      episodes: parseInt(document.getElementById('episodes').value),
      script_path: scriptPath,
      api_key: document.getElementById('apiKey').value,
      ken_burns: document.getElementById('tglKenBurns').classList.contains('active'),
      bgm: document.getElementById('tglBGM').classList.contains('active'),
      color_grade: document.getElementById('tglColorGrade').classList.contains('active'),
      intro: document.getElementById('tglIntro').classList.contains('active'),
      outro: document.getElementById('tglOutro').classList.contains('active'),
      transitions: document.getElementById('tglTransitions').classList.contains('active'),
      color_preset: document.getElementById('colorPreset').value,
      bgm_volume: parseFloat(document.getElementById('bgmVolume').value),
    };

    fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => r.json()).then(res => {
      if (res.error) {
        alert(res.error);
        resetButton();
        return;
      }
      addLog('info', '流水线已启动...');
      pollStatus();
    });
  }

  function pollStatus() {
    checkInterval = setInterval(() => {
      fetch('/api/status').then(r => r.json()).then(s => {
        document.getElementById('progressFill').style.width = s.progress + '%';
        document.getElementById('progressLabel').textContent =
          `[${s.progress}%] ${s.stage}`;

        if (s.log.length > 0) {
          s.log.forEach(l => addLog('info', l));
        }

        if (!s.running) {
          clearInterval(checkInterval);
          resetButton();
          if (s.result) {
            showResult(s.result);
          }
        }
      });
    }, 1000);
  }

  function addLog(type, msg) {
    const area = document.getElementById('logArea');
    const line = document.createElement('div');
    line.className = 'log-line ' + type;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    area.appendChild(line);
    area.scrollTop = area.scrollHeight;
  }

  function resetButton() {
    const btn = document.getElementById('btnGenerate');
    btn.disabled = false;
    btn.textContent = '🚀 一键生成抖音短剧';
  }

  function showResult(result) {
    document.getElementById('resultCard').style.display = 'block';
    document.getElementById('resultContent').innerHTML = `
      <p><b>剧名:</b> ${result.title}</p>
      <p><b>集数:</b> ${result.episodes}</p>
      <p><b>视频:</b> <code>${result.video}</code></p>
      <p><b>输出:</b> <code>${result.output_dir}</code></p>
    `;

    // 预览视频
    const preview = document.getElementById('previewArea');
    preview.innerHTML = `<video src="/output/${result.video.split('/').pop()}" controls autoplay loop></video>`;
  }
</script>
</body>
</html>"""


def render_template_string(template_str):
    """简化版 Flask 模板渲染"""
    return template_str


if __name__ == "__main__":
    start_server()