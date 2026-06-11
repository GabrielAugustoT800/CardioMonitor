"""Timeline cronológica de eventos clínicos do paciente (fase 10).

Agrega eventos de 3 fontes do JSON enriquecido (consultas, medicações,
exames) em uma lista única ordenada por data desc. Função pura — sem
callbacks, sem efeitos colaterais.

Usada pelo bloco _bloco_timeline_paciente em utils/prontuario.py quando
papel='medico'. Paciente NÃO vê a timeline (decisão da Fase 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EventoTimeline:
    """Item da timeline. Ordenado por `data` (ISO completa)."""
    tipo: str           # "CONSULTA" | "MEDICACAO" | "EXAME"
    data: str           # ISO "YYYY-MM-DD" pra ordenação
    data_exibicao: str  # formato amigável "10/05/2026" ou "08/2023"
    titulo: str
    descricao: str


def _normalizar_data(s: str) -> tuple[str, str]:
    """Recebe data heterogênea, retorna (iso_completa, exibicao).

    Aceita:
      - "YYYY-MM-DD"  -> ISO igual, exibe "DD/MM/YYYY"
      - "YYYY-MM"     -> ISO "YYYY-MM-01", exibe "MM/YYYY"
      - "DD/MM/YYYY"  -> converte, exibe igual

    Datas não reconhecidas vão pra "9999-12-31" (ordenam no fim) com
    exibição preservando o string original.
    """
    if not s:
        return "9999-12-31", "—"
    s = s.strip()

    # YYYY-MM-DD
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m/%Y")
        except ValueError:
            pass

    # YYYY-MM
    if len(s) == 7 and s[4] == "-":
        try:
            dt = datetime.strptime(s + "-01", "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d"), dt.strftime("%m/%Y")
        except ValueError:
            pass

    # DD/MM/YYYY
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        try:
            dt = datetime.strptime(s, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m/%Y")
        except ValueError:
            pass

    return "9999-12-31", s


def gerar_eventos_timeline(paciente: dict) -> list[EventoTimeline]:
    """Agrega eventos de consultas + medicações + exames em lista
    ordenada por data desc (mais recente primeiro).

    Dedup defensivo: `consultas.ultima` é frequentemente o mesmo item
    de `consultas.historico[0]` no JSON enriquecido. Pra evitar card
    duplicado na timeline, `ultima` só entra se nenhum evento do
    histórico bater pela data ISO.
    """
    eventos: list[EventoTimeline] = []

    consultas = paciente.get("consultas") or {}

    # 1. Histórico de consultas
    datas_historico = set()
    for c in consultas.get("historico", []) or []:
        iso, exib = _normalizar_data(c.get("data", ""))
        datas_historico.add(iso)
        eventos.append(EventoTimeline(
            tipo="CONSULTA",
            data=iso,
            data_exibicao=exib,
            titulo=f"Consulta — {c.get('tipo') or c.get('especialidade') or '—'}",
            descricao=c.get("resumo") or c.get("observacoes") or "—",
        ))

    # 2. Ultima consulta (se NÃO duplica histórico)
    ultima = consultas.get("ultima") or {}
    if ultima.get("data"):
        iso, exib = _normalizar_data(ultima["data"])
        if iso not in datas_historico:
            eventos.append(EventoTimeline(
                tipo="CONSULTA",
                data=iso,
                data_exibicao=exib,
                titulo=(f"Última consulta — "
                        f"{ultima.get('especialidade') or '—'}"),
                descricao=ultima.get("observacoes") or "—",
            ))

    # 3. Próxima consulta (agendada)
    proxima = consultas.get("proxima") or {}
    if proxima.get("data"):
        iso, exib = _normalizar_data(proxima["data"])
        eventos.append(EventoTimeline(
            tipo="CONSULTA",
            data=iso,
            data_exibicao=exib,
            titulo=(f"Próxima consulta — "
                    f"{proxima.get('especialidade') or '—'}"),
            descricao=f"Status: {proxima.get('status') or 'agendada'}",
        ))

    # 4. Medicações (data de início)
    for m in paciente.get("medicacoes_ativas", []) or []:
        if not m.get("inicio"):
            continue
        iso, exib = _normalizar_data(m["inicio"])
        nome = m.get("nome") or "—"
        dose = m.get("dose") or ""
        titulo = f"Início — {nome} {dose}".strip()
        descricao = " · ".join(filter(None, [
            m.get("frequencia"),
            m.get("indicacao"),
        ])) or "—"
        eventos.append(EventoTimeline(
            tipo="MEDICACAO",
            data=iso,
            data_exibicao=exib,
            titulo=titulo,
            descricao=descricao,
        ))

    # 5. Exames recentes
    for e in paciente.get("exames_recentes", []) or []:
        iso, exib = _normalizar_data(e.get("data", ""))
        tipo_exame = e.get("tipo") or e.get("nome") or "—"
        eventos.append(EventoTimeline(
            tipo="EXAME",
            data=iso,
            data_exibicao=exib,
            titulo=f"Exame — {tipo_exame}",
            descricao=e.get("resultado") or e.get("laudo") or "—",
        ))

    eventos.sort(key=lambda ev: ev.data, reverse=True)
    return eventos
