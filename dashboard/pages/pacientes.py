"""Página /pacientes — gestão de perfis ativos."""
from __future__ import annotations

import dash
from dash import html, dcc
from shared.patient_registry import get_patient

dash.register_page(__name__, path="/pacientes", name="Pacientes", order=6)

PERFIS_GERENCIADOS = ["GABRIEL", "MEU_PERFIL"]


def _card_perfil(perfil_id: str) -> html.Div:
    """Card de um perfil com link pra sua página."""
    perfil = get_patient(perfil_id)
    if not perfil:
        return html.Div([
            html.H3(f"Perfil {perfil_id}"),
            html.P("Não encontrado em perfis_clinicos.json", className="hud-warn"),
        ], className="hud-panel pacientes-card")

    nome = perfil.get("nome") or "Sem nome"
    idade = perfil.get("idade")
    rota = "/gabriel" if perfil_id == "GABRIEL" else "/meu-perfil"
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
    children.append(
        dcc.Link("Ver prontuário", href=rota, className="hud-btn hud-btn--ghost")
    )

    return html.Div(children, className="hud-panel pacientes-card")


def layout():
    return html.Div([
        html.Div([
            html.H1("Gestão de Perfis"),
            html.P(
                "Sistema gerencia 2 perfis: Gabriel (paciente canônico do projeto, "
                "dados completos) e Meu Perfil (usuário do sistema, customizável)."
            ),
        ], className="hud-hero"),

        html.Div([
            _card_perfil(pid) for pid in PERFIS_GERENCIADOS
        ], className="pacientes-grid"),

        html.Div([
            html.Em(
                "Para editar dados do Meu Perfil, use o chatbot (tool "
                "criar_perfil_paciente) ou edite data/mocks/perfis_clinicos.json."
            ),
        ], className="hud-info", style={"marginTop": "24px"}),

    ], className="hud-page")
