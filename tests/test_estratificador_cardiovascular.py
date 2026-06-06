"""
Testes do estratificador cardiovascular (HEART simplificado).

Nota: testes adaptados à API atual de `estratificar_dor_toracica` —
`caracteristicas_dor`/`sintomas_associados` (listas) em vez de
`tipo_dor`/`irradiacao`/`sudorese` (escalares). Retorno usa `nivel`.
"""

from __future__ import annotations

import pytest
from src.tools.estratificador_cardiovascular import estratificar_dor_toracica


def test_estrutura_resposta():
    """Resposta sempre tem chaves essenciais."""
    r = estratificar_dor_toracica(
        idade=50, sexo="masculino",
        caracteristicas_dor=["opressiva"],
        sintomas_associados=[],
        fatores_risco=[],
    )
    assert "nivel" in r or "risco" in r
    assert "score" in r or "score_heart" in r or "pontuacao" in r
    assert (
        "conduta_recomendada" in r
        or "conduta" in r
        or "encaminhamento" in r
        or "recomendacao" in r
    )


def test_sca_obvio():
    """Apresentação clássica de SCA → alto risco."""
    r = estratificar_dor_toracica(
        idade=72,
        sexo="masculino",
        caracteristicas_dor=["opressiva", "irradiacao_braco_esquerdo"],
        sintomas_associados=["sudorese_fria"],
        fatores_risco=["hipertensao", "diabetes", "tabagismo_ativo", "dislipidemia"],
    )
    assert r["nivel"] in {"alto", "critico"}


def test_jovem_atleta_taquicardia_pos_esforco():
    """
    Caso CV-ATIP-04 — jovem atleta com palpitação pós-esforço transitória.
    Não deve disparar alto risco.
    """
    r = estratificar_dor_toracica(
        idade=32,
        sexo="masculino",
        caracteristicas_dor=[],  # palpitação não é dor torácica
        sintomas_associados=[],
        fatores_risco=[],
    )
    # NÃO deve classificar como alto/critico sem outros sintomas
    assert r["nivel"] not in {"alto", "critico"}


def test_diabetica_idosa_sintoma_atipico():
    """
    Caso CV-ATIP-03 — diabética idosa com desconforto epigástrico.
    Estratificador deve considerar idade + DM como sinal de alerta
    mesmo sem dor torácica clássica.
    """
    r = estratificar_dor_toracica(
        idade=65,
        sexo="feminino",
        caracteristicas_dor=[],  # sem dor torácica clássica
        sintomas_associados=["sudorese_fria"],
        fatores_risco=["diabetes"],
        grupos_atipicos=["mulher", "diabetico", "idoso_65"],
    )
    # Pelo menos não pode ser baixo — DM + idade + grupo atípico é sinal
    assert r["nivel"] != "baixo"


def test_baixo_risco_real():
    """Jovem saudável sem fatores."""
    r = estratificar_dor_toracica(
        idade=25,
        sexo="feminino",
        caracteristicas_dor=["pleuritica"],
        sintomas_associados=[],
        fatores_risco=[],
    )
    assert r["nivel"] in {"baixo", "muito_baixo"}


def test_idade_extrema():
    """Idoso muito idoso é considerado fator de risco isolado relevante."""
    r = estratificar_dor_toracica(
        idade=88,
        sexo="masculino",
        caracteristicas_dor=["opressiva"],
        sintomas_associados=[],
        fatores_risco=[],
    )
    # Idade > 80 sozinha não deve gerar baixo risco
    assert r["nivel"] != "baixo"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
