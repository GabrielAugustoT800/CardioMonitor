# Políticas Care Plus — Telemedicina e Plataforma Blua
## BluaDiagnostics — Base de Conhecimento Clínico
### Fonte: careplus.com.br, exame.com (out/2024), blogdocorretor.com (fev/2024)
### Versão: 1.0.0 | 2026-05-15

---

## 1. A Plataforma Blua

A Blua é a plataforma de saúde digital da Care Plus, lançada em
dezembro de 2023. Unifica os serviços digitais de saúde da
operadora em um único aplicativo, com o objetivo de transformar
a jornada do cuidado — de reativa para proativa.

A plataforma já é utilizada por mais de 25% dos beneficiários
da Care Plus. No primeiro semestre de 2024, foram registradas
42 mil consultas virtuais pela plataforma.

---

## 2. Serviços Disponíveis na Blua

### Teleconsulta
Consultas médicas com especialistas por videoconferência,
acessíveis pelo aplicativo Care Plus. Inclui:
- Pronto-atendimento virtual — disponível a qualquer momento,
  sem agendamento prévio
- Consultas com especialistas agendadas — incluindo cardiologia

### Telepsicologia
Atendimento psicológico por videoconferência. Canal adequado
para questões de saúde mental — fora do escopo do BluaDiagnostics.

### Programas Preventivos
Programas de acompanhamento de saúde incluindo prevenção de
doenças cardiovasculares — área de atuação direta do
BluaDiagnostics.

### Teste de Bem-Estar
Recurso inédito no Brasil que avalia sinais biométricos em tempo
real por câmera do smartphone — batimentos cardíacos, nível de
estresse e saúde da pele via medição óptica transdérmica com
inteligência artificial.

### Gestão de Plano
Autorização e reimbursamento, rede credenciada, IRPF, entre outros.

---

## 3. Como Agendar Teleconsulta pelo Blua

O agente BluaDiagnostics pode acionar o agendamento via tool
`agendar_teleconsulta`. Do ponto de vista do beneficiário, o
fluxo no aplicativo é:

1. Abrir o aplicativo Care Plus
2. Acessar o menu Blua
3. Selecionar Teleconsulta
4. Escolher entre Pronto Atendimento Virtual ou consulta agendada
5. Selecionar especialidade (Cardiologia para casos cardiovasculares)
6. Confirmar horário e receber link de acesso

Para urgências cardiovasculares identificadas pelo agente, o
pronto-atendimento virtual é o canal mais rápido — sem necessidade
de agendamento prévio.

---

## 4. Níveis de Urgência no Agendamento

O BluaDiagnostics classifica o agendamento em três níveis
conforme a avaliação clínica:

### Urgente
Disponibilidade em aproximadamente 20 minutos via plantão
cardiológico. Acionado quando há red flag cardiovascular sem
indicação de SAMU imediato — arritmia com síncope, pressão
acima de 180x120 sem sintoma neurológico, dor torácica atípica
com outros fatores de risco.

### Prioritário
Disponibilidade no mesmo dia. Acionado quando há sintoma
cardiovascular ativo que requer avaliação nas próximas horas —
palpitações com mal-estar, ritmo irregular detectado pelo ML,
interação medicamentosa moderada ou grave identificada.

### Rotina
Próxima disponibilidade em dias. Acionado para retornos
preventivos, dúvidas sobre medicação sem urgência, check-up
sem alterações.

---

## 5. Cobertura de Telemedicina — Aspectos Regulatórios

A telemedicina no Brasil é regulamentada pela CFM Resolução
2.314/2022, que estabelece:

- Teleconsulta é permitida em todas as especialidades médicas
- O médico deve ser devidamente identificado e registrado no CRM
- A prescrição digital requer assinatura eletrônica qualificada
  (ICP-Brasil) pelo médico responsável
- O prontuário eletrônico deve ser mantido pelo médico

O BluaDiagnostics opera dentro desses limites — nunca emite
prescrição, nunca assina documentos médicos, sempre encaminha
para aprovação do médico cardiologista responsável.

---

## 6. Programa de Prevenção Cardiovascular Care Plus

A Care Plus oferece programa específico de prevenção de doenças
cardiovasculares, que inclui:

- Acompanhamento com cardiologista, nutricionista e enfermeira
- Monitoramento de pressão arterial e frequência cardíaca
- Orientação sobre hábitos de vida — alimentação, exercício,
  cessação do tabagismo
- Integração com dados de wearables para monitoramento contínuo

O BluaDiagnostics é parte da evolução desse programa —
transformando o acompanhamento reativo em cuidado proativo
com check-up digital conversacional e detecção precoce de
alterações cardiovasculares.

---

## 7. Privacidade e LGPD na Plataforma Blua

Os dados de saúde dos beneficiários são classificados como dados
sensíveis pela LGPD (Lei 13.709/2018, art. 11) e exigem:

- Consentimento explícito do titular para tratamento
- Finalidade específica e informada
- Armazenamento em território nacional
- Direitos de acesso, portabilidade e exclusão garantidos ao
  beneficiário
- Nomeação de Encarregado de Dados (DPO) pela operadora

O BluaDiagnostics, em sua versão de PoC acadêmica, utiliza
dados exclusivamente mockados — sem dados reais de beneficiários.
Em produção, exigiria conformidade completa com LGPD e
certificação SBIS.

---

*Documento elaborado para fins acadêmicos com base em informações
públicas da Care Plus (careplus.com.br) e legislação vigente.*
*Informações sobre cobertura e serviços podem ser alteradas pela
operadora sem aviso prévio.*