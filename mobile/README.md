# Íustus mobile — primeira entrega

Aplicativo do associado em Expo SDK 57, React Native e TypeScript. Android e iOS compartilham a base em `src/`. O site e o dashboard web continuam em `../frontend`; identidade, associação e casos usam o mesmo Django/PostgreSQL.

## Implementado

- Identidade Íustus e AJA ANADECON, navegação por abas com Expo Router.
- Login do associado com a conta existente e recuperação de senha por e-mail. O link de redefinição continua abrindo a web; depois o usuário retorna ao app.
- Sessão opaca por aparelho, guardada no SecureStore; somente hash no servidor. Expiração absoluta e por inatividade iguais às do associado web (hoje 24 h e 2 h), sem refresh nesta entrega.
- Início com indicadores reais, situação e vigência da associação, casos que precisam de atenção e últimas movimentações.
- Lista paginada, detalhes e histórico público dos casos; conta e logout.
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
python manage.py test tests.test_mobile tests.test_identity --settings=config.settings.test --noinput
python manage.py makemigrations --check --dry-run --settings=config.settings.test
```

Da raiz: `node --test tests/frontend/proxy.test.cjs` (requer dependências de `frontend`). O workflow do GitHub verifica tipos, lint, testes e exportação mobile.

## Próximas entregas

1. Homologar login, reabertura, expiração, navegação e logout em Android e iPhone reais.
2. Cadastro de ocorrência, câmera/arquivos, upload seguro e procuração por caso.
3. Adesão e pagamento após definir o enquadramento nas lojas; o checkout não foi colocado no app. Oferta comercial: 12x de R$ 79,90; viabilidade nas lojas ainda pendente.
4. Notificações push, links diretos de casos e ações sobre pendências.
5. Fluxo de exclusão de conta/privacidade, textos legais, ícone de loja em alta resolução, splash e acessibilidade em aparelhos.
6. Builds assinadas e distribuição de teste; publicação só depois de homologação e revisão das lojas.

`eas.json` prepara perfis de preview interno e produção. Ainda é necessário vincular o projeto EAS e as contas Apple/Google da organização, configurar a origem por ambiente e validar os identificadores propostos `br.org.ajaanadecon.iustus` antes da primeira publicação. Nenhum projeto externo, cobrança, build em nuvem ou publicação foi criado nesta entrega.

O `npm audit` inicial apontou avisos em dependências transitivas do SDK (braces, node-forge, uuid e decode-uri-component). A correção automática sugeria inclusive downgrade incompatível do Expo. Não usar `npm audit fix --force`; revisar atualizações compatíveis e exposição dos avisos antes de distribuição externa.
