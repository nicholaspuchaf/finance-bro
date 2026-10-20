# Estado do projeto e evolução de system design

Atualizado em 20/10/2026. Este documento descreve o checkout atual; funcionalidades listadas como futuras ainda não estão implementadas.

## Escopo e arquitetura atual

Finance Bro é um gerenciador financeiro de uso pessoal e local. O frontend está em `frontend/` (Svelte 5, Vite, pnpm), o backend em `backend/` (FastAPI, Python, uv) e os dados em `backend/data/finance_bro.db` (SQLite via SQLAlchemy). Não há autenticação nem suporte multiusuário. A API e o servidor de desenvolvimento são iniciados em `127.0.0.1`; o backend rejeita clientes que não apareçam como loopback e restringe CORS à origem configurada.

Fluxo principal: conectar bancos no Meu Pluggy, criar um item do conector MeuPluggy na aplicação Pluggy, importar o Item ID completo ou usar o widget, consultar manualmente contas e transações e salvar uma cópia local. A integração do backend usa `httpx`; o frontend usa `pluggy-connect-sdk`. O backend pagina `GET /v2/transactions` por cursor, sem recorte de datas próprio: a janela histórica efetiva depende do que a Pluggy e a instituição disponibilizam. Não há sincronização automática agendada.

As categorias recebidas da Pluggy são aproveitadas na importação. Alterações manuais, regras por nome e classificações por IA são preservadas em sincronizações subsequentes conforme a precedência implementada. A IA da OpenAI só é chamada por ação explícita: uma transação ou lote de até 10 transações sem categoria. Não há classificação em massa automática após conectar um banco. A descrição, o valor e a moeda da transação são enviados à OpenAI nesse fluxo.

A interface tem lista paginada, busca e filtros por categoria/tag/datas; edição e lançamento manual; página de tags com contagem; sugestões de recorrência; resumo mensal; regras para reaplicar categoria por nome; dashboard de gastos e aportes em investimentos com até 24 meses, múltiplas categorias agregadas, evolução diária e mensal e gráficos alternáveis. O botão de privacidade só mascara os valores renderizados; a API e os dados locais continuam contendo os valores originais.

O frontend foi reorganizado em páginas distintas: **Início** compõe os widgets da visão geral e até 20 transações recentes; **Transações** apresenta apenas o histórico com filtros e carregamento de 50 itens por vez; **Dashboards** substitui o antigo nome Categorias; **Tags** mantém a gestão de etiquetas. `TransactionsTable.svelte`, `CategorySelector.svelte` e `CategorySelection.svelte` são compartilhados. Os demais blocos do Início foram extraídos para widgets independentes; a composição e as propriedades estão descritas em [frontend/README.md](../frontend/README.md).

Transações e Dashboards permitem combinar categorias e macro-categorias e limpar as seleções. As macro-categorias correspondem aos grupos da taxonomia Pluggy mantida no backend, não à lista de 15 categorias comuns. As seleções são unidas sem dupla contagem; no dashboard, composição, totais e séries diária/mensal respeitam os mesmos filtros. A taxonomia no checkout tem 134 categorias e 24 grupos; os identificadores permanecem canônicos, com rótulos traduzidos na interface.

Há temas claro/escuro e i18n em `pt-BR`/`en-US`, com catálogos JSON, interpolação, plurais e formatação por `Intl`. A bandeira é plana, retangular, sem contorno e fica imediatamente à esquerda do botão de tema. Idioma, tema, privacidade e escala de fonte persistem no navegador. A navegação continua por fragmentos (`#inicio`, `#transacoes`, `#dashboards`, `#tags`), com compatibilidade para o antigo `#categorias`.

Existem testes automatizados de backend em `backend/tests/`, scripts de verificação de frontend e um script de backup consistente em `backend/scripts/backup.py`. Este documento não registra uma nova execução desses testes.

## Trabalho ainda pendente

1. Validar o fluxo completo com os itens reais do Meu Pluggy em cada instituição conectada. Houve um retorno HTTP 410 em `GET /v2/transactions` durante uma tentativa de sincronização; a causa não foi confirmada. Registrar apenas código, etapa e identificadores mascarados ao investigar.
2. Definir política de janela histórica e backfill. Hoje cada sync lê todas as páginas disponíveis; acompanhar limite, volume, latência e cobertura real por banco antes de definir sync incremental.
3. Revisar qualidade dos dados: pendente versus confirmado, estornos, transferência entre contas, pagamento de fatura, cartão de crédito, investimentos, moedas e diferenças entre saldo, fatura e fluxo de caixa. Conferir se a taxonomia da Pluggy permanece atual.
4. Tornar as regras de categoria administráveis (listar, alterar, excluir e revisar impacto) e permitir desfazer uma aplicação em massa. Hoje elas são criadas/atualizadas pelo aviso após editar a categoria.
5. Melhorar recorrências: distinguir sugestão de compromisso confirmado, identificar cancelamentos e mudança de valor, sem criar lançamentos futuros automaticamente.
6. Definir exportação dos dados, retenção, exclusão e restauração operacional; conferir periodicamente backups e recuperação.

## Problemas de system design adiados deliberadamente

| Tema | Decisão futura necessária | Motivo |
| --- | --- | --- |
| Webhooks e atualização | Receber eventos da Pluggy, verificar autenticidade, reconciliar estados e manter um fallback de consulta | Hoje a atualização depende do botão de sincronizar e do espelhamento do Meu Pluggy. |
| Filas e retentativas | Processar importações fora da requisição HTTP, com limite de concorrência, backoff e tratamento de falhas parciais | Uma sincronização grande ocupa a requisição; falha de uma etapa pode exigir repetição. |
| Idempotência e reconciliação | Definir identidade estável de conta/transação, lidar com reautorização que gera novo Item ID, IDs alterados, registros removidos e pendentes convertidos em confirmados | Já existe unicidade `(account_id, external_id)` e atualização em sync repetido da mesma conta, mas isso não resolve duplicatas entre itens nem todo o ciclo de vida. |
| Modelo financeiro | Separar transação, fatura, compra no cartão, transferência interna, aporte, resgate e saldo; definir sinais e contagem | Evita dupla contagem e melhora análises de gastos e investimentos. |
| Custo e escala | Sincronização incremental, índices/consultas agregadas, limites da Pluggy, controle do custo da IA e eventual Postgres | O SQLite e consultas atuais bastam ao uso pessoal, mas não a volumes ou concorrência maiores. |
| Deploy e usuários | Autenticação, autorização por recurso, isolamento de dados, migrações de banco e política de sessões | O limite de rede local não substitui controles de acesso na internet. |
| Operação | Métricas de frescor, auditoria sem dados sensíveis, alertas, backups e recuperação testada | Erros silenciosos ou dados defasados afetam a confiança no dashboard. |

Webhooks, filas e idempotência completa foram explicitamente postergados no MVP; a restrição está registrada na decisão `decisions/personal-finance-mvp-architecture.md` da ai-memory. Priorize primeiro correção dos dados e segurança antes de expor o serviço fora da máquina local.

Ver também [configuração do Pluggy](PLUGGY_SETUP.md) e [segurança](SECURITY.md).
