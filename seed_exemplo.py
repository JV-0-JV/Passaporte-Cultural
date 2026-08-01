"""
seed_exemplo.py
----------------
Script opcional. Roda uma vez e preenche o banco com alguns exemplos,
só para você já ver o app funcionando (dashboard com gráficos, biblioteca
com cards, repertório com anotações) sem precisar cadastrar tudo na mão
antes de gravar a demonstração para a faculdade.

Como usar:
    python3 seed_exemplo.py

Se quiser recomeçar do zero, apague o arquivo data/imersao.db e rode
o script de novo (ou não rode, e comece com o banco vazio mesmo).
"""

from datetime import date, timedelta
from database import get_db, init_db

init_db()
conn = get_db()

conn.execute('DELETE FROM atividades')
conn.execute('DELETE FROM midias')

midias = [
    ('Kiki\'s Delivery Service', 'Filme', 'Japonês', 'Concluído', 5, None, None,
     1, 'meio ambiente e cidade', 'A relação entre Kiki e a cidade grande mostra a adaptação de jovens que saem do interior. Bom repertório para redações sobre êxodo rural e autonomia na juventude.'),
    ('The Witcher 3: Wild Hunt', 'Jogo', 'Inglês', 'Em andamento', None, 'Capítulo 2 - Velen', None,
     0, None, None),
    ('Extraordinary Attorney Woo', 'Série', 'Coreano', 'Em andamento', 4, 'Episódio 8', None,
     1, 'inclusão e capacitismo', 'A protagonista é uma advogada autista. Traz discussões sobre inclusão no mercado de trabalho e preconceito velado — ótimo repertório para temas sobre pessoas com deficiência.'),
    ('Cien años de soledad', 'Livro', 'Espanhol', 'Quero começar', None, None, None,
     0, None, None),
    ('Death Note', 'Mangá', 'Japonês', 'Concluído', 5, 'Volume 12 (completo)', None,
     1, 'justiça e vigilantismo', 'Discute os limites entre justiça e vingança, e o perigo de um poder absoluto sem controle social. Útil para temas sobre justiça, poder e ética.'),
]

ids = []
for m in midias:
    cur = conn.execute('''
        INSERT INTO midias (titulo, tipo, idioma, status, nota, progresso, capa_url,
                             repertorio, tema_repertorio, anotacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', m)
    ids.append(cur.lastrowid)

hoje = date.today()
atividades = [
    (ids[0], hoje - timedelta(days=6), 50, 'Assisti dublado com legenda em japonês'),
    (ids[1], hoje - timedelta(days=5), 40, None),
    (ids[2], hoje - timedelta(days=4), 35, 'Ep. 6 e 7'),
    (ids[1], hoje - timedelta(days=3), 60, None),
    (ids[4], hoje - timedelta(days=2), 25, None),
    (ids[2], hoje - timedelta(days=1), 30, 'Ep. 8'),
    (ids[1], hoje, 45, None),
]

for midia_id, data_atividade, minutos, obs in atividades:
    conn.execute('''
        INSERT INTO atividades (midia_id, data, minutos, observacao)
        VALUES (?, ?, ?, ?)
    ''', (midia_id, data_atividade.isoformat(), minutos, obs))

conn.commit()
conn.close()

print('Banco de dados populado com exemplos!')
print('Rode "python3 app.py" e acesse http://127.0.0.1:5000')
