#!/usr/bin/env python3
"""
create_distribution.py - Gera os pacotes oficiais de distribuição para Mac:
Cria o pacote ZIP (.zip) oficial preservando atributos e permissões Unix com 'ditto'.
"""

import os
import shutil
import subprocess

APP_NAME = "Descompactador Drive"
APP_BUNDLE = f"{APP_NAME}.app"
ZIP_NAME = "Descompactador-Drive-Mac.zip"
DIST_DIR = "dist"

def create_distribution():
    print("=== Criando Pacote de Distribuição para Mac ===")
    
    # 1. Garante que o .app está montado e atualizado
    subprocess.run(["python3", "build_app.py"], check=True)
    
    if not os.path.exists(APP_BUNDLE):
        print(f"Erro: {APP_BUNDLE} não encontrado!")
        return

    os.makedirs(DIST_DIR, exist_ok=True)
    zip_output = os.path.join(DIST_DIR, ZIP_NAME)
    
    if os.path.exists(zip_output):
        os.remove(zip_output)

    # Cria o arquivo ZIP preservando atributos e permissões Unix com 'ditto'
    print(f"\n-> Gerando pacote ZIP para distribuição: {zip_output}...")
    subprocess.run([
        "ditto", "-c", "-k", "--keepParent", "--sequesterRsrc",
        APP_BUNDLE,
        zip_output
    ], check=True)
    
    # Cria o guia de instruções para envio junto ao zip
    guide_path = os.path.join(DIST_DIR, "INSTRUCOES_DE_INSTALACAO.txt")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write("""COMO INSTALAR E ABRIR NO MAC:
==============================
1. Dê um duplo clique no arquivo 'Descompactador-Drive-Mac.zip' para extrair o aplicativo.
2. Arraste 'Descompactador Drive' para a sua pasta 'Aplicativos' (ou use direto de Downloads/Mesa).
3. Na PRIMEIRA vez que for abrir:
   - Clique no aplicativo com o BOTÃO DIREITO (ou segure Control e clique).
   - Escolha a opção 'Abrir'.
   - Na janela de segurança do macOS, clique em 'Abrir' novamente.
   
(A partir da segunda vez, basta dar dois cliques normalmente!).
""")

    print("   -> ZIP criado com sucesso!")
    print("\n" + "="*50)
    print("🎉 PACOTE PRONTO PARA DISTRIBUIÇÃO NA PASTA 'dist/':")
    print(f" 📦 Arquivo para envio: {os.path.abspath(zip_output)}")
    print(f" 📄 Instruções: {os.path.abspath(guide_path)}")
    print("="*50 + "\n")

if __name__ == "__main__":
    create_distribution()
