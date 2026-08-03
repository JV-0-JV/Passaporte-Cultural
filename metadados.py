"""
metadados.py
------------
Busca automática de capas e informações em APIs públicas, uma por tipo
de mídia — a mesma ideia do Kechimochi (que busca em AniList, VNDB,
Bookmeter, etc), só que usando APIs que são livres/gratuitas de verdade:

    Anime            -> AniList        (sem chave)
    Mangá            -> AniList        (sem chave)
    Novel            -> AniList        (sem chave, formato "light novel")
    Visual Novel     -> VNDB           (sem chave)
    Livro / HQ       -> Open Library   (sem chave)
    Podcast / Música -> iTunes Search  (sem chave)
    Filme / Série    -> OMDb           (precisa de chave grátis, veja config.py)
    Jogo             -> IGDB           (precisa de Client ID/Secret grátis, veja config.py)

Todas as funções abaixo devolvem uma lista no MESMO formato, não importa
a fonte, para o resto do app não precisar saber de onde veio:

    [{"titulo": ..., "capa_url": ..., "ano": ..., "descricao": ..., "fonte": ...}, ...]
"""

import requests

import config

TIMEOUT = 8  # segundos - não trava o site esperando um site externo lento


def _limpar_descricao(texto, limite=400):
    if not texto:
        return None
    texto = (
        texto.replace('<br>', ' ')
        .replace('<br/>', ' ')
        .replace('<i>', '')
        .replace('</i>', '')
        .replace('<b>', '')
        .replace('</b>', '')
    )
    texto = ' '.join(texto.split())
    return texto[:limite]


# ---------------------------------------------------------------------
# ANILIST (Anime, Mangá, Novel) — API GraphQL, sem chave
# ---------------------------------------------------------------------

def buscar_anilist(query, tipo_anilist, formato=None):
    gql = '''
    query ($search: String, $type: MediaType, $format: [MediaFormat]) {
      Page(page: 1, perPage: 6) {
        media(search: $search, type: $type, format_in: $format) {
          title { romaji english native }
          coverImage { large }
          startDate { year }
          description(asHtml: false)
        }
      }
    }
    '''
    variaveis = {'search': query, 'type': tipo_anilist}
    if formato:
        variaveis['format'] = [formato]

    resp = requests.post(
        'https://graphql.anilist.co',
        json={'query': gql, 'variables': variaveis},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    dados = resp.json()

    if dados.get('errors'):
        raise ValueError(dados['errors'][0].get('message', 'Erro na busca do AniList'))

    resultados = []
    for m in dados.get('data', {}).get('Page', {}).get('media', []):
        titulo_obj = m.get('title', {})
        titulo = titulo_obj.get('english') or titulo_obj.get('romaji') or titulo_obj.get('native')
        resultados.append({
            'titulo': titulo,
            'capa_url': (m.get('coverImage') or {}).get('large'),
            'ano': (m.get('startDate') or {}).get('year'),
            'descricao': _limpar_descricao(m.get('description')),
            'fonte': 'AniList',
        })
    return resultados


# ---------------------------------------------------------------------
# VNDB (Visual Novel) — API "Kana" v2, sem chave para busca básica
# ---------------------------------------------------------------------

def buscar_vndb(query):
    corpo = {
        'filters': ['search', '=', query],
        'fields': 'title, image.url, released, description',
        'results': 6,
    }
    resp = requests.post('https://api.vndb.org/kana/vn', json=corpo, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    resultados = []
    for vn in dados.get('results', []):
        lancamento = vn.get('released') or ''
        resultados.append({
            'titulo': vn.get('title'),
            'capa_url': (vn.get('image') or {}).get('url'),
            'ano': lancamento[:4] if lancamento else None,
            'descricao': _limpar_descricao(vn.get('description')),
            'fonte': 'VNDB',
        })
    return resultados


# ---------------------------------------------------------------------
# OMDb (Filme, Série) — precisa de chave gratuita em config.py
# ---------------------------------------------------------------------

def buscar_omdb(query, tipo_omdb):
    if not config.OMDB_API_KEY:
        raise ValueError('Chave da OMDb não configurada. Veja config.py.')

    params = {'apikey': config.OMDB_API_KEY, 's': query, 'type': tipo_omdb}
    resp = requests.get('https://www.omdbapi.com/', params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    if dados.get('Response') == 'False':
        return []

    resultados = []
    for item in dados.get('Search', [])[:6]:
        capa = item.get('Poster')
        resultados.append({
            'titulo': item.get('Title'),
            'capa_url': capa if capa and capa != 'N/A' else None,
            'ano': item.get('Year'),
            'descricao': None,  # a busca por lista não traz sinopse na OMDb
            'fonte': 'OMDb',
        })
    return resultados


# ---------------------------------------------------------------------
# IGDB (Jogo) — precisa de Client ID + Client Secret gratuitos em config.py
#
# A IGDB usa autenticação OAuth2 da Twitch: antes de buscar jogos, é
# preciso trocar o Client ID/Secret por um "access token" temporário.
# Guardamos esse token em memória (_igdb_token) e só pedimos um novo
# quando ele expira, para não gastar uma chamada extra a cada busca.
# ---------------------------------------------------------------------

_igdb_token = {'valor': None, 'expira_em': 0}


def _obter_token_igdb():
    import time

    if _igdb_token['valor'] and time.time() < _igdb_token['expira_em']:
        return _igdb_token['valor']

    params = {
        'client_id': config.IGDB_CLIENT_ID,
        'client_secret': config.IGDB_CLIENT_SECRET,
        'grant_type': 'client_credentials',
    }
    resp = requests.post('https://id.twitch.tv/oauth2/token', params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    _igdb_token['valor'] = dados['access_token']
    # Guarda uma margem de segurança de 60s antes do vencimento real
    _igdb_token['expira_em'] = time.time() + dados.get('expires_in', 0) - 60
    return _igdb_token['valor']


def buscar_igdb(query):
    if not config.IGDB_CLIENT_ID or not config.IGDB_CLIENT_SECRET:
        raise ValueError('Client ID/Secret da IGDB não configurados. Veja config.py.')

    token = _obter_token_igdb()
    headers = {
        'Client-ID': config.IGDB_CLIENT_ID,
        'Authorization': f'Bearer {token}',
    }
    # A IGDB usa a linguagem de consulta "Apicalypse" em vez de query params comuns
    corpo = (
        f'search "{query}"; '
        'fields name, cover.url, first_release_date, summary; '
        'limit 6;'
    )
    resp = requests.post(
        'https://api.igdb.com/v4/games',
        headers=headers,
        data=corpo,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    dados = resp.json()

    resultados = []
    for item in dados[:6]:
        capa = (item.get('cover') or {}).get('url')
        if capa:
            # A IGDB devolve a capa em miniatura ("t_thumb"); trocamos por
            # uma resolução maior ("t_cover_big") e adicionamos o https:
            capa = 'https:' + capa.replace('t_thumb', 't_cover_big')

        ano = None
        if item.get('first_release_date'):
            from datetime import datetime, timezone
            ano = datetime.fromtimestamp(item['first_release_date'], tz=timezone.utc).year

        resultados.append({
            'titulo': item.get('name'),
            'capa_url': capa,
            'ano': ano,
            'descricao': _limpar_descricao(item.get('summary')),
            'fonte': 'IGDB',
        })
    return resultados


# ---------------------------------------------------------------------
# OPEN LIBRARY (Livro, HQ) — sem chave
# ---------------------------------------------------------------------

def buscar_openlibrary(query):
    params = {'q': query, 'limit': 6}
    resp = requests.get('https://openlibrary.org/search.json', params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    resultados = []
    for doc in dados.get('docs', [])[:6]:
        capa_url = None
        if doc.get('cover_i'):
            capa_url = f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg"
        autores = ', '.join(doc.get('author_name', [])[:2]) or None
        resultados.append({
            'titulo': doc.get('title'),
            'capa_url': capa_url,
            'ano': doc.get('first_publish_year'),
            'descricao': f'de {autores}' if autores else None,
            'fonte': 'Open Library',
        })
    return resultados


# ---------------------------------------------------------------------
# ITUNES SEARCH (Podcast, Música) — sem chave
# ---------------------------------------------------------------------

def buscar_itunes(query, media):
    params = {'term': query, 'media': media, 'limit': 6}
    resp = requests.get('https://itunes.apple.com/search', params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    resultados = []
    for item in dados.get('results', [])[:6]:
        titulo = item.get('trackName') or item.get('collectionName')
        lancamento = item.get('releaseDate') or ''
        resultados.append({
            'titulo': titulo,
            'capa_url': item.get('artworkUrl100'),
            'ano': lancamento[:4] if lancamento else None,
            'descricao': item.get('artistName'),
            'fonte': 'iTunes',
        })
    return resultados


# ---------------------------------------------------------------------
# DESPACHANTE: escolhe a função certa a partir do tipo de mídia
# ---------------------------------------------------------------------

def buscar(tipo, query):
    if tipo == 'Anime':
        return buscar_anilist(query, 'ANIME')
    if tipo == 'Mangá':
        return buscar_anilist(query, 'MANGA', formato='MANGA')
    if tipo == 'Novel':
        return buscar_anilist(query, 'MANGA', formato='NOVEL')
    if tipo == 'Visual Novel':
        return buscar_vndb(query)
    if tipo == 'Filme':
        return buscar_omdb(query, 'movie')
    if tipo == 'Série':
        return buscar_omdb(query, 'series')
    if tipo == 'Jogo':
        return buscar_igdb(query)
    if tipo in ('Livro', 'HQ'):
        return buscar_openlibrary(query)
    if tipo == 'Podcast':
        return buscar_itunes(query, 'podcast')
    if tipo == 'Música':
        return buscar_itunes(query, 'music')
    raise ValueError(f'Não existe busca automática para o tipo "{tipo}".')
