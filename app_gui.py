#!/usr/bin/env python3
"""
app_gui.py - Interface gráfica para o Descompactador Google Drive no macOS.
Design moderno e nativo para macOS.
"""

import os
import sys
import time
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List

from core_unpacker import (
    UnpackEngine,
    UnpackProgress,
    natural_sort_key,
    detect_base_folder_name,
    scan_directory_for_zips,
    format_size
)

class DriveUnpackerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Descompactador Google Drive")
        self.root.geometry("720x620")
        self.root.minsize(640, 560)
        
        # Centraliza a janela na tela
        self.center_window(720, 620)
        
        # Variáveis de estado
        self.zip_files: List[str] = []
        self.dest_folder = tk.StringVar(value="")
        self.clean_macosx_var = tk.BooleanVar(value=True)
        self.open_finder_var = tk.BooleanVar(value=True)
        self.delete_source_var = tk.BooleanVar(value=False)
        
        self.is_running = False
        self.cancel_event = threading.Event()
        self.current_engine = None
        
        # Configuração de estilo ttk
        self.setup_styles()
        
        # Constrói os componentes da interface
        self.build_ui()
        
        # Tratamento para fechar a janela com segurança
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self, width: int, height: int):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, int((screen_width - width) / 2))
        y = max(0, int((screen_height - height) / 2) - 40)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_styles(self):
        style = ttk.Style()
        # Usa tema 'aqua' no Mac se disponível
        if "aqua" in style.theme_names():
            style.theme_use("aqua")
            
        style.configure("Title.TLabel", font=("SF Pro Display", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("SF Pro Text", 12), foreground="#666666")
        style.configure("Header.TLabel", font=("SF Pro Text", 12, "bold"))
        style.configure("Status.TLabel", font=("SF Pro Text", 11))
        style.configure("Accent.TButton", font=("SF Pro Text", 13, "bold"))
        style.configure("Card.TFrame", background="#f5f5f7")

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding="18 16 18 16")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- CABEÇALHO ---
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 12))
        
        title_lbl = ttk.Label(header_frame, text="📦 Descompactador Google Drive", style="Title.TLabel")
        title_lbl.pack(anchor="w")
        
        desc_lbl = ttk.Label(
            header_frame, 
            text="Mescla e descompacta arquivos particionados (ex: -001.zip, -002.zip) em uma única pasta.",
            style="Subtitle.TLabel"
        )
        desc_lbl.pack(anchor="w", pady=(2, 0))

        # --- SEÇÃO 1: SELEÇÃO DE ARQUIVOS ---
        files_group = ttk.LabelFrame(main_frame, text=" 1. Arquivos ZIP do Google Drive ", padding="12")
        files_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        btn_bar = ttk.Frame(files_group)
        btn_bar.pack(fill=tk.X, pady=(0, 8))
        
        self.btn_select_files = ttk.Button(btn_bar, text="📄 Selecionar Arquivos .zip...", command=self.select_files)
        self.btn_select_files.pack(side=tk.LEFT, padx=(0, 8))
        
        self.btn_select_folder = ttk.Button(btn_bar, text="📁 Selecionar Pasta com Zips...", command=self.select_folder)
        self.btn_select_folder.pack(side=tk.LEFT, padx=(0, 8))
        
        self.btn_clear = ttk.Button(btn_bar, text="Limpar Lista", command=self.clear_files)
        self.btn_clear.pack(side=tk.RIGHT)
        
        # Lista com barra de rolagem para ver os zips selecionados
        list_frame = ttk.Frame(files_group)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            list_frame,
            columns=("name", "size", "path"),
            show="headings",
            selectmode="extended",
            yscrollcommand=scrollbar.set,
            height=5
        )
        scrollbar.config(command=self.tree.yview)
        
        self.tree.heading("name", text="Nome do Arquivo ZIP", anchor="w")
        self.tree.heading("size", text="Tamanho", anchor="e")
        self.tree.heading("path", text="Localização", anchor="w")
        
        self.tree.column("name", width=220, minwidth=150)
        self.tree.column("size", width=85, minwidth=60, anchor="e")
        self.tree.column("path", width=340, minwidth=180)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Rodapé da lista de arquivos
        self.lbl_list_summary = ttk.Label(files_group, text="Nenhum arquivo selecionado.", foreground="#777777")
        self.lbl_list_summary.pack(anchor="w", pady=(6, 0))

        # --- SEÇÃO 2: DESTINO UNIFICADO ---
        dest_group = ttk.LabelFrame(main_frame, text=" 2. Pasta Raiz de Destino (Unificada) ", padding="12")
        dest_group.pack(fill=tk.X, pady=(0, 10))
        
        dest_input_frame = ttk.Frame(dest_group)
        dest_input_frame.pack(fill=tk.X)
        
        self.ent_dest = ttk.Entry(dest_input_frame, textvariable=self.dest_folder, font=("SF Pro Text", 11))
        self.ent_dest.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        self.btn_choose_dest = ttk.Button(dest_input_frame, text="Escolher...", command=self.choose_destination)
        self.btn_choose_dest.pack(side=tk.RIGHT)

        # --- SEÇÃO 3: OPÇÕES ---
        opts_frame = ttk.Frame(main_frame)
        opts_frame.pack(fill=tk.X, pady=(0, 10))
        
        chk_clean = ttk.Checkbutton(
            opts_frame, 
            text="Limpar arquivos desnecessários (__MACOSX, .DS_Store)", 
            variable=self.clean_macosx_var
        )
        chk_clean.pack(anchor="w")
        
        chk_finder = ttk.Checkbutton(
            opts_frame, 
            text="Abrir pasta no Finder ao terminar", 
            variable=self.open_finder_var
        )
        chk_finder.pack(anchor="w", pady=(2, 0))
        
        chk_delete = ttk.Checkbutton(
            opts_frame, 
            text="Excluir arquivos .zip originais após extração bem-sucedida (economiza espaço)", 
            variable=self.delete_source_var
        )
        chk_delete.pack(anchor="w", pady=(2, 0))

        # --- SEÇÃO 4: PROGRESSO E AÇÃO ---
        action_card = ttk.Frame(main_frame, padding="10")
        action_card.pack(fill=tk.X, pady=(0, 4))
        
        # Status text
        self.lbl_status = ttk.Label(action_card, text="Pronto para iniciar.", style="Status.TLabel")
        self.lbl_status.pack(anchor="w", pady=(0, 4))
        
        # Barra de progresso
        self.progress_bar = ttk.Progressbar(action_card, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))
        
        # Detalhes de velocidade e percentual
        self.lbl_details = ttk.Label(action_card, text="", foreground="#666666", font=("SF Pro Text", 10))
        self.lbl_details.pack(anchor="w", pady=(0, 8))
        
        # Botões de ação
        btn_action_box = ttk.Frame(action_card)
        btn_action_box.pack(fill=tk.X)
        
        self.btn_start = ttk.Button(
            btn_action_box, 
            text="🚀 Descompactar e Unificar Arquivos", 
            style="Accent.TButton",
            command=self.start_unpacking
        )
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        self.btn_cancel = ttk.Button(btn_action_box, text="Cancelar", command=self.cancel_unpacking, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.RIGHT)
        
        self.btn_open_folder = ttk.Button(btn_action_box, text="Abrir no Finder", command=self.open_destination_in_finder)
        # Oculto até concluir

    def select_files(self):
        selected = filedialog.askopenfilenames(
            title="Selecione os arquivos .zip do Google Drive",
            filetypes=[("Arquivos ZIP", "*.zip"), ("Todos os Arquivos", "*.*")]
        )
        if selected:
            self.add_zip_files(list(selected))

    def select_folder(self):
        folder = filedialog.askdirectory(title="Selecione a pasta que contém os arquivos .zip")
        if folder:
            zips = scan_directory_for_zips(folder)
            if not zips:
                messagebox.showwarning("Nenhum ZIP encontrado", "Nenhum arquivo .zip foi encontrado na pasta selecionada.")
                return
            self.add_zip_files(zips)

    def add_zip_files(self, paths: List[str]):
        new_set = set(self.zip_files)
        for p in paths:
            if p.lower().endswith(".zip") and os.path.isfile(p):
                new_set.add(os.path.abspath(p))
                
        self.zip_files = sorted(list(new_set), key=natural_sort_key)
        self.refresh_treeview()
        
        # Se o destino estiver em branco, sugere um caminho inteligente
        if not self.dest_folder.get() and self.zip_files:
            parent_dir = os.path.dirname(self.zip_files[0])
            base_name = detect_base_folder_name(self.zip_files)
            suggested = os.path.join(parent_dir, base_name)
            self.dest_folder.set(suggested)

    def clear_files(self):
        if self.is_running:
            return
        self.zip_files = []
        self.refresh_treeview()
        self.lbl_status.config(text="Pronto para iniciar.")
        self.lbl_details.config(text="")
        self.progress_bar["value"] = 0

    def refresh_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        total_size = 0
        for p in self.zip_files:
            size = os.path.getsize(p) if os.path.exists(p) else 0
            total_size += size
            name = os.path.basename(p)
            dir_name = os.path.dirname(p)
            self.tree.insert("", tk.END, values=(name, format_size(size), dir_name))
            
        count = len(self.zip_files)
        if count == 0:
            self.lbl_list_summary.config(text="Nenhum arquivo selecionado.")
        else:
            self.lbl_list_summary.config(
                text=f"{count} parte(s) selecionada(s) • Tamanho compactado: {format_size(total_size)}"
            )

    def choose_destination(self):
        initial = self.dest_folder.get()
        if not initial and self.zip_files:
            initial = os.path.dirname(self.zip_files[0])
            
        folder = filedialog.askdirectory(
            title="Escolha a pasta raiz de destino para descompactar",
            initialdir=initial or os.path.expanduser("~")
        )
        if folder:
            self.dest_folder.set(folder)

    def start_unpacking(self):
        if not self.zip_files:
            messagebox.showwarning("Atenção", "Por favor, selecione ao menos um arquivo .zip antes de iniciar.")
            return
            
        target = self.dest_folder.get().strip()
        if not target:
            messagebox.showwarning("Atenção", "Por favor, informe a pasta raiz de destino.")
            return
            
        # Aviso de segurança se marcou excluir zips
        if self.delete_source_var.get():
            confirm = messagebox.askyesno(
                "Confirmação de Exclusão",
                "Atenção: A opção de excluir os arquivos .zip originais após a extração está ativada.\n\n"
                "Os arquivos .zip selecionados serão apagados permanentemente após a descompactação bem-sucedida.\n\n"
                "Deseja continuar?",
                icon="warning"
            )
            if not confirm:
                return

        # Prepara UI para execução
        self.is_running = True
        self.cancel_event.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        self.btn_select_files.config(state=tk.DISABLED)
        self.btn_select_folder.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)
        self.btn_choose_dest.config(state=tk.DISABLED)
        self.ent_dest.config(state=tk.DISABLED)
        self.btn_open_folder.pack_forget()
        
        self.lbl_status.config(text="Calculando arquivos e preparando descompactação...")
        self.progress_bar["value"] = 0
        self.lbl_details.config(text="")

        # Inicia em thread separada
        threading.Thread(target=self._run_unpack_thread, daemon=True).start()

    def _progress_callback(self, progress: UnpackProgress):
        # Envia atualização para a thread principal do Tkinter
        self.root.after(0, self._update_progress_ui, progress)

    def _update_progress_ui(self, p: UnpackProgress):
        self.progress_bar["value"] = p.percent
        self.lbl_status.config(text=p.status_message)
        
        mb_extracted = p.bytes_extracted / (1024 * 1024)
        mb_total = p.total_bytes / (1024 * 1024)
        speed_mb = p.speed_bytes_sec / (1024 * 1024)
        
        file_info = f" • Arquivo atual: {p.current_file_name}" if p.current_file_name else ""
        self.lbl_details.config(
            text=f"{p.percent:.1f}% • {mb_extracted:.1f} MB de {mb_total:.1f} MB ({speed_mb:.1f} MB/s){file_info}"
        )

    def _run_unpack_thread(self):
        target = self.dest_folder.get().strip()
        self.current_engine = UnpackEngine(
            zip_files=self.zip_files,
            destination_dir=target,
            clean_macosx=self.clean_macosx_var.get(),
            overwrite_policy="overwrite_if_different",
            delete_zips_after=self.delete_source_var.get(),
            progress_callback=self._progress_callback,
            cancel_event=self.cancel_event
        )
        
        result = self.current_engine.run()
        self.root.after(0, self._on_unpack_finished, result)

    def _on_unpack_finished(self, result: dict):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.btn_select_files.config(state=tk.NORMAL)
        self.btn_select_folder.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)
        self.btn_choose_dest.config(state=tk.NORMAL)
        self.ent_dest.config(state=tk.NORMAL)
        
        if result["cancelled"]:
            self.lbl_status.config(text="Operação cancelada pelo usuário.")
            self.lbl_details.config(text=f"{result['files_extracted']} arquivos foram extraídos antes do cancelamento.")
            messagebox.showinfo("Cancelado", "A descompactação foi interrompida.")
            return

        dest = result.get("destination_dir", self.dest_folder.get())
        errors = result.get("errors", [])
        
        self.lbl_status.config(text="✅ Descompactação e unificação concluídas com sucesso!")
        self.lbl_details.config(
            text=f"{result['files_extracted']} arquivos combinados em {result['duration']:.1f}s • Pasta: {dest}"
        )
        self.progress_bar["value"] = 100
        
        # Mostra o botão "Abrir no Finder"
        self.btn_open_folder.pack(side=tk.RIGHT, padx=(8, 0))
        
        # Se solicitado abrir no finder automaticamente
        if self.open_finder_var.get():
            self.open_destination_in_finder()
            
        # Se arquivos de origem foram excluídos, atualiza lista
        if result.get("deleted_zips"):
            self.zip_files = [z for z in self.zip_files if z not in result["deleted_zips"]]
            self.refresh_treeview()
            
        if errors:
            err_msg = "\n".join(errors[:5])
            if len(errors) > 5:
                err_msg += f"\n...e mais {len(errors) - 5} aviso(s)."
            messagebox.showwarning("Concluído com avisos", f"Os arquivos foram descompactados, mas ocorreram alguns avisos:\n\n{err_msg}")
        else:
            messagebox.showinfo(
                "Sucesso!", 
                f"Todos os arquivos ({result['files_extracted']} itens) foram descompactados e unificados na pasta:\n\n{dest}"
            )

    def cancel_unpacking(self):
        if self.is_running and self.cancel_event:
            self.lbl_status.config(text="Cancelando operação...")
            self.cancel_event.set()

    def open_destination_in_finder(self):
        target = self.dest_folder.get().strip()
        if os.path.exists(target):
            subprocess.run(["open", target])
        else:
            messagebox.showwarning("Pasta não encontrada", f"A pasta '{target}' ainda não existe.")

    def on_closing(self):
        if self.is_running:
            if messagebox.askyesno("Sair", "Uma descompactação está em andamento. Deseja realmente cancelar e sair?"):
                self.cancel_event.set()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = DriveUnpackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
