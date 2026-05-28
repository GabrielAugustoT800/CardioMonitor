"""
Tool: analisar_ritmo_cardiaco
Análise mockada de ritmo cardíaco via atributos de IBI.
"""


def analisar_ritmo_cardiaco(
    timestamp_s: float,
    IBI_ms: float,
    BPM: float,
    media_IBI: float,
    desvio_medio: float,
    batimentos_anormais: int,
) -> dict:
    """
    Analisa ritmo cardíaco a partir de atributos calculados do IBI.

    Sprint 1: lógica determinística mockada.
    Projeto final: substituir pelo modelo de ML real.

    Regra mock:
    - 0 a 1 batimentos anormais → regular
    - 2 a 3 batimentos anormais → limítrofe → regular com aviso
    - 4 a 5 batimentos anormais → irregular

    Args:
        timestamp_s: Momento da leitura em segundos.
        IBI_ms: Intervalo entre batimentos em milissegundos.
        BPM: Batimentos por minuto.
        media_IBI: Média dos IBI na janela de 5 registros.
        desvio_medio: Desvio médio dos IBI na janela.
        batimentos_anormais: Quantidade de batimentos anormais na janela.

    Returns:
        Dicionário com atributos de entrada + classificacao + observacao.
    """
    # Validação de entrada
    if not (0 <= batimentos_anormais <= 5):
        return {"erro": "batimentos_anormais deve ser entre 0 e 5."}

    # Lógica determinística mock
    if batimentos_anormais <= 1:
        classificacao = "regular"
        observacao = (
            "Ritmo sinusal regular. "
            "Variabilidade dentro dos parâmetros fisiológicos normais."
        )
    elif batimentos_anormais <= 3:
        classificacao = "regular"
        observacao = (
            f"{batimentos_anormais} de 5 batimentos com variação detectada. "
            "Dentro do limiar aceitável. Monitoramento contínuo recomendado."
        )
    else:
        classificacao = "irregular"
        observacao = (
            f"Irregularidade detectada. {batimentos_anormais} de 5 registros "
            "classificados como anormais. Alta variabilidade de IBI. "
            "Recomenda avaliação médica."
        )

    return {
        "timestamp_s": timestamp_s,
        "IBI_ms": IBI_ms,
        "BPM": BPM,
        "media_IBI": media_IBI,
        "desvio_medio": desvio_medio,
        "batimentos_anormais": batimentos_anormais,
        "classificacao": classificacao,
        "observacao": observacao,
        "nota": "Sprint 1: análise mockada."
    }