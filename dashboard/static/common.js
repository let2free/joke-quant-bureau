/* 九章量化局 · 共享JS v1.0 */

// ── 统一导航栏 ──
function renderNav(activePage) {
  const pages = [
    { id:'dashboard', name:'📊 实时看板', href:'dashboard.html' },
    { id:'jiuzhang', name:'🧮 测算中心', href:'jiuzhang.html' },
    { id:'etf_monitor', name:'📈 ETF监测', href:'etf_monitor.html' },
    { id:'topology', name:'🔗 拓扑分析', href:'topology.html' },
    { id:'backtest', name:'📉 回测验证', href:'backtest.html' },
    { id:'history', name:'📁 历史数据', href:'history.html' },
    { id:'lobster_collab', name:'🦞 龙虾协同', href:'lobster_collab.html' }
  ];
  return pages.map(p =>
    `<a href="${p.href}" class="nav-tab ${p.id===activePage?'active':''}">${p.name}</a>`
  ).join('');
}

// ── 时钟 ──
function updateClock(id) {
  const el = document.getElementById(id);
  if (el) el.textContent = new Date().toLocaleTimeString('zh-CN',{hour12:false});
}

// ── 连接状态 ──
function checkConnection(dotId, textId) {
  const dot = document.getElementById(dotId);
  const text = document.getElementById(textId);
  if (!dot || !text) return;
  dot.className = 'dot ok'; text.textContent = '已连接';
}

// ── 通用fetch封装 ──
async function api(url) {
  const r = await fetch(url + (url.includes('?')?'&':'?') + 't=' + Date.now());
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── HTML转义 ──
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }

// ── 涨跌class ──
function upDown(val) { return val >= 0 ? 'up' : 'down'; }
function sign(val) { return val >= 0 ? '+' : ''; }
