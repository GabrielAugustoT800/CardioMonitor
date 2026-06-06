"""
Bridge layer entre chatbot e telemetria do dashboard.

Responsabilidade: filtragem de batimentos por paciente_id do chatbot.
Mapa _ALIAS resolve o mismatch entre como o /monitor grava (patient="live"
ou similar) e como o chatbot referencia (paciente_id="GABRIEL").

Decisão arquitetural (C1 revisado, integração ArrhythmiaMonitor maio/2026):
- Este módulo MANTÉM pd.read_csv raw (não delega pra dashboard.utils.storage).
- Razão: dashboard/utils/storage.py upstream usa imports relativos
  (`from utils.analysis import ...`) que só funcionam com dashboard/ no
  sys.path. Delegar leitura de CSV daqui forçaria shared/ a mexer no
  sys.path, violando o conceito de bridge layer self-contained.
- A "duplicação" é trivial (1 linha pd.read_csv em cada lado) e os dois
  módulos têm responsabilidades distintas:
    - shared/telemetry_store.py: filtragem por paciente (bridge layer)
    - dashboard/utils/storage.py: persistência CSV/Blob (CRUD)
- Nenhuma das funções públicas deste módulo (load_recent_beats, latest_beat,
  window_summary, register_alias) tem equivalente no upstream.

Cuidados de design preservados do código original:
- não cache o DataFrame inteiro: o CSV é apendado em tempo real pelo /monitor
  e qualquer cache stale entregaria dados antigos. Usamos pandas.read_csv
  direto — cache do filesystem do kernel já faz o trabalho pesado.
- a coluna `patient` do dashboard nem sempre bate com o `paciente_id` do
  chatbot. O dashboard atualmente grava "live", "live-sim" e nomes próprios
  como "Gabriel". O mapa `_ALIAS` resolve esses casos sem alterar dados
  legados.

Tools que consomem este módulo:
- src/tools/ritmo.py (live mode do analisar_ritmo_cardiaco)
- src/tools/telemetria.py (consultar_telemetria_dashboard)
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .paths import (
    TELEMETRY_CSV,
    GABRIEL_CSV,
    MEU_PERFIL_CSV,
    MARIA_CSV,
    HELENA_CSV,
    PEDRO_CSV,
)

# Map opcional de paciente_id (chatbot) → strings aceitas na coluna `patient`
# do dashboard. Estendido em runtime via `register_alias`.
_ALIAS: dict[str, list[str]] = {
    # GABRIEL é o paciente canônico — alinhado com o dataset de referência
    # do dashboard ("gabriel_data.csv" com 200 batimentos).
    "GABRIEL": ["GABRIEL", "Gabriel", "live", "live-sim"],
    # MEU_PERFIL (J.2 Fase J) — dataset saudável demonstrativo
    # ("meu_perfil_data.csv" com 200 batimentos, BPM 65-76, 100% regular).
    "MEU_PERFIL": ["MEU_PERFIL", "Meu Perfil", "meu_perfil"],
    # Pacientes da clínica do Dr. Robert Chase (fase fundação app médico).
    "MARIA": ["MARIA", "Maria", "maria"],
    "HELENA": ["HELENA", "Helena", "helena"],
    "PEDRO": ["PEDRO", "Pedro", "pedro"],
}

# Mapa de fallback CSV por paciente_id quando o paciente não está presente
# em TELEMETRY_CSV (live cardiac_data.csv). Permite que load_recent_beats
# retorne dado de referência ao invés de DataFrame vazio.
# J.2 Fase J: adicionado MEU_PERFIL apontando pra meu_perfil_data.csv,
# análogo ao GABRIEL que já existia pra gabriel_data.csv.
_FALLBACK_CSV_BY_ID: dict[str, "Path"] = {
    "GABRIEL": GABRIEL_CSV,
    "MEU_PERFIL": MEU_PERFIL_CSV,
    "MARIA": MARIA_CSV,
    "HELENA": HELENA_CSV,
    "PEDRO": PEDRO_CSV,
}


def register_alias(paciente_id: str, *aliases: str) -> None:
    """Permite que outros módulos plugem aliases extras em runtime."""
    bag = _ALIAS.setdefault(paciente_id, [paciente_id])
    for a in aliases:
        if a not in bag:
            bag.append(a)


def _candidate_keys(paciente_id: str) -> list[str]:
    """Todos os valores aceitos para a coluna `patient` ao filtrar."""
    return list({paciente_id, *_ALIAS.get(paciente_id, [])})


def _read_csv_safe(path: Path) -> pd.DataFrame:
    """read_csv com fallback para DataFrame vazio se o arquivo não existir."""
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def load_recent_beats(
    paciente_id: str,
    *,
    n: int = 60,
    csv_path: Path = TELEMETRY_CSV,
    fallback_to_gabriel: bool = True,
) -> pd.DataFrame:
    """
    Retorna os últimos `n` batimentos do paciente.

    Se não houver linhas para o paciente em `csv_path` (live data), cai
    para um CSV de referência conforme `_FALLBACK_CSV_BY_ID` (GABRIEL →
    gabriel_data.csv, MEU_PERFIL → meu_perfil_data.csv). Outros pacientes
    sem fallback registrado retornam DataFrame vazio.

    Nome legado `fallback_to_gabriel` é mantido por compatibilidade —
    semanticamente agora controla TODOS os fallbacks (não só Gabriel).
    """
    df = _read_csv_safe(csv_path)
    if not df.empty:
        keys = _candidate_keys(paciente_id)
        sub = df[df["patient"].isin(keys)]
        if not sub.empty:
            return sub.tail(n).reset_index(drop=True)

    # Fallback: dataset de referência por paciente_id
    if fallback_to_gabriel:
        fallback_path = _FALLBACK_CSV_BY_ID.get(paciente_id)
        if fallback_path is not None:
            fb = _read_csv_safe(fallback_path)
            if not fb.empty:
                return fb.tail(n).reset_index(drop=True)

    return pd.DataFrame()


def latest_beat(paciente_id: str) -> Optional[dict[str, Any]]:
    """
    Devolve o último batimento como dict no formato esperado pelo tool
    `analisar_ritmo_cardiaco` (chaves: IBI_ms, BPM, etc — note os
    nomes em CamelCase para casar com a assinatura legada).
    """
    df = load_recent_beats(paciente_id, n=1)
    if df.empty:
        return None
    row = df.iloc[-1]
    return {
        "timestamp_s": float(row["timestamp_s"]),
        "IBI_ms": float(row["ibi_ms"]),
        "BPM": float(row["bpm"]),
        "media_IBI": float(row["media_ibi"]),
        "desvio_medio": float(row["desvio_medio"]),
        "batimentos_anormais": int(row["bat_anormais"]),
        "status": str(row.get("status", "")),
        "datetime": str(row.get("datetime", "")),
    }


def window_summary(
    paciente_id: str,
    *,
    minutes: int = 5,
) -> dict[str, Any]:
    """
    Agrega estatísticas dos últimos N minutos do paciente.

    Returns:
        dict com BPM médio/mín/máx, distribuição de status (% regular,
        atenção, irregular) e timestamp da janela.
    """
    df = load_recent_beats(paciente_id, n=10_000)
    if df.empty:
        return {
            "paciente_id": paciente_id,
            "telemetria_disponivel": False,
            "mensagem": "Sem dados de PPG no dashboard para este paciente.",
        }

    # Filtrar pela janela temporal se houver coluna datetime
    if "datetime" in df.columns:
        df = df.copy()
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        cutoff = df["datetime"].max() - timedelta(minutes=minutes)
        recent = df[df["datetime"] >= cutoff]
        if recent.empty:
            recent = df.tail(60)  # fallback: últimos 60 batimentos
    else:
        recent = df.tail(int(minutes * 60))

    total = max(len(recent), 1)
    status_counts = recent["status"].value_counts().to_dict()

    return {
        "paciente_id": paciente_id,
        "telemetria_disponivel": True,
        "janela_min": minutes,
        "n_beats": int(len(recent)),
        "bpm_medio": round(float(recent["bpm"].mean()), 1),
        "bpm_min": round(float(recent["bpm"].min()), 1),
        "bpm_max": round(float(recent["bpm"].max()), 1),
        "ibi_medio_ms": round(float(recent["ibi_ms"].mean()), 1),
        "desvio_medio_ms": round(float(recent["desvio_medio"].mean()), 1),
        "irregulares_pct": round(100 * status_counts.get("irregular", 0) / total, 1),
        "atencao_pct": round(100 * status_counts.get("atencao", 0) / total, 1),
        "regular_pct": round(100 * status_counts.get("regular", 0) / total, 1),
        "ultimo_status": str(recent.iloc[-1]["status"]),
        "ultimo_timestamp": str(recent.iloc[-1].get("datetime", "")),
    }
