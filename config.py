"""
config.py
---------
Chaves de API para a busca automática de capas/informações.

AniList, VNDB, Open Library e iTunes NÃO precisam de chave — já funcionam
assim que você roda o projeto.

OMDb (Filme/Série) e RAWG (Jogo) são gratuitos, mas exigem um cadastro
rápido (só um e-mail) para gerar uma chave pessoal. Sem a chave, a busca
automática desses dois tipos específicos fica desligada (você ainda
pode cadastrar a mídia manualmente, só não vem a busca automática).

Como conseguir cada chave (grátis, leva ~1 minuto):
- OMDb: https://www.omdbapi.com/apikey.aspx  (escolha o plano gratuito "FREE")
- RAWG: https://rawg.io/apidocs  (crie uma conta e pegue sua chave no painel)

Depois é só colar a chave entre as aspas abaixo e salvar o arquivo.
"""

OMDB_API_KEY = ""
RAWG_API_KEY = ""
