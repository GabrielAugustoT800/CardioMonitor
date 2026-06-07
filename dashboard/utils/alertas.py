"""Agregador de alertas cross-paciente pro app médico (fase 5).

Coleta 3 tipos de alerta dos 5 pacientes e retorna lista priorizada:

1. CRITICO  — paciente com semáforo 🔴 (telemetria global + condição grave)
2. PICO     — deterioração súbita na telemetria (janela curta 10 leituras
              com >=50% irregular, em paciente verde/amarelo global)
3. RASCUNHO — rascunho de prescrição pendente de aprovação

Ordem na fila: CRITICO -> PICO -> RASCUNHO (por data_geracao asc — mais
antigos primeiro, urgência por espera).

Convenção do projeto: 'from utils.X' (dashboard/ no sys.path).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shared.patient_registry import list_patients

from utils.storage import load_csv
from utils.semaforo import calcular_semaforo, detectar_pico_telemetria
from utils.prontuario import csv_do_paciente
from utils.rascunhos_runtime import listar_pendentes


@dataclass
class Alerta:
    """Item da fila de alertas. prioridade=0 é o topo (mais urgente)."""
    tipo: str               # "CRITICO" | "PICO" | "RASCUNHO"
    prioridade: int         # 0 (CRITICO) | 1 (PICO) | 2 (RASCUNHO)
    paciente_id: str
    paciente_nome: str
    titulo: str
    descricao: str
    ancora: str             # id HTML da seção do prontuário pra scroll
    data_geracao: str       # ISO (ordenacao de desempate)


def listar_alertas() -> list[Alerta]:
    """Coleta todos os alertas dos 5 pacientes, ordenados por prioridade.

    Pacientes 🔴 NÃO geram PICO redundante (já estão em CRITICO).
    Rascunhos são incluídos independente do semáforo do paciente.
    """
    alertas: list[Alerta] = []
    agora = datetime.now().isoformat(timespec="minutes")

    for p in list_patients():
        pid = p["id"]
        nome = p.get("nome") or pid
        csv_p = csv_do_paciente(pid)
        df = load_csv(csv_p) if csv_p and csv_p.exists() else None

        # 1. CRITICO — semáforo vermelho (telemetria global + condição grave)
        cor, justif = calcular_semaforo(p, df)
        if cor == "vermelho":
            alertas.append(Alerta(
                tipo="CRITICO",
                prioridade=0,
                paciente_id=pid,
                paciente_nome=nome,
                titulo=f"{nome} em vigilância crítica",
                descricao=justif,
                ancora="bloco-telemetria",
                data_geracao=agora,
            ))

        # 2. PICO — deterioração súbita. Suprime se já é CRITICO (evita duplo
        # alerta pro mesmo paciente; o CRITICO já cobre a urgência clínica).
        tem_pico, justif_pico = detectar_pico_telemetria(df)
        if tem_pico and cor != "vermelho":
            alertas.append(Alerta(
                tipo="PICO",
                prioridade=1,
                paciente_id=pid,
                paciente_nome=nome,
                titulo=f"Deterioração recente — {nome}",
                descricao=justif_pico,
                ancora="bloco-telemetria",
                data_geracao=agora,
            ))

        # 3. RASCUNHO — todos os pendentes (independente do semáforo do paciente)
        for r in listar_pendentes(pid):
            alertas.append(Alerta(
                tipo="RASCUNHO",
                prioridade=2,
                paciente_id=pid,
                paciente_nome=nome,
                titulo=f"Rascunho pendente: {r.get('medicamento', '?')}",
                descricao=r.get("alteracao", ""),
                ancora="bloco-aprovacao-rascunho",
                data_geracao=r.get("data_geracao", agora),
            ))

    # Ordena: prioridade asc; dentro do mesmo tipo, data_geracao asc
    # (rascunhos mais antigos primeiro — espera virou prioridade).
    alertas.sort(key=lambda a: (a.prioridade, a.data_geracao))
    return alertas


def total_alertas() -> int:
    """Número agregado pra badge do nav. Re-calcula a cada chamada."""
    return len(listar_alertas())
