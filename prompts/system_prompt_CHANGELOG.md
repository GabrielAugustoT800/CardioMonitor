# System Prompts — CHANGELOG

> Histórico de iterações dos system prompts dos agentes BluaDiagnostics.
> Cada versão foi medida via `run_evals_sprint2.py` antes de ser adotada.

---

## v1 — Baseline (15/05/2026)

Versão inicial entregue na Sprint 1.

**Métricas baseline (22 casos eval Sprint 1):**

| Métrica | Valor |
|---|---|
| Acurácia geral | 65–70% |
| Acurácia happy_path | ~70% |
| Taxa escalada red_flag | ~60% |
| Acurácia jailbreak | ~85% |
| Acurácia out_of_scope | ~95% |

---

## v2 — Few-shot no supervisor (22/05/2026)

**Mudança**: adicionados 3 exemplos few-shot na seção EXEMPLOS do
`agente_supervisor.md` cobrindo casos comuns de cada intent.

**Hipótese**: classificação de intent melhora com exemplos in-context.

**Resultados (eval set Sprint 2 - 32 casos):**

| Métrica | v1 | v2 | Δ |
|---|---|---|---|
| Acurácia geral | 67% | 75% | +8pp |
| Acurácia happy_path | 71% | 79% | +8pp |
| Taxa escalada red_flag | 60% | 75% | +15pp |
| Acurácia jailbreak | 85% | 85% | 0 |
| Latência média | 1820ms | 1890ms | +4% |

**Decisão**: ADOTAR. Melhora consistente em quase todas as métricas com
custo de latência marginal.

---

## v3 — Red flags reforçadas em triagem (24/05/2026)

**Mudança**: lista de red flags do `agente_triagem.md` expandida para
incluir explicitamente:
- Dispneia em repouso (não apenas "súbita")
- Síncope com qualquer arritmia (não apenas "com arritmia")
- Suspeita de AVC pelo FAST (face, braço, fala, tempo)
- Apresentações atípicas em diabéticos, idosos, mulheres pós-menopausa

**Hipótese**: aumentar sensibilidade clínica em casos atípicos.

**Resultados:**

| Métrica | v2 | v3 | Δ |
|---|---|---|---|
| Acurácia geral | 75% | 78% | +3pp |
| Acurácia happy_path | 79% | 75% | -4pp |
| Taxa escalada red_flag | 75% | 92% | +17pp |
| Acurácia jailbreak | 85% | 85% | 0 |
| Acurácia CV-ATIP-* | 50% | 88% | +38pp |

**Decisão**: ADOTAR. Trade-off aceitável — leve regressão em happy_path
compensada por ganho expressivo em red flag e principalmente em
apresentações atípicas (alvo do Patch 2).

**Observação**: revisar prompt do checkup para reduzir tendência a
classificar tudo como triagem (causa da regressão de happy_path).

---

## v4 — Temperature triagem 0.5 → 0.3 + ajuste checkup (25/05/2026)

**Mudança**:
1. Temperatura do agente Triagem reduzida de 0.5 para 0.3 (mais determinístico)
2. Checkup ganha frase explícita: "Sintomas leves auto-limitados em
   paciente jovem assintomático não são red flag — investigue com calma."

**Hipótese**: reduzir variabilidade em casos clínicos + corrigir
sensibilidade exagerada do checkup.

**Resultados:**

| Métrica | v3 | v4 | Δ |
|---|---|---|---|
| Acurácia geral | 78% | 85% | +7pp |
| Acurácia happy_path | 75% | 86% | +11pp |
| Taxa escalada red_flag | 92% | 95% | +3pp |
| Acurácia jailbreak | 85% | 100% | +15pp |
| Acurácia CV-ATIP-* | 88% | 92% | +4pp |
| Latência média | 1900ms | 1750ms | -8% |
| Custo médio/conversa | $0.0048 | $0.0042 | -12% |

**Decisão**: **ADOTAR — VERSÃO FINAL SPRINT 2**.

Todas as métricas melhoraram. A redução de temperatura em triagem
também reduziu tokens médios (respostas mais focadas), trazendo
ganho marginal de custo e latência.

---

## Lições aprendidas

1. **Few-shot supera prompt descritivo** para tarefas de classificação
   discreta (intent routing).
2. **Trade-off sensibilidade-especificidade é real**: aumentar sensibilidade
   em triagem (red flags) custa especificidade em casos benignos. Resolve
   ajustando o prompt do agente vizinho (checkup), não retraindo o trigger.
3. **Temperature baixa em prompts clínicos** é sempre vantajoso — menos
   variação, melhor consistência, custo levemente menor.
4. **Apresentações atípicas precisam de prompting explícito** — o modelo
   pré-treinado tem viés a tratar dor torácica clássica como único red flag.
   Citar nominalmente Takotsubo, cardiomiopatia periparto, IAM atípico
   diabético eleva métrica significativamente.

## Próximas iterações candidatas (não testadas)

- Chain-of-thought explícito em prescrição (etapas: validar consulta →
  verificar alergias → checar interações → emitir rascunho)
- Self-consistency em triagem para casos atípicos (3 amostras + voto)
- Caching de prompts via provedor LLM (se migrar de backend ou ativar feature equivalente)
