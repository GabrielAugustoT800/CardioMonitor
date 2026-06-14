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
    # id e classe inicial pra suportar temas por papel (fase 8).
    # Callback _aplicar_tema_topbar troca className conforme papel-ativo +
    # pathname (login/paciente/medico).
    return html.Header(id="topbar-root",
                       className="hud-topbar hud-topbar--login",
                       children=[
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
                    # Fase 6: options agora sao dinamicas — _popular_dropdown
                    # adapta conforme papel-ativo (paciente ve 5 + separador +
                    # atalho medico; medico ve 5 "voltar como paciente").
                    # Sem value hardcoded — evita disparar callback na carga
                    # inicial antes do login.
                    options=[],
                    placeholder="Selecionar perfil...",
                    clearable=False,
                    className="hud-topbar__dropdown",
                    style={"minWidth": "230px", "marginLeft": "8px"},
                ),
            ]),
            # Botao 'Sair' dedicado (fase 6): limpa Stores + dropdown + vai /login.
            # Sempre visivel — usuario nao logado nem deveria estar aqui mas o
            # guard cuida disso.
            html.Div(className="tel", children=[
                html.Button(
                    "SAIR",
                    id="topbar-logout-btn",
                    n_clicks=0,
                    className="hud-btn hud-btn--ghost",
                    style={
                        "padding": "6px 14px", "fontSize": "0.74rem",
                        "fontWeight": "700", "letterSpacing": "0.08em",
                        "marginLeft": "8px",
                    },
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
    # Fase 6: default None (nao logado) — guard redireciona pro /login.
    # Login (pages/medico/login.py) seta {"role": "paciente"|"medico"}.
    dcc.Store(id="papel-ativo", storage_type="session", data=None),
    # Trigger pra re-render do prontuario apos salvar anotacao clinica (fase 4a).
    # storage_type='memory' — so serve pra disparar callback no mesmo turno;
    # nao precisa persistir entre reloads (o arquivo runtime ja persiste).
    dcc.Store(id="anotacoes-refresh", storage_type="memory", data=0),
    # Trigger pra re-render apos aprovar/editar/rejeitar rascunho (fase 4b).
    # Mesmo padrao: memory, contador incrementado pelo callback de decisao.
    dcc.Store(id="rascunhos-refresh", storage_type="memory", data=0),
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
    # Re-renderiza nav quando rascunho e decidido (fase 4b) — badge da rota
    # /medico/alertas atualiza. Outros gatilhos (paciente fica vermelho,
    # pico aparece) requerem recarregar a pagina; nao automatizamos isso pra
    # nao recalcular alertas a cada Interval de relogio.
    Input("rascunhos-refresh", "data"),
)
def _nav_active(pathname, papel, _rascunhos_refresh):
    role_atual = (papel or {}).get("role", "paciente")
    ordered = sorted(dash.page_registry.values(),
                     key=lambda p: p.get("order", 99))

    # Conta alertas SO no nav medico (evita import + I/O desnecessario no nav
    # do paciente).
    total = 0
    if role_atual == "medico":
        try:
            from utils.alertas import total_alertas
            total = total_alertas()
        except Exception:
            # Degrada gracioso — sem badge se import/IO falhar
            total = 0

    links = []
    for p in ordered:
        # role metadata: ausência = paciente; 'oculto' nunca no nav (/login).
        p_role = p.get("role", "paciente")
        if p_role == "oculto" or p_role != role_atual:
            continue
        href = p["relative_path"]
        is_active = (pathname or "/") == href
        css_class = "hud-nav-link active" if is_active else "hud-nav-link"

        # Badge na rota /medico/alertas (so quando ha alertas pendentes).
        if (role_atual == "medico"
                and href == "/medico/alertas"
                and total > 0):
            children_link = [
                p["name"].upper(),
                html.Span(str(total), style={
                    "background": "#E53E3E", "color": "#fff",
                    "borderRadius": "10px",
                    "padding": "1px 7px", "fontSize": "0.7rem",
                    "fontWeight": "700",
                    "marginLeft": "6px",
                    "fontFamily": "JetBrains Mono, Consolas, monospace",
                }),
            ]
        else:
            children_link = p["name"].upper()

        links.append(dcc.Link(
            children_link,
            href=href,
            className=css_class,
            refresh=False,
        ))
    return links


# Fase 8: tema visual da topbar conforme papel + rota.
# - /login: tema cinza claro (neutro, ponto de entrada).
# - papel=paciente: tema azul (default da .hud-topbar, sem modificador).
# - papel=medico: tema verde denso.
# Pathname tem prioridade sobre papel pra /login — quando o usuario vai pro
# /login (via logout, etc.), a topbar fica neutra mesmo se Store ainda tem
# papel residual num intervalo curto antes de _logout limpar.
@app.callback(
    Output("topbar-root", "className"),
    Input("papel-ativo", "data"),
    Input("hud-url", "pathname"),
)
def _aplicar_tema_topbar(papel_data, pathname):
    if pathname == "/login":
        return "hud-topbar hud-topbar--login"
    papel = (papel_data or {}).get("role")
    if papel == "medico":
        return "hud-topbar hud-topbar--medico"
    if papel == "paciente":
        # default (azul atual) — sem classe modificadora.
        return "hud-topbar"
    # Sem papel valido e fora do /login: estado transicional ate o guard
    # redirecionar. Mostra tema login (neutro) pra nao piscar cores erradas.
    return "hud-topbar hud-topbar--login"


# Fase 6: dropdown topbar agora tem options dinamicas + 2 atalhos especiais.
# _popular_dropdown injeta as opcoes conforme papel-ativo:
#   - paciente: 5 pacientes + separador + atalho "Dr. Robert Chase (visao medico)"
#   - medico:   5 pacientes com label "Voltar como paciente: X"
@app.callback(
    Output("topbar-perfil-dropdown", "options"),
    Input("papel-ativo", "data"),
)
def _popular_dropdown(papel_data):
    """Options dinamicas pro dropdown topbar (fase 6).

    role=paciente: 5 pacientes + separador + atalho medico (6 itens + sep).
    role=medico:   5 entradas 'Voltar como paciente: X' (sem atalho medico).
    role None/desconhecido: cai no default paciente (defensivo).
    """
    pacientes = [
        {"label": "Gabriel Oliveira", "value": "GABRIEL"},
        {"label": "Lucas Andrade",    "value": "LUCAS"},
        {"label": "Maria Almeida",    "value": "MARIA"},
        {"label": "Helena Souza",     "value": "HELENA"},
        {"label": "Pedro Santos",     "value": "PEDRO"},
    ]
    papel = (papel_data or {}).get("role", "paciente")

    if papel == "medico":
        return [
            {"label": f"← Voltar como paciente: {p['label']}",
             "value": p["value"]}
            for p in pacientes
        ]

    # Paciente (default): 5 + separador desabilitado + atalho medico
    return [
        *pacientes,
        {"label": "─────────────────────────",
         "value": "__SEPARATOR__", "disabled": True},
        {"label": "Dr. Robert Chase (visão médico)",
         "value": "__MEDICO_SHORTCUT__"},
    ]


# C13 + fase 6: trocar item do dropdown topbar dispara navegacao contextual.
# 3 fluxos possiveis:
#   - atalho __MEDICO_SHORTCUT__ (paciente -> medico): seta papel=medico,
#     navega /medico/caseload, perfil-ativo intocado.
#   - estando medico, seleciona paciente: seta papel=paciente, perfil-ativo
#     do paciente, navega /prontuario (volta pra visao paciente).
#   - estando paciente, seleciona outro paciente: troca perfil-ativo, navega
#     /prontuario (comportamento da Fase 2B preservado).
# __SEPARATOR__ e ignorado (disabled no dropdown mas defensivo aqui).
@app.callback(
    # allow_duplicate em todos os 3 outputs — sao escritos por outros callbacks
    # (login, caseload, alertas, logout, chat.py para perfil-ativo).
    Output("perfil-ativo", "data", allow_duplicate=True),
    Output("papel-ativo", "data", allow_duplicate=True),
    Output("hud-url", "pathname", allow_duplicate=True),
    Input("topbar-perfil-dropdown", "value"),
    State("papel-ativo", "data"),
    prevent_initial_call=True,
)
def _trocar_perfil_ativo(novo_valor, papel_atual_data):
    if not novo_valor or novo_valor == "__SEPARATOR__":
        return dash.no_update, dash.no_update, dash.no_update

    papel_atual = (papel_atual_data or {}).get("role", "paciente")

    # Atalho medico
    if novo_valor == "__MEDICO_SHORTCUT__":
        return dash.no_update, {"role": "medico"}, "/medico/caseload"

    # Voltar pra paciente (estando como medico)
    if papel_atual == "medico":
        return {"id": novo_valor}, {"role": "paciente"}, "/prontuario"

    # Paciente trocando entre pacientes (Fase 2B preservada)
    return {"id": novo_valor}, dash.no_update, "/prontuario"


# Logout (fase 6): limpa papel-ativo + perfil-ativo + dropdown e vai /login.
# Botao 'SAIR' no topbar dispara este callback.
@app.callback(
    Output("perfil-ativo", "data", allow_duplicate=True),
    Output("papel-ativo", "data", allow_duplicate=True),
    Output("hud-url", "pathname", allow_duplicate=True),
    Output("topbar-perfil-dropdown", "value", allow_duplicate=True),
    Input("topbar-logout-btn", "n_clicks"),
    prevent_initial_call=True,
)
def _logout(n_clicks):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    # papel=None faz o guard redirecionar todas as tentativas pra /login.
    return None, None, "/login", None


# Callback _sync_dropdown_to_url REMOVIDO (fase 2c): sincronizava dropdown
# topbar com pathname das rotas legacy /gabriel e /meu-perfil, que foram
# deletadas. Sem rotas dedicadas, o dropdown e fonte da verdade — _trocar_
# perfil_ativo escreve no Store perfil-ativo e navega pro /prontuario.


# Callback _resetar_tick_rehidratacao REMOVIDO (lote 2 etapa 3): escrevia no
# componente fantasma chat-rehidratar-tick que não existe no layout. A
# rehidratação agora usa Input("beneficiario-select","value") em chat.py.


# Guard de autenticacao estrito (fase 6, substitui _guard_papel da fase 1):
# qualquer rota acessada sem papel-ativo valido redireciona pro /login.
# /login sempre acessivel (sem loop). prevent_initial_call=True garante que
# nao dispare na carga do app — mas o callback dispara apos qualquer
# atualizacao de hud-url.pathname (incluindo navegacao client-side via
# dcc.Link), e ai checa papel.
#
# IMPORTANTE: papel-ativo e STATE (nao Input) — se fosse Input, o callback
# rodaria quando ele mesmo escreve indiretamente (via outros callbacks que
# tocam papel-ativo), gerando loop. Como State, so a navegacao dispara.
@app.callback(
    Output("hud-url", "pathname", allow_duplicate=True),
    Input("hud-url", "pathname"),
    State("papel-ativo", "data"),
    prevent_initial_call=True,
)
def _guard_autenticacao(pathname, papel_data):
    if not pathname:
        return dash.no_update

    # /login sempre acessivel (evita loop quando o proprio guard manda pra la)
    if pathname == "/login":
        return dash.no_update

    # Sem papel valido -> redireciona pro login
    papel = (papel_data or {}).get("role")
    if papel not in ("paciente", "medico"):
        return "/login"

    # Paciente tentando rota /medico/* -> login (mantem proteção da fase 1)
    if pathname.startswith("/medico/") and papel != "medico":
        return "/login"

    return dash.no_update


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
