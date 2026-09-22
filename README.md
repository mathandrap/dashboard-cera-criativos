# Dashboard CERA - Analise por Criativo

Dashboard interativo com taxa de conversao e tempo medio de venda por criativo da Plataforma CERA.

## Como atualizar os dados

### Opcao 1: Duplo clique (mais facil)
1. Execute o arquivo `atualizar.bat`
2. Aguarde a atualizacao automatica
3. Pronto!

### Opcao 2: Linha de comando
```bash
python update_dashboard.py
```

## O que o script faz

1. Conecta no banco de dados CERA (PostgreSQL)
2. Extrai leads com UTM e conversoes
3. Processa dados por criativo
4. Gera o HTML atualizado
5. Faz commit e push automatico pro GitHub (se configurado)

## Configuracao inicial do GitHub

Se ainda nao configurou o remote:

```bash
git remote add origin https://github.com/SEU-USUARIO/dashboard-cera-criativos.git
git push -u origin master
```

## Requisitos

- Python 3.8+
- Bibliotecas: `pandas`, `sqlalchemy`, `psycopg2`
- Certificados SSL do banco CERA (ja configurados no script)

## URL do dashboard

Apos configurar o GitHub Pages:
```
https://SEU-USUARIO.github.io/dashboard-cera-criativos/
```

## Ultima atualizacao

22/09/2026
