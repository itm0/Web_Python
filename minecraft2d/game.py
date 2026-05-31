from datetime import datetime, timedelta

import os

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory
from flask_login import current_user, login_required

from game_data import BUILDINGS


game_bp = Blueprint("game", __name__)
# Estes valores controlam a jogabilidade no browser.
# Alguns deles são extensão do que foi visto na matéria, porque adicionam ciclos de recursos e ações assíncronas.
RESOURCE_RESPAWN_SECONDS = 10
RESOURCE_MAX_AMOUNT = 64
TREE_WOOD_YIELD = 4
STONE_STONE_YIELD = 2


def get_db():
    # A app guarda a base de dados em app.config["db"], seguindo a organização que já foi ajustada.
    return current_app.config["db"]


def clamp_resource_amount(value):
    # Garante que os recursos não passam do máximo permitido no jogo.
    return min(value, RESOURCE_MAX_AMOUNT)


def sync_slot(slot):
    # Função de sincronização "on demand": o servidor verifica o tempo quando a página é aberta.
    # Isto é um pouco fora da matéria porque usa timestamps para completar tarefas sem worker/cron.
    database = get_db()
    now = datetime.utcnow()
    if slot.ready_at is None:
        return

    if slot.state == "building" and now >= slot.ready_at:
        slot.state = "ready"
        slot.started_at = None
        slot.ready_at = None
        database.update_slot(slot)
        database.add_action_log(slot.user_id, f"A construção no slot {slot.slot_number} terminou.")
    elif slot.state == "working" and now >= slot.ready_at:
        slot.state = "collectable"
        slot.started_at = None
        slot.ready_at = None
        database.update_slot(slot)
        database.add_action_log(slot.user_id, f"A tarefa no slot {slot.slot_number} terminou. Podes recolher a recompensa.")


def ensure_state(user):
    # Atualiza todos os slots do utilizador e normaliza recursos antes de renderizar a vista.
    database = get_db()
    for slot in database.list_user_slots(user.id):
        sync_slot(slot)

    user.wood = clamp_resource_amount(user.wood)
    user.stone = clamp_resource_amount(user.stone)
    database.update_user_resources(user)


def slot_payload(slot):
    # Converte um slot para JSON para o frontend saber como o mostrar.
    building = BUILDINGS.get(slot.building_type) if slot.building_type else None
    return {
        "id": slot.id,
        "slot_number": slot.slot_number,
        "building_type": slot.building_type,
        "building_name": building["name"] if building else None,
        "state": slot.state,
        "action_type": slot.action_type,
        "started_at": slot.started_at.isoformat() if slot.started_at else None,
        "ready_at": slot.ready_at.isoformat() if slot.ready_at else None,
        "construction_seconds": building["construction_seconds"] if building else None,
        "task_seconds": building["task_seconds"] if building else None,
        "description": building["description"] if building else None,
    }


@game_bp.route("/")
@game_bp.route("/dashboard")
@login_required
def dashboard():
    # Página principal do jogo, equivalente à view do exemplo da matéria.
    ensure_state(current_user)
    return render_template("dashboard.html", buildings=BUILDINGS)


@game_bp.route("/api/state")
@login_required
def api_state():
    # Endpoint JSON que alimenta o frontend com o estado completo do jogo.
    # Isto vai além do básico da matéria porque junta vários conjuntos de dados numa resposta.
    database = get_db()
    ensure_state(current_user)
    logs = database.list_action_logs(current_user.id, limit=8)
    database.ensure_trees()
    database.ensure_stones()

    now = datetime.utcnow()
    trees = []
    for tree in database.list_trees():
        # Árvores com cooldown: se foram cortadas recentemente, ainda não podem ser usadas.
        available = True
        seconds_left = 0
        if tree.chopped_at:
            elapsed = (now - tree.chopped_at).total_seconds()
            if elapsed < RESOURCE_RESPAWN_SECONDS:
                available = False
                seconds_left = int(RESOURCE_RESPAWN_SECONDS - elapsed)
            else:
                tree.chopped_at = None
                database.update_tree(tree)
        trees.append(
            {
                "column": tree.column,
                "available": available,
                "seconds_left": seconds_left,
            }
        )

    stones = []
    for stone in database.list_stones():
        # O mesmo padrão é usado para as pedras.
        available = True
        seconds_left = 0
        if stone.mined_at:
            elapsed = (now - stone.mined_at).total_seconds()
            if elapsed < RESOURCE_RESPAWN_SECONDS:
                available = False
                seconds_left = int(RESOURCE_RESPAWN_SECONDS - elapsed)
            else:
                stone.mined_at = None
                database.update_stone(stone)
        stones.append(
            {
                "column": stone.column,
                "available": available,
                "seconds_left": seconds_left,
            }
        )

    return jsonify(
        {
            "user": {
                "username": current_user.username,
                "wood": current_user.wood,
                "stone": current_user.stone,
            },
            "slots": [slot_payload(slot) for slot in database.list_user_slots(current_user.id)],
            "logs": [{"message": log.message, "created_at": log.created_at.isoformat()} for log in logs],
            "buildings": BUILDINGS,
            "trees": trees,
            "stones": stones,
        }
    )


@game_bp.route("/api/build/<int:slot_id>", methods=["POST"])
@login_required
def api_build(slot_id):
    # Inicia uma construção num slot vazio, consumindo recursos do jogador.
    database = get_db()
    slot = database.get_slot(slot_id, current_user.id)
    if slot is None:
        return jsonify({"ok": False, "message": "Slot inválido."}), 404

    ensure_state(current_user)

    payload = request.get_json(silent=True) or {}
    building_key = payload.get("building_key") if request.is_json else request.form.get("building_key")
    building = BUILDINGS.get(building_key)

    if building is None:
        return jsonify({"ok": False, "message": "Construção inválida."}), 400

    if slot.state != "empty":
        return jsonify({"ok": False, "message": "Esse slot já tem uma construção."}), 400

    if current_user.wood < building["cost_wood"] or current_user.stone < building["cost_stone"]:
        return jsonify({"ok": False, "message": "Recursos insuficientes."}), 400

    current_user.wood -= building["cost_wood"]
    current_user.stone -= building["cost_stone"]
    slot.building_type = building_key
    slot.state = "building"
    slot.action_type = None
    slot.started_at = datetime.utcnow()
    slot.ready_at = slot.started_at + timedelta(seconds=building["construction_seconds"])
    database.update_user_resources(current_user)
    database.update_slot(slot)
    database.add_action_log(current_user.id, f"Iniciada construção de {building['name']} no slot {slot.slot_number}.")
    return jsonify({"ok": True})


@game_bp.route("/api/task/<int:slot_id>/start", methods=["POST"])
@login_required
def api_task_start(slot_id):
    # Depois da construção estar pronta, esta rota inicia a tarefa do edifício.
    database = get_db()
    slot = database.get_slot(slot_id, current_user.id)
    if slot is None:
        return jsonify({"ok": False, "message": "Slot inválido."}), 404

    ensure_state(current_user)

    if slot.state != "ready" or slot.building_type is None:
        return jsonify({"ok": False, "message": "O slot ainda não está pronto para tarefa."}), 400

    building = BUILDINGS.get(slot.building_type)
    slot.state = "working"
    slot.action_type = building["task_name"]
    slot.started_at = datetime.utcnow()
    slot.ready_at = slot.started_at + timedelta(seconds=building["task_seconds"])
    database.update_slot(slot)
    database.add_action_log(current_user.id, f"Tarefa '{building['task_name']}' iniciada no slot {slot.slot_number}.")
    return jsonify({"ok": True})


@game_bp.route("/api/task/<int:slot_id>/collect", methods=["POST"])
@login_required
def api_task_collect(slot_id):
    # Recolhe a recompensa quando a tarefa já terminou.
    database = get_db()
    slot = database.get_slot(slot_id, current_user.id)
    if slot is None:
        return jsonify({"ok": False, "message": "Slot inválido."}), 404

    ensure_state(current_user)

    if slot.state != "collectable" or slot.building_type is None:
        return jsonify({"ok": False, "message": "Não há recompensa para recolher."}), 400

    building = BUILDINGS.get(slot.building_type)
    current_user.wood += building["reward_wood"]
    current_user.stone += building["reward_stone"]
    slot.state = "ready"
    slot.action_type = None
    database.update_user_resources(current_user)
    database.update_slot(slot)
    database.add_action_log(current_user.id, f"Recompensa recolhida do slot {slot.slot_number}.")
    return jsonify({"ok": True})


@game_bp.route("/api/chop", methods=["POST"])
@login_required
def api_chop():
    # Minerar árvores/pedra por AJAX é uma funcionalidade um pouco além da matéria, mas segue a mesma ideia de rota Flask + resposta JSON.
    database = get_db()
    data = request.get_json(silent=True) or {}
    column = data.get("column")
    wood_amount = TREE_WOOD_YIELD
    if column is None:
        return jsonify({"ok": False, "message": "Coluna inválida."}), 400

    tree = database.get_tree_by_column(int(column))
    if not tree:
        return jsonify({"ok": False, "message": "Árvore inexistente."}), 400

    now = datetime.utcnow()
    if tree.chopped_at:
        elapsed = (now - tree.chopped_at).total_seconds()
        if elapsed < RESOURCE_RESPAWN_SECONDS:
            return jsonify({"ok": False, "message": "Árvore ainda não regenerou."}), 400
        tree.chopped_at = None

    tree.chopped_at = now
    current_user.wood = clamp_resource_amount(current_user.wood + wood_amount)
    database.update_tree(tree)
    database.update_user_resources(current_user)
    database.add_action_log(current_user.id, f"Árvore cortada: +{min(wood_amount, RESOURCE_MAX_AMOUNT)} madeira.")
    return jsonify({"ok": True, "wood": current_user.wood, "respawn_seconds": RESOURCE_RESPAWN_SECONDS})


@game_bp.route("/api/mine-stone", methods=["POST"])
@login_required
def api_mine_stone():
    # Rota equivalente à de cortar árvores, mas para pedra.
    database = get_db()
    data = request.get_json(silent=True) or {}
    column = data.get("column")
    stone_amount = STONE_STONE_YIELD
    if column is None:
        return jsonify({"ok": False, "message": "Coluna inválida."}), 400

    stone = database.get_stone_by_column(int(column))
    if not stone:
        return jsonify({"ok": False, "message": "Pedra inexistente."}), 400

    now = datetime.utcnow()
    if stone.mined_at:
        elapsed = (now - stone.mined_at).total_seconds()
        if elapsed < RESOURCE_RESPAWN_SECONDS:
            return jsonify({"ok": False, "message": "Pedra ainda não regenerou."}), 400
        stone.mined_at = None

    stone.mined_at = now
    current_user.stone = clamp_resource_amount(current_user.stone + stone_amount)
    database.update_stone(stone)
    database.update_user_resources(current_user)
    database.add_action_log(current_user.id, f"Pedra minerada: +{min(stone_amount, RESOURCE_MAX_AMOUNT)} pedra.")
    return jsonify({"ok": True, "stone": current_user.stone, "respawn_seconds": RESOURCE_RESPAWN_SECONDS})


@game_bp.route("/api/inventory/remove", methods=["POST"])
@login_required
def api_inventory_remove():
    # Remove itens do inventário do utilizador.
    database = get_db()
    data = request.get_json(silent=True) or {}
    resource = data.get("resource")
    amount = data.get("amount", 1)

    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Quantidade inválida."}), 400

    if resource not in {"wood", "stone"}:
        return jsonify({"ok": False, "message": "Recurso inválido."}), 400

    if amount <= 0:
        return jsonify({"ok": False, "message": "A quantidade tem de ser maior que zero."}), 400

    current_value = getattr(current_user, resource)
    if current_value < amount:
        return jsonify({"ok": False, "message": "Inventário insuficiente."}), 400

    setattr(current_user, resource, current_value - amount)
    label = "madeira" if resource == "wood" else "pedra"
    database.update_user_resources(current_user)
    database.add_action_log(current_user.id, f"{amount} {label} removida do inventário.")

    return jsonify({"ok": True, "wood": current_user.wood, "stone": current_user.stone})


def ensure_trees():
    # Garante que as árvores padrão existem na base de dados.
    get_db().ensure_trees()


def ensure_stones():
    # Garante que as pedras padrão existem na base de dados.
    get_db().ensure_stones()


@game_bp.route("/img/<path:filename>")
def image_file(filename):
    # Serve imagens estáticas do jogo sem passar pelo directório static padrão.
    image_folder = os.path.join(os.path.dirname(__file__), "img")
    return send_from_directory(image_folder, filename)
