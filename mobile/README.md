# Íustus mobile — jornada do associado

Aplicativo do associado em Expo SDK 57, React Native e TypeScript. Android e iOS compartilham a base em `src/`. O site e o dashboard web continuam em `../frontend`; identidade, associação e casos usam o mesmo Django/PostgreSQL.

## Implementado

- Identidade Íustus e AJA ANADECON, navegação por abas com Expo Router.
- Login do associado com a conta existente e recuperação de senha por e-mail. O link pode ser usado na web ou colado na tela Concluir meu acesso do app.
- Sessão opaca por aparelho, guardada no SecureStore; somente hash no servidor. Expiração absoluta e por inatividade iguais às do associado web (hoje 24 h e 2 h), sem refresh nesta entrega.
- Início com indicadores reais, situação e vigência da associação, casos que precisam de atenção e últimas movimentações.
- Lista paginada, detalhes e histórico público dos casos; conta e logout.
- Conversa por caso (07/10/2026): mensagens públicas paginadas, atualização manual e envio durante o atendimento com advogado atribuído. Repetir um envio com o mesmo texto após falha de rede reutiliza a chave para evitar duplicação enquanto a tela permanece aberta; notas internas não são expostas.
- Propostas de atendimento: consulta, aceite e recusa; a decisão não realiza cobrança.
- Ocorrência: criação/edição de rascunho, categoria, data, relato, ciência do escopo e submissão com chave de idempotência. O servidor exige elegibilidade e documentos verificados conforme a configuração.
- Documentos por arquivo ou câmera (PDF/JPEG/PNG até 20 MiB), checksum, envio binário ou direto ao armazenamento, quarentena, novas versões e download privado. Arquivos nativos baixados são temporários e abertos pelo compartilhamento do sistema.
- Pendências paginadas, resposta com documentos próprios verificados e seleção paginada de anexos.
- Procuração: baixar modelo, anexar versão assinada, entregar para conferência e reenviar após devolução. A assinatura segue a orientação do advogado; não foi integrada uma assinatura eletrônica.
- Trabalho contratado, peça publicada, protocolo/comprovante, agenda e consulta dos casos encerrados. Ações profissionais continuam restritas ao portal do advogado.
- Aba Avisos: consulta, paginação, marcação de leitura e abertura do caso. Link nativo `iustus://open-case/UUID` conserva o destino durante o login e revalida a titularidade no servidor.
- Primeiro acesso: cadastro quando habilitado, reenvio de confirmação/ativação, confirmação de e-mail, ativação de associado e redefinição de senha colando o link completo do e-mail. O link também continua funcionando na web.
- Conta: alteração de nome/preferência de e-mails, solicitações de acesso/correção/exclusão com acompanhamento, e páginas informativas do serviço/privacidade no portal.
- Carregamento, estados vazios, falha de conexão, repetição e retorno ao login em sessão inválida.

Consulta não representa liberação para novos atendimentos. O backend continua sendo a autoridade sobre associação, propriedade dos casos e permissões. Contas de equipe/administrador não entram no app nesta entrega.

## Rodar

1. Use Node 24 e instale com `npm ci` nesta pasta.
2. Copie `.env.example` para `.env.local` e defina `EXPO_PUBLIC_API_ORIGIN` com a **origem pública do portal Next.js**, sem `/api/v1`. Nunca inclua credenciais nessa variável.
3. Aplique a migração `identity.0005_mobilesession` no backend de desenvolvimento e execute o backend e o portal com as configurações existentes. Publique ambos antes de testar contra um ambiente remoto.
4. Execute `npm start` (ou `npm run mobile:start` na raiz) e abra no Expo Go compatível com SDK 57. `npm run android` abre o emulador instalado; iOS pode usar Expo Go em aparelho ou simulador em macOS.
5. Entre com um **associado ativo e com e-mail verificado**. Não há conta nem senha de demonstração embutida.

O código exige HTTPS fora do desenvolvimento. Para aparelho físico, `localhost` é o próprio celular: prefira um portal de homologação HTTPS. Usar IP privado em desenvolvimento exige configurar a origem do portal, hosts permitidos e proxy para esse mesmo endereço; não apenas trocar a URL no app. Não coloque `IUSTUS_PROXY_SECRET` nem URL privada do Django no aplicativo.

## Sessão e API

O app chama `/api/v1/mobile/*` pelo proxy Next.js existente. Apenas as novas rotas aceitam o header `Authorization: Bearer ...`. O proxy retira cookies dessas chamadas e nunca encaminha Bearer às rotas web. O Django mantém a exigência do segredo privado do proxy. Login web e CSRF permanecem inalterados.

| Rota relativa a `/api/v1/mobile` | Método | Uso |
| --- | --- | --- |
| `/auth/login` | POST | E-mail e senha; retorna token, validade e perfil |
| `/auth/recovery` | POST | Resposta neutra; envia recuperação para conta elegível |
| `/auth/logout` | POST | Revoga a sessão corrente |
| `/dashboard` | GET | Perfil, associação e indicadores existentes |
| `/cases` | GET | Casos próprios, paginação por `cursor` |
| `/cases/:id` | GET | Detalhes do caso próprio |
| `/cases/:id/timeline` | GET | Histórico público paginado |
| `/cases/:id/messages` | GET, POST | Conversa pública paginada e envio com chave de idempotência |

Tokens não ficam em URLs, AsyncStorage, logs ou localStorage. A prévia web do Expo usa somente memória; o produto web permanece no Next.js. Reset de senha (`auth_version`), desativação, perda da verificação de e-mail e mudança de papel invalidam a sessão. Até cinco sessões por associado; novo login substitui a mais antiga ao exceder o limite. Logout offline apaga o acesso local, mas a revogação remota depende de conexão ou expiração.

## Verificar

```sh
npm run typecheck
npm run lint
npm test
npx expo-doctor
npm run export:check
npx playwright install chromium
npm run test:ui
```

Os testes visuais usam **dados sintéticos e API simulada** e rodam a prévia web em largura de celular. Não substituem testes de SecureStore, teclado, navegação e rede em aparelhos Android/iOS. A exportação gera bundles; não gera um aplicativo assinado para as lojas.

Do diretório `backend`, execute:

```sh
python manage.py test tests.test_mobile tests.test_mobile_flows tests.test_documents tests.test_identity --settings=config.settings.test --noinput
python manage.py makemigrations --check --dry-run --settings=config.settings.test
```

Da raiz: `node --test tests/frontend/proxy.test.cjs` (requer dependências de `frontend`). O workflow do GitHub verifica tipos, lint, testes e exportação mobile.

## Verificação local de 08/10/2026

- Tipos, lint e testes de transporte mobile; testes do proxy/contratos compartilhados.
- Suíte backend: 182 testes, com seis testes dependentes de PostgreSQL ignorados em SQLite. Nenhuma migração nova necessária.
- Seis testes Playwright no Edge aprovados: login, sessão expirada, recuperação, rede indisponível, primeiro acesso/confirmar e-mail, link direto de caso e jornada da ocorrência até procuração/peça publicada e solicitação de exclusão. Dados sintéticos e API simulada; scanner simulado somente nos testes backend.
- Build Next.js e exportação Expo Android/iOS/web aprovados. Isso não equivale a APK/IPA assinado nem homologação física.
- O verificador global de documentação encontrou um link para `frontend/.env.example`, arquivo que já estava excluído no workspace antes desta tarefa. A exclusão preexistente foi preservada.

O inventário completo das novas rotas está em [API_ROTAS.md](../docs/API_ROTAS.md). Endpoints de documentos mobile usam Bearer em cada download, sem reaproveitar cookies ou links assinados de sessão web.

## Adesão e dependências externas

A tela Associação consulta o plano do servidor. A continuidade para `/checkout` só aparece se `BILLING_ENABLED` e `MOBILE_EXTERNAL_CHECKOUT_ENABLED` estiverem habilitados no backend. O segundo flag vem desabilitado: habilitar por canal de distribuição depois de definir o enquadramento comercial nas lojas. A cobrança continua no checkout existente, e a ativação depende da confirmação real do provedor. Não há checkout nativo, renovação automática nova ou cobrança disparada nesta entrega.

## Pendências de lançamento

1. Homologar login, reabertura, expiração, navegação e logout em Android e iPhone reais.
2. Homologar armazenamento privado, CORS do envio direto, scanner real e entrega de e-mails no ambiente de destino.
3. Definir o enquadramento da adesão nas lojas e habilitar o checkout externo somente no canal apropriado.
4. Push externo: a revisão automática rejeitou a inclusão do worker que enviaria tokens de aparelhos e identificadores de casos ao Expo. Nenhum worker, cadastro de dispositivo ou chamada a esse provedor foi adicionado. Requer autorização específica. A aba Avisos já funciona sem esse envio externo.
5. Consolidar os textos institucionais aprovados (prestador/controlador, canal público, retenção e cobertura); as páginas informativas não certificam revisão jurídica. O fluxo de exclusão registra uma solicitação para tratamento pela operação, não apaga registros automaticamente. Preparar ícone de loja em alta resolução, splash e validar acessibilidade em aparelhos.
6. Builds assinadas e distribuição de teste; publicação só depois de homologação e revisão das lojas.

`eas.json` prepara perfis de preview interno e produção. Ainda é necessário vincular o projeto EAS e as contas Apple/Google da organização, configurar a origem por ambiente e validar os identificadores propostos `br.org.ajaanadecon.iustus` antes da primeira publicação. Nenhum projeto externo, cobrança, build em nuvem ou publicação foi criado nesta entrega.

O `npm audit` inicial apontou avisos em dependências transitivas do SDK (braces, node-forge, uuid e decode-uri-component). A correção automática sugeria inclusive downgrade incompatível do Expo. Não usar `npm audit fix --force`; revisar atualizações compatíveis e exposição dos avisos antes de distribuição externa.
