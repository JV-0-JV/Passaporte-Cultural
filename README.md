# Passaporte Cultural

Um rastreador pessoal de imersão em idiomas e com um objetivo extra: ajudar a montar **repertório sociocultural para redação**.

Trabalho de faculdade, primeiro período, feito com apoio de IA. 

---

## 1. O que o projeto faz

- **Biblioteca de mídias**: cadastre filmes, séries, animes, jogos, livros, mangás, HQs, visual novels, novels, podcasts, música — em qualquer idioma que você esteja estudando.
- **Busca automática de capa e informações**: ao cadastrar uma mídia, clique em "Buscar" e o app procura a capa, ano e sinopse automaticamente em APIs públicas (uma para cada tipo de mídia — veja a seção 3 abaixo).
- **Log de imersão**: para cada mídia, registre sessões (data + minutos + episódios/páginas/palavras, dependendo do tipo), como um diário de estudo.
- **Painel**: horas totais, horas por idioma, mídias por tipo, atividade dos últimos 7 dias, **mapa de calor de atividade** (estilo GitHub) dos últimos 12 meses, e uma tabela de detalhamento por idioma (horas, mídias, episódios, páginas, palavras).
- **Repertório sociocultural**: marque qualquer mídia como "repertório", associe um tema (ex: meio ambiente, inclusão, tecnologia) e escreva uma anotação. Depois é só abrir a aba **Repertório** antes de escrever uma redação e revisar tudo já organizado por tema.
- **Backup**: exporta tudo em um `.json` (para guardar ou levar para outro computador), importa de volta, e opcionalmente **sincroniza direto com o Google Drive**.

## 2. Requisitos

- **Site local** (Python + Flask), roda no navegador 
- **backup local** (exportar/importar .json)
- **Busca automática**, em OMDb, IGDB, Open Library, AniList, VNDB e iTunes 
- **Qualquer idioma**, faça o track de suas imersões em qualquer idioma 
- Aba de **repertório sociocultural**
- **Sync com Google Drive** (opcional)

## 3. Como o projeto é organizado (arquitetura)

```
passaporte-cultural/
├── app.py               # Backend: todas as rotas da API (o "C-R-U-D")
├── database.py          # Conexão com o banco e criação das tabelas
├── metadados.py          # Busca automática de capas/informações (AniList, VNDB, OMDb, IGDB, Open Library, iTunes)
├── config.py             # Suas chaves de API (OMDb e IGDB) — veja seção 4
├── drive_sync.py          # Sincronização opcional com o Google Drive
├── autenticar_drive.py    # Script para conectar sua conta do Google (rodar 1x)
├── seed_exemplo.py       # Script opcional: preenche o banco com exemplos
├── teste_metadados.py     # Script opcional: valida a lógica de busca de metadados
├── requirements.txt     # Lista de dependências Python
├── data/
│   └── imersao.db        # Banco SQLite — TODOS os seus dados ficam aqui
├── templates/
│   └── index.html       # A página HTML única do site
└── static/
    ├── style.css         # Toda a aparência visual
    └── script.js         # Toda a lógica do frontend (chama a API, monta a tela)
```

**Como as peças conversam:**

1. O **navegador** carrega `index.html`, que carrega `style.css` e `script.js`.
2. `script.js` faz chamadas `fetch()` para endereços como `/api/midias`.
3. Essas chamadas chegam no **Flask** (`app.py`), que lê/escreve no banco (`database.py`) ou, quando é uma busca de capa, repassa para `metadados.py`, que conversa com o site externo certo — e devolve tudo em JSON.
4. `script.js` recebe o JSON e desenha a tela (cards, gráficos, formulários).

Isso é o modelo clássico de **CRUD com API REST**: o frontend nunca acessa o banco (nem os sites externos) diretamente, só conversa com o backend por HTTP.

### Banco de dados (2 tabelas)

- **`midias`**: uma linha por mídia (título, tipo, idioma, status, nota, progresso, se é repertório, tema, anotações...).
- **`atividades`**: uma linha por sessão de imersão registrada (data, minutos, quantidade — episódios/páginas/palavras — ligada a uma mídia pelo `midia_id`).

## 4. Busca automática de capas e informações

| Tipo de mídia | API usada | Precisa de chave? |
|---|---|---|
| Anime, Mangá, Novel | [AniList](https://anilist.co) | Não — já funciona |
| Visual Novel | [VNDB](https://vndb.org) | Não — já funciona |
| Livro, HQ | [Open Library](https://openlibrary.org) | Não — já funciona |
| Podcast, Música | [iTunes Search](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) | Não — já funciona |
| Filme, Série | [OMDb](https://www.omdbapi.com) | **Sim**, grátis |
| Jogo | [IGDB](https://api-docs.igdb.com/) | **Sim**, grátis (via login Twitch) |

Ou seja: assim que você roda o projeto, a busca automática **já funciona** para 4 dos 6 grupos de tipos. Só Filme/Série e Jogo precisam de credenciais gratuitas:

1. **OMDb**: acesse https://www.omdbapi.com/apikey.aspx, escolha o plano **FREE** (1.000 buscas/dia), preencha e-mail e confirme pelo link que chega na caixa de entrada.

2. **IGDB**: a IGDB pertence à Twitch, então a chave é gerada através de uma conta Twitch, seguindo estes passos:
   1. Crie uma conta gratuita em https://www.twitch.tv (se ainda não tiver uma) e depois acesse o Twitch Developer Console em https://dev.twitch.tv/console/apps.
   2. Clique em **Register Your Application**.
   3. Preencha:
      - **Name**: qualquer nome (ex: `passaporte-cultural`).
      - **OAuth Redirect URLs**: `http://localhost`.
      - **Category**: escolha `Application Integration` (ou similar).
   4. Salve e, na lista de aplicativos, clique em **Manage** no app que você acabou de criar.
   5. Copie o **Client ID** que aparece na tela.
   6. Clique em **New Secret** para gerar o **Client Secret** e copie-o também (ele só aparece uma vez — se perder, gere outro).

3. Abra o arquivo `config.py` e cole cada credencial entre as aspas:

```python
OMDB_API_KEY = "sua-chave-aqui"
IGDB_CLIENT_ID = "seu-client-id-aqui"
IGDB_CLIENT_SECRET = "seu-client-secret-aqui"
```

4. Salve o arquivo e reinicie o servidor (`Ctrl+C` e rode `python3 app.py` de novo).

Se você não configurar essas credenciais, o resto do app continua funcionando normalmente — só a busca automática de Filme/Série/Jogo fica desativada (você preenche esses campos na mão).

> **Como funciona por trás dos panos:** diferente das outras APIs, a IGDB não aceita o Client ID/Secret diretamente nas buscas. O app primeiro troca essas credenciais por um "access token" temporário junto à Twitch (isso é automático, feito em `metadados.py`) e só depois usa esse token para buscar os jogos. O token é guardado em memória enquanto o servidor roda e renovado sozinho quando expira, então você não precisa se preocupar com isso no dia a dia.

## 5. Sincronização com Google Drive (opcional)

Isso é **opcional** — o backup local (exportar/importar `.json`, seção 6) já cobre a necessidade básica. Mas se quiser sincronizar de verdade com o Google Drive, o passo a passo é:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um novo projeto (gratuito).
2. No menu, vá em **APIs e serviços → Biblioteca**, procure por "Google Drive API" e clique em **Ativar**.
3. Vá em **APIs e serviços → Tela de consentimento OAuth**. Escolha **Externo**, preencha nome do app e seu e-mail, e em "usuários de teste" adicione o seu próprio e-mail do Google. Isso evita precisar passar pelo processo de verificação do Google (só quem você adicionar como testador consegue logar).
4. Vá em **APIs e serviços → Credenciais → Criar credenciais → ID do cliente OAuth**. Escolha o tipo **App para computador** (Desktop app).
5. Baixe o arquivo JSON gerado, renomeie para `client_secret.json` e coloque na pasta `passaporte-cultural` (a mesma pasta do `app.py`).
6. No terminal, rode:
   ```bash
   python3 autenticar_drive.py
   ```
   Isso abre uma aba no navegador pedindo login no Google — faça login com a mesma conta que você adicionou como testador, e autorize.
7. Pronto! Na aba **Backup** do site, os botões "Enviar para o Drive" e "Baixar do Drive" já vão funcionar.

O app pede só a permissão `drive.file`, que dá acesso **apenas ao arquivo que ele mesmo cria** — nunca ao resto do seu Google Drive.

## 6. Como rodar na sua máquina

Você precisa ter **Python 3** instalado ([python.org](https://www.python.org/downloads/) — no Windows, marque "Add Python to PATH" durante a instalação).

Abra um terminal dentro da pasta `passaporte-cultural` e rode:

```bash
pip install -r requirements.txt
python3 app.py
```

(No Windows, use `python` em vez de `python3` se `python3` não for reconhecido.)

Você vai ver algo como `Running on http://127.0.0.1:5000`. Abra esse endereço no navegador — pronto, o site está rodando **localmente** (localhost = seu próprio computador, ninguém mais acessa).

Para parar o servidor, `Ctrl+C` no terminal.

O banco já vem com **5 mídias de exemplo** (para você não abrir uma tela vazia). Se quiser recomeçar do zero, apague o arquivo `data/imersao.db` e rode `python3 seed_exemplo.py` de novo (ou simplesmente não rode nada — o `app.py` cria um banco vazio sozinho na primeira execução).

Lembrando: busca automática de capa (seção 4) e Google Drive (seção 5) são **opcionais** — o site roda perfeitamente sem configurar nenhum dos dois.

## 7. Para apresentar / defender o trabalho

- **Backend (Flask/Python)**: define "rotas" — cada rota é uma URL + um verbo HTTP (GET busca, POST cria, PUT atualiza, DELETE apaga). Isso está todo em `app.py`.
- **Banco de dados (SQLite)**: um arquivo só, sem precisar instalar servidor de banco nenhum. As tabelas estão descritas em `database.py`.
- **Frontend (HTML/CSS/JS puro, sem framework)**: `script.js` usa `fetch()` para conversar com o backend e `innerHTML` para desenhar os cards na tela — nenhuma biblioteca externa além do Chart.js (só para os gráficos).
- **CRUD**: toda operação de "Criar mídia", "Editar", "Apagar" no site corresponde diretamente a um `POST`, `PUT` ou `DELETE` em `app.py`.
- **Integrações externas**: `metadados.py` isola toda a lógica de "conversar com sites de fora" (AniList, VNDB, OMDb, IGDB, Open Library, iTunes) atrás de uma única função `buscar(tipo, query)` — o resto do app não precisa saber os detalhes de cada API.
- **Google Drive**: `drive_sync.py` usa o protocolo OAuth 2.0 (o mesmo que "Entrar com o Google" usa) para pedir permissão, e a API do Google Drive para enviar/baixar o arquivo de backup.

## 8. Possíveis extensões futuras (se quiser ir além)

- Gráfico de "ritmo de leitura" (para prever quando você termina um livro/mangá com base no seu ritmo atual).
- Sincronização automática em segundo plano (hoje o envio/download do Google Drive é manual, por botão).
- Cache local das buscas de metadados, para não repetir a mesma busca em APIs externas toda vez.
