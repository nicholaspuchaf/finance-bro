# Segurança e privacidade: estado e próximos passos

Atualizado em 20/10/2026. Este documento distingue controles presentes de recomendações para evolução. Ele não certifica o aplicativo para exposição pública.

## Controles presentes no MVP

- `Client ID`, `Client Secret` e chave OpenAI são lidos pelo backend do `.env`; `.env` e arquivos `*.db` estão no `.gitignore`. A API devolve ao navegador apenas o Connect Token temporário necessário ao widget, nunca a API Key da Pluggy nem o Client Secret.
- O backend tem restrição por endereço de cliente local e CORS configurado para a origem do frontend. Respostas em `/api/` recebem `Cache-Control: no-store`.
- A aplicação não executa classificação pela OpenAI na importação. O envio de descrição, valor e moeda ocorre quando o usuário aciona a classificação.
- O script de backup local cria cópias do SQLite com permissões restritas. O botão de olho mascara valores na interface.

Esses controles são adequados como defesa inicial de um app executado pelo próprio usuário em loopback, mas **não equivalem a autenticação ou criptografia do banco**. CORS limita leitura por navegadores em certas origens, não autoriza usuários; proxies podem fazer requisições remotas parecerem locais. O modo público oculta texto e detalhes dos gráficos, mas os dados continuam na resposta da API, na memória do navegador e no SQLite.

## Recomendações priorizadas

| Prioridade | Ação | Momento |
| --- | --- | --- |
| Alta | Manter backend e Vite em `127.0.0.1`, evitar proxy/túnel público e limitar acesso aos arquivos `.env`, SQLite e backups ao usuário do sistema. | Agora, enquanto não houver autenticação. |
| Alta | Antes de qualquer acesso remoto: implementar login forte, autorização em todos os endpoints financeiros, sessão segura (cookie `HttpOnly`, `Secure`, `SameSite`), proteção CSRF onde houver cookie e HTTPS. Reavaliar o middleware de loopback atrás de proxy confiável. | Antes de deploy. |
| Alta | Usar segredos separados por ambiente; não incluir chaves em Git, screenshots, mensagens de erro ou logs; rotacionar imediatamente qualquer chave exposta. No deploy, usar gerenciador de segredos. | Agora e antes de deploy. |
| Alta | Proteger dados em repouso e backups: permissões do sistema, criptografia do disco/backup, política de retenção e teste periódico de restauração. | Antes de depender do histórico para decisões. |
| Média | Reduzir dados enviados à IA ao estritamente necessário, deixar claro quando a classificação externa será acionada, registrar custos/limites e permitir revisão humana. | Ao ampliar uso da IA. |
| Média | Sanitizar logs e erros: não registrar respostas brutas da Pluggy, credenciais, tokens, Item IDs completos, descrições ou saldos; usar IDs de correlação opacos para diagnosticar falhas. | Antes de observabilidade/deploy. |
| Média | Adicionar limites de tamanho e taxa para ações de sincronização/classificação, atualização regular de dependências e controles de timeout e retry. | Antes de deploy e sync automático. |
| Média | Se webhooks forem introduzidos, validar assinatura/autenticidade conforme o mecanismo oficial da Pluggy, rejeitar replay, tratar evento como sinal para reconciliação e limitar logs de payload. | Junto à implementação de webhooks. |

Se o projeto virar produto para terceiros, planejar isolamento por usuário/tenant, consentimento, exclusão e exportação de dados desde o desenho do banco e das APIs. O acesso pessoal gratuito do Meu Pluggy é voltado ao próprio usuário; confirme as condições vigentes com a [documentação oficial](https://docs.pluggy.ai/en/docs/guides/meu-pluggy-personal-use).

Referências: [Pluggy Connect Authentication](https://v2.docs.pluggy.ai/en/docs/connect-widget/authentication), [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html), [OWASP Webhook Security](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html).
