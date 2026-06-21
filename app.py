import os
import secrets
from flask import Flask, redirect, url_for, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-key")

# Usar threading (evita eventlet/gevent em Windows)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ===================== TELA INICIAL (SESSÃO) =====================
HOME_HTML = r"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8" />
<title>Sessão CTG</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin:0;
    min-height:100vh;
    background:
      radial-gradient(circle at top left, rgba(31,111,235,.20), transparent 34%),
      linear-gradient(180deg, #08101f 0%, #0b1220 42%, #09111f 100%);
    color:#e6edf3;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:18px;
  }
  .box {
    width:min(860px, 96vw);
    background:linear-gradient(180deg, rgba(16,26,51,.96), rgba(12,22,43,.96));
    border:1px solid rgba(129,161,213,.22);
    border-radius:18px;
    padding:22px;
    box-shadow:0 18px 40px rgba(0,0,0,.28);
  }
  h1 { margin:0 0 8px; font-size:24px; }
  h2 { margin:18px 0 8px; font-size:16px; color:#dbeafe; }
  p { margin:8px 0; color:#c9d7ee; line-height:1.35; }
  .code {
    display:inline-block;
    margin-top:6px;
    padding:5px 10px;
    border-radius:999px;
    background:#122042;
    border:1px solid #223058;
    color:#dbeafe;
    font-weight:800;
  }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:16px 0 10px; }
  a.btn, button.btn {
    display:block;
    text-align:center;
    padding:14px 12px;
    border-radius:12px;
    text-decoration:none;
    color:#fff;
    font-weight:800;
    background:linear-gradient(180deg, #2f81f7, #1f6feb);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 8px 18px rgba(0,0,0,.18);
    border:0;
    cursor:pointer;
    width:100%;
    font:inherit;
  }
  a.secondary { background:linear-gradient(180deg, #2ea043, #238636); }
  .small { font-size:13px; opacity:.82; }
  .linkbox {
    margin-top:12px;
    padding:10px;
    border-radius:12px;
    background:rgba(8,16,31,.38);
    border:1px solid rgba(129,161,213,.15);
    overflow-wrap:anywhere;
    font-size:13px;
    color:#c9d7ee;
  }
  .qrGrid {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:12px;
    margin-top:12px;
  }
  .qrCard {
    background:rgba(8,16,31,.38);
    border:1px solid rgba(129,161,213,.15);
    border-radius:14px;
    padding:12px;
    text-align:center;
  }
  .qrCard h3 {
    margin:0 0 8px;
    font-size:15px;
    color:#e6edf3;
  }
  .qrBox {
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:190px;
    padding:10px;
    background:#fff;
    border-radius:12px;
    width:max-content;
    max-width:100%;
    margin:0 auto 10px;
  }
  .qrBox canvas,
  .qrBox img {
    display:block;
    width:180px !important;
    height:180px !important;
  }
  .copyBtn {
    margin-top:8px;
    padding:9px 10px;
    border-radius:10px;
    border:1px solid rgba(129,161,213,.25);
    color:#dbeafe;
    background:#122042;
    cursor:pointer;
    font-weight:700;
    width:100%;
  }
  .hint {
    margin-top:10px;
    padding:10px;
    border-radius:12px;
    background:rgba(31,111,235,.12);
    border:1px solid rgba(88,166,255,.20);
    color:#dbeafe;
    font-size:13px;
    line-height:1.35;
  }
  @media (max-width: 720px) {
    .grid, .qrGrid { grid-template-columns:1fr; }
    .box { padding:18px; }
  }
</style>
</head>
<body>
  <main class="box">
    <h1>Simulador CTG</h1>
    <p>Esta é uma sessão individual. O controle desta sessão só interfere no monitor com o mesmo código.</p>
    <p>Código da sessão: <span class="code">{{ room_id }}</span></p>

    <div class="grid">
      <a class="btn" href="{{ control_url }}" target="_blank" rel="noopener noreferrer">Abrir controle em nova aba</a>
      <a class="btn secondary" href="{{ monitor_url }}" target="_blank" rel="noopener noreferrer">Abrir monitor em nova aba</a>
    </div>

    <div class="hint">
      A página inicial fica aberta. Para usar com celular: abra o monitor no PC em nova aba e escaneie o QR Code do controle com o celular.
    </div>

    <h2>QR Codes da sessão</h2>
    <div class="qrGrid">
      <section class="qrCard">
        <h3>Controle no celular</h3>
        <div id="qrControl" class="qrBox"></div>
        <p class="small">Escaneie este QR Code no celular para controlar esta sessão.</p>
        <button class="copyBtn" type="button" onclick="copyLink(CONTROL_URL, 'Controle')">Copiar link do controle</button>
      </section>

      <section class="qrCard">
        <h3>Monitor</h3>
        <div id="qrMonitor" class="qrBox"></div>
        <p class="small">Use este QR Code se quiser abrir o monitor em outro aparelho.</p>
        <button class="copyBtn" type="button" onclick="copyLink(MONITOR_URL, 'Monitor')">Copiar link do monitor</button>
      </section>
    </div>

    <p class="small">Exemplo: deixe o monitor no PC e abra o controle no celular usando os links desta mesma sessão.</p>
    <div class="linkbox">
      Controle: {{ control_url }}<br>
      Monitor: {{ monitor_url }}
    </div>
  </main>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<script>
  const CONTROL_URL = {{ control_url|tojson }};
  const MONITOR_URL = {{ monitor_url|tojson }};

  function fallbackQr(id, url){
    const el = document.getElementById(id);
    if (!el) return;
    el.style.background = '#0b1430';
    el.innerHTML = '<a href="' + url + '" target="_blank" rel="noopener noreferrer" style="color:#dbeafe;text-decoration:none;word-break:break-word;">Abrir link</a>';
  }

  function makeQr(id, url){
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '';

    if (typeof QRCode === 'undefined') {
      fallbackQr(id, url);
      return;
    }

    new QRCode(el, {
      text: url,
      width: 180,
      height: 180,
      colorDark: '#000000',
      colorLight: '#ffffff',
      correctLevel: QRCode.CorrectLevel.M
    });
  }

  function copyLink(url, label){
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(() => {
        alert(label + ' copiado.');
      }).catch(() => {
        prompt('Copie o link:', url);
      });
    } else {
      prompt('Copie o link:', url);
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    makeQr('qrControl', CONTROL_URL);
    makeQr('qrMonitor', MONITOR_URL);
  });
</script>
</body>
</html>
"""

# ===================== TELA 1 (CONTROLE) =====================
CONTROL_HTML = r"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8" />
<title>Tela 1 — Controle CTG</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  body {
    margin:0;
    background:
      radial-gradient(circle at top left, rgba(31,111,235,.18), transparent 34%),
      linear-gradient(180deg, #08101f 0%, #0b1220 42%, #09111f 100%);
    color:#e6edf3;
  }
  header {
    padding:8px 12px;
    border-bottom:1px solid rgba(120,147,190,.18);
    background:rgba(8,16,31,.72);
    backdrop-filter: blur(10px);
    position:sticky;
    top:0;
    z-index:10;
  }
  .wrap { max-width:1760px; margin:0 auto; padding:8px 10px; }
  .cardsGrid {
    display:grid;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap:8px;
    align-items:start;
  }
  .card {
    grid-column: span 3;
    background:linear-gradient(180deg, rgba(16,26,51,.96), rgba(12,22,43,.96));
    border:1px solid rgba(129,161,213,.20);
    border-radius:12px;
    padding:10px;
    box-shadow:0 8px 20px rgba(0,0,0,.20);
  }
  .card.wide { grid-column: 1 / -1; }
  .card.full { grid-column: 1 / -1; }
  h3 {
    margin:0 0 7px;
    font-size:14px;
    letter-spacing:.2px;
    display:flex;
    align-items:center;
    gap:8px;
  }
  h3::before {
    content:"";
    width:6px;
    height:16px;
    border-radius:999px;
    background:#58a6ff;
    display:inline-block;
  }
  h4 { color:#c9d7ee; font-size:12px; margin:6px 0 5px; }
  .btn {
    width:100%;
    min-height:31px;
    padding:6px 8px;
    border:0;
    border-radius:9px;
    font-size:12px;
    cursor:pointer;
    font-weight:700;
    color:#fff;
    background:linear-gradient(180deg, #2f81f7, #1f6feb);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 8px 18px rgba(0,0,0,.18);
    transition: transform .08s ease, filter .12s ease, opacity .12s ease;
  }
  .btn:hover { filter:brightness(1.08); }
  .btn:active { transform:translateY(1px); }
  .btn.locked,
  .btn:disabled {
    background:linear-gradient(180deg, #6b7280, #4b5563) !important;
    color:#d1d5db !important;
    opacity:.72;
    cursor:not-allowed;
    filter:grayscale(.25);
    box-shadow:none;
  }
  .btn.scenario-active {
    background:linear-gradient(180deg, #6b7280, #4b5563) !important;
    color:#e5e7eb !important;
    opacity:.84;
    box-shadow:none;
  }
  .btn.warn { background:linear-gradient(180deg, #a371f7, #8e5eff); }
  .btn.secondary { background:linear-gradient(180deg, #3a4554, #30363d); }
  .btn.danger { background:linear-gradient(180deg, #da4a4a, #c93c3c); }
  .btn.yellow { background:linear-gradient(180deg, #ffd75a, #f4c430); color:#171717; }
  .btn.green { background:linear-gradient(180deg, #2ea043, #238636); color:#fff; }
  .btngrid2, .btnGrid { display:grid; grid-template-columns: 1fr 1fr; gap:6px; }
  .btngrid1, .btnGrid.oneCol { display:grid; grid-template-columns: 1fr; gap:6px; }
  .eventsGrid { display:grid; grid-template-columns: repeat(auto-fit, minmax(132px, 1fr)); gap:6px; }
  .scenarioGrid { display:grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap:6px; }
  .hr { height:1px; background:rgba(129,161,213,.18); margin:7px 0; }
  label { display:block; margin:4px 0 4px; opacity:.92; font-size:11px; color:#d7e3f7; }
  input[type=range], input[type=number] {
    width:100%;
    background:#0c1627;
    color:#e6edf3;
    border:1px solid #263a5d;
    border-radius:9px;
    padding:5px;
    outline:none;
  }
  input[type=range] { accent-color:#58a6ff; }
  .pill {
    display:inline-block;
    padding:4px 10px;
    border-radius:999px;
    background:#122042;
    border:1px solid #223058;
    margin-left:6px;
    font-size:12px;
    color:#dbeafe;
  }
  .row { display:grid; grid-template-columns: minmax(0, 1fr) 72px; gap:6px; align-items:center; }
  .status {
    font-size:11px;
    line-height:1.32;
    color:#c9d7ee;
    background:rgba(8,16,31,.36);
    border:1px solid rgba(129,161,213,.13);
    border-radius:9px;
    padding:6px;
    margin-top:6px;
  }
  .muted { opacity:.75; font-size:11px; margin-top:4px; line-height:1.25; }
  input[type=range] { height:26px; }
  .card p, .card .status div { margin:0; }
  @media (max-width: 1100px) {
    .card, .card.wide { grid-column: span 6; }
  }
  @media (max-width: 740px) {
    .wrap { padding:14px; }
    .card, .card.wide { grid-column: 1 / -1; }
    .btngrid2, .eventsGrid, .scenarioGrid { grid-template-columns:1fr; }
  }
</style>
</head>
<body>
<header><div class="wrap"><h1 style="margin:0;font-size:18px;line-height:1.1">Simulador — <span style="opacity:.85">Tela 1 (Controle CTG)</span></h1></div></header>

<div class="wrap">
  <div class="cardsGrid">

    <!-- CARD: FHR — BASELINE (ajuste fino) -->
    <div class="card">
      <h3 style="margin:0 0 10px">FHR — Baseline</h3>

      <label>Baseline (bpm) <span class="pill" id="basepill">140</span></label>
      <div class="row">
        <input id="base_range" type="range" min="0" max="240" value="140" oninput="syncBase(this.value)">
        <input id="base_num"   type="number" min="0" max="240" value="140" oninput="syncBase(this.value)">
      </div>

      <div style="height:6px"></div>
      <button class="btn secondary" onclick="sendBaseline()">Enviar baseline</button>

      <div class="status" style="margin-top:10px; opacity:.8">
        Dica: normal costuma ficar na faixa 110–160 bpm (ex.: 140).
      </div>
    </div>

    <!-- CARD: FHR — VARIABILIDADE -->
    <div class="card">
      <h3 style="margin:0 0 10px">FHR — Variabilidade</h3>

      <label>Variação mínima total (bpm) <span class="pill" id="vminpill">5</span></label>
      <div class="row">
        <input id="vmin_range" type="range" min="0" max="80" value="5" oninput="syncVMin(this.value)">
        <input id="vmin_num"   type="number" min="0" max="80" value="5" oninput="syncVMin(this.value)">
      </div>

      <label style="margin-top:10px">Variação máxima total (bpm) <span class="pill" id="vmaxpill">25</span></label>
      <div class="row">
        <input id="vmax_range" type="range" min="0" max="80" value="25" oninput="syncVMax(this.value)">
        <input id="vmax_num"   type="number" min="0" max="80" value="25" oninput="syncVMax(this.value)">
      </div>

      <div style="height:6px"></div>
      <button class="btn secondary" onclick="sendSetVar()">Enviar variabilidade</button>

      <div style="height:6px"></div>
      <div class="status" id="rangeHintMax">≈ máx total 25 → 128–153 bpm</div>
      <div class="status" id="rangeHintMin">≈ mín total 5 → 138–143 bpm</div>
    </div>

    
    <!-- CARD: TOCO — COMANDOS -->
    <div class="card">
      <h3 style="margin:0 0 10px">TOCO — Comandos</h3>
      <div class="muted">
        Controle o tônus basal separadamente e depois envie contrações manuais. No grid, 1 quadradinho = 30 segundos.
      </div>

      <div class="hr"></div>

      <h4 style="margin:0 0 8px">Tônus basal</h4>
      <label>Tônus basal (mmHg) <span class="pill" id="toco_tone_pill">10</span></label>
      <div class="row">
        <input id="toco_tone_range" type="range" min="0" max="100" value="10" oninput="syncTocoTone(this.value)">
        <input id="toco_tone_num"   type="number" min="0" max="100" value="10" oninput="syncTocoTone(this.value)">
      </div>

      <div style="height:6px"></div>
      <button class="btn secondary" onclick="sendTocoTone()">Enviar tônus basal</button>

      <div class="hr"></div>

      <h4 style="margin:0 0 8px">Contração manual</h4>

      <label>Intensidade / pico (mmHg) <span class="pill" id="toco_peak_pill">50</span></label>
      <div class="row">
        <input id="toco_peak_range" type="range" min="0" max="100" value="50" oninput="syncTocoPeak(this.value)">
        <input id="toco_peak_num"   type="number" min="0" max="100" value="50" oninput="syncTocoPeak(this.value)">
      </div>

      <label style="margin-top:10px">Duração da contração <span class="pill" id="toco_dur_pill">50s</span></label>
      <div class="row">
        <input id="toco_dur_range" type="range" min="5" max="70" value="50" oninput="syncTocoDuration(this.value)">
        <input id="toco_dur_num"   type="number" min="5" max="70" value="50" oninput="syncTocoDuration(this.value)">
      </div>
      <div class="muted" id="toco_grid_hint">50s ≈ 1,67 quadradinhos</div>

      <div style="height:6px"></div>
      <button class="btn" onclick="sendTocoContraction()">Enviar contração</button>

      <div class="hr"></div>

      <button class="btn secondary" onclick="sendReset()">Limpar eventos</button>

      <div class="status" id="s3">—</div>
    </div>

    <!-- CARD: VELOCIDADE -->
    <div class="card">
      <h3 style="margin:0 0 10px">Velocidade</h3>

      <h4 style="margin:0 0 8px">Velocidade do tempo</h4>
      <label>Fator (×) <span class="pill" id="speedpill">1.0×</span></label>

      <div class="row">
       <input id="speed_range" type="range" min="0.05" max="20" step="0.05" value="1.0" oninput="syncSpeed(this.value)">
       <input id="speed_num"   type="number" min="0.05" max="20" step="0.05" value="1.0" oninput="syncSpeed(this.value)">
      </div>

      <div style="height:6px"></div>
      <button class="btn secondary" onclick="sendTimeScale()">Aplicar velocidade</button>

      <div class="status" id="s4">—</div>
    </div>

  


<!-- CARD: EVENTOS OBSTÉTRICOS -->
<div class="card wide">
  <h3 style="margin:0 0 10px">Eventos — Aceleração e DIPs</h3>
  <div class="muted">Eventos temporários. Enquanto um evento estiver ativo, outro comando de DIP/aceleração é ignorado até terminar.</div>

  <div class="hr"></div>

  <div class="eventsGrid">
    <button id="btn_acel" class="btn green" onclick="sendAceleracaoTransitoria()">Aceleração transitória</button>
    <button id="btn_dip_precoce" class="btn green" onclick="sendDIPIVerdadeira()">DIP precoce</button>
    <button id="btn_dip_tardia" class="btn yellow" onclick="sendDIPTardia()">DIP tardia</button>
    <button id="btn_var_v_con" class="btn yellow" onclick="sendDIPVarVContracao()">DIP variável V com onda</button>
    <button id="btn_var_v_sem" class="btn yellow" onclick="sendDIPVarVSemContracao()">DIP variável V sem onda</button>
    <button id="btn_var_u_con" class="btn yellow" onclick="sendDIPVarUContracao()">DIP variável U com onda</button>
    <button id="btn_var_u_sem" class="btn yellow" onclick="sendDIPVarUSemContracao()">DIP variável U sem onda</button>
    <button id="btn_var_w_con" class="btn yellow" onclick="sendDIPVarWContracao()">DIP variável W com onda</button>
    <button id="btn_var_w_sem" class="btn yellow" onclick="sendDIPVarWSemContracao()">DIP variável W sem onda</button>
  </div>

  <div class="hr"></div>

  <div class="status">
    <div><strong>Modo:</strong> <span id="cfg_mode">—</span></div>
    <div><strong>Baseline:</strong> <span id="cfg_base">—</span> bpm</div>
    <div><strong>Variação total:</strong> mín <span id="cfg_vmin">—</span> / máx <span id="cfg_vmax">—</span> bpm</div>
    <div><strong>TOCO:</strong> <span id="cfg_uc">—</span></div>
  </div>
</div>

<!-- CARD: CENÁRIOS / TRABALHO DE PARTO -->
<div class="card wide">
  <h3 style="margin:0 0 10px">Cenários / Trabalho de parto</h3>
  <div class="muted">Nos trabalhos de parto, as contrações têm 60s, pico de 50 mmHg e retornam ao tônus basal que estiver setado na TOCO.</div>

  <div class="hr"></div>

  <div class="scenarioGrid">
    <button id="btn_basal" class="btn" onclick="sendPresetNormal()">Basal / Repouso</button>
    <button id="btn_sinusoidal" class="btn danger" onclick="sendSinusoidalToggle()">Padrão sinusoidal: ligar/desligar</button>
    <button id="btn_hiper" class="btn danger" onclick="sendHipersistoliaToggle()">Hipersistolia</button>
    <button id="btn_labor_1" class="btn" onclick="sendLaborRate(1)">Trabalho de parto 1/10</button>
    <button id="btn_labor_2" class="btn" onclick="sendLaborRate(2)">Trabalho de parto 2/10</button>
    <button id="btn_labor_3" class="btn" onclick="sendLaborRate(3)">Trabalho de parto 3/10</button>
    <button id="btn_labor_4" class="btn" onclick="sendLaborRate(4)">Trabalho de parto 4/10</button>
    <button id="btn_labor_5" class="btn" onclick="sendLaborRate(5)">Trabalho de parto 5/10</button>
  </div>
</div>

  </div> <!-- fecha .cardsGrid -->
</div>   <!-- fecha .wrap -->

<script src="https://cdn.socket.io/4.7.5/socket.io.min.js" crossorigin="anonymous"></script>
<script>
  const ROOM_ID = "{{ room_id }}";
  const socket = io({ query: { room: ROOM_ID } });
  const clamp = (x,a,b)=> Math.max(a, Math.min(b, x));
  const log = (el, obj)=> { const e=document.getElementById(el); if(e) e.textContent = "Enviado: " + JSON.stringify(obj); };
  const send = (p)=> socket.emit('command', p);

  // --- helpers de forma ---
  function clamp01(t){ return Math.max(0, Math.min(1, t)); }
  function smooth01(t){ t = clamp01(t); return t*t*(3 - 2*t); }

  function trapezoid01(x, riseFrac=0.20, fallFrac=0.20){
    x = clamp01(x);
    const platStart = clamp01(riseFrac);
    const platEnd   = clamp01(1 - fallFrac);
    if (platStart + fallFrac > 1) {
      const s = (riseFrac) / (riseFrac + fallFrac);
      return (x < s) ? smooth01(x/s) : 1 - smooth01((x - s)/(1 - s));
    }
    if (x < platStart) return smooth01(x / platStart);
    if (x <= platEnd)  return 1;
    return 1 - smooth01((x - platEnd) / (1 - platEnd));
  }

  function getSpeed(){
    const v = parseFloat(document.getElementById('speed_num').value);
    return isNaN(v) ? 1.0 : Math.max(0.05, Math.min(20.0, v));
  }
  function syncSpeed(v){
    let n = parseFloat(v); if (isNaN(n)) n = 1.0;
  n = Math.max(0.05, Math.min(20.0, n));
    document.getElementById('speed_range').value = n;
    document.getElementById('speed_num').value   = n.toFixed(2);
    document.getElementById('speedpill').textContent = n.toFixed(2) + '×';
  }
  function sendTimeScale(){
    const factor = getSpeed();
    const payload = { mode:'time_scale', factor };
    socket.emit('command', payload);
    log('s4', payload);
  }

  const obstBtnIds = [
    'btn_acel','btn_dip_precoce','btn_dip_tardia',
    'btn_var_v_con','btn_var_v_sem','btn_var_u_con','btn_var_u_sem','btn_var_w_con','btn_var_w_sem'
  ];
  const laborBtnIds = ['btn_labor_1','btn_labor_2','btn_labor_3','btn_labor_4','btn_labor_5'];
  let obstLockTimer = null;
  let laborLockTimer = null;
  let sinusoidalActiveUi = false;
  let hipersistoliaActiveUi = false;

  function btn(id){ return document.getElementById(id); }
  function setBtnLocked(id, locked, disable=true){
    const b = btn(id); if(!b) return;
    b.classList.toggle('locked', !!locked);
    if (disable) b.disabled = !!locked;
  }
  function setScenarioActive(id, active){
    const b = btn(id); if(!b) return;
    b.classList.toggle('scenario-active', !!active);
    b.classList.toggle('locked', !!active);
    b.disabled = false; // cenários liga/desliga continuam clicáveis
  }
  function unlockObstButtons(){
    if (obstLockTimer) { clearTimeout(obstLockTimer); obstLockTimer = null; }
    obstBtnIds.forEach(id => setBtnLocked(id, false, true));
  }
  function lockObstButtons(durationSec){
    unlockObstButtons();
    obstBtnIds.forEach(id => setBtnLocked(id, true, true));
    const ms = Math.max(250, (durationSec * 1000) / Math.max(0.05, getSpeed()));
    obstLockTimer = setTimeout(unlockObstButtons, ms);
  }
  function unlockLaborButtons(){
    if (laborLockTimer) { clearTimeout(laborLockTimer); laborLockTimer = null; }
    laborBtnIds.forEach(id => setBtnLocked(id, false, true));
  }
  function lockLaborButtons(contractionsPer10){
    unlockLaborButtons();
    laborBtnIds.forEach(id => setBtnLocked(id, true, true));
    // Duração real do bloco agendado: início da última contração + 60s.
    const n = Math.max(1, Math.min(5, Number(contractionsPer10 || 4)));
    const ctgSec = 1.2 + ((n - 1) * (600 / n)) + 60;
    const ms = Math.max(1000, (ctgSec * 1000) / Math.max(0.05, getSpeed()));
    laborLockTimer = setTimeout(unlockLaborButtons, ms);
  }
  function resetUiLocks(){
    unlockObstButtons();
    unlockLaborButtons();
    sinusoidalActiveUi = false;
    hipersistoliaActiveUi = false;
    setScenarioActive('btn_sinusoidal', false);
    setScenarioActive('btn_hiper', false);
  }
  function sendReset(){
    resetUiLocks();
    send({mode:'reset', tone:getTocoTone()});
    log('s3', {mode:'reset', tone:getTocoTone()});
  }

  function sendObstEvent(mode, durationSec){
    socket.emit('command', { mode });
    lockObstButtons(durationSec);
  }
  function sendDIPVarVContracao(){ sendObstEvent('dip_variavel_v_contracao', 60); }
  function sendDIPVarVSemContracao(){ sendObstEvent('dip_variavel_v_sem_contracao', 25); }
  function sendDIPVarUContracao(){ sendObstEvent('dip_variavel_u_contracao', 80); }
  function sendDIPVarUSemContracao(){ sendObstEvent('dip_variavel_u_sem_contracao', 85); }
  function sendDIPVarWContracao(){ sendObstEvent('dip_variavel_w_contracao', 65); }
  function sendDIPVarWSemContracao(){ sendObstEvent('dip_variavel_w_sem_contracao', 49); }
  function sendDIPIVerdadeira(){ sendObstEvent('dipi_precoce_verdadeira', 60); }
  function sendDIPTardia(){ sendObstEvent('dip_tardia', 130); }
  function sendAceleracaoTransitoria(){ sendObstEvent('acel_transitoria', 20); }
  function sendSinusoidalToggle(){
    sinusoidalActiveUi = !sinusoidalActiveUi;
    if (sinusoidalActiveUi) {
      hipersistoliaActiveUi = false;
      unlockLaborButtons();
      setScenarioActive('btn_hiper', false);
    }
    setScenarioActive('btn_sinusoidal', sinusoidalActiveUi);
    socket.emit('command', { mode: 'sinusoidal_toggle', tone:getTocoTone() });
  }
  function sendHipersistoliaToggle(){
    hipersistoliaActiveUi = !hipersistoliaActiveUi;
    if (hipersistoliaActiveUi) {
      sinusoidalActiveUi = false;
      unlockLaborButtons();
      setScenarioActive('btn_sinusoidal', false);
    }
    setScenarioActive('btn_hiper', hipersistoliaActiveUi);
    socket.emit('command', { mode: 'hipersistolia_toggle', tone:getTocoTone() });
  }
  function sendLaborRate(n){
    if (laborBtnIds.some(id => btn(id)?.disabled)) return;
    sinusoidalActiveUi = false;
    hipersistoliaActiveUi = false;
    setScenarioActive('btn_sinusoidal', false);
    setScenarioActive('btn_hiper', false);
    lockLaborButtons(n);
    socket.emit('command', {
      mode:'apply_preset',
      name:'labor_' + n,
      tone:getTocoTone()
    });
  }

  // Dicas (baseline ± metade da variação total)
  function updateRangeHints(){
    const base = getBase(), vmin = getVMin(), vmax = getVMax();
    const cb = v=>Math.max(0,Math.min(240,v));
    const halfMax = vmax / 2;
    const halfMin = vmin / 2;
    const eMax=document.getElementById('rangeHintMax'), eMin=document.getElementById('rangeHintMin');
    if(eMax) eMax.textContent=`≈ máx total ${vmax} → ${Math.round(cb(base-halfMax))}–${Math.round(cb(base+halfMax))} bpm`;
    if(eMin) eMin.textContent=`≈ mín total ${vmin} → ${Math.round(cb(base-halfMin))}–${Math.round(cb(base+halfMin))} bpm`;
  }

  // ====== EVENTOS (Presets) ======
  function sendPresetNormal(){ resetUiLocks(); socket.emit('command', { mode:'apply_preset', name:'normal' }); }
  function sendLabor(){ sendLaborRate(4); }

  // Preenche display do card "Eventos"
  socket.on('ack', (m)=>{
    if(!m||!m.echo) return;
    const e=m.echo;

    if (e.mode === 'reset') {
      resetUiLocks();
      return;
    }

    if(e.mode==='apply_preset' && e.name==='normal'){
      resetUiLocks();
      document.getElementById('cfg_mode').textContent='normal';
      document.getElementById('cfg_base').textContent=e.bpm;
      document.getElementById('cfg_vmin').textContent=e.vmin;
      document.getElementById('cfg_vmax').textContent=e.vmax;
      const toneMin = (e.uc_tone_min!=null)? e.uc_tone_min : 0;
      const toneMax = (e.uc_tone_max!=null)? e.uc_tone_max : 0;
      document.getElementById('cfg_uc').textContent = `tônus: ${toneMin}–${toneMax} mmHg (sem contrações)`;
      return;
    }

    if(e.mode==='apply_preset' && (e.name==='labor' || String(e.name||'').startsWith('labor_'))){
      document.getElementById('cfg_mode').textContent='normal (trabalho de parto)';
      document.getElementById('cfg_base').textContent=e.bpm;
      document.getElementById('cfg_vmin').textContent=e.vmin;
      document.getElementById('cfg_vmax').textContent=e.vmax;
      const toneMin = (e.uc_tone_min!=null)? e.uc_tone_min : 0;
      const toneMax = (e.uc_tone_max!=null)? e.uc_tone_max : 0;
      document.getElementById('cfg_uc').textContent = `tônus: ${toneMin}–${toneMax} mmHg, pico até ${e.uc_amp} (60s, ${e.contractions_per_10 ?? 4}/10min)`;
      return;
    }

    if (e.mode === 'sinusoidal_toggle') {
      document.getElementById('cfg_mode').textContent = 'Padrão sinusoidal';
      document.getElementById('cfg_uc').textContent = 'senoide 40s, ±5 bpm, sem ruído aleatório de movimento fetal';
      return;
    }

    if (e.mode === 'hipersistolia_toggle') {
      document.getElementById('cfg_mode').textContent = 'Hipersistolia';
      document.getElementById('cfg_uc').textContent =
        '6 contrações/10min; duração 78s; pico 90 mmHg; tônus basal 23 mmHg; evolução fetal em 10min e estado final persistente';
      return;
    }

    if (e.mode === 'toco_tone') {
      document.getElementById('cfg_mode').textContent = 'TOCO tônus basal';
      document.getElementById('cfg_uc').textContent = `tônus basal fixo em ${e.tone} mmHg`;
      return;
    }

    if (e.mode === 'toco_single') {
      document.getElementById('cfg_mode').textContent = 'TOCO manual';
      document.getElementById('cfg_uc').textContent =
        `contração até ${e.peak} mmHg, duração ${e.duration_sec}s (${(e.duration_sec/30).toFixed(2).replace('.', ',')} quadradinhos)`;
      return;
    }

    if (e.mode === 'toco_normal') {
      document.getElementById('cfg_mode').textContent = 'TOCO normal';
      document.getElementById('cfg_uc').textContent =
        `4 contrações/10min; tônus ${e.tone} mmHg; pico ${e.peak} mmHg; duração ${e.duration_sec}s; encerra após o ciclo`;
      return;
    }

    if (e.mode === 'dip_variavel_v_contracao') {
      document.getElementById('cfg_mode').textContent = 'DIP variável V com onda';
      document.getElementById('cfg_uc').textContent =
        'TOCO 60s até 50 mmHg; ombro +15 bpm antes e depois; queda de 60 bpm em 10s com nadir no pico da contração';
      return;
    }

    if (e.mode === 'dip_variavel_v_sem_contracao') {
      document.getElementById('cfg_mode').textContent = 'DIP variável V sem onda';
      document.getElementById('cfg_uc').textContent =
        'Sem TOCO; FHR cai 45 bpm em 12s e sobe em 13s';
      return;
    }

    if (e.mode === 'dip_variavel_u_contracao') {
      document.getElementById('cfg_mode').textContent = 'DIP variável U com onda';
      document.getElementById('cfg_uc').textContent =
        'TOCO 60s até 50 mmHg; FHR cai 70 bpm, fica 30s no nadir e normaliza 20s após a contração';
      return;
    }

    if (e.mode === 'dip_variavel_u_sem_contracao') {
      document.getElementById('cfg_mode').textContent = 'DIP variável U sem onda';
      document.getElementById('cfg_uc').textContent =
        'Sem TOCO; FHR cai 60 bpm em 20s, mantém 40s no nadir e retorna em 25s';
      return;
    }

    if (e.mode === 'dip_variavel_w_contracao') {
      document.getElementById('cfg_mode').textContent = 'DIP variável W com onda';
      document.getElementById('cfg_uc').textContent =
        'TOCO 60s até 50 mmHg; W inicia no 10º segundo, com duas quedas e recuperação em 20s';
      return;
    }

    if (e.mode === 'dip_variavel_w_sem_contracao') {
      document.getElementById('cfg_mode').textContent = 'DIP variável W sem onda';
      document.getElementById('cfg_uc').textContent =
        'Sem TOCO; queda 50 bpm, recuperação parcial, nova queda 35 bpm e retorno em 15s';
      return;
    }

    if (e.mode === 'dip_variavel') {
      document.getElementById('cfg_mode').textContent = 'DIP variável';
      document.getElementById('cfg_uc').textContent = `TOCO 60s até ${e.uc_peak ?? 50} + FHR em V por ${e.duration ?? 40}s até ${e.fhr_target ?? 100} bpm`;
      return;
    }

    if (e.mode === 'dipi_precoce_verdadeira') {
      document.getElementById('cfg_mode').textContent = 'DIP precoce';
      document.getElementById('cfg_uc').textContent =
        `TOCO 60s até ${e.uc_peak ?? 50} (pico no vale); ` +
        `FHR em V por ${e.fhr_total_sec ?? 40}s até ${e.fhr_target ?? 100} (nadir no pico da TOCO)`;
      return;
    }

    if (e.mode === 'dip_tardia') {
      document.getElementById('cfg_mode').textContent = 'DIP tardia';
      document.getElementById('cfg_uc').textContent =
        `TOCO 60s até ${e.uc_peak ?? 50}; ` +
        `FHR tardia: queda 30s até o nadir, nadir 40s após o pico da TOCO, retorno em 60s ao basal`;
      return;
    }

    if (e.mode === 'acel_transitoria') {
      document.getElementById('cfg_mode').textContent = 'Aceleração transitória';
      document.getElementById('cfg_uc').textContent =
        `FHR sobe +${e.rise ?? 16} bpm, duração ${e.duration ?? 20}s e depois retorna ao basal`;
      return;
    }

    if(e.mode==='set_baseline' && typeof e.bpm==='number'){
      const el=document.getElementById('cfg_base'); if(el) el.textContent=e.bpm;
    } else if(e.mode==='set_var'){
      const vminEl=document.getElementById('cfg_vmin'), vmaxEl=document.getElementById('cfg_vmax');
      if(vminEl) vminEl.textContent=e.vmin; if(vmaxEl) vmaxEl.textContent=e.vmax;
    } else if(e.mode==='uc_level' && typeof e.uc==='number'){
      const el=document.getElementById('cfg_uc'); if(el) el.textContent=e.uc;
    } else if(e.mode && ['normal','tachy','brady','afib','asystole'].includes(e.mode)){
      const el=document.getElementById('cfg_mode'); if(el) el.textContent=e.mode;
    }
  });

  // ====== Modo / Baseline / Variação / TOCO ======
  function sendRitmo(mode){ send({mode}); log('s1',{mode}); }

  function getBase(){ return parseInt(document.getElementById('base_num').value,10)||140; }
  function syncBase(v){
    let n=clamp(parseInt(v||0,10),0,240);
    base_range.value=n; base_num.value=n; basepill.textContent=n;
    updateRangeHints();
  }
  function sendBaseline(){ const p={mode:'set_baseline', bpm:getBase()}; send(p); log('s1',p); }

  function getVMin(){
    const v = parseInt(document.getElementById('vmin_num').value,10);
    return isNaN(v) ? 0 : v;
  }
  function getVMax(){
    const v = parseInt(document.getElementById('vmax_num').value,10);
    return isNaN(v) ? 0 : v;
  }
  function syncVMin(v){
    let n=clamp(parseInt(v||0,10),0,80);
    const vmax=getVMax(); if(n>vmax) n=vmax;
    vmin_range.value=n; vmin_num.value=n; vminpill.textContent=n;
    updateRangeHints();
  }
  function syncVMax(v){
    let n=clamp(parseInt(v||0,10),0,80);
    const vmin=getVMin(); if(n<vmin) n=vmin;
    vmax_range.value=n; vmax_num.value=n; vmaxpill.textContent=n;
    updateRangeHints();
  }
  function sendSetVar(){ const p={mode:'set_var', vmin:getVMin(), vmax:getVMax()}; send(p); log('s1',p); }

  function getTocoTone(){ return parseInt(document.getElementById('toco_tone_num').value,10)||0; }
  function syncTocoTone(v){
    const n=clamp(parseInt(v||0,10),0,100);
    toco_tone_range.value=n; toco_tone_num.value=n; toco_tone_pill.textContent=n;
  }

  function getTocoPeak(){ return parseInt(document.getElementById('toco_peak_num').value,10)||0; }
  function syncTocoPeak(v){
    const n=clamp(parseInt(v||0,10),0,100);
    toco_peak_range.value=n; toco_peak_num.value=n; toco_peak_pill.textContent=n;
  }

  function getTocoDuration(){ return parseInt(document.getElementById('toco_dur_num').value,10)||50; }
  function syncTocoDuration(v){
    const n=clamp(parseInt(v||0,10),5,70);
    toco_dur_range.value=n; toco_dur_num.value=n; toco_dur_pill.textContent=n + 's';
    const squares = (n / 30).toFixed(2).replace('.', ',');
    const el = document.getElementById('toco_grid_hint');
    if(el) el.textContent = `${n}s ≈ ${squares} quadradinhos`;
  }

  function sendTocoTone(){
    const p = {
      mode:'toco_tone',
      tone:getTocoTone()
    };
    send(p);
    log('s3', p);
  }

  function sendTocoContraction(){
    const p = {
      mode:'toco_single',
      peak:getTocoPeak(),
      duration_sec:getTocoDuration()
    };
    send(p);
    log('s3', p);
  }

  updateRangeHints();
  syncTocoDuration(getTocoDuration());
</script>

</body>
</html>
"""

# ===================== TELA 2 (MONITOR) =====================

MONITOR_HTML = r"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8" />
<title>Tela 2 — Monitor (CTG grid fixo)</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root { font-family: system-ui, Arial; }
  body { margin:0; background:#0a1022; color:#d6e5ff; }
  header { padding:6px 10px; background:#0f1630; border-bottom:1px solid #1a2750; font-size:13px; }
  .topbar { display:flex; gap:14px; align-items:center; white-space:nowrap; }
  .wrap { display:grid; grid-template-columns: 4fr 1.2fr; gap:0; height: calc(100vh - 42px); }
  .left { padding:8px 10px 10px 10px; }
  .stack { display:flex; flex-direction:column; gap:8px; height:100%; }
  .panel { background:#0b1430; border:1px solid #1b2a57; border-radius:10px; padding:8px; flex:1; position:relative; }
  .title { position:absolute; left:10px; top:8px; font-size:12px; opacity:.8 }
  canvas { display:block; width:100%; height:100%; background:#091334; border-radius:8px; }
  .right { background:#0b1430; border-left:1px solid #1b2a57; padding:10px; display:flex; flex-direction:column; gap:10px; }
  .chip { background:#0e1d3a; border:1px solid #18305f; padding:6px 10px; border-radius:999px; font-size:12px; width:max-content }
  .big { font-size:84px; font-weight:800; line-height:0.95 }
  .lab { font-size:12px; opacity:.75 }
  .pink { color:#ff4dc4 }
  .green { color:#20d37b }
  .vio { color:#b48fff }
  .clock { margin-top:auto; font-size:14px; opacity:.85 }
  .legend { display:flex; gap:10px; align-items:center; font-size:12px; opacity:.85 }
  .dot { width:10px; height:3px; border-radius:2px; display:inline-block; }
  .dot-fhr { background:#ff4dc4 }
  .dot-uc { background:#20d37b }
  .btn { background:#18305f; border:1px solid #25478e; color:#d6e5ff; border-radius:10px; padding:6px 10px; cursor:pointer; width:max-content; }
</style>
</head>
<body>
  <header>
    <div class="topbar">
      <span>* CTG simulado</span>
      <span class="chip">Status: <span id="conn">desconectado</span></span>
      <span class="chip">Ritmo: <span id="mode">normal</span></span>
      <span class="chip">BPM: <span id="bpm">140</span></span>
      <span class="chip">UC: <span id="uc">10</span></span>
      <span class="legend"><span class="dot dot-fhr"></span> FHR</span>
      <span class="legend"><span class="dot dot-uc"></span> TOCO</span>
      <button class="btn" id="soundBtn">Ativar sonar</button>
    </div>
  </header>

  <div class="wrap">
    <div class="left">
      <div class="stack">
        <div class="panel">
          <div class="title">FHR (20–240 bpm)</div>
          <canvas id="hrCanvas" width="1200" height="420"></canvas>
        </div>
        <div class="panel">
          <div class="title">TOCO (0–100 mmHg)</div>
          <canvas id="ucCanvas" width="1200" height="280"></canvas>
        </div>
      </div>
    </div>

    <aside class="right">
      <div class="lab">FHR</div>
      <div class="big pink" id="bpmBig">140</div>
      <div class="lab" style="margin-top:8px">TOCO</div>
      <div class="big green" id="ucBig">10</div>
      <div class="lab" style="margin-top:12px">Modo</div>
      <div class="vio" id="modeTag">normal</div>
      <div class="clock" id="clock">--:--:--</div>
    </aside>
  </div>

<script src="https://cdn.socket.io/4.7.5/socket.io.min.js" crossorigin="anonymous"></script>
<script>
  // ===== Estado/HUD =====
  const ROOM_ID = "{{ room_id }}";
  const socket = io({ query: { room: ROOM_ID } });
  const connEl  = document.getElementById('conn');
  const modeEl  = document.getElementById('mode');
  const modeTag = document.getElementById('modeTag');
  const bpmEl   = document.getElementById('bpm');
  const bpmBig  = document.getElementById('bpmBig');
  const ucEl    = document.getElementById('uc');
  const ucBig   = document.getElementById('ucBig');
  const clockEl = document.getElementById('clock');

// --- helpers de forma (usados pelo monitor) ---
function clamp01(t){ return Math.max(0, Math.min(1, t)); }
function smooth01(t){ t = clamp01(t); return t*t*(3 - 2*t); }

function trapezoid01(x, riseFrac=0.20, fallFrac=0.20){
  x = clamp01(x);
  const platStart = clamp01(riseFrac);
  const platEnd   = clamp01(1 - fallFrac);
  if (platStart + fallFrac > 1) {
    const s = (riseFrac) / (riseFrac + fallFrac);
    return (x < s) ? smooth01(x/s) : 1 - smooth01((x - s)/(1 - s));
  }
  if (x < platStart) return smooth01(x / platStart);
  if (x <= platEnd)  return 1;
  return 1 - smooth01((x - platEnd) / (1 - platEnd));
}

function hann01(x){
  x = clamp01(x);
  return 0.5 - 0.5 * Math.cos(2 * Math.PI * x);
}

function gauss01(x, sigma=0.20){
  x = clamp01(x);
  const s = Math.max(0.05, sigma);
  const z = (x - 0.5) / s;
  return Math.exp(-0.5 * z * z);
}

// NOVO: forma em "V" suave (vamos usar nas desacelerações em V)
function vshape01(x){
  x = clamp01(x);
  return (x < 0.5) ? smooth01(x/0.5) : smooth01((1 - x)/0.5);
}

// Forma assimétrica para a DIP tardia: queda um pouco mais rápida
// e retorno mais lento, lembrando levemente um sinal de certo (✓).
function asymVShape01(x, nadirFrac=0.40){
  x = clamp01(x);
  const n = Math.max(0.25, Math.min(0.49, nadirFrac));
  return (x < n) ? smooth01(x / n) : smooth01((1 - x) / (1 - n));
}

// Padrão sinusoidal: senoide mecânica, mais espaçada e sem variabilidade basal.
// Ciclo de 40s: 140 → 145 → 140 → 135 → 140, com áudio previsível e hipnótico.
const SINUSOIDAL_PERIOD_MS = 40000;
const SINUSOIDAL_AMP_BPM = 5;
function sinusoidalOffset(nowMs){
  if (!state.sinusoidalOn) return 0;
  const phase = (((nowMs - state.sinusoidalStartMs) % SINUSOIDAL_PERIOD_MS) + SINUSOIDAL_PERIOD_MS) % SINUSOIDAL_PERIOD_MS;
  return SINUSOIDAL_AMP_BPM * Math.sin((2 * Math.PI * phase) / SINUSOIDAL_PERIOD_MS);
}

// Hipersistolia: 6 contrações/10min, contrações longas, pouco repouso e hipertonia.
// O cenário evolui por 10min e, depois, mantém a FHR terminal até ser desligado.
const HYPER_PERIOD_MS = 100000;       // 6 contrações em 10min
const HYPER_UC_DUR_MS = 78000;        // 78s contraindo, ~22s de repouso
const HYPER_UC_TONE = 23;             // hipertonia basal 20–25 mmHg
const HYPER_UC_PEAK = 90;             // pico alto 80–100 mmHg

function hipersistoliaSec(nowMs){
  return Math.max(0, (nowMs - (state.hipersistoliaStartMs || nowMs)) / 1000);
}

function hipersistoliaUCValue(nowMs){
  const phaseMs = (((nowMs - state.hipersistoliaStartMs) % HYPER_PERIOD_MS) + HYPER_PERIOD_MS) % HYPER_PERIOD_MS;
  if (phaseMs <= HYPER_UC_DUR_MS) {
    const env = hann01(phaseMs / HYPER_UC_DUR_MS);
    return HYPER_UC_TONE + env * (HYPER_UC_PEAK - HYPER_UC_TONE);
  }
  return HYPER_UC_TONE;
}

function hipersistoliaLateDrop(sec){
  // DIPs tardias repetitivas entre 3 e 7 min. A queda começa após a contração subir,
  // o nadir vem atrasado e a recuperação invade parcialmente o repouso.
  const period = 100;
  const ucDur = 78;
  let maxDrop = 0;

  // Avalia ciclo atual e anterior para permitir cauda tardia após o fim da contração.
  const baseCycle = Math.floor(sec / period) * period;
  for (let j = -1; j <= 0; j++){
    const cycleStart = baseCycle + j * period;
    const c = sec - cycleStart;
    const fallStart = 48;       // começa bem depois do início da contração
    const nadirAt = 72;         // nadir após o pico da contração
    const recoverEnd = ucDur + 30; // volta cerca de 30s após a contração terminar

    if (c < fallStart || c > recoverEnd) continue;

    let drop;
    if (c <= nadirAt) {
      drop = 60 * smooth01((c - fallStart) / (nadirAt - fallStart));
    } else {
      drop = 60 * (1 - smooth01((c - nadirAt) / (recoverEnd - nadirAt)));
    }
    if (drop > maxDrop) maxDrop = drop;
  }

  return maxDrop;
}

function hipersistoliaFHRValue(dt, nowMs){
  const sec = hipersistoliaSec(nowMs);

  // 0–3 min: estresse/compensação, baseline sobe e a variabilidade fica áspera.
  if (sec < 180) {
    const u = smooth01(sec / 180);
    const base = 140 + 28 * u;
    const amp = 5 + 13 * u;
    stv += (Math.random() - 0.5) * 0.42 * amp;
    stv *= 0.90;
    const spikes =
      0.40 * amp * Math.sin(nowMs / 720 + phi) +
      0.25 * amp * Math.sin(nowMs / 310 + 1.9 * phi) +
      (Math.random() - 0.5) * 0.55 * amp;
    return Math.max(30, Math.min(240, base + stv + spikes));
  }

  // 3–7 min: taquicardia sustentada com DIPs tardias em praticamente toda contração.
  if (sec < 420) {
    const base = 170;
    const drop = hipersistoliaLateDrop(sec);
    const rough = 2.5 * Math.sin(nowMs / 950 + phi) + (Math.random() - 0.5) * 4.0;
    return Math.max(30, Math.min(240, base - drop + rough));
  }

  // 7–10 min: queda terminal abrupta para bradicardia profunda e perda da variabilidade.
  if (sec < 600) {
    const u = smooth01(Math.min(1, (sec - 420) / 24));
    const base = 170 + (75 - 170) * u;
    const minimal = (1 - u) * ((Math.random() - 0.5) * 3.0) + u * (0.25 * Math.sin(nowMs / 500));
    return Math.max(30, Math.min(240, base + minimal));
  }

  // Após 10 min: permanece no estado final até clicar novamente.
  return 75 + 0.2 * Math.sin(nowMs / 700);
}

// Eventos one-shot de TOCO (picos únicos)
const uc_events = [];

function scheduleUCOneShot(peak, durMs, sigma = 0.20, delayMs = 0){
  const now = ctgNow();
  uc_events.push({
    start: now + Math.max(0, Number(delayMs || 0)),
    durMs: Math.max(1000, Number(durMs || 0)),
    peak: Math.max(0, Math.min(100, Number(peak || 0))),
    shape: 'hann',   // subida e descida suaves, sem degrau no início
    sigma,           // (ignorado quando shape = 'hann')
    startFrom: null  // vamos capturar do baseline no 1º frame ativo
  });
}

function scheduleDecelV(delaySec, totalSec, targetBpm, options = {}){
  const now = ctgNow();
  const total = Math.max(40, Number(totalSec || 40)); // todas as DIPs têm pelo menos 40s
  events.push({
    kind: 'decel_v',
    start: now + Math.max(0, Number(delaySec || 0) * 1000),
    durMs: Math.max(1000, total * 1000),
    target: Math.max(30, Math.min(240, targetBpm|0)),
    shape: options.shape || 'symmetric_v',
    nadirFrac: (typeof options.nadirFrac === 'number') ? options.nadirFrac : 0.5,
    rippleScale: (typeof options.rippleScale === 'number') ? options.rippleScale : 0.08,
    skipClamp: true  // permite passar do limite ±variação durante o evento
  });
}

// DIPI sincronizada: cai até targetBpm e volta no mesmo tempo da contração
function scheduleDecelSynced(durSec, targetBpm){
  const now = ctgNow();
  events.push({
    kind: 'decel_sync',
    start: now,
    durMs: Math.max(1000, (durSec||0) * 1000),
    target: Math.max(30, Math.min(240, targetBpm|0)),
    skipClamp: true // permite passar do limite ±variação
  });
}

// Curvas livres para as novas DIPs variáveis.
// points = [[tempo_em_segundos, offset_bpm], ...]
// Ex.: offset -60 significa cair 60 bpm em relação à linha de base daquele momento.
function scheduleFhrKeyframes(points, options = {}){
  if (!points || !points.length) return;
  const cleanPoints = points
    .map(p => [Number(p[0] || 0), Number(p[1] || 0)])
    .filter(p => isFinite(p[0]) && isFinite(p[1]))
    .sort((a,b) => a[0] - b[0]);

  if (!cleanPoints.length) return;
  const totalSec = Math.max(1, cleanPoints[cleanPoints.length - 1][0]);
  const now = ctgNow();

  events.push({
    kind: 'fhr_keyframes',
    start: now + Math.max(0, Number(options.delaySec || 0) * 1000),
    durMs: totalSec * 1000,
    points: cleanPoints,
    smooth: options.smooth !== false,
    skipClamp: true
  });
}

function keyframeOffset(points, sec, useSmooth = true){
  if (!points || !points.length) return 0;
  if (sec <= points[0][0]) return points[0][1];

  for (let i = 0; i < points.length - 1; i++){
    const t0 = points[i][0], y0 = points[i][1];
    const t1 = points[i+1][0], y1 = points[i+1][1];

    if (sec <= t1){
      if (t1 <= t0) return y1;
      let u = (sec - t0) / (t1 - t0);
      u = clamp01(u);
      if (useSmooth) u = smooth01(u);
      return y0 + (y1 - y0) * u;
    }
  }

  return points[points.length - 1][1];
}

function scheduleVariableDip(mode){
  const UC_DUR_MS = 60000;
  const UC_PEAK = 50;

  if (mode === 'dip_variavel_v_contracao'){
    scheduleUCOneShot(UC_PEAK, UC_DUR_MS, 0.22);
    scheduleFhrKeyframes([
      [0,   0],
      [5,   0],
      [10,  15],
      [15,  15],
      [20,  0],
      [30, -60],
      [40,  0],
      [45,  15],
      [50,  15],
      [55,  0],
      [60,  0]
    ]);
    return;
  }

  if (mode === 'dip_variavel_v_sem_contracao'){
    scheduleFhrKeyframes([
      [0,   0],
      [12, -45],
      [25,  0]
    ]);
    return;
  }

  if (mode === 'dip_variavel_u_contracao'){
    scheduleUCOneShot(UC_PEAK, UC_DUR_MS, 0.22);
    scheduleFhrKeyframes([
      [0,   0],
      [15,  0],
      [30, -70],
      [60, -70],
      [80,  0]
    ]);
    return;
  }

  if (mode === 'dip_variavel_u_sem_contracao'){
    scheduleFhrKeyframes([
      [0,   0],
      [20, -60],
      [60, -60],
      [85,  0]
    ]);
    return;
  }

  if (mode === 'dip_variavel_w_contracao'){
    scheduleUCOneShot(UC_PEAK, UC_DUR_MS, 0.22);
    scheduleFhrKeyframes([
      [0,   0],
      [10,  0],
      [20, -60],
      [30, -30],
      [40, -65],
      [45, -65],
      [65,  0]
    ]);
    return;
  }

  if (mode === 'dip_variavel_w_sem_contracao'){
    scheduleFhrKeyframes([
      [0,   0],
      [12, -50],
      [22, -20],
      [34, -55],
      [49,  0]
    ]);
    return;
  }
}


// Bloqueia novo comando de DIP/aceleração até o evento atual terminar.
let obstEventBusyUntil = 0;
const OBST_EVENT_DURATIONS = {
  acel_transitoria: 20,
  dipi_precoce_verdadeira: 60,
  dip_tardia: 130,
  dip_variavel_v_contracao: 60,
  dip_variavel_v_sem_contracao: 25,
  dip_variavel_u_contracao: 80,
  dip_variavel_u_sem_contracao: 85,
  dip_variavel_w_contracao: 65,
  dip_variavel_w_sem_contracao: 49
};
function obstEventDurationSec(p){
  if (!p || !p.mode) return 0;
  if (p.mode === 'acel_transitoria') return Math.max(1, Number(p.duration || 20));
  if (p.mode === 'dipi_precoce_verdadeira') {
    const total = Math.max(40, Number(p.fhr_total_sec || 40));
    const delay = Math.max(0, Number(p.fhr_delay_sec || 0));
    const ucDur = Math.max(1, Number(p.uc_duration_sec || 60));
    return Math.max(ucDur, delay + total);
  }
  if (p.mode === 'dip_tardia') {
    const fall = Math.max(1, Number(p.late_fall_sec || 30));
    const ret = Math.max(1, Number(p.late_return_sec || 60));
    const delay = Math.max(0, Number(p.fhr_delay_sec || 40));
    const ucDur = Math.max(1, Number(p.uc_duration_sec || 60));
    return Math.max(ucDur, delay + fall + ret);
  }
  return OBST_EVENT_DURATIONS[p.mode] || 0;
}
function tryStartObstEvent(p){
  const dur = obstEventDurationSec(p);
  if (!dur) return true;
  const now = ctgNow();
  if (now < obstEventBusyUntil) return false;
  obstEventBusyUntil = now + dur * 1000;
  return true;
}
function clearTimedEvents(){
  events.length = 0;
  uc_events.length = 0;
  obstEventBusyUntil = 0;
}

function setStaticTocoTone(tone){
  const t = Math.max(0, Math.min(100, tone | 0));

  // Tônus basal fixo, sem oscilação automática.
  // Se o usuário escolhe 10, a linha basal permanece em 10 mmHg.
  state.uc_tone_min = t;
  state.uc_tone_max = t;

  // Não muda ucTone de uma vez. Só muda o alvo.
  // A função sampleUC() faz a linha subir/descer suavemente até esse alvo.
  ucToneTarget = t;
  ucToneTimer = 0;
}

function rememberAndSetTocoTone(tone){
  const t = Math.max(0, Math.min(100, tone | 0));
  state.preferredTocoTone = t;
  setStaticTocoTone(t);
}

function clearTocoContractions(){
  uc_events.length = 0;       // tira contrações antigas/agendadas
  state.uc_paused = false;
  state.uc_level = 0;         // desliga contração periódica antiga
  laborAuto.enabled = false;  // não deixa o ciclo antigo interferir
}

function configureTocoContractions(tone, peak, durSec, count = 1, periodMs = 150000){
  const t = Math.max(0, Math.min(100, tone | 0));
  const p = Math.max(t, Math.max(0, Math.min(100, peak | 0)));
  const d = Math.max(5, Math.min(90, durSec | 0));
  const c = Math.max(1, Math.min(10, count | 0));
  const per = Math.max(1000, periodMs | 0);

  clearTocoContractions();
  rememberAndSetTocoTone(t);

  // Nos cenários de trabalho de parto, a contração deve sair exatamente do tônus basal
  // setado e voltar para ele. Por isso alinhamos imediatamente o tônus atual ao alvo.
  ucTone = t;
  ucToneTarget = t;
  ucToneTimer = 1000000000;

  // Pequeno lead-in para a primeira onda não nascer já desenhada em fase intermediária.
  // Isso remove o degrau/erro visual no início dos cenários 1/10 a 5/10.
  const firstDelayMs = 1200;
  for (let i = 0; i < c; i++){
    scheduleUCOneShot(p, d * 1000, 0.20, firstDelayMs + i * per);
  }
}

function configureTocoContractionsFromCurrentTone(peak, durSec, count = 1, periodMs = 150000){
  const currentTone = Math.max(0, Math.min(100, Math.round(ucTone)));
  const p = Math.max(currentTone, Math.max(0, Math.min(100, peak | 0)));
  const d = Math.max(5, Math.min(70, durSec | 0));
  const c = Math.max(1, Math.min(10, count | 0));
  const per = Math.max(1000, periodMs | 0);

  clearTocoContractions();

  for (let i = 0; i < c; i++){
    scheduleUCOneShot(p, d * 1000, 0.20, i * per);
  }
}

 let state = {
  mode:'normal',
  bpm:140,
  fhr_base:140,
  fhr_base_target:140,
  var_min:5, var_max:25,
  uc_level:0, uc_paused:false,
  showBand:false,
  sinusoidalOn:false,
  sinusoidalStartMs:0,
  hipersistoliaOn:false,
  hipersistoliaStartMs:0,
  preferredTocoTone:10,
  // inicia no modo Basal/Repouso: sem contrações, com tônus basal fixo em 10 mmHg
  uc_pattern: { period_ms: 150000, dur_ms: 13000 },
  uc_tone_min: 10, 
  uc_tone_max: 10,
  timeScale: 1.0
};

let laborAuto = {
  enabled: false,
  max: 4,
  windowMs: 600000, // 10 min
  period: 150000,   // será atualizado pelo servidor
  count: 0,
  startMs: 0,
  lastPhase: 0
};

  // ===== Canvases =====
  const hr  = document.getElementById('hrCanvas');  const hrx  = hr.getContext('2d');
  const ucC = document.getElementById('ucCanvas');  const ucx  = ucC.getContext('2d');

  // ===== RÉGUA CTG (fixa) =====
 // Requisito: 1 quadradinho = 30s; 2 quadradinhos = 1 min; papel = 1 cm/min
   const BASE_PAPER_CM_PER_MIN = 1.0;
   const SMALL_SQUARE_SEC = 30;
   const MS = 1000;

  // Aproximação: 96dpi ~ 37.795 px/cm (mantém proporção)
  const PX_PER_CM = 37.795;

  // pixels por ms em 1 cm/min  => 1 cm / 60s
  const pxPerMs = (PX_PER_CM * BASE_PAPER_CM_PER_MIN) / (60 * 1000);

  // tamanhos do grid no eixo do tempo
  const pxSmall = SMALL_SQUARE_SEC * MS * pxPerMs; // 30s -> 0.5cm
  const pxBig   = 2 * pxSmall;                     // 60s -> 1cm

  // ===== Cursor (ESQ -> DIR) =====
  let xHR = 0, xUC = 0;
  const stepHR = 2, stepUC = 2;
  let prevXhr = 0, prevYhr = Math.round(hr.height*0.52);
  let prevXuc = 0, prevYuc = Math.round(ucC.height*0.9);

  // ===== Grid offscreen (fixo) =====
  let gridHR = null, gridUC = null;

  // Régua vertical
  function drawVerticalScale(c, minVal, maxVal, step, axisX){
    const g = c.getContext('2d');
    const w = c.width, h = c.height;
    g.save();
    g.strokeStyle = '#cfe3ff'; g.globalAlpha = 0.9; g.lineWidth = 1;
    g.beginPath(); g.moveTo(axisX, 0); g.lineTo(axisX, h); g.stroke();
    g.fillStyle = '#cfe3ff'; g.font = '12px system-ui, Arial, sans-serif';
    g.textAlign = 'right'; g.textBaseline = 'middle';
    const yFromVal = (v)=> Math.round((1 - (v - minVal) / (maxVal - minVal)) * (h - 1));
    for (let v = minVal; v <= maxVal; v += step){
      const y = yFromVal(v);
      g.beginPath(); g.moveTo(axisX - 6, y); g.lineTo(axisX + 6, y); g.stroke();
      g.fillText(String(v), axisX - 8, y);
    }
    g.restore();
  }

 function makeGridCanvas(w, h) {
  const c = document.createElement('canvas'); 
  c.width = w; 
  c.height = h;

  const g = c.getContext('2d');

  // fundo
  g.fillStyle = '#091334';
  g.fillRect(0, 0, w, h);

  // >>> AQUI É O PONTO QUE MUDA: o grid agora usa a régua CTG
  const MINOR = pxSmall;  // 30s por quadradinho (X)
  const MAJOR = pxBig;    // 1 min (2 quadradinhos) por linha forte

  const minorColor = '#5160d6', majorColor = '#7d88ff';

  // linhas finas
  g.strokeStyle = minorColor;
  g.globalAlpha = 0.45;
  g.lineWidth = 1;

  for (let x = 0; x <= w; x += MINOR) {
    const xi = Math.round(x);
    g.beginPath(); 
    g.moveTo(xi, 0); 
    g.lineTo(xi, h); 
    g.stroke();
  }
  for (let y = 0; y <= h; y += MINOR) {
    const yi = Math.round(y);
    g.beginPath(); 
    g.moveTo(0, yi); 
    g.lineTo(w, yi); 
    g.stroke();
  }

  // linhas fortes
  g.strokeStyle = majorColor;
  g.globalAlpha = 0.9;
  g.lineWidth = 1.2;

  for (let x = 0; x <= w; x += MAJOR) {
    const xi = Math.round(x);
    g.beginPath(); 
    g.moveTo(xi, 0); 
    g.lineTo(xi, h); 
    g.stroke();
  }
  for (let y = 0; y <= h; y += MAJOR) {
    const yi = Math.round(y);
    g.beginPath(); 
    g.moveTo(0, yi); 
    g.lineTo(w, yi); 
    g.stroke();
  }

  g.globalAlpha = 1;
  return c;
}

function buildGrids() {
  gridHR = makeGridCanvas(hr.width,  hr.height);
  gridUC = makeGridCanvas(ucC.width, ucC.height);

  if (state.showBand) {
    const g = gridHR.getContext('2d');
    const bandTop = Math.round(hr.height * 0.25);
    const bandH   = Math.round(hr.height * 0.24);
    g.save();
    g.globalAlpha = 0.14;
    g.fillStyle = '#244a9a';
    g.fillRect(0, bandTop, hr.width, bandH);
    g.restore();
  }

  const axisX = 96;
  drawVerticalScale(gridHR, 30, 240, 30, axisX);
  drawVerticalScale(gridUC, 0, 100, 20, axisX);

  hrx.globalCompositeOperation = 'source-over';
  hrx.clearRect(0, 0, hr.width, hr.height);
  hrx.drawImage(gridHR, 0, 0);

  ucx.globalCompositeOperation = 'source-over';
  ucx.clearRect(0, 0, ucC.width, ucC.height);
  ucx.drawImage(gridUC, 0, 0);
}

  // ===== Som Doppler / sonar fetal =====
  let audioCtx = null, soundOn = false;
  let sonarMaster = null;
  let sonarCompressor = null;
  let noiseBuffer = null;
  let backgroundNoise = null;
  let placentaOsc = null;
  let placentaGain = null;

  // Perfil de áudio: no PC mantém exatamente o mesmo som;
  // no celular/tablet aplica filtros extras e desbloqueio de áudio.
  const AUDIO_IS_MOBILE_OR_TABLET =
    /Android|iPhone|iPad|iPod|Mobile|Tablet/i.test(navigator.userAgent) ||
    (navigator.maxTouchPoints > 1 && /Macintosh/i.test(navigator.userAgent));
  let mobileAudioUnlocked = false;

  async function resumeAudioContextFromGesture(){
    if (!audioCtx) ensureAudio();
    if (!audioCtx) return false;

    try {
      if (audioCtx.state === 'suspended') await audioCtx.resume();
    } catch (e) {}

    // iOS/iPadOS/Android às vezes só liberam o WebAudio depois
    // de um som curtíssimo iniciado diretamente pelo toque do usuário.
    if (AUDIO_IS_MOBILE_OR_TABLET && !mobileAudioUnlocked) {
      try {
        const t = audioCtx.currentTime + 0.01;
        const osc = audioCtx.createOscillator();
        const g = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(120, t);
        g.gain.setValueAtTime(0.00001, t);
        osc.connect(g).connect(audioCtx.destination);
        osc.start(t);
        osc.stop(t + 0.04);
        mobileAudioUnlocked = true;
      } catch (e) {}
    }

    return audioCtx.state === 'running';
  }

  function ensureAudio(){
    if (audioCtx) return;

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    sonarCompressor = audioCtx.createDynamicsCompressor();
    sonarCompressor.threshold.setValueAtTime(-24, audioCtx.currentTime);
    sonarCompressor.knee.setValueAtTime(18, audioCtx.currentTime);
    sonarCompressor.ratio.setValueAtTime(3, audioCtx.currentTime);
    sonarCompressor.attack.setValueAtTime(0.004, audioCtx.currentTime);
    sonarCompressor.release.setValueAtTime(0.16, audioCtx.currentTime);

    sonarMaster = audioCtx.createGain();
    sonarMaster.gain.setValueAtTime(0.0001, audioCtx.currentTime);
    sonarMaster.connect(sonarCompressor).connect(audioCtx.destination);

    // Buffer de ruído branco reaproveitado para chiado, sopro e "vruush".
    const sr = audioCtx.sampleRate;
    noiseBuffer = audioCtx.createBuffer(1, sr * 2, sr);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < data.length; i++){
      data[i] = Math.random() * 2 - 1;
    }

    startBackgroundDopplerNoise();
    startPlacentalHum();
  }

  function startBackgroundDopplerNoise(){
    if (!audioCtx || !noiseBuffer || backgroundNoise) return;

    const src = audioCtx.createBufferSource();
    src.buffer = noiseBuffer;
    src.loop = true;

    const hp = audioCtx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 120 : 180, audioCtx.currentTime);

    const lp = audioCtx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 900 : 1400, audioCtx.currentTime);

    const g = audioCtx.createGain();
    g.gain.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 0.0045 : 0.014, audioCtx.currentTime);

    src.connect(hp).connect(lp).connect(g).connect(sonarMaster);
    src.start();

    backgroundNoise = src;
  }

  function startPlacentalHum(){
    if (!audioCtx || placentaOsc) return;

    // Sopro placentário grave e discreto, só para dar corpo ao Doppler.
    placentaOsc = audioCtx.createOscillator();
    placentaOsc.type = 'sine';
    placentaOsc.frequency.setValueAtTime(72, audioCtx.currentTime);

    const lp = audioCtx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 150 : 170, audioCtx.currentTime);

    placentaGain = audioCtx.createGain();
    placentaGain.gain.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 0.014 : 0.018, audioCtx.currentTime);

    placentaOsc.connect(lp).connect(placentaGain).connect(sonarMaster);
    placentaOsc.start();
  }

  document.getElementById('soundBtn').onclick = async () => {
    await resumeAudioContextFromGesture();
    if (!audioCtx || !sonarMaster) return;

    soundOn = !soundOn;
    const now = audioCtx.currentTime;

    if (soundOn) {
      sonarMaster.gain.cancelScheduledValues(now);
      sonarMaster.gain.setValueAtTime(Math.max(0.0001, sonarMaster.gain.value), now);
      sonarMaster.gain.exponentialRampToValueAtTime(0.85, now + 0.12);
      document.getElementById('soundBtn').textContent = "Sonar ligado";

      // Só no celular/tablet: dispara um batimento logo após o toque
      // para confirmar o desbloqueio do áudio. No PC, não altera o comportamento.
      if (AUDIO_IS_MOBILE_OR_TABLET) {
        resetSonarTiming();
        setTimeout(() => { if (soundOn) beep(state.bpm || 140); }, 80);
      }
    } else {
      sonarMaster.gain.cancelScheduledValues(now);
      sonarMaster.gain.setValueAtTime(Math.max(0.0001, sonarMaster.gain.value), now);
      sonarMaster.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
      document.getElementById('soundBtn').textContent = "Ativar sonar";
    }
  };

  function createNoiseBurst(startTime, dur, amp, centerFreq = 420, q = 0.8){
    if (!audioCtx || !noiseBuffer) return;

    const src = audioCtx.createBufferSource();
    src.buffer = noiseBuffer;

    const bp = audioCtx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? Math.min(centerFreq, 360) : centerFreq, startTime);
    bp.Q.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? Math.max(0.45, q * 0.65) : q, startTime);

    const lp = audioCtx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 620 : 900, startTime);

    const g = audioCtx.createGain();
    const safeAmp = AUDIO_IS_MOBILE_OR_TABLET ? amp * 0.32 : amp;
    g.gain.setValueAtTime(0.0001, startTime);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, safeAmp), startTime + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, startTime + dur);

    src.connect(bp).connect(lp).connect(g).connect(sonarMaster);
    src.start(startTime);
    src.stop(startTime + dur + 0.02);
  }

  function createDopplerThump(startTime, amp, bpm, secondClick = false, mechanical = false){
    if (!audioCtx || !sonarMaster) return;

    const safeBpm = Math.max(50, Math.min(220, bpm || 140));
    const baseFreq = Math.max(82, Math.min(150, 92 + (safeBpm - 100) * 0.28));
    const dur = secondClick ? 0.105 : 0.13;

    const osc = audioCtx.createOscillator();
    osc.type = 'triangle';

    // Pequena queda de frequência no pulso: dá sensação de "fofo/abafado".
    osc.frequency.setValueAtTime(baseFreq + (secondClick ? 9 : 18), startTime);
    osc.frequency.exponentialRampToValueAtTime(Math.max(65, baseFreq * 0.72), startTime + dur);

    const lp = audioCtx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(
      AUDIO_IS_MOBILE_OR_TABLET ? (secondClick ? 390 : 450) : (secondClick ? 480 : 560),
      startTime
    );
    lp.Q.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 0.45 : 0.65, startTime);

    const g = audioCtx.createGain();
    const thumpAmp = AUDIO_IS_MOBILE_OR_TABLET ? amp * 0.94 : amp;
    g.gain.setValueAtTime(0.0001, startTime);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, thumpAmp), startTime + 0.014);
    g.gain.exponentialRampToValueAtTime(0.0001, startTime + dur);

    osc.connect(lp).connect(g).connect(sonarMaster);
    osc.start(startTime);
    osc.stop(startTime + dur + 0.03);

    createNoiseBurst(startTime + 0.006, dur * 0.9, amp * (mechanical ? 0.045 : 0.18), secondClick ? 360 : 430, 0.7);
  }

  // Ruído de movimento fetal opcional: usado raramente para dar realismo, sem atrapalhar.
  function fetalMovementWhoosh(){
    if (!soundOn || !audioCtx || !noiseBuffer) return;
    const t = audioCtx.currentTime;

    const src = audioCtx.createBufferSource();
    src.buffer = noiseBuffer;

    const bp = audioCtx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 220 : 260, t);
    bp.frequency.exponentialRampToValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 520 : 900, t + 0.38);
    bp.Q.setValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 0.45 : 0.7, t);

    const g = audioCtx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(AUDIO_IS_MOBILE_OR_TABLET ? 0.035 : 0.12, t + 0.05);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.42);

    src.connect(bp).connect(g).connect(sonarMaster);
    src.start(t);
    src.stop(t + 0.46);
  }

  function beep(currentBpm) {
    if (!soundOn || !audioCtx || !sonarMaster) return;

    const bpm = Math.max(50, Math.min(220, currentBpm || state.bpm || 140));
    const t = audioCtx.currentTime;
    const mechanical = !!state.sinusoidalOn;

    // Batimento fetal Doppler: TUM-tum. No sinusoidal ele fica frio, regular e sem whoosh aleatório.
    const firstAmp = AUDIO_IS_MOBILE_OR_TABLET ? (mechanical ? 0.24 : 0.28) : (mechanical ? 0.26 : 0.30);
    const secondAmp = AUDIO_IS_MOBILE_OR_TABLET ? (mechanical ? 0.13 : 0.16) : (mechanical ? 0.15 : 0.18);
    createDopplerThump(t, firstAmp, bpm, false, mechanical);
    createDopplerThump(t + 0.085, secondAmp, bpm, true, mechanical);

    // Interferência discreta ocasional só fora do padrão sinusoidal.
    // No celular/tablet, fica mais rara para reduzir chiado de alto-falante pequeno.
    const whooshChance = AUDIO_IS_MOBILE_OR_TABLET ? 0.0015 : 0.006;
    if (!mechanical && Math.random() < whooshChance) fetalMovementWhoosh();
  }

  // ===== Temporização e geração (BPM, não ECG) =====
  let lastTS = performance.now();

  // Tempo interno da CTG ("tempo do filme").
  // Ele avança conforme a velocidade escolhida. Assim, um evento de 15s ocupa
  // sempre 15s no papel/grade da CTG. Em 10x ele apenas roda 10x mais rápido
  // na vida real, sem ficar mais largo no traçado.
  let ctgNowMs = 0;
  const ctgNow = () => ctgNowMs;

  let rrRemainAudio = 0;                  // ms até o próximo som Doppler
  function resetSonarTiming(){
    // Evita travamento/intervalo longo quando entra/sai de cenários.
    rrRemainAudio = 0;
  }
  function handleSonarBeat(currentBpm, dtReal){
    // O som usa tempo REAL, não o tempo acelerado da CTG.
    // Assim, ao colocar 5x/10x, o traçado acelera, mas o Doppler continua natural.
    if (state.mode === 'asystole') return;
    const bpm = Math.max(30, Math.min(240, currentBpm || state.bpm || 140));
    const beatMs = (bpm > 0) ? (60000 / bpm) : 1e9;

    rrRemainAudio -= dtReal;
    if (rrRemainAudio <= 0){
      beep(bpm);
      // Evita “catch-up” artificial quando a aba perde foco ou há travamento.
      rrRemainAudio = Math.min(beatMs, rrRemainAudio + beatMs);
    }
  }
  let stv = 0;                            // variabilidade curta (random walk)
  const phi = Math.random() * Math.PI*2;  // fase da variabilidade lenta
  let tUc = 0;
  // começa em Basal/Repouso em 10 mmHg, evitando degrau visual
  let ucTone = 10;
  let ucToneTarget = 10;
  let ucToneTimer = 0;

  // último valor renderizado do TOCO (antes do overlay)
// usado para iniciar o pico one-shot do nível atual, sem degrau
let ucLast = 0;

// soft-max para misturar baseline com overlay sem salto
function smoothMax(a, b, k = 10) {
  // k maior = transição mais “dura”; menor = mais suave
const m = Math.max(a, b);
  return (m + Math.log(Math.exp(k*(a-m)) + Math.exp(k*(b-m))) / k);
}

  // Amplitude de variação (metade do pico-a-pico) para o modo normal
  let ampHalf = 7.5;      // metade da variação total atual
  let ampTarget = 7.5;
  let ampTimer = 0;       // ms até escolher novo alvo
  let randomDrift = 0;
  let randomDriftTarget = 0;
  let randomDriftTimer = 0;

  // Eventos de acel/desc (obstétricos)
  const events = [];
  function schedulePattern(p){
    const kind = String(p.pattern||'').toLowerCase();
    if (kind === 'reset') { events.length = 0; return; }
    let depth = Math.max(1, Math.min(100, parseInt(p.depth||30,10)));
    let durMs = Math.max(5, parseInt(p.duration||60,10)) * 1000;
    let sign = (kind === 'accel') ? +1 : -1;

    const period = 90000; // ~90s
    const now = ctgNow();
    const nextPeak = now + (period - (tUc % period));
    let start = now;
    if (kind === 'early')      start = nextPeak - durMs*0.5;
    else if (kind === 'late')  start = nextPeak + durMs*0.3;
    else if (kind === 'prolonged') durMs = Math.max(durMs, 120000);

    events.push({ kind, start, durMs, depth, sign });
  }

  
  function fhrOffset(nowMs){
  let off = 0;
  let skipClamp = false;

  for (let i = events.length - 1; i >= 0; i--){
    const e = events[i];
    const t = (nowMs - e.start);
    if (t < 0) continue;
    if (t > e.durMs){ events.splice(i, 1); continue; }

    const x = t / e.durMs; // 0..1

    if (e.kind === 'decel_sync'){
      // DIPI sincronizada: trapézio arredondado + leve oscilação
      const env    = trapezoid01(x, e.riseFrac ?? 0.20, e.fallFrac ?? 0.20);
      const base   = state.fhr_base || state.bpm || 140;
      const target = e.target ?? 55;
      const delta  = target - base;                         // negativo (queda)
      const ripple = 0.10 * delta * Math.sin(x * Math.PI * 4);
      off += delta * env + ripple;
      if (e.skipClamp) skipClamp = true;

    } else if (e.kind === 'dipi_precoce'){
      // compat: versão antiga
      const env = trapezoid01(x, 0.20, 0.20);
      off += -1 * (e.depth || 90) * env;

    } else if (e.kind === 'variable'){
      // variável (exemplo)
      let shape;
      if (x < 0.2)      shape = 1 - (x / 0.2);
      else if (x < 0.4) shape = 0;
      else              shape = 1 - ((x - 0.4) / 0.6);
      off += -1 * (e.depth || 30) * shape;

    } else if (e.kind === 'fhr_keyframes'){
      off += keyframeOffset(e.points, t / 1000, e.smooth !== false);
      if (e.skipClamp) skipClamp = true;

    } else if (e.kind === 'decel_v'){
      // Perfil em V até 'target'. Na tardia, usamos uma forma assimétrica:
      // desce um pouco mais rápido e retorna mais devagar.
      const base   = state.fhr_base || state.bpm || 140;
      const target = e.target ?? 100;
      const delta  = target - base;             // negativo
      const env    = (e.shape === 'late_check') ? asymVShape01(x, e.nadirFrac ?? 0.40) : vshape01(x);
      const ripple = (e.rippleScale ?? 0.08) * delta * Math.sin(x * Math.PI * 6);
      off += delta * env + ripple;
      if (e.skipClamp) skipClamp = true;

    } else if (e.kind === 'accel_transitoria') {
      // Aceleração transitória: sobe +18 bpm, com pequena variação de ±2 bpm,
      // e retorna ao basal no fim do evento.
      const env = trapezoid01(x, 0.20, 0.20);
      const rise = e.rise ?? 18;
      const ripple = (e.ripple ?? 2) * Math.sin(x * Math.PI * 6);
      off += (rise + ripple) * env;
      if (e.skipClamp) skipClamp = true;

    } else {
      // fallback semicosseno (acel/desc simples)
      const shape = Math.sin(Math.PI * x);
      const sign  = (e.sign != null ? e.sign : -1);
      off += sign * (e.depth || 30) * shape;
    }
  }
  return { off, skipClamp };
}

  // Conversor BPM -> Y
  function bpmToY(bpm, h){
    const min=30, max=240;
    const v = Math.max(min, Math.min(max, bpm));
    return Math.round((1 - (v-min)/(max-min)) * (h - 1));
  }

  // Gera BPM efetivo com variabilidade — var_min/var_max são amplitude TOTAL.
  // Ex.: var_max=20 significa cerca de 10 bpm para baixo e 10 bpm para cima.
  function sampleFHR(dt, nowMs){
    const mode = state.mode;

    if (mode === 'asystole') return { bpm: 0, beat: false };

    if (state.hipersistoliaOn) {
      const hyperBpm = Math.max(0, Math.min(240, hipersistoliaFHRValue(dt, nowMs)));
      return { bpm: hyperBpm, beat: false };
    }

    let base, ltv, stepSize, stvLimit, bpmEff;

    if (mode === 'normal'){
      // Transição suave do baseline fetal: evita “degrau” quando enviar novo baseline.
      const targetBase = (typeof state.fhr_base_target === 'number') ? state.fhr_base_target : state.fhr_base;
      const baseK = Math.min(1, dt / 6500);
      state.fhr_base = state.fhr_base + (targetBase - state.fhr_base) * baseK;
      if (Math.abs(targetBase - state.fhr_base) < 0.1) state.fhr_base = targetBase;
      base = state.fhr_base;

      const ev = fhrOffset(nowMs);

      if (state.sinusoidalOn) {
        // Sem variabilidade basal: senoide pura + eventos que ainda estejam ativos.
        bpmEff = base + sinusoidalOffset(nowMs) + ev.off;
      } else {
        // Atualiza alvo de amplitude total e converte para metade para desenhar acima/abaixo.
        ampTimer -= dt;
        if (ampTimer <= 0){
          const a = state.var_min, b = state.var_max;
          const lo = Math.min(a,b), hi = Math.max(a,b);
          const totalTarget = lo + Math.random()*(hi - lo);
          ampTarget = totalTarget / 2;
          ampTimer  = 2500 + Math.random()*6500; // troca irregular para ficar menos “padronizado”
        }
        const kAmp = Math.min(1, dt / 1800);
        ampHalf = ampHalf + (ampTarget - ampHalf) * kAmp;

        // Variabilidade mais aleatorizada: menos senoidal pura e mais drift/jitter.
        // Mesmo com variação total = 0, mantemos uma micro-oscilação visual discreta,
        // simulando ruído mecânico do transdutor, movimento materno e artefatos de captação.
        const noiseFloor = 0.65; // bpm: pequeno o bastante para não parecer variabilidade real
        const activeNoiseAmp = Math.max(ampHalf, noiseFloor);

        randomDriftTimer -= dt;
        if (randomDriftTimer <= 0){
          randomDriftTarget = (Math.random()*2 - 1) * (ampHalf > 0 ? 0.55 * ampHalf : 0.22);
          randomDriftTimer = 300 + Math.random()*1200;
        }
        randomDrift += (randomDriftTarget - randomDrift) * Math.min(1, dt / 650);

        ltv =
          0.25*ampHalf*Math.sin(nowMs/13000 + phi) +
          0.18*ampHalf*Math.sin(nowMs/5100 + 1.7*phi) +
          0.10*ampHalf*Math.sin(nowMs/2300 + 0.4*phi);

        stepSize = 0.32*activeNoiseAmp;
        stv += (Math.random() - 0.5) * stepSize;
        stv *= 0.92;
        stvLimit = Math.max(0.38, 0.65*ampHalf);
        if (stv >  stvLimit) stv =  stvLimit;
        if (stv < -stvLimit) stv = -stvLimit;

        const microJitter = (Math.random() - 0.5) * (ampHalf > 0 ? 0.35 * ampHalf : 0.55);
        const captureNoise = 0.18 * Math.sin(nowMs / 173 + 0.3*phi) + 0.10 * Math.sin(nowMs / 89 + phi);
        bpmEff = base + ltv + stv + randomDrift + microJitter + captureNoise + ev.off;

        // só aplica o “aperto” da variação total se não houver evento profundo.
        // Quando ampHalf=0, permite apenas o ruído de captação mínimo.
        if (!ev.skipClamp) {
          const clampHalf = Math.max(ampHalf, 0.85);
          bpmEff = Math.max(base - clampHalf, Math.min(base + clampHalf, bpmEff));
        }
      }

      bpmEff = Math.max(0, Math.min(240, bpmEff));

    } else {
      // modos basais antigos (tachy/brady)
      base = state.bpm;
      if (mode === 'tachy') base = Math.max(base, 160);
      if (mode === 'brady') base = Math.min(base, 100);

      ltv = 6*Math.sin(nowMs/15000 + phi) + 3*Math.sin(nowMs/7000 + 1.7*phi);
      stv += (Math.random()-0.5) * 0.9;
      if (stv > 8) stv = 8; if (stv < -8) stv = -8;

      const ev = fhrOffset(nowMs);
      bpmEff = base + ltv + stv + ev.off;
      bpmEff = Math.max(0, Math.min(240, bpmEff));
    }

    // O som Doppler é controlado separadamente pelo tempo real no loop().
    return { bpm: bpmEff, beat: false };
  }

function sampleUC(dt, nowMs){
  if (state.uc_paused) return 0;
  tUc += dt;

  if (state.hipersistoliaOn) {
    const value = Math.max(0, Math.min(100, hipersistoliaUCValue(nowMs)));
    ucLast = value;
    return value;
  }

  // ---- TÔNUS BASAL (transição suave, sem degrau) ----
  const loTone = Math.max(0, Math.min(state.uc_tone_min, state.uc_tone_max));
  const hiTone = Math.max(loTone, Math.max(state.uc_tone_min, state.uc_tone_max));

  if (loTone !== hiTone) {
    // Quando existir faixa de tônus, o alvo varia lentamente dentro dela.
    ucToneTimer -= dt;
    if (ucToneTimer <= 0){
      ucToneTarget = loTone + Math.random() * (hiTone - loTone);
      ucToneTimer  = 8000 + Math.random() * 8000;
    }
  } else {
    // Quando for tônus fixo, inclusive 0, só muda o alvo.
    ucToneTarget = loTone;
    ucToneTimer = 1000000000;
  }

  const toneK = Math.min(1, dt / 4500); // divisor maior = transição um pouco mais lenta
  ucTone = ucTone + (ucToneTarget - ucTone) * toneK;
  if (Math.abs(ucToneTarget - ucTone) < 0.05) ucTone = ucToneTarget;

  // ---- CONTRAÇÃO PERIÓDICA (envelope gaussiano) ----
  const amp = Math.max(0, state.uc_level|0);
  let base = 0;
  if (amp > 0){
    const period = Math.max(1000, state.uc_pattern.period_ms|0);
    const dur    = Math.max(1000, state.uc_pattern.dur_ms|0);
    const phase  = (tUc % period) / period;
    const sigma  = dur / 2.5;
    const t      = phase * period;
    const mu     = period / 2;
    const envelope = Math.exp( - Math.pow(t - mu, 2) / (2 * Math.pow(sigma, 2)) );
    base = envelope * amp;
  }

  // ---- Baseline (tônus + contração) ----
  const baselineTotal = ucTone + base;

  // ---- Overlays one-shot (DIPI precoce etc.) — sem degrau ----
  let overlayAbs = baselineTotal;
  const now = nowMs;

  for (let i = uc_events.length - 1; i >= 0; i--){
    const e = uc_events[i];
    const t = now - e.start;
    if (t < 0) continue;
    if (t > e.durMs){ uc_events.splice(i,1); continue; }

    if (e.startFrom == null) e.startFrom = baselineTotal;

    const x = t / e.durMs;
    let env;
    if (e.shape === 'hann')      env = hann01(x);
    else if (e.shape === 'gauss') env = gauss01(x, e.sigma ?? 0.22);
    else                          env = trapezoid01(x, 0.20, 0.20);

    const target    = Math.max(0, Math.min(100, e.peak)); // p.ex. 80
    const candidate = e.startFrom + env * (target - e.startFrom);

    if (candidate > overlayAbs) overlayAbs = candidate;
  }

  // ---- Resultado final ----
  // Sem ruído basal: tônus fixo realmente permanece fixo.
  let value = overlayAbs;
  value = Math.max(0, Math.min(100, value));
  ucLast = value;
  return value;
}

  // ===== Socket =====
socket.on('connect', ()=> connEl.textContent = 'conectado');
socket.on('disconnect', ()=> connEl.textContent = 'desconectado');

socket.on('command', (p)=>{
  if (!p) { applyHud(); return; }

  if (!tryStartObstEvent(p)) {
    applyHud();
    return;
  }

  if (p.mode === 'uc_level' && typeof p.uc === 'number') {
    state.uc_level = Math.max(0, Math.min(100, p.uc));

  } else if (p.mode === 'uc_pattern') {
    const per = parseInt(p.period_ms || 0, 10);
    const dur = parseInt(p.dur_ms    || 0, 10);
    if (per > 0) state.uc_pattern.period_ms = per;
    if (dur > 0) state.uc_pattern.dur_ms    = dur;

    if (typeof p.uc_amp === 'number') {
      state.uc_level = Math.max(0, Math.min(100, p.uc_amp));
    }

    if (typeof p.tone_min === 'number' || typeof p.tone_max === 'number') {
      const tmin = Math.max(0, Math.min(100, parseInt(p.tone_min ?? state.uc_tone_min, 10)));
      const tmax = Math.max(0, Math.min(100, parseInt(p.tone_max ?? state.uc_tone_max, 10)));
      state.uc_tone_min = Math.min(tmin, tmax);
      state.uc_tone_max = Math.max(tmin, tmax);
      state.preferredTocoTone = Math.round((state.uc_tone_min + state.uc_tone_max) / 2);
      // Ajusta apenas o alvo do tônus; a linha chega nele suavemente em sampleUC().
      ucToneTarget = (state.uc_tone_min + state.uc_tone_max) / 2;
      ucToneTimer = 0;
    }

  } else if (p.mode === 'uc_pause') {
    state.uc_paused = !state.uc_paused;

  } else if (p.mode === 'toco_tone') {
    const tone = Math.max(0, Math.min(100, parseInt(p.tone ?? 10, 10)));
    rememberAndSetTocoTone(tone);

  } else if (p.mode === 'toco_single') {
    const peak = Math.max(0, Math.min(100, parseInt(p.peak ?? 50, 10)));
    const dur  = Math.max(5, Math.min(70, parseInt(p.duration_sec ?? 50, 10)));
    configureTocoContractionsFromCurrentTone(peak, dur, 1, 150000);

  } else if (p.mode === 'toco_normal') {
    const tone = Math.max(0, Math.min(100, parseInt(p.tone ?? 10, 10)));
    const peak = Math.max(0, Math.min(100, parseInt(p.peak ?? 50, 10)));
    const dur  = Math.max(5, Math.min(70, parseInt(p.duration_sec ?? 50, 10)));
    const count = Math.max(1, Math.min(10, parseInt(p.count ?? 4, 10)));
    const windowMs = Math.max(1000, parseInt(p.window_ms ?? 600000, 10));
    const periodMs = Math.round(windowMs / count);
    configureTocoContractions(tone, peak, dur, count, periodMs);

      } else if (p.mode === 'dipi_precoce_verdadeira') {
    const total  = Math.max(40, (typeof p.fhr_total_sec === 'number') ? p.fhr_total_sec : 40);
    const target = (typeof p.fhr_target === 'number')    ? p.fhr_target    : 100;

    const ucDur  = (typeof p.uc_duration_sec === 'number') ? p.uc_duration_sec : 60;
    const ucPeak = (typeof p.uc_peak === 'number')         ? p.uc_peak         : 50;
    const delay  = (typeof p.fhr_delay_sec === 'number')
      ? p.fhr_delay_sec
      : Math.max(0, (ucDur / 2) - (total / 2));

    // TOCO: inicia agora, dura 60s; pico no meio coincide com o vale do FHR
    scheduleUCOneShot(ucPeak, Math.max(1000, ucDur * 1000), 0.22);

    // FHR: forma em V por pelo menos 40s
    scheduleDecelV(delay, total, target);

  } else if (p.mode === 'dip_tardia') {
    const fallSec = (typeof p.late_fall_sec === 'number') ? Math.max(1, p.late_fall_sec) : 30;
    const returnSec = (typeof p.late_return_sec === 'number') ? Math.max(1, p.late_return_sec) : 60;
    const total = fallSec + returnSec; // queda 30s + retorno 60s = 90s
    const target = (typeof p.fhr_target === 'number')    ? p.fhr_target    : 100;

    const ucDur  = (typeof p.uc_duration_sec === 'number') ? p.uc_duration_sec : 60;
    const ucPeak = (typeof p.uc_peak === 'number')         ? p.uc_peak         : 50;
    const lateNadirAfterPeak = (typeof p.late_nadir_after_peak_sec === 'number') ? p.late_nadir_after_peak_sec : 40;
    const nadirFrac = fallSec / total; // nadir ocorre após 30s de queda
    const ucPeakAt = ucDur / 2;
    const delay = (typeof p.fhr_delay_sec === 'number')
      ? p.fhr_delay_sec
      : Math.max(0, ucPeakAt + lateNadirAfterPeak - fallSec);

    // TOCO: pico no meio da onda de 60s
    scheduleUCOneShot(ucPeak, Math.max(1000, ucDur * 1000), 0.22);

    // DIP tardia: começa a cair, leva 30s até o nadir; depois retorna em 60s.
    // Mantém o nadir 40s após o pico da TOCO.
    scheduleDecelV(delay, total, target, { shape:'late_check', nadirFrac, rippleScale:0.04 });

  } else if (p.mode === 'acel_transitoria') {
    const dur = (typeof p.duration === 'number') ? p.duration : 20;
    const rise = (typeof p.rise === 'number') ? p.rise : 16;
    const ripple = (typeof p.ripple === 'number') ? p.ripple : 0;

    events.push({
      kind: 'accel_transitoria',
      start: ctgNow(),
      durMs: Math.max(1000, dur * 1000),
      rise: Math.max(1, Math.min(60, rise)),
      ripple: Math.max(0, Math.min(10, ripple)),
      skipClamp: true
    });

  } else if (p.mode === 'sinusoidal_toggle') {
    resetSonarTiming();
    stv = 0;
    randomDrift = 0;
    randomDriftTarget = 0;
    const tone = Math.max(0, Math.min(100, parseInt(p.tone ?? state.preferredTocoTone ?? 10, 10)));
    state.preferredTocoTone = tone;
    state.hipersistoliaOn = false;
    if (state.sinusoidalOn) {
      state.sinusoidalOn = false;
      setStaticTocoTone(state.preferredTocoTone);
    } else {
      clearTimedEvents();
      setStaticTocoTone(state.preferredTocoTone);
      state.sinusoidalOn = true;
      state.sinusoidalStartMs = ctgNow();
      state.mode = 'normal';
    }

  } else if (p.mode === 'hipersistolia_toggle') {
    resetSonarTiming();
    stv = 0;
    randomDrift = 0;
    randomDriftTarget = 0;
    const tone = Math.max(0, Math.min(100, parseInt(p.tone ?? state.preferredTocoTone ?? 10, 10)));

    if (state.hipersistoliaOn) {
      // Desliga e volta ao tônus basal que estava setado na tela de controle.
      clearTimedEvents();
      state.hipersistoliaOn = false;
      state.sinusoidalOn = false;
      state.mode = 'normal';
      state.fhr_base = 140;
      state.fhr_base_target = 140;
      state.bpm = 140;
      state.var_min = 5;
      state.var_max = 25;
      state.preferredTocoTone = tone;
      setStaticTocoTone(tone);
      state.uc_level = 0;
    } else {
      // Liga a cascata de hipersistolia, preservando o tônus basal escolhido para restaurar ao desligar.
      clearTimedEvents();
      state.preferredTocoTone = tone;
      state.sinusoidalOn = false;
      state.hipersistoliaOn = true;
      state.hipersistoliaStartMs = ctgNow();
      state.mode = 'normal';
      state.fhr_base = 140;
      state.fhr_base_target = 140;
      state.bpm = 140;
      state.var_min = 5;
      state.var_max = 25;
      setStaticTocoTone(HYPER_UC_TONE);
      state.uc_level = 0;
    }

  } else if (p.mode === 'pattern') {
    schedulePattern(p);

  } else if (p.mode === 'reset') {
    clearTimedEvents();
    laborAuto.enabled = false;
    state.uc_level = 0;
    state.sinusoidalOn = false;
    state.hipersistoliaOn = false;
    const resetTone = Math.max(0, Math.min(100, parseInt(p.tone ?? state.preferredTocoTone ?? 10, 10)));
    state.preferredTocoTone = resetTone;
    setStaticTocoTone(resetTone);
    resetSonarTiming();

  } else if (p.mode === 'band') {
    state.showBand = !!p.show;
    buildGrids();

  } else if (p.mode === 'set_baseline') {
    const base = Math.max(0, Math.min(240, parseInt(p.bpm||140,10)));
    // Não altera a linha de uma vez. Define o alvo e o sampleFHR() aproxima suavemente.
    state.fhr_base_target = base;
    state.bpm = base;

  } else if (p.mode === 'set_var') {
    let vmin = Math.max(0, Math.min(80, parseInt((p.vmin ?? 0),10)));
    let vmax = Math.max(0, Math.min(80, parseInt((p.vmax ?? 0),10)));
    if (vmin > vmax) { const t=vmin; vmin=vmax; vmax=t; }
    state.var_min = vmin;
    state.var_max = vmax;
    ampTarget = (vmin + Math.random()*(vmax - vmin)) / 2;

  } else if (p.mode === 'time_scale') {
    const f = parseFloat(p.factor);
    if (!isNaN(f)) state.timeScale = Math.max(0.05, Math.min(20.0, f));

  } else if (p.mode === 'labor_auto') {
    laborAuto.enabled  = !!p.enabled;
    laborAuto.max      = (p.max_contr ?? 4) | 0;
    laborAuto.windowMs = (p.window_ms ?? 600000) | 0;
    laborAuto.period   = (p.period_ms ?? laborAuto.period) | 0;
    laborAuto.count = 0;
    laborAuto.startMs = 0;
    laborAuto.lastPhase = 0;

} else if ([
  'dip_variavel_v_contracao',
  'dip_variavel_v_sem_contracao',
  'dip_variavel_u_contracao',
  'dip_variavel_u_sem_contracao',
  'dip_variavel_w_contracao',
  'dip_variavel_w_sem_contracao'
].includes(p.mode)) {
  scheduleVariableDip(p.mode);

} else if (p.mode === 'dip_variavel' || p.mode === 'dipi_precoce') {
  const durSec = Math.max(40, (typeof p.duration === 'number') ? p.duration : 40);
  const target = (typeof p.fhr_target === 'number') ? p.fhr_target : 100;
  const ucDurSec = (typeof p.uc_duration_sec === 'number') ? p.uc_duration_sec : 60;

  // DIP variável: FHR dura pelo menos 40s e o nadir coincide com o pico da contração de 60s.
  const delaySec = Math.max(0, (ucDurSec - durSec) / 2);
  scheduleDecelV(delaySec, durSec, target);

 // TOCO: onda de desaceleração com duração fixa de 60s
const peak = (typeof p.uc_peak === 'number') ? p.uc_peak : 50;
scheduleUCOneShot(peak, Math.max(1000, ucDurSec * 1000), 0.22);

  // (opcional) manter tônus basal, se vier no payload
  if (typeof p.tone_min === 'number' || typeof p.tone_max === 'number') {
    const tmin = Math.max(0, Math.min(100, parseInt(p.tone_min ?? state.uc_tone_min, 10)));
    const tmax = Math.max(0, Math.min(100, parseInt(p.tone_max ?? state.uc_tone_max, 10)));
    state.uc_tone_min = Math.min(tmin, tmax);
    state.uc_tone_max = Math.max(tmin, tmax);
    // Ajusta apenas o alvo do tônus; a linha chega nele suavemente em sampleUC().
    ucToneTarget = (state.uc_tone_min + state.uc_tone_max) / 2;
    ucToneTimer = 0;
  }

  } else {
    // modos basais etc.
    if (p.mode) {
      state.mode = p.mode;
      if (p.mode === 'normal') { state.sinusoidalOn = false; state.hipersistoliaOn = false; resetSonarTiming(); }
    }
    if (typeof p.bpm === 'number') state.bpm = Math.max(0, Math.min(240, p.bpm));
  }

  applyHud();
});

  function applyHud(){
    const shownMode = state.hipersistoliaOn ? 'hipersistolia' : (state.sinusoidalOn ? 'sinusoidal' : state.mode);
    modeEl.textContent  = shownMode;
    modeTag.textContent = shownMode;
    bpmEl.textContent   = state.bpm;
    bpmBig.textContent  = state.bpm;
    const shownUC = (typeof ucTone === 'number') ? Math.round(ucTone) : state.uc_level;
    ucEl.textContent    = shownUC;
    ucBig.textContent   = shownUC;
  }

// ===== Loop (grid fixo + cursor ESQ→DIR) =====
// O fator de velocidade (timeScale) acelera/desacelera o "filme" inteiro.
// Eventos, TOCO, FHR e cursor usam o mesmo tempo CTG. Assim, 15s de evento
// ocupam sempre 15s na grade; em 10x apenas passam 10x mais rápido na vida real.
let pxCarryHR = 0; // acumulador de pixels FHR
let pxCarryUC = 0; // acumulador de pixels TOCO

function loop(ts){
  const dtReal = Math.min(32, ts - lastTS);
  lastTS = ts;

  // fator do filme/CTG
  const k = state.timeScale || 1.0;
  const dtCTG = dtReal * k;
  ctgNowMs += dtCTG;

  // ---------- FHR ----------
  const w1 = hr.width, h1 = hr.height;

  // avanço horizontal visual proporcional ao tempo CTG
  pxCarryHR += (dtCTG * pxPerMs);
  let advHR = Math.floor(pxCarryHR);
  if (advHR < 1) advHR = 0;
  pxCarryHR -= advHR;

  // amostra do sinal com o mesmo tempo CTG usado pela rolagem
  const s = sampleFHR(dtCTG, ctgNowMs);
  const yNew = bpmToY(s.bpm, h1);

  if (advHR > 0){
    hrx.clearRect(xHR, 0, advHR, h1);
    hrx.drawImage(gridHR, xHR, 0, advHR, h1, xHR, 0, advHR, h1);

    const xNew = (xHR + advHR) % w1;
    hrx.strokeStyle = (state.mode==='asystole') ? "#00ff88" : "#ff4dc4";
    hrx.lineWidth = 2;
    hrx.beginPath();
    if (xNew < xHR) {
      hrx.moveTo(xNew, yNew);
    } else {
      hrx.moveTo(prevXhr, prevYhr);
      hrx.lineTo(xNew, yNew);
    }
    hrx.stroke();

    prevXhr = xNew; prevYhr = yNew;
    xHR = xNew;
  }
  handleSonarBeat(s.bpm, dtReal);

// ---------- TOCO ----------
const w2 = ucC.width, h2 = ucC.height;

// avanço horizontal visual (scroll) IGUAL ao FHR (baseado no tempo CTG)
pxCarryUC += (dtCTG * pxPerMs);
let advUC = Math.floor(pxCarryUC);
if (advUC < 1) advUC = 0;
pxCarryUC -= advUC;

// TOCO também usa o mesmo tempo CTG usado pela rolagem
const valUC = sampleUC(dtCTG, ctgNowMs);
const yUC   = Math.round((1 - (valUC/100)) * (h2 - 1));

  // --- Auto-retorno ao basal após 4 contrações em ≤10min ---
const periodNow = Math.max(1000, (state.uc_pattern.period_ms | 0));
const phaseNow  = (tUc % periodNow) / periodNow;

if (laborAuto.enabled) {
  const prev = laborAuto.lastPhase || 0;

  // cruzou de ~fim (>=95%) para ~início (<=5%) => nova contração
  if (prev > 0.95 && phaseNow < 0.05) {
    const nowMs = ctgNowMs;

    if (laborAuto.count === 0) laborAuto.startMs = nowMs;
    laborAuto.count += 1;

    // se estourou a janela, reinicia contagem a partir desta contração
    if ((nowMs - laborAuto.startMs) > laborAuto.windowMs) {
      laborAuto.count = 1;
      laborAuto.startMs = nowMs;
    }

    // atingiu a meta dentro da janela? retorna ao basal
    if (laborAuto.count >= laborAuto.max &&
        (nowMs - laborAuto.startMs) <= laborAuto.windowMs) {
      socket.emit('command', { mode: 'apply_preset', name: 'normal' });
      laborAuto.enabled = false; // desarma localmente
    }
  }
  laborAuto.lastPhase = phaseNow;
}

  if (advUC > 0){
    ucx.clearRect(xUC, 0, advUC, h2);
    ucx.drawImage(gridUC, xUC, 0, advUC, h2, xUC, 0, advUC, h2);

    const xNewUC = (xUC + advUC) % w2;
    ucx.strokeStyle = "#20d37b";
    ucx.lineWidth = 2;
    ucx.beginPath();
    if (xNewUC < xUC) {
      ucx.moveTo(xNewUC, yUC);
    } else {
      ucx.moveTo(prevXuc, prevYuc);
      ucx.lineTo(xNewUC, yUC);
    }
    ucx.stroke();

    prevXuc = xNewUC; prevYuc = yUC;
    xUC = xNewUC;
  }

  // HUD
  const shownModeLoop = state.hipersistoliaOn ? 'hipersistolia' : (state.sinusoidalOn ? 'sinusoidal' : state.mode);
  modeEl.textContent = shownModeLoop;
  modeTag.textContent = shownModeLoop;
  bpmEl.textContent  = Math.round(s.bpm);
  bpmBig.textContent = Math.round(s.bpm);
  ucEl.textContent   = Math.round(valUC);
  ucBig.textContent  = Math.round(valUC);
  clockEl.textContent = new Date().toLocaleTimeString();

  requestAnimationFrame(loop);
}

  // ===== Start =====
  applyHud();
  buildGrids();
  requestAnimationFrame(loop);
</script>
</body>
</html>
"""

# ===================== ROTAS FLASK =====================
@app.route("/")
def index():
    room_id = secrets.token_urlsafe(5)
    return redirect(url_for("session_home", room_id=room_id))

@app.route("/s/<room_id>")
def session_home(room_id):
    control_url = request.url_root.rstrip("/") + url_for("control_room", room_id=room_id)
    monitor_url = request.url_root.rstrip("/") + url_for("monitor_room", room_id=room_id)
    return render_template_string(
        HOME_HTML,
        room_id=room_id,
        control_url=control_url,
        monitor_url=monitor_url,
    )

@app.route("/s/<room_id>/control")
def control_room(room_id):
    return render_template_string(CONTROL_HTML, room_id=room_id)

@app.route("/s/<room_id>/monitor")
def monitor_room(room_id):
    return render_template_string(MONITOR_HTML, room_id=room_id)

# Rotas antigas: mantidas para não quebrar o link, mas agora criam uma sessão nova.
@app.route("/control")
def control_legacy():
    room_id = secrets.token_urlsafe(5)
    return redirect(url_for("control_room", room_id=room_id))

@app.route("/monitor")
def monitor_legacy():
    room_id = secrets.token_urlsafe(5)
    return redirect(url_for("monitor_room", room_id=room_id))

# ===================== SOCKET.IO ======================

socket_rooms = {}

@socketio.on("connect")
def on_connect():
    room_id = request.args.get("room") or "global"
    socket_rooms[request.sid] = room_id
    join_room(room_id)
    emit("joined", {"room": room_id})

@socketio.on("disconnect")
def on_disconnect():
    socket_rooms.pop(request.sid, None)

def emit_command_to_room(command):
    room_id = socket_rooms.get(request.sid, "global")
    socketio.emit("command", command, to=room_id)

@socketio.on("command")
def on_command(payload):
    mode = payload.get("mode")
    bpm  = payload.get("bpm")
    uc   = payload.get("uc")

    # ----- Ritmos basais -----
    if mode in {"normal","tachy","brady","afib","asystole"}:
        clean = {"mode": mode}
        if isinstance(bpm, (int, float)):
            clean["bpm"] = max(40, min(240, int(bpm)))
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Contrações -----
    if mode == "uc_level" and isinstance(uc, (int, float)):
        clean = {"mode": "uc_level", "uc": max(0, min(100, int(uc)))}
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    if mode == "uc_pause":
        emit_command_to_room({"mode": "uc_pause"})
        emit("ack", {"ok": True, "echo": {"mode": "uc_pause"}})
        return

    # ----- TOCO tônus basal: comando separado, sem contração -----
    if mode == "toco_tone":
        try:
            tone_raw = payload.get("tone", 10)
            tone = int(10 if tone_raw is None or tone_raw == "" else tone_raw)
        except Exception:
            emit("ack", {"ok": False, "error": "tônus basal da TOCO inválido"})
            return

        clean = {
            "mode": "toco_tone",
            "tone": max(0, min(100, tone)),
        }
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- TOCO manual: uma contração configurada, usando o tônus basal atual -----
    if mode == "toco_single":
        try:
            peak = int(payload.get("peak", 50) or 50)
            duration_sec = int(payload.get("duration_sec", 50) or 50)
        except Exception:
            emit("ack", {"ok": False, "error": "comando TOCO inválido"})
            return

        clean = {
            "mode": "toco_single",
            "peak": max(0, min(100, peak)),
            "duration_sec": max(5, min(70, duration_sec)),
        }
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- TOCO normal: 4 contrações em 10 min e depois encerra -----
    if mode == "toco_normal":
        clean = {
            "mode": "toco_normal",
            "tone": 10,
            "peak": 50,
            "duration_sec": 60,
            "count": 4,
            "window_ms": 600000,
        }
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Faixa 110–160 -----
    if mode == "band":
        show = bool(payload.get("show"))
        clean = {"mode": "band", "show": show}
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Ajuste baseline -----
    if mode == "set_baseline":
        try:
            base = int(payload.get("bpm", 140) or 140)
        except Exception:
            emit("ack", {"ok": False, "error": "baseline inválida"})
        else:
            base = max(0, min(240, base))
            clean = {"mode": "set_baseline", "bpm": base}
            emit_command_to_room(clean)
            emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Ajuste variação -----
    if mode == "set_var":
        try:
            vmin = int(payload.get("vmin", 0))
            vmax = int(payload.get("vmax", 0))
        except Exception:
            emit("ack", {"ok": False, "error": "vmin/vmax inválidos"})
        else:
            vmin = max(0, min(80, vmin))
            vmax = max(0, min(80, vmax))
            if vmin > vmax: vmin, vmax = vmax, vmin
            clean = {"mode": "set_var", "vmin": vmin, "vmax": vmax}
            emit_command_to_room(clean)
            emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Padrões obstétricos (eventos FHR) -----
    if mode == "pattern":
        pattern  = str(payload.get("pattern", "")).lower()
        depth    = int(payload.get("depth", 30) or 30)
        duration = int(payload.get("duration", 60) or 60)
        clean = {"mode": "pattern", "pattern": pattern, "depth": depth, "duration": duration}
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Limpar eventos -----
    if mode == "reset":
        try:
            tone_raw = payload.get("tone", None)
            tone = None if tone_raw is None or tone_raw == "" else max(0, min(100, int(tone_raw)))
        except Exception:
            tone = None
        clean = {"mode": "reset"}
        if tone is not None:
            clean["tone"] = tone
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Padrão sinusoidal: liga/desliga no monitor -----
    if mode == "sinusoidal_toggle":
        try:
            tone_raw = payload.get("tone", None)
            tone = None if tone_raw is None or tone_raw == "" else max(0, min(100, int(tone_raw)))
        except Exception:
            tone = None
        clean = {"mode": "sinusoidal_toggle"}
        if tone is not None:
            clean["tone"] = tone
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Hipersistolia: liga/desliga no monitor -----
    if mode == "hipersistolia_toggle":
        try:
            tone_raw = payload.get("tone", None)
            tone = None if tone_raw is None or tone_raw == "" else max(0, min(100, int(tone_raw)))
        except Exception:
            tone = None
        clean = {"mode": "hipersistolia_toggle"}
        if tone is not None:
            clean["tone"] = tone
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ===== Presets atômicos =====
    if mode == "apply_preset":
        name = str(payload.get("name", "")).lower()

        if name == "normal":
            base, vmin, vmax, uc0 = 140, 5, 25, 0
            tone_min, tone_max = 10, 10

            emit_command_to_room({"mode": "reset", "tone": tone_min})
            emit_command_to_room({"mode": "set_baseline", "bpm": base})
            emit_command_to_room({"mode": "set_var", "vmin": vmin, "vmax": vmax})

            # Sem contração periódica (UC=0)…
            emit_command_to_room({"mode": "uc_level", "uc": uc0})
            # …mas com tônus basal fixo em 10 mmHg:
            emit_command_to_room({
            "mode": "uc_pattern",
            "period_ms": 150000,   # irrelevante com UC=0, mas mantido por compat.
            "dur_ms": 13000,
            "tone_min": tone_min,
            "tone_max": tone_max
              })

            emit_command_to_room({"mode": "normal"})
            # <-- DESARMA qualquer contador de trabalho de parto ativo no monitor
            emit_command_to_room({"mode": "labor_auto", "enabled": False})

            emit("ack", {"ok": True, "echo": {
             "mode": "apply_preset", "name": "normal",
             "bpm": base, "vmin": vmin, "vmax": vmax,
             "uc": uc0, "uc_tone_min": tone_min, "uc_tone_max": tone_max
               }})
            return

        elif name == "labor" or name.startswith("labor_"):
            try:
                contractions = 4 if name == "labor" else int(name.split("_", 1)[1])
            except Exception:
                contractions = 4
            contractions = max(1, min(5, contractions))

            # n/10min => período = 10 minutos / n; duração 60s; pico 50 mmHg
            base, vmin, vmax = 140, 5, 25
            period_ms = int(round(600000 / contractions))
            dur_ms, uc_amp = 60000, 50

            try:
                tone_raw = payload.get("tone", 10)
                tone = int(10 if tone_raw is None or tone_raw == "" else tone_raw)
            except Exception:
                tone = 10
            tone = max(0, min(100, tone))
            tone_min, tone_max = tone, tone

            emit_command_to_room({"mode": "reset", "tone": tone_min})
            emit_command_to_room({"mode": "set_baseline", "bpm": base})
            emit_command_to_room({"mode": "set_var", "vmin": vmin, "vmax": vmax})
            emit_command_to_room({"mode": "normal"})
            # Agenda as contrações como ondas individuais, começando do basal.
            # Isso evita que a primeira onda nasça no meio da fase periódica e forme degrau.
            emit_command_to_room({
                "mode": "toco_normal",
                "tone": tone_min,
                "peak": uc_amp,
                "duration_sec": int(dur_ms / 1000),
                "count": contractions,
                "window_ms": 600000
            })
            emit_command_to_room({"mode": "labor_auto", "enabled": False})

            emit("ack", {"ok": True, "echo": {
                "mode": "apply_preset", "name": f"labor_{contractions}",
                "bpm": base, "vmin": vmin, "vmax": vmax,
                "uc_amp": uc_amp, "period_ms": period_ms, "dur_ms": dur_ms,
                "contractions_per_10": contractions,
                "uc_tone_min": tone_min, "uc_tone_max": tone_max
            }})
            return

        else:
            emit("ack", {"ok": False, "error": "preset desconhecido", "echo": payload})
            return

    # ----- Padrão de contrações (period/duration + amplitude) -----
    if mode == "uc_pattern":
        try:
            per = int(payload.get("period_ms", 150000) or 150000)
            dur = int(payload.get("dur_ms", 40000) or 40000)
            uc_amp   = payload.get("uc_amp", None)
            tone_min = payload.get("tone_min", None)
            tone_max = payload.get("tone_max", None)
        except Exception:
            emit("ack", {"ok": False, "error": "uc_pattern inválido"})
            return

        clean = {
            "mode": "uc_pattern",
            "period_ms": max(1000, per),
            "dur_ms": max(1000, dur),
        }
        if isinstance(uc_amp, (int, float)):
            clean["uc_amp"] = max(0, min(100, int(uc_amp)))

        # suporte ao tônus basal (opcional)
        if isinstance(tone_min, (int, float)) or isinstance(tone_max, (int, float)):
            try:
                tmin = 0 if tone_min is None else int(tone_min)
                tmax = 0 if tone_max is None else int(tone_max)
            except Exception:
                pass
            else:
                tmin = max(0, min(100, tmin))
                tmax = max(0, min(100, tmax))
                if tmin > tmax:
                    tmin, tmax = tmax, tmin
                clean["tone_min"] = tmin
                clean["tone_max"] = tmax

        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Controle do auto-retorno (4 contrações em ≤10min) -----
    if mode == "labor_auto":
        try:
            enabled   = bool(payload.get("enabled", True))
            max_contr = int(payload.get("max_contr", 4) or 4)
            window_ms = int(payload.get("window_ms", 600000) or 600000)
            period_ms = int(payload.get("period_ms", 150000) or 150000)
        except Exception:
            emit("ack", {"ok": False, "error": "labor_auto inválido"})
            return

        clean = {
            "mode": "labor_auto",
            "enabled": enabled,
            "max_contr": max(1, min(10, max_contr)),
            "window_ms": max(1000, window_ms),
            "period_ms": max(1000, period_ms),
        }
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

        # ----- Escala de tempo (0.05x..10x) -----
    if mode == "time_scale":
        try:
            factor = float(payload.get("factor", 1.0))
        except Exception:
            emit("ack", {"ok": False, "error": "factor inválido"})
            return
        factor = max(0.05, min(20.0, factor))
        clean = {"mode": "time_scale", "factor": factor}
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Novas DIPs variáveis: V, U e W, com/sem contração -----
    variable_dip_labels = {
        "dip_variavel_v_contracao": "DIP variável V com onda",
        "dip_variavel_v_sem_contracao": "DIP variável V sem onda",
        "dip_variavel_u_contracao": "DIP variável U com onda",
        "dip_variavel_u_sem_contracao": "DIP variável U sem onda",
        "dip_variavel_w_contracao": "DIP variável W com onda",
        "dip_variavel_w_sem_contracao": "DIP variável W sem onda",
    }

    if mode in variable_dip_labels:
        clean = {
            "mode": mode,
            "label": variable_dip_labels[mode],
        }
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- DIP variável (antiga DIPI precoce): queda sincronizada menos profunda -----
    if mode in {"dip_variavel", "dipi_precoce"}:
        duration = int(payload.get("duration", 40) or 40)  # FHR em segundos
        uc_peak  = int(payload.get("uc_peak", 50) or 50)   # mmHg
        uc_duration_sec = 60
        fhr_target = int(payload.get("fhr_target", 100) or 100)
        clean = {
            "mode": "dip_variavel",
            "duration": max(40, duration),
            "uc_duration_sec": uc_duration_sec,
            "uc_peak": max(0, min(100, uc_peak)),
            "fhr_target": max(30, min(240, fhr_target)),
        }
        emit_command_to_room(clean)           # envia p/ monitor
        emit("ack", {"ok": True, "echo": clean})  # ack p/ controle
        return
    
        # ----- DIP precoce: FHR em V + TOCO 60s com pico no vale -----
    if mode == "dipi_precoce_verdadeira":
        # defaults conforme sua especificação
        fhr_total_sec    = max(40, int(payload.get("fhr_total_sec", 40) or 40))   # queda+subida: mínimo 40s
        fhr_target       = int(payload.get("fhr_target", 100)   or 100)  # vale a 100 bpm

        uc_duration_sec  = 60 # TOCO 60s nas desacelerações
        uc_peak          = int(payload.get("uc_peak", 50) or 50)         # sobe até 50 mmHg
        fhr_delay_sec    = max(0, (uc_duration_sec / 2) - (fhr_total_sec / 2))  # nadir coincide com pico da TOCO

        clean = {
            "mode": "dipi_precoce_verdadeira",
            "fhr_total_sec": fhr_total_sec,
            "fhr_delay_sec": fhr_delay_sec,
            "fhr_target": max(30, min(240, fhr_target)),
            "uc_duration_sec": max(1, uc_duration_sec),
            "uc_peak": max(0, min(100, uc_peak))
        }
        emit_command_to_room(clean)            # envia p/ monitor
        emit("ack", {"ok": True, "echo": clean})   # ack p/ controle
        return

    # ----- DIP tardia: queda 30s, nadir 40s após pico da TOCO, retorno 60s -----
    if mode == "dip_tardia":
        late_fall_sec    = 30   # início da queda até nadir
        late_return_sec  = 60   # nadir até voltar ao basal
        fhr_total_sec    = late_fall_sec + late_return_sec
        fhr_target       = int(payload.get("fhr_target", 100) or 100)

        uc_duration_sec  = 60
        uc_peak          = int(payload.get("uc_peak", 50) or 50)
        late_nadir_after_peak_sec = 40
        late_nadir_frac = late_fall_sec / fhr_total_sec
        # Pico da TOCO ocorre no meio da onda de 60s: aos 30s.
        # Nadir desejado = 30s + 40s = 70s após início da TOCO.
        # Como a queda dura 30s, a FHR começa a cair aos 40s.
        fhr_delay_sec = max(0, (uc_duration_sec / 2) + late_nadir_after_peak_sec - late_fall_sec)

        clean = {
            "mode": "dip_tardia",
            "fhr_total_sec": fhr_total_sec,
            "fhr_delay_sec": fhr_delay_sec,
            "late_fall_sec": late_fall_sec,
            "late_return_sec": late_return_sec,
            "late_nadir_after_peak_sec": late_nadir_after_peak_sec,
            "late_nadir_frac": late_nadir_frac,
            "fhr_target": max(30, min(240, fhr_target)),
            "uc_duration_sec": max(1, uc_duration_sec),
            "uc_peak": max(0, min(100, uc_peak))
        }
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Aceleração transitória: sobe 16 bpm por 20s e retorna -----
    if mode == "acel_transitoria":
        duration = int(payload.get("duration", 20) or 20)
        rise = int(payload.get("rise", 16) or 16)
        ripple = int(payload.get("ripple", 0) or 0)

        clean = {
            "mode": "acel_transitoria",
            "duration": max(1, duration),
            "rise": max(1, min(60, rise)),
            "ripple": max(0, min(10, ripple)),
        }
        emit_command_to_room(clean)
        emit("ack", {"ok": True, "echo": clean})
        return

    # ----- Comando desconhecido -----
    emit("ack", {"ok": False, "echo": payload})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5050)
