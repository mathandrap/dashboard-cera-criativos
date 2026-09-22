import sys
import json
import subprocess
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text

# ============================================================
# CONFIGURACOES
# ============================================================
DB_URL = "postgresql+psycopg2://postgres:giwS2InC1gqYAmjCSbL@cera-database-automacao.plataformacera.com:5437/postgres"
SSL_CERT = r"C:\Users\PC\.config\opencode\skills\cera-db\certs\client.crt"
SSL_KEY = r"C:\Users\PC\.config\opencode\skills\cera-db\certs\client.key"
REPO_DIR = r"C:\Users\PC\Documents\Dashboards\CERA"
HTML_OUTPUT = f"{REPO_DIR}\\index.html"
MIN_LEADS = 20

# ============================================================
# 1. CONECTAR NO BANCO
# ============================================================
print("[1/5] Conectando ao banco CERA...")
engine = create_engine(
    DB_URL,
    connect_args={
        "sslmode": "require",
        "sslcert": SSL_CERT,
        "sslkey": SSL_KEY,
    }
)

def query(sql):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)

# ============================================================
# 2. EXTRAIR DADOS
# ============================================================
print("[2/5] Extraindo dados de leads e conversoes...")

sql = """
WITH leads_utm AS (
    SELECT 
        e._id as idempresa,
        e.dataregistro as data_lead,
        e.situacao,
        e.plano,
        u.email,
        u.rastreamento,
        u.contato->>'whatsapp' as whatsapp
    FROM mongodb_cera.empresas e
    JOIN mongodb_cera.usuarios u ON u.idempresa = e._id
    WHERE e.dataregistro >= '2025-05-01'
      AND u.rastreamento IS NOT NULL 
      AND u.rastreamento != ''
      AND u.rastreamento LIKE '%utm_content%'
),
conversoes AS (
    SELECT 
        idempresa,
        MIN(datainicio) as data_primeira_conversao,
        MIN(valor) as valor_primeiro_plano
    FROM mongodb_cera.planosempresas
    WHERE nome != 'Teste Grátis' 
      AND valor > 0
    GROUP BY idempresa
)
SELECT 
    l.idempresa,
    l.data_lead,
    l.email,
    l.rastreamento,
    c.data_primeira_conversao,
    c.valor_primeiro_plano,
    CASE WHEN c.idempresa IS NOT NULL THEN 1 ELSE 0 END as converteu,
    CASE WHEN c.idempresa IS NOT NULL 
         THEN EXTRACT(EPOCH FROM (c.data_primeira_conversao - l.data_lead))/86400.0 
         ELSE NULL END as dias_ate_conversao
FROM leads_utm l
LEFT JOIN conversoes c ON c.idempresa = l.idempresa
ORDER BY l.data_lead DESC
"""

df = query(sql)
print(f"      Leads extraidos: {len(df)}")
print(f"      Conversoes: {df['converteu'].sum()}")

# ============================================================
# 3. PROCESSAR DADOS
# ============================================================
print("[3/5] Processando dados por criativo...")

def parse_rastreamento(r):
    try:
        return json.loads(r.replace("'", '"'))
    except:
        return {}

utm_data = df['rastreamento'].apply(parse_rastreamento)
utm_df = pd.DataFrame(utm_data.tolist())
df = pd.concat([df, utm_df], axis=1)

df['criativo'] = df['utm_content'].fillna('desconhecido').astype(str)
df['campanha'] = df['utm_campaign'].fillna('desconhecido').astype(str)
df['fonte'] = df['utm_source'].fillna('desconhecido').astype(str)

# Agregar por criativo
agg = df.groupby('criativo').agg(
    total_leads=('idempresa', 'count'),
    conversoes=('converteu', 'sum'),
    taxa_conversao=('converteu', 'mean'),
    dias_medios_conversao=('dias_ate_conversao', 'mean'),
    dias_mediana_conversao=('dias_ate_conversao', 'median'),
    receita_media=('valor_primeiro_plano', 'mean'),
    campanha=('campanha', lambda x: x.mode()[0] if not x.mode().empty else 'varias'),
    fonte=('fonte', lambda x: x.mode()[0] if not x.mode().empty else 'varias'),
).reset_index()

agg = agg[agg['total_leads'] >= MIN_LEADS].sort_values('taxa_conversao', ascending=False)
agg['taxa_conversao_pct'] = agg['taxa_conversao'] * 100

records = agg.to_dict('records')
total_leads = int(df['idempresa'].count())
total_conv = int(df['converteu'].sum())
taxa_geral = (total_conv / total_leads) * 100 if total_leads > 0 else 0

print(f"      Criativos analisados: {len(records)}")

# ============================================================
# 4. GERAR HTML
# ============================================================
print("[4/5] Gerando HTML do dashboard...")

criativos_json = json.dumps(records, ensure_ascii=False, default=str)
data_hoje = datetime.now().strftime('%d/%m/%Y')

# Template HTML - usar placeholder para dados
with open('template.html', 'w', encoding='utf-8') as f:
    f.write('''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard - Analise por Criativo | CERA</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  :root {
    --bg: #0f172a; --card: #1e293b; --card-hover: #334155;
    --text: #f1f5f9; --text-muted: #94a3b8; --accent: #3b82f6;
    --accent-glow: rgba(59,130,246,0.3); --success: #22c55e;
    --warning: #f59e0b; --danger: #ef4444;
    --border: rgba(148,163,184,0.1);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text); min-height:100vh; line-height:1.6;
  }
  .container { max-width:1400px; margin:0 auto; padding:2rem; }
  header {
    text-align:center; padding:2rem 0 1rem;
    border-bottom:1px solid var(--border); margin-bottom:2rem;
  }
  header h1 { font-size:2rem; font-weight:800; margin-bottom:0.5rem; }
  header h1 span { color:var(--accent); }
  header p { color:var(--text-muted); font-size:0.95rem; }
  .stats-grid {
    display:grid; grid-template-columns:repeat(auto-fit, minmax(220px,1fr));
    gap:1rem; margin-bottom:2rem;
  }
  .stat-card {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:1.5rem; text-align:center; transition:transform 0.2s, box-shadow 0.2s;
  }
  .stat-card:hover { transform:translateY(-2px); box-shadow:0 8px 24px rgba(0,0,0,0.3); }
  .stat-card .value { font-size:2.2rem; font-weight:800; margin:0.5rem 0; }
  .stat-card .label { color:var(--text-muted); font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em; }
  .stat-card .change { font-size:0.85rem; margin-top:0.25rem; font-weight:600; }
  .success { color:var(--success); } .warning { color:var(--warning); } .danger { color:var(--danger); }
  .section { margin-bottom:2.5rem; }
  .section-title {
    font-size:1.3rem; font-weight:700; margin-bottom:1rem;
    display:flex; align-items:center; gap:0.5rem;
  }
  .section-title::before { content:''; width:4px; height:24px; background:var(--accent); border-radius:2px; }
  .chart-container {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:1.5rem; margin-bottom:1.5rem;
  }
  .charts-row {
    display:grid; grid-template-columns:repeat(auto-fit, minmax(500px,1fr)); gap:1.5rem;
  }
  table { width:100%; border-collapse:collapse; font-size:0.9rem; }
  th, td { padding:0.85rem 1rem; text-align:left; border-bottom:1px solid var(--border); }
  th {
    background:rgba(59,130,246,0.1); color:var(--accent); font-weight:700;
    text-transform:uppercase; font-size:0.75rem; letter-spacing:0.05em; position:sticky; top:0;
  }
  tr:hover { background:rgba(255,255,255,0.03); }
  .badge {
    display:inline-block; padding:0.25rem 0.6rem; border-radius:999px;
    font-size:0.75rem; font-weight:700;
  }
  .badge-success { background:rgba(34,197,94,0.15); color:var(--success); }
  .badge-warning { background:rgba(245,158,11,0.15); color:var(--warning); }
  .badge-danger { background:rgba(239,68,68,0.15); color:var(--danger); }
  .badge-info { background:rgba(59,130,246,0.15); color:var(--accent); }
  .truncate { max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .table-container {
    background:var(--card); border:1px solid var(--border); border-radius:12px;
    overflow:hidden; max-height:500px; overflow-y:auto;
  }
  .filter-bar { display:flex; gap:1rem; margin-bottom:1rem; flex-wrap:wrap; }
  .filter-bar input, .filter-bar select {
    background:var(--card); border:1px solid var(--border); color:var(--text);
    padding:0.6rem 1rem; border-radius:8px; font-size:0.9rem;
  }
  .filter-bar input:focus, .filter-bar select:focus { outline:none; border-color:var(--accent); }
  footer {
    text-align:center; padding:2rem; color:var(--text-muted); font-size:0.85rem;
    border-top:1px solid var(--border); margin-top:2rem;
  }
  @media (max-width:768px) {
    .charts-row { grid-template-columns:1fr; }
    .stat-card .value { font-size:1.5rem; }
  }
</style>
</head>
<body>

<div class="container">

<header>
  <h1>Analise por <span>Criativo</span></h1>
  <p>Taxa de Conversao + Tempo Medio de Venda | Plataforma CERA | Atualizado em {{DATA_HOJE}}</p>
</header>

<div class="stats-grid">
  <div class="stat-card">
    <div class="label">Total de Leads</div>
    <div class="value">{{TOTAL_LEADS}}</div>
    <div class="change success">Com rastreamento UTM</div>
  </div>
  <div class="stat-card">
    <div class="label">Conversoes</div>
    <div class="value" style="color:var(--success)">{{TOTAL_CONV}}</div>
    <div class="change">Taxa geral: {{TAXA_GERAL}}%</div>
  </div>
  <div class="stat-card">
    <div class="label">Criativos</div>
    <div class="value" style="color:var(--accent)">{{TOTAL_CRIATIVOS}}</div>
    <div class="change warning">Min. 20 leads</div>
  </div>
  <div class="stat-card">
    <div class="label">Melhor Taxa</div>
    <div class="value" style="color:var(--success)">{{MELHOR_TAXA}}%</div>
    <div class="change">{{MELHOR_CRIATIVO}}</div>
  </div>
  <div class="stat-card">
    <div class="label">Ultima Atualizacao</div>
    <div class="value" style="color:var(--accent);font-size:1.4rem">{{DATA_HOJE}}</div>
    <div class="change">Dados em tempo real do banco</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Performance por Criativo</div>
  <div class="charts-row">
    <div class="chart-container">
      <h3 style="margin-bottom:1rem;font-size:1rem;color:var(--text-muted)">Taxa de Conversao (%)</h3>
      <canvas id="chartTaxa"></canvas>
    </div>
    <div class="chart-container">
      <h3 style="margin-bottom:1rem;font-size:1rem;color:var(--text-muted)">Tempo Medio de Conversao (dias)</h3>
      <canvas id="chartTempo"></canvas>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Volume vs Conversao</div>
  <div class="chart-container">
    <canvas id="chartScatter" height="80"></canvas>
  </div>
</div>

<div class="section">
  <div class="section-title">Top 15 Criativos - Maior Taxa de Conversao</div>
  <div class="table-container">
    <table id="tableTop">
      <thead>
        <tr>
          <th>#</th><th>Criativo</th><th>Campanha</th><th>Fonte</th>
          <th>Leads</th><th>Conv.</th><th>Taxa</th><th>Tempo (dias)</th><th>Receita Media</th>
        </tr>
      </thead>
      <tbody id="tbodyTop"></tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-title" style="color:var(--danger)">Criativos com 0% Conversao - Desperdicio</div>
  <div class="table-container">
    <table id="tableZero">
      <thead>
        <tr><th>Criativo</th><th>Campanha</th><th>Fonte</th><th>Leads Perdidos</th><th>Status</th></tr>
      </thead>
      <tbody id="tbodyZero"></tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-title">Tabela Completa - Todos os Criativos</div>
  <div class="filter-bar">
    <input type="text" id="searchInput" placeholder="Buscar criativo..." onkeyup="filterTable()">
    <select id="filterTaxa" onchange="filterTable()">
      <option value="all">Todas taxas</option>
      <option value="high">Alta (&gt;5%)</option>
      <option value="mid">Media (1-5%)</option>
      <option value="low">Baixa (&lt;1%)</option>
      <option value="zero">Zero (0%)</option>
    </select>
  </div>
  <div class="table-container" style="max-height:600px;">
    <table id="tableFull">
      <thead>
        <tr>
          <th>Criativo</th><th>Campanha</th><th>Fonte</th><th>Leads</th>
          <th>Conv.</th><th>Taxa</th><th>Tempo (dias)</th>
        </tr>
      </thead>
      <tbody id="tbodyFull"></tbody>
    </table>
  </div>
</div>

<footer>
  Dashboard CERA | Dados extraidos do banco de dados em tempo real | Atualizado em {{DATA_HOJE}}
</footer>

</div>

<script>
const criativos = {{CRIATIVOS_JSON}};

function renderTables() {
  // Top 15
  const top = criativos.filter(c=>c.taxa_conversao>0).sort((a,b)=>b.taxa_conversao-a.taxa_conversao).slice(0,15);
  document.getElementById('tbodyTop').innerHTML = top.map((c,i)=>`
    <tr>
      <td><span class="badge badge-info">${i+1}</span></td>
      <td class="truncate" title="${c.criativo}">${c.criativo}</td>
      <td class="truncate">${c.campanha}</td>
      <td>${c.fonte}</td>
      <td>${c.total_leads}</td>
      <td>${c.conversoes}</td>
      <td><span class="badge ${c.taxa_conversao_pct>=5?'badge-success':c.taxa_conversao_pct>=2?'badge-warning':'badge-danger'}">${c.taxa_conversao_pct.toFixed(2)}%</span></td>
      <td>${c.dias_medios_conversao!==null?c.dias_medios_conversao.toFixed(1):'N/A'}</td>
      <td>R$ ${c.receita_media!==null?c.receita_media.toFixed(2):'0.00'}</td>
    </tr>
  `).join('');

  // Zero
  const zeros = criativos.filter(c=>c.taxa_conversao===0).sort((a,b)=>b.total_leads-a.total_leads);
  document.getElementById('tbodyZero').innerHTML = zeros.map(c=>`
    <tr>
      <td class="truncate" title="${c.criativo}">${c.criativo}</td>
      <td class="truncate">${c.campanha}</td>
      <td>${c.fonte}</td>
      <td style="color:var(--danger);font-weight:700">${c.total_leads}</td>
      <td><span class="badge badge-danger">PAUSAR</span></td>
    </tr>
  `).join('');

  renderFull(criativos);
}

function renderFull(data) {
  document.getElementById('tbodyFull').innerHTML = data.map(c=>`
    <tr>
      <td class="truncate" title="${c.criativo}">${c.criativo}</td>
      <td class="truncate">${c.campanha}</td>
      <td>${c.fonte}</td>
      <td>${c.total_leads}</td>
      <td>${c.conversoes}</td>
      <td><span class="badge ${c.taxa_conversao_pct>=5?'badge-success':c.taxa_conversao_pct>=2?'badge-warning':c.taxa_conversao_pct>0?'badge-danger':'badge-danger'}">${c.taxa_conversao_pct.toFixed(2)}%</span></td>
      <td>${c.dias_medios_conversao!==null?c.dias_medios_conversao.toFixed(1):'N/A'}</td>
    </tr>
  `).join('');
}

function filterTable() {
  const search = document.getElementById('searchInput').value.toLowerCase();
  const taxaFilter = document.getElementById('filterTaxa').value;
  let filtered = criativos.filter(c=>c.criativo.toLowerCase().includes(search)||c.campanha.toLowerCase().includes(search));
  if(taxaFilter==='high') filtered=filtered.filter(c=>c.taxa_conversao_pct>5);
  else if(taxaFilter==='mid') filtered=filtered.filter(c=>c.taxa_conversao_pct>=1&&c.taxa_conversao_pct<=5);
  else if(taxaFilter==='low') filtered=filtered.filter(c=>c.taxa_conversao_pct>0&&c.taxa_conversao_pct<1);
  else if(taxaFilter==='zero') filtered=filtered.filter(c=>c.taxa_conversao_pct===0);
  renderFull(filtered);
}

// Charts
const top10 = criativos.filter(c=>c.taxa_conversao>0).sort((a,b)=>b.taxa_conversao-a.taxa_conversao).slice(0,10);
const topTempo = criativos.filter(c=>c.dias_medios_conversao!==null).sort((a,b)=>a.dias_medios_conversao-b.dias_medios_conversao).slice(0,10);

new Chart(document.getElementById('chartTaxa'),{
  type:'bar',
  data:{
    labels:top10.map(c=>c.criativo.length>20?c.criativo.slice(0,20)+'...':c.criativo),
    datasets:[{
      label:'Taxa de Conversao (%)',
      data:top10.map(c=>c.taxa_conversao_pct),
      backgroundColor:top10.map(c=>c.taxa_conversao_pct>=8?'rgba(34,197,94,0.7)':c.taxa_conversao_pct>=3?'rgba(245,158,11,0.7)':'rgba(239,68,68,0.7)'),
      borderColor:top10.map(c=>c.taxa_conversao_pct>=8?'#22c55e':c.taxa_conversao_pct>=3?'#f59e0b':'#ef4444'),
      borderWidth:1
    }]
  },
  options:{
    responsive:true,
    plugins:{legend:{display:false}},
    scales:{
      y:{beginAtZero:true,grid:{color:'rgba(148,163,184,0.1)'},ticks:{color:'#94a3b8'}}},
      x:{grid:{display:false},ticks:{color:'#94a3b8',maxRotation:45}}
    }
  }
});

new Chart(document.getElementById('chartTempo'),{
  type:'bar',
  data:{
    labels:topTempo.map(c=>c.criativo.length>20?c.criativo.slice(0,20)+'...':c.criativo),
    datasets:[{
      label:'Dias ate Conversao',
      data:topTempo.map(c=>c.dias_medios_conversao),
      backgroundColor:'rgba(59,130,246,0.6)',
      borderColor:'#3b82f6',
      borderWidth:1
    }]
  },
  options:{
    responsive:true,
    plugins:{legend:{display:false}},
    scales:{
      y:{beginAtZero:true,grid:{color:'rgba(148,163,184,0.1)'},ticks:{color:'#94a3b8'}}},
      x:{grid:{display:false},ticks:{color:'#94a3b8',maxRotation:45}}
    }
  }
});

const convs = criativos.filter(c=>c.taxa_conversao>0);
new Chart(document.getElementById('chartScatter'),{
  type:'scatter',
  data:{
    datasets:[{
      label:'Criativos',
      data:convs.map(c=>({x:c.total_leads,y:c.taxa_conversao_pct,r:Math.sqrt(c.conversoes)*3})),
      backgroundColor:convs.map(c=>c.taxa_conversao_pct>=8?'rgba(34,197,94,0.6)':c.taxa_conversao_pct>=3?'rgba(245,158,11,0.6)':'rgba(239,68,68,0.6)')
    }]
  },
  options:{
    responsive:true,
    plugins:{
      tooltip:{
        callbacks:{
          label:(ctx)=>`${convs[ctx.dataIndex].criativo}: ${ctx.raw.y.toFixed(2)}% conv. (${ctx.raw.x} leads)`
        }
      }
    },
    scales:{
      x:{title:{display:true,text:'Volume de Leads',color:'#94a3b8'},grid:{color:'rgba(148,163,184,0.1)'},ticks:{color:'#94a3b8'}}},
      y:{title:{display:true,text:'Taxa de Conversao (%)',color:'#94a3b8'},grid:{color:'rgba(148,163,184,0.1)'},ticks:{color:'#94a3b8'}}}
    }
  }
});

renderTables();
</script>

</body>
</html>''')

# Agora ler o template e substituir os placeholders
with open('template.html', 'r', encoding='utf-8') as f:
    template = f.read()

# Substituir placeholders
html_final = template \
    .replace('{{DATA_HOJE}}', data_hoje) \
    .replace('{{TOTAL_LEADS}}', f"{total_leads:,}") \
    .replace('{{TOTAL_CONV}}', str(total_conv)) \
    .replace('{{TAXA_GERAL}}', f"{taxa_geral:.2f}") \
    .replace('{{TOTAL_CRIATIVOS}}', str(len(records))) \
    .replace('{{MELHOR_TAXA}}', f"{records[0]['taxa_conversao_pct']:.2f}" if records else "0.00") \
    .replace('{{MELHOR_CRIATIVO}}', records[0]['criativo'][:25] if records else "N/A") \
    .replace('{{CRIATIVOS_JSON}}', criativos_json)

with open(HTML_OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html_final)

# Remover template temporario
import os
os.remove('template.html')

print(f"      HTML gerado: {HTML_OUTPUT}")

# ============================================================
# 5. GIT COMMIT + PUSH
# ============================================================
print("[5/5] Fazendo commit e push para o GitHub...")

try:
    subprocess.run(['git', 'add', 'index.html'], cwd=REPO_DIR, check=True)
    subprocess.run(['git', 'commit', '-m', f'update: dados atualizados em {data_hoje}'], cwd=REPO_DIR, check=True)
    subprocess.run(['git', 'push', 'origin', 'main'], cwd=REPO_DIR, check=True)
    print("      Push realizado com sucesso!")
except subprocess.CalledProcessError as e:
    print(f"      [AVISO] Erro no git: {e}")
    print("      Verifique se o remote 'origin' esta configurado corretamente.")

print("\n" + "="*60)
print("ATUALIZACAO CONCLUIDA!")
print("="*60)
print(f"Data: {data_hoje}")
print(f"Leads: {total_leads}")
print(f"Conversoes: {total_conv}")
print(f"Taxa geral: {taxa_geral:.2f}%")
print(f"Criativos: {len(records)}")
print("="*60)
