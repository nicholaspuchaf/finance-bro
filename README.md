# Finance Bro

Gerenciador financeiro pessoal local. O frontend Svelte e o backend Python ficam separados; transações ficam em SQLite na máquina local.

## Requisitos

- Node.js 20.19+ e pnpm
- Python 3.12+ e uv

## Começar

1. Copie `.env.example` para `.env`. As credenciais são opcionais para abrir o app; são necessárias para conectar a Pluggy e usar a classificação com IA.
2. Terminal 1: `cd backend && uv sync && uv run uvicorn app.main:app --reload --host 127.0.0.1`
3. Terminal 2: `cd frontend && pnpm install && pnpm dev`
4. Abra `http://localhost:5173`.

A API fica em `http://localhost:8000/docs`. O banco é criado automaticamente em `backend/data/finance_bro.db`. O arquivo `.env` deve ficar na raiz do projeto.

Os botões `A−` e `A+` ao lado de **Ambiente local** ajustam a escala da interface entre 80% e 150%. A escolha fica salva neste navegador.

O botão de olho na barra superior ativa o modo público: saldos e valores monetários aparecem como `R$ •••••` (ou com o código da moeda da transação). O valor no formulário de nova transação também fica oculto enquanto o modo estiver ativo. Clique novamente para revelar os valores. A preferência fica salva neste navegador; ela altera apenas a exibição, sem remover dados do banco ou das respostas da API.

## Integrações

- Meu Pluggy pessoal: conecte seus bancos no [Meu Pluggy](https://www.pluggy.ai/meu-pluggy) e crie uma aplicação no Dashboard com a mesma conta. Em `Customization → Connectors`, habilite a seleção personalizada e deixe somente **MeuPluggy** (conector ID 200). Em `Aplicações → sua aplicação → Demo`, clique em `Connect Account`, escolha **MeuPluggy** e conclua o login; depois abra o item em `Connected Items` e copie o **Item ID completo (UUID)** pelo botão de cópia. Um trecho curto do ID, como `68e9a286`, não funciona. Importe o ID pela tela do site. A API pessoal não lista itens por `GET /v2/items`; o proxy é atualizado pela Pluggy, geralmente em até 24 horas, e não aceita atualização forçada. Verifique o vencimento do consentimento. [Guia oficial](https://docs.pluggy.ai/en/docs/guides/meu-pluggy-personal-use), [configuração de conectores](https://docs.pluggy.ai/en/docs/guides/dashboard-connectors).
- Pluggy: informe `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` no `.env`. O backend cria o Connect Token. A importação aceita apenas o conector MeuPluggy, lê as transações por `GET /v2/transactions` com paginação por cursor e reaproveita IDs de transações em sincronizações repetidas. Estados de erro e consentimento expirado aparecem na conexão; corrija no Meu Pluggy e tente novamente.
- Classificação: quando a Pluggy retorna `category` na transação, o app usa esse valor diretamente e marca a origem como Pluggy. A IA não é acionada na importação. Para transações sem categoria, o uso da OpenAI é opcional e exige um clique em uma transação ou no lote de até 10; a descrição, o valor e a moeda são enviados à API da OpenAI. A justificativa da IA fica separada das notas pessoais. Revise as categorias sugeridas.
- Categorias e tags: os seletores usam os nomes em inglês da [árvore de categorias publicada pela Pluggy](https://v1.docs.pluggy.ai/docs/transaction-categories). Por padrão, mostram 15 categorias frequentes; marque **Todas** ao lado para ver a lista completa. Uma categoria rara já atribuída continua visível mesmo no modo reduzido. `Uncategorized` indica ausência de categoria. Na página **Tags**, acessível pela barra lateral, crie, renomeie ou exclua tags e veja quantas transações usam cada uma. É possível combinar várias tags por transação e filtrar a lista por tag. A sincronização não remove tags locais.
- Regras de categoria: ao trocar a categoria de uma transação, o aviso no canto inferior esquerdo permite aplicar a escolha a todas as transações com o mesmo nome e às futuras. O nome é o estabelecimento exibido, ou a descrição quando ele não existe; a comparação ignora maiúsculas e espaços repetidos. **Só esta** mantém a alteração apenas na transação editada. As regras ficam no SQLite e prevalecem sobre a categoria recebida da Pluggy nas próximas importações.

## Consulta e cálculo

Busca, categoria, tag e intervalo de datas podem ser combinados. A lista carrega 50 itens por vez. Recorrências são sugestões baseadas no mesmo nome em dois meses e valores próximos; não geram lançamentos futuros. O resumo mensal conta débitos positivos confirmados em BRL, excluindo transferências, investimentos, pagamentos de fatura e estornos identificados. Lançamentos sem categoria ainda contam como despesa; revise os casos ambíguos. Transações em outras moedas aparecem na lista, mas não entram no total em BRL sem conversão.

## Dados locais e backup

O SQLite e o `.env` ficam somente na máquina que executa o backend. Pluggy recebe os dados bancários da conexão; a IA recebe os campos usados para classificação. Não execute o backend em rede pública sem autenticação. Para backup consistente, rode `cd backend && uv run python scripts/backup.py`; a cópia vai para `backend/data/backups/` com permissão restrita. Para restaurar, pare o backend, faça uma cópia do arquivo atual e substitua `backend/data/finance_bro.db` pelo backup. A migração das categorias antigas em português cria uma cópia `*.before-category-migration-*.db` antes de substituí-las pelos nomes em inglês. A primeira migração de esquema cria uma cópia `*.before-migration-*.db`. Se você usou a primeira versão do MVP, o SQLite em `data/finance_bro.db` na raiz é copiado automaticamente para o novo caminho na primeira inicialização, preservando o arquivo original.

## Verificação sem chaves

`cd backend && uv run pytest -q` e `cd frontend && pnpm check && pnpm build`. Os testes simulam respostas da Pluggy e da IA; não fazem conexão bancária real.

O servidor deve permanecer vinculado a `127.0.0.1` enquanto a aplicação não tiver autenticação. Os dados financeiros e as credenciais não devem ser expostos em uma implantação pública.
