"""Variantes do modelo testadas no backtest. Todas ficam registradas no
relatório de calibração, inclusive as descartadas, para que a escolha final
possa ser auditada."""

BASE = dict(fx_ini="2003-01-01", deriva_fx="zero", btc_alvo_anos=None, crise=False,
            deriva_incerta_fx=False, deriva_incerta_btc=False, recal=False)

VARIANTES = {
    # ---- v1 (registradas na primeira rodada) ----
    "zero_tudo": dict(BASE, nome="Deriva zero, sem camada de crise", rodada=1),
    "carry_tudo": dict(BASE, deriva_fx="carry", nome="Deriva do diferencial de juros (Selic − Fed Funds), sem camada de crise", rodada=1),
    "zero_tudo_crise": dict(BASE, crise=True, nome="Deriva zero + camada de crise (escolhida na v1)", rodada=1),
    "carry_tudo_crise": dict(BASE, deriva_fx="carry", crise=True, nome="Deriva do diferencial de juros + camada de crise", rodada=1),
    # ---- v2 ----
    "v2_1999_crise": dict(BASE, fx_ini="1999-03-01", crise=True,
                          nome="Câmbio desde o início do câmbio flutuante (mar/1999) + camada de crise", rodada=2),
    "v2_1999_crise_tend": dict(BASE, fx_ini="1999-03-01", crise=True, deriva_incerta_fx=True,
                               nome="Câmbio desde mar/1999 + camada de crise + incerteza de tendência no câmbio", rodada=2),
    "v2_2003_crise_tend": dict(BASE, crise=True, deriva_incerta_fx=True,
                               nome="Câmbio desde 2003 + camada de crise + incerteza de tendência no câmbio", rodada=2),
    "v2_1999_crise_tend2": dict(BASE, fx_ini="1999-03-01", crise=True, deriva_incerta_fx=True, deriva_incerta_btc=True,
                                nome="Câmbio desde mar/1999 + camada de crise + incerteza de tendência nos dois ativos", rodada=2),
    # ---- v3: recalibração de quantis estimada dentro da amostra ----
    "v3_1999_crise_tend_recal": dict(BASE, fx_ini="1999-03-01", crise=True, deriva_incerta_fx=True, recal=True,
                                     nome="v2 (1999 + crise + tendência no câmbio) + recalibração de quantis dentro da amostra", rodada=3),
    "v3_1999_crise_recal": dict(BASE, fx_ini="1999-03-01", crise=True, recal=True,
                                nome="Câmbio desde 1999 + crise + recalibração de quantis dentro da amostra", rodada=3),
    "v3_2003_crise_recal": dict(BASE, crise=True, recal=True,
                                nome="v1 (2003 + crise) + recalibração de quantis dentro da amostra", rodada=3),
}
