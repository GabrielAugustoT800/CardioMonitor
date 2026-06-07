"""
Run with:  python app.py
"""

from __future__ import annotations

# uuid removido: thread_id/cliente_id agora gerados lazy em chat.py
# (_garantir_perfil), não mais no literal do dcc.Store (lote 2 etapa 2).
from datetime import datetime, timezone
from pathlib import Path  # FIX 8.5: pages_folder absoluto

import dash
from dash import Dash, Input, Output, State, dcc, html, no_update

from utils.storage import ensure_csv, DEFAULT_CSV

ensure_csv(DEFAULT_CSV)

# FIX 8.5: pages_folder relativo falha quando rodando de outro cwd
# (descoberto no Passo 8.5 — "python dashboard/app.py" do cwd da raiz
# resolvia "pages" como ./pages em vez de dashboard/pages).
_PAGES_DIR = Path(__file__).resolve().parent / "pages"

app = Dash(
    __name__,
    use_pages=True,
    pages_folder=str(_PAGES_DIR),  # FIX 8.5: caminho absoluto
    suppress_callback_exceptions=True,
    title="Cardio Monitor | HUD",
    update_title=None,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"},
    ],
)
server = app.server


# ---- static layout -------------------------------------------------------

def _nav_links(role_atual: str = "paciente"):
    """Render inicial do nav, filtrado por papel. role metadata no
    register_page: ausência = paciente. 'oculto' nunca aparece (ex: /login).
    O callback _nav_active sobrescreve isto no primeiro pathname, mas o filtro
    aqui evita flash de rotas do papel errado na carga inicial."""
    ordered = sorted(dash.page_registry.values(),
                     key=lambda p: p.get("order", 99))
    links = []
    for p in ordered:
        p_role = p.get("role", "paciente")
        if p_role == "oculto" or p_role != role_atual:
            continue
        links.append(dcc.Link(
            p["name"].upper(),
            href=p["relative_path"],
            className="hud-nav-link",
            refresh=False,
        ))
    return links


def _topbar():
    return html.Header(className="hud-topbar", children=[
        html.Div(className="hud-topbar__brand", children=[
            html.Span("C+", className="mark"),
            html.Div([
                html.Div("CardioMonitor"),
                html.Small("Clinical Telemetry // telemetria clínica"),
            ]),
        ]),
        html.Nav(className="hud-topbar__nav", id="hud-nav", children=_nav_links()),
        html.Div(className="hud-topbar__telemetry", children=[
            # C13: dropdown de perfil ativo (atalho de navegação contextual).
            # Posicionado dentro da seção telemetria pra preservar grid CSS
            # upstream (auto/1fr/auto — 3 colunas). 4º elemento direto no
            # Header quebraria o grid.
            html.Div(className="tel", children=[
                html.Span("PERFIL", className="lbl"),
                dcc.Dropdown(
                    id="topbar-perfil-dropdown",
                    # Fase 2B: dropdown topbar lista os 5 pacientes da clinica
                    # do Dr. Chase. Selecionar -> _trocar_perfil_ativo navega
                    # pro /prontuario (render data-driven via render_prontuario).
                    options=[
                        {"label": "Gabriel Oliveira", "value": "GABRIEL"},
                        {"label": "Lucas Andrade",    "value": "LUCAS"},
                        {"label": "Maria Almeida",    "value": "MARIA"},
                        {"label": "Helena Souza",     "value": "HELENA"},
                        {"label": "Pedro Santos",     "value": "PEDRO"},
                    ],
                    value="GABRIEL",
                    clearable=False,
                    className="hud-topbar__dropdown",
                    style={"minWidth": "180px", "marginLeft": "8px"},
                ),
            ]),
            html.Div(className="tel", children=[
                html.Span(className="sig-dot"),
                html.Span("LINK", className="lbl"),
                html.Span("ACTIVE", className="val"),
            ]),
            html.Div(className="tel", children=[
                html.Span("UTC", className="lbl"),
                html.Span(id="hud-clock", className="val", children="--:--:--"),
            ]),
            html.Div(className="tel", children=[
                html.Span("DATE", className="lbl"),
                html.Span(id="hud-date", className="val", children="----"),
            ]),
        ]),
    ])


def _footer():
    return html.Footer(className="hud-footer", children=[
        html.Span("⚕️ Este sistema não substitui avaliação médica · "
                  "Em emergência: SAMU 192"),
    ])


app.layout = html.Div(className="app-shell", children=[
    dcc.Location(id="hud-url"),
    dcc.Interval(id="hud-clock-tick", interval=1000, n_intervals=0),
    # CHAT INTEGRATION: estado de sessão do chatbot preservado entre páginas.
    # storage_type default ("memory") — vai zerar ao recarregar a aba.
    # Para sobreviver a refresh, mudar para storage_type="session".
    # session-data segmentado por paciente (lote 2 etapa 2):
    # storage_type="local" sobrevive F5/fechar aba (era "session").
    # cliente_id gerado LAZY no 1o turno em chat.py (era str(uuid.uuid4())
    # no literal = avaliado 1x no import, igual pra todos os clientes ->
    # cross-talk). Estrutura: {cliente_id, perfis: {GABRIEL: {...}, ...}}.
    dcc.Store(id="session-data", storage_type="local", data={
        "cliente_id": None,
        "perfis": {},
    }),
    # C13: perfil ativo (atalho de navegação contextual entre Gabriel e Meu Perfil)
    # storage_type="session" (não "local") — zera ao fechar aba pra evitar
    # dessincronização entre dropdown (value="GABRIEL" hardcoded) e Store
    # persistido com valor de sessão anterior. Telemetria (/monitor, /analise)
    # NÃO consome este Store — upstream usa dataset Azure Blob único.
    dcc.Store(id="perfil-ativo", data={"id": "GABRIEL"}, storage_type="session"),
    # Papel ativo (app médico, fase 1): "paciente" (default, não quebra o
    # estado atual) ou "medico". Setado no /login, lido pelo nav filtrado +
    # guard de rota. storage_type="session" zera ao fechar aba.
    dcc.Store(id="papel-ativo", storage_type="session", data={"role": "paciente"}),
    # Stores meu-perfil-refresh e meu-perfil-reload-dummy REMOVIDOS (fase 2c):
    # workaround do J.1.b pra reload do formulario de criacao de /meu-perfil.
    # /meu-perfil foi deletado, callbacks orfaos cairam com ele.

    # CHAT INTEGRATION: audio element global pra alerts do chatbot
    html.Audio(id="audio-alert", src="/assets/alert.wav",
               className="blua-audio-alert", autoPlay=False),
    _topbar(),
    html.Main(dash.page_container, className="hud-page"),
    _footer(),
])


# ---- clock / nav active-state callbacks ---------------------------------

@app.callback(
    Output("hud-clock", "children"),
    Output("hud-date", "children"),
    Input("hud-clock-tick", "n_intervals"),
)
def _tick(_n):
    now = datetime.now(timezone.utc)
    return now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d")


@app.callback(
    Output("hud-nav", "children"),
    Input("hud-url", "pathname"),
    Input("papel-ativo", "data"),
)
def _nav_active(pathname, papel):
    role_atual = (papel or {}).get("role", "paciente")
    ordered = sorted(dash.page_registry.values(),
                     key=lambda p: p.get("order", 99))
    links = []
    for p in ordered:
        # role metadata: ausência = paciente; 'oculto' nunca no nav (/login).
        p_role = p.get("role", "paciente")
        if p_role == "oculto" or p_role != role_atual:
            continue
        href = p["relative_path"]
        is_active = (pathname or "/") == href
        css_class = "hud-nav-link active" if is_active else "hud-nav-link"
        links.append(dcc.Link(
            p["name"].upper(),
            href=href,
            className=css_class,
            refresh=False,
        ))
    return links


# C13: dropdown de perfil ativo (atalho de navegação contextual).
# Atualiza dcc.Store(perfil-ativo) E navega pra rota do prontuário escolhido.
# Não filtra telemetria — upstream usa dataset Azure Blob único sem coluna
# patient (decisão tomada em H.A.3 após investigação).
@app.callback(
    # allow_duplicate=True em perfil-ativo: chat.py:440
    # (_sync_store_from_chat_dropdown) também escreve nesse Store.
    Output("perfil-ativo", "data", allow_duplicate=True),
    Output("hud-url", "pathname", allow_duplicate=True),
    Input("topbar-perfil-dropdown", "value"),
    prevent_initial_call=True,
)
def _trocar_perfil_ativo(perfil_id):
    """Trocar paciente no dropdown topbar -> atualiza Store + navega
    pro /prontuario (decisao 'dropdown como navegacao principal',
    fase 2B). Os 5 pacientes (GABRIEL, LUCAS, MARIA, HELENA, PEDRO)
    rendem o mesmo prontuario data-driven via render_prontuario."""
    if not perfil_id:
        return dash.no_update, dash.no_update
    return {"id": perfil_id}, "/prontuario"


# Callback _sync_dropdown_to_url REMOVIDO (fase 2c): sincronizava dropdown
# topbar com pathname das rotas legacy /gabriel e /meu-perfil, que foram
# deletadas. Sem rotas dedicadas, o dropdown e fonte da verdade — _trocar_
# perfil_ativo escreve no Store perfil-ativo e navega pro /prontuario.


# Callback _resetar_tick_rehidratacao REMOVIDO (lote 2 etapa 3): escrevia no
# componente fantasma chat-rehidratar-tick que não existe no layout. A
# rehidratação agora usa Input("beneficiario-select","value") em chat.py.


# Guard de papel (app médico, fase 1): paciente tentando rota /medico/* é
# redirecionado pro /login. allow_duplicate=True porque hud-url.pathname já
# tem escritores (_trocar_perfil_ativo + login). prevent_initial_call=True
# pra não disparar na carga inicial.
@app.callback(
    Output("hud-url", "pathname", allow_duplicate=True),
    Input("hud-url", "pathname"),
    State("papel-ativo", "data"),
    prevent_initial_call=True,
)
def _guard_papel(pathname, papel):
    role = (papel or {}).get("role", "paciente")
    if pathname and pathname.startswith("/medico/") and role != "medico":
        return "/login"
    return dash.no_update


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
