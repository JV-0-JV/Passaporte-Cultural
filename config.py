"""
config.py
---------
Chaves de API para a busca automática de capas/informações.

AniList, VNDB, Open Library e iTunes NÃO precisam de chave — já funcionam
assim que você roda o projeto.

OMDb (Filme/Série) é gratuito, mas exige um cadastro rápido (só um
e-mail) para gerar uma chave pessoal. Sem a chave, a busca automática
desse tipo específico fica desligada (você ainda pode cadastrar a mídia
manualmente, só não vem a busca automática).

IGDB (Jogo) é gratuito, mas usa autenticação via Twitch: você precisa
criar um aplicativo no Twitch Developer Console para conseguir um
Client ID e um Client Secret (veja o passo a passo na seção 4 do
README.md).

Como conseguir cada chave (grátis):
- OMDb: https://www.omdbapi.com/apikey.aspx  (escolha o plano gratuito "FREE"), leva ~1 minuto
- IGDB: https://dev.twitch.tv/console/apps  (crie um app na Twitch e pegue Client ID + Client Secret), leva ~5 minutos — veja o passo a passo no README.md

Depois é só colar a chave entre as aspas abaixo e salvar o arquivo.
"""

OMDB_API_KEY = ""
IGDB_CLIENT_ID = ""
IGDB_CLIENT_SECRET = ""
