import json
import subprocess
import os

REPO_DIR = r"C:\Users\PC\Documents\Dashboards\CERA"

# Ler dados
with open(f"{REPO_DIR}\\data.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['criativos']
sources = data['sources']
mediums = data['mediums']
campaigns = data['campaigns']
contents = data['contents']
total_leads = data['total_leads']
total_com_decil = data['total_com_decil']
total_conv = data['total_conv']
taxa_geral = data['taxa_geral']
decil_medio_geral = data['decil_medio_geral']
data_hoje = data['data_hoje']

# Gerar options para filtros
source_options = "\n".join([f'        <option value="{s}">{s}</option>' for s in sources if s != 'desconhecido'])
medium_options = "\n".join([f'        <option value="{m}">{m}</option>' for m in mediums if m != 'desconhecido'])
campaign_options = "\n".join([f'        <option value="{c}">{c[:50]}{"..." if len(c) > 50 else ""}</option>' for c in campaigns if c != 'desconhecido'])
content_options = "\n".join([f'        <option value="{c}">{c[:50]}{"..." if len(c) > 50 else ""}</option>' for c in contents if c != 'desconhecido'])

# Cores CERA
CERA_RED = "#FE1F2D"
CERA_RED_DARK = "#A80F1C"
CERA_RED_DEEP = "#710812"
CERA_BLACK = "#08090B"
CERA_GRAPHITE = "#17191E"
CERA_GRAY_DARK = "#2C2F35"
CERA_GRAY_MID = "#92959C"
CERA_WHITE = "#F5F5F5"

# Template HTML - salvar em arquivo temporário para evitar problemas com f-string
template_path = f"{REPO_DIR}\\template_v3.html"

with open(template_path, 'w', encoding='utf-8') as f:
    f.write('''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard CERA | Analise por Criativo + Decil</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  :root {
    --bg: {{CERA_BLACK}};
    --card: {{CERA_GRAPHITE}};
    --card-hover: {{CERA_GRAY_DARK}};
    --text: {{CERA_WHITE}};
    --text-muted: {{CERA_GRAY_MID}};
    --accent: {{CERA_RED}};
    --accent-dark: {{CERA_RED_DARK}};
    --accent-deep: {{CERA_RED_DEEP}};
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: {{CERA_RED}};
    --border: rgba(146,149,156,0.15);
    --gradient: linear-gradient(135deg, {{CERA_RED_DEEP}} 0%, {{CERA_RED}} 50%, #FF3542 100%);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text); min-height:100vh; line-height:1.6;
  }
  .container { max-width:1480px; margin:0 auto; padding:2rem; }
  
  header {
    text-align:center; padding:2.5rem 0 1.5rem;
    border-bottom:2px solid var(--accent);
    margin-bottom:2rem;
    background: linear-gradient(180deg, rgba(254,31,45,0.05) 0%, transparent 100%);
  }
  header h1 { font-size:2.2rem; font-weight:900; letter-spacing:-0.02em; }
  header h1 .cera-red { color:var(--accent); }
  header p { color:var(--text-muted); font-size:0.95rem; margin-top:0.5rem; }
  
  .stats-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(200px,1fr));
    gap:1rem; margin-bottom:2rem;
  }
  .stat-card {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:1.5rem; text-align:center; position:relative; overflow:hidden;
    transition:all 0.3s ease;
  }
  .stat-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:var(--gradient);
  }
  .stat-card:hover {
    transform:translateY(-3px);
    border-color:var(--accent);
    box-shadow:0 8px 32px rgba(254,31,45,0.15);
  }
  .stat-card .value { font-size:2.2rem; font-weight:800; margin:0.5rem 0; }
  .stat-card .label { color:var(--text-muted); font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; }
  .stat-card .change { font-size:0.8rem; margin-top:0.25rem; color:var(--text-muted); }
  
  .filters-section {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:1.5rem; margin-bottom:2rem;
  }
  .filters-title {
    font-size:1rem; font-weight:700; color:var(--accent); margin-bottom:1rem;
    display:flex; align-items:center; gap:0.5rem; text-transform:uppercase; letter-spacing:0.05em;
  }
  .filters-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(250px,1fr));
    gap:1rem;
  }
  .filter-group { display:flex; flex-direction:column; gap:0.4rem; }
  .filter-group label { font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; }
  .filter-group select {
    background:{{CERA_BLACK}}; border:1px solid var(--border); color:var(--text);
    padding:0.7rem 1rem; border-radius:8px; font-size:0.9rem;
    cursor:pointer; transition:border-color 0.2s;
  }
  .filter-group select:hover, .filter-group select:focus {
    border-color:var(--accent); outline:none;
  }
  .filter-actions {
    display:flex; gap:1rem; margin-top:1rem; justify-content:flex-end;
  }
  .btn {
    padding:0.6rem 1.2rem; border-radius:8px; border:none; font-size:0.85rem;
    font-weight:600; cursor:pointer; transition:all 0.2s; text-transform:uppercase; letter-spacing:0.05em;
  }
  .btn-primary {
    background:var(--accent); color:{{CERA_WHITE}};
  }
  .btn-primary:hover {
    background:var(--accent-dark); box-shadow:0 4px 16px rgba(254,31,45,0.3);
  }
  .btn-secondary {
    background:transparent; color:var(--text-muted); border:1px solid var(--border);
  }
  .btn-secondary:hover {
    border-color:var(--accent); color:var(--accent);
  }
  
  .section { margin-bottom:2.5rem; }
  .section-title {
    font-size:1.2rem; font-weight:700; margin-bottom:1rem;
    display:flex; align-items:center; gap:0.5rem;
    text-transform:uppercase; letter-spacing:0.03em;
  }
  .section-title::before {
    content:''; width:4px; height:24px;
    background:var(--gradient); border-radius:2px;
  }
  .chart-container {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:1.5rem; margin-bottom:1.5rem;
  }
  .charts-row {
    display:grid; grid-template-columns:repeat(auto-fit, minmax(450px,1fr)); gap:1.5rem;
  }
  
  table { width:100%; border-collapse:collapse; font-size:0.85rem; }
  th, td { padding:0.8rem 0.9rem; text-align:left; border-bottom:1px solid var(--border); }
  th {
    background:rgba(254,31,45,0.08); color:var(--accent); font-weight:700;
    text-transform:uppercase; font-size:0.7rem; letter-spacing:0.05em;
    position:sticky; top:0;
  }
  tr:hover { background:rgba(254,31,45,0.03); }
  .badge {
    display:inline-block; padding:0.2rem 0.5rem; border-radius:999px;
    font-size:0.7rem; font-weight:700;
  }
  .badge-success { background:rgba(34,197,94,0.15); color:#22c55e; }
  .badge-warning { background:rgba(245,158,11,0.15); color:#f59e0b; }
  .badge-danger { background:rgba(254,31,45,0.15); color:var(--accent); }
  .badge-info { background:rgba(254,31,45,0.1); color:var(--accent); }
  .truncate { max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .table-container {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    overflow:hidden; max-height:500px; overflow-y:auto;
  }
  
  .decil-box {
    display:inline-block; padding:0.25rem 0.6rem; border-radius:6px;
    font-weight:700; font-size:0.75rem;
  }
  .decil-quente { background:rgba(34,197,94,0.15); color:#22c55e; border:1px solid rgba(34,197,94,0.3); }
  .decil-morno { background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); }
  .decil-frio { background:rgba(254,31,45,0.1); color:var(--accent); border:1px solid rgba(254,31,45,0.2); }
  
  .correlation-grid {
    display:grid; grid-template-columns:repeat(auto-fit, minmax(300px,1fr)); gap:1rem;
  }
  .corr-card {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:1.2rem; transition:all 0.2s;
  }
  .corr-card:hover { border-color:var(--accent); }
  .corr-card h4 { color:var(--accent); font-size:0.9rem; margin-bottom:0.5rem; }
  .corr-card .metric { font-size:1.8rem; font-weight:800; }
  .corr-card .desc { color:var(--text-muted); font-size:0.8rem; }
  
  footer {
    text-align:center; padding:2rem; color:var(--text-muted);
    font-size:0.8rem; border-top:1px solid var(--border); margin-top:2rem;
  }
  footer .cera-brand { color:var(--accent); font-weight:700; }
  
  @media (max-width:768px) {
    .charts-row { grid-template-columns:1fr; }
    .stats-grid { grid-template-columns:repeat(2,1fr); }
    .filters-grid { grid-template-columns:1fr; }
  }
</style>
</head>
<body>

<div class="container">

<header>
  <h1>Dashboard <span class="cera-red">CERA</span> | Analise por Criativo</h1>
  <p>Conversao + Qualificacao Decil + Tempo Medio | Atualizado em {{DATA_HOJE}}</p>
</header>

<div class="stats-grid">
  <div class="stat-card">
    <div class="label">Total Leads</div>
    <div class="value">{{TOTAL_LEADS}}</div>
    <div class="change">Com rastreamento UTM</div>
  </div>
  <div class="stat-card">
    <div class="label">Com Decil</div>
    <div class="value" style="color:var(--accent)">{{TOTAL_COM_DECIL}}</div>
    <div class="change">{{PCT_COM_DECIL}}% dos leads</div>
  </div>
  <div class="stat-card">
    <div class="label">Conversoes</div>
    <div class="value" style="color:#22c55e">{{TOTAL_CONV}}</div>
    <div class="change">{{TAXA_GERAL}}% geral</div>
  </div>
  <div class="stat-card">
    <div class="label">Decil Medio</div>
    <div class="value" style="color:#f59e0b">{{DECIL_MEDIO}}</div>
    <div class="change">/100 pontos</div>
  </div>
  <div class="stat-card">
    <div class="label">Criativos</div>
    <div class="value">{{TOTAL_CRIATIVOS}}</div>
    <div class="change">Min. 20 leads</div>
  </div>
  <div class="stat-card">
    <div class="label">Melhor Taxa</div>
    <div class="value" style="color:#22c55e">{{MELHOR_TAXA}}%</div>
    <div class="change">{{MELHOR_CRIATIVO}}</div>
  </div>
</div>

<div class="filters-section">
  <div class="filters-title">🎯 Filtros UTM</div>
  <div class="filters-grid">
    <div class="filter-group">
      <label>Fonte (utm_source)</label>
      <select id="filterSource" onchange="updateFilters()">
        <option value="all">Todas as fontes</option>
{{SOURCE_OPTIONS}}
      </select>
    </div>
    <div class="filter-group">
      <label>Midia (utm_medium)</label>
      <select id="filterMedium" onchange="updateFilters()">
        <option value="all">Todas as midias</option>
{{MEDIUM_OPTIONS}}
      </select>
    </div>
    <div class="filter-group">
      <label>Campanha (utm_campaign)</label>
      <select id="filterCampaign" onchange="updateFilters()">
        <option value="all">Todas as campanhas</option>
{{CAMPAIGN_OPTIONS}}
      </select>
    </div>
    <div class="filter-group">
      <label>Criativo (utm_content)</label>
      <select id="filterContent" onchange="updateFilters()">
        <option value="all">Todos os criativos</option>
{{CONTENT_OPTIONS}}
      </select>
    </div>
  </div>
  <div class="filter-actions">
    <button class="btn btn-secondary" onclick="resetFilters()">Limpar Filtros</button>
    <button class="btn btn-primary" onclick="applyFilters()">Aplicar Filtros</button>
  </div>
</div>

<div class="section">
  <div class="section-title">Performance por Criativo</div>
  <div class="charts-row">
    <div class="chart-container">
      <h3 style="margin-bottom:1rem;font-size:0.9rem;color:var(--text-muted)">Taxa de Conversao (%)</h3>
      <canvas id="chartTaxa"></canvas>
    </div>
    <div class="chart-container">
      <h3 style="margin-bottom:1rem;font-size:0.9rem;color:var(--text-muted)">Decil Medio por Criativo</h3>
      <canvas id="chartDecil"></canvas>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Correlacao: Decil vs Conversao</div>
  <div class="chart-container">
    <canvas id="chartScatter" height="80"></canvas>
  </div>
</div>

<div class="section">
  <div class="section-title">Distribuicao por Temperatura Decil</div>
  <div class="charts-row">
    <div class="chart-container"><canvas id="chartTemperatura"></canvas></div>
    <div class="chart-container"><canvas id="chartTempo"></canvas></div>
  </div>
</div>

<div class="section">
  <div class="section-title">Correlacao Campanha x Criativo</div>
  <div class="correlation-grid" id="correlationCards"></div>
</div>

<div class="section">
  <div class="section-title">Top 20 Criativos - Conversao + Decil</div>
  <div class="table-container">
    <table id="tableTop">
      <thead>
        <tr>
          <th>#</th><th>Criativo</th><th>Campanha</th><th>Fonte</th><th>Midia</th><th>Leads</th>
          <th>Conv.</th><th>Taxa</th><th>Decil</th><th>Quente</th><th>Morno</th><th>Frio</th><th>Tempo</th>
        </tr>
      </thead>
      <tbody id="tbodyTop"></tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-title" style="color:var(--accent)">Criativos com 0% Conversao</div>
  <div class="table-container">
    <table id="tableZero">
      <thead>
        <tr><th>Criativo</th><th>Campanha</th><th>Leads</th><th>Decil</th><th>Quente</th><th>Morno</th><th>Status</th></tr>
      </thead>
      <tbody id="tbodyZero"></tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-title">Tabela Completa</div>
  <div class="table-container" style="max-height:600px;">
    <table id="tableFull">
      <thead>
        <tr>
          <th>Criativo</th><th>Campanha</th><th>Fonte</th><th>Midia</th><th>Leads</th><th>Conv.</th>
          <th>Taxa</th><th>Decil</th><th>Quente</th><th>Morno</th><th>Frio</th><th>Decil%</th><th>Tempo</th>
        </tr>
      </thead>
      <tbody id="tbodyFull"></tbody>
    </table>
  </div>
</div>

<footer>
  <span class="cera-brand">CERA</span> — Dashboard de Analise por Criativo v3.0 | Atualizado em {{DATA_HOJE}}
</footer>

</div>

<script>
const criativos = {{CRIATIVOS_JSON}};

function updateFilters() {
  const source = document.getElementById('filterSource').value;
  const medium = document.getElementById('filterMedium').value;
  const campaign = document.getElementById('filterCampaign').value;
  const content = document.getElementById('filterContent').value;
  
  let filtered = criativos;
  if(source !== 'all') filtered = filtered.filter(c => c.fonte === source);
  if(medium !== 'all') filtered = filtered.filter(c => c.midia === medium);
  if(campaign !== 'all') filtered = filtered.filter(c => c.campanha === campaign);
  if(content !== 'all') filtered = filtered.filter(c => c.criativo === content);
  
  renderAllTables(filtered);
  updateCharts(filtered);
}

function applyFilters() { updateFilters(); }

function resetFilters() {
  document.getElementById('filterSource').value = 'all';
  document.getElementById('filterMedium').value = 'all';
  document.getElementById('filterCampaign').value = 'all';
  document.getElementById('filterContent').value = 'all';
  renderAllTables(criativos);
  updateCharts(criativos);
}

function renderAllTables(data) {
  const top = data.filter(c=>c.taxa_conversao>0).sort((a,b)=>b.taxa_conversao-a.taxa_conversao).slice(0,20);
  document.getElementById('tbodyTop').innerHTML = top.map((c,i)=>
    `<tr>` +
      `<td><span class="badge badge-info">${i+1}</span></td>` +
      `<td class="truncate" title="${c.criativo}">${c.criativo}</td>` +
      `<td class="truncate">${c.campanha}</td>` +
      `<td>${c.fonte}</td>` +
      `<td>${c.midia}</td>` +
      `<td>${c.total_leads}</td>` +
      `<td>${c.conversoes}</td>` +
      `<td><span class="badge ${c.taxa_conversao_pct>=5?'badge-success':c.taxa_conversao_pct>=2?'badge-warning':'badge-danger'}">${c.taxa_conversao_pct.toFixed(2)}%</span></td>` +
      `<td><span class="decil-box ${c.decil_medio>=60?'decil-quente':c.decil_medio>=45?'decil-morno':'decil-frio'}">${c.decil_medio.toFixed(1)}</span></td>` +
      `<td>${c.pct_quente.toFixed(1)}%</td>` +
      `<td>${c.pct_morno.toFixed(1)}%</td>` +
      `<td>${c.pct_frio.toFixed(1)}%</td>` +
      `<td>${c.dias_medios_conversao!==null?c.dias_medios_conversao.toFixed(1):'N/A'}</td>` +
    `</tr>`
  ).join('');

  const zeros = data.filter(c=>c.taxa_conversao===0).sort((a,b)=>b.total_leads-a.total_leads);
  document.getElementById('tbodyZero').innerHTML = zeros.map(c=>
    `<tr>` +
      `<td class="truncate" title="${c.criativo}">${c.criativo}</td>` +
      `<td class="truncate">${c.campanha}</td>` +
      `<td style="color:var(--accent);font-weight:700">${c.total_leads}</td>` +
      `<td><span class="decil-box ${c.decil_medio>=60?'decil-quente':c.decil_medio>=45?'decil-morno':'decil-frio'}">${c.decil_medio.toFixed(1)}</span></td>` +
      `<td>${c.pct_quente.toFixed(1)}%</td>` +
      `<td>${c.pct_morno.toFixed(1)}%</td>` +
      `<td><span class="badge badge-danger">PAUSAR</span></td>` +
    `</tr>`
  ).join('');

  document.getElementById('tbodyFull').innerHTML = data.map(c=>
    `<tr>` +
      `<td class="truncate" title="${c.criativo}">${c.criativo}</td>` +
      `<td class="truncate">${c.campanha}</td>` +
      `<td>${c.fonte}</td>` +
      `<td>${c.midia}</td>` +
      `<td>${c.total_leads}</td>` +
      `<td>${c.conversoes}</td>` +
      `<td><span class="badge ${c.taxa_conversao_pct>=5?'badge-success':c.taxa_conversao_pct>=2?'badge-warning':c.taxa_conversao_pct>0?'badge-danger':'badge-danger'}">${c.taxa_conversao_pct.toFixed(2)}%</span></td>` +
      `<td><span class="decil-box ${c.decil_medio>=60?'decil-quente':c.decil_medio>=45?'decil-morno':'decil-frio'}">${c.decil_medio.toFixed(1)}</span></td>` +
      `<td>${c.pct_quente.toFixed(1)}%</td>` +
      `<td>${c.pct_morno.toFixed(1)}%</td>` +
      `<td>${c.pct_frio.toFixed(1)}%</td>` +
      `<td>${c.pct_com_decil.toFixed(1)}%</td>` +
      `<td>${c.dias_medios_conversao!==null?c.dias_medios_conversao.toFixed(1):'N/A'}</td>` +
    `</tr>`
  ).join('');

  renderCorrelation(data);
}

function renderCorrelation(data) {
  const campData = {};
  data.forEach(c => {
    if(!campData[c.campanha]) campData[c.campanha] = {leads:0, conv:0, decil:0, count:0};
    campData[c.campanha].leads += c.total_leads;
    campData[c.campanha].conv += c.conversoes;
    campData[c.campanha].decil += c.decil_medio * c.total_leads;
    campData[c.campanha].count += c.total_leads;
  });
  
  const cards = Object.entries(campData)
    .map(([camp, v]) => ({camp, leads: v.leads, conv: v.conv, taxa: v.conv/v.leads*100, decil: v.decil/v.count}))
    .sort((a,b) => b.taxa - a.taxa)
    .slice(0,6);
  
  document.getElementById('correlationCards').innerHTML = cards.map(c=>
    `<div class="corr-card">` +
      `<h4>${c.camp.length>25?c.camp.slice(0,25)+'...':c.camp}</h4>` +
      `<div class="metric" style="color:${c.taxa>=5?'#22c55e':c.taxa>=2?'#f59e0b':'#FE1F2D'}">${c.taxa.toFixed(2)}%</div>` +
      `<div class="desc">${c.leads} leads | Decil: ${c.decil.toFixed(1)} | ${c.conv} conv.</div>` +
    `</div>`
  ).join('');
}

let charts = {};

function updateCharts(data) {
  const top10 = data.filter(c=>c.taxa_conversao>0).sort((a,b)=>b.taxa_conversao-a.taxa_conversao).slice(0,10);
  if(charts.taxa) charts.taxa.destroy();
  charts.taxa = new Chart(document.getElementById('chartTaxa'),{
    type:'bar',
    data:{
      labels:top10.map(c=>c.criativo.length>18?c.criativo.slice(0,18)+'...':c.criativo),
      datasets:[{
        label:'Taxa Conversao (%)',
        data:top10.map(c=>c.taxa_conversao_pct),
        backgroundColor:top10.map(c=>c.taxa_conversao_pct>=8?'rgba(34,197,94,0.8)':c.taxa_conversao_pct>=3?'rgba(245,158,11,0.8)':'rgba(254,31,45,0.7)'),
        borderColor:top10.map(c=>c.taxa_conversao_pct>=8?'#22c55e':c.taxa_conversao_pct>=3?'#f59e0b':'#FE1F2D'),
        borderWidth:1
      }]
    },
    options:{
      responsive:true,plugins:{legend:{display:false}},
      scales:{
        y:{beginAtZero:true,grid:{color:'rgba(146,149,156,0.1)'},ticks:{color:'#92959C'}}},
        x:{grid:{display:false},ticks:{color:'#92959C',maxRotation:45}}
      }
    }
  });

  const topDecil = data.filter(c=>c.decil_medio>0).sort((a,b)=>b.decil_medio-a.decil_medio).slice(0,10);
  if(charts.decil) charts.decil.destroy();
  charts.decil = new Chart(document.getElementById('chartDecil'),{
    type:'bar',
    data:{
      labels:topDecil.map(c=>c.criativo.length>18?c.criativo.slice(0,18)+'...':c.criativo),
      datasets:[{
        label:'Decil Medio',
        data:topDecil.map(c=>c.decil_medio),
        backgroundColor:topDecil.map(c=>c.decil_medio>=60?'rgba(34,197,94,0.8)':c.decil_medio>=45?'rgba(245,158,11,0.8)':'rgba(254,31,45,0.7)'),
        borderWidth:1
      }]
    },
    options:{
      responsive:true,plugins:{legend:{display:false}},
      scales:{
        y:{beginAtZero:true,max:100,grid:{color:'rgba(146,149,156,0.1)'},ticks:{color:'#92959C'}}},
        x:{grid:{display:false},ticks:{color:'#92959C',maxRotation:45}}
      }
    }
  });

  const convs = data.filter(c=>c.taxa_conversao>0);
  if(charts.scatter) charts.scatter.destroy();
  charts.scatter = new Chart(document.getElementById('chartScatter'),{
    type:'scatter',
    data:{
      datasets:[{
        label:'Criativos',
        data:convs.map(c=>({x:c.decil_medio,y:c.taxa_conversao_pct,r:Math.sqrt(c.total_leads)*1.5})),
        backgroundColor:convs.map(c=>c.decil_medio>=60?'rgba(34,197,94,0.7)':c.decil_medio>=45?'rgba(245,158,11,0.7)':'rgba(254,31,45,0.6)')
      }]
    },
    options:{
      responsive:true,
      plugins:{tooltip:{callbacks:{label:(ctx)=>`${convs[ctx.dataIndex].criativo}: ${ctx.raw.y.toFixed(2)}% conv. | Decil: ${ctx.raw.x.toFixed(1)}`}}}},
      scales:{
        x:{title:{display:true,text:'Decil Medio',color:'#92959C'},grid:{color:'rgba(146,149,156,0.1)'},ticks:{color:'#92959C'}}},
        y:{title:{display:true,text:'Taxa Conversao (%)',color:'#92959C'},grid:{color:'rgba(146,149,156,0.1)'},ticks:{color:'#92959C'}}}
      }
    }
  });

  const tempData = data.reduce((acc,c)=>{
    acc.quente += c.pct_quente * c.total_leads / 100;
    acc.morno += c.pct_morno * c.total_leads / 100;
    acc.frio += c.pct_frio * c.total_leads / 100;
    return acc;
  },{quente:0,morno:0,frio:0});
  if(charts.temp) charts.temp.destroy();
  charts.temp = new Chart(document.getElementById('chartTemperatura'),{
    type:'doughnut',
    data:{
      labels:['Quente (60-100)','Morno (45-59)','Frio (0-44)'],
      datasets:[{
        data:[tempData.quente,tempData.morno,tempData.frio],
        backgroundColor:['rgba(34,197,94,0.8)','rgba(245,158,11,0.8)','rgba(254,31,45,0.7)'],
        borderWidth:0
      }]
    },
    options:{responsive:true,plugins:{legend:{position:'bottom',labels:{color:'#92959C'}}}}
  });

  const topTempo = data.filter(c=>c.dias_medios_conversao!==null).sort((a,b)=>a.dias_medios_conversao-b.dias_medios_conversao).slice(0,10);
  if(charts.tempo) charts.tempo.destroy();
  charts.tempo = new Chart(document.getElementById('chartTempo'),{
    type:'bar',
    data:{
      labels:topTempo.map(c=>c.criativo.length>18?c.criativo.slice(0,18)+'...':c.criativo),
      datasets:[{
        label:'Dias ate Conversao',
        data:topTempo.map(c=>c.dias_medios_conversao),
        backgroundColor:'rgba(254,31,45,0.6)',
        borderWidth:1
      }]
    },
    options:{
      responsive:true,plugins:{legend:{display:false}},
      scales:{
        y:{beginAtZero:true,grid:{color:'rgba(146,149,156,0.1)'},ticks:{color:'#92959C'}}},
        x:{grid:{display:false},ticks:{color:'#92959C',maxRotation:45}}
      }
    }
  });
}

renderAllTables(criativos);
updateCharts(criativos);
</script>

</body>
</html>''')

# Ler template e substituir placeholders
with open(template_path, 'r', encoding='utf-8') as f:
    template = f.read()

html_final = template \
    .replace('{{CERA_BLACK}}', CERA_BLACK) \
    .replace('{{CERA_GRAPHITE}}', CERA_GRAPHITE) \
    .replace('{{CERA_GRAY_DARK}}', CERA_GRAY_DARK) \
    .replace('{{CERA_GRAY_MID}}', CERA_GRAY_MID) \
    .replace('{{CERA_WHITE}}', CERA_WHITE) \
    .replace('{{CERA_RED}}', CERA_RED) \
    .replace('{{CERA_RED_DARK}}', CERA_RED_DARK) \
    .replace('{{CERA_RED_DEEP}}', CERA_RED_DEEP) \
    .replace('{{DATA_HOJE}}', data_hoje) \
    .replace('{{TOTAL_LEADS}}', f"{total_leads:,}") \
    .replace('{{TOTAL_COM_DECIL}}', f"{total_com_decil:,}") \
    .replace('{{PCT_COM_DECIL}}', f"{total_com_decil/total_leads*100:.1f}" if total_leads > 0 else "0") \
    .replace('{{TOTAL_CONV}}', str(total_conv)) \
    .replace('{{TAXA_GERAL}}', f"{taxa_geral:.2f}") \
    .replace('{{DECIL_MEDIO}}', f"{decil_medio_geral:.1f}") \
    .replace('{{TOTAL_CRIATIVOS}}', str(len(records))) \
    .replace('{{MELHOR_TAXA}}', f"{records[0]['taxa_conversao_pct']:.2f}" if records else "0.00") \
    .replace('{{MELHOR_CRIATIVO}}', records[0]['criativo'][:20] if records else "N/A") \
    .replace('{{SOURCE_OPTIONS}}', source_options) \
    .replace('{{MEDIUM_OPTIONS}}', medium_options) \
    .replace('{{CAMPAIGN_OPTIONS}}', campaign_options) \
    .replace('{{CONTENT_OPTIONS}}', content_options) \
    .replace('{{CRIATIVOS_JSON}}', json.dumps(records, ensure_ascii=False, default=str))

with open(f"{REPO_DIR}\\index.html", 'w', encoding='utf-8') as f:
    f.write(html_final)

os.remove(template_path)

print(f"Dashboard gerado: {REPO_DIR}\\index.html")

# Git push
try:
    subprocess.run(['git', 'add', 'index.html', 'data.json', 'generate_data.py', 'build_dashboard.py'], cwd=REPO_DIR, check=True)
    subprocess.run(['git', 'commit', '-m', f'feat: dashboard v3.0 CERA com filtros UTM e Decil - {data_hoje}'], cwd=REPO_DIR, check=True)
    subprocess.run(['git', 'push', 'origin', 'main'], cwd=REPO_DIR, check=True)
    print("Push realizado com sucesso!")
except Exception as e:
    print(f"Aviso: {e}")

print("\n" + "="*60)
print("DASHBOARD V3.0 PUBLICADO!")
print("="*60)
print(f"URL: https://mathandrap.github.io/dashboard-cera-criativos/")
print(f"Leads: {total_leads} | Com Decil: {total_com_decil}")
print(f"Taxa: {taxa_geral:.2f}% | Decil: {decil_medio_geral:.1f}")
print("="*60)
