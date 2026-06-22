import os
import re
import json
import shutil
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from version import APP_VERSION
import updater as _updater

# ─────────────────────────────────────────────
#  CAMINHOS PADRÃO DOS ARQUIVOS LUA
# ─────────────────────────────────────────────
BASE_LUA = r"z:\Base-MonteAzul\server-data\resources"

LUA_FILES = {
    "config_garage": {
        "path": os.path.join(BASE_LUA, r"[scripts]\skips_garagem\config\config_garage.lua"),
        "pattern": r"Config\.vehList\s*=\s*\{",
        "format": "\t{{ hash = GetHashKey(\"{spawn}\"), name = '{spawn}', price = {price}, banido = false, modelo = '{name}', capacidade = {capacity}, tipo = '{type}' }},"
    },
    "config_server": {
        "path": os.path.join(BASE_LUA, r"[scripts]\skips_inventario\server-side\Config_server.lua"),
        "pattern": r"vehList\s*=\s*\{",
        "format": "\t{{ hash = GetHashKey(\"{spawn}\"), name = \"{spawn}\", capacidade = {capacity} }},"
    },
    "basic_garage": {
        "path": os.path.join(BASE_LUA, r"[vrp]\vrp\client\basic_garage.lua"),
        "pattern": r"local\s+vehList\s*=\s*\{",
        "format": "\t{{ ['hash'] = GetHashKey(\"{spawn}\"), ['name'] = '{spawn}', ['banned'] = false }},"
    },
    "inventory": {
        "path": os.path.join(BASE_LUA, r"[vrp]\vrp\modules\inventory.lua"),
        "pattern": r"vehs\.vehglobal\s*=\s*\{",
        "format": "\t[\"{spawn}\"] = {{ ['name'] = \"{name}\", ['price'] = {price}, ['tipo'] = \"{type}\",  ['hash'] = GetHashKey(\"{spawn}\"), ['banned'] = false }},"
    }
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {
    "stream_path": r"Z:\Base-MonteAzul\server-data\resources\[veiculos]\monte_veiculos\stream",
    "data_path":   r"Z:\Base-MonteAzul\server-data\resources\[veiculos]\monte_veiculos\data",
}

# ─────────────────────────────────────────────
#  HELPERS DE LÓGICA
# ─────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def backup_file(filepath):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.{timestamp}.bak"
    try:
        shutil.copy2(filepath, backup_path)
        return True, backup_path
    except Exception as e:
        return False, str(e)


def append_to_table(filepath, table_start_pattern, content_to_append, spawn):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if f'"{spawn}"' in content or f"'{spawn}'" in content or f'GetHashKey("{spawn}")' in content:
            return "skip", f"Veículo '{spawn}' já existe em {os.path.basename(filepath)}"

        match = re.search(table_start_pattern, content)
        if not match:
            return "error", f"Tabela não encontrada em {os.path.basename(filepath)}"

        start_index = match.end()
        brace_count = 1
        i = start_index
        while i < len(content):
            if content[i] == "{":
                brace_count += 1
            elif content[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    break
            i += 1

        if brace_count != 0:
            return "error", f"Fim da tabela não encontrado em {os.path.basename(filepath)}"

        new_content = content[:i] + content_to_append + "\n" + content[i:]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        return "ok", os.path.basename(filepath)
    except Exception as e:
        return "error", str(e)


# ─────────────────────────────────────────────
#  CORES E ESTILOS
# ─────────────────────────────────────────────
BG       = "#1a1a2e"
SURFACE  = "#16213e"
CARD     = "#0f3460"
ACCENT   = "#e94560"
ACCENT2  = "#533483"
TEXT     = "#eaeaea"
TEXT_DIM = "#8892a4"
SUCCESS  = "#2ecc71"
WARNING  = "#f39c12"
ERROR    = "#e74c3c"
SKIP     = "#3498db"

FONT_TITLE  = ("Segoe UI", 18, "bold")
FONT_HEADER = ("Segoe UI", 11, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_MONO   = ("Consolas", 9)
FONT_BTN    = ("Segoe UI", 10, "bold")

# ─────────────────────────────────────────────
#  JANELA PRINCIPAL
# ─────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()

        self.title("Sistema de Veículos — Monte Azul")
        self.geometry("780x560")
        self.minsize(700, 480)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._center_window()
        self._build_ui()
        # Verifica atualizações silenciosamente após a UI estar pronta
        self.after(1500, self._check_updates)

    def _center_window(self):
        self.update_idletasks()
        w, h = 780, 560
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI ─────────────────────────────────────

    def _build_ui(self):
        # Topo / Header
        header = tk.Frame(self, bg=CARD, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._header = header  # referência para injetar botão de update depois

        tk.Label(header, text="🚗  Sistema de Veículos", font=FONT_TITLE,
                 bg=CARD, fg=TEXT).pack(side="left", padx=20, pady=10)
        tk.Label(header, text="Monte Azul FiveM", font=("Segoe UI", 9),
                 bg=CARD, fg=TEXT_DIM).pack(side="left", padx=0, pady=20)

        btn_cfg = tk.Button(header, text="⚙  Configurações", font=FONT_BTN,
                            bg=ACCENT2, fg=TEXT, relief="flat", cursor="hand2",
                            activebackground="#6a4aad", activeforeground=TEXT,
                            padx=12, pady=4, command=self._open_settings)
        btn_cfg.pack(side="right", padx=16, pady=14)

        # Corpo central
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Botão grande adicionar
        btn_frame = tk.Frame(body, bg=BG)
        btn_frame.pack(fill="x")

        self.btn_add = tk.Button(
            btn_frame,
            text="➕  Adicionar Carro",
            font=("Segoe UI", 13, "bold"),
            bg=ACCENT, fg="white",
            relief="flat", cursor="hand2",
            activebackground="#c0392b", activeforeground="white",
            padx=24, pady=12,
            command=self._on_add_car
        )
        self.btn_add.pack(side="left")

        self.status_lbl = tk.Label(btn_frame, text="Pronto.", font=FONT_BODY,
                                   bg=BG, fg=TEXT_DIM)
        self.status_lbl.pack(side="left", padx=20)

        # Separador
        tk.Frame(body, bg=SURFACE, height=2).pack(fill="x", pady=12)

        # Log
        log_header = tk.Frame(body, bg=BG)
        log_header.pack(fill="x")
        tk.Label(log_header, text="📋  Log de Operações", font=FONT_HEADER,
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Button(log_header, text="Limpar", font=("Segoe UI", 9),
                  bg=SURFACE, fg=TEXT_DIM, relief="flat", cursor="hand2",
                  padx=8, pady=2,
                  command=self._clear_log).pack(side="right")

        log_frame = tk.Frame(body, bg=SURFACE, relief="flat", bd=0)
        log_frame.pack(fill="both", expand=True, pady=(6, 0))

        self.log = tk.Text(
            log_frame, bg=SURFACE, fg=TEXT, font=FONT_MONO,
            relief="flat", bd=0, padx=10, pady=8,
            state="disabled", wrap="word",
            selectbackground=ACCENT2
        )
        self.log.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(log_frame, command=self.log.yview, bg=SURFACE, troughcolor=SURFACE)
        scroll.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scroll.set)

        # Tags de cor
        self.log.tag_configure("ok",      foreground=SUCCESS)
        self.log.tag_configure("error",   foreground=ERROR)
        self.log.tag_configure("warning", foreground=WARNING)
        self.log.tag_configure("skip",    foreground=SKIP)
        self.log.tag_configure("info",    foreground=TEXT_DIM)
        self.log.tag_configure("title",   foreground=ACCENT, font=("Consolas", 9, "bold"))

        # Status bar
        bar = tk.Frame(self, bg=SURFACE, height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Label(bar, text=f"Monte Azul Automation  •  v{APP_VERSION}", font=("Segoe UI", 8),
                 bg=SURFACE, fg=TEXT_DIM).pack(side="left", padx=10, pady=4)

        self._log_info("Sistema iniciado. Clique em '➕ Adicionar Carro' para começar.")

    # ── LOG ────────────────────────────────────

    def _log(self, msg, tag="info"):
        self.log.configure(state="normal")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        prefix_tag = tag
        self.log.insert("end", f"[{ts}] ", "info")
        self.log.insert("end", msg + "\n", prefix_tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log_ok(self, msg):      self._log("✔  " + msg, "ok")
    def _log_error(self, msg):   self._log("✘  " + msg, "error")
    def _log_warning(self, msg): self._log("⚠  " + msg, "warning")
    def _log_skip(self, msg):    self._log("→  " + msg, "skip")
    def _log_info(self, msg):    self._log("ℹ  " + msg, "info")
    def _log_title(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", "\n" + "─" * 50 + "\n", "info")
        self.log.insert("end", f"  {msg}\n", "title")
        self.log.insert("end", "─" * 50 + "\n", "info")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log_info("Log limpo.")

    # ── FLUXO PRINCIPAL ────────────────────────

    def _on_add_car(self):
        folder = filedialog.askdirectory(
            title="Selecione a pasta do veículo extraído"
        )
        if not folder:
            return

        folder = os.path.normpath(folder)

        # Detecta arquivos
        files_in_folder = os.listdir(folder)
        yft_files  = [f for f in files_in_folder if f.lower().endswith(".yft")]
        ytd_files  = [f for f in files_in_folder if f.lower().endswith(".ytd")]
        meta_files = [f for f in files_in_folder if f.lower().endswith(".meta")]

        if not yft_files:
            messagebox.showerror("Erro", "Nenhum arquivo .yft encontrado na pasta selecionada.")
            return

        # Resolve spawn name
        if len(yft_files) == 1:
            spawn_name = os.path.splitext(yft_files[0])[0]
        else:
            spawn_name = self._pick_spawn(yft_files)
            if not spawn_name:
                return

        # Abre modal de formulário
        self._open_form(folder, spawn_name, yft_files, ytd_files, meta_files)

    def _pick_spawn(self, yft_files):
        """Diálogo para escolher qual .yft usar como spawn name."""
        dialog = tk.Toplevel(self)
        dialog.title("Escolher Spawn Name")
        dialog.geometry("360x280")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self)
        _center_toplevel(dialog, self)

        tk.Label(dialog, text="Múltiplos .yft encontrados.\nEscolha o arquivo principal:",
                 font=FONT_BODY, bg=BG, fg=TEXT, justify="center").pack(pady=(20, 10))

        var = tk.StringVar(value=yft_files[0])
        for f in yft_files:
            rb = tk.Radiobutton(dialog, text=f, variable=var, value=f,
                                font=FONT_BODY, bg=BG, fg=TEXT,
                                selectcolor=CARD, activebackground=BG,
                                activeforeground=ACCENT)
            rb.pack(anchor="w", padx=40)

        result = [None]

        def confirm():
            result[0] = os.path.splitext(var.get())[0]
            dialog.destroy()

        tk.Button(dialog, text="Confirmar", font=FONT_BTN,
                  bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                  padx=20, pady=6, command=confirm).pack(pady=20)

        self.wait_window(dialog)
        return result[0]

    # ── FORMULÁRIO ─────────────────────────────

    def _open_form(self, folder, spawn_name, yft_files, ytd_files, meta_files):
        dlg = tk.Toplevel(self)
        dlg.title("Informações do Veículo")
        dlg.geometry("480x500")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)
        _center_toplevel(dlg, self)

        # Título
        tk.Frame(dlg, bg=CARD, height=48).pack(fill="x")
        hdr = dlg.children[list(dlg.children)[-1]]
        tk.Label(hdr, text="🚗  Novo Veículo", font=FONT_HEADER,
                 bg=CARD, fg=TEXT).place(x=16, y=12)

        content = tk.Frame(dlg, bg=BG)
        content.pack(fill="both", expand=True, padx=24, pady=16)

        def field(parent, label, row, default="", readonly=False):
            tk.Label(parent, text=label, font=("Segoe UI", 9, "bold"),
                     bg=BG, fg=TEXT_DIM).grid(row=row, column=0, sticky="w", pady=(8, 0))
            var = tk.StringVar(value=default)
            state = "readonly" if readonly else "normal"
            e = tk.Entry(parent, textvariable=var, font=FONT_BODY,
                         bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=ACCENT2, highlightcolor=ACCENT,
                         state=state)
            e.grid(row=row + 1, column=0, sticky="ew", ipady=6, pady=(2, 0))
            return var

        content.columnconfigure(0, weight=1)

        var_spawn    = field(content, "Nome de Spawn (detectado do .yft)", 0, default=spawn_name)
        var_name     = field(content, "Nome Exibido (ex: Eclipse Spyder)", 2)
        var_capacity = field(content, "Capacidade do Porta-malas (ex: 150)", 4, default="150")
        var_price    = field(content, "Preço (ex: 0 para VIP/Facção)", 6, default="0")

        # Tipo — dropdown
        tk.Label(content, text="Tipo do Veículo", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=TEXT_DIM).grid(row=8, column=0, sticky="w", pady=(8, 0))

        tipos = ["carros", "motos", "work", "barcos", "helicoptero", "avioes", "especial"]
        var_tipo = tk.StringVar(value=tipos[0])
        combo = ttk.Combobox(content, textvariable=var_tipo, values=tipos,
                             font=FONT_BODY, state="readonly")
        combo.grid(row=9, column=0, sticky="ew", ipady=4, pady=(2, 0))

        # Estilo do combobox
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=SURFACE, background=SURFACE,
                        foreground=TEXT, selectbackground=CARD,
                        arrowcolor=ACCENT)

        # Info arquivos detectados
        info_txt = f"📁  {len(yft_files)} .yft  |  {len(ytd_files)} .ytd  |  {len(meta_files)} .meta"
        tk.Label(content, text=info_txt, font=("Segoe UI", 8),
                 bg=BG, fg=TEXT_DIM).grid(row=10, column=0, sticky="w", pady=(12, 0))

        # Botões
        btn_row = tk.Frame(content, bg=BG)
        btn_row.grid(row=11, column=0, sticky="e", pady=(16, 0))

        def on_cancel():
            dlg.destroy()

        def on_confirm():
            spawn    = var_spawn.get().strip()
            name     = var_name.get().strip()
            cap_str  = var_capacity.get().strip()
            price_str = var_price.get().strip()
            tipo     = var_tipo.get().strip()

            # Validação
            if not spawn:
                messagebox.showerror("Erro", "Nome de spawn é obrigatório.", parent=dlg)
                return
            if not name:
                messagebox.showerror("Erro", "Nome exibido é obrigatório.", parent=dlg)
                return
            try:
                capacity = int(cap_str)
            except ValueError:
                messagebox.showerror("Erro", "Capacidade deve ser um número inteiro.", parent=dlg)
                return
            try:
                price = int(price_str)
            except ValueError:
                messagebox.showerror("Erro", "Preço deve ser um número inteiro.", parent=dlg)
                return

            dlg.destroy()
            self._run_automation(folder, spawn, name, capacity, price, tipo,
                                 yft_files, ytd_files, meta_files)

        tk.Button(btn_row, text="Cancelar", font=FONT_BTN,
                  bg=SURFACE, fg=TEXT_DIM, relief="flat", cursor="hand2",
                  padx=14, pady=6, command=on_cancel).pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="✔  Confirmar", font=FONT_BTN,
                  bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                  activebackground="#c0392b", activeforeground="white",
                  padx=14, pady=6, command=on_confirm).pack(side="left")

    # ── AUTOMAÇÃO ──────────────────────────────

    def _run_automation(self, folder, spawn, name, capacity, price, tipo,
                        yft_files, ytd_files, meta_files):
        self._log_title(f"Adicionando veículo: {spawn}")
        self.status_lbl.config(text=f"Processando {spawn}...", fg=WARNING)
        self.update_idletasks()

        cfg = self.config_data
        stream_root = cfg["stream_path"]
        data_root   = cfg["data_path"]

        errors = 0

        # ── 1. Copiar .yft e .ytd para stream ──
        stream_dest = os.path.join(stream_root, spawn)
        self._log_info(f"Criando pasta stream: {stream_dest}")
        try:
            os.makedirs(stream_dest, exist_ok=True)
            self._log_ok(f"Pasta criada: {stream_dest}")
        except Exception as e:
            self._log_error(f"Falha ao criar pasta stream: {e}")
            errors += 1

        for fname in yft_files + ytd_files:
            src = os.path.join(folder, fname)
            dst = os.path.join(stream_dest, fname)
            try:
                shutil.copy2(src, dst)
                self._log_ok(f"Copiado → stream\\{fname}")
            except Exception as e:
                self._log_error(f"Falha ao copiar {fname}: {e}")
                errors += 1

        # ── 2. Copiar .meta para data ──
        data_dest = os.path.join(data_root, spawn)
        self._log_info(f"Criando pasta data: {data_dest}")
        try:
            os.makedirs(data_dest, exist_ok=True)
            self._log_ok(f"Pasta criada: {data_dest}")
        except Exception as e:
            self._log_error(f"Falha ao criar pasta data: {e}")
            errors += 1

        if meta_files:
            for fname in meta_files:
                src = os.path.join(folder, fname)
                dst = os.path.join(data_dest, fname)
                try:
                    shutil.copy2(src, dst)
                    self._log_ok(f"Copiado → data\\{fname}")
                except Exception as e:
                    self._log_error(f"Falha ao copiar {fname}: {e}")
                    errors += 1
        else:
            self._log_warning("Nenhum arquivo .meta encontrado na pasta.")

        # ── 3. Inserir nos .lua ──
        self._log_info("Inserindo veículo nos arquivos .lua...")

        for key, info in LUA_FILES.items():
            filepath = info["path"]
            if not os.path.exists(filepath):
                self._log_error(f"Arquivo não encontrado: {os.path.basename(filepath)}")
                errors += 1
                continue

            ok, bak = backup_file(filepath)
            if not ok:
                self._log_error(f"Falha no backup de {os.path.basename(filepath)}: {bak}")
                errors += 1
                continue

            line = info["format"].format(
                spawn=spawn, name=name,
                capacity=capacity, price=price, type=tipo
            )

            status, msg = append_to_table(filepath, info["pattern"], line, spawn)
            if status == "ok":
                self._log_ok(f"Inserido em {msg}")
            elif status == "skip":
                self._log_skip(msg)
            else:
                self._log_error(msg)
                errors += 1

        # ── Resultado ──
        if errors == 0:
            self._log_ok(f"Veículo '{spawn}' adicionado com sucesso! 🎉")
            self.status_lbl.config(text=f"'{spawn}' adicionado com sucesso!", fg=SUCCESS)
            messagebox.showinfo("Sucesso",
                f"✔  Veículo '{name}' adicionado com sucesso!\n\nSpawn: {spawn}\nPreço: R$ {price:,}\nTipo: {tipo}")
        else:
            self._log_warning(f"Processo concluído com {errors} erro(s). Verifique o log.")
            self.status_lbl.config(text=f"Concluído com {errors} erro(s).", fg=WARNING)
            messagebox.showwarning("Atenção",
                f"Processo concluído com {errors} erro(s).\nVerifique o log para detalhes.")

    # ── AUTO-UPDATE ──────────────────────────────────────

    def _check_updates(self):
        """Inicia verificação de update em thread background."""
        _updater.check_for_updates(self._on_update_available)

    def _on_update_available(self, version, url, changelog):
        """Callback chamado pela thread de update (pode ser qualquer thread)."""
        if version:
            # Agenda execução na thread da UI via after()
            self.after(0, lambda: self._show_update_badge(version, url, changelog))

    def _show_update_badge(self, version, url, changelog):
        """Exibe botão verde de update no header."""
        UPDATE_BG  = "#1a7a50"
        UPDATE_HOV = "#156040"
        self._update_btn = tk.Button(
            self._header,
            text=f"🔄  v{version} disponível",
            font=FONT_BTN,
            bg=UPDATE_BG, fg="white",
            relief="flat", cursor="hand2",
            activebackground=UPDATE_HOV, activeforeground="white",
            padx=12, pady=4,
            command=lambda: self._confirm_update(version, url, changelog)
        )
        self._update_btn.pack(side="right", padx=(0, 8), pady=14)
        self._log_info(f"Nova versão disponível: v{version} — Clique no botão verde para atualizar.")

    def _confirm_update(self, version, url, changelog):
        """Diálogo de confirmação com changelog antes de baixar."""
        UPDATE_BG  = "#1a7a50"
        UPDATE_HOV = "#156040"

        dlg = tk.Toplevel(self)
        dlg.title("Atualização Disponível")
        dlg.geometry("480x340")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)
        _center_toplevel(dlg, self)

        hdr = tk.Frame(dlg, bg=UPDATE_BG, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"🔄  Atualização v{version}", font=FONT_HEADER,
                 bg=UPDATE_BG, fg="white").pack(side="left", padx=16, pady=12)

        content = tk.Frame(dlg, bg=BG)
        content.pack(fill="both", expand=True, padx=24, pady=16)

        tk.Label(content, text="O que há de novo:", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=TEXT_DIM).pack(anchor="w")

        txt = tk.Text(content, bg=SURFACE, fg=TEXT, font=FONT_MONO,
                      relief="flat", bd=0, padx=8, pady=6, height=8, wrap="word")
        txt.pack(fill="both", expand=True, pady=(4, 0))
        txt.insert("end", changelog)
        txt.configure(state="disabled")

        btn_row = tk.Frame(dlg, bg=BG)
        btn_row.pack(fill="x", padx=24, pady=(8, 16))

        tk.Button(btn_row, text="Agora não", font=FONT_BTN,
                  bg=SURFACE, fg=TEXT_DIM, relief="flat", cursor="hand2",
                  padx=14, pady=6, command=dlg.destroy).pack(side="left")

        def on_update():
            dlg.destroy()
            self._do_update(url, version)

        tk.Button(btn_row, text="✔  Atualizar Agora", font=FONT_BTN,
                  bg=UPDATE_BG, fg="white", relief="flat", cursor="hand2",
                  activebackground=UPDATE_HOV, activeforeground="white",
                  padx=14, pady=6, command=on_update).pack(side="right")

    def _do_update(self, url, version):
        """Baixa o exe novo e exibe barra de progresso, depois fecha o app."""
        prog_dlg = tk.Toplevel(self)
        prog_dlg.title("Baixando atualização...")
        prog_dlg.geometry("380x150")
        prog_dlg.configure(bg=BG)
        prog_dlg.resizable(False, False)
        prog_dlg.grab_set()
        prog_dlg.transient(self)
        _center_toplevel(prog_dlg, self)

        tk.Label(prog_dlg, text=f"Baixando v{version}...", font=FONT_HEADER,
                 bg=BG, fg=TEXT).pack(pady=(20, 8))

        progress_var = tk.IntVar(value=0)
        style = ttk.Style()
        style.configure("Green.Horizontal.TProgressbar",
                        troughcolor=SURFACE, background="#1a7a50", bordercolor=SURFACE)
        progress_bar = ttk.Progressbar(prog_dlg, variable=progress_var,
                                       maximum=100, length=320,
                                       style="Green.Horizontal.TProgressbar")
        progress_bar.pack(pady=4)

        pct_lbl = tk.Label(prog_dlg, text="0%", font=FONT_BODY, bg=BG, fg=TEXT_DIM)
        pct_lbl.pack()

        def progress_cb(pct):
            self.after(0, lambda: [
                progress_var.set(pct),
                pct_lbl.config(text=f"{pct}%")
            ])

        def run_download():
            try:
                _updater.download_and_install(url, progress_cb)
                # Fecha o app para o .bat substituir o exe
                self.after(500, self.destroy)
            except Exception as e:
                self.after(0, lambda err=e: [
                    prog_dlg.destroy(),
                    messagebox.showerror("Erro", f"Falha ao baixar atualização:\n{err}")
                ])

        threading.Thread(target=run_download, daemon=True).start()

    # ── CONFIGURAÇÕES ──────────────────────────

    def _open_settings(self):
        dlg = tk.Toplevel(self)
        dlg.title("Configurações de Caminhos")
        dlg.geometry("580x320")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)
        _center_toplevel(dlg, self)

        # Cabeçalho
        hdr = tk.Frame(dlg, bg=CARD, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Configurações de Caminhos", font=FONT_HEADER,
                 bg=CARD, fg=TEXT).pack(side="left", padx=16, pady=12)

        content = tk.Frame(dlg, bg=BG)
        content.pack(fill="both", expand=True, padx=24, pady=16)
        content.columnconfigure(0, weight=1)

        def path_field(parent, label, row, default):
            tk.Label(parent, text=label, font=("Segoe UI", 9, "bold"),
                     bg=BG, fg=TEXT_DIM).grid(row=row, column=0, columnspan=2,
                                               sticky="w", pady=(10, 0))
            var = tk.StringVar(value=default)
            e = tk.Entry(parent, textvariable=var, font=FONT_MONO,
                         bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=ACCENT2, highlightcolor=ACCENT)
            e.grid(row=row + 1, column=0, sticky="ew", ipady=6, pady=(2, 0), padx=(0, 6))

            def browse():
                p = filedialog.askdirectory(title=f"Selecionar: {label}", parent=dlg)
                if p:
                    var.set(os.path.normpath(p))

            tk.Button(parent, text="📂", font=FONT_BODY,
                      bg=SURFACE, fg=TEXT, relief="flat", cursor="hand2",
                      padx=6, pady=4, command=browse).grid(row=row + 1, column=1,
                                                            pady=(2, 0), sticky="e")
            return var

        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=0)

        cfg = self.config_data
        var_stream = path_field(content, "📁  Pasta Stream (.yft / .ytd)", 0, cfg["stream_path"])
        var_data   = path_field(content, "📁  Pasta Data (.meta)", 2, cfg["data_path"])

        # Botões
        btn_row = tk.Frame(content, bg=BG)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(24, 0))

        def on_save():
            self.config_data["stream_path"] = var_stream.get().strip()
            self.config_data["data_path"]   = var_data.get().strip()
            save_config(self.config_data)
            self._log_ok("Configurações salvas.")
            dlg.destroy()

        tk.Button(btn_row, text="Cancelar", font=FONT_BTN,
                  bg=SURFACE, fg=TEXT_DIM, relief="flat", cursor="hand2",
                  padx=14, pady=6, command=dlg.destroy).pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="💾  Salvar", font=FONT_BTN,
                  bg=ACCENT2, fg="white", relief="flat", cursor="hand2",
                  activebackground="#6a4aad", activeforeground="white",
                  padx=14, pady=6, command=on_save).pack(side="left")


# ─────────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────────

def _center_toplevel(win, parent):
    win.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_x()
    py = parent.winfo_y()
    ww = win.winfo_width()
    wh = win.winfo_height()
    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2
    win.geometry(f"+{x}+{y}")


# ─────────────────────────────────────────────
#  ENTRYPOINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
