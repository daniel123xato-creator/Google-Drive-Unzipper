#!/usr/bin/env python3
"""
core_unpacker.py - Motor de descompactação e unificação para Google Drive

Descompacta múltiplos arquivos ZIP (ex: Arquivo-001.zip, Arquivo-002.zip...)
em uma única pasta raiz compartilhada, unificando árvores de diretórios
e tratando conflitos de arquivos de forma segura.
"""

import os
import re
import sys
import time
import zipfile
import threading
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable

@dataclass
class UnpackProgress:
    current_zip_index: int
    total_zips: int
    current_zip_name: str
    current_file_name: str
    bytes_extracted: int
    total_bytes: int
    percent: float
    files_extracted_count: int
    speed_bytes_sec: float
    status_message: str


def natural_sort_key(s: str):
    """Ordenação natural para strings contendo números (ex: 001, 002, 010)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def is_drive_split_file(filename: str) -> bool:
    """Verifica se o nome de arquivo segue o padrão de partes do Drive/lotes."""
    name = os.path.basename(filename)
    return bool(re.search(r'[-_.](\d{3,4})\.zip$', name, re.IGNORECASE) or 
                name.lower().startswith("drive-download-"))


def detect_base_folder_name(zip_paths: List[str]) -> str:
    """
    Deduz um bom nome de pasta para a extração com base nos nomes dos arquivos.
    Ex: Arquivo-001.zip, Arquivo-002.zip -> Arquivo
    Ex: drive-download-20230910T123456Z-001.zip -> Download_Drive
    """
    if not zip_paths:
        return "Descompactado"
    
    names = [os.path.splitext(os.path.basename(p))[0] for p in zip_paths]
    
    # Remove sufixos como -001, _001, .001
    cleaned = [re.sub(r'[-_. ]0*(\d+)$', '', n, flags=re.IGNORECASE) for n in names]
    
    # Se todos têm o mesmo prefixo limpo
    if len(set(cleaned)) == 1 and cleaned[0]:
        base = cleaned[0]
        if base.lower().startswith("drive-download-"):
            return "Google_Drive_Arquivos"
        return base
    
    # Se só tem um arquivo
    if len(zip_paths) == 1:
        return cleaned[0] if cleaned[0] else "Descompactado"
        
    return "Arquivos_Combinados"


def scan_directory_for_zips(dir_path: str) -> List[str]:
    """Varre um diretório e retorna todos os arquivos .zip ordenados naturalmente."""
    if not os.path.isdir(dir_path):
        return []
    
    zips = []
    for item in os.listdir(dir_path):
        if item.lower().endswith(".zip") and not item.startswith("."):
            full_path = os.path.join(dir_path, item)
            if os.path.isfile(full_path):
                zips.append(full_path)
                
    zips.sort(key=natural_sort_key)
    return zips


class UnpackEngine:
    def __init__(
        self,
        zip_files: List[str],
        destination_dir: str,
        clean_macosx: bool = True,
        overwrite_policy: str = "overwrite_if_different", # 'skip', 'overwrite', 'overwrite_if_different', 'rename'
        delete_zips_after: bool = False,
        progress_callback: Optional[Callable[[UnpackProgress], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ):
        self.zip_files = sorted(zip_files, key=natural_sort_key)
        self.destination_dir = os.path.abspath(destination_dir)
        self.clean_macosx = clean_macosx
        self.overwrite_policy = overwrite_policy
        self.delete_zips_after = delete_zips_after
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event or threading.Event()
        
        self.total_uncompressed_bytes = 0
        self.extracted_bytes = 0
        self.files_extracted = 0
        self.errors = []
        self.start_time = 0.0

    def calculate_total_size(self) -> int:
        """Calcula o tamanho total descompactado de todos os zips válidos."""
        total = 0
        for zip_path in self.zip_files:
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    for info in zf.infolist():
                        if self.clean_macosx and (info.filename.startswith("__MACOSX/") or "/__MACOSX/" in info.filename or os.path.basename(info.filename) == ".DS_Store"):
                            continue
                        total += info.file_size
            except Exception as e:
                self.errors.append(f"Erro ao ler cabeçalho de {os.path.basename(zip_path)}: {e}")
        self.total_uncompressed_bytes = total
        return total

    def _resolve_unique_path(self, target_path: str) -> str:
        """Gera um nome único caso o arquivo já exista (ex: foto (1).jpg)."""
        if not os.path.exists(target_path):
            return target_path
        
        dir_name, file_name = os.path.split(target_path)
        base, ext = os.path.splitext(file_name)
        counter = 1
        while True:
            candidate = os.path.join(dir_name, f"{base} ({counter}){ext}")
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    def run(self) -> Dict:
        """Executa a descompactação e merge de todos os zips na pasta raiz."""
        self.start_time = time.time()
        self.calculate_total_size()
        os.makedirs(self.destination_dir, exist_ok=True)
        
        last_progress_update = 0.0
        bytes_at_last_update = 0
        current_speed = 0.0
        
        successful_zips = []

        for z_idx, zip_path in enumerate(self.zip_files):
            if self.cancel_event.is_set():
                break
                
            zip_name = os.path.basename(zip_path)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    infolist = zf.infolist()
                    
                    for info in infolist:
                        if self.cancel_event.is_set():
                            break

                        # Ignora arquivos de metadados indesejados
                        norm_name = info.filename.replace('\\', '/')
                        if self.clean_macosx:
                            if norm_name.startswith("__MACOSX/") or "/__MACOSX/" in norm_name:
                                continue
                            if os.path.basename(norm_name) == ".DS_Store":
                                continue

                        # Proteção contra Zip Slip (Path Traversal)
                        dest_path = os.path.abspath(os.path.join(self.destination_dir, norm_name))
                        if not dest_path.startswith(self.destination_dir + os.sep) and dest_path != self.destination_dir:
                            self.errors.append(f"Caminho inseguro detectado e ignorado: {norm_name}")
                            continue

                        # Se for diretório
                        if info.is_dir() or norm_name.endswith('/'):
                            os.makedirs(dest_path, exist_ok=True)
                            continue

                        # Garante que a pasta pai existe
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                        # Tratamento de arquivo existente
                        if os.path.exists(dest_path):
                            if self.overwrite_policy == "skip":
                                self.extracted_bytes += info.file_size
                                continue
                            elif self.overwrite_policy == "overwrite_if_different":
                                if os.path.getsize(dest_path) == info.file_size:
                                    self.extracted_bytes += info.file_size
                                    continue
                            elif self.overwrite_policy == "rename":
                                dest_path = self._resolve_unique_path(dest_path)

                        # Extrai com streaming em blocos para atualizar barra de progresso suavemente
                        file_chunk_size = 1024 * 128 # 128 KB
                        with zf.open(info, 'r') as source_f, open(dest_path, 'wb') as target_f:
                            while True:
                                if self.cancel_event.is_set():
                                    break
                                chunk = source_f.read(file_chunk_size)
                                if not chunk:
                                    break
                                target_f.write(chunk)
                                self.extracted_bytes += len(chunk)

                                now = time.time()
                                if now - last_progress_update >= 0.08:
                                    elapsed = now - last_progress_update
                                    bytes_delta = self.extracted_bytes - bytes_at_last_update
                                    current_speed = (bytes_delta / elapsed) if elapsed > 0 else 0.0
                                    
                                    percent = (self.extracted_bytes / self.total_uncompressed_bytes * 100.0) if self.total_uncompressed_bytes > 0 else 0.0
                                    
                                    if self.progress_callback:
                                        self.progress_callback(UnpackProgress(
                                            current_zip_index=z_idx + 1,
                                            total_zips=len(self.zip_files),
                                            current_zip_name=zip_name,
                                            current_file_name=os.path.basename(norm_name),
                                            bytes_extracted=self.extracted_bytes,
                                            total_bytes=self.total_uncompressed_bytes,
                                            percent=min(100.0, percent),
                                            files_extracted_count=self.files_extracted,
                                            speed_bytes_sec=current_speed,
                                            status_message=f"Extraindo {zip_name} ({z_idx + 1}/{len(self.zip_files)})"
                                        ))
                                    last_progress_update = now
                                    bytes_at_last_update = self.extracted_bytes

                        # Preserva data de modificação se disponível
                        if hasattr(info, 'date_time') and info.date_time:
                            try:
                                dt = time.mktime(info.date_time + (0, 0, -1))
                                os.utime(dest_path, (dt, dt))
                            except Exception:
                                pass

                        self.files_extracted += 1

                if not self.cancel_event.is_set():
                    successful_zips.append(zip_path)

            except Exception as e:
                self.errors.append(f"Erro ao extrair {zip_name}: {e}")

        # Se cancelado pelo usuário
        if self.cancel_event.is_set():
            return {
                "cancelled": True,
                "files_extracted": self.files_extracted,
                "bytes_extracted": self.extracted_bytes,
                "errors": self.errors,
                "duration": time.time() - self.start_time
            }

        # Se solicitado excluir zips originais após extração com sucesso
        deleted_zips = []
        if self.delete_zips_after and len(successful_zips) == len(self.zip_files) and not self.errors:
            for zp in successful_zips:
                try:
                    os.remove(zp)
                    deleted_zips.append(zp)
                except Exception as e:
                    self.errors.append(f"Não foi possível remover arquivo original {os.path.basename(zp)}: {e}")

        total_duration = time.time() - self.start_time
        
        # Chamada final de progresso
        if self.progress_callback:
            self.progress_callback(UnpackProgress(
                current_zip_index=len(self.zip_files),
                total_zips=len(self.zip_files),
                current_zip_name="Concluído",
                current_file_name="",
                bytes_extracted=self.extracted_bytes,
                total_bytes=self.total_uncompressed_bytes,
                percent=100.0,
                files_extracted_count=self.files_extracted,
                speed_bytes_sec=0.0,
                status_message="Descompactação concluída com sucesso!"
            ))

        return {
            "cancelled": False,
            "files_extracted": self.files_extracted,
            "bytes_extracted": self.extracted_bytes,
            "duration": total_duration,
            "errors": self.errors,
            "destination_dir": self.destination_dir,
            "deleted_zips": deleted_zips,
            "zips_processed": len(successful_zips)
        }


def format_size(num_bytes: int) -> str:
    """Formata bytes para leitura humana (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Descompactador de lotes e divisões do Google Drive para uma única pasta.")
    parser.add_argument("inputs", nargs="+", help="Arquivos .zip ou pasta contendo arquivos .zip")
    parser.add_argument("-o", "--output", help="Pasta de destino raiz para a mesclagem dos arquivos", default=None)
    parser.add_argument("--delete-source", action="store_true", help="Excluir os arquivos .zip de origem após extração")
    parser.add_argument("--keep-macosx", action="store_true", help="Não remover pastas __MACOSX ou .DS_Store")
    
    args = parser.parse_args()
    
    zip_list = []
    for inp in args.inputs:
        if os.path.isdir(inp):
            zip_list.extend(scan_directory_for_zips(inp))
        elif os.path.isfile(inp) and inp.lower().endswith(".zip"):
            zip_list.append(inp)
            
    if not zip_list:
        print("Nenhum arquivo .zip válido foi encontrado.", file=sys.stderr)
        sys.exit(1)
        
    dest = args.output
    if not dest:
        first_dir = os.path.dirname(os.path.abspath(zip_list[0]))
        base_name = detect_base_folder_name(zip_list)
        dest = os.path.join(first_dir, base_name)
        
    print(f"-> Arquivos a descompactar e combinar ({len(zip_list)} partes):")
    for z in zip_list:
        print(f"   - {os.path.basename(z)}")
    print(f"-> Destino unificado: {dest}\n")
    
    def print_progress(p: UnpackProgress):
        mb_extracted = p.bytes_extracted / (1024 * 1024)
        mb_total = p.total_bytes / (1024 * 1024)
        speed_mb = p.speed_bytes_sec / (1024 * 1024)
        sys.stdout.write(f"\r[{p.percent:5.1f}%] Parte {p.current_zip_index}/{p.total_zips} | {mb_extracted:.1f}/{mb_total:.1f} MB ({speed_mb:.1f} MB/s) - {p.current_file_name[:25]:<25}")
        sys.stdout.flush()

    engine = UnpackEngine(
        zip_files=zip_list,
        destination_dir=dest,
        clean_macosx=not args.keep_macosx,
        delete_zips_after=args.delete_source,
        progress_callback=print_progress
    )
    
    result = engine.run()
    print("\n")
    if result["cancelled"]:
        print("Operação cancelada pelo usuário.")
    else:
        print(f"Sucesso! {result['files_extracted']} arquivos combinados em '{dest}' em {result['duration']:.1f}s.")
        if result["errors"]:
            print("Avisos/Erros:")
            for err in result["errors"]:
                print(f" - {err}")
