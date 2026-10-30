# PRD: Automação do controle diário de parcelas pendentes nas seguradoras

## 1. Alinhamento Estratégico

* **Problema:** A equipe precisa entrar diariamente no portal de cada seguradora, com 4 a 5 cliques por consulta, para descobrir se há parcelas pendentes. O controle é fragmentado e manual, e uma parcela não percebida pode deixar o cliente sem cobertura e gerar perda de comissão.
* **Objetivo do Negócio:** Centralizar a verificação diária em uma única visão, reduzir o esforço operacional e garantir que nenhuma parcela pendente passe despercebida, permitindo crescer a carteira sem aumentar o time na mesma proporção.
* **Métricas de Sucesso (KPIs):**
  * Reduzir em ≥ 90% o tempo diário dedicado à conferência manual nos portais.
  * 100% das parcelas pendentes disponíveis no painel em até 1 dia útil após aparecerem no portal, com zero casos de “sem pendências” causados por falha de coleta.

## 2. Personas & Histórias de Usuário

* **Persona Principal:** Operador de carteira da corretora, responsável por conferir pendências, acionar produtores/clientes e atualizar o controle.
* **Personas Secundárias:** Produtor de seguros, que acompanha as pendências dos seus clientes; e gestor da corretora, que monitora volume, atrasos e confiabilidade da operação.
* **User Stories:**
  * Como operador da corretora, eu quero uma lista consolidada das parcelas pendentes de todas as seguradoras para não precisar acessar cada portal diariamente.
  * Como operador, eu quero identificar o que é novo, o que está a vencer e o que já venceu para priorizar meu trabalho.
  * Como operador, eu quero registrar ação, novo vencimento, data limite e responsável para acompanhar o tratamento de cada pendência.
  * Como produtor, eu quero visualizar as pendências dos meus clientes para orientá-los antes do vencimento.
  * Como gestor, eu quero ver indicadores e o status da coleta de cada seguradora para confiar nos dados exibidos.
  * Como administrador, eu quero habilitar uma nova seguradora por configuração para ampliar a cobertura sem desenvolver uma nova funcionalidade.

## 3. Escopo da Funcionalidade

### O que entra (In Scope)

* **Escopo atual:** coleta automática diária, somente leitura, das **propostas pendentes** nas seguradoras ativas, preferencialmente pela **API oficial** quando disponível.
* **Evolução prevista:** parcelas em atraso de apólices emitidas, já implementadas no plugin Bradesco atrás da flag `BRADESCO_COLLECT_PARCELAS`.
* Separação explícita entre os tipos **Parcela** (apólice emitida) e **Proposta** (1ª parcela/CCB aguardando emissão), com filtro no painel.
* Painel consolidado com seguradora, tipo, segurado, apólice/proposta, ramo, número da parcela, vencimento, valor, produtor e status.
* Destaque de pendências novas, a vencer nos próximos 7 dias e vencidas.
* Workflow de status: Detectada, Em análise, Avisada, Regularizada, Vencida e Descartada.
* Registro de data da ação, ação, novo vencimento, data limite, responsável, produtor e observações.
* Visão **Planilha** e exportação CSV no formato do controle operacional, com DATA AÇÃO, CIA, TIPO, SEGURADO, RAMO, FORMA PAGTO, VENCIMENTO, PARCELA PENDENTE, VIGENCIA AJUSTADA, AÇÃO, PRODUTOR, NOVO VENC, DATA LIMITE e STATUS.
* Filtros por seguradora, tipo, status, segurado, apólice e produtor; busca textual.
* Resumo com total de pendências abertas, a vencer, vencidas e seguradoras com falha de coleta.
* Histórico de alterações de status e de campos de tratamento.
* Status de saúde da coleta por seguradora: última execução, último sucesso e indicação de dados desatualizados.
* Execução manual da coleta sob demanda.
* Exportação CSV da visão filtrada.
* Inclusão e ativação de novas seguradoras por configuração, com validação antes de entrar em operação.
* Resiliência a mudanças na estrutura dos portais: continuar coletando quando possível e sinalizar falha sem gerar dados incorretos.

### O que NÃO entra (Out of Scope)

* Pagamento, emissão de boleto, cancelamento ou alteração de apólice.
* Notificação automática ao cliente por WhatsApp, e-mail ou SMS nesta versão.
* Integração bidirecional com ERP/CRM; o MVP entrega painel próprio e exportação CSV.
* Conciliação de comissões.
* Outros tipos de pendência, como sinistros, renovações e documentos.
* Multiusuário avançado e operação multi-corretora.
* Aplicativo mobile.
* Qualquer tentativa de contornar MFA, captcha ou mecanismos de segurança dos portais.

## 4. Regras de Negócio e Critérios de Aceitação

### Regras de Negócio

* **Definição de parcela pendente:** parcela de apólice já emitida que o portal apresenta como em aberto/não paga; parcelas quitadas não entram no controle.
* **Definição de proposta pendente:** proposta aguardando emissão, com 1ª parcela (CCB) pendente. Não deve ser confundida com parcela de apólice emitida; o painel precisa exibir o tipo.
* **Identidade única:** seguradora + tipo + apólice/proposta + número da parcela + vencimento. Reexecuções não podem duplicar pendências, históricos ou alertas.
* **Status da planilha:** pendências abertas aparecem como `PENDENTE`; regularizadas como `REGULARIZADA`; vencidas como `VENCIDA`; descartadas como `DESCARTADA`.
* **Frequência:** coleta automática em dias úteis, no fuso America/Sao_Paulo, com possibilidade de execução manual.
* **Regularização automática:** uma parcela só pode ser marcada como Regularizada por ausência quando a coleta da seguradora terminar com sucesso. Em caso de falha, os status anteriores são preservados.
* **Reaparecimento:** se uma parcela regularizada reaparecer em coleta posterior, ela deve ser reaberta como Detectada e sinalizada para o operador.
* **Vencimento:** pendências abertas com vencimento anterior à data atual devem ser classificadas como Vencidas diariamente.
* **Atualidade dos dados:** se a última coleta bem-sucedida de uma seguradora tiver mais de 26 horas, o painel deve indicar “dados desatualizados”.
* **Falha explícita:** falha de coleta nunca pode ser exibida como ausência de pendências. Resultados parciais devem ser identificados como tais.
* **Descarte:** a mudança para Descartada exige justificativa registrada e não reabre automaticamente se a parcela reaparecer; o caso deve ser sinalizado.
* **Acesso:** operadores e gestores visualizam toda a carteira; produtores visualizam apenas seus clientes. Toda alteração deve ser auditável.
* **Privacidade:** CPF e demais dados pessoais devem ser mascarados quando não essenciais, com controle de acesso e retenção definida.
* **Somente leitura:** nenhuma ação financeira ou alteração de apólice pode ser executada pela solução.
* **Nova seguradora:** só pode ser ativada após validação de coleta e deve aparecer no painel de saúde com seu status.

### Critérios de Aceitação (Gherkin/Cenários)

* **Cenário 1: Coleta diária com pendências**
  * **Dado que** as seguradoras cadastradas estão ativas e acessíveis
  * **Quando** a coleta diária for executada
  * **Então** o painel deve exibir todas as pendências consolidadas com seguradora, tipo, segurado, apólice/proposta, ramo, parcela, vencimento, valor, produtor e status
  * **E** as pendências novas devem ser destacadas
  * **E** o resumo e a data da última coleta devem ser atualizados
  * **E** uma nova execução no mesmo dia não pode gerar duplicatas

* **Cenário 2: Portal indisponível ou estrutura alterada**
  * **Dado que** uma seguradora está ativa, mas o portal está fora do ar ou sua estrutura mudou
  * **Quando** a coleta for executada
  * **Então** a seguradora deve ser marcada com falha de coleta ou dados desatualizados
  * **E** o painel deve preservar as pendências da última coleta bem-sucedida
  * **E** o operador deve receber um aviso explícito com opção de nova tentativa
  * **E** o sistema não pode exibir “nenhuma pendência” como se a consulta tivesse sido concluída

## 5. Experiência do Usuário (UX) & Estados da Tela

* **Comportamento de Carregamento:** ao executar a coleta, desabilitar o botão, exibir spinner e a mensagem “Consultando seguradoras...”, com progresso por seguradora. A tabela deve mostrar os dados anteriores com o selo “atualizando”, evitando tela em branco.
* **Empty State (Estado Vazio):** se todas as seguradoras ativas concluírem com sucesso e não houver pendências, exibir “Nenhuma parcela pendente encontrada”, com horário da última coleta e próxima execução prevista. Se alguma seguradora falhar, exibir estado parcial com “Não foi possível verificar X seguradora(s)” e botão de nova tentativa — nunca um vazio genérico.
* **Fluxo de Erro:** exibir banner por seguradora com o motivo resumido, a data do último sucesso e ação de tentar novamente. Manter os dados anteriores visíveis com o selo “desatualizado desde...”, registrar a ocorrência para auditoria e destacar o problema no resumo do painel.
* **Sessão expirada:** ao final de uma coleta com sessão inválida, abrir um aviso listando os portais afetados e um link para `/sessions`, onde o operador vê o status e o comando/fluxo de renovação assistida. O sistema não deve tentar contornar reCAPTCHA/MFA.
