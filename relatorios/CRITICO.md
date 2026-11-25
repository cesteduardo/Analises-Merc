# Revisão do crítico cego

O crítico é um subagente que vê só o painel renderizado (texto e capturas em desktop, 360 px e 390 px, claro e escuro) e o METODOLOGIA.md. Não vê código, dados brutos nem a conversa. Critério de aprovação: nenhum defeito acima de "menor".

| Rodada | Versão | Veredito | Defeitos acima de "menor" |
|---|---|---|---|
| 1 | v1 | REPROVADO | 21 apontamentos, vários maiores (tratados na v2) |
| 2 | v2, primeira prévia | REPROVADO | 13 apontamentos |
| 3 | v2 com correções da rodada 2 | REPROVADO | 1 maior: o painel chamava de "premissa pessimista" a soma dos piores pontos, que no BTC/BRL é mais branda que o episódio |
| 4 | v2 com correções da rodada 3 | **APROVADO** | nenhum |

## Rodada 4 (final): APROVADO

Os sete apontamentos da rodada 3 foram resolvidos:

1. **Combinação dos piores pontos no BTC/BRL.** A frase "premissa pessimista deliberada" saiu dos cartões, do bloco "Como os estresses são montados" e da METODOLOGIA. O painel agora diz que somar os dois piores pontos é pessimista para USD/BRL e BTC/USD isolados e mais brando no BTC/BRL, e mostra os dois números lado a lado (2015: +24% contra −17%; Covid: −36% contra −48%; 2022: −74% contra −77%). A escolha de manter BTC/BRL = BTC/USD × USD/BRL está declarada.
2. **Selic real de 2015.** O Focus de IPCA 12 meses começa em 2014, então 2015 é ex-ante de fato; só 2002 aparece como ex-post.
3. **Legenda do P1 do estresse.** Muda conforme o caso e bate com o rodapé ("mais brando que o P1 da base", "além do pior histórico, fora do plausível", "dentro do pior histórico").
4. **Duas medidas de queda.** "Queda desde o pico" e "pior nível contra o início" são nomeadas; há aviso quando a queda-alvo vem depois do ponto de parada (USD/BRL 2022) e quando as medidas diferem (BTC/BRL 2015).
5. **"Com confiança estatística"** foi trocado por "com intervalo estreito (menos de 15 p.p.)".
6. **Números entre parênteses no resumo** viraram texto explícito.
7. **Frase do BTC/BRL no resumo** foi corrigida e cita os números exibidos.

Defeito menor restante, corrigido depois da aprovação: terminologia antiga ("queda mediana no caminho" no rodapé do cone e "No pior ponto dos análogos" no cartão 2026–27), unificada para "queda mediana desde o pico" e "pior nível contra o início (média dos análogos)".

Sem regressão nas capturas de 360 e 390 px, claro e escuro.

## O que a aprovação não significa

A aprovação do crítico cobre honestidade, clareza e coerência entre painel e metodologia. **Ela não diz que o modelo está calibrado.** A especificação de calibração continua não cumprida, e o painel declara isso no topo: por corte, 2 de 24 combinações na meta com intervalo estreito, 6 na faixa sem poder estatístico, 16 inconclusivas, 0 fora com significância; o P5 não conteve a Covid (USD/BRL em 30 e 90 dias, BTC em 30 dias) nem o inverno cripto (BTC/USD em 365 dias, BTC/BRL em 180 e 365 dias). Ver [CALIBRACAO.md](CALIBRACAO.md).
