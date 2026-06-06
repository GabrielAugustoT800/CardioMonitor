"""Tool: estratificação de risco cardiovascular para dor torácica e equivalentes.

Inspirada no HEART score, com adaptação pré-hospitalar (sem ECG nem
troponina). Mantida em regras determinísticas em Python por
auditabilidade — risco de alucinação LLM em estratificação clínica é
inaceitável.

Em produção, substituir por implementação validada com integração de
ECG e biomarcadores.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---- vocabulários clínicos (HEART-like) ---------------------------------
# Tokens normalizados aceitos como caracteristicas_dor / sintomas_associados
# / fatores_risco. Não tente "adivinhar" — o LLM tem prompt orientando.

_HISTORIA_ALTA_SUSPEITA = {
    "opressiva", "aperto", "peso", "queimacao_retroesternal",
    "irradiacao_braco_esquerdo", "irradiacao_mandibula",
    "irradiacao_dorso", "deflagrada_por_esforco",
    "alivio_repouso", "alivio_nitrato",
}

_HISTORIA_BAIXA_SUSPEITA = {
    "pleuritica", "reproduzivel_palpacao", "punctada",
    "ventilatorio_dependente", "movimentos_dependente",
    "longa_duracao_estavel",
}

_SINTOMAS_ASSOCIADOS = {
    "sudorese", "sudorese_fria", "nausea", "vomito",
    "dispneia", "sincope", "pre_sincope", "palidez",
}

_FATORES_RISCO_VALIDOS = {
    "hipertensao", "diabetes", "dislipidemia", "tabagismo_ativo",
    "tabagismo_recente", "dac_previa", "iam_previo", "avc_previo",
    "doenca_arterial_periferica", "drc_estagio_3_ou_mais",
    "obesidade", "sedentarismo", "iam_familia_precoce",
}

_GRUPOS_ATIPICOS = {"mulher", "diabetico", "idoso_65", "neuropata", "ic_previa"}


# ---- schema de entrada (validação Pydantic) -----------------------------

class EstratificacaoCVInput(BaseModel):
    """Valida os argumentos antes da estratificação determinística."""
    caracteristicas_dor: list[str] = Field(default_factory=list)
    sintomas_associados: list[str] = Field(default_factory=list)
    idade: int = Field(..., ge=0, le=120)
    sexo: Literal["masculino", "feminino", "outro"] = "outro"
    fatores_risco: list[str] = Field(default_factory=list)
    grupos_atipicos: list[str] = Field(default_factory=list)
    duracao_minutos: int | None = None
    em_esforco: bool = False


# ---- componentes do score (H, A, R, S) ----------------------------------

def _pontuar_historia(caracteristicas: list[str], em_esforco: bool) -> int:
    """Componente H do HEART simplificado (0-2)."""
    alta = sum(1 for c in caracteristicas if c in _HISTORIA_ALTA_SUSPEITA)
    baixa = sum(1 for c in caracteristicas if c in _HISTORIA_BAIXA_SUSPEITA)

    if em_esforco:
        alta += 1

    if alta >= 2 and baixa == 0:
        return 2
    if alta >= 1 or (alta == 0 and baixa == 0):
        return 1
    return 0


def _pontuar_idade(idade: int) -> int:
    """Componente A do HEART (0-2)."""
    if idade >= 65:
        return 2
    if idade >= 45:
        return 1
    return 0


def _pontuar_fatores_risco(fatores: list[str]) -> int:
    """Componente R do HEART (0-2)."""
    fatores_validos = [f for f in fatores if f in _FATORES_RISCO_VALIDOS]
    doenca_aterosclerotica = any(
        f in fatores_validos
        for f in ("dac_previa", "iam_previo", "avc_previo",
                  "doenca_arterial_periferica")
    )

    if doenca_aterosclerotica or len(fatores_validos) >= 3:
        return 2
    if len(fatores_validos) >= 1:
        return 1
    return 0


def _pontuar_sintomas(sintomas: list[str]) -> int:
    """Componente S adicionado (sintomas associados) (0-2)."""
    presentes = sum(1 for s in sintomas if s in _SINTOMAS_ASSOCIADOS)
    if presentes >= 2:
        return 2
    if presentes >= 1:
        return 1
    return 0


# ---- estratificador principal -------------------------------------------

def estratificar_dor_toracica(
    caracteristicas_dor: list[str],
    sintomas_associados: list[str],
    idade: int,
    sexo: str,
    fatores_risco: list[str],
    grupos_atipicos: list[str] | None = None,
    duracao_minutos: int | None = None,
    em_esforco: bool = False,
) -> dict[str, Any]:
    """Estratifica risco CV de dor torácica / equivalente anginoso.

    Retorna dicionário com score, nível, conduta e justificativa.
    """
    grupos_atipicos = grupos_atipicos or []

    # Pydantic levanta ValueError em entradas inválidas — bom pra audit.
    EstratificacaoCVInput(
        caracteristicas_dor=caracteristicas_dor,
        sintomas_associados=sintomas_associados,
        idade=idade,
        sexo=sexo,
        fatores_risco=fatores_risco,
        grupos_atipicos=grupos_atipicos,
        duracao_minutos=duracao_minutos,
        em_esforco=em_esforco,
    )

    h = _pontuar_historia(caracteristicas_dor, em_esforco)
    a = _pontuar_idade(idade)
    r = _pontuar_fatores_risco(fatores_risco)
    s = _pontuar_sintomas(sintomas_associados)
    score = h + a + r + s

    # Apresentação atípica: grupo de risco + equivalente anginoso sem dor
    # típica sobe 1 ponto. Cobre IAM silencioso em diabético/idoso/mulher.
    eh_atipico = any(g in _GRUPOS_ATIPICOS for g in grupos_atipicos)
    tem_equivalente = bool(sintomas_associados) and not caracteristicas_dor
    ajuste_atipico = 1 if (eh_atipico and tem_equivalente) else 0
    score_ajustado = min(score + ajuste_atipico, 8)

    # Cascata de decisão: score ajustado mapeia direto na conduta.
    if score_ajustado >= 5:
        nivel, manchester = "alto", "vermelho"
        conduta = (
            "encaminhamento imediato para emergência com hemodinâmica — "
            "acionar SAMU 192 ou pronto-socorro de referência"
        )
    elif score_ajustado >= 3:
        nivel, manchester = "moderado", "laranja"
        conduta = (
            "avaliação presencial em até 4-6h em pronto-atendimento ou "
            "unidade básica com ECG e troponina disponíveis"
        )
    else:
        nivel, manchester = "baixo", "verde"
        conduta = (
            "teleconsulta com cardiologia ou clínica geral em 24-48h, "
            "com orientações claras de retorno em caso de piora"
        )

    componentes = {
        "H_historia_clinica": h,
        "A_idade": a,
        "R_fatores_risco": r,
        "S_sintomas_associados": s,
        "score_base": score,
        "ajuste_apresentacao_atipica": ajuste_atipico,
        "score_ajustado_total": score_ajustado,
    }

    return {
        "nivel": nivel,
        "manchester": manchester,
        "score": score_ajustado,
        "componentes": componentes,
        "conduta_recomendada": conduta,
        "apresentacao_atipica_detectada": bool(ajuste_atipico),
        "disclaimer": (
            "Estratificação de apoio à triagem, sem ECG nem biomarcadores. "
            "Não substitui avaliação médica completa."
        ),
    }
