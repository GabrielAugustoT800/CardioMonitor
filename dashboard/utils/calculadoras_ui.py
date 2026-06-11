"""UI compartilhada das calculadoras clínicas (fase 9 — fix import duplo).

Separa o que NÃO é callback (renderização + adapters de cálculo) do
módulo de rota (pages/medico/calculadoras.py). Sem essa separação, o
import duplo via use_pages + via from pages.medico.calculadoras provoca
registro duplicado dos @callback da rota → 'Duplicate callback outputs'.

Aqui ficam:
- _render_calculadoras_ui(prefixo, paciente): monta a UI das 4 calc.
- _DISCLAIMER, _label_field, _card_calc, _render_resultado_score: helpers.
- calcular_cha2ds2 / calcular_hb / calcular_egfr / calcular_heart:
  adapters que recebem inputs do UI e retornam componente de resultado.

Callbacks da rota (prefixo 'rota-') ficam em pages/medico/calculadoras.py.
Callbacks do bloco prontuário (prefixo 'pron-') ficam em pages/prontuario.py.
"""

from __future__ import annotations

from dash import html, dcc

from utils.calculadoras import (
    cha2ds2_vasc, has_bled, egfr_ckd_epi, heart_score,
)
from utils.theme import (
    SUCCESS, WARNING, DANGER, TEXT_DARK, TEXT_MUTED, BORDER,
)


_DISCLAIMER = html.Div([
    html.Span("⚠ ", style={"color": WARNING, "fontWeight": "700"}),
    html.Span(
        "Ferramenta de apoio à decisão clínica. Resultados devem ser "
        "interpretados no contexto clínico individual. Não substitui "
        "julgamento médico.",
        style={"color": TEXT_MUTED, "fontStyle": "italic",
               "fontSize": "0.84rem"},
    ),
], style={
    "padding": "10px 14px",
    "background": "rgba(242, 183, 5, 0.10)",
    "borderLeft": f"3px solid {WARNING}",
    "borderRadius": "4px",
    "marginBottom": "16px",
})


def _label_field(texto: str) -> html.Label:
    return html.Label(texto, style={
        "color": TEXT_DARK, "fontWeight": "600",
        "display": "inline-block", "minWidth": "200px",
        "fontSize": "0.86rem",
    })


def _card_calc(titulo: str, ref: str, conteudo, btn_id: str,
               resultado_id: str) -> html.Div:
    return html.Div([
        html.H3(titulo, style={
            "color": TEXT_DARK, "marginBottom": "4px", "fontSize": "1.05rem",
        }),
        html.P(ref, style={
            "color": TEXT_MUTED, "fontSize": "0.78rem",
            "marginBottom": "12px",
        }),
        *conteudo,
        html.Button("Calcular", id=btn_id, n_clicks=0,
                    className="hud-btn",
                    style={"marginTop": "8px", "background": SUCCESS,
                           "borderColor": SUCCESS}),
        html.Div(id=resultado_id, style={"marginTop": "10px"}),
    ], style={
        "padding": "16px 18px", "marginBottom": "14px",
        "background": "rgba(0,0,0,0.02)",
        "border": f"1px solid {BORDER}",
        "borderRadius": "6px",
    })


def _render_calculadoras_ui(prefixo: str = "rota-",
                             paciente: dict | None = None) -> html.Div:
    """Monta as 4 calculadoras. Prefixo evita colisão de IDs entre
    o bloco do prontuário ('pron-') e a rota autônoma ('rota-')."""
    pre_idade = (paciente or {}).get("idade", 0) or 0
    pre_sexo_raw = (paciente or {}).get("sexo", "") or ""
    pre_sexo = "F" if pre_sexo_raw.strip().lower().startswith("f") else "M"

    pre_has = pre_ic = pre_vasc = pre_dm = pre_avc = False
    if paciente:
        for c in paciente.get("condicoes_ativas", []):
            nome = ((c.get("nome") or "") + " " + (c.get("cid") or "")).lower()
            if "hipertens" in nome or "i10" in nome:
                pre_has = True
            if ("insuficiência cardíaca" in nome
                    or "insuficiencia cardiaca" in nome
                    or "i50" in nome):
                pre_ic = True
            if ("infarto" in nome or "i21" in nome or "i25" in nome
                    or "doença vascular" in nome or "dap" in nome):
                pre_vasc = True
            if "diabetes" in nome or nome[:3].startswith("e1"):
                pre_dm = True
            if ("avc" in nome or "ait" in nome
                    or "i63" in nome or "i64" in nome):
                pre_avc = True

    cha_fatores_pre = [k for k, v in [
        ("ic", pre_ic), ("has", pre_has), ("avc", pre_avc),
        ("vasc", pre_vasc), ("dm", pre_dm),
    ] if v]

    cha_conteudo = [
        html.Div([
            _label_field("Idade:"),
            dcc.Input(id=f"{prefixo}cha-idade", type="number",
                      value=pre_idade, min=0, max=120,
                      style={"width": "100px", "marginLeft": "8px"}),
        ], style={"marginBottom": "8px"}),
        html.Div([
            _label_field("Sexo:"),
            dcc.Dropdown(
                id=f"{prefixo}cha-sexo",
                options=[{"label": "Masculino", "value": "M"},
                         {"label": "Feminino", "value": "F"}],
                value=pre_sexo, clearable=False,
                style={"width": "150px", "marginLeft": "8px",
                       "display": "inline-block"},
            ),
        ], style={"marginBottom": "8px"}),
        dcc.Checklist(
            id=f"{prefixo}cha-fatores",
            options=[
                {"label": " Insuficiência cardíaca congestiva", "value": "ic"},
                {"label": " Hipertensão arterial", "value": "has"},
                {"label": " AVC/AIT/TEV prévio", "value": "avc"},
                {"label": " Doença vascular (IAM, DAP, placa aórtica)",
                 "value": "vasc"},
                {"label": " Diabetes mellitus", "value": "dm"},
            ],
            value=cha_fatores_pre,
            style={"color": TEXT_DARK, "marginBottom": "8px"},
            inputStyle={"marginRight": "4px"},
            labelStyle={"display": "block", "marginBottom": "4px"},
        ),
    ]
    cha_card = _card_calc(
        "CHA₂DS₂-VASc",
        "Risco de AVC em FA não-valvar. Ref: ESC 2024.",
        cha_conteudo,
        btn_id=f"{prefixo}cha-btn",
        resultado_id=f"{prefixo}cha-resultado",
    )

    hb_pre = (["e"] if pre_idade > 65 else []) + (["s"] if pre_avc else [])
    hb_conteudo = [
        dcc.Checklist(
            id=f"{prefixo}hb-fatores",
            options=[
                {"label": " Hipertensão descontrolada (PA sist >160)", "value": "h"},
                {"label": " Função renal anormal (Cr >2.3 mg/dL ou diálise)",
                 "value": "r"},
                {"label": " Função hepática anormal (cirrose, bilirrubina >2x)",
                 "value": "l"},
                {"label": " AVC prévio", "value": "s"},
                {"label": " História de sangramento", "value": "b"},
                {"label": " INR lábil (TTR <60%)", "value": "i"},
                {"label": " Idade >65 anos", "value": "e"},
                {"label": " Drogas (antiplaquetários, AINEs) ou álcool",
                 "value": "d"},
            ],
            value=hb_pre,
            style={"color": TEXT_DARK, "marginBottom": "8px"},
            inputStyle={"marginRight": "4px"},
            labelStyle={"display": "block", "marginBottom": "4px"},
        ),
    ]
    hb_card = _card_calc(
        "HAS-BLED",
        "Risco de sangramento maior em anticoagulados. Ref: ESC 2024.",
        hb_conteudo,
        btn_id=f"{prefixo}hb-btn",
        resultado_id=f"{prefixo}hb-resultado",
    )

    pre_idade_egfr = pre_idade if pre_idade >= 18 else 30
    egfr_conteudo = [
        html.Div([
            _label_field("Creatinina (mg/dL):"),
            dcc.Input(id=f"{prefixo}egfr-cr", type="number",
                      value=1.0, min=0.1, max=20, step=0.1,
                      style={"width": "100px", "marginLeft": "8px"}),
        ], style={"marginBottom": "8px"}),
        html.Div([
            _label_field("Idade:"),
            dcc.Input(id=f"{prefixo}egfr-idade", type="number",
                      value=pre_idade_egfr, min=18, max=120,
                      style={"width": "100px", "marginLeft": "8px"}),
        ], style={"marginBottom": "8px"}),
        html.Div([
            _label_field("Sexo:"),
            dcc.Dropdown(
                id=f"{prefixo}egfr-sexo",
                options=[{"label": "Masculino", "value": "M"},
                         {"label": "Feminino", "value": "F"}],
                value=pre_sexo, clearable=False,
                style={"width": "150px", "marginLeft": "8px",
                       "display": "inline-block"},
            ),
        ], style={"marginBottom": "8px"}),
    ]
    egfr_card = _card_calc(
        "eGFR (CKD-EPI 2021)",
        "Taxa de filtração glomerular estimada. Ref: KDIGO 2024.",
        egfr_conteudo,
        btn_id=f"{prefixo}egfr-btn",
        resultado_id=f"{prefixo}egfr-resultado",
    )

    if pre_idade and pre_idade >= 65:
        pre_idade_heart = 2
    elif pre_idade and pre_idade >= 45:
        pre_idade_heart = 1
    else:
        pre_idade_heart = 0

    heart_dropdowns = []
    for key, label, opt0, opt1, opt2 in [
        ("hist", "História:", "Pouco suspeita", "Moderada",
         "Altamente suspeita"),
        ("ecg", "ECG:", "Normal", "Inespecífico",
         "Supra/infra ST significativo"),
        ("idade", "Idade:", "<45", "45-64", "≥65"),
        ("risco", "Fatores de risco:", "Nenhum", "1-2 fatores",
         "≥3 ou aterosclerose"),
        ("trop", "Troponina:", "Normal", "1-3× normal", ">3× normal"),
    ]:
        valor_inicial = pre_idade_heart if key == "idade" else 0
        heart_dropdowns.append(html.Div([
            _label_field(label),
            dcc.Dropdown(
                id=f"{prefixo}heart-{key}",
                options=[
                    {"label": f"0 — {opt0}", "value": 0},
                    {"label": f"1 — {opt1}", "value": 1},
                    {"label": f"2 — {opt2}", "value": 2},
                ],
                value=valor_inicial, clearable=False,
                style={"width": "320px", "display": "inline-block",
                       "marginLeft": "8px"},
            ),
        ], style={"marginBottom": "8px"}))

    heart_card = _card_calc(
        "HEART score",
        "Risco MACE em 6 semanas — dor torácica na emergência. "
        "Ref: Backus et al 2013.",
        heart_dropdowns,
        btn_id=f"{prefixo}heart-btn",
        resultado_id=f"{prefixo}heart-resultado",
    )

    return html.Div([_DISCLAIMER, cha_card, hb_card, egfr_card, heart_card])


# =============================================================================
# Helpers de resultado + adapters (chamados pelos callbacks de cada contexto)
# =============================================================================

def _cor_por_score(score, baixo_lim, alto_lim, invertido=False):
    """Verde se score < baixo_lim, vermelho se >= alto_lim, amarelo entre.
    invertido=True: maior é PIOR (default das calculadoras de risco)."""
    if invertido:
        if score < baixo_lim:
            return SUCCESS
        if score < alto_lim:
            return WARNING
        return DANGER
    return SUCCESS


def _render_resultado_score(label_score: str, conduta: str, cor: str):
    return html.Div([
        html.Div(label_score, style={
            "fontSize": "1.4rem", "fontWeight": "700", "color": cor,
            "fontFamily": "JetBrains Mono, Consolas, monospace",
            "marginBottom": "6px",
        }),
        html.P(conduta, style={
            "color": TEXT_DARK, "margin": 0,
            "fontSize": "0.86rem", "lineHeight": "1.5",
        }),
    ], style={
        "padding": "10px 12px",
        "background": "rgba(255,255,255,0.6)",
        "borderLeft": f"3px solid {cor}",
        "borderRadius": "4px",
    })


def calcular_cha2ds2(idade, sexo, fatores):
    fatores = fatores or []
    try:
        score, conduta = cha2ds2_vasc(
            idade=int(idade or 0),
            sexo=sexo or "M",
            ic_congestiva="ic" in fatores,
            hipertensao="has" in fatores,
            avc_previo="avc" in fatores,
            doenca_vascular="vasc" in fatores,
            diabetes="dm" in fatores,
        )
    except Exception as exc:
        return html.P(f"Erro no cálculo: {exc}", style={"color": DANGER})
    cor = _cor_por_score(score, 2, 3, invertido=True)
    return _render_resultado_score(f"Score: {score} / 9", conduta, cor)


def calcular_hb(fatores):
    fatores = fatores or []
    score, conduta = has_bled(
        hipertensao_descontrolada="h" in fatores,
        funcao_renal_anormal="r" in fatores,
        funcao_hepatica_anormal="l" in fatores,
        avc_previo="s" in fatores,
        sangramento_previo="b" in fatores,
        inr_labil="i" in fatores,
        idade_maior_65="e" in fatores,
        drogas_alcool="d" in fatores,
    )
    cor = _cor_por_score(score, 1, 3, invertido=True)
    return _render_resultado_score(f"Score: {score} / 8", conduta, cor)


def calcular_egfr(cr, idade, sexo):
    try:
        egfr, cls = egfr_ckd_epi(float(cr or 1.0), int(idade or 0),
                                  sexo or "M")
    except (ValueError, TypeError) as exc:
        return html.P(f"Erro no cálculo: {exc}", style={"color": DANGER})
    if egfr >= 60:
        cor = SUCCESS
    elif egfr >= 30:
        cor = WARNING
    else:
        cor = DANGER
    return _render_resultado_score(
        f"eGFR: {egfr} mL/min/1.73m²", cls, cor,
    )


def calcular_heart(h, e, i, r, t):
    try:
        score, conduta = heart_score(int(h or 0), int(e or 0), int(i or 0),
                                      int(r or 0), int(t or 0))
    except ValueError as exc:
        return html.P(f"Erro: {exc}", style={"color": DANGER})
    cor = _cor_por_score(score, 4, 7, invertido=True)
    return _render_resultado_score(f"Score: {score} / 10", conduta, cor)
