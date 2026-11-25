# Metodologia do Painel Merc

> **Aviso.** Este painel é um estudo de risco. Não é recomendação de investimento, não diz o que vai acontecer e não sugere compra nem venda de nenhum ativo.

## 1. O que o painel responde

Quão ruim pode ficar, em 30, 90, 180 e 365 dias, o preço do dólar em reais (USD/BRL), do bitcoin em dólar (BTC/USD) e do bitcoin em reais (BTC/BRL), dentro do que é plausível pela história recente. A pergunta é sobre a cauda ruim, não sobre o cenário mais provável.

**"Ruim" tem direção fixa.** Para USD/BRL, ruim é o dólar mais caro (o real perdendo valor). Para BTC/USD e BTC/BRL, ruim é o preço mais baixo. Choques correlacionados, em que uma aversão a risco global derruba o real e o bitcoin juntos, são tratados explicitamente.

## 2. Como ler os números

Toda saída é uma distribuição, nunca um valor único.

| Rótulo | Significado | USD/BRL | BTC/USD e BTC/BRL |
|---|---|---|---|
| P50 | mediana | percentil 50 | percentil 50 |
| P10 | 10% das trajetórias terminam pior | percentil 90 | percentil 10 |
| P5 | 5% terminam pior | percentil 95 | percentil 5 |
| P1 | 1% termina pior (cauda ruim) | percentil 99 | percentil 1 |
| P90 | lado favorável, só como referência | percentil 10 | percentil 90 |

O **pior caso plausível** do painel é o P1 da distribuição-base em 365 dias: o nível que só 1 em cada 100 trajetórias ultrapassa **no fim** do horizonte. Cada P1 é marginal, medido para um ativo de cada vez; o painel informa à parte a probabilidade de os dois P1 acontecerem juntos na mesma trajetória e a de o P1 ser tocado em algum momento do caminho.

Os cenários de estresse respondem a outra pergunta: "e se um episódio real se repetisse a partir dos preços de hoje?". A mediana de cada estresse reproduz a queda máxima que o episódio teve (seção 5). Os P5 e P1 dos estresses somam esse episódio à volatilidade de hoje e ficam, por construção, além do pior movimento histórico de 12 meses; por isso não são chamados de plausíveis e não aparecem no resumo do topo.

O **drawdown máximo** é a maior queda desde o pico ao longo do caminho, até cada horizonte. Para USD/BRL, é a maior perda do real contra o dólar (queda máxima de BRL/USD). O mapa de calor mostra o P5 (a queda que só 1 em 20 trajetórias ultrapassa) e, menor, a mediana.

## 3. Dados

Só fontes públicas. Cada série é gravada com URL e data e hora de coleta (`data/raw/*.json`); o painel lista todas na seção "Fontes e datas de coleta".

| Uso | Série | Fonte |
|---|---|---|
| Câmbio | Dólar (venda), PTAX, diário, desde 1999 | BCB/SGS 1 |
| BTC/USD | BTCUSDT, fechamento diário UTC, desde 17/08/2017 | Binance (`data-api.binance.vision`) |
| BTC/USD antes de 17/08/2017 | Coinbase Bitcoin, desde 26/01/2015 | FRED CBBTCUSD |
| Conferência do preço à vista | BTC em USD e BRL | CoinGecko |
| Selic | Meta Selic | BCB/SGS 432 |
| Inflação esperada | IPCA esperado 12 meses à frente (suavizado) | BCB/Focus |
| Expectativas anuais | Câmbio, IPCA, Selic, primário, dívida bruta | BCB/Focus |
| Juro real de mercado | Tesouro IPCA+ (NTN-B) e Prefixado, taxa de compra | Tesouro Transparente |
| Risco fiscal | Dívida bruta do governo geral (% PIB); primário 12 meses (% PIB) | BCB/SGS 13762 e 5793 |
| Fluxo cambial | Fluxo contratado, total, diário | BCB/SGS 13961 |
| Dólar global | Índice amplo nominal do dólar | FRED DTWEXBGS |
| Juros americanos | Fed Funds efetivo | FRED DFF |
| Aversão a risco | VIX | FRED VIXCLS |

**Decisões sobre os dados (premissas):**

- O **DXY** da ICE não é publicado no FRED. Usamos o índice amplo do Fed (DTWEXBGS) como proxy público.
- A série da Coinbase no FRED tem lacunas e cotações isoladas antes da abertura da bolsa da Coinbase (por exemplo, US$ 120 em 14/01/2015). Por isso o BTC começa em 26/01/2015.
- O BTC é alinhado às datas da PTAX: em cada dia útil brasileiro usamos o fechamento UTC do mesmo dia. O retorno de segunda-feira inclui o fim de semana. A PTAX é formada por volta das 13h de Brasília, então há algumas horas de defasagem entre as duas séries, o que tende a atenuar a correlação medida.
- O **fluxo de ETFs de BTC** está na lista de gatilhos, mas nenhuma das fontes autorizadas o publica. Ele aparece como "sem dado" e não entra no modelo.
- O **halving** é estimado por cálculo próprio (bloco 1.050.000, a 10 minutos por bloco desde o halving de 20/04/2024), sem série externa. Cai fora da janela de 365 dias e não entra no modelo.

## 4. Modelo-base

### 4.1 Retornos na direção ruim

Trabalhamos com dois retornos diários, ambos com sinal tal que negativo é perda:

- câmbio: `x_fx = −ln(USD/BRL_t / USD/BRL_{t−1})`, o retorno do real contra o dólar;
- bitcoin: `x_btc = ln(BTC_t / BTC_{t−1})`.

### 4.2 Volatilidade: GJR-GARCH(1,1) com t de Student

Para cada ativo:

`σ²_t = ω + (α + γ·1[ε_{t−1} < 0]) · ε²_{t−1} + β · σ²_{t−1}`,   `ε_t = σ_t · z_t`,   `z_t ~ t de Student padronizada (ν)`.

- O termo γ dá **assimetria**: choques ruins (real caindo, BTC caindo) elevam mais a volatilidade seguinte.
- Estimação por máxima verossimilhança com *variance targeting*: ω é fixado para que a variância de longo prazo seja a variância amostral da janela de estimação.
- A persistência α + γ/2 + β é limitada a 0,99 para evitar volatilidade integrada, que faria o cone explodir sem base empírica.
- Amostras: câmbio desde 2003 (inclui 2008, 2013, 2015, 2018, 2020 e 2024); BTC desde 26/01/2015.

### 4.3 Deriva do câmbio condicionada ao juro real

O BTC não tem deriva. Para o câmbio, a deriva diária depende do juro real ex-post (Selic meta deflacionada pelo IPCA acumulado em 12 meses, com o IPCA de cada mês usado só a partir do dia 15 do mês seguinte, quando já foi divulgado):

`retorno do real nos 63 dias úteis seguintes = a + b · juro real ex-post + erro`, estimado por MQO com erros de Newey-West, desde 2003, só com janelas que terminam antes da data de corte.

- Amostra completa: a ≈ −0,029, b ≈ 0,0046 (t ≈ 2,7). O juro real neutro, em que a deriva é zero, fica perto de 6,3%.
- Com o juro real de hoje, acima do neutro, a mediana do dólar recua cerca de 4% ao ano antes da camada de crise.
- Usamos o ex-post porque o Focus de 12 meses coletado só começa em 2014 e o ajuste começa em 2003. O gatilho "Selic real" do painel mostra a versão ex-ante, mais intuitiva.
- Testamos também deriva zero, o carrego (Selic − Fed Funds) e tendências passadas (ver `relatorios/CALIBRACAO.md`). A deriva pelo juro real foi a que melhor calibrou, mas foi **escolhida olhando o backtest**, o que é uma forma branda de sobreajuste.
- Referências mostradas no painel, que não entram no modelo: o forward de 1 ano pelo diferencial Selic − Fed Funds (embute carrego, não expectativa) e a mediana do Focus para o câmbio no fim do ano corrente e do próximo.

### 4.4 Camada de crise

O GARCH-t subestima episódios em que a perda se acumula por semanas. A camada de crise acrescenta, a cada trajetória, a chance de uma crise começar:

1. **Episódios históricos**: janelas de 21 dias úteis cujo retorno acumulado está entre os 2,5% piores da amostra, separadas por pelo menos 126 dias úteis.
2. **Taxa extra**: simulamos 400 anos com o próprio GARCH-t e contamos quantos episódios ele já gera com o mesmo critério. A camada só acrescenta a diferença entre a taxa observada e a do modelo, para não contar a cauda duas vezes.
3. **Dinâmica**: a crise chega como processo de Poisson. Ao começar, a variância salta para o nível mediano das crises históricas e, por 21 dias, a trajetória recebe a deriva do choque mediano histórico. Nos 126 dias seguintes, devolve a fração mediana historicamente devolvida.

Os valores estimados (taxa extra por ano, choque mediano, fração devolvida) aparecem no painel, na seção de premissas. A camada só empurra para o lado ruim: o painel mostra quanto ela desloca a mediana de 365 dias, comparando a mesma simulação com e sem ela. **Ela não entra nos cenários de estresse**, que já são crises por construção.

### 4.5 Correlação e cópula

Os choques padronizados dos dois ativos são ligados por uma **cópula t**, que permite caudas conjuntas (os dois piores dias acontecendo juntos):

- correlação: a dos últimos 250 dias úteis entre os resíduos padronizados do câmbio e do BTC;
- graus de liberdade da cópula: estimados por máxima verossimilhança. Na amostra completa o estimador vai ao limite superior (60), o que equivale a uma cópula quase gaussiana: os dados não mostram dependência de cauda forte no dia a dia.
- **Nos estresses**, a correlação sobe para o maior valor entre a do episódio e o percentil 95 histórico da correlação móvel de 63 dias, e a cópula passa a ter 4 graus de liberdade. Essa é uma piora deliberada (premissa), não uma estimativa.

### 4.6 BTC/BRL

Nunca é projetado sozinho. Em cada trajetória simulada, `BTC/BRL = BTC/USD × USD/BRL`. Assim, um choque que derruba o real atenua a queda do BTC em reais, e um choque que derruba os dois ao mesmo tempo aparece com a força correta.

### 4.7 Simulação

20.000 trajetórias de 252 dias úteis, semente fixa. Os horizontes de 30, 90, 180 e 365 dias corridos são lidos nos passos 21, 63, 126 e 252. As datas exibidas seguem o calendário da PTAX: sem fins de semana e sem feriados nacionais (fixos, Carnaval, Sexta-feira Santa, Corpus Christi e, desde 2024, 20 de novembro), conferido contra os dias úteis ausentes da série em 2024 e 2025. Por isso o passo 252 cai alguns dias depois de um ano corrido.

**Volatilidade de partida.** A largura do cone depende da volatilidade condicional de hoje, que o GARCH faz voltar à média de longo prazo ao longo do horizonte. O painel mostra as duas, por ativo.

## 5. Cenários de estresse

Cada cenário é uma distribuição condicional: "se as condições do episódio se repetissem a partir dos preços de hoje".

**Regra comum (premissas):**

- **Pior ponto conjunto**: para os episódios reconstruídos, localizamos o pior ponto de cada ativo dentro de 252 dias úteis e usamos o mais tardio dos dois (T\*). Os dois ativos seguem a trajetória histórica dia a dia **até a mesma data T\*** e ficam parados depois. Assim o BTC/BRL do cenário corresponde a um momento que de fato existiu. **A recuperação depois do pior ponto não é assumida.**
- **Sem dupla contagem**: a trajetória histórica já contém a volatilidade do episódio. Por isso não somamos a ela a volatilidade realizada inteira. O cenário é `m · trajetória histórica + λ · ruído`, em que o ruído vem do GARCH-t-base partindo da volatilidade de hoje, sem a camada de crise:
  1. com λ = 1, escolhemos m entre 0 e 1 (bisseção) para que a **mediana do drawdown máximo em 365 dias seja igual ao drawdown histórico do episódio**;
  2. se a volatilidade de hoje, sozinha, já gera drawdown mediano maior que o histórico (caso do BTC em 2015), a trajetória sai (m = 0) e λ é reduzido até a mediana bater.
  Os valores de m e λ de cada cenário aparecem nas premissas do cartão. O BTC/BRL não é calibrado: sai do produto das duas trajetórias, e o painel mostra ao lado o drawdown histórico dele.
- **Correlação**: a maior entre a do episódio (até T\*, pelo menos 63 dias) e o percentil 95 histórico da correlação móvel de 63 dias; cópula t com 4 graus de liberdade.
- **Caudas**: P5 e P1 de um estresse somam o episódio à volatilidade de hoje. Eles ficam além do pior movimento histórico de 12 meses de cada ativo, que o painel mostra como âncora, e por isso não são chamados de plausíveis.
- **Ordem**: do mais severo ao menos severo pelo drawdown mediano em 365 dias **do ativo selecionado**.

| Cenário | Tipo | Início | Base |
|---|---|---|---|
| Crise fiscal, 2015 | reconstruído | 26/01/2015 | PTAX e BTC reais. O início é o primeiro dia com BTC confiável; o real já vinha se depreciando. |
| Covid, mar/2020 | reconstruído | 14/02/2020 | Véspera do choque global de liquidez. |
| Inverno cripto, 2022 | reconstruído | 10/11/2021 | Máxima histórica do BTC antes da queda de 2022. |
| Fiscal e eleitoral, 2026–27 | **construído** | hoje | Câmbio segue a média diária, com peso de 1/3 cada, de três episódios domésticos: eleição de 2002 (desde 01/04/2002), crise fiscal de 2015 (desde 02/01/2015) e pacote fiscal de 2024 (desde 30/09/2024), até o pior ponto dessa média. O alvo da mediana do drawdown é a média dos drawdowns dos três. BTC sem trajetória própria (m = 0, λ = 1, volatilidade condicional de hoje); o contágio vem só da correlação, que parte da de hoje e sobe ao piso de estresse. |

O cenário 2026–27 é uma **hipótese**, não uma reconstrução. Ele não afirma nada sobre o resultado da eleição; descreve uma transição com dúvida sobre o arcabouço fiscal.

**"O que precisaria acontecer"**: para cada cenário, o painel lista só as condições que foram gatilho no episódio, isto é, que ficaram em atenção ou alerta pelas mesmas regras da seção 6. Para cada uma mostra o valor no episódio, o valor de hoje e a situação:

- **presente**: hoje o status é igual ou pior que o do episódio;
- **próxima**: hoje está em atenção e o episódio esteve em alerta;
- **distante**: hoje está normal.

As janelas são iguais nos dois lados: no episódio, os 63 dias úteis a partir do início (o VIX é o pico nessa janela); hoje, os 63 dias úteis até a data-base. Fed Funds e dívida bruta usam 12 meses. No cenário construído, os valores são os dos três análogos, e conta o status mais adverso entre eles. Quebras no setor cripto (Terra/Luna, FTX) não têm série pública autorizada e aparecem como "sem dado".

## 6. Gatilhos monitorados

Cada gatilho tem uma regra explícita de status (normal, atenção, alerta). Os limiares são **premissas do painel**, escolhidas para marcar movimentos raros na história, e não fazem parte do modelo: eles informam, não alteram as projeções.

| Gatilho | Leitura | Atenção | Alerta | Entra no modelo? |
|---|---|---|---|---|
| Risco fiscal | variação da dívida bruta em 12 meses | > +1,5 p.p. | > +3 p.p. | não |
| Selic real | Selic meta deflacionada pelo IPCA esperado em 12 meses (ex-ante) | < 6% | < 4% | sim, na versão ex-post (seção 4.3) |
| Prêmio do Tesouro IPCA+ | taxa do Tesouro IPCA+ com vencimento mais próximo de 10 anos | > 6,5% | > 7,5% | não |
| Dólar global | variação do índice amplo em 63 dias úteis | > +2% | > +4% | não |
| Juros nos EUA | variação do Fed Funds em 12 meses | > +1 p.p. | > +2 p.p. | não |
| Fluxo cambial | soma de 63 dias úteis, percentil histórico desde 2008 | abaixo do percentil 25 | abaixo do percentil 10 | não |
| Aversão a risco | VIX | > 20 | > 30 | não |
| Halving | data estimada | informativo | — | não |
| ETFs de BTC | sem fonte autorizada: **lacuna da especificação** | sem dado | — | não |

## 7. Verificação

### 7.1 Backtest fora da amostra

- **Cortes**: parâmetros estimados só com dados até 31/12/2017 e até 31/12/2020, e congelados.
- **Origens**: a cada 5 dias úteis, de 2018 a 2020 (corte 2018) e de 2021 ao último dado com horizonte completo (corte 2021). Em cada origem, a volatilidade é filtrada com os dados até ali e a correlação usa os 250 dias anteriores.
- **Métrica**: frequência com que o realizado ficou pior que o P10. Meta: entre 8% e 12%.
- **Choques reais**: posição do realizado na distribuição projetada na véspera da Covid (14/02/2020), do inverno cripto (10/11/2021) e do pacote fiscal (30/09/2024). O critério é que o P5 contenha o choque.
- **Limitação**: as origens se sobrepõem, então o número de observações independentes é pequeno, sobretudo em 365 dias (cerca de 3 a 4 por corte). Painel e relatório trazem o intervalo de confiança de 95% de Wilson, calculado com o número aproximado de janelas independentes (`n × 5 / passos`).
- **Classificação**: "na meta" quando a frequência fica entre 8% e 12%; "inconclusivo" quando fica fora, mas o intervalo cruza a faixa; "risco subestimado" ou "pessimista demais" só quando o intervalo inteiro fica fora.

### 7.2 Estado atual da calibração

**A especificação ainda não está cumprida.** Resultados completos em `relatorios/CALIBRACAO.md`; resumo da variante em uso (deriva pelo juro real e camada de crise):

- **Por corte**: 8 de 24 combinações na meta; as outras 16 são inconclusivas, e nenhuma fica fora com significância. A amostra independente é pequena demais para confirmar ou rejeitar a calibração na maior parte das células.
- **Somando os dois cortes**: 9 de 12 na meta; BTC/USD em 30 e 365 dias e BTC/BRL em 180 dias ficam inconclusivos.
- No **corte 2018**, o modelo subestimou a desvalorização do real de 2018 a 2020 (15% a 20% das origens abaixo do P10 até 180 dias). No **corte 2021**, ficou pessimista demais em USD/BRL de 90 e 180 dias (3% a 5%).
- **Choques reais**: a Covid ficou além do P1 em 30 dias nos três ativos e em 90 dias no câmbio. O inverno cripto ficou entre o P5 e o P1 em BTC/USD (365 dias) e BTC/BRL (180 e 365 dias). O critério "o P5 contém os choques reais" não é atendido; esses episódios entram como estresses justamente porque a distribuição-base não os contém.

### 7.3 Crítico cego

Um revisor que vê apenas o painel publicado e este documento, nunca o código, aponta premissas ocultas, pessimismo exagerado ou fraco e gráficos que enganam. As revisões ficam em `relatorios/CRITICO.md`.

## 8. Limitações conhecidas

- **Mudança de regime**: o modelo não prevê mudanças persistentes de tendência (como 2018 a 2020 no câmbio). A camada de crise e os estresses compensam parte disso, não tudo.
- **Parâmetros estimados**: a incerteza de estimação dos parâmetros do GARCH não é propagada para as trajetórias.
- **Correlação**: a correlação medida entre real e BTC é baixa (cerca de 0,2) e instável; a defasagem de horário entre a PTAX e o fechamento do BTC tende a reduzi-la.
- **Dados de BTC antes de 2017** vêm de uma única corretora (Coinbase), com liquidez menor.
- **Gatilhos** não alimentam o modelo. Um gatilho em alerta não muda as faixas; ele indica que um dos estresses ficou mais relevante.
- **Escolhas guiadas pelo backtest**: a variante final foi escolhida olhando os resultados do teste, o que é uma forma branda de sobreajuste. Todas as variantes testadas estão registradas.

## 9. Como atualizar

```
pip install numpy pandas scipy statsmodels
python3 pipeline/coletar.py              # baixa as séries
python3 pipeline/backtest.py juro_real 0 crise  # backtest da variante em uso
python3 pipeline/projetar.py             # gera projections.json
python3 pipeline/relatorio.py            # gera relatorios/CALIBRACAO.md
```

O painel (`index.html`, `style.css`, `charts.js`) lê `projections.json` e não depende de servidor próprio.
