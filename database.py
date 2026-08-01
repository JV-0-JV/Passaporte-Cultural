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
    ''')
    conn.commit()

    # Se o banco já existia de uma versão anterior do projeto (sem a coluna
    # "quantidade"), adiciona ela agora, sem apagar nada que já estava salvo.
    colunas = [linha['name'] for linha in conn.execute('PRAGMA table_info(atividades)').fetchall()]
    if 'quantidade' not in colunas:
        conn.execute('ALTER TABLE atividades ADD COLUMN quantidade INTEGER')
        conn.commit()

    conn.close()
