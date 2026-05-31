# Configurações centralizadas da aplicação. ✅ (Lab 07 — settings.py).
# Separar configurações do server.py facilita a manutenção e segurança.
import os

# Chave secreta usada pelo Flask para assinar cookies de sessão e CSRF.
# ✅ (Lab 07/08 — SECRET_KEY).
SECRET_KEY = "dev-minecraft-2d"

# Diretório base do projeto (a partir da localização deste ficheiro).
# ✅ (Lab 07 — os.path.dirname, os.path.abspath).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Caminho absoluto para o ficheiro SQLite dentro de models/.
# ❌ fora (Lab 07 guarda a BD na raiz, não em subpasta). Usado para organizar melhor o projeto.
DATABASE_PATH = os.path.join(BASE_DIR, "models", "minecraft2d.sqlite")
