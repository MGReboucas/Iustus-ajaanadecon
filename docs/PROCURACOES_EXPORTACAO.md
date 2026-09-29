# Procurações em PDF e exportação do caso

Incremento local de 29/09/2026 para DEV-028 e DEV-037. Integra-se ao [fluxo de atendimento](FLUXO_ATENDIMENTO.md), sem serviço externo de assinatura ou protocolo.

## Modelos e geração

O advogado responsável cadastra e aprova seu próprio texto jurídico no painel do caso aceito. O sistema não fornece poderes jurídicos prontos nem afirma aprovação externa. Cada revisão cria uma versão imutável, com autor, data e SHA-256 do texto. A revisão exige a versão mais recente da família do modelo; outro advogado não pode alterar ou gerar a partir de um modelo privado alheio.

Campos obrigatórios no modelo: `{{cliente_nome}}`, `{{advogado_nome}}` e `{{advogado_oab}}`. Também disponíveis: `{{cliente_documento}}`, `{{cliente_endereco}}`, `{{advogado_endereco}}`, `{{cidade}}`, `{{data_emissao}}` e `{{caso_referencia}}`. Data e referência são preenchidas pelo backend; os demais campos presentes no modelo são obrigatórios na emissão. Placeholders desconhecidos, campos extras/ausentes, caracteres de controle e glifos não suportados são recusados. O sistema valida preenchimento, não autenticidade de documento ou inscrição profissional.

A emissão exige caso ACEITO, atribuição atual e versão do caso. Gera um PDF A4 com acentos, paginação, identificação do modelo e número da emissão. A versão do modelo, dados preenchidos e hashes do modelo e PDF ficam persistidos. O arquivo integra os documentos privados e é automaticamente selecionado no painel para solicitar assinatura, após conferência visual pelo advogado.

O PDF é composto exclusivamente pelo servidor a partir de texto escapado, sem anexos, HTML ativo ou recursos remotos. Por isso fica disponível como documento gerado, sem simular inspeção de upload ou preencher `scanned_at`. PDFs enviados pelo usuário, incluindo a devolução assinada, continuam passando por quarentena e scanner. A geração não certifica uma assinatura.

## Dossiê

Cliente e advogado atualmente atribuído podem preparar o ZIP, inclusive após encerramento. O administrador não acessa o conteúdo. A criação exige versão atual do caso, usa bloqueio transacional e registra auditoria. O pacote contém:

- `caso.json`: dados do caso e escopo compartilhado.
- `historico.json`, `mensagens.json`, `complementos.json` e `compromissos.json`: conteúdo público e resultados.
- `pecas/`: snapshots de publicações e última peça publicada, em texto UTF-8.
- `documentos/`: todas as versões disponíveis, com caminhos gerados pelo servidor.
- `manifesto.json`: associação entre arquivos e nomes originais, hashes e documentos omitidos por estado.

Notas internas, minutas não publicadas e eventos administrativos privados nunca integram o pacote, mesmo quando solicitado pelo advogado. O hash e o tamanho de cada documento são conferidos durante a leitura. Arquivo ausente ou divergente impede a exportação inteira; documentos em quarentena/erro/recusados são explicitamente listados como omitidos no manifesto.

Limites por pacote: até 200 documentos liberados, 100 MiB de documentos, até 1.000 registros em cada conjunto e 10 MiB por arquivo JSON. Não há truncamento silencioso: casos maiores recebem erro orientando cópia assistida. Limite de três pedidos por minuto por usuário quando o rate limit está habilitado.

O ZIP fica em armazenamento privado, com SHA-256. Link e pacote expiram em 15 minutos. O download exige a mesma sessão, usuário e portal da solicitação, além de revalidar acesso atual ao caso. Transferência revoga downloads antigos do advogado anterior. O navegador verifica o hash do pacote recebido.

## Rotas

| Rota | Função |
| --- | --- |
| GET/POST `/api/v1/legal/mandate-templates` | Listar modelos próprios / criar modelo aprovado ou nova versão com `previousId` |
| POST `/api/v1/cases/{id}/mandates` | Emitir PDF com `version`, `templateId`, `fields` e `confirmed` |
| POST `/api/v1/cases/{id}/exports` | Preparar pacote com `version` |
| GET `/api/v1/exports/{id}/content?token=...` | Baixar pacote dentro da validade, com sessão e acesso revalidados |

As respostas privadas não permitem cache. Downloads usam attachment e nosniff. O proxy encaminha apenas o token na rota de conteúdo autorizada.

## Operação

Instalar dependências de execução e aplicar migrações:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\backend\.venv\Scripts\python.exe backend/manage.py migrate
```

Executar periodicamente a limpeza física dos pacotes expirados:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py purge_case_exports
```

O comando remove somente objetos de exportações expiradas e mantém metadados para auditoria. O agendamento deve ser configurado na infraestrutura de implantação; a expiração do acesso independe da execução da limpeza. Não houve criação de tarefa no Windows nem alteração de infraestrutura externa nesta entrega.

O armazenamento privado disponível ainda é local e explicitamente habilitado. Em ambiente sem armazenamento configurado, geração e exportação retornam indisponibilidade. Integração com armazenamento produtivo, revisão jurídica dos modelos reais e assinatura eletrônica externa continuam pendentes.

## Verificação

72 testes aprovados no PostgreSQL, incluindo geração PDF e extração do texto, modelos imutáveis, campos obrigatórios, hash, versão desatualizada, rollback de banco/arquivo, integridade dos anexos, exclusão de notas/minutas, expiração, isolamento entre sessões, transferência e limpeza seletiva. Dependências de teste: `pip install -r backend/requirements-test.txt`.

Build Next.js, tipos e verificação de migrações aprovados. Jornada ampliada aprovada no Edge, do cadastro do modelo à emissão/download do PDF, atendimento e exportação ZIP pelo cliente em 390px. Amostra sintética de duas páginas renderizada e conferida visualmente; telas de geração e exportação também conferidas. Scanner simulado somente na fixture E2E de uploads, conforme o teste existente. Nenhuma homologação produtiva ou certificação jurídica foi realizada.
