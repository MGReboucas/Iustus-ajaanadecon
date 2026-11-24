# Anexos privados com S3 e GuardDuty no Render

## Configuração da AWS

- Bucket privado com os quatro bloqueios públicos, ACLs desabilitadas e SSE-S3.
- Malware Protection for S3 ativo na mesma região, cobrindo `iustus/objects/` ou todo o bucket; **marcar objetos verificados** habilitado.
- IAM do backend limitado ao prefixo conforme [política de runtime](s3-runtime-policy.example.json), incluindo `s3:GetObjectTagging`. Não conceder `PutObjectTagging` ou `DeleteObjectTagging` à aplicação: só GuardDuty deve definir o resultado.
- CORS: PUT para `https://www.iustus.app` e `https://iustus.app`; headers `content-type`, `if-none-match`, `x-amz-checksum-sha256`, `x-amz-server-side-encryption`.
- Não é necessário habilitar todos os recursos GuardDuty. Custos seguem o consumo de S3 e Malware Protection.

## Ativação na API Render

Primeiro publique a revisão que contém esta integração. Configure estas três variáveis juntas e faça deploy:

```dotenv
DOCUMENT_STORAGE_BACKEND=s3
DOCUMENT_SCANNER_BACKEND=guardduty
DOCUMENT_DIRECT_UPLOAD_ENABLED=true
```

Mantenha as chaves privadas já cadastradas e estes valores:

```dotenv
DOCUMENT_S3_BUCKET=iustus-documentos-2026-ajaanadecon
DOCUMENT_S3_REGION=us-east-2
DOCUMENT_S3_PREFIX=iustus/objects
```

`DOCUMENT_S3_ENDPOINT` deve estar vazio/ausente (AWS nativa). `DOCUMENT_DEMO_ENABLED` deve estar ausente ou `false`. `DOCUMENT_SCANNER_HOST` não é necessário no modo GuardDuty. Nenhum segredo AWS vai para Vercel ou `NEXT_PUBLIC_*`. Publique também o frontend desta revisão para atualização automática do status.

## Funcionamento e limites

O navegador envia por PUT assinado com checksum, tamanho e condição de não sobrescrita. A confirmação valida tamanho, assinatura de formato e SHA-256 e coloca o arquivo em quarentena. Apenas a etiqueta `GuardDutyMalwareScanStatus=NO_THREATS_FOUND` permite liberar, após nova conferência de integridade. Ameaça ou formato não verificável resulta em recusa; erro, falta de etiqueta e falha de rede mantêm o bloqueio. Download continua autenticado, restrito ao cliente/advogado do caso, com nova consulta da etiqueta.

O backend consulta **um documento pendente por listagem autorizada do caso**, com lease persistente e intervalo mínimo de 15 segundos (60 segundos em erro). A interface atualiza a cada 15 segundos enquanto houver pendências e a aba estiver visível. Não há worker obrigatório: a AWS analisa mesmo com a página fechada; a atualização do estado no banco ocorre na próxima consulta. `scan_documents`/`run_operations` também podem reconciliar os resultados se houver worker no futuro. Essa mudança não substitui workers de outros módulos.

Documentos enviados antes da ativação do GuardDuty podem não ter etiqueta; envie uma nova versão. Erros são consultados novamente sem liberar o arquivo por timeout. Sem resultado, o arquivo permanece bloqueado.

## Remoção de anexos do rascunho

O titular pode remover suas versões enquanto o caso estiver em `RASCUNHO`, inclusive uploads incompletos. Após a submissão, a API bloqueia a remoção. O registro recebe o estado `REMOVED`, sai da lista e das exportações, deixa de contar como comprovante e não permite download nem confirmação tardia. A lease do scanner é revogada na mesma transação do caso.

O objeto é excluído imediatamente quando o armazenamento está acessível. Uma limpeza posterior, após o prazo máximo das URLs assinadas, remove eventual upload que tenha chegado atrasado. Ela ocorre na consulta ao caso, no worker operacional se existente, ou por `python manage.py purge_removed_documents`. Sem novas consultas nem worker, a limpeza pendente precisa desse comando; o anexo continua inacessível pela aplicação. Buckets com versionamento preservam versões anteriores conforme sua política de retenção. A migração `documents.0003` registra a nova opção de status sem apagar dados existentes.

## Validação após deploy (ainda necessária na AWS real)

1. Conta de teste autorizada: criar rascunho e enviar PDF/JPEG/PNG sintético pequeno. Verificar envio direto, quarentena, liberação automática e download.
2. Confirmar no S3 a etiqueta `NO_THREATS_FOUND`; outro cliente deve continuar sem acesso ao caso/anexo. O bucket deve continuar privado.
3. Testar checksum inválido, arquivo acima de 20 MiB e formato incompatível: não devem liberar arquivo.
4. Em ambiente de homologação, validar detecção com amostra padrão EICAR (inofensiva) e verificar recusa. Não usar malware real ou documento de cliente para teste.
5. Confirmar envio da ocorrência após documento disponível, sem conflito de versão do caso.

Os testes locais usam S3 simulado (Moto): não comprovam CORS real, credenciais da produção nem detecção real da AWS. Para diagnóstico somente leitura: `python manage.py check_document_services --only scanner --object-key CHAVE_INTERNA_32_HEX` consulta uma amostra limpa já enviada. A auditoria `--only storage` exige as permissões adicionais da [política de auditoria](s3-audit-policy.example.json), que não são necessárias no runtime. Não confundir uma consulta de etiqueta bem-sucedida com um teste antivírus completo.

Para interromper novos anexos sem apagar arquivos, use `DOCUMENT_STORAGE_BACKEND=disabled`, `DOCUMENT_SCANNER_BACKEND=clamav` e `DOCUMENT_DIRECT_UPLOAD_ENABLED=false` e faça deploy. Os objetos e metadados são preservados.

Referências: [resultados GuardDuty](https://docs.aws.amazon.com/guardduty/latest/ug/monitoring-malware-protection-s3-scans-gdu.html), [etiquetas](https://docs.aws.amazon.com/guardduty/latest/ug/monitor-enable-s3-object-tagging-malware-protection.html).
