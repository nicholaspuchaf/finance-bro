# Componentes do frontend

`HomePage.svelte` compõe a página Início com widgets independentes. `App.svelte` mantém a navegação, os dados gerais e as ações de edição e integração. Os widgets recebem os dados e as ações por propriedades.

| Componente | Uso |
| --- | --- |
| `TransactionsTable.svelte` | Lista com edição de categorias e tags. `compact` mostra até `previewLimit` registros (20 por padrão); o modo completo oferece filtros e carrega `pageSize` registros por vez (50 por padrão). |
| `CategorySelection.svelte` | Seleções de categorias e macros, com remoção individual e limpeza; compartilhado entre Transações e Dashboards. |
| `CategoryIcon.svelte` | Ícone vetorial da categoria, compartilhado pelas transações do Início e do histórico. |
| `widgets/SummaryCard.svelte` | Cartão genérico com título, valor, ícone e snippet `footer` opcional. |
| `widgets/FinancialSummary.svelte` | Compõe os quatro cartões de resumo a partir de `summary` e `connectionCount`. |
| `widgets/SpendingByCategory.svelte` | Distribuição dos gastos, recebendo `categories` e `limit` opcional. |
| `widgets/RecurringExpenses.svelte` | Sugestões de recorrências, recebendo `items` e `limit` opcional. |
| `widgets/AiAssistantCard.svelte` | Estado da integração de IA e acesso à página de transações. |
| `widgets/PluggyImport.svelte` | Formulário do Item ID; chama `onimport(itemId)` e limpa o campo quando a ação retorna `true`. |
| `widgets/IntegrationSetup.svelte` | Estado de configuração das integrações Pluggy e IA. |

Os componentes que exibem valores recebem `formatMoney`, mantendo a formatação e o modo de ocultar valores definidos pela aplicação. Por exemplo:

```svelte
<SpendingByCategory categories={summary.categories} limit={5} {formatMoney} />
```

Cada instância de `TransactionsTable` mantém seus próprios filtros e resultados. No modo completo, categorias e macro-categorias podem ser combinadas; `transactions.js` envia parâmetros repetidos `categories` e `macro_categories`, e a API aplica a união antes de paginar. Busca, tag e datas restringem essa união. **Limpar seleção** remove apenas as categorias; **Limpar filtros** também limpa busca, tag e datas. A lista resumida do Início sempre busca as últimas transações, sem filtros. O modo completo identifica o fim dos resultados, cancela requisições anteriores quando os filtros mudam e preserva a quantidade de registros carregados ao chamar o método público `refresh()` depois de uma edição.

`transactions.js` concentra a paginação e respeita o limite de 500 registros por requisição da API. `api.js` compartilha o tratamento de requisições e erros.

Validação local: `pnpm test`, `pnpm check` e `pnpm build`.

## Ícones de categoria

`CategoryIcon.svelte` desenha SVGs de traço, sem fontes de ícones ou emojis. Os desenhos e o mapeamento ficam em `src/categoryIcons.js`: `categoryIconPaths` contém os traços; `categoryIconConfig.groups` define os ícones dos grupos e `categoryIconConfig.categories` as exceções por categoria. As demais subcategorias herdam o ícone do grupo informado pela taxonomia de `/api/config`, sem duplicar a árvore no frontend.

Para trocar um ícone, altere o desenho ou seu mapeamento nesse arquivo. Para desativar os ícones específicos, defina `categoryIconConfig.enabled = false`; todas as transações voltam à marca genérica circular. Categorias desconhecidas e sem classificação também usam essa marca. O componente aceita `enabled={false}` para o mesmo efeito numa instância. A integração com as duas páginas fica apenas em `TransactionsTable.svelte`.

O ícone herda as cores existentes do tema e o destaque de entradas; o tooltip usa o nome traduzido da categoria. O SVG é decorativo para leitores de tela, pois o seletor da linha já apresenta a categoria em texto. Nenhum nome traduzido é usado como identificador do ícone ou da transação.

## Idiomas

O frontend oferece português do Brasil (`pt-BR`) e inglês dos Estados Unidos (`en-US`). `LocaleToggle.svelte` alterna o idioma pelo botão com bandeira retangular no cabeçalho. A preferência fica em `finance-bro-locale` no navegador; sem preferência salva, o idioma acompanha o navegador, com português como alternativa para idiomas não suportados.

Os catálogos estão em `src/i18n/locales/pt-BR.json` e `en-US.json`, com chaves agrupadas por área, interpolação de parâmetros e formas de plural selecionadas por `Intl.PluralRules`. `src/i18n/index.js` expõe os stores reativos `locale`, `t`, `categoryLabel`, `currency`, `date` e `number`. O atributo `lang` do documento e o título também acompanham o idioma.

As 134 categorias e os 24 grupos usam os mesmos identificadores canônicos da Pluggy nos dados, filtros, regras e chamadas à API. `categoryLabel` traduz apenas a apresentação, incluindo seletores, grupos, chips, gráficos e o formulário de edição. Descrições bancárias, nomes de estabelecimentos e tags cadastradas pelo usuário continuam sendo dados originais. A formatação dos valores acompanha o idioma; a moeda continua sendo a da transação, sem conversão cambial.

Notificações guardam chave e parâmetros para acompanhar uma troca de idioma enquanto estão abertas. Mensagens conhecidas da API são mapeadas por `server-messages.json`, preservando o contrato do backend. Os testes conferem paridade dos catálogos, cobertura da árvore da Pluggy, pluralização, persistência, formatação, renderização dos componentes nos dois idiomas e envio dos identificadores canônicos à API.
