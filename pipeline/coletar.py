"""Coleta das séries públicas usadas pelo painel.

Cada série é gravada em data/raw/<nome>.json com fonte, URL e data/hora de coleta.
Fontes: BCB/SGS (PTAX, Selic, IPCA, dívida, primário, fluxo cambial), BCB/Focus
(Olinda), Tesouro Transparente (Tesouro Direto: NTN-B e prefixados), FRED
(índice amplo do dólar, Fed Funds, VIX, BTC Coinbase), Binance (BTCUSDT) e
CoinGecko (preço à vista de conferência).
"""
import csv, io, json, sys, time, urllib.request, urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "analises-merc/1.0 (painel de risco)"}


def get(url, tries=4, timeout=90):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # rede instável: tenta de novo com espera crescente
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def salvar(nome, fonte, url, dados, extra=None):
    meta = {
        "serie": nome,
        "fonte": fonte,
        "url": url,
        "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n": len(dados),
        "dados": dados,
    }
    if extra:
        meta.update(extra)
    (RAW / f"{nome}.json").write_text(json.dumps(meta, ensure_ascii=False))
    print(f"{nome}: {len(dados)} pontos", file=sys.stderr)


def sgs(codigo, nome, desc, inicio=1999):
    """SGS limita séries diárias a 10 anos por consulta."""
    hoje = date.today()
    out, urls = [], []
    for a in range(inicio, hoje.year + 1, 9):
        fim = min(a + 8, hoje.year)
        url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json"
               f"&dataInicial=01/01/{a}&dataFinal=31/12/{fim}")
        urls.append(url)
        try:
            for x in json.loads(get(url)):
                d, m, y = x["data"].split("/")
                out.append([f"{y}-{m}-{d}", float(x["valor"])])
        except Exception as e:
            print(f"  aviso {codigo} {a}-{fim}: {e}", file=sys.stderr)
    out = sorted({d: v for d, v in out}.items())
    salvar(nome, f"BCB/SGS série {codigo} — {desc}",
           f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados", [list(x) for x in out])


def get_curl(url, timeout=120):
    """O FRED derruba conexões de clientes HTTP genéricos; o curl passa."""
    import subprocess
    for i in range(4):
        r = subprocess.run(["curl", "-sfL", "-m", str(timeout), url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout
        time.sleep(2 ** i)
    raise RuntimeError(f"curl falhou: {url}")


def fred(sid, nome, desc):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    rows = list(csv.reader(io.StringIO(get_curl(url).decode())))[1:]
    out = [[d, float(v)] for d, v in rows if v not in ("", ".")]
    salvar(nome, f"FRED série {sid} — {desc}", url, out)


def binance():
    out, start = [], 1500000000000
    base = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000"
    while True:
        k = json.loads(get(f"{base}&startTime={start}"))
        if not k:
            break
        for row in k:
            d = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).date().isoformat()
            out.append([d, float(row[4])])  # fechamento 00:00 UTC do dia seguinte
        start = k[-1][0] + 86400000
        if len(k) < 1000:
            break
    salvar("btc_binance", "Binance (data-api.binance.vision) — BTCUSDT, fechamento diário UTC",
           base, out)


def coingecko():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,brl&include_last_updated_at=true"
    d = json.loads(get(url))["bitcoin"]
    salvar("btc_coingecko_spot", "CoinGecko — preço à vista (conferência)", url,
           [[datetime.fromtimestamp(d["last_updated_at"], tz=timezone.utc).isoformat(), d["usd"], d["brl"]]])


def focus():
    base = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    inds = ["Câmbio", "IPCA", "Selic", "Resultado primário", "Dívida bruta do governo geral", "PIB Total"]
    out = []
    for ind in inds:
        q = {"$filter": f"Indicador eq '{ind}' and baseCalculo eq 0 and Data ge '2014-01-01'",
             "$select": "Indicador,Data,DataReferencia,Mediana,Media,DesvioPadrao,Minimo,Maximo,numeroRespondentes",
             "$format": "json", "$top": "100000"}
        url = base + "ExpectativasMercadoAnuais?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)
        out += json.loads(get(url, timeout=180))["value"]
    salvar("focus_anuais", "BCB/Focus — Expectativas de Mercado Anuais (mediana, base de cálculo 0)",
           base + "ExpectativasMercadoAnuais", out)
    # extrato versionado: só a última data, com as colunas que o painel usa
    ult = max(x["Data"] for x in out)
    salvar("focus_resumo", "BCB/Focus — Expectativas de Mercado Anuais (mediana, base de cálculo 0) — extrato da última data",
           base + "ExpectativasMercadoAnuais",
           [{k: x[k] for k in ("Indicador", "Data", "DataReferencia", "Mediana")} for x in out if x["Data"] == ult])
    q = {"$filter": "Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0 and Data ge '2014-01-01'",
         "$select": "Indicador,Data,Mediana", "$format": "json", "$top": "100000"}
    url = base + "ExpectativasMercadoInflacao12Meses?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)
    v = json.loads(get(url, timeout=180))["value"]
    salvar("focus_ipca12m", "BCB/Focus — IPCA esperado 12 meses à frente (suavizado)",
           base + "ExpectativasMercadoInflacao12Meses", [[x["Data"], x["Mediana"]] for x in v])


def tesouro():
    url = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
           "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv")
    txt = get(url, timeout=300).decode("latin-1")
    rows = list(csv.reader(io.StringIO(txt), delimiter=";"))
    hdr, rows = rows[0], rows[1:]
    out = []
    for r in rows:
        try:
            tipo, venc, dbase, tx_compra = r[0], r[1], r[2], float(r[3].replace(",", "."))
        except Exception:
            continue
        if tipo in ("Tesouro IPCA+", "Tesouro Prefixado"):
            d, m, y = dbase.split("/")
            dv, mv, yv = venc.split("/")
            out.append([f"{y}-{m}-{d}", tipo, f"{yv}-{mv}-{dv}", tx_compra])
    salvar("tesouro_direto", "Tesouro Transparente — Taxas dos títulos ofertados pelo Tesouro Direto (taxa de compra, % a.a.)",
           url, out, {"colunas": ["data_base", "titulo", "vencimento", "taxa_compra"], "cabecalho_original": hdr})
    ult = max(r[0] for r in out)
    salvar("tesouro_resumo", "Tesouro Transparente — Taxas dos títulos ofertados pelo Tesouro Direto (taxa de compra, % a.a.) — extrato da última data-base",
           url, [r for r in out if r[0] == ult], {"colunas": ["data_base", "titulo", "vencimento", "taxa_compra"]})


if __name__ == "__main__":
    so = set(sys.argv[1:])
    passos = [
        lambda: sgs(1, "usdbrl_ptax", "Dólar americano (venda), PTAX, R$/US$", 1999),
        lambda: sgs(432, "selic_meta", "Meta Selic definida pelo Copom, % a.a.", 1999),
        lambda: sgs(13522, "ipca_12m", "IPCA acumulado em 12 meses, %", 1999),
        lambda: sgs(13762, "dbgg_pib", "Dívida bruta do governo geral, % do PIB", 2006),
        lambda: sgs(5793, "primario_12m_pib", "NFSP sem desvalorização cambial, resultado primário, setor público consolidado, 12 meses, % do PIB (positivo = déficit)", 2002),
        lambda: sgs(13961, "fluxo_cambial", "Fluxo cambial contratado, total, diário, US$ milhões", 2008),
        lambda: fred("DTWEXBGS", "dolar_amplo", "Nominal Broad U.S. Dollar Index (proxy público do DXY)"),
        lambda: fred("DFF", "fed_funds", "Federal Funds Effective Rate, % a.a."),
        lambda: fred("VIXCLS", "vix", "CBOE Volatility Index (VIX)"),
        lambda: fred("CBBTCUSD", "btc_coinbase_fred", "Coinbase Bitcoin, US$ (usado só antes de ago/2017)"),
        binance, coingecko, focus, tesouro,
    ]
    nomes = ["ptax", "selic", "ipca", "dbgg", "primario", "fluxo", "dolar", "fedfunds", "vix",
             "btcfred", "binance", "coingecko", "focus", "tesouro"]
    for n, p in zip(nomes, passos):
        if so and n not in so:
            continue
        try:
            p()
        except Exception as e:
            print(f"FALHA: {e}", file=sys.stderr)
