"""
Testes de regressão de escopo e disciplina clínica.

Garantem que a tool analisar_ritmo_cardiaco:
1. Mantém recorte cardiovascular descritivo (não-diagnóstico).
2. Não usa linguagem que afirme diagnóstico.
3. Inclui disclaimers obrigatórios em saídas não-regulares.
4. Não alarma em saídas regulares.

Estes testes validam apenas saídas DETERMINÍSTICAS das tools — não
testam o comportamento do LLM (que é não-determinístico). O teste do
LLM respeitando o system prompt fica para o smoke manual do Passo 7.
"""
from src.tools.ritmo import analisar_ritmo_cardiaco


def test_disclaimer_ppg_em_classificacao_irregular():
    """Toda saída irregular deve mencionar PPG e que não substitui ECG."""
    r = analisar_ritmo_cardiaco(
        timestamp_s=0, IBI_ms=800, BPM=75,
        media_IBI=800, desvio_medio=200, batimentos_anormais=4,
    )
    obs = r.get("observacao", "")
    assert r["classificacao"] == "irregular"
    assert "PPG" in obs, f"Disclaimer PPG ausente em caso irregular: {obs!r}"
    assert "não substitui" in obs, f"Disclaimer 'não substitui' ausente: {obs!r}"


def test_observacao_nao_usa_linguagem_diagnostica():
    """
    Observação gerada NÃO deve afirmar diagnósticos específicos sobre o paciente.
    A tool descreve sinal de PPG, não diagnostica doença.
    """
    r = analisar_ritmo_cardiaco(
        timestamp_s=0, IBI_ms=800, BPM=75,
        media_IBI=800, desvio_medio=200, batimentos_anormais=4,
    )
    obs = r.get("observacao", "").lower()

    # Frases diagnósticas proibidas — ataques na 2ª pessoa
    proibidas = [
        "você tem arritmia",
        "voce tem arritmia",
        "diagnóstico de",
        "diagnostico de",
        "você está com fibrilação",
        "voce esta com fibrilacao",
        "você tem fibrilação",
        "confirma fibrilação",
    ]
    for frase in proibidas:
        assert frase not in obs, (
            f"Linguagem diagnóstica detectada: {frase!r} em obs={obs!r}"
        )


def test_classificacao_regular_nao_alarma():
    """Caso regular não deve mencionar SAMU nem urgência."""
    r = analisar_ritmo_cardiaco(
        timestamp_s=0, IBI_ms=800, BPM=75,
        media_IBI=800, desvio_medio=20, batimentos_anormais=0,
    )
    obs = r.get("observacao", "")
    assert r["classificacao"] == "regular"
    assert "SAMU" not in obs, f"SAMU mencionado em caso regular (false alarm): {obs!r}"
    assert "192" not in obs, f"192 mencionado em caso regular: {obs!r}"


def test_rota_emergencia_em_irregular():
    """Caso irregular deve apontar rota de emergência (SAMU 192) e sintomas-gatilho."""
    r = analisar_ritmo_cardiaco(
        timestamp_s=0, IBI_ms=800, BPM=75,
        media_IBI=800, desvio_medio=200, batimentos_anormais=4,
    )
    obs = r.get("observacao", "")
    assert "SAMU 192" in obs or "192" in obs, (
        f"Rota de emergência (SAMU 192) ausente em irregular: {obs!r}"
    )
    obs_lower = obs.lower()
    sintomas_gatilho = ["dor torácica", "dor toracica", "dispneia", "síncope", "sincope"]
    assert any(s in obs_lower for s in sintomas_gatilho), (
        f"Sintomas-gatilho de emergência ausentes: {obs!r}"
    )
