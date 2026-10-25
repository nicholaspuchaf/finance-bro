# Finance Bro

Gerenciador financeiro pessoal local. O frontend Svelte e o backend Python ficam separados; transações ficam em SQLite na máquina local.

Documentação: [Docker e decisão de arquitetura](docs/DOCKER.md), [estado do projeto e próximos passos](docs/PROJECT_STATUS.md), [configuração do Meu Pluggy](docs/PLUGGY_SETUP.md) e [segurança e privacidade](docs/SECURITY.md).

## Executar com Docker

Requer Docker com Compose v2.24+. Na raiz, copie `.env.example` para `.env` se ainda não tiver esse arquivo e execute:

```sh
docker compose --env-file .env.conf up --build -d
```

Abra `http://localhost:<FINANCE_BRO_PORT>`, usando a porta definida em `.env.conf`. As chaves são opcionais para abrir o site. A API e o frontend compilado são servidos pelo mesmo processo, em uma imagem Debian slim; Node/pnpm são usados apenas no build. O SQLite fica em um volume persistente e começa vazio na primeira execução. Bancos do modo nativo não são importados automaticamente.

`docker compose --env-file .env.conf down` encerra o app preservando os dados; `down -v` apaga o volume. Porta, backup, migração do banco e comparação entre um/dois containers estão em [docs/DOCKER.md](docs/DOCKER.md).

### Selecionar a porta

Edite **`.env.conf`**, que contém a única porta publicada no host:

```dotenv
FINANCE_BRO_PORT=808
```

`FINANCE_BRO_PORT` controla o endereço do site e da API. Por exemplo, use `FINANCE_BRO_PORT=9080` para abrir o site em `http://localhost:9080` e a documentação da API em `http://localhost:9080/docs`. As credenciais continuam somente no `.env`. Após alterar a porta, recrie o serviço com `docker compose --env-file .env.conf up -d`.

O Docker Compose é o fluxo de execução do projeto; o antigo `dev.py` foi removido. Para editar o código e publicar uma nova versão local, execute novamente `docker compose --env-file .env.conf up --build -d`. Node/pnpm e Python/uv no host são opcionais, usados apenas para executar as verificações locais de contribuição.

Os botões `A−` e `A+` ao lado de **Ambiente local** ajustam a escala da interface entre 80% e 150%. A escolha fica salva neste navegador.

O botão com bandeira retangular no cabeçalho alterna entre **português (Brasil)** e **inglês (Estados Unidos)** e salva a preferência no navegador. Textos, categorias, macro-categorias, datas e valores acompanham o idioma. Os nomes internos da Pluggy são preservados nos filtros e no banco de dados; a moeda não é convertida. A estrutura i18n está documentada em [frontend/README.md](frontend/README.md#idiomas).

O botão de lua/sol na barra superior alterna entre os temas claro e escuro. Na primeira visita, o site segue a preferência do sistema; depois guarda a escolha neste navegador.

O botão de olho na barra superior ativa o modo público: saldos e valores monetários aparecem como `R$ •••••` (ou com o código da moeda da transação). O valor no formulário de nova transação também fica oculto enquanto o modo estiver ativo. Clique novamente para revelar os valores. A preferência fica salva neste navegador; ela altera apenas a exibição, sem remover dados do banco ou das respostas da API.

## Integrações

- Meu Pluggy pessoal: conecte seus bancos no [Meu Pluggy](https://www.pluggy.ai/meu-pluggy) e crie uma aplicação no Dashboard com a mesma conta. Em `Customization → Connectors`, habilite a seleção personalizada e deixe somente **MeuPluggy** (conector ID 200). Em `Aplicações → sua aplicação → Demo`, clique em `Connect Account`, escolha **MeuPluggy** e conclua o login; depois abra o item em `Connected Items` e copie o **Item ID completo (UUID)** pelo botão de cópia. Um trecho curto do ID, como `68e9a286`, não funciona. Importe o ID pela tela do site. A API pessoal não lista itens por `GET /v2/items`; o proxy é atualizado pela Pluggy, geralmente em até 24 horas, e não aceita atualização forçada. Verifique o vencimento do consentimento. [Guia oficial](https://docs.pluggy.ai/en/docs/guides/meu-pluggy-personal-use), [configuração de conectores](https://docs.pluggy.ai/en/docs/guides/dashboard-connectors).
- Pluggy: informe `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` no `.env`. O backend cria o Connect Token. A importação aceita apenas o conector MeuPluggy, lê as transações por `GET /v2/transactions` com paginação por cursor e reaproveita IDs de transações em sincronizações repetidas. Estados de erro e consentimento expirado aparecem na conexão; corrija no Meu Pluggy e tente novamente.
- Classificação: quando a Pluggy retorna `category` na transação, o app usa esse valor diretamente e marca a origem como Pluggy. A IA não é acionada na importação. Para transações sem categoria, o uso da OpenAI é opcional e exige um clique em uma transação ou no lote de até 10; a descrição, o valor e a moeda são enviados à API da OpenAI. A justificativa da IA fica separada das notas pessoais. Revise as categorias sugeridas.
- Categorias e tags: os seletores seguem a [árvore de categorias publicada pela Pluggy](https://v1.docs.pluggy.ai/docs/transaction-categories), com os nomes exibidos no idioma selecionado e os identificadores originais preservados na API. Por padrão, mostram 15 categorias frequentes; marque **Todas** ao lado para ver a lista completa. Uma categoria rara já atribuída continua visível mesmo no modo reduzido. `Uncategorized` indica ausência de categoria. Na página **Tags**, acessível pela barra lateral, crie, renomeie ou exclua tags e veja quantas transações usam cada uma. É possível combinar várias tags por transação e filtrar a lista por tag. A sincronização não remove tags locais.
- Regras de categoria: ao trocar a categoria de uma transação, o aviso no canto inferior esquerdo permite aplicar a escolha a todas as transações com o mesmo nome e às futuras. O nome é o estabelecimento exibido, ou a descrição quando ele não existe; a comparação ignora maiúsculas e espaços repetidos. **Só esta** mantém a alteração apenas na transação editada. As regras ficam no SQLite e prevalecem sobre a categoria recebida da Pluggy nas próximas importações.

## Consulta e cálculo

O **Início** apresenta a visão geral e até 20 transações recentes. A página **Transações** é dedicada à lista completa: busca, várias categorias ou macro-categorias, tag e intervalo de datas podem ser combinados, e o botão **Carregar mais** adiciona 50 itens por vez. As categorias selecionadas aparecem abaixo dos filtros; remova uma por vez, use **Limpar seleção** para remover as categorias ou **Limpar filtros** para zerar toda a pesquisa. Uma transação que corresponde a mais de uma seleção aparece apenas uma vez. As duas páginas usam o mesmo componente de tabela. Os demais blocos do Início também são widgets reutilizáveis, documentados em [frontend/README.md](frontend/README.md). Recorrências são sugestões baseadas no mesmo nome em dois meses e valores próximos; não geram lançamentos futuros. O resumo mensal conta débitos positivos confirmados em BRL, excluindo transferências, investimentos, pagamentos de fatura e estornos identificados. Lançamentos sem categoria ainda contam como despesa; revise os casos ambíguos. Transações em outras moedas aparecem na lista, mas não entram no total em BRL sem conversão.

A página **Dashboards** apresenta um dashboard independente da paginação da lista, começando pelo mês atual e permitindo análise de 1, 3, 6, 12 ou 24 meses. É possível alternar entre gastos e investimentos, marcar várias categorias para somar seus valores (por exemplo, `Food delivery` e `Eating out`), filtrar por uma ou mais tags, escolher o mês da visão diária quando o período inclui vários meses e trocar gráficos de colunas, linha ou área. Transações que tenham mais de uma tag selecionada entram no total apenas uma vez; tags e categorias podem ser combinadas. O dashboard e a aba Transações usam o mesmo componente de seleção: ele mostra as mesmas 15 categorias comuns; **Todas** abre o `<select>` com a árvore completa em grupos da Pluggy e **Macro-categorias** mostra apenas os nomes desses grupos no mesmo `<select>`. No dashboard, cada opção escolhida é adicionada à agregação e pode ser removida pelos chips. Cada macro-categoria soma suas subcategorias. Todas as categorias da Pluggy podem ser selecionadas; os totais seguem o tipo de análise escolhido, então uma categoria de receita, por exemplo, não terá valores na análise de gastos. Sem categorias ou tags marcadas, a análise usa todas as disponíveis no modo escolhido. A visão diária também oferece valores por dia ou acumulados. Em investimentos, os gráficos representam aportes (saídas positivas classificadas na família Investments); as entradas relacionadas incluem resgates e proventos e aparecem separadas. O dashboard não calcula saldo ou rentabilidade da carteira. Valores ocultos pelo botão de olho também ficam ocultos nos gráficos e seus detalhes.

## Dados locais e backup

O SQLite e o `.env` ficam somente na máquina que executa o backend. Pluggy recebe os dados bancários da conexão; a IA recebe os campos usados para classificação. Não execute o backend em rede pública sem autenticação. Para backup consistente no Docker, rode `docker compose --env-file .env.conf exec -T app python scripts/backup.py`; a cópia vai para `/data/backups/` no volume, com permissão restrita. Exportação, restauração e migração de bancos antigos estão em [docs/DOCKER.md](docs/DOCKER.md). Na execução nativa, o script ainda pode ser usado com `cd backend && uv run python scripts/backup.py`. Para restaurar, pare o backend, faça uma cópia do arquivo atual e substitua `backend/data/finance_bro.db` pelo backup. A migração das categorias antigas em português cria uma cópia `*.before-category-migration-*.db` antes de substituí-las pelos nomes em inglês. A primeira migração de esquema cria uma cópia `*.before-migration-*.db`. Se você usou a primeira versão do MVP, o SQLite em `data/finance_bro.db` na raiz é copiado automaticamente para o novo caminho na primeira inicialização, preservando o arquivo original.

## Verificação sem chaves

`cd backend && uv run pytest -q` e `cd frontend && pnpm test && pnpm check && pnpm build`. Os testes simulam respostas da Pluggy e da IA; não fazem conexão bancária real.

Sem Docker, o servidor deve permanecer vinculado a `127.0.0.1` enquanto a aplicação não tiver autenticação. No Compose, o processo escuta na rede interna do container e somente `127.0.0.1` do host publica a porta. Os dados financeiros e as credenciais não devem ser expostos em uma implantação pública.
