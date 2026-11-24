# Gerar o Íustus para Android e iOS

Execute os comandos na pasta `mobile`, com Node 24. A versão preparada é 1.0.0.
Os identificadores atuais são `br.org.ajaanadecon.iustus` nas duas plataformas.

## Preparação única da sua conta

```sh
npm ci
npx eas-cli@latest login
npx eas-cli@latest init
```

O `init` vincula este aplicativo ao seu projeto Expo e registra o `projectId` no
app config. Use a conta/organização que será proprietária do app. Esse vínculo
e as credenciais Apple/Google não são inventados nem compartilhados no código.
Preserve o vínculo gerado para as próximas builds.

## Conferir e gerar

```sh
npm run release:check
npm run service:check
```

O primeiro comando valida configuração, TypeScript, lint, testes e bundles das
três plataformas. O segundo consulta a API pública, sem enviar e-mails ou
alterar contas. Para testar a interface com dados simulados:

```sh
npx playwright install chromium
npm run test:ui
```

| Objetivo | Comando | Resultado |
| --- | --- | --- |
| Instalar no Android para testar | `npm run build:android:preview` | APK |
| Enviar ao Google Play | `npm run build:android` | AAB assinado |
| Enviar ao TestFlight/App Store | `npm run build:ios` | Build iOS assinada |

O EAS pede as credenciais de assinatura necessárias durante a geração. Uma
build iOS para distribuição requer a conta Apple Developer apropriada. Os
comandos de build não submetem nem publicam automaticamente nas lojas.

## Configuração incluída

- Origem pública `https://www.iustus.app` nos perfis preview e production.
- Ícone 1024 px sem transparência, ícone adaptativo Android e splash com a marca
  existente, exportada do SVG do projeto.
- Numeração remota com incremento automático em produção.
- SecureStore, câmera, arquivos e compartilhamento configurados por plugins.
- Microfone bloqueado no Android: o app captura fotografias de documentos.
- `.easignore` na raiz inclui mobile e contratos compartilhados, excluindo
  backend, arquivos de ambiente, credenciais, dependências e dados locais.
- `eas-build-post-install` confere assets, contratos e origem antes da compilação.

Para desenvolvimento, copie `.env.example` para `.env.local`. Para homologação
em outro servidor, altere a origem pública no perfil correspondente de
`eas.json`; não use a URL privada do Django nem inclua segredos no aplicativo.

## Comportamentos da primeira versão

A jornada é do associado. Profissionais usam o portal. Cadastro e checkout
obedecem aos flags da API; o checkout, quando habilitado, abre o portal. O
retorno ao app atualiza a associação quando o painel recebe foco. Confirmação
de e-mail, ativação e recuperação aceitam o link completo na tela de acesso;
links nativos `iustus://access#reset=TOKEN` também preenchem essa tela. Links de
caso `iustus://open-case/UUID` preservam o destino durante o login.

Avisos ficam na aba Avisos e são atualizados ao entrar nela. Não há push externo
nesta versão. A exclusão de conta é solicitada dentro do app, sem obrigar o
usuário a escrever uma justificativa, e acompanhada pela área de privacidade;
a operação responde e executa o tratamento aplicável dos registros.

## Validação e limites

Verificações executadas nesta revisão:

- TypeScript e ESLint aprovados.
- 7 testes de transporte e links aprovados.
- 12 testes Playwright no Edge aprovados, com API simulada.
- 69 testes backend de mobile, identidade, documentos, propostas e contratos
  entre canais aprovados em banco de teste SQLite.
- Expo Doctor: 21/21 verificações aprovadas.
- Configuração nativa Android/iOS validada por `expo config --type introspect`.
- Exportação dos bundles Android, iOS e web aprovada.

Em 09/11/2026, os endpoints públicos mobile responderam após uma primeira
resposta 503 durante a disponibilidade inicial do serviço. O servidor informou
cadastro por ativação, checkout mobile desabilitado e Mercado Pago em sandbox.
Esses flags precisam refletir o ambiente desejado antes da distribuição real.

Testes de interface usam API simulada. Exportar JavaScript e validar os plugins
nativos não substitui instalar a build assinada em Android/iPhone e conferir
câmera, compartilhamento, armazenamento de sessão, teclado e links externos.
As contas das lojas, assinatura e aprovação continuam vinculadas ao proprietário.

As correções compatíveis de dependências foram aplicadas sem trocar o SDK 57.
O audit caiu de 20 para 14 avisos (11 moderados e 3 altos, contando a cadeia de
dependências afetadas). Ainda aponta dependências de Expo/ESLint, inclusive
`decode-uri-component` usado pelo Router. Não aplicar `audit fix --force`:
a resolução sugerida troca versões principais. Revisar a atualização do SDK
e suas dependências antes de uma distribuição pública ampla.

Referências: [build em monorepo](https://docs.expo.dev/build-reference/build-with-monorepos/),
[arquivos enviados ao EAS](https://docs.expo.dev/build-reference/easignore/),
[versões de build](https://docs.expo.dev/build-reference/app-versions/).
