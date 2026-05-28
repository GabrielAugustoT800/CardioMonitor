"""Tool: classificação de risco clínico (heurística determinística inspirada no Manchester).

Mantida em regras fixas em Python (não LLM) por auditabilidade e para
eliminar risco de alucinação em decisão crítica. É uma versão
simplificada do Sistema de Triagem de Manchester — em produção,
substituir por uma implementação validada/certificada.

Lógica de decisão:
- red flag OU score de sinais vitais ≥ 4 → CRÍTICO (vermelho, SAMU)
- score ≥ 2 ou alto desconforto + (idoso ou polipatológico) → ALTO (laranja)
- alto desconforto OU score == 1 → MODERADO (amarelo)
- algum sintoma → BAIXO (verde)
- nada → orientação educacional (azul)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---- vocabulários clínicos ----------------------------------------------
# Termos normalizados (sem acento, lowercase) — qualquer match dispara
# a classificação correspondente em _classificar_risco_clinico.

_RED_FLAGS = {
    "dor toracica em esforco", "dor toracica intensa", "sudorese fria",
    "dispneia subita", "falta de ar grave", "perda de consciencia",
    "deficit neurologico", "fraqueza unilateral", "fala arrastada",
    "cefaleia subita", "pior dor de cabeca da vida", "ideacao suicida",
    "tentativa de suicidio", "sangramento ativo", "sangramento abundante",
    "convulsao", "dor abdominal severa",
    # Cardiovascular — apresentações típicas
    "dor opressiva retroesternal", "dor irradiando braco esquerdo",
    "dor irradiando mandibula", "sincope em esforco",
    "sincope sem pedrodromos",
    # Cardiovascular — emergências específicas
    "dor toracica lancinante", "dor migratoria peito dorso",
    "assimetria de pulsos", "turgencia jugular",
    "pa sistolica acima 180 com cefaleia",
    "pa sistolica acima 180 com alteracao visual",
    # Cardiovascular — equivalentes anginosos em grupos de risco
    "dispneia subita em diabetico", "dispneia subita em idoso",
    "epigastralgia com sudorese em diabetico",
}

_ALTO_DESCONFORTO = {
    "dispneia leve", "febre alta persistente", "vomitos repetidos",
    "desidratacao", "dor moderada", "tontura intensa",
}


# ---- schema de entrada (validação Pydantic) -----------------------------

class ClassificacaoInput(BaseModel):
    """Valida os argumentos antes da classificação determinística."""
    sintomas: list[str] = Field(default_factory=list)
    sinais_vitais: dict[str, float] = Field(default_factory=dict)
    idade: int = Field(..., ge=0, le=120)
    comorbidades: list[str] = Field(default_factory=list)


# ---- helpers ------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """Remove acentos e padroniza lowercase para casamento robusto contra vocabulário."""
    return (
        texto.lower()
        .replace("á", "a").replace("â", "a").replace("ã", "a")
        .replace("é", "e").replace("ê", "e").replace("í", "i")
        .replace("ó", "o").replace("ô", "o").replace("õ", "o")
        .replace("ú", "u").replace("ç", "c").strip()
    )


def _avaliar_sinais_vitais(sinais: dict[str, float]) -> int:
    """Pontuação NEWS2-like (0 a 4+) somando alterações em FC, SpO2, PA, T° e FR."""
    score = 0
    fc = sinais.get("fc")
    if fc is not None and (fc < 40 or fc > 130):
        score += 2
    elif fc is not None and (fc < 50 or fc > 110):
        score += 1
    spo2 = sinais.get("spo2")
    if spo2 is not None and spo2 < 90:
        score += 3
    elif spo2 is not None and spo2 < 94:
        score += 1
    pas = sinais.get("pa_sistolica")
    if pas is not None and (pas < 90 or pas > 200):
        score += 2
    temp = sinais.get("temperatura")
    if temp is not None and temp >= 39.5:
        score += 1
    fr = sinais.get("fr")
    if fr is not None and (fr < 8 or fr > 30):
        score += 2
    return score


# ---- classificador principal --------------------------------------------

def classificar_risco_clinico(
    sintomas: list[str],
    sinais_vitais: dict[str, float],
    idade: int,
    comorbidades: list[str],
) -> dict[str, Any]:
    """Classifica o risco com lógica simples e auditável (Manchester simplificado)."""
    # Pydantic levanta ValueError em entradas inválidas — bom pra audit.
    ClassificacaoInput(
        sintomas=sintomas, sinais_vitais=sinais_vitais,
        idade=idade, comorbidades=comorbidades,
    )

    sintomas_norm = [_normalizar(s) for s in sintomas]
    red_flag = any(any(rf in s for rf in _RED_FLAGS) for s in sintomas_norm)
    alto_desc = any(any(a in s for a in _ALTO_DESCONFORTO) for s in sintomas_norm)
    score_vitais = _avaliar_sinais_vitais(sinais_vitais)
    # Idosos e polipatológicos sobem 1 nível em quadros borderline.
    fator_idade = 1 if idade >= 65 else 0
    fator_comorb = 1 if len(comorbidades) >= 2 else 0

    # Cascata de decisão: do mais grave (vermelho) ao mais leve (azul).
    if red_flag or score_vitais >= 4:
        nivel, manchester = "critico", "vermelho"
        tempo = "atendimento imediato — acionar SAMU 192 ou ir ao pronto-socorro mais próximo"
        especialidade = "emergencia"
    elif score_vitais >= 2 or (alto_desc and (fator_idade or fator_comorb)):
        nivel, manchester = "alto", "laranja"
        tempo = "atendimento em até 10 minutos via teleconsulta de urgência ou pronto atendimento"
        especialidade = "clinica_geral"
    elif alto_desc or score_vitais == 1:
        nivel, manchester = "moderado", "amarelo"
        tempo = "atendimento em até 60 minutos por teleconsulta ou unidade básica"
        especialidade = "clinica_geral"
    elif sintomas:
        nivel, manchester = "baixo", "verde"
        tempo = "atendimento em até 24 horas por teleconsulta de rotina"
        especialidade = "clinica_geral"
    else:
        nivel, manchester = "baixo", "azul"
        tempo = "orientação educacional, sem necessidade imediata de atendimento"
        especialidade = "clinica_geral"

    justificativa_partes = []
    if red_flag:
        justificativa_partes.append("sintomas compatíveis com red flag clínica")
    if score_vitais:
        justificativa_partes.append(f"alteração em sinais vitais (score {score_vitais})")
    if fator_idade:
        justificativa_partes.append("idade ≥ 65 anos potencializa risco")
    if fator_comorb:
        justificativa_partes.append("múltiplas comorbidades aumentam vulnerabilidade")
    if not justificativa_partes:
        justificativa_partes.append("quadro estável, sem critérios de gravidade evidentes")

    return {
        "nivel": nivel,
        "manchester": manchester,
        "justificativa": "; ".join(justificativa_partes) + ".",
        "especialidade_sugerida": especialidade,
        "tempo_recomendado_atendimento": tempo,
        "score_sinais_vitais": score_vitais,
        "red_flag_detectada": red_flag,
    }
