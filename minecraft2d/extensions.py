# Flask-Login: gestor de sessões de autenticação. ✅ (Lab 08).
# Permite criar o objeto LoginManager antes da app existir (evita imports circulares).
from flask_login import LoginManager

# Instância global do LoginManager.
# ✅ (Lab 08 — LoginManager(), init_app()).
login_manager = LoginManager()

# Rota para redirecionar quando um user não autenticado tenta aceder a uma rota protegida.
# usa o prefixo "auth." porque a rota está no Blueprint auth.
# ✅ (Lab 08 — login_view).
login_manager.login_view = "auth.login"
