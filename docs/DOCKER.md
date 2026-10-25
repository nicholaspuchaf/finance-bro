# Execução com Docker Compose

## Arquitetura escolhida

Para o MVP, a distribuição usa **um container e um servidor FastAPI**. O build Svelte gera HTML, JavaScript e CSS; o FastAPI entrega esses arquivos junto da API, na mesma origem. Não há servidor Vite/Node nem supervisor de processos em execução no container final. O código continua separado em `frontend/` e `backend/`.

| Opção | Vantagem | Custo neste projeto | Decisão |
| --- | --- | --- | --- |
| FastAPI + frontend compilado, um container | Uma imagem, uma porta, atualização conjunta e chamadas `/api` sem proxy | UI e API são publicadas juntas; arquivos estáticos usam o mesmo processo | Adotada agora |
| Frontend estático + API em dois containers | Deploy e escala independentes; permite servidor estático/CDN dedicado | Mais imagens, configuração de proxy e operação | Evolução quando houver necessidade |
| Dois servidores no mesmo container | Reúne serviços numa imagem | Exige coordenar processos, sinais e healthchecks sem oferecer separação de deploy | Não adotada |

O `Dockerfile` usa estágios de build baseados em Debian Bookworm: `node:24-bookworm-slim` compila o frontend e `python:3.12-slim-bookworm` prepara o backend com uv. A imagem final usa Python slim da mesma distribuição, com dependências de execução e frontend compilado. Node, pnpm, uv, dependências de teste e caches dos instaladores ficam fora da imagem final. pnpm e uv têm versões explícitas; dependências são instaladas usando os lockfiles. As tags das imagens base recebem atualizações de patch; não são fixadas por digest.

## Iniciar

Requisitos: Docker Engine com Compose v2.24+ e suporte a build (Buildx), ou Docker Desktop. Node, Python, pnpm e uv não precisam estar instalados no host.

Na raiz do projeto:

```sh
cp .env.example .env
docker compose --env-file .env.conf up --build -d
```

Se o `.env` já existir, mantenha o arquivo atual. As credenciais são opcionais para abrir o site e usar lançamentos manuais; cada pessoa configura suas próprias credenciais Pluggy/OpenAI. O Compose funciona também sem `.env`, com os valores padrão e sem integrações configuradas.

Os endereços abaixo usam a porta `808` como exemplo; substitua pela porta configurada em `.env.conf`.

- Site: `http://localhost:808`.
- API: `http://localhost:808/api/health`.
- Documentação da API: `http://localhost:808/docs`.
- As páginas continuam usando fragmentos: `/#inicio`, `/#transacoes`, `/#dashboards`, `/#tags`.

Para alterar a porta, defina `FINANCE_BRO_PORT=9080` no `.env.conf` e recrie o serviço com `docker compose --env-file .env.conf up -d`. O endereço publicado continua limitado a `127.0.0.1`.

```sh
docker compose --env-file .env.conf ps
docker compose --env-file .env.conf logs -f app
docker compose --env-file .env.conf down
```

`down` remove o container e a rede, preservando o volume. `docker compose --env-file .env.conf down -v` **apaga o volume e seus dados**. Para atualizar o código/imagem, use `docker compose --env-file .env.conf up --build -d`.

Caso o host recuse acesso a `/var/run/docker.sock`, a execução precisa ocorrer numa conta autorizada a usar Docker, ou com o procedimento administrativo do seu sistema. Não é necessário abrir permissões do socket nem tornar o container privilegiado. O diretório do projeto deve continuar acessível ao usuário que executar o Compose.

## Dados e backup

O volume nomeado `finance-data` guarda `/data/finance_bro.db`, backups e cópias de migração. Por padrão, o Docker usa o nome do projeto como prefixo: `finance-bro_finance-data`. Escolher outro nome de projeto (`-p`) cria outro conjunto de dados.

O container não incorpora nem importa automaticamente o banco em `backend/data/` do host. Uma primeira execução com volume novo começa vazia; reconstruir a imagem não apaga o volume existente. A imagem usa o usuário `app`, UID/GID `10001`, com acesso de escrita ao volume. Há um único worker, adequado ao SQLite pessoal.

Backup consistente com o app em execução:

```sh
docker compose --env-file .env.conf exec -T app python scripts/backup.py
mkdir -p backups
docker compose --env-file .env.conf cp app:/data/backups/. ./backups
```

Para migrar o SQLite do modo nativo ou restaurar uma cópia, use um backup consistente, não copie um arquivo que esteja recebendo escritas. No modo nativo, o script existente continua disponível: `cd backend && uv run python scripts/backup.py`.

Com o serviço parado e uma imagem já construída, substitua o caminho abaixo pelo arquivo escolhido. Se o volume de destino já tiver dados, faça backup dele antes da substituição:

```sh
docker compose --env-file .env.conf stop app
docker compose --env-file .env.conf create app
docker compose --env-file .env.conf cp /caminho/do/backup.db app:/data/finance_bro.db
docker compose --env-file .env.conf run --rm --no-deps --user 0 --cap-add CHOWN app chown 10001:10001 /data/finance_bro.db
docker compose --env-file .env.conf up -d
```

O ajuste de proprietário é necessário porque arquivos copiados pelo Docker podem pertencer a root. A execução pontual adiciona somente a capability CHOWN; o serviço normal continua sem capabilities. A cópia original do host é preservada. O backend executa as migrações existentes na inicialização; o caminho do volume não depende do diretório do host.

## Configuração e rede

A única porta publicada fica em `.env.conf`, na variável `FINANCE_BRO_PORT`. Site e API compartilham esse endereço. Os comandos deste guia passam esse arquivo explicitamente; o Compose não procura automaticamente um arquivo chamado `.env.conf`. Credenciais ficam no `.env`, carregado apenas no ambiente de execução do serviço. Dentro do container a porta continua `8000`, sem disputar a porta `8000` do host.

O Compose lê as portas de `.env.conf` pelo argumento `--env-file`. O arquivo `.env` é carregado separadamente, como `env_file` opcional do serviço, apenas para o ambiente de execução do backend. As chaves não são enviadas como argumentos de build ou variáveis `VITE_*`. As variáveis de banco, frontend, origem e acesso local são sobrescritas explicitamente no Compose. `.dockerignore` restringe o contexto a fontes e lockfiles: não envia `.env`, bancos, backups, Git, testes, `node_modules` ou ambientes virtuais locais.

| Configuração | No Compose |
| --- | --- |
| `DATABASE_URL` | `sqlite:////data/finance_bro.db`, dentro do volume |
| `FRONTEND_DIST` | `/app/frontend/dist`, contendo o build Svelte |
| `FRONTEND_ORIGIN` | `http://localhost:<porta publicada>` |
| `LOCAL_ONLY` | `false`, para aceitar a conexão encaminhada pela bridge Docker |
| `PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET`, `PLUGGY_API_URL` | Injetadas a partir do ambiente/`.env` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Injetadas a partir do ambiente/`.env` |

O Uvicorn escuta em `0.0.0.0:8000` **dentro do container**; o Compose publica a porta apenas em `127.0.0.1` no host. O filtro por endereço de cliente precisa ser desativado nesse modo, pois a origem encaminhada não é o loopback do container. Na execução nativa, `LOCAL_ONLY=true` continua sendo o padrão. Cabeçalhos de proxy não são confiados pelo comando do container. Respostas da API mantêm `Cache-Control: no-store`.

O filesystem da imagem é somente leitura, `/tmp` é temporário e somente o volume de dados é persistente e gravável. O container não roda como root, descarta capabilities e desabilita aquisição de novos privilégios. O healthcheck consulta `/api/health` usando Python, sem adicionar curl.

## Desenvolvimento e deploy futuro

O Docker Compose substitui o antigo `dev.py`, que foi removido. O frontend é compilado no build e servido pelo FastAPI; editar fontes exige rebuild com `docker compose --env-file .env.conf up --build -d`. Não há necessidade de iniciar dois servidores no host. `FRONTEND_DIST` é opcional fora do container e, quando definido, precisa conter `index.html`. O servidor só publica esse diretório, não os fontes do backend. Rotas desconhecidas da API permanecem 404.

Distribuir o app para outras pessoas significa cada instalação manter suas credenciais e seu volume, sem compartilhar dados. A imagem ainda **não torna o aplicativo um serviço público**: autenticação/autorização e HTTPS continuam pendentes. Para deploy público, adicionar esses controles antes de publicar a porta, fornecer armazenamento persistente e backup e reavaliar SQLite/concorrência. Um proxy TLS e, depois, um servidor/CDN estático podem ser introduzidos sem alterar os identificadores ou as chamadas relativas `/api` do frontend.

## Verificação

```sh
docker compose --env-file .env.conf config --quiet
docker compose --env-file .env.conf build
docker compose --env-file .env.conf up -d
docker compose --env-file .env.conf ps
```

A verificação usa `--quiet` para não imprimir configurações ou segredos. Evite compartilhar a saída completa de `docker compose config`, pois ela pode conter as credenciais resolvidas. Os testes em `backend/tests/test_container_app.py` verificam arquivos estáticos e API na mesma origem, 404s, isolamento do diretório publicado e a opção de acesso pela bridge. O build e a inicialização reais também devem ser conferidos num host com Docker autorizado.

Referências: [build em estágios](https://docs.docker.com/build/building/multi-stage/), [uv em Docker](https://docs.astral.sh/uv/guides/integration/docker/), [arquivos estáticos no FastAPI](https://fastapi.tiangolo.com/tutorial/static-files/).
