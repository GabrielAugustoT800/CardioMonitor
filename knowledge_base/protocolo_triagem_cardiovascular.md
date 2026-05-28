# Protocolo de Triagem Cardiovascular Digital
## BluaDiagnostics — Base de Conhecimento Clínico
### Fonte: Sistema de Triagem de Manchester (STM) adaptado para contexto digital
### Referências: souenfermagem.com.br, telemedicinamorsch.com.br, totvs.com.br, rmmg.org
### Versão: 1.0.0 | 2026-05-15

---

## 1. O que é a Triagem Cardiovascular Digital

A triagem cardiovascular digital é o processo de avaliação inicial
de sintomas cardíacos relatados pelo beneficiário, com o objetivo de
classificar o nível de urgência e direcionar para o atendimento mais
adequado — desde orientação preventiva até encaminhamento imediato
ao SAMU.

O BluaDiagnostics adapta os princípios do Sistema de Triagem de
Manchester (STM) para o contexto de atendimento digital conversacional,
reconhecendo suas limitações: a triagem digital não substitui avaliação
presencial e não realiza ECG — discriminador fundamental para síndrome
coronariana aguda.

---

## 2. Classificação de Urgência — Escala de Cores Adaptada

O STM utiliza cinco cores para classificar a urgência clínica. No
contexto digital cardiovascular, o BluaDiagnostics opera com três
níveis funcionais:

### Nível Vermelho — Emergência (Atendimento Imediato)

Risco iminente de vida. O agente encerra qualquer outro fluxo e
instrui o beneficiário a ligar para 192 (SAMU) ou ir ao pronto-socorro
imediatamente.

Sintomas cardiovasculares que acionam nível vermelho:
- Dor torácica intensa com irradiação para braço esquerdo, mandíbula
  ou costas, com duração superior a 15 minutos
- Dor torácica que não melhora com repouso ou mudança de posição,
  acompanhada de suor frio e falta de ar
- Suspeita de AVC — confusão mental súbita, assimetria facial,
  fraqueza ou dormência unilateral, dificuldade de fala
- Parada cardiorrespiratória ou perda de consciência súbita
- Pressão arterial acima de 180x120 mmHg com sintomas neurológicos
  ou dor torácica

Conduta do agente: "O que você está descrevendo pode indicar uma
emergência cardíaca. Ligue agora para 192 (SAMU) ou peça para alguém
te levar ao pronto-socorro. Não dirija sozinho."

### Nível Laranja — Muito Urgente (Atendimento em até 10 minutos)

Condição grave sem risco iminente imediato. O agente agenda
teleconsulta com urgência máxima e orienta monitoramento contínuo
até o atendimento.

Sintomas cardiovasculares que acionam nível laranja:
- Dor torácica atípica sem irradiação, com duração inferior a 15
  minutos, que melhora parcialmente com repouso
- Arritmia cardíaca com tontura ou pré-síncope (quase desmaio)
- Palpitações intensas e sustentadas com mal-estar associado
- Pressão arterial acima de 180x120 mmHg sem sintomas neurológicos
- Dispneia moderada em repouso sem histórico de asma ou DPOC
- Edema súbito de membros inferiores com falta de ar

Conduta do agente: Agendar teleconsulta urgente. Orientar repouso,
não dirigir, não ficar sozinho. Instruir ligar para 192 se piorar.

### Nível Amarelo/Verde — Urgente e Rotina

Condição que requer atenção médica mas sem risco imediato. O agente
conduz o check-up completo e oferece agendamento prioritário ou de
rotina conforme avaliação.

Sintomas cardiovasculares que acionam nível amarelo:
- Palpitações episódicas sem mal-estar associado
- Pressão arterial entre 140x90 e 180x120 mmHg sem sintomas agudos
- Tontura postural isolada, sem síncope
- Cansaço fora do usual sem dispneia em repouso
- Dúvidas sobre medicação cardiovascular

---

## 3. Fluxo de Triagem Digital — Perguntas Guiadas

O agente conduz a triagem por meio de perguntas estruturadas, uma
por vez, seguindo esta sequência:

### Passo 1 — Sintoma Principal
"O que está sentindo hoje?" — identificar o sintoma principal relatado.

### Passo 2 — Localização e Irradiação
Para dor: "Onde exatamente você sente a dor? Ela se irradia para
algum outro lugar, como braço, mandíbula ou costas?"

### Passo 3 — Tempo de Evolução
"Há quanto tempo está sentindo isso? O sintoma é contínuo ou vai
e vem?"

### Passo 4 — Sintomas Associados
"Junto com isso, você está sentindo falta de ar, tontura, suor
frio, náusea ou palpitações?"

### Passo 5 — Fatores de Alívio ou Piora
"O sintoma melhora com repouso? Piorou com esforço físico ou
emoção?"

### Passo 6 — Histórico Relevante
Consultar `consultar_historico_paciente` para verificar condições
preexistentes antes de classificar o risco.

### Passo 7 — Classificação e Conduta
Com base nas respostas, classificar em vermelho, laranja ou
amarelo/verde e adotar a conduta correspondente.

---

## 4. Limitações da Triagem Digital

O STM foi desenvolvido para triagem presencial com acesso a ECG,
oximetria e ausculta cardíaca. A triagem digital apresenta limitações
importantes que o agente deve reconhecer:

- Não é possível realizar ECG — discriminador fundamental para
  síndrome coronariana aguda. Estudos mostram que até 21% dos
  infartos com supradesnivelamento de ST foram classificados
  erroneamente como urgente-amarelo sem ECG disponível.
- Não é possível auscultar o coração ou medir pressão arterial
  diretamente — o agente depende dos valores relatados pelo
  beneficiário.
- A variabilidade na apresentação clínica de síndromes coronarianas
  é alta — especialmente em mulheres, diabéticos e idosos, que
  frequentemente apresentam sintomas atípicos.

Por essas razões, o agente deve ter viés conservador: na dúvida
entre dois níveis de urgência, classificar sempre no nível mais
alto.

---

## 5. Considerações Especiais por Perfil de Paciente

### Mulheres
Sintomas de infarto em mulheres são frequentemente atípicos —
náusea, fadiga intensa, dor nas costas ou mandíbula sem dor
torácica clássica. O agente deve manter alto índice de suspeita
mesmo sem dor torácica típica.

### Idosos
Podem apresentar dispneia como equivalente anginoso — falta de ar
sem dor torácica pode ser a única manifestação de infarto em
pacientes acima de 75 anos.

### Diabéticos
Neuropatia autonômica pode mascarar a dor isquêmica. Infarto
silencioso é mais comum nessa população.

### Hipertensos em uso de betabloqueadores
Betabloqueadores como Atenolol podem mascarar taquicardia
compensatória — a frequência cardíaca pode parecer normal mesmo
em situações de emergência.

---

## 6. Integração com o Modelo de ML de Detecção de Arritmias

O BluaDiagnostics integra um modelo de Machine Learning treinado
para classificar ritmo cardíaco como regular ou irregular a partir
de dados de IBI (Intervalo Entre Batimentos).

A triagem digital usa esse modelo como dado objetivo complementar
à triagem sintomática:

- Ritmo regular + sintomas leves → nível amarelo/verde
- Ritmo irregular + sintomas moderados → nível laranja
- Ritmo irregular + síncope ou pré-síncope → nível vermelho

O sistema de alerta automático dispara notificação quando 4 ou 5
registros consecutivos na janela deslizante de 5 são classificados
como irregulares — sinal de arritmia sustentada que requer avaliação
médica urgente.

---

*Documento elaborado para fins acadêmicos. Não substitui protocolo
clínico institucional nem avaliação médica presencial.*
*Em emergência: ligue 192 (SAMU).*