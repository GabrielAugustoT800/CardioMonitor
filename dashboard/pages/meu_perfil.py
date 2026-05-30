"""Página /meu-perfil — prontuário simplificado do usuário."""
from __future__ import annotations

import dash
from dash import html, dcc
from shared.patient_registry import get_patient

dash.register_page(__name__, path="/meu-perfil", name="Meu Perfil", order=4)


def _info_row(label: str, value) -> html.Div:
    """Linha de informação simples."""
    return html.Div([
        html.Span(f"{label}: ", className="hud-info-label"),
        html.Strong(str(value) if value not in (None, "") else "—"),
    ], className="hud-info-row")


def _list_or_empty(items: list, empty_msg: str = "Nenhum item registrado.") -> html.Div:
    """Renderiza lista ou mensagem de vazio."""
    if not items:
        return html.Div(empty_msg, className="hud-info-empty")
    return html.Ul([
        html.Li(item.get("nome", str(item)) if isinstance(item, dict) else str(item))
        for item in items
    ], className="hud-info-list")


def _render_perfil(perfil: dict | None) -> html.Div:
    if not perfil:
        return html.Div([
            html.H1("Perfil não encontrado"),
            html.P("MEU_PERFIL não está registrado em perfis_clinicos.json."),
        ], className="hud-page")

    return html.Div([
        html.Div([
            html.H1(perfil.get("nome") or "Sem nome", className="hud-hero__title"),
            html.Span(f"ID: {perfil['id']}", className="hud-hero__tag"),
        ], className="hud-hero"),

        # Informações básicas
        html.Section([
            html.H2("Informações Básicas", className="hud-section__title"),
            _info_row("Idade", perfil.get("idade")),
            _info_row("Sexo", perfil.get("sexo")),
            _info_row("Plano", perfil.get("plano")),
            _info_row("Score de risco cardiovascular", perfil.get("score_risco_cardiovascular")),
        ], className="hud-panel"),

        # Condições
        html.Section([
            html.H2("Condições Ativas", className="hud-section__title"),
            _list_or_empty(perfil.get("condicoes_ativas", [])),
        ], className="hud-panel"),

        # Medicações
        html.Section([
            html.H2("Medicações", className="hud-section__title"),
            _list_or_empty(perfil.get("medicacoes_ativas", [])),
        ], className="hud-panel"),

        # Alergias
        html.Section([
            html.H2("Alergias", className="hud-section__title"),
            _list_or_empty(perfil.get("alergias", [])),
        ], className="hud-panel"),

        # Ação: editar via chatbot
        html.Div([
            dcc.Link(
                "Editar via chatbot",
                href="/chat",
                className="hud-btn hud-btn--ghost",
            ),
        ], className="hud-actions"),

        # Nota
        html.Div([
            html.Em(
                "Este perfil é editável via chatbot (tool criar_perfil_paciente) "
                "ou editando diretamente data/mocks/perfis_clinicos.json."
            ),
        ], className="hud-info"),

    ], className="hud-page")


def layout():
    """Layout da página, gerado a cada request.

    Usa def layout() (não constante) pra que get_patient() seja chamado
    a cada visita à página — edita JSON e reflete na próxima abertura
    sem reiniciar app.
    """
    perfil = get_patient("MEU_PERFIL")
    return _render_perfil(perfil)
