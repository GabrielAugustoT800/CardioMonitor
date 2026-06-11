"""Calculadoras clínicas cardiovasculares (fase 9).

Todas as funções são puras (sem efeitos colaterais), determinísticas
(sem LLM), e retornam tupla (score, interpretacao_clinica). Referências
de guidelines no docstring de cada função.

Princípio: ferramenta de apoio à decisão. Médico decide com base no
score + contexto clínico. Resultado nunca prescreve sozinho.
"""

from __future__ import annotations


def cha2ds2_vasc(idade: int, sexo: str, ic_congestiva: bool, hipertensao: bool,
                 avc_previo: bool, doenca_vascular: bool,
                 diabetes: bool) -> tuple[int, str]:
    """CHA₂DS₂-VASc — estratificação de risco de AVC em FA não-valvar.

    Ref: Lip GY et al. Chest. 2010;137(2):263-72.
    Guidelines: ESC 2024, AHA/ACC/HRS 2023.

    Pontuação:
      C  Insuficiência cardíaca congestiva  +1
      H  Hipertensão                         +1
      A₂ Idade ≥75 anos                      +2 (entre 65-74: +1, abaixo: 0)
      D  Diabetes mellitus                   +1
      S₂ AVC/AIT/TEV prévio                  +2
      V  Doença vascular (IAM, DAP, placa)   +1
      A  Idade 65-74                         +1
      Sc Sexo feminino                       +1

    Conduta sugerida (homem / mulher):
      0 / 1   : não anticoagular
      1 / 2   : considerar (decisão compartilhada)
      ≥2 / ≥3 : anticoagular (DOAC preferível a varfarina)
    """
    score = 0
    if ic_congestiva:
        score += 1
    if hipertensao:
        score += 1
    if idade >= 75:
        score += 2
    elif idade >= 65:
        score += 1
    if diabetes:
        score += 1
    if avc_previo:
        score += 2
    if doenca_vascular:
        score += 1
    eh_feminino = (sexo or "").strip().lower() in ("f", "feminino")
    if eh_feminino:
        score += 1

    if eh_feminino:
        if score <= 1:
            conduta = "Não anticoagular (sexo feminino sem outros fatores)."
        elif score == 2:
            conduta = "Considerar anticoagulação (decisão compartilhada)."
        else:
            conduta = "Anticoagulação indicada (DOAC preferível a varfarina)."
    else:
        if score == 0:
            conduta = "Não anticoagular."
        elif score == 1:
            conduta = "Considerar anticoagulação (decisão compartilhada)."
        else:
            conduta = "Anticoagulação indicada (DOAC preferível a varfarina)."

    return score, conduta


def has_bled(hipertensao_descontrolada: bool, funcao_renal_anormal: bool,
             funcao_hepatica_anormal: bool, avc_previo: bool,
             sangramento_previo: bool, inr_labil: bool,
             idade_maior_65: bool, drogas_alcool: bool) -> tuple[int, str]:
    """HAS-BLED — risco de sangramento maior em anticoagulados.

    Ref: Pisters R et al. Chest. 2010;138(5):1093-100.
    Guidelines: ESC 2024.

    Cada fator: +1.
      H  Hipertensão sistólica >160 mmHg (descontrolada)
      A  Função renal anormal (Cr >2.3 mg/dL ou diálise/transplante)
      A  Função hepática anormal (cirrose, bilirrubina >2x, ALT >3x)
      S  AVC prévio
      B  História de sangramento ou predisposição
      L  INR lábil (TTR <60%)
      E  Idade >65 anos
      D  Drogas (antiplaquetários, AINEs) ou álcool excessivo

    Score ≥3 = alto risco de sangramento. NÃO contraindica anticoagulação
    — sinaliza necessidade de vigilância e correção de fatores reversíveis.
    """
    score = sum([
        bool(hipertensao_descontrolada),
        bool(funcao_renal_anormal),
        bool(funcao_hepatica_anormal),
        bool(avc_previo),
        bool(sangramento_previo),
        bool(inr_labil),
        bool(idade_maior_65),
        bool(drogas_alcool),
    ])

    if score == 0:
        conduta = "Baixo risco. Anticoagular conforme indicação."
    elif score <= 2:
        conduta = "Risco intermediário. Anticoagular com vigilância."
    else:
        conduta = (
            "Alto risco de sangramento. NÃO contraindica anticoagulação; "
            "corrigir fatores reversíveis (controle PA, suspender AAS "
            "desnecessário, reduzir álcool) e reavaliar trimestralmente."
        )
    return score, conduta


def egfr_ckd_epi(creatinina_mg_dl: float, idade: int,
                 sexo: str) -> tuple[float, str]:
    """eGFR pela fórmula CKD-EPI 2021 (sem coeficiente racial).

    Ref: Inker LA et al. NEJM. 2021;385(19):1737-1749.

    Fórmula CKD-EPI 2021 (creatinina):
      eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^(-1.200) ×
             0.9938^idade × (1.012 se feminino)
    Onde:
      κ = 0.7 (F) ou 0.9 (M)
      α = -0.241 (F) ou -0.302 (M)

    Resultado em mL/min/1.73m². Classificação KDIGO 2024:
      G1  ≥90  : normal/alta
      G2  60-89: levemente reduzida
      G3a 45-59: leve-moderada
      G3b 30-44: moderada-severa
      G4  15-29: severa
      G5  <15  : falência renal
    """
    if creatinina_mg_dl <= 0:
        raise ValueError("Creatinina deve ser positiva.")
    if idade < 18:
        raise ValueError("Fórmula CKD-EPI 2021 é validada apenas em adultos.")

    eh_feminino = (sexo or "").strip().lower() in ("f", "feminino")
    k = 0.7 if eh_feminino else 0.9
    alpha = -0.241 if eh_feminino else -0.302
    sexo_factor = 1.012 if eh_feminino else 1.0

    scr_k = creatinina_mg_dl / k
    egfr = (142
            * (min(scr_k, 1) ** alpha)
            * (max(scr_k, 1) ** (-1.200))
            * (0.9938 ** idade)
            * sexo_factor)

    if egfr >= 90:
        cls = "G1 — função renal normal ou alta"
    elif egfr >= 60:
        cls = "G2 — levemente reduzida"
    elif egfr >= 45:
        cls = "G3a — leve a moderadamente reduzida"
    elif egfr >= 30:
        cls = "G3b — moderada a severamente reduzida"
    elif egfr >= 15:
        cls = "G4 — severamente reduzida"
    else:
        cls = "G5 — falência renal (TFG <15)"

    return round(egfr, 1), cls


def heart_score(historia: int, ecg: int, idade: int, fatores_risco: int,
                troponina: int) -> tuple[int, str]:
    """HEART score — risco MACE em 6 semanas em dor torácica na emergência.

    Ref: Backus BE et al. Int J Cardiol. 2013;168(3):2153-58.

    Cada parâmetro pontua 0, 1 ou 2:

    HISTÓRIA  0=Pouco suspeita | 1=Moderadamente | 2=Altamente suspeita
    ECG       0=Normal | 1=Alt. inespecíficas | 2=Desnivelamento ST sig.
    IDADE     0=<45 | 1=45-64 | 2=≥65
    FATORES   0=Nenhum | 1=1-2 (HAS/DLP/DM/tabag/obes/famil) | 2=≥3 ou
              aterosclerose conhecida
    TROPONINA 0=≤ LSN | 1=1-3× LSN | 2=>3× LSN

    Risco MACE (Major Adverse Cardiac Events) em 6 semanas:
      0-3 : BAIXO    (~1.7%)  — alta possível com seguimento ambulatorial
      4-6 : MODERADO (~16.6%) — internação/observação, seriação troponina
      7-10: ALTO     (~50.1%) — abordagem invasiva precoce (cateterismo)
    """
    for nome, valor in [("historia", historia), ("ecg", ecg),
                        ("idade", idade), ("fatores_risco", fatores_risco),
                        ("troponina", troponina)]:
        if valor not in (0, 1, 2):
            raise ValueError(
                f"Parâmetro '{nome}'={valor} inválido — deve ser 0, 1 ou 2."
            )

    score = historia + ecg + idade + fatores_risco + troponina

    if score <= 3:
        cls = ("BAIXO risco MACE em 6 semanas (~1,7%). "
               "Considerar alta com seguimento ambulatorial.")
    elif score <= 6:
        cls = ("MODERADO risco (~16,6%). Internação/observação com "
               "seriação de troponina e estratificação.")
    else:
        cls = ("ALTO risco (~50,1%). Abordagem invasiva precoce "
               "(cateterismo).")

    return score, cls
