# Investigar descrições genéricas e categorização incorreta do C6 no Meu Pluggy

## Resumo

Transações do C6 que antes apareciam no **Meu Pluggy** com nomes de estabelecimentos e contrapartes passaram a aparecer com descrições genéricas, como `DEBITO DE CARTAO` e `PIX RECEBIDO`. O extrato no aplicativo do banco continua exibindo os detalhes esperados.

O problema foi observado na interface do Meu Pluggy, antes da importação pelo projeto. A causa ainda não foi confirmada: pode envolver os dados compartilhados pelo banco, a coleta ou normalização da Pluggy, ou a apresentação no Meu Pluggy.

Esta issue contém somente informações técnicas e exemplos genéricos. Não inclui nomes de pessoas, estabelecimentos reais, datas ou valores de movimentações, capturas de tela, credenciais nem identificadores de conexão, conta ou transação.

## Comportamento observado

- Antes: nomes de estabelecimentos e contrapartes permitiam identificar os gastos.
- Agora: algumas movimentações aparecem com descrições genéricas.
- Algumas despesas descritas como `DEBITO DE CARTAO` aparecem categorizadas como `Credit card payment`.
- O extrato do C6 mantém os nomes detalhados, segundo a verificação manual do usuário.

## Comportamento esperado

Identificar onde o detalhe está sendo perdido e, quando disponível na API, aproveitar o campo correto sem inventar o estabelecimento ou a categoria. O fato de o aplicativo bancário mostrar o nome não comprova que a mesma informação esteja sendo compartilhada via Open Finance.

## Impacto no projeto

- Descrições genéricas dificultam buscas, categorização e identificação de recorrências.
- A classificação `Credit card payment` pode excluir compras reais dos totais de gastos: o cálculo atual trata essa categoria como pagamento de fatura para evitar dupla contagem.
- Regras por nome aplicadas a uma descrição genérica podem reunir despesas de estabelecimentos diferentes.
- IA não consegue recuperar com confiabilidade um nome de estabelecimento ausente dos dados recebidos.

## O que a documentação permite verificar

### Acesso pessoal e atualização

O fluxo pessoal é banco → Meu Pluggy → conector MeuPluggy na aplicação → API. Cada banco corresponde a um item espelhado. A atualização ocorre a cada 24 horas; esses itens não permitem atualização manual. Importar novamente no projeto consulta os dados disponíveis, sem garantir uma nova coleta bancária.

Para consultar uma conexão conhecida, usar `GET /items/{id}`. A listagem `GET /v2/items` não está disponível para contas pessoais Meu Pluggy. No Dashboard, escolher o conector **MeuPluggy**, e não o conector direto do C6.

Referências: [guia do Meu Pluggy](https://meu.pluggy.ai/api-guide) e [uso pessoal](https://docs.pluggy.ai/en/docs/guides/meu-pluggy-personal-use).

### Dados de uma transação

Usar `GET /transactions/{id}` para comparar os campos abaixo. Eles podem estar ausentes ou nulos; não existe garantia de detalhe em toda operação.

| Campo | Utilidade no diagnóstico |
| --- | --- |
| `description` / `descriptionRaw` | Comparar a descrição tratada com a original recebida da instituição. |
| `merchant.name` / `merchant.businessName` | Verificar se há identificação do estabelecimento em outro campo. |
| `paymentData` | Verificar participantes e informações do pagamento, especialmente em transferências. |
| `operationType` / `operationTypeAdditionalInfo` | Investigar o tipo de operação informado, sem confundi-lo com o nome do estabelecimento. |
| `status` | Distinguir pendente de liquidada; pendência não garante enriquecimento posterior. |
| `category` / `categoryId` | Comparar a classificação com a natureza real da operação. |
| `accountId` | Identificar se a operação pertence à conta bancária ou ao cartão. |
| `providerId` / `providerCode` | Auxiliar a correspondência privada com a movimentação bancária. |

Referência: [consulta de transação e descrição dos campos](https://v2.docs.pluggy.ai/en/reference/transaction/transactions-retrieve).

### Estado da conexão

Consultar `status`, `executionStatus` e, quando disponível, `executionReport` no item. A documentação descreve o relatório como evidência de falhas de execução. Uma execução sem erros não comprova que os nomes dos estabelecimentos tenham sido recebidos corretamente; no item espelhado, também não se deve presumir acesso a todos os detalhes internos da coleta do C6.

Referências: [Reporting Issues](https://docs.pluggy.ai/en/docs/connections/reporting-issues) e [status público](https://status.pluggy.ai).

## Hipóteses a testar

| Hipótese | Evidência que ajudaria a diferenciá-la |
| --- | --- |
| Informação existe, mas a tela não a utiliza | Nome detalhado em `descriptionRaw`, `merchant` ou `paymentData`, apesar da descrição exibida ser genérica. |
| Normalização removeu detalhes | `descriptionRaw` detalhada e `description` genérica. |
| Dados já chegam incompletos à API pública | Todos os campos relevantes genéricos ou vazios. Isso não distingue sozinho banco de coleta da Pluggy. |
| Problema depende do tipo de conta ou operação | Diferença consistente entre conta bancária, cartão, compras e transferências. |
| Atualização posterior altera os detalhes | Mesma operação recebe informação adicional após um ciclo de atualização. |
| Problema está associado à conexão atual | Uma reconexão controlada muda o resultado; isso ainda não comprova a causa raiz. |

Não foi encontrada, nas páginas consultadas, uma explicação específica para esse comportamento do C6 nem um modo público documentado que exponha toda a comunicação bruta entre a Pluggy e o banco.

## Próximos passos de diagnóstico

### 1. Preservar evidências antes de alterar a conexão

- [ ] Fazer backup privado do banco local antes de novas importações ou reconexões.
- [ ] Selecionar uma transação antiga detalhada e uma recente genérica, preferencialmente da mesma conta e modalidade.
- [ ] Comparar cada uma com sua correspondente no extrato bancário, sem pressupor correspondência apenas por valor e data.
- [ ] Registrar privadamente os identificadores necessários para repetir a consulta e o estado atual da conexão.
- [ ] Manter respostas completas somente em local privado, fora do Git e de anexos públicos.

### 2. Comparar a API com as duas interfaces

- [ ] Consultar `GET /items/{id}` para verificar o estado da conexão.
- [ ] Consultar `GET /accounts?itemId={id}` para identificar a conta de origem e seu tipo.
- [ ] Localizar as operações com `GET /v2/transactions?accountId={id}`, respeitando a paginação.
- [ ] Consultar `GET /transactions/{id}` para cada amostra e comparar os campos listados acima.
- [ ] Comparar banco, Meu Pluggy, resposta da API e projeto local separadamente.
- [ ] Registrar na issue apenas conclusões sanitizadas, como “descrição original genérica; estabelecimento ausente”.

Autenticar as consultas em ambiente privado, mantendo as credenciais no servidor ou em ferramenta local. Não publicar cabeçalhos, tokens, arquivos `.env`, respostas completas ou exportações HAR.

### 3. Verificar atualização e incidentes

- [ ] Consultar a página pública de status e registrar eventual incidente relacionado, sem assumir que a ausência de incidente descarta um defeito.
- [ ] Após um ciclo de atualização de aproximadamente 24 horas, repetir a consulta das amostras.
- [ ] Verificar se mudou a descrição, o status ou a categoria. Não assumir que aguardar necessariamente recuperará o nome.

### 4. Testar reconexão do C6, se o diagnóstico anterior não esclarecer

**Reconectar é um experimento, não uma correção documentada para descrições genéricas. Esta issue não executa nenhuma exclusão.**

- [ ] Antes de excluir, concluir a coleta de evidências e considerar abrir o chamado com a conexão ainda existente, para facilitar a investigação pela Pluggy.
- [ ] Entender na interface o alcance da remoção: conexão, consentimento e disponibilidade do histórico podem ser afetados.
- [ ] Se optar pelo teste, remover a conexão do C6 no **Meu Pluggy** e autorizar o banco novamente por lá.
- [ ] Verificar no Dashboard se o novo banco está disponível pelo conector **MeuPluggy**; registrar privadamente o novo Item ID caso ele mude.
- [ ] Antes de importar no banco local existente, comparar a nova resposta da API com as evidências anteriores.
- [ ] Validar a importação em uma base isolada: novos IDs podem impedir a correspondência com registros antigos e gerar duplicação.
- [ ] Comparar operações correspondentes do mesmo período e modalidade, quando o histórico estiver disponível. A nova conexão pode disponibilizar um histórico diferente.
- [ ] Registrar se houve melhora e se ela persiste no ciclo seguinte. Evitar exclusões e reconexões repetidas sem evidência de benefício.

### 5. Escalar para o suporte se necessário

- [ ] Preparar relato sanitizado com a diferença entre o extrato bancário, Meu Pluggy e API.
- [ ] Informar se `descriptionRaw`, `merchant` e `paymentData` contêm os detalhes esperados e se a execução apresenta erros.
- [ ] Perguntar se houve alteração na origem, coleta, normalização ou categorização das operações do C6.
- [ ] Fornecer Item ID e exemplos reais somente pelo canal privado oficial solicitado pelo suporte. A documentação informa que o Item ID é necessário para investigar erros.

## Revisão complementar do projeto

Estes pontos locais não explicam, por si, o problema já visível no Meu Pluggy, mas podem agravar seu impacto:

- `backend/app/services/pluggy.py`: o mapeamento atual utiliza `description` e `merchant.name`, mas não preserva `descriptionRaw`, `paymentData`, `merchant.businessName` nem os identificadores do provedor para diagnóstico.
- `frontend/src/TransactionsTable.svelte`: o título prioriza `merchant`, seguido de `description`.
- `backend/app/services/finance.py`: a categoria `Credit card payment` é excluída dos gastos.
- `backend/app/services/category_rules.py`: regras por nome precisam de cuidado quando a origem passa a usar descrições genéricas.

Possíveis melhorias futuras, após confirmar a causa:

- [ ] Definir quais campos adicionais realmente precisam ser persistidos, com retenção e acesso apropriados.
- [ ] Criar diagnóstico que exponha apenas presença/ausência e qualidade dos campos, sem registrar dados bancários completos em logs.
- [ ] Evitar substituir descrições úteis por genéricas sem um critério verificável.
- [ ] Adicionar testes com exemplos inteiramente fictícios para descrições genéricas, campos alternativos e impacto da categoria nos totais.

## Critérios de conclusão

- [ ] Identificar em qual etapa o detalhe está ausente, ou registrar explicitamente o limite da investigação pela API pública.
- [ ] Registrar o resultado da comparação e, se realizado, do teste de reconexão, sem dados pessoais.
- [ ] Definir correção local baseada em evidências ou encaminhamento ao provedor.
- [ ] Confirmar que nenhuma credencial, identificação ou movimentação real foi adicionada à issue ou ao repositório.
