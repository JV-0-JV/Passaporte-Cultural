"""
database.py
------------
Tudo relacionado ao banco de dados SQLite fica neste arquivo:
- como conectar
- como criar as tabelas na primeira vez que o app roda

Usamos SQLite porque ele não precisa de instalação nenhuma: é só um
arquivo (data/imersao.db) que o Python lê e escreve diretamente.
"""

import sqlite3
import os

PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PASTA_ATUAL, 'data', 'imersao.db')


def get_db():
    """Abre uma conexão nova com o banco de dados."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # permite acessar colunas pelo nome (linha['titulo'])
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    """Cria as tabelas do zero, caso ainda não existam."""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS midias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            idioma TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Quero começar',
            nota INTEGER,
            progresso TEXT,
            capa_url TEXT,
            repertorio INTEGER NOT NULL DEFAULT 0,
            tema_repertorio TEXT,
            anotacoes TEXT,
            data_criacao TEXT NOT NULL DEFAULT (datetime('now')),
            data_inicio TEXT,
            data_fim TEXT
        );

        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            midia_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            minutos INTEGER NOT NULL,
            quantidade INTEGER,
            observacao TEXT,
            FOREIGN KEY (midia_id) REFERENCES midias (id) ON DELETE CASCADE
        );

        -- Tabela de perfil (cabeçalho, bio, badges, redes sociais e filmes favoritos top 4)
        CREATE TABLE IF NOT EXISTS perfil (
            id INTEGER PRIMARY KEY DEFAULT 1,
            nome TEXT NOT NULL DEFAULT 'Viajante Cultural',
            localizacao TEXT DEFAULT 'São Paulo, Brasil',
            avatar_url TEXT DEFAULT '',
            bio TEXT DEFAULT 'Explorando o mundo através do cinema, leitura e imersão cultural em idiomas.',
            links_sociais TEXT DEFAULT '{"letterboxd": "https://letterboxd.com", "github": "https://github.com", "instagram": "https://instagram.com"}',
            seguidores INTEGER DEFAULT 128,
            seguindo INTEGER DEFAULT 45,
            badge_pro INTEGER DEFAULT 1,
            badge_patron INTEGER DEFAULT 1,
            top4_midias TEXT DEFAULT '[]'
        );
    ''')
    conn.commit()

    # Se o banco já existia de uma versão anterior do projeto (sem a coluna
    # "quantidade"), adiciona ela agora, sem apagar nada que já estava salvo.
    colunas = [linha['name'] for linha in conn.execute('PRAGMA table_info(atividades)').fetchall()]
    if 'quantidade' not in colunas:
        conn.execute('ALTER TABLE atividades ADD COLUMN quantidade INTEGER')
        conn.commit()

    # "unidade" guarda em que unidade a "quantidade" daquela sessão foi
    # registrada (ex: 'páginas' ou 'palavras'). Esse campo é da época em
    # que a sessão escolhia UMA unidade por vez com um seletor; hoje ele só
    # é mantido para não perder sessões antigas (veja migração abaixo).
    if 'unidade' not in colunas:
        conn.execute('ALTER TABLE atividades ADD COLUMN unidade TEXT')
        conn.commit()

    # "paginas" e "palavras" são campos dedicados e independentes: uma
    # sessão de Livro/Mangá/HQ/Novel pode ter as duas quantidades juntas
    # (ex: avançou 20 páginas e também leu 4.000 palavras naquele dia), e
    # Visual Novel usa só "palavras". Substituem o antigo par
    # "quantidade" + "unidade" para esses tipos.
    paginas_eh_nova = 'paginas' not in colunas
    palavras_eh_nova = 'palavras' not in colunas

    if paginas_eh_nova:
        conn.execute('ALTER TABLE atividades ADD COLUMN paginas INTEGER')
        conn.commit()
    if palavras_eh_nova:
        conn.execute('ALTER TABLE atividades ADD COLUMN palavras INTEGER')
        conn.commit()

    if paginas_eh_nova or palavras_eh_nova:
        # Migração única: sessões registradas antes dessa mudança guardavam
        # a quantidade de Livro/Mangá/HQ/Novel/Visual Novel no campo
        # genérico "quantidade" (com "unidade" indicando se era páginas ou
        # palavras, quando preenchida). Copiamos esse valor para o campo
        # dedicado certo. Série/Anime não entram aqui: continuam usando
        # "quantidade" normalmente, para episódios.
        conn.execute('''
            UPDATE atividades
            SET paginas = quantidade
            WHERE quantidade IS NOT NULL
              AND paginas IS NULL
              AND midia_id IN (SELECT id FROM midias WHERE tipo IN ('Livro', 'Mangá', 'HQ'))
              AND (unidade IS NULL OR unidade = 'páginas')
        ''')
        conn.execute('''
            UPDATE atividades
            SET palavras = quantidade
            WHERE quantidade IS NOT NULL
              AND palavras IS NULL
              AND midia_id IN (SELECT id FROM midias WHERE tipo IN ('Novel', 'Visual Novel'))
              AND (unidade IS NULL OR unidade = 'palavras')
        ''')
        conn.execute('''
            UPDATE atividades
            SET palavras = quantidade
            WHERE quantidade IS NOT NULL
              AND palavras IS NULL
              AND midia_id IN (SELECT id FROM midias WHERE tipo IN ('Livro', 'Mangá', 'HQ'))
              AND unidade = 'palavras'
        ''')
        conn.commit()

    # Garante que o perfil inicial (ID 1) existe no banco de dados
    existente_perfil = conn.execute('SELECT id FROM perfil WHERE id = 1').fetchone()
    if not existente_perfil:
        conn.execute('''
            INSERT INTO perfil (id, nome, localizacao, avatar_url, bio, links_sociais, seguidores, seguindo, badge_pro, badge_patron, top4_midias)
            VALUES (1, 'Viajante Cultural', 'São Paulo, Brasil',
                    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop&q=80',
                    'Explorando o mundo através do cinema, literatura e imersão cultural.',
                    '{"letterboxd": "https://letterboxd.com", "github": "https://github.com", "instagram": "https://instagram.com"}',
                    128, 45, 1, 1, '[]')
        ''')
        conn.commit()

    conn.close()
