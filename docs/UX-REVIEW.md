# Revisão de UX/UI — Corretor RPA

- **Data:** 06/11/2026
- **Escopo:** Painel, Planilha, Detalhe da pendência, Sessões, Plugins e Execuções
- **Cenário avaliado:** 4 seguradoras simuladas (uma saudável, uma com falha, uma sem coleta e uma desatualizada) e dados fictícios do adapter demo
- **Método:** inspeção dos templates/rotas + capturas em desktop (1440 px) e mobile (390 px)

> As capturas usam apenas dados fictícios de demonstração. O cenário multi-seguradora foi simulado para revelar problemas de escala. Os PNGs ficam em docs/ux-review/ e são mantidos localmente (o .gitignore do projeto ignora imagens).

---

## 0. Status de implementação (06/11/2026)

A **Fase 1 do P0** já foi aplicada:

- decisão **single-tenant**: uma corretora, várias seguradoras;
- fila abre em **Abertas**; “Todas (inclui fechadas)” explícito; filtros refletidos na URL, com recarga completa correta e “Limpar filtros”;
- estados unificados por seguradora (**Em dia, Falha, Parcial, Aguardando intervenção, Desatualizada, Sem coleta**) no card, nas pills e no painel;
- painel **“Precisa de atenção”** com resumo amigável, “Detalhes técnicos” e ação por seguradora (**Tentar novamente**, **Coletar agora**, **Renovar conexão**);
- pills de seguradora clicáveis para filtrar o painel;
- navegação separada em operação (**Painel, Planilha, Seguradoras**) e administração (**Coletas, Conexões**), com página ativa e skip link;
- mobile sem estouro horizontal: **390 px de viewport = 390 px de página**.

![Painel após a Fase 1](ux-review/dashboard-after.png)

![Painel mobile após a Fase 1](ux-review/dashboard-mobile-after.png)

Ainda pendente para as próximas fases: paginação/ordenação e ações em lote na tabela, confirmação/desfazer na mudança de status, colunas fixas na Planilha, orientação de status e “motivo da alteração” no Detalhe, controles de teste escondidos em Conexões, foco no modal e outros ajustes de acessibilidade. As seções 1–3 preservam o diagnóstico original e servem de baseline para o que falta.

---

## 1. Veredito em uma frase

A base visual é limpa e consistente, mas hoje a interface foi desenhada para **uma seguradora e um operador técnico**. Para várias seguradoras, ela mistura **operação** com **administração técnica**, não responde com clareza “o que precisa da minha atenção agora?” e não oferece ações no lugar certo — especialmente quando algo falha.

Os três riscos que mais geram confusão:

1. **Status divergentes entre resumo, pills, painel de falhas e tabela.** O usuário vê “2 seguradoras com falha”, mas só uma aparece em “Falhas na coleta”.
2. **Linguagem e navegação de desenvolvedor** (Plugins, Sessões, Execuções, healthz, “Capabilities”, caminho de state.json) em um produto que será usado por operação.
3. **Densidade e mobile.** Tabelas de 10–15 colunas, sem paginação nem priorização, e topbar que estoura a largura no celular.

**Decisão de produto (06/11/2026): single-tenant.** O sistema atende **uma única corretora**, com **várias seguradoras**. Não haverá seletor de corretora nem isolamento multi-tenant; operação multi-corretora já está fora do escopo do PRD. A multiplicidade que a UX precisa resolver é a de **seguradoras**.

---

## 2. O que já está bom

- Identidade visual simples, legível e coerente; cores semânticas (vermelho, amarelo, verde) com texto, não só cor.
- Hierarquia clara no painel: página → filtros → resumo → seguradoras → pendências → execuções.
- Filtros ficam fora do bloco trocado pelo HTMX, preservando foco durante a digitação.
- Erros de coleta já ficam visíveis e persistentes (última entrega), com detalhe expansível.
- Página de detalhe com formulário completo e histórico de eventos.
- Planilha operacional e exportação CSV alinhadas ao processo da corretora.
- Stack enxuta, sem build step; HTMX dá feedback rápido.

---

## 3. Diagnóstico por tela

### 3.1 Painel

![Painel atual com 4 seguradoras simuladas](ux-review/dashboard.png)

**Problemas principais**

1. **Números que não batem.** O card mostra “2 Seguradoras com falha · de 4”, mas o painel “Falhas na coleta” lista só a Porto Seguro. A SulAmérica (sem nenhuma coleta) entra no card como falha, mas não entra no painel porque nunca teve execução com erro. Para o usuário, é um bug de confiança.
2. **Filtro padrão “Todos” inclui itens fechados.** O resumo conta apenas pendências abertas, mas a tabela mostra também REGULARIZADA/DESCARTADA. Com histórico, a tabela enche de itens que não exigem ação e os números do topo deixam de corresponder ao que está na tela.
3. **Falta ação por seguradora.** “Coletar agora” é global. Quando a Porto falha, o usuário não tem “Tentar novamente” ali: precisa rodar todas as seguradoras de novo e esperar.
4. **Erro cru, sem tradução.** “Timeout de 60000ms aguardando a tabela de parcelas…” é linguagem de suporte técnico. O operador precisa de “Portal não respondeu. Verifique a conexão e tente novamente” + “Detalhes técnicos”.
5. **Pills não são clicáveis.** Allianz, Porto, Demo e SulAmérica parecem filtros, mas são apenas indicadores. O usuário tenta clicar.
6. **Coluna “Ação / Prazo” mistura coisas.** Ação, novo vencimento, data limite e alerta (“Com crítica”) dividem a mesma célula. O cabeçalho não descreve o conteúdo.
7. **Mudança de status sem rótulo, confirmação ou desfazer.** O select da linha altera o workflow imediatamente via HTMX. Um clique errado gera evento de auditoria e some da fila sem aviso.
8. **Sem paginação, ordenação ou agrupamento.** A consulta limita silenciosamente a 1.000 linhas. Com muitas seguradoras/apólices, o usuário não sabe que há mais dados.
9. **Sem “limpar filtros”, sem estado na URL e vazio genérico.** Ao filtrar e não achar nada, a mensagem é “Nenhuma parcela pendente encontrada” — não “nenhum resultado para estes filtros”. O filtro não vai para a URL, então não dá para compartilhar/voltar.
10. **“Últimas execuções” e “healthz” são técnicos demais** no meio da operação.

### 3.2 Mobile

![Painel no mobile: topbar e tabela estouram a largura](ux-review/dashboard-mobile.png)

Medição real: a página tem **514 px de largura** em uma viewport de **390 px**. A causa é a topbar (nav), não só a tabela.

- “Plugins” fica cortado; a navegação não cabe e não vira menu.
- A tabela mostra só as primeiras colunas e não há indicação visual de rolagem horizontal.
- Os 4 cards ficam um por linha, ocupando quase uma tela inteira antes do conteúdo útil.
- Filtros ocupam muito espaço vertical; poderiam virar um painel recolhível.
- O botão de ação principal não fica acessível durante a rolagem.

### 3.3 Planilha

![Planilha operacional com 15 colunas](ux-review/planilha.png)

- 15 colunas com nowrap; a tabela corta em “AÇÃO” e depende de rolagem horizontal sem primeira coluna fixa.
- Título duplicado (“Controle de parcelas pendentes” na página e no painel).
- Interação inconsistente com o painel: aqui existe botão “Filtrar”; no painel, os filtros aplicam sozinhos.
- O objetivo da tela não está claro em relação ao Painel. Se ela existe para exportar/operar no formato da planilha, o “Exportar planilha” deveria ser a ação principal, e a tabela deveria ter colunas fixas e agrupamento.
- Não há link visível para abrir o detalhe sem rolar até o fim.

### 3.4 Detalhe da pendência

![Detalhe da pendência](ux-review/detail.png)

- O status aparece no topo e de novo no formulário; se o usuário mudar o select sem salvar, o topo continua mostrando o valor antigo.
- Campos técnicos (“ID externo”, “Status no portal”) no meio dos dados operacionais.
- Datas nativas aparecem como mm/dd/yyyy em navegador com locale inglês; usuários em pt-BR veem outro formato. Vale padronizar a experiência.
- Não há texto de ajuda sobre o significado dos status (ex.: “Regularizada sai da fila”, “Descartada não reabre automaticamente”).
- “Salvar tratamento” fica só no fim; em telas pequenas o usuário pode editar e não ver o botão.
- Não existe campo “Motivo da alteração” — o histórico registra a transição, mas não o porquê.
- Não há aviso de alterações não salvas ao sair.

### 3.5 Sessões

![Sessões dos portais](ux-review/sessions.png)

- Cards são um bom começo, mas misturam inglês (“ok”) e português; os badges não seguem o mesmo vocabulário do resto do produto.
- O aviso global diz que “o sistema tenta renovar a sessão automaticamente”, mas isso só existe para o Bradesco. Com várias seguradoras, a promessa fica falsa.
- Seguradoras sem renovação mostram um texto sem ação (“Este portal ainda não possui fluxo…”), um beco sem saída.
- “Forçar expiração da sessão” e o comando de terminal são controles de teste/desenvolvedor expostos na tela de operação.
- Não há “Testar conexão”, “Atualizar agora” nem indicação de quando será a próxima verificação.
- O caminho data/sessions/bradesco.json é detalhe interno.

### 3.6 Plugins

![Página de plugins](ux-review/plugins.png)

- É a tela mais técnica do produto: “Plugins”, “Adapters descobertos em runtime”, “descoberta”, “pronto”, “v0.1.0 · python”, “Capabilities: read_only”, “Sessão: necessária”.
- O nome “Plugins” não significa nada para a operação; o usuário pensa em “Seguradoras”.
- Não há ação de negócio: adicionar, ativar/desativar, testar conexão, renovar acesso, ver pendências daquela seguradora.
- A página lista manifests, não necessariamente todas as seguradoras ativas do banco; no cenário, Allianz/Porto/SulAmérica aparecem no painel e não aqui.
- O caminho do state.json e a versão do adapter são detalhes que deveriam ficar em “Administração > Detalhes técnicos”.

### 3.7 Execuções

![Histórico de execuções](ux-review/runs.png)

- Sem filtro por seguradora, status ou período; com várias seguradoras, vira uma lista longa e ruidosa.
- “Itens / Novas / Resolvidas” são úteis, mas não há duração, horário de término nem link para a seguradora.
- Não há ação “Tentar novamente” a partir da falha.
- O erro completo fica em details (bom), mas o resumo ainda é o texto técnico.
- O nome “Execuções” é interno; para a operação, “Coletas” ou “Atualizações” comunica melhor.

### 3.8 Navegação e linguagem

- A navegação principal mistura operação (Painel, Planilha) e administração (Sessões, Execuções, Plugins) no mesmo nível, sem separação.
- Não há indicação de página ativa (aria-current / estilo).
- “Coletar agora”, “Marcar vencidas”, “Sessões”, “Plugins”, “Execuções” e “healthz” são termos de engenharia.
- Não há contexto de usuário no topo. Como o produto é single-tenant, não é necessário seletor de corretora; um menu de usuário/perfil ainda ajuda.
- O rodapé “healthz” expõe um endpoint técnico para o usuário final.

---

## 4. Arquitetura de informação proposta

### Navegação principal (operação)

    Painel | Pendências | Planilha | Seguradoras          [Usuário ▾]

### Administração (menu secundário ou “Engrenagem”)

    Coletas | Configurações | Auditoria | Status do sistema

- **Painel:** resposta rápida para “o que precisa de atenção hoje?”.
- **Pendências:** a tabela completa, com filtros, visões salvas, paginação e ações em lote.
- **Planilha:** visão/exportação no formato operacional, com colunas fixas.
- **Seguradoras:** uma linha por seguradora com situação, última coleta, próxima coleta, pendências abertas e ações.
- **Coletas:** histórico técnico/operacional com filtros (substitui “Execuções”).
- **Configurações/Status:** plugins, credenciais, healthz, testes — longe da operação.

### Nova composição do Painel

1. **Faixa de contexto:** “Dados atualizados às 16:03 · 2 seguradoras precisam de atenção”.
2. **“Precisa de atenção”** (lista curta, não parede de erros): cada item com seguradora, motivo em linguagem de negócio e **uma ação primária** (“Tentar novamente”, “Renovar acesso”).
3. **KPIs:** abertas, vencendo em 7 dias, vencidas, seguradoras OK (não “falhas” ambíguas).
4. **Pendências prioritárias:** top 10 por vencimento, com “Ver todas”.
5. **Saúde das seguradoras:** chips/linhas clicáveis que filtram o painel.
6. **Última coleta:** resumo compacto; histórico completo em “Coletas”.

### Página “Seguradoras” (substitui “Plugins” na visão de negócio)

| Seguradora | Situação | Última coleta | Pendências abertas | Ações |
|---|---|---|---|---|
| Bradesco | Conectada | hoje 08:00 | 23 | Atualizar · Renovar acesso |
| Porto | Ação necessária | hoje 08:00 (falhou) | 0 | Tentar novamente · Detalhes |
| SulAmérica | Sem dados | — | 0 | Configurar · Atualizar |

Detalhes técnicos (adapter, versão, caminho de state, capabilities) em um painel expansível “Detalhes técnicos” ou em Administração.

---

## 5. Prioridades

### P0 — antes de adicionar a segunda seguradora

Esforço: **P** = pequeno (até ~1 dia), **M** = médio (2–3 dias), **G** = grande (1+ semana).

| # | Melhoria | Por quê | Esforço |
|---|---|---|---|
| 1 | Unificar o conceito de saúde: Falha, Sem coleta, Desatualizada e OK, com os mesmos números no card, nas pills e no painel | Hoje o usuário vê 2 falhas no card e 1 no painel; perde a confiança | M |
| 2 | Filtrar Abertas por padrão; “Todas” explícito; adicionar “Limpar filtros” e estado na URL | Evita misturar histórico com fila de trabalho e permite compartilhar/voltar | P |
| 3 | Ações por seguradora: Atualizar agora, Tentar novamente, Renovar acesso | O usuário resolve o problema no lugar, sem rodar tudo de novo | M |
| 4 | Erro em duas camadas: resumo amigável + ação + “Detalhes técnicos” colapsado | O texto cru atual não orienta a operação | P/M |
| 5 | Corrigir mobile: menu, largura e tabela | Hoje a página tem 514 px em viewport de 390 px e a navegação corta | M |
| 6 | Separar operação de administração; renomear “Plugins” para “Seguradoras” e esconder “healthz” | Reduz jargão e evita que o operador entre em telas de desenvolvedor | P |

### P1 — antes de 5–10 seguradoras

- Tabela de pendências com colunas prioritárias, paginação, ordenação, agrupamento por seguradora e “visões salvas”.
- Status da linha com confirmação + desfazer e transições permitidas; aria-label no select.
- Página “Seguradoras” com status, última/próxima coleta, pendências e ações.
- “Sessões” com vocabulário único, expiração/próxima verificação, “Testar conexão” e controles de teste escondidos.
- “Coletas” com filtros por seguradora/status/período, duração, detalhe e “Tentar novamente”.
- Detalhe com ajuda de status, motivo da alteração, save fixo e aviso de alterações não salvas.
- Acessibilidade: aria-current, foco no modal, skip link, caption na tabela, labels.

### P2 — escala e produto

- Papéis (admin, operação, leitura) dentro da única corretora, se necessário.
- Onboarding/wizard de nova seguradora.
- Notificações e central de alertas.
- Métricas de uso e testes de usabilidade recorrentes.

---

## 6. Quick wins (baixo esforço, alto impacto)

1. Mudar o padrão para **Abertas** e adicionar “Todas” como opção explícita.
2. Corrigir a contagem “Seguradoras com falha” para bater com o painel ou separar “Com falha” de “Sem coleta”.
3. Tornar as pills de seguradora clicáveis (filtram o painel).
4. Adicionar “Tentar novamente” no painel de falhas e “Atualizar” por seguradora.
5. Trocar rótulos: “Coletar agora” → “Atualizar dados”; “Execuções” → “Coletas”; “Sessões” → “Acessos”; “Plugins” → “Seguradoras”.
6. Adicionar aria-label ao select de status e aria-current na navegação.
7. Esconder “Forçar expiração” e comandos de terminal atrás de “Avançado”.
8. No mobile, permitir quebra/menu na topbar e cards 2×2; esconder colunas secundárias.

---

## 7. Como validar antes de crescer

Teste com 5 operadores da corretora, 3 tarefas:

1. **“Descubra o que falhou hoje e resolva.”** Medir tempo até a ação e erros de caminho.
2. **“Encontre as parcelas vencidas de uma seguradora específica.”** Medir cliques e uso de filtros.
3. **“Altere o status de uma pendência e confirme que ela saiu da fila.”** Medir cliques errados e necessidade de ajuda.

Critérios de sucesso sugeridos:

- Resolver uma falha de seguradora em **≤ 3 cliques** a partir do painel.
- Nenhum usuário precisar abrir “Plugins” ou “Execuções” para o fluxo diário.
- Zero inconsistência entre números do topo e lista de atenção.
- Tarefa mobile concluída sem rolagem horizontal da página.

---

## 8. Decisão de produto

**Single-tenant:** uma única corretora, várias seguradoras. Não haverá seletor de corretora, isolamento por corretora nem operação multi-corretora. O plano acima foca em escalar a experiência para **N seguradoras** dentro dessa única corretora.

---

## Anexos

- [Painel](ux-review/dashboard.png)
- [Painel mobile](ux-review/dashboard-mobile.png)
- [Planilha](ux-review/planilha.png)
- [Detalhe](ux-review/detail.png)
- [Sessões](ux-review/sessions.png)
- [Plugins](ux-review/plugins.png)
- [Execuções](ux-review/runs.png)
