"""Página /pacientes — gestão de perfis ativos."""
from __future__ import annotations

import dash
from dash import html, dcc
from shared.patient_registry import get_patient

# role="oculto" (fase 2c): pagina /pacientes ficou redundante com o dropdown
# topbar + /prontuario data-driven. Mantida acessivel por URL pra rollback /
# debug, mas fora do nav do paciente.
dash.register_page(__name__, path="/pacientes", name="Pacientes",
                   role="oculto", order=6)

# Lista dos pacientes da clinica do Dr. Chase. MEU_PERFIL (id antigo) removido —
# /meu-perfil nao existe mais (fase 2c). LUCAS/MARIA/HELENA/PEDRO adicionados
# pra refletir o caseload real; todos os cards apontam pra /prontuario, que
# resolve o paciente ativo via dropdown topbar (perfil-ativo Store).
PERFIS_GERENCIADOS = ["GABRIEL", "LUCAS", "MARIA", "HELENA", "PEDRO"]


def _card_perfil(perfil_id: str) -> html.Div:
    """Card de um perfil com link pro /prontuario data-driven."""
    perfil = get_patient(perfil_id)
    if not perfil:
        return html.Div([
            html.H3(f"Perfil {perfil_id}"),
            html.P("Não encontrado em perfis_clinicos.json", className="hud-warn"),
        ], className="hud-panel pacientes-card")

    nome = perfil.get("nome") or "Sem nome"
    idade = perfil.get("idade")
    descricao = perfil.get("_meta", {}).get("descricao", "")

    children = [
        html.H3(nome, className="pacientes-card__nome"),
        html.Div(f"ID: {perfil_id}", className="pacientes-card__id"),
        html.Div(
            f"Idade: {idade if idade is not None else '—'}",
            className="pacientes-card__meta",
        ),
    ]
    if descricao:
        children.append(html.P(descricao, className="pacientes-card__descricao"))
    # Sempre aponta pro /prontuario — paciente ativo via dropdown topbar.
    children.append(
        dcc.Link("Ver prontuário", href="/prontuario",
                 className="hud-btn hud-btn--ghost")
    )

    return html.Div(children, className="hud-panel pacientes-card")


def layout():
    return html.Div([
        html.Div([
            html.H1("Gestão de Perfis"),
            html.P(
                "Caseload do Dr. Robert Chase — 5 pacientes da clínica. "
                "Selecione um perfil no dropdown topbar para abrir o prontuário."
            ),
        ], className="hud-hero"),

        html.Div([
            _card_perfil(pid) for pid in PERFIS_GERENCIADOS
        ], className="pacientes-grid"),

        html.Div([
            html.Em(
                "Para editar dados clínicos, edite data/mocks/perfis_clinicos.json."
            ),
        ], className="hud-info", style={"marginTop": "24px"}),

    ], className="hud-page")
