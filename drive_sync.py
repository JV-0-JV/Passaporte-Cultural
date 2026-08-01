"""
drive_sync.py
-------------
Sincronização OPCIONAL do backup com o Google Drive.

Se você não configurou nada ainda (sem client_secret.json / token.json),
as funções aqui simplesmente avisam isso com uma mensagem clara — o
resto do site continua funcionando normalmente com o backup local
(exportar/importar .json manualmente).

Como configurar: siga o passo a passo na seção "Google Drive" do README.md.
Resumo:
  1. Criar um projeto gratuito no Google Cloud Console e ativar a Drive API.
  2. Criar uma credencial OAuth do tipo "App para computador" (Desktop app)
     e baixar o arquivo, salvando-o aqui como "client_secret.json".
  3. Rodar "python3 autenticar_drive.py" uma vez (abre o navegador para
     você fazer login e autorizar).
  4. Pronto — os botões de Google Drive na aba Backup passam a funcionar.

Usamos o escopo "drive.file", que só dá acesso a arquivos que o PRÓPRIO
app cria — ele nunca enxerga o resto do seu Google Drive.
"""

import io
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']
NOME_ARQUIVO_DRIVE = 'passaporte-cultural-backup.json'

PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(PASTA_ATUAL, 'token.json')
CLIENT_SECRET_PATH = os.path.join(PASTA_ATUAL, 'client_secret.json')

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
    BIBLIOTECAS_OK = True
except ImportError:
    BIBLIOTECAS_OK = False


def esta_configurado():
    """True se as bibliotecas do Google estão instaladas E o usuário já
    autenticou (rodou autenticar_drive.py com sucesso)."""
    return BIBLIOTECAS_OK and os.path.exists(TOKEN_PATH) and os.path.exists(CLIENT_SECRET_PATH)


def obter_credenciais():
    if not os.path.exists(TOKEN_PATH):
        return None

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, 'w') as arquivo:
            arquivo.write(creds.to_json())
    return creds


def obter_servico():
    if not BIBLIOTECAS_OK:
        raise RuntimeError(
            'As bibliotecas do Google não estão instaladas. Rode: pip install -r requirements.txt'
        )
    creds = obter_credenciais()
    if not creds:
        raise RuntimeError(
            'Google Drive ainda não conectado. Rode "python3 autenticar_drive.py" primeiro '
            '(veja o README, seção Google Drive).'
        )
    return build('drive', 'v3', credentials=creds)


def _encontrar_arquivo(servico):
    resposta = servico.files().list(
        q=f"name='{NOME_ARQUIVO_DRIVE}' and trashed=false",
        spaces='drive',
        fields='files(id, name, modifiedTime)',
    ).execute()
    arquivos = resposta.get('files', [])
    return arquivos[0] if arquivos else None


def enviar_backup(conteudo_json):
    """Envia (cria ou atualiza) o arquivo de backup no Google Drive."""
    servico = obter_servico()
    midia = MediaIoBaseUpload(
        io.BytesIO(conteudo_json.encode('utf-8')),
        mimetype='application/json',
        resumable=False,
    )
    existente = _encontrar_arquivo(servico)
    if existente:
        return servico.files().update(fileId=existente['id'], media_body=midia).execute()

    metadados_arquivo = {'name': NOME_ARQUIVO_DRIVE}
    return servico.files().create(body=metadados_arquivo, media_body=midia, fields='id').execute()


def baixar_backup():
    """Baixa o conteúdo do backup salvo no Google Drive e devolve como string JSON."""
    servico = obter_servico()
    existente = _encontrar_arquivo(servico)
    if not existente:
        raise RuntimeError('Nenhum backup encontrado no Google Drive ainda. Use "Enviar" primeiro.')

    solicitacao = servico.files().get_media(fileId=existente['id'])
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, solicitacao)
    concluido = False
    while not concluido:
        _, concluido = downloader.next_chunk()
    return buffer.getvalue().decode('utf-8')
