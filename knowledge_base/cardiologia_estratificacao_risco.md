# Estratificação de risco cardiovascular — referência clínica

> Documento de referência para o agente de Triagem do BluaDiagnostics.
> **Não é guideline oficial** — versão simplificada para apoio de
> triagem em telessaúde. Em produção, substituir por implementação
> validada e auditada por cardiologia clínica.

## Quando estratificar

Sempre que o paciente apresentar sintomas com diferencial cardiovascular
plausível: dor/desconforto torácico, dispneia, síncope, pré-síncope,
palpitações, fadiga desproporcional ou dor epigástrica em paciente com
fatores de risco.

## Fatores de risco cardiovascular (FRCV)

**Não modificáveis**:
- Idade: ≥45 anos (homens) / ≥55 anos (mulheres).
- Sexo masculino.
- História familiar de doença coronariana precoce (IAM/AVC em parente
  de primeiro grau antes dos 55a homens / 65a mulheres).

**Modificáveis**:
- Hipertensão arterial sistêmica (PAS ≥140 ou PAD ≥90, ou em
  tratamento).
- Diabetes mellitus.
- Dislipidemia (LDL elevado, HDL baixo, hipertrigliceridemia).
- Tabagismo atual ou recente (< 1 ano).
- Obesidade (IMC ≥30) e sedentarismo.
- Doença renal crônica.

**Equivalentes de DAC** (paciente de alto risco mesmo sem evento prévio):
- Diabetes com lesão de órgão-alvo.
- Doença arterial periférica.
- AVC isquêmico prévio.
- DRC com TFG <60.

## Score HEART simplificado (para triagem telefônica/digital)

Adaptado do HEART score original para uso pré-hospitalar **sem ECG nem
troponina**. Apenas a parte H+A+R+S é computável remotamente.

| Componente | 0 pontos | 1 ponto | 2 pontos |
|---|---|---|---|
| **H** — História/quadro clínico | Pouco suspeito (atípico, reproduzível) | Moderadamente suspeito (mista) | Altamente suspeito (típico, em esforço) |
| **A** — Idade | <45 anos | 45–64 anos | ≥65 anos |
| **R** — Fatores de risco | Nenhum | 1–2 FRCV | ≥3 FRCV ou doença aterosclerótica conhecida |
| **S** — Sintomas associados | Nenhum | Um (sudorese OU náusea OU dispneia) | Dois ou mais |

**Interpretação (somatório 0–8)**:
- **0–2 pontos**: risco baixo → teleconsulta com cardiologia ou clínica
  geral em até 24–48h, orientações de retorno.
- **3–4 pontos**: risco moderado → avaliação presencial em até 4–6h
  (pronto-atendimento ou unidade básica com ECG/troponina).
- **5–8 pontos**: risco alto → SAMU 192 ou pronto-socorro com
  hemodinâmica disponível, imediatamente.

> **Importante**: este score é **apoio de triagem**, não substitui
> avaliação médica completa com ECG e troponina. Em qualquer suspeita
> de dissecção aórtica, EP maciça ou tamponamento, escalar como
> vermelho independente do score.

## Estratificação de palpitações

| Característica | Risco | Conduta sugerida |
|---|---|---|
| Esporádicas, regulares, autolimitadas, sem outros sintomas | Baixo | Holter eletivo em ambulatório |
| Sustentadas (>30s), regulares, em jovem sem cardiopatia | Baixo-moderado | Cardiologia em até 7 dias |
| Irregulares "como tambor" sustentadas | Moderado-alto | Cardiologia em até 48h (avaliar FA) |
| Com dor torácica, dispneia ou síncope associada | Alto | Emergência |
| Em paciente com IC, valvopatia ou DAC conhecida | Alto | Emergência |

## Estratificação de dispneia

| Apresentação | Sugere | Próximo passo |
|---|---|---|
| Súbita + dor torácica + imobilização recente | Embolia pulmonar | Emergência |
| Súbita + dor pleurítica + assimetria respiratória | Pneumotórax | Emergência |
| Aos esforços + edema MMII + ortopneia + DPN | Insuficiência cardíaca | Cardiologia urgente |
| Crônica de esforço com sibilância | DPOC/asma | Pneumologia |
| Súbita + sibilância em paciente asmático | Crise asmática | Pronto-atendimento |

## Crise hipertensiva — diferenciação

- **Urgência hipertensiva**: PA muito elevada (PAS ≥180 ou PAD ≥120)
  **sem** lesão aguda de órgão-alvo → controle ambulatorial em 24h.
- **Emergência hipertensiva**: PA muito elevada **com** lesão aguda
  (cefaleia intensa + alteração visual + dor torácica + déficit
  neurológico + dispneia) → SAMU/pronto-socorro imediatamente.

Sinais de lesão de órgão-alvo agudo:
- Encefalopatia (confusão, sonolência, convulsão).
- AVC.
- IAM ou angina instável.
- EAP (edema agudo de pulmão).
- Dissecção aórtica.
- Eclâmpsia (em gestantes).
- Insuficiência renal aguda.

## Referências para o RAG indexar

- `red_flags_cardiovasculares.md` (Sprint-main — seção CV consolidada)
- `cardiologia_apresentacoes_atipicas.md`
- `protocolo_triagem_cardiovascular.md`
- `diretrizes_sbc_hipertensao_arritmia.md`
