# Documentos privados — incremento local

> Implementação e verificação local em 21/09/2026. Somente arquivos fictícios; não representa homologação produtiva.

O cliente e o advogado atribuído podem enviar anexos compartilhados, acompanhar a verificação, criar novas versões e baixar versões liberadas. O cliente pode vincular até 20 versões próprias, disponíveis e do mesmo caso a uma resposta de complemento. A resposta preserva a versão exata; substituições posteriores não alteram a evidência anexada.

Administrador, outros clientes e advogados sem atribuição não acessam arquivos nem metadados. Após transferência, o advogado anterior perde inclusive o acesso por links emitidos antes da mudança. Minutas internas, procurações, modelos e exportações não fazem parte deste incremento; todo anexo deste módulo é compartilhado com o titular.

## Contrato implementado

Todas as rotas ficam em `/api/v1`. Sessão válida é obrigatória; mutações exigem CSRF. Listagens usam cursor, 20 versões por página, mais recentes primeiro. Identificadores de objetos de armazenamento nunca são retornados.

| Método / rota | Entrada e resultado |
| --- | --- |
| GET `/cases/{id}/documents` | Lista versões no escopo do titular/atribuído |
| POST `/cases/{id}/documents/uploads` | `filename`, `sizeBytes`, `mime` → `uploadId`, `uploadUrl`, expiração e versão |
| POST `/uploads/{id}/content` | Binário `application/octet-stream`, pelo autor do envio → 204; conteúdo não pode ser sobrescrito |
| POST `/uploads/{id}/complete` | `checksum` SHA-256 hexadecimal → 202 em quarentena; repetição com mesmo hash é idempotente |
| POST `/documents/{id}/versions` | Metadados do novo arquivo e `previousVersion` → novo envio; versão desatualizada retorna 409 |
| GET `/documents/{id}/versions/{versionId}/download` | Versão AVAILABLE → link assinado por até 300 segundos |
| GET `/documents/{id}/versions/{versionId}/content` | Token, mesma sessão/usuário/portal e vínculo vigente → download como anexo |
| POST `/cases/{id}/requests/{requestId}/response` | `version`, `text` e `documentVersionIds` opcionais; só versões próprias, disponíveis e deste caso |

Envios expiram em 30 minutos. Arquivos vazios, maiores que 20 MiB, extensões incompatíveis, assinaturas binárias desconhecidas ou checksum divergente são recusados. Tipos aceitos: PDF, JPEG e PNG. Identificação binária não é validação estrutural completa do documento; o scanner é uma etapa adicional. Um envio interrompido permanece identificado como incompleto e requer nova versão. Casos recusados não aceitam novos envios. Rascunhos próprios aceitam documentos.

Estados: UPLOADING → QUARANTINED → SCANNING → AVAILABLE ou REJECTED. Falha operacional gera ERROR com download bloqueado e nova tentativa agendada. A versão anterior permanece disponível se já foi liberada, mesmo enquanto a substituta aguarda análise.

## Armazenamento e worker

O adaptador local grava em `.local/documents`, sem rota estática pública, usando chaves aleatórias. O ambiente E2E usa `.local/documents-e2e`. A configuração base desabilita armazenamento local; somente settings de desenvolvimento/teste o habilitam. Fornecedor de objetos, região, retenção, limpeza de envios abandonados, backup e restauração produtivos continuam pendentes (DEV-006 / EXT-03). Não usar esse diretório em disco efêmero de produção.

Na raiz, aplique as migrações:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py migrate
```

O worker usa o protocolo INSTREAM do ClamAV em `127.0.0.1:3310`. `DOCUMENT_SCANNER_HOST` e `DOCUMENT_SCANNER_PORT` podem ser configurados em `backend/.env`. O serviço ClamAV precisa estar instalado separadamente, com assinaturas atualizadas, acessível apenas pela rede privada/loopback. Configure `StreamMaxLength`, `MaxFileSize` e `MaxScanSize` para suportar os arquivos aceitos e revise a política de arquivos criptografados/limites antes da homologação. Referências: [protocolo oficial](https://docs.clamav.net/manual/Usage/ClamdProtocol.html) e [configuração oficial](https://github.com/Cisco-Talos/clamav/blob/main/etc/clamd.conf.sample).

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py scan_documents
# Processar somente itens disponíveis e encerrar:
.\backend\.venv\Scripts\python.exe backend/manage.py scan_documents --once
# Depois de corrigir o scanner, reagendar erros e processar:
.\backend\.venv\Scripts\python.exe backend/manage.py scan_documents --retry-failed --once
```

O worker reserva cada versão no PostgreSQL com lease de 5 minutos e token exclusivo; uma execução antiga não pode publicar resultado após perder a reserva. O scanner tem prazo total de 30 segundos. Há até 5 tentativas, com espera crescente; reservas vencidas são retomadas, inclusive após interrupção. Erros esgotados continuam bloqueados até intervenção pelo comando. Não existe botão ou endpoint para liberar manualmente um arquivo sem verificação.

## Evidências e limites

47 testes Django passaram no PostgreSQL local, incluindo disputa por versão de documento, isolamento, CSRF, expiração de link/envio, integridade, falha/rejeição do scanner, retomada de lease e vínculo de anexo com o caso correto. O protocolo ClamAV é exercitado por servidor TCP de teste com respostas de sucesso, detecção e erro; isso não comprova um antivírus real instalado. A jornada de navegador usa um scanner substituto restrito ao processo de fixture e ao banco E2E; a aplicação não possui bypass.

Build e TypeScript passaram. As quatro jornadas Playwright passaram no Edge instalado (`PLAYWRIGHT_CHANNEL=msedge`). A jornada cliente → upload → quarentena → download → complemento anexado → conferência pelo advogado faz parte de `tests/e2e/access.spec.cjs`, inclusive em tela de 390 px, sem transbordamento horizontal. A homologação com ClamAV real, armazenamento de objetos, políticas de retenção e infraestrutura permanece pendente. Pagamentos e assinatura não foram alterados.
