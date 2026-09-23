import sys
import json
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text
import os

DB_URL = "postgresql+psycopg2://postgres:giwS2InC1gqYAmjCSbL@cera-database-automacao.plataformacera.com:5437/postgres"
SSL_CERT = r"C:\Users\PC\.config\opencode\skills\cera-db\certs\client.crt"
SSL_KEY = r"C:\Users\PC\.config\opencode\skills\cera-db\certs\client.key"
REPO_DIR = r"C:\Users\PC\Documents\Dashboards\CERA"
HTML_OUTPUT = f"{REPO_DIR}\\index.html"
MIN_LEADS = 20

# REGRAS DECIL
FAT_PONTOS = {"ate_5k": 0, "5k_10k": 10, "10k_15k": 20, "15k_25k": 30, "acima_25k": 40, "nao_respondeu": 5, "desconhecido": 0}
FUNC_PONTOS = {"sozinho": 0, "1-2": 8, "3-5": 18, "6+": 25, "desconhecido": 0}
RAMO_PONTOS = {
    "Martelinho de ouro": 15, "Insulfilm e acessórios": 15, "Funilaria e pintura": 15,
    "Estacionamento": 12, "Franquias automotivas": 12, "Auto elétrica": 12,
    "Auto center": 12, "Estética automotiva": 10, "Oficina Mecânica": 10,
    "Higienização de estofados": 10, "Lava rápido": 7, "Borracharia": 7, "Outro ramo": 3,
}
DOR_PONTOS = {
    "Falta de dados para gerir": 15, "Insatisfação com o software atual": 15,
    "Baixa performance operacional": 13, "Desorganização operacional": 12,
    "Organizar minha agenda": 12, "Problemas com gestão": 12,
    "Fidelizar clientes": 10, "Atração de clientes": 8,
    "Dificuldade de Venda e Precificação": 7, "Precificar com lucro": 7,
    "Problemas financeiros": 5, "Controlar minhas finanças (entrada e saída)": 5,
    "Aumentar minhas vendas": 4, "Outro": 7,
}
CANAL_PONTOS = {
    "Eventos presenciais": 5, "Recomendação de Amigos ou Familiares": 5, "Recomendação": 5,
    "Pesquisa no Google": 5, "Outro": 3, "Influenciadores": 2, "Youtube": 2, "Podcast": 2,
    "Apple Store": 0, "Anúncios nas Redes Sociais": 0, "Instagram": -2, "TikTok": -3,
    "Whatsapp": -5, "Facebook": -5, "Play Store": -5, "LinkedIn": -5,
}

def normalizar_faturamento(valor):
    texto = str(valor or "")
    if "Prefiro" in texto: return "nao_respondeu"
    if texto in ["Até R$ 5.000,00", "R$ 0,00 a R$ 5.000,00"]: return "ate_5k"
    if "Acima" in texto and "25.000" in texto: return "acima_25k"
    if "15.001" in texto or "15.000" in texto: return "15k_25k"
    if "10.001" in texto or "10.000" in texto: return "10k_15k"
    if "5001" in texto or "5.001" in texto or "5.000" in texto: return "5k_10k"
    return "desconhecido"

def normalizar_funcionarios(valor):
    if valor == "Trabalho sozinho": return "sozinho"
    if any(v in str(valor) for v in ["1 a 2", "2 pessoas"]): return "1-2"
    if any(v in str(valor) for v in ["3 a 5", "3 pessoas", "4 pessoas"]): return "3-5"
    if any(v in str(valor) for v in ["6 ou mais", "5 ou mais"]): return "6+"
    return "desconhecido"

def calcular_decil(resultados):
    if not resultados or len(resultados) < 5:
        return None, None
    try:
        ramos = resultados[0].get('resposta', [])
        func_raw = resultados[1].get('resposta', [''])[0] if len(resultados) > 1 else ''
        fat_raw = resultados[2].get('resposta', [''])[0] if len(resultados) > 2 else ''
        dores = resultados[3].get('resposta', []) if len(resultados) > 3 else []
        canal_raw = resultados[4].get('resposta', ['desconhecido'])[0] if len(resultados) > 4 else 'desconhecido'
        
        fat = normalizar_faturamento(fat_raw)
        func = normalizar_funcionarios(func_raw)
        
        pts = {
            'faturamento': FAT_PONTOS.get(fat, 0),
            'funcionarios': FUNC_PONTOS.get(func, 0),
            'ramo': max([RAMO_PONTOS.get(r, 3) for r in ramos] or [0]),
            'dor': max([DOR_PONTOS.get(d, 4) for d in dores] or [0]),
            'canal': CANAL_PONTOS.get(canal_raw, 0),
        }
        
        score_bruto = max(0, min(100, sum(pts.values())))
        exige_teto = fat in ["ate_5k", "nao_respondeu", "desconhecido"]
        score = min(score_bruto, 54) if exige_teto else score_bruto
        
        if score >= 60: faixa = "Quente"
        elif score >= 45: faixa = "Morno"
        else: faixa = "Frio"
        
        return score, faixa
    except:
        return None, None

print("[1/6] Conectando ao banco CERA...")
engine = create_engine(DB_URL, connect_args={"sslmode": "require", "sslcert": SSL_CERT, "sslkey": SSL_KEY})

def query(sql):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)

print("[2/6] Extraindo leads e conversoes...")
sql_leads = """
WITH leads_utm AS (
    SELECT e._id as idempresa, e.dataregistro as data_lead, u.email, u.rastreamento
    FROM mongodb_cera.empresas e
    JOIN mongodb_cera.usuarios u ON u.idempresa = e._id
    WHERE e.dataregistro >= '2025-05-01'
      AND u.rastreamento IS NOT NULL AND u.rastreamento != ''
      AND u.rastreamento LIKE '%utm_content%'
),
conversoes AS (
    SELECT idempresa, MIN(datainicio) as data_primeira_conversao, MIN(valor) as valor_primeiro_plano
    FROM mongodb_cera.planosempresas
    WHERE nome != 'Teste Grátis' AND valor > 0
    GROUP BY idempresa
)
SELECT l.idempresa, l.data_lead, l.email, l.rastreamento,
    c.data_primeira_conversao, c.valor_primeiro_plano,
    CASE WHEN c.idempresa IS NOT NULL THEN 1 ELSE 0 END as converteu,
    CASE WHEN c.idempresa IS NOT NULL 
         THEN EXTRACT(EPOCH FROM (c.data_primeira_conversao - l.data_lead))/86400.0 
         ELSE NULL END as dias_ate_conversao
FROM leads_utm l
LEFT JOIN conversoes c ON c.idempresa = l.idempresa
ORDER BY l.data_lead DESC
"""
df_leads = query(sql_leads)

print("[3/6] Extraindo pesquisas onboarding...")
sql_onb = "SELECT idempresa, resultados FROM mongodb_cera.pesquisasonboardings WHERE resultados IS NOT NULL"
df_onb = query(sql_onb)
df_onb_unique = df_onb.drop_duplicates('idempresa', keep='last')

print("[4/6] Calculando Decil e processando UTM...")
def parse_rastreamento(r):
    try:
        return json.loads(r.replace("'", '"'))
    except:
        return {}

utm_data = df_leads['rastreamento'].apply(parse_rastreamento)
utm_df = pd.DataFrame(utm_data.tolist())
df_leads = pd.concat([df_leads, utm_df], axis=1)
df_leads['criativo'] = df_leads['utm_content'].fillna('desconhecido').astype(str)
df_leads['campanha'] = df_leads['utm_campaign'].fillna('desconhecido').astype(str)
df_leads['fonte'] = df_leads['utm_source'].fillna('desconhecido').astype(str)
df_leads['midia'] = df_leads['utm_medium'].fillna('desconhecido').astype(str)

df = df_leads.merge(df_onb_unique[['idempresa', 'resultados']], on='idempresa', how='left')

def safe_calc_decil(r):
    if r is None or (isinstance(r, float) and np.isnan(r)) or (isinstance(r, list) and len(r) == 0):
        return (None, None)
    return calcular_decil(r)

decil_data = df['resultados'].apply(safe_calc_decil)
df['decil_score'] = decil_data.apply(lambda x: x[0])
df['decil_faixa'] = decil_data.apply(lambda x: x[1])

agg = df.groupby('criativo').agg(
    total_leads=('idempresa', 'count'),
    conversoes=('converteu', 'sum'),
    taxa_conversao=('converteu', 'mean'),
    decil_medio=('decil_score', 'mean'),
    pct_quente=('decil_faixa', lambda x: (x == 'Quente').mean() if x.notna().any() else 0),
    pct_morno=('decil_faixa', lambda x: (x == 'Morno').mean() if x.notna().any() else 0),
    pct_frio=('decil_faixa', lambda x: (x == 'Frio').mean() if x.notna().any() else 0),
    pct_com_decil=('decil_score', lambda x: x.notna().mean()),
    dias_medios_conversao=('dias_ate_conversao', 'mean'),
    receita_media=('valor_primeiro_plano', 'mean'),
    campanha=('campanha', lambda x: x.mode()[0] if not x.mode().empty else 'varias'),
    fonte=('fonte', lambda x: x.mode()[0] if not x.mode().empty else 'varias'),
    midia=('midia', lambda x: x.mode()[0] if not x.mode().empty else 'varias'),
    data_min=('data_lead', 'min'),
    data_max=('data_lead', 'max'),
).reset_index()

agg = agg[agg['total_leads'] >= MIN_LEADS].sort_values('taxa_conversao', ascending=False)
agg['taxa_conversao_pct'] = agg['taxa_conversao'] * 100
agg['pct_quente'] = agg['pct_quente'] * 100
agg['pct_morno'] = agg['pct_morno'] * 100
agg['pct_frio'] = agg['pct_frio'] * 100
agg['pct_com_decil'] = agg['pct_com_decil'] * 100
agg['data_min'] = agg['data_min'].dt.strftime('%Y-%m-%d')
agg['data_max'] = agg['data_max'].dt.strftime('%Y-%m-%d')

records = agg.to_dict('records')

# Limpar NaN para JSON valido
import math
for r in records:
    for k, v in r.items():
        if isinstance(v, float) and math.isnan(v):
            r[k] = None

# Adicionar nomes Meta Ads
meta_ids_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meta_ids.json')
try:
    with open(meta_ids_path, 'r', encoding='utf-8') as f:
        meta_ids = json.load(f)
    for r in records:
        r['nome_meta_criativo'] = meta_ids.get('anuncios', {}).get(r['criativo'], '')
        r['nome_meta_campanha'] = meta_ids.get('campanhas', {}).get(r['campanha'], '')
except Exception as e:
    print(f"      [Aviso] Nao carregou meta_ids.json: {e}")

total_leads = len(df)
total_conv = int(df['converteu'].sum())
taxa_geral = (total_conv / total_leads) * 100 if total_leads > 0 else 0
decil_medio_geral = df['decil_score'].mean()
df_decil = df[df['decil_score'].notna()]
total_com_decil = len(df_decil)

sources = sorted(df['fonte'].dropna().unique().tolist())
mediums = sorted(df['midia'].dropna().unique().tolist())
campaigns = sorted(df['campanha'].dropna().unique().tolist())
contents = sorted(df['criativo'].dropna().unique().tolist())

print(f"      Leads: {total_leads} | Com Decil: {total_com_decil} | Criativos: {len(records)}")

print("[5/6] Gerando HTML com paleta CERA...")
criativos_json = json.dumps(records, ensure_ascii=False, default=str)
sources_json = json.dumps(sources, ensure_ascii=False, default=str)
mediums_json = json.dumps(mediums, ensure_ascii=False, default=str)
campaigns_json = json.dumps(campaigns, ensure_ascii=False, default=str)
contents_json = json.dumps(contents, ensure_ascii=False, default=str)
data_hoje = datetime.now().strftime('%d/%m/%Y')

# Extrair datas min/max
df['data_lead'] = pd.to_datetime(df['data_lead'], utc=True)
data_min = df['data_lead'].min().strftime('%Y-%m-%d')
data_max = df['data_lead'].max().strftime('%Y-%m-%d')

# Salvar dados para o template
with open(f"{REPO_DIR}\\data.json", 'w', encoding='utf-8') as f:
    json.dump({
        'criativos': records,
        'sources': sources,
        'mediums': mediums,
        'campaigns': campaigns,
        'contents': contents,
        'total_leads': total_leads,
        'total_com_decil': total_com_decil,
        'total_conv': total_conv,
        'taxa_geral': taxa_geral,
        'decil_medio_geral': decil_medio_geral,
        'data_hoje': data_hoje,
        'data_min': data_min,
        'data_max': data_max
    }, f, ensure_ascii=False, default=str)

print("[6/6] HTML gerado e dados salvos!")
print("\n" + "="*60)
print("DADOS PRONTOS PARA O DASHBOARD!")
print("="*60)
print(f"Arquivo de dados: {REPO_DIR}\\data.json")
print(f"Leads: {total_leads} | Com Decil: {total_com_decil}")
print(f"Taxa geral: {taxa_geral:.2f}% | Decil medio: {decil_medio_geral:.1f}")
print(f"Criativos: {len(records)}")
print("="*60)
