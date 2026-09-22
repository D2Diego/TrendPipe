# Como aplicar os 5 commits

## Onde cada coisa fica (leia antes de rodar)

Nesse repo (padrão de TCC da PUC) o `.git` fica na **raiz do repositório**
(a pasta que também tem `atas/`, `documentos/`, `apresentacao/`, `proex/`),
e o código de verdade fica **um nível abaixo**, dentro de `codigo-fonte/`:

```
pmv-ads-2026-2-...-yagolobo/        <- aqui fica o .git (raiz do repo)
├── .git/
├── atas/
├── documentos/
├── apresentacao/
├── proex/
└── codigo-fonte/                   <- TODOS os 5 zips extraem AQUI DENTRO
    ├── vendor/trendpipe/
    ├── app/
    ├── webui-react/
    ├── Dockerfile
    └── ...
```

**Todos os 5 zips vão pro mesmo lugar: `codigo-fonte/`.** Nunca na raiz do
repo, nunca em pasta separada por zip — é sempre essa mesma pasta, pra todo
mundo do grupo.

O `$DEST` que você passa pro `apply_commit.py` é `.../codigo-fonte`
(caminho completo até essa pasta). O `git commit`, por outro lado, precisa
enxergar o repo — e o repo git começa um nível **acima** de `codigo-fonte/`.
Por isso:

- Usando `apply_commit.py` (recomendado): ele já resolve isso sozinho —
  acha o `.git` subindo os diretórios a partir do `$DEST`, não importa de
  onde você rodou o comando.
- Rodando `git commit` na mão: **sempre com `-C "$DEST"`** (ou faça `cd
  "$DEST"` antes). Sem isso, se o seu terminal estiver em outra pasta (ex.:
  dentro de `dist-commits/` onde ficam os zips), o commit vai tentar rodar
  no repo errado.

Aplique **nessa ordem exata**, sempre no mesmo `target_dir` (`codigo-fonte/`),
commitando entre um e outro:

```bash
DEST=/caminho/para/codigo-fonte   # ajuste aqui

python3 apply_commit.py commit-1-vendor-trendpipe-engine.zip      "$DEST"
git -C "$DEST" commit -F <(unzip -p commit-1-vendor-trendpipe-engine.zip COMMIT_MESSAGE.txt)

python3 apply_commit.py commit-2-backend-api-wiring.zip           "$DEST"
git -C "$DEST" commit -F <(unzip -p commit-2-backend-api-wiring.zip COMMIT_MESSAGE.txt)

python3 apply_commit.py commit-3-frontend-app-foundation.zip      "$DEST"
git -C "$DEST" commit -F <(unzip -p commit-3-frontend-app-foundation.zip COMMIT_MESSAGE.txt)

python3 apply_commit.py commit-4-frontend-research-feature.zip    "$DEST"
git -C "$DEST" commit -F <(unzip -p commit-4-frontend-research-feature.zip COMMIT_MESSAGE.txt)

python3 apply_commit.py commit-5-docker-packaging.zip             "$DEST"
git -C "$DEST" commit -F <(unzip -p commit-5-docker-packaging.zip COMMIT_MESSAGE.txt)
```

O `apply_commit.py` só extrai e dá `git add` — quem decide e roda o `git
commit` é você (assim consegue revisar `git diff --cached` antes).

## No macOS

Os comandos bash lá em cima (os do início do manual) funcionam **sem
nenhuma alteração** — o Terminal do Mac usa zsh (padrão desde o macOS
Catalina) ou bash, e os dois suportam `$DEST`, `<(...)` e `unzip` do mesmo
jeito que Linux/WSL. Só confira antes:

```bash
python3 --version   # se der "command not found", instale com:
                     #   xcode-select --install   (Xcode Command Line Tools, traz python3 e git)
                     # ou, se já usa Homebrew:
                     #   brew install python3
git --version        # já vem no Xcode Command Line Tools também
unzip -v              # já vem instalado por padrão no macOS
```

Com isso funcionando, é rodar exatamente os comandos bash do topo do manual.

## No Windows (PowerShell, sem WSL)

O bloco acima é bash — não roda direto no PowerShell/CMD porque usa `$DEST`
no estilo bash, `<(...)` (process substitution) e `unzip`, e nenhum dos três
existe nativamente no Windows. Equivalente em PowerShell (abre o PowerShell
dentro da pasta `dist-commits`, onde estão os zips e o `apply_commit.py`):

```powershell
$DEST = "C:\caminho\completo\ate\codigo-fonte"   # troque pelo caminho real

python apply_commit.py commit-1-vendor-trendpipe-engine.zip $DEST
python -c "import zipfile; print(zipfile.ZipFile('commit-1-vendor-trendpipe-engine.zip').read('COMMIT_MESSAGE.txt').decode())" | git -C $DEST commit -F -

python apply_commit.py commit-2-backend-api-wiring.zip $DEST
python -c "import zipfile; print(zipfile.ZipFile('commit-2-backend-api-wiring.zip').read('COMMIT_MESSAGE.txt').decode())" | git -C $DEST commit -F -

python apply_commit.py commit-3-frontend-app-foundation.zip $DEST
python -c "import zipfile; print(zipfile.ZipFile('commit-3-frontend-app-foundation.zip').read('COMMIT_MESSAGE.txt').decode())" | git -C $DEST commit -F -

python apply_commit.py commit-4-frontend-research-feature.zip $DEST
python -c "import zipfile; print(zipfile.ZipFile('commit-4-frontend-research-feature.zip').read('COMMIT_MESSAGE.txt').decode())" | git -C $DEST commit -F -

python apply_commit.py commit-5-docker-packaging.zip $DEST
python -c "import zipfile; print(zipfile.ZipFile('commit-5-docker-packaging.zip').read('COMMIT_MESSAGE.txt').decode())" | git -C $DEST commit -F -
```

Notas:
- `$DEST` aqui é uma variável do **PowerShell**, não do bash — a sintaxe
  `$Nome = "valor"` e o uso depois como `$DEST` (sem aspas ao redor, o
  PowerShell entende) é diferente do `export DEST=...` do bash, mas serve
  pro mesmo propósito: evitar redigitar o caminho em cada linha.
- Se preferir não usar variável nenhuma, troca `$DEST` pelo caminho literal
  em cada linha, ex.: `python apply_commit.py commit-1-vendor-trendpipe-engine.zip "C:\Users\voce\tcc\codigo-fonte"`.
- É `python`, não `python3`, no Windows (a menos que você tenha instalado
  com o launcher `py`, aí também funciona `py apply_commit.py ...`).
- Isso assume Python e Git já instalados e no PATH (`python --version` e
  `git --version` funcionando no PowerShell). Se não tiver, é mais simples
  instalar o WSL (`wsl --install` no PowerShell como admin) e seguir os
  comandos bash do início do manual dentro do Ubuntu do WSL.

## O que cada zip carrega (e por quê nessa ordem)

| # | Zip | Path relativo dentro de `$DEST` | Depende de |
|---|-----|----------------------------------|------------|
| 1 | `commit-1-vendor-trendpipe-engine.zip` | `vendor/trendpipe/**` | nada |
| 2 | `commit-2-backend-api-wiring.zip` | `main.py`, `requirements.txt`, `config.example.toml`, `app/**` | commit 1 (chama `vendor/trendpipe/trendpipe.py` via subprocess) |
| 3 | `commit-3-frontend-app-foundation.zip` | `webui-react/package.json`, configs (`vite`, `tsconfig`, `tailwind`...), `webui-react/src/{main.tsx,index.css,i18n,lib,store,types,api,components/ui,test}` | nada do backend; é só o esqueleto React + peças compartilhadas que a feature usa |
| 4 | `commit-4-frontend-research-feature.zip` | `webui-react/src/features/researches/**`, `App.tsx`, `App.test.tsx`, `features/start/StartPage.tsx` | commit 3 (usa o esqueleto e os componentes de UI) + commit 2 (chama a API) |
| 5 | `commit-5-docker-packaging.zip` | `Dockerfile`, `docker-compose.yml`, `deploy/nginx-react.conf`, `.dockerignore` | commits 2-4 (builda e roda os dois) |

## Importante: isso NÃO é uma cópia 1:1 de 4 arquivos do repo original

Pra rodar sozinho (sem o resto do TrendPipe — geração de vídeo, TTS, etc.)
alguns arquivos compartilhados foram **adaptados**, não copiados como estão:

- `app/router.py` — no repo original registra ~12 controllers; aqui registra
  só o de research.
- `app/asgi.py` — no repo original o startup dispara
  `task_service.recover_interrupted_cross_posts()` (feature de cross-post de
  vídeo, puxa um monte de serviço não relacionado); aqui só inicializa o
  banco do research.
- `requirements.txt` — no repo original tem moviepy, edge-tts,
  faster-whisper, azure-speech etc. (~20 pacotes); aqui só o que o research
  precisa: `fastapi`, `uvicorn`, `openai`, `loguru`, `toml`.
- `webui-react/src/App.tsx` e `features/start/StartPage.tsx` — no repo
  original também montam a tela de geração de vídeo (`AudioPanel`,
  `VideoPanel`, `ScriptPanel`...) e um card linkando pra `/generate`; aqui
  só a rota `/researches`.
- `webui-react/src/App.test.tsx` — ajustado pra não testar mais a tela de
  `/generate`, que não existe nesse recorte.

Isso foi validado: consegui importar `app.asgi:app` de verdade com o venv do
projeto e ele só expõe as rotas `/api/v1/researches*`; e não sobrou nenhum
import quebrado pra `@/features/generation` ou `@/features/onboarding` no
frontend.

## Depois de aplicar os 5

```bash
cd "$DEST"
cp config.example.toml config.toml   # ou deixa: o app copia sozinho no 1º boot
pip install -r requirements.txt
python3 main.py                      # sobe a API em :8080 (http://127.0.0.1:8080/docs)

cd webui-react
npm install
npm run dev                          # sobe o front em :5173, ou:
# npm run build && cd .. && docker compose up --build   # sobe tudo containerizado
```

## Configurar API keys

Tem **duas** configurações de credenciais separadas — não confundir:

### 1. Fontes que o trendpipe consulta (Reddit, GitHub, buscadores, etc.)

Arquivo: `vendor/trendpipe/.env` (gitignorado, nunca commita).

```bash
cd "$DEST"
cp vendor/trendpipe/.env.example vendor/trendpipe/.env
# edita vendor/trendpipe/.env e preenche as chaves que você tiver
```

Todas as chaves são **opcionais** — reddit, github, hackernews, arxiv,
techmeme e outras fontes funcionam sem nenhuma chave (modo "keyless"). Mais
chave preenchida = mais fontes/melhor qualidade. Pra destravar rápido, as
mais fáceis de conseguir de graça são `SERPER_API_KEY`, `BRAVE_API_KEY` ou
`OPENAI_API_KEY`. A tela de configurações da UI (`/researches?settings=researcher`)
também escreve nesse arquivo por você.

### 2. LLM do "artifact chat" (a conversa sobre um cluster de pesquisa)

Arquivo: `config.toml` (gitignorado; é copiado de `config.example.toml` no
primeiro boot). Seção `[app]`:

```toml
llm_provider = "openai"       # ou "moonshot" (default), "gemini", "groq" etc.
openai_api_key = "sk-..."
openai_base_url = ""          # deixa vazio pra usar o padrão da OpenAI
```

Sem isso preenchido, tudo que **não** for o botão de chat/artifact-chat
funciona normal (criar pesquisa, listar, ver clusters) — só o chat que
depende de LLM configurado.

## O que NÃO vai nos zips (de propósito)

- `vendor/trendpipe/.env` — chaves de API reais, nunca deve ser versionado.
- `config.toml` (só o `.example.toml` vai) e `storage/` — estado local/gerado.
