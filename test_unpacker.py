#!/usr/bin/env python3
"""
test_unpacker.py - Teste de validação para descompactação e merge do Google Drive
"""

import os
import shutil
import zipfile
import tempfile
from core_unpacker import UnpackEngine, scan_directory_for_zips, detect_base_folder_name

def run_test():
    temp_dir = tempfile.mkdtemp(prefix="drive_test_")
    output_dir = os.path.join(temp_dir, "resultado_combinado")
    
    try:
        print(f"Ambiente de teste temporário: {temp_dir}")
        
        # Cria 3 zips simulando Google Drive particionado
        zip1_path = os.path.join(temp_dir, "MeusArquivos-001.zip")
        zip2_path = os.path.join(temp_dir, "MeusArquivos-002.zip")
        zip3_path = os.path.join(temp_dir, "MeusArquivos-003.zip")
        
        with zipfile.ZipFile(zip1_path, 'w') as z1:
            z1.writestr("MeusArquivos/Fotos/viagem1.jpg", "conteudo foto 1")
            z1.writestr("MeusArquivos/Docs/guia.pdf", "conteudo pdf")
            z1.writestr("__MACOSX/MeusArquivos/Fotos/._viagem1.jpg", "lixo macosx")
            z1.writestr("MeusArquivos/.DS_Store", "lixo ds store")
            
        with zipfile.ZipFile(zip2_path, 'w') as z2:
            z2.writestr("MeusArquivos/Fotos/viagem2.jpg", "conteudo foto 2")
            z2.writestr("MeusArquivos/Docs/manual.txt", "conteudo manual")
            z2.writestr("__MACOSX/._lixo", "lixo macosx 2")
            
        with zipfile.ZipFile(zip3_path, 'w') as z3:
            z3.writestr("MeusArquivos/Fotos/viagem3.jpg", "conteudo foto 3")
            z3.writestr("MeusArquivos/Videos/intro.mp4", "conteudo video")
            z3.writestr("README.txt", "conteudo raiz")
            
        # Testa detecção de arquivos no diretório
        found_zips = scan_directory_for_zips(temp_dir)
        assert len(found_zips) == 3, f"Esperado 3 zips, encontrado {len(found_zips)}"
        print("[OK] scan_directory_for_zips encontrou as 3 partes ordenadas.")
        
        # Testa detecção do nome base da pasta
        base_name = detect_base_folder_name(found_zips)
        assert base_name == "MeusArquivos", f"Esperado 'MeusArquivos', obteve '{base_name}'"
        print(f"[OK] detect_base_folder_name identificou: '{base_name}'")
        
        # Executa a descompactação
        engine = UnpackEngine(
            zip_files=found_zips,
            destination_dir=output_dir,
            clean_macosx=True,
            overwrite_policy="overwrite_if_different"
        )
        result = engine.run()
        
        assert not result["cancelled"], "Operação não deveria estar cancelada"
        assert len(result["errors"]) == 0, f"Erros encontrados: {result['errors']}"
        print(f"[OK] Descompactação finalizada com {result['files_extracted']} arquivos.")
        
        # Verifica se todos os arquivos esperados foram combinados na MESMA pasta raiz
        expected_files = [
            os.path.join(output_dir, "MeusArquivos", "Fotos", "viagem1.jpg"),
            os.path.join(output_dir, "MeusArquivos", "Fotos", "viagem2.jpg"),
            os.path.join(output_dir, "MeusArquivos", "Fotos", "viagem3.jpg"),
            os.path.join(output_dir, "MeusArquivos", "Docs", "guia.pdf"),
            os.path.join(output_dir, "MeusArquivos", "Docs", "manual.txt"),
            os.path.join(output_dir, "MeusArquivos", "Videos", "intro.mp4"),
            os.path.join(output_dir, "README.txt")
        ]
        
        for ef in expected_files:
            assert os.path.exists(ef), f"Arquivo esperado não encontrado: {ef}"
            
        print("[OK] Todos os arquivos dos 3 zips foram unificados na mesma estrutura com sucesso!")
        
        # Verifica se metadados indesejados foram filtrados
        assert not os.path.exists(os.path.join(output_dir, "__MACOSX")), "Pasta __MACOSX não deveria ter sido extraída"
        assert not os.path.exists(os.path.join(output_dir, "MeusArquivos", ".DS_Store")), "Arquivo .DS_Store não deveria ter sido extraído"
        print("[OK] Lixo de sistema (__MACOSX e .DS_Store) foi filtrado perfeitamente.")
        
        print("\n--- TODOS OS TESTES PASSARAM COM SUCESSO! ---")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_test()
