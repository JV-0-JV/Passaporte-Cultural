"""
app.py
------
Backend em Flask do "Passaporte Cultural".

Cada função abaixo (chamada de "rota") responde a um endereço da API.
O padrão que seguimos é REST:
    GET    /api/midias          -> listar
    POST   /api/midias          -> criar
    GET    /api/midias/<id>     -> ver uma
    PUT    /api/midias/<id>     -> editar
    DELETE /api/midias/<id>     -> apagar

Isso é o "CRUD": Create, Read, Update, Delete.
"""

import json
from datetime import datetime

from flask import Flask, jsonify, request, render_template, Response

from database import get_db, init_db
import metadados
import drive_sync

app = Flask(__name__)

# Garante que o banco e as tabelas existem assim que o servidor sobe.
init_db()


# ---------------------------------------------------------------------------
# PÁGINA PRINCIPAL (frontend)
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


# ---------------------------------------------------------------------------
# CRUD DE MÍDIAS
# ---------------------------------------------------------------------------

@app.route('/api/midias', methods=['GET'])
def listar_midias():
    """Lista mídias, com filtros opcionais por idioma, tipo, status,
    repertório (?repertorio=1) e busca por texto no título (?busca=)."""
    idioma = request.args.get('idioma')
    tipo = request.args.get('tipo')
    status = request.args.get('status')
    repertorio = request.args.get('repertorio')
    busca = request.args.get('busca')

    query = 'SELECT * FROM midias WHERE 1=1'
    params = []

    if idioma:
        query += ' AND idioma = ?'
        params.append(idioma)
    if tipo:
        query += ' AND tipo = ?'
        params.append(tipo)
    if status:
        query += ' AND status = ?'
        params.append(status)
    if repertorio == '1':
        query += ' AND repertorio = 1'
    if busca:
        query += ' AND titulo LIKE ?'
        params.append(f'%{busca}%')

    query += ' ORDER BY datetime(data_criacao) DESC'

    conn = get_db()
    linhas = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(linha) for linha in linhas])


@app.route('/api/midias/<int:midia_id>', methods=['GET'])
def obter_midia(midia_id):
    conn = get_db()
    midia = conn.execute('SELECT * FROM midias WHERE id = ?', (midia_id,)).fetchone()
    if midia is None:
        conn.close()
        return jsonify({'erro': 'Mídia não encontrada'}), 404

    atividades = conn.execute(
        'SELECT * FROM atividades WHERE midia_id = ? ORDER BY date(data) DESC, id DESC',
        (midia_id,)
    ).fetchall()
    conn.close()

    resultado = dict(midia)
    resultado['atividades'] = [dict(a) for a in atividades]
    return jsonify(resultado)


@app.route('/api/midias', methods=['POST'])
def criar_midia():
    dados = request.get_json(force=True) or {}

    if not dados.get('titulo') or not dados.get('tipo') or not dados.get('idioma'):
        return jsonify({'erro': 'Título, tipo e idioma são obrigatórios'}), 400

    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO midias
            (titulo, tipo, idioma, status, nota, progresso, capa_url,
             repertorio, tema_repertorio, anotacoes, data_inicio, data_fim)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        dados.get('titulo', '').strip(),
        dados.get('tipo'),
        dados.get('idioma', '').strip(),
        dados.get('status') or 'Quero começar',
        dados.get('nota'),
        dados.get('progresso'),
        dados.get('capa_url'),
        1 if dados.get('repertorio') else 0,
        dados.get('tema_repertorio'),
        dados.get('anotacoes'),
        dados.get('data_inicio'),
        dados.get('data_fim'),
    ))
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return jsonify({'id': novo_id}), 201


@app.route('/api/midias/<int:midia_id>', methods=['PUT'])
def atualizar_midia(midia_id):
    dados = request.get_json(force=True) or {}

    conn = get_db()
    existente = conn.execute('SELECT id FROM midias WHERE id = ?', (midia_id,)).fetchone()
    if existente is None:
        conn.close()
        return jsonify({'erro': 'Mídia não encontrada'}), 404

    conn.execute('''
        UPDATE midias SET
            titulo = ?, tipo = ?, idioma = ?, status = ?, nota = ?,
            progresso = ?, capa_url = ?, repertorio = ?, tema_repertorio = ?,
            anotacoes = ?, data_inicio = ?, data_fim = ?
        WHERE id = ?
    ''', (
        dados.get('titulo', '').strip(),
        dados.get('tipo'),
        dados.get('idioma', '').strip(),
        dados.get('status'),
        dados.get('nota'),
        dados.get('progresso'),
        dados.get('capa_url'),
        1 if dados.get('repertorio') else 0,
        dados.get('tema_repertorio'),
        dados.get('anotacoes'),
        dados.get('data_inicio'),
        dados.get('data_fim'),
        midia_id,
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/midias/<int:midia_id>', methods=['DELETE'])
def deletar_midia(midia_id):
    conn = get_db()
    conn.execute('DELETE FROM midias WHERE id = ?', (midia_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# ATIVIDADES (sessões de imersão registradas para cada mídia)
# ---------------------------------------------------------------------------

@app.route('/api/midias/<int:midia_id>/atividades', methods=['POST'])
def registrar_atividade(midia_id):
    dados = request.get_json(force=True) or {}

    if not dados.get('data') or not dados.get('minutos'):
        return jsonify({'erro': 'Data e minutos são obrigatórios'}), 400

    conn = get_db()
    midia = conn.execute('SELECT id FROM midias WHERE id = ?', (midia_id,)).fetchone()
    if midia is None:
        conn.close()
        return jsonify({'erro': 'Mídia não encontrada'}), 404

    quantidade = dados.get('quantidade')
    quantidade = int(quantidade) if quantidade not in (None, '') else None

    cursor = conn.execute('''
        INSERT INTO atividades (midia_id, data, minutos, quantidade, observacao)
        VALUES (?, ?, ?, ?, ?)
    ''', (midia_id, dados['data'], int(dados['minutos']), quantidade, dados.get('observacao')))
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return jsonify({'id': novo_id}), 201


@app.route('/api/atividades/<int:atividade_id>', methods=['DELETE'])
def deletar_atividade(atividade_id):
    conn = get_db()
    conn.execute('DELETE FROM atividades WHERE id = ?', (atividade_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# ESTATÍSTICAS (usadas no Painel / Dashboard)
# ---------------------------------------------------------------------------

# Cada tipo de mídia tem uma unidade de progresso diferente. Isso é usado
# tanto para o detalhamento por idioma quanto para o rótulo do campo
# "quantidade" na tela de registrar sessão.
TIPOS_EPISODIOS = ('Série', 'Anime')
TIPOS_PAGINAS = ('Livro', 'Mangá', 'HQ')
TIPOS_PALAVRAS = ('Novel',)


def _caso_sql(tipos):
    """Monta um trecho SQL tipo: CASE WHEN m.tipo IN ('Série','Anime') THEN a.quantidade ELSE 0 END"""
    lista = ','.join(f"'{t}'" for t in tipos)
    return f"COALESCE(SUM(CASE WHEN m.tipo IN ({lista}) THEN a.quantidade ELSE 0 END), 0)"


@app.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    conn = get_db()

    total_minutos = conn.execute(
        'SELECT COALESCE(SUM(minutos), 0) AS total FROM atividades'
    ).fetchone()['total']

    total_midias = conn.execute('SELECT COUNT(*) AS total FROM midias').fetchone()['total']

    total_concluidas = conn.execute(
        "SELECT COUNT(*) AS total FROM midias WHERE status = 'Concluído'"
    ).fetchone()['total']

    total_idiomas = conn.execute(
        'SELECT COUNT(DISTINCT idioma) AS total FROM midias'
    ).fetchone()['total']

    detalhamento_idioma = conn.execute(f'''
        SELECT
            m.idioma AS idioma,
            COALESCE(SUM(a.minutos), 0) AS minutos,
            COUNT(DISTINCT m.id) AS midias,
            {_caso_sql(TIPOS_EPISODIOS)} AS episodios,
            {_caso_sql(TIPOS_PAGINAS)} AS paginas,
            {_caso_sql(TIPOS_PALAVRAS)} AS palavras
        FROM midias m LEFT JOIN atividades a ON a.midia_id = m.id
        GROUP BY m.idioma
        ORDER BY minutos DESC
    ''').fetchall()

    por_tipo = conn.execute('''
        SELECT tipo, COUNT(*) AS total
        FROM midias
        GROUP BY tipo
        ORDER BY total DESC
    ''').fetchall()

    ultimos_dias = conn.execute('''
        SELECT data, COALESCE(SUM(minutos), 0) AS minutos
        FROM atividades
        WHERE date(data) >= date('now', '-6 days')
        GROUP BY data
        ORDER BY data ASC
    ''').fetchall()

    conn.close()

    detalhamento = [dict(r) for r in detalhamento_idioma]

    return jsonify({
        'total_minutos': total_minutos,
        'total_midias': total_midias,
        'total_concluidas': total_concluidas,
        'total_idiomas': total_idiomas,
        # "por_idioma" é mantido com esse nome por compatibilidade com o gráfico de horas
        'por_idioma': [{'idioma': d['idioma'], 'minutos': d['minutos']} for d in detalhamento],
        'detalhamento_idioma': detalhamento,
        'por_tipo': [dict(r) for r in por_tipo],
        'ultimos_dias': [dict(r) for r in ultimos_dias],
    })


@app.route('/api/atividades/heatmap', methods=['GET'])
def heatmap_atividades():
    """Retorna minutos totais por dia nos últimos N dias (padrão 365), para
    desenhar o mapa de calor de atividade no Painel."""
    dias = request.args.get('dias', default=365, type=int)
    conn = get_db()
    linhas = conn.execute('''
        SELECT data, COALESCE(SUM(minutos), 0) AS minutos
        FROM atividades
        WHERE date(data) >= date('now', ?)
        GROUP BY data
        ORDER BY data ASC
    ''', (f'-{dias} days',)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in linhas])


@app.route('/api/idiomas', methods=['GET'])
def listar_idiomas():
    """Retorna a lista de idiomas já usados, para preencher sugestões no formulário."""
    conn = get_db()
    linhas = conn.execute(
        'SELECT DISTINCT idioma FROM midias ORDER BY idioma'
    ).fetchall()
    conn.close()
    return jsonify([linha['idioma'] for linha in linhas])


# ---------------------------------------------------------------------------
# BUSCA AUTOMÁTICA DE METADADOS (capas, sinopses, ano...) EM APIS PÚBLICAS
# ---------------------------------------------------------------------------

@app.route('/api/buscar-metadados', methods=['GET'])
def buscar_metadados_rota():
    tipo = request.args.get('tipo', '')
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'erro': 'Digite algo para buscar'}), 400

    try:
        resultados = metadados.buscar(tipo, query)
        return jsonify(resultados)
    except ValueError as erro:
        return jsonify({'erro': str(erro)}), 400
    except metadados.requests.exceptions.RequestException as erro:
        return jsonify({'erro': f'Não consegui conectar ao serviço externo: {erro}'}), 502


# ---------------------------------------------------------------------------
# PERFIL DO USUÁRIO E FILMES FAVORITOS (TOP 4)
# ---------------------------------------------------------------------------

@app.route('/api/perfil', methods=['GET'])
def obter_perfil():
    """Retorna as informações do perfil do usuário e os detalhes dos seus 4 filmes favoritos."""
    conn = get_db()
    linha_perfil = conn.execute('SELECT * FROM perfil WHERE id = 1').fetchone()
    
    if not linha_perfil:
        # Se por algum motivo o perfil não existir, cria o registro padrão
        conn.execute('''
            INSERT INTO perfil (id, nome, localizacao, avatar_url, bio, links_sociais, seguidores, seguindo, badge_pro, badge_patron, top4_midias)
            VALUES (1, 'Viajante Cultural', 'São Paulo, Brasil', '',
                    'Explorando o mundo através do cinema, leitura e imersão cultural.',
                    '{"letterboxd": "https://letterboxd.com", "github": "https://github.com", "instagram": "https://instagram.com"}',
                    128, 45, 1, 1, '[]')
        ''')
        conn.commit()
        linha_perfil = conn.execute('SELECT * FROM perfil WHERE id = 1').fetchone()
        
    perfil = dict(linha_perfil)
    
    # Processa os links de redes sociais salvos em JSON
    try:
        perfil['links_sociais'] = json.loads(perfil['links_sociais']) if perfil.get('links_sociais') else {}
    except Exception:
        perfil['links_sociais'] = {}
        
    # Processa a lista de IDs ou objetos do Top 4 Filmes
    try:
        top4_ids = json.loads(perfil['top4_midias']) if perfil.get('top4_midias') else []
    except Exception:
        top4_ids = []

    # Busca no banco as mídias selecionadas para o Top 4
    top4_detalhados = []
    for item in top4_ids:
        if isinstance(item, int):
            # Se for ID, consulta na tabela de mídias
            midia = conn.execute('SELECT id, titulo, capa_url, tipo, status, nota FROM midias WHERE id = ?', (item,)).fetchone()
            if midia:
                top4_detalhados.append(dict(midia))
            else:
                top4_detalhados.append(None)
        elif isinstance(item, dict):
            # Se for um objeto customizado
            top4_detalhados.append(item)
        else:
            top4_detalhados.append(None)

    conn.close()
    perfil['top4_detalhados'] = top4_detalhados
    return jsonify(perfil)


@app.route('/api/perfil', methods=['PUT'])
def atualizar_perfil():
    """Atualiza as informações de perfil, biografia, redes sociais e favoritos."""
    dados = request.get_json(force=True) or {}
    
    conn = get_db()
    
    links = dados.get('links_sociais', {})
    links_json = json.dumps(links, ensure_ascii=False) if isinstance(links, dict) else str(links)
    
    top4 = dados.get('top4_midias', [])
    top4_json = json.dumps(top4, ensure_ascii=False) if isinstance(top4, (list, dict)) else str(top4)

    conn.execute('''
        UPDATE perfil SET
            nome = ?,
            localizacao = ?,
            avatar_url = ?,
            bio = ?,
            links_sociais = ?,
            seguidores = ?,
            seguindo = ?,
            badge_pro = ?,
            badge_patron = ?,
            top4_midias = ?
        WHERE id = 1
    ''', (
        dados.get('nome', 'Viajante Cultural').strip(),
        dados.get('localizacao', '').strip(),
        dados.get('avatar_url', '').strip(),
        dados.get('bio', '').strip(),
        links_json,
        int(dados.get('seguidores', 0)),
        int(dados.get('seguindo', 0)),
        1 if dados.get('badge_pro') else 0,
        1 if dados.get('badge_patron') else 0,
        top4_json
    ))
    
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/perfil/conexoes', methods=['GET'])
def obter_conexoes():
    """Retorna a lista de conexões (seguidores/seguindo) para exibição no atalho."""
    seguidores = [
        {"nome": "Sofia Chen", "user": "@sofiachen", "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80", "bio": "Cineasta & estudante de Mandarim", "seguindo": True},
        {"nome": "Lucas Vance", "user": "@lucasvance", "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80", "bio": "Fã de animes & literatura japonesa", "seguindo": True},
        {"nome": "Amina Diop", "user": "@aminadiop", "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80", "bio": "Poliglota | 5 idiomas em aprendizado", "seguindo": False},
        {"nome": "Mateo Rossi", "user": "@mateorossi", "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80", "bio": "Amante do cinema clássico italiano", "seguindo": True},
        {"nome": "Elena Rostova", "user": "@elenarostova", "avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80", "bio": "Leitora compulsiva de novels e HQs", "seguindo": True}
    ]
    seguindo = [
        {"nome": "Sofia Chen", "user": "@sofiachen", "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80", "bio": "Cineasta & estudante de Mandarim", "seguindo": True},
        {"nome": "Lucas Vance", "user": "@lucasvance", "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80", "bio": "Fã de animes & literatura japonesa", "seguindo": True},
        {"nome": "Mateo Rossi", "user": "@mateorossi", "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80", "bio": "Amante do cinema clássico italiano", "seguindo": True},
        {"nome": "Elena Rostova", "user": "@elenarostova", "avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80", "bio": "Leitora compulsiva de novels e HQs", "seguindo": True}
    ]
    return jsonify({'seguidores': seguidores, 'seguindo': seguindo})


# ---------------------------------------------------------------------------
# BACKUP (exportar / importar tudo em um único arquivo JSON)
# ---------------------------------------------------------------------------

def _gerar_backup_json():
    """Monta uma string JSON com tudo que está no banco (mídias, atividades e perfil)."""
    conn = get_db()
    midias = [dict(r) for r in conn.execute('SELECT * FROM midias').fetchall()]
    atividades = [dict(r) for r in conn.execute('SELECT * FROM atividades').fetchall()]
    perfil_row = conn.execute('SELECT * FROM perfil WHERE id = 1').fetchone()
    perfil = dict(perfil_row) if perfil_row else None
    conn.close()
    return json.dumps({'midias': midias, 'atividades': atividades, 'perfil': perfil}, ensure_ascii=False, indent=2)


def _restaurar_backup(dados):
    """Apaga os dados atuais e recarrega a partir de um dicionário."""
    midias = dados.get('midias', [])
    atividades = dados.get('atividades', [])
    perfil = dados.get('perfil')

    conn = get_db()
    conn.execute('DELETE FROM atividades')
    conn.execute('DELETE FROM midias')

    for m in midias:
        conn.execute('''
            INSERT INTO midias
                (id, titulo, tipo, idioma, status, nota, progresso, capa_url,
                 repertorio, tema_repertorio, anotacoes, data_criacao, data_inicio, data_fim)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            m.get('id'), m.get('titulo'), m.get('tipo'), m.get('idioma'), m.get('status'),
            m.get('nota'), m.get('progresso'), m.get('capa_url'), m.get('repertorio', 0),
            m.get('tema_repertorio'), m.get('anotacoes'), m.get('data_criacao'),
            m.get('data_inicio'), m.get('data_fim'),
        ))

    for a in atividades:
        conn.execute('''
            INSERT INTO atividades (id, midia_id, data, minutos, quantidade, observacao)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            a.get('id'), a.get('midia_id'), a.get('data'), a.get('minutos'),
            a.get('quantidade'), a.get('observacao'),
        ))

    if perfil:
        conn.execute('DELETE FROM perfil')
        conn.execute('''
            INSERT INTO perfil (id, nome, localizacao, avatar_url, bio, links_sociais, seguidores, seguindo, badge_pro, badge_patron, top4_midias)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            perfil.get('id', 1), perfil.get('nome'), perfil.get('localizacao'), perfil.get('avatar_url'),
            perfil.get('bio'), perfil.get('links_sociais'), perfil.get('seguidores', 0), perfil.get('seguindo', 0),
            perfil.get('badge_pro', 0), perfil.get('badge_patron', 0), perfil.get('top4_midias', '[]')
        ))

    conn.commit()
    conn.close()
    return len(midias), len(atividades)


@app.route('/api/backup/exportar', methods=['GET'])
def exportar_backup():
    payload = _gerar_backup_json()
    nome_arquivo = f"backup-passaporte-cultural-{datetime.now().strftime('%Y-%m-%d')}.json"
    return Response(
        payload,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={nome_arquivo}'}
    )


@app.route('/api/backup/importar', methods=['POST'])
def importar_backup():
    """Restaura um backup exportado anteriormente. Isso SUBSTITUI os dados atuais."""
    dados = request.get_json(force=True) or {}
    total_midias, total_atividades = _restaurar_backup(dados)
    return jsonify({
        'ok': True,
        'midias_importadas': total_midias,
        'atividades_importadas': total_atividades,
    })


# ---------------------------------------------------------------------------
# SINCRONIZAÇÃO COM GOOGLE DRIVE (opcional)
# ---------------------------------------------------------------------------
# Isso é opcional: se você não configurou o Google Drive (veja o README),
# essas rotas simplesmente respondem que não está configurado, e o resto
# do site continua funcionando normalmente com o backup local (.json).

@app.route('/api/drive/status', methods=['GET'])
def drive_status():
    return jsonify({'configurado': drive_sync.esta_configurado()})


@app.route('/api/drive/enviar', methods=['POST'])
def drive_enviar():
    try:
        conteudo = _gerar_backup_json()
        drive_sync.enviar_backup(conteudo)
        return jsonify({'ok': True})
    except RuntimeError as erro:
        return jsonify({'erro': str(erro)}), 400
    except Exception as erro:
        return jsonify({'erro': f'Erro ao enviar para o Google Drive: {erro}'}), 500


@app.route('/api/drive/baixar', methods=['POST'])
def drive_baixar():
    try:
        conteudo = drive_sync.baixar_backup()
        dados = json.loads(conteudo)
        total_midias, total_atividades = _restaurar_backup(dados)
        return jsonify({
            'ok': True,
            'midias_importadas': total_midias,
            'atividades_importadas': total_atividades,
        })
    except RuntimeError as erro:
        return jsonify({'erro': str(erro)}), 400
    except Exception as erro:
        return jsonify({'erro': f'Erro ao baixar do Google Drive: {erro}'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
