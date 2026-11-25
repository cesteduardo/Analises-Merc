"""Núcleo do modelo: carga das séries, GARCH-t, cópula t e simulação de Monte Carlo.

Convenção de sinal: trabalhamos com retornos na "direção ruim" para quem tem reais
ou bitcoin. x_fx = -log(USD/BRL_t / USD/BRL_{t-1}) é o retorno do real contra o
dólar; x_btc = log(BTC_t / BTC_{t-1}). Valores negativos são perdas nos dois casos,
e correlação positiva entre eles significa choques que derrubam real e BTC juntos.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import special, stats, optimize

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
HORIZ_DIAS = [30, 90, 180, 365]
HORIZ_PASSOS = {30: 21, 90: 63, 180: 126, 365: 252}  # dias úteis aproximados
H_MAX = 252


def serie(nome):
    d = json.loads((RAW / f"{nome}.json").read_text())
    s = pd.Series({pd.Timestamp(a): b for a, b in d["dados"]}).sort_index()
    return s, d


def btc_usd():
    """Binance a partir de 17/08/2017; antes disso, Coinbase via FRED, só depois
    da abertura da bolsa da Coinbase (26/01/2015). Antes dessa data a série do
    FRED tem lacunas e cotações isoladas (ex.: US$ 120 em 14/01/2015)."""
    bn, _ = serie("btc_binance")
    cb, _ = serie("btc_coinbase_fred")
    cb = cb[cb.index >= "2015-01-26"]
    corte = bn.index[0]
    return pd.concat([cb[cb.index < corte], bn]).sort_index()


def base_diaria():
    fx, _ = serie("usdbrl_ptax")
    btc = btc_usd()
    # BTC alinhado às datas da PTAX: fechamento do mesmo dia (UTC).
    btc_al = btc.reindex(fx.index, method="ffill")
    df = pd.DataFrame({"fx": fx, "btc": btc_al}).dropna()
    return df


def retornos(df):
    r = pd.DataFrame({
        "x_fx": -np.log(df["fx"]).diff(),
        "x_btc": np.log(df["btc"]).diff(),
    }).dropna()
    return r


class Garch:
    """GJR-GARCH(1,1) com inovações t de Student, ajustado sobre x (direção ruim),
    por máxima verossimilhança com *variance targeting*.

    - A assimetria (gamma) amplia a volatilidade depois de quedas: desvalorização
      do real ou queda do BTC.
    - omega é fixado para que a variância incondicional seja a variância amostral
      da janela de alvo (por padrão, a janela de ajuste inteira).
    - Persistência limitada a PERSIST_MAX para evitar volatilidade integrada, que
      faria o cone explodir sem base empírica.
    """
    PERSIST_MAX = 0.99

    def __init__(self, x, media="zero", alvo_var=None):
        x = np.asarray(x, dtype=float)
        self.x = x
        self.mu = 0.0 if media == "zero" else float(np.mean(x))
        e = x - self.mu
        self.var_alvo = float(np.var(e) if alvo_var is None else alvo_var)
        s2_ini = float(np.var(e[:250]))

        def nll(th):
            a, gm, b, nu = th
            pers = a + gm / 2 + b
            if pers >= self.PERSIST_MAX or a + gm < 0:
                return 1e10
            om = self.var_alvo * (1 - pers)
            s2 = np.empty(len(e))
            s2[0] = s2_ini
            for t in range(1, len(e)):
                s2[t] = om + (a + gm * (e[t - 1] < 0)) * e[t - 1] ** 2 + b * s2[t - 1]
            # densidade t com variância s2 (t padronizada)
            ll = (special.gammaln((nu + 1) / 2) - special.gammaln(nu / 2)
                  - 0.5 * np.log(np.pi * (nu - 2)) - 0.5 * np.log(s2)
                  - (nu + 1) / 2 * np.log1p(e * e / ((nu - 2) * s2)))
            return -ll.sum()

        best = None
        for x0 in ([0.06, 0.04, 0.85, 6.0], [0.1, 0.0, 0.85, 4.0], [0.04, 0.02, 0.92, 8.0]):
            r = optimize.minimize(nll, x0, method="L-BFGS-B",
                                  bounds=[(0.005, 0.35), (-0.2, 0.35), (0.3, 0.985), (2.2, 60)])
            if best is None or r.fun < best.fun:
                best = r
        self.alpha, self.gamma, self.beta, self.nu = map(float, best.x)
        self.omega = self.var_alvo * (1 - self.alpha - self.gamma / 2 - self.beta)
        self.loglik = -float(best.fun)

    def params(self):
        pers = self.alpha + self.gamma / 2 + self.beta
        return dict(mu=self.mu, omega=self.omega, alpha=self.alpha, gamma=self.gamma,
                    beta=self.beta, nu=self.nu, persistencia=pers,
                    meia_vida_dias=float(np.log(0.5) / np.log(pers)),
                    vol_anual_incond=float(np.sqrt(252 * self.var_alvo)))

    def filtrar(self, x):
        """Variância condicional ao longo de x com parâmetros congelados. Devolve a
        série de sigma2 e a variância prevista para o passo seguinte."""
        x = np.asarray(x, dtype=float)
        s2 = np.empty(len(x) + 1)
        s2[0] = np.var(x[:250]) if len(x) > 250 else np.var(x)
        for t in range(len(x)):
            e = x[t] - self.mu
            s2[t + 1] = self.omega + (self.alpha + self.gamma * (e < 0)) * e * e + self.beta * s2[t]
        return s2[:-1], s2[-1]


def residuos_padronizados(g, x):
    s2, _ = g.filtrar(x)
    return (np.asarray(x) - g.mu) / np.sqrt(s2)


def t_padronizada_ppf(u, nu):
    """Quantil de uma t com variância unitária."""
    return special.stdtrit(nu, u) * np.sqrt((nu - 2) / nu)


def ajustar_nu_copula(z1, z2, rho):
    """Graus de liberdade da cópula t por máxima verossimilhança, com rho fixo."""
    u = np.column_stack([stats.rankdata(z1) / (len(z1) + 1), stats.rankdata(z2) / (len(z2) + 1)])

    def nll(nu):
        q = special.stdtrit(nu, u)
        R = np.array([[1, rho], [rho, 1]])
        ld = stats.multivariate_t(loc=[0, 0], shape=R, df=nu).logpdf(q)
        lm = stats.t(nu).logpdf(q).sum(axis=1)
        return -(ld - lm).sum()

    r = optimize.minimize_scalar(nll, bounds=(2.5, 60), method="bounded")
    return float(r.x)


def inovacoes(n, h, rho, nu_c, nu1, nu2, rng):
    """Inovações padronizadas conjuntas via cópula t: dependência de cauda real,
    marginais t com os graus de liberdade de cada GARCH."""
    g = np.sqrt(nu_c / rng.chisquare(nu_c, size=(n, h)))
    a = rng.standard_normal((n, h))
    b = rho * a + np.sqrt(1 - rho * rho) * rng.standard_normal((n, h))
    u1 = special.stdtr(nu_c, a * g)
    u2 = special.stdtr(nu_c, b * g)
    u1 = np.clip(u1, 1e-12, 1 - 1e-12)
    u2 = np.clip(u2, 1e-12, 1 - 1e-12)
    return t_padronizada_ppf(u1, nu1), t_padronizada_ppf(u2, nu2)


def simular_garch(g, s2_0, eps, mu=None):
    """Trajetórias de retornos (n, h) a partir da variância inicial s2_0.
    mu pode ser escalar ou vetor (h,) de deriva diária."""
    n, h = eps.shape
    mu = g.mu if mu is None else mu
    mu = np.broadcast_to(np.asarray(mu, dtype=float), (h,))
    x = np.empty((n, h))
    s2 = np.full(n, s2_0)
    for t in range(h):
        e = np.sqrt(s2) * eps[:, t]
        x[:, t] = mu[t] + e
        s2 = g.omega + (g.alpha + g.gamma * (e < 0)) * e * e + g.beta * s2
    return x


def drawdown_max(log_caminho):
    """Maior queda desde o pico, na direção ruim, para caminhos (n, h) de log-nível
    acumulado que começam em 0."""
    lv = np.concatenate([np.zeros((log_caminho.shape[0], 1)), log_caminho], axis=1)
    pico = np.maximum.accumulate(lv, axis=1)
    return 1 - np.exp((lv - pico).min(axis=1))


def drawdown_ate(log_caminho, passos):
    lv = np.concatenate([np.zeros((log_caminho.shape[0], 1)), log_caminho], axis=1)
    pico = np.maximum.accumulate(lv, axis=1)
    dd = 1 - np.exp(lv - pico)
    dd_acum = np.maximum.accumulate(dd, axis=1)
    return {k: dd_acum[:, p] for k, p in passos.items()}


def _episodios(acc, lim, separacao):
    cand = acc[acc < lim].sort_values()
    ep = []
    for i in cand.index:
        if all(abs(i - j) >= separacao for j in ep):
            ep.append(i)
    return ep


def estimar_crise(x, janela=21, q=0.025, separacao=126, g=None, seed=7):
    """Camada de crise estimada só com dados históricos da janela de ajuste.

    Episódio = mínimo local do retorno acumulado em `janela` dias abaixo do
    quantil q, com pelo menos `separacao` dias entre episódios. Devolve a taxa
    anual de episódios, a severidade mediana (retorno acumulado no episódio,
    direção ruim) e a variância diária típica dentro dos episódios.
    """
    x = pd.Series(np.asarray(x, dtype=float))
    acc = x.rolling(janela).sum()
    lim = acc.quantile(q)
    eps_fim = _episodios(acc, lim, separacao)
    sev = [float(acc[i]) for i in eps_fim]
    # Fração do choque devolvida nos 126 dias úteis seguintes (mediana histórica).
    R = 126
    devol = [float(x[i + 1:i + 1 + R].sum()) / -float(acc[i]) for i in eps_fim if i + R < len(x)]
    frac_devol = float(np.clip(np.median(devol), 0, 1)) if devol else 0.0
    var = [float((x[i - janela + 1:i + 1] ** 2).mean()) for i in eps_fim]
    anos = len(x) / 252
    taxa_obs = len(eps_fim) / anos
    # Taxa que o GARCH-t sozinho já gera (400 anos simulados com os mesmos
    # parâmetros). A camada de crise só acrescenta o excesso observado.
    taxa_mod = 0.0
    if g is not None:
        rng = np.random.default_rng(seed)
        T = 252 * 400
        e = t_padronizada_ppf(np.clip(rng.random((1, T)), 1e-12, 1 - 1e-12), g.nu)
        sim = pd.Series(simular_garch(g, g.var_alvo, e, 0.0)[0]).rolling(janela).sum()
        taxa_mod = len(_episodios(sim, lim, separacao)) / 400
    return dict(taxa_anual=max(0.0, taxa_obs - taxa_mod), taxa_observada=taxa_obs,
                taxa_garch=taxa_mod, severidade=float(np.median(sev)),
                var_diaria=float(np.median(var)), n_episodios=len(eps_fim), janela=janela,
                limiar=float(lim), frac_devolvida=frac_devol, dias_devolucao=R,
                episodios=[int(i) for i in eps_fim])


def simular_com_crise(g, s2_0, eps, mu, crise, rng, ativo=True):
    """GARCH-t com uma camada de crise: em cada trajetória, o início de uma crise
    chega como processo de Poisson (taxa anual estimada). Ao começar, a variância
    salta para o nível típico das crises históricas e, por `janela` dias, a
    trajetória recebe a deriva da severidade mediana histórica."""
    n, h = eps.shape
    mu = np.broadcast_to(np.asarray(mu, dtype=float), (h,))
    if not ativo or crise is None or crise["taxa_anual"] <= 0:
        return simular_garch(g, s2_0, eps, mu)
    p_dia = 1 - np.exp(-crise["taxa_anual"] / 252)
    inicio = rng.geometric(p_dia, size=n) - 1  # passo de início (pode passar de h)
    J = crise["janela"]
    d = crise["severidade"] / J
    R = crise.get("dias_devolucao", 126)
    dv = -crise["severidade"] * crise.get("frac_devolvida", 0.0) / R
    x = np.empty((n, h))
    s2 = np.full(n, s2_0)
    for t in range(h):
        em = (t >= inicio) & (t < inicio + J)
        dev = (t >= inicio + J) & (t < inicio + J + R)
        comeca = t == inicio
        s2 = np.where(comeca, np.maximum(s2, crise["var_diaria"]), s2)
        e = np.sqrt(s2) * eps[:, t]
        x[:, t] = mu[t] + e + np.where(em, d, 0.0) + np.where(dev, dv, 0.0)
        s2 = g.omega + (g.alpha + g.gamma * (e < 0)) * e * e + g.beta * s2
    return x
