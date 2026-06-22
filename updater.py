"""
updater.py — Auto-update via GitHub Releases
Verifica e baixa novas versões do Monte Azul Automation.
"""

import os
import sys
import json
import threading
import tempfile
import subprocess
import ssl
import urllib.request

try:
    from packaging.version import Version
except ImportError:
    Version = None

# ─── Certificados SSL ───────────────────────────────────────────────────────

def _get_ssl_context():
    """Cria contexto SSL usando certifi (funciona em exe empacotado)."""
    try:
        if getattr(sys, "frozen", False):
            # App empacotado pelo PyInstaller
            ca_path = os.path.join(sys._MEIPASS, "certifi", "cacert.pem")
        else:
            import certifi
            ca_path = certifi.where()
        return ssl.create_default_context(cafile=ca_path)
    except Exception:
        return ssl.create_default_context()

# ─── Constantes ─────────────────────────────────────────────────────────────

try:
    from version import APP_VERSION, GITHUB_REPO
except ImportError:
    APP_VERSION = "0.0.0"
    GITHUB_REPO = "nycolasmello/automacao-bots-monteazul"

_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_HEADERS = {"User-Agent": "MonteAzul-Automation-Updater/1.0"}

# ─── Lógica de verificação ──────────────────────────────────────────────────

def _get_latest_release():
    """
    Consulta a API do GitHub e retorna (version_str, download_url, changelog).
    Lança exceção em caso de falha de rede.
    """
    ctx = _get_ssl_context()
    req = urllib.request.Request(_API_URL, headers=_HEADERS)

    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tag = data.get("tag_name", "").lstrip("v")
    changelog = (data.get("body") or "").strip() or "Sem notas de versão."

    # Procura o primeiro asset .exe
    download_url = None
    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(".exe"):
            download_url = asset["browser_download_url"]
            break

    return tag, download_url, changelog


def _is_newer(latest_str: str) -> bool:
    """Retorna True se a versão do release for maior que APP_VERSION."""
    try:
        if Version:
            return Version(latest_str) > Version(APP_VERSION)
        # Fallback: comparação simples de string de versão
        return latest_str != APP_VERSION
    except Exception:
        return False


def check_for_updates(callback):
    """
    Verifica atualizações em background sem travar a UI.

    Parâmetros:
        callback(version, url, changelog)  — chamado quando há nova versão
        callback(None, None, None)         — chamado se já está atualizado ou erro
    """
    def _run():
        try:
            version, url, changelog = _get_latest_release()
            if _is_newer(version) and url:
                callback(version, url, changelog)
            else:
                callback(None, None, None)
        except Exception:
            callback(None, None, None)

    threading.Thread(target=_run, daemon=True).start()


# ─── Download e instalação ──────────────────────────────────────────────────

def download_and_install(download_url: str, progress_callback=None):
    """
    Baixa o novo .exe e o substitui usando um script .bat temporário.
    O processo atual será encerrado após iniciar o script de atualização.

    Parâmetros:
        download_url      — URL do asset no GitHub Release
        progress_callback — função(int) recebe 0–100 com o progresso do download
    """
    # Resolve o caminho do executável atual
    if getattr(sys, "frozen", False):
        current_exe = os.path.abspath(sys.executable)
    else:
        current_exe = os.path.abspath(sys.argv[0])

    # Diretório temporário para o download
    tmp_dir = tempfile.mkdtemp(prefix="monteazul_upd_")
    new_exe = os.path.join(tmp_dir, "MonteAzul-Automation.exe")

    # Baixa o arquivo com progresso
    ctx = _get_ssl_context()
    req = urllib.request.Request(download_url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        chunk_size = 65536  # 64 KB por chunk

        with open(new_exe, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    pct = min(100, int(downloaded * 100 / total))
                    progress_callback(pct)

    if progress_callback:
        progress_callback(100)

    # Cria o script .bat que faz a substituição após o app fechar
    bat_path = os.path.join(tmp_dir, "do_update.bat")
    bat_lines = [
        "@echo off",
        "ping 127.0.0.1 -n 3 >nul",                      # aguarda 2 s
        f'copy /Y "{new_exe}" "{current_exe}"',
        f'start "" "{current_exe}"',
        "exit",
    ]
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(bat_lines) + "\r\n")

    # Executa o script em background e sai
    subprocess.Popen(
        bat_path,
        shell=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
