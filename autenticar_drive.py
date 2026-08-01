"""
autenticar_drive.py
--------------------
Rode este script UMA VEZ para conectar sua conta do Google Drive:

    python3 autenticar_drive.py

Isso abre uma aba no seu navegador pedindo login no Google e autorização
para o Passaporte Cultural criar/ler o arquivo de backup dele no seu
Drive (só esse arquivo — o escopo usado não enxerga o resto do seu Drive).

Pré-requisito: ter o arquivo client_secret.json nesta mesma pasta.
Veja o passo a passo para conseguir esse arquivo na seção "Google Drive"
do README.md (é grátis, leva uns 5 minutos na primeira vez).
"""

import os

from drive_sync import CLIENT_SECRET_PATH, TOKEN_PATH, SCOPES, BIBLIOTECAS_OK


def main():
    if not BIBLIOTECAS_OK:
        print('As bibliotecas do Google não estão instaladas.')
        print('Rode primeiro: pip install -r requirements.txt')
        return

    if not os.path.exists(CLIENT_SECRET_PATH):
        print('Não encontrei o arquivo client_secret.json nesta pasta.')
        print('Siga o passo a passo da seção "Google Drive" no README.md para gerá-lo (é grátis).')
        return

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, 'w') as arquivo:
        arquivo.write(creds.to_json())

    print()
    print('Conta do Google conectada com sucesso!')
    print('Agora os botões de Google Drive na aba Backup do site já funcionam.')


if __name__ == '__main__':
    main()
