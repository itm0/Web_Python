  // O código só começa depois de a página carregar os elementos HTML.
function initGame() {
  // Guardamos referências aos elementos da interface para os atualizar depois.
  var steeve = document.getElementById('steeve');
  var sceneFrame = document.getElementById('scene-frame');
  var sceneGrid = document.getElementById('scene-grid');
  var inventoryMain = document.getElementById('inventory-main');
  var inventoryHotbar = document.getElementById('inventory-hotbar');
  var slotsGrid = document.getElementById('slots-grid');
  var logsList = document.getElementById('logs-list');
  var buildingButtons = document.getElementsByClassName('building-option');

  // Estas variáveis controlam o tamanho do mapa, a posição do jogador e o estado da interface.
  var tileSize = 96;
  var mapColumns = 12;
  var minimumColumns = 12;
  var mapRows = 2;
  var selectedBuildingKey = 'cabana';
  // A posição é guardada no navegador para não se perder quando a página recarrega.
  var steeveTile = parseInt(localStorage.getItem('steeve-tile'), 10) || 2;
  var walkLimit = mapColumns - 1;
  var latestStatePayload = null;
  // Guardamos os valores anteriores para perceber se o inventário mudou.
  var previousInventory = {
    wood: -1,
    stone: -1
  };

  // Esta função define o tamanho base dos tiles conforme o tamanho do ecrã.
  function getBaseTileSize() {
    if (window.innerWidth <= 720) {
      return 72;
    }

    return 96;
  }

  // Aqui adaptamos o mapa ao espaço disponível e evitamos que o jogador saia fora da área.
  function updateSceneMetrics() {
    var frameWidth = 0;
    var computedColumns = 0;

    if (!sceneFrame) {
      tileSize = getBaseTileSize();
      walkLimit = mapColumns - 1;
      return;
    }

    frameWidth = sceneFrame.clientWidth || sceneFrame.getBoundingClientRect().width || window.innerWidth;

    if (window.innerWidth <= 430) {
      // Mantém as colunas obrigatórias visíveis em ecrãs estreitos.
      var maxMin = frameWidth / minimumColumns;
      tileSize = maxMin > 32 ? maxMin : 32;
      tileSize = parseInt(tileSize, 10);
    } else {
      tileSize = getBaseTileSize();
    }

    computedColumns = parseInt(frameWidth / tileSize, 10);
    if (frameWidth % tileSize !== 0) { computedColumns = computedColumns + 1; }
    mapColumns = minimumColumns > computedColumns ? minimumColumns : computedColumns;
    walkLimit = mapColumns - 1;

    if (steeveTile > walkLimit) {
      steeveTile = walkLimit;
    }
  }

  // Desenha o cenário completo com tiles, pedras e posições.
  // Esta parte trata da interface do utilizador.
  function buildScene(stones) {
    var row;
    var column;
    var stoneByColumn = {};

    if (!sceneGrid) {
      return;
    }

    updateSceneMetrics();

    sceneGrid.innerHTML = '';

    for (var si = 0; si < (stones || []).length; si++) {
      var stone = (stones || [])[si];
      stoneByColumn[parseInt(stone.column, 10)] = stone;
    }

    for (row = 0; row < mapRows; row += 1) {
      for (column = 0; column < mapColumns; column += 1) {
        var tile = document.createElement('img');
        var isGrassRow = row === mapRows - 1;
        var isDirtRow = row === 0;
        var stone = isDirtRow ? stoneByColumn[column] : null;

        tile.className = 'scene-tile';
        tile.src = isGrassRow ? '/static/img/relva.png' : (stone && stone.available ? '/static/img/stone.png' : '/static/img/terra.png');
        tile.alt = isGrassRow ? 'Relva' : (stone && stone.available ? 'Pedra' : 'Terra');
        tile.setAttribute('data-col', '' + column);
        tile.style.left = (column * tileSize) + 'px';
        tile.style.bottom = (row * tileSize) + 'px';
        tile.style.width = tileSize + 'px';
        tile.style.height = tileSize + 'px';

        // Clique direto no tile para minerar pedra.
        if (stone && stone.available) {
          tile.className = 'scene-tile scene-stone';
          tile.style.zIndex = '2';
          tile.style.pointerEvents = 'auto';
          tile.setAttribute('draggable', 'false');
          tile.setAttribute('tabindex', '-1');

          tile.onclick = function (ev) {
            var clicked = ev.target;
            if (!clicked) return;
            var col = parseInt(clicked.getAttribute('data-col'), 10);

            if (clicked.getAttribute('data-mined')) return;

            if (!canInteractWithColumn(col)) {
              alert('Estás muito longe da pedra. Aproxima-te 1 tile.');
              return;
            }

            clicked.setAttribute('data-mined', '1');
            clicked.style.pointerEvents = 'none';

            requestJson('/api/mine-stone', { column: col })
              .then(function (payload) {
                if (!payload.ok) {
                  alert(payload.payload.message || 'Não foi possível minerar a pedra.');
                  clicked.setAttribute('data-mined', '');
                  clicked.style.pointerEvents = 'auto';
                  return;
                }

                clicked.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                clicked.style.opacity = '0.35';
                clicked.style.transform = 'translateY(-12px) scale(0.95)';

                setTimeout(function () {
                  refreshState();
                }, 250);
              }).catch(function () {
                alert('Erro de rede ao minerar a pedra.');
                clicked.setAttribute('data-mined', '');
                clicked.style.pointerEvents = 'auto';
              });
          };
        }

        // Contador visual por cima da pedra enquanto espera.
        if (stone && !stone.available) {
          var stoneBadge = document.createElement('div');
          stoneBadge.className = 'stone-timer-badge';
          stoneBadge.setAttribute('data-col', '' + column);
          stoneBadge.style.position = 'absolute';
          stoneBadge.style.left = (column * tileSize + 6) + 'px';
          stoneBadge.style.bottom = (row * tileSize + (tileSize * 0.9) + 2) + 'px';
          stoneBadge.style.zIndex = '3';
          stoneBadge.style.background = 'rgba(0,0,0,0.6)';
          stoneBadge.style.color = '#fff';
          stoneBadge.style.padding = '4px 6px';
          stoneBadge.style.borderRadius = '6px';
          stoneBadge.style.fontSize = '12px';
          stoneBadge.textContent = '' + (stone.seconds_left || 0);
          sceneGrid.appendChild(stoneBadge);
        }

        sceneGrid.appendChild(tile);

        // As árvores são desenhadas pela função renderTrees.
      }
    }
  }

  // Animação visual para remover elementos da interface.
  function deleteItem(element, options) {
    var node = element;
    var delay = 0;

    if (!node) {
      return;
    }

    options = options || {};
    delay = typeof options.delay === 'number' ? options.delay : 250;

    node.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
    node.style.opacity = '0';
    node.style.transform = 'scale(0.9)';

    setTimeout(function () {
      if (node.parentNode) {
        node.parentNode.removeChild(node);
      }
    }, delay);
  }

  // Posicionamento visual do personagem no mapa.
  function setSteevePosition() {
    if (!steeve) {
      return;
    }

    if (steeveTile < 0) {
      steeveTile = 0;
    }

    if (steeveTile > walkLimit) {
      steeveTile = walkLimit;
    }

    steeve.style.left = (steeveTile * tileSize) + 'px';
    steeve.style.bottom = ((tileSize * mapRows) - parseInt(tileSize / 12, 10)) + 'px';
    steeve.style.width = 'auto';
    steeve.style.height = (tileSize * 1.375) + 'px';
    localStorage.setItem('steeve-tile', '' + steeveTile);
  }

  // Movimento do personagem com base em teclas.
  function moveSteeve(direction) {
    steeveTile += direction;

    if (steeve) {
      if (direction < 0) {
        steeve.classList.add('facing-left');
      } else {
        steeve.classList.remove('facing-left');
      }
    }

    setSteevePosition();
  }

  // Devolve a coluna atual do jogador a partir do estado já guardado no JS.
  function getPlayerTile() {
    return steeveTile;
  }

  // Confirma se o jogador está perto o suficiente para interagir com uma coluna.
  function canInteractWithColumn(column) {
    var diff = getPlayerTile() - column;
    return (diff >= -1 && diff <= 1);
  }

  // Faz um pedido JSON ao servidor e devolve o resultado já organizado.
  function requestJson(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body || {})
    }).then(function (response) {
      return response.json().then(function (payload) {
        return { ok: response.ok, payload: payload };
      });
    });
  }

  // Traduz o estado interno do slot para texto legível na interface.
  function formatState(state) {
    if (state === 'building') {
      return 'A construir';
    }

    if (state === 'ready') {
      return 'Pronto';
    }

    if (state === 'working') {
      return 'A processar';
    }

    if (state === 'collectable') {
      return 'Concluída';
    }

    return 'Vazio';
  }

  // Painel visual com o histórico de ações.
  function renderLogs(logs) {
    if (!logsList) {
      return;
    }

    logsList.innerHTML = '';

    for (var li = 0; li < logs.length; li++) {
      var log = logs[li];
      var card = document.createElement('article');
      var message = document.createElement('p');
      var time = document.createElement('time');
      var d = new Date(log.created_at);
      var h = d.getHours();
      var m = d.getMinutes();

      card.className = 'log-card';
      message.textContent = log.message;
      time.textContent = (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;

      card.appendChild(message);
      card.appendChild(time);
      logsList.appendChild(card);
    }
  }

  // Interface dinâmica dos slots de construção.
  function renderSlots(slots, buildings) {
    if (!slotsGrid) {
      return;
    }

    slotsGrid.innerHTML = '';

    for (var sli = 0; sli < slots.length; sli++) {
      var slot = slots[sli];
      var building = slot.building_type ? buildings[slot.building_type] : null;
      var card = document.createElement('article');
      var header = document.createElement('div');
      var title = document.createElement('strong');
      var state = document.createElement('span');
      var meta = document.createElement('div');
      var actionBox = document.createElement('div');

      card.className = 'slot-card';
      card.setAttribute('data-slot-id', slot.id);

      header.className = 'slot-title';
      title.textContent = 'Slot ' + slot.slot_number;
      state.className = 'slot-state ' + slot.state;
      state.textContent = formatState(slot.state);

      header.appendChild(title);
      header.appendChild(state);
      card.appendChild(header);

      meta.className = 'slot-meta';
      meta.textContent = building ? building.name + ' · ' + building.description : 'Sem construção';
      card.appendChild(meta);

      actionBox.className = 'slot-actions';

      (function (slotId) {
        if (slot.state === 'empty') {
          var buildButton = document.createElement('button');
          buildButton.className = 'slot-action build';
          buildButton.textContent = 'Construir aqui';
          buildButton.onclick = function () {
            buildSlot(slotId);
          };
          actionBox.appendChild(buildButton);
        }

        if (slot.state === 'ready') {
          var taskButton = document.createElement('button');
          taskButton.className = 'slot-action task';
          taskButton.textContent = 'Iniciar tarefa';
          taskButton.onclick = function () {
            startTask(slotId);
          };
          actionBox.appendChild(taskButton);
        }

        if (slot.state === 'collectable') {
          var collectButton = document.createElement('button');
          collectButton.className = 'slot-action collect';
          collectButton.textContent = 'Recolher recompensa';
          collectButton.onclick = function () {
            collectTask(slotId);
          };
          actionBox.appendChild(collectButton);
        }
      })(slot.id);

      card.appendChild(actionBox);
      slotsGrid.appendChild(card);
    }
  }

  // Cria visualmente cada caixa do inventário.
  function createInventorySlot(item) {
    var slot = document.createElement('div');
    slot.className = 'inventory-slot';

    if (!item || item.amount <= 0) {
      return slot;
    }

    var itemNode = document.createElement('div');
    var icon = document.createElement('img');
    var amount = document.createElement('span');

    itemNode.className = 'inventory-item';
    if (item.changed) {
      itemNode.classList.add('item-enter');
    }

    icon.src = item.icon;
    icon.alt = item.label;
    icon.setAttribute('draggable', 'false');

    amount.className = 'inventory-number';
    amount.textContent = '' + item.amount;

    itemNode.appendChild(icon);
    itemNode.appendChild(amount);
    slot.appendChild(itemNode);
    return slot;
  }

  // Organização visual do inventário na página.
  function renderInventory(user) {
    var totalMainSlots = 27;
    var totalHotbarSlots = 9;
    var items = [
      {
        key: 'wood',
        label: 'Madeira',
        amount: parseInt(user.wood || 0, 10),
        icon: '/static/img/tree.png'
      },
      {
        key: 'stone',
        label: 'Pedra',
        amount: parseInt(user.stone || 0, 10),
        icon: '/static/img/stone.png'
      }
    ];
    var index;

    if (!inventoryMain || !inventoryHotbar) {
      return;
    }

    inventoryMain.innerHTML = '';
    inventoryHotbar.innerHTML = '';

    for (var ii = 0; ii < items.length; ii++) {
      var item = items[ii];
      item.changed = previousInventory[item.key] !== item.amount;
      previousInventory[item.key] = item.amount;
    }

    for (index = 0; index < totalMainSlots; index += 1) {
      inventoryMain.appendChild(createInventorySlot(items[index] || null));
    }

    for (index = 0; index < totalHotbarSlots; index += 1) {
      inventoryHotbar.appendChild(createInventorySlot(items[totalMainSlots + index] || null));
    }
  }

  // Atualiza toda a interface com dados do servidor.
  function renderState(payload) {
    latestStatePayload = payload;
    renderInventory(payload.user);

    renderSlots(payload.slots, payload.buildings);
    renderLogs(payload.logs);
    buildScene(payload.stones || []);
    if (payload.trees) {
      renderTrees(payload.trees);
    }
  }

  // Árvores e tocos desenhados com lógica visual.
  function renderTrees(trees) {
    if (!sceneGrid) return;
  // Remove árvores e tocos desenhados anteriormente.
    var existingTrees = sceneGrid.getElementsByClassName('scene-tree');
var existingStumps = sceneGrid.getElementsByClassName('scene-tree-stump');
var existing = [];
for (var ei = 0; ei < existingTrees.length; ei++) { existing.push(existingTrees[ei]); }
for (var ei = 0; ei < existingStumps.length; ei++) { existing.push(existingStumps[ei]); }
    for (var ei2 = 0; ei2 < existing.length; ei2++) {
      if (existing[ei2].parentNode) { existing[ei2].parentNode.removeChild(existing[ei2]); }
    }

    for (var ti = 0; ti < trees.length; ti++) {
      var t = trees[ti];
      var column = parseInt(t.column, 10);
      var row = mapRows - 1;

      if (t.available) {
        // Clique direto na árvore para cortar madeira.
        var tree = document.createElement('img');
        tree.className = 'scene-tree';
        tree.src = '/static/img/tree.png';
        tree.alt = 'Árvore';
        tree.setAttribute('data-col', '' + column);
        tree.style.left = (column * tileSize + (tileSize / 8)) + 'px';
        tree.style.bottom = (row * tileSize + (tileSize * 0.9) + 2) + 'px';
        tree.style.width = (tileSize * 1.8) + 'px';
        tree.style.height = 'auto';
        tree.style.pointerEvents = 'auto';
        tree.setAttribute('draggable', 'false');
        tree.setAttribute('tabindex', '-1');

        tree.onclick = function (ev) {
          var clicked = ev.target;
          if (!clicked) return;
          var col = parseInt(clicked.getAttribute('data-col'), 10);

          if (clicked.getAttribute('data-chopped')) return;

          if (!canInteractWithColumn(col)) {
            alert('Estás muito longe da árvore. Aproxima-te 1 tile.');
            return;
          }

          clicked.setAttribute('data-chopped', '1');
          clicked.style.pointerEvents = 'none';

          requestJson('/api/chop', { column: col })
            .then(function (payload) {
              if (!payload.ok) {
                alert(payload.payload.message || 'Não foi possível cortar a árvore.');
                clicked.setAttribute('data-chopped', '');
                clicked.style.pointerEvents = 'auto';
                return;
              }

              clicked.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
              clicked.style.opacity = '0.35';
              clicked.style.transform = 'translateY(-20px) scale(0.9)';
              deleteItem(clicked, { delay: 300 });
              setTimeout(function () { if (clicked.parentNode) { clicked.parentNode.removeChild(clicked); } }, 400);
            }).catch(function () {
              alert('Erro de rede ao cortar a árvore.');
              clicked.setAttribute('data-chopped', '');
              clicked.style.pointerEvents = 'auto';
            });
        };

        sceneGrid.appendChild(tree);
      } else {
        // Desenha o toco e o contador de tempo.
        // Toco com contador visual até a árvore voltar.
        var stump = document.createElement('div');
        stump.className = 'scene-tree-stump';
        stump.setAttribute('data-col', '' + column);
        stump.style.position = 'absolute';
        stump.style.left = (column * tileSize + (tileSize / 8)) + 'px';
        stump.style.bottom = (row * tileSize + (tileSize * 0.9) + 2) + 'px';
        stump.style.width = (tileSize * 1.8) + 'px';
        stump.style.height = (tileSize * 1.0) + 'px';
        stump.style.pointerEvents = 'none';

        var badge = document.createElement('div');
        badge.className = 'tree-timer-badge';
        badge.setAttribute('data-col', '' + column);
        badge.style.position = 'absolute';
        badge.style.right = '6px';
        badge.style.top = '-20px';
        badge.style.background = 'rgba(0,0,0,0.6)';
        badge.style.color = '#fff';
        badge.style.padding = '4px 6px';
        badge.style.borderRadius = '6px';
        badge.style.fontSize = '12px';
        badge.textContent = '' + (t.seconds_left || 0);

        stump.appendChild(badge);
        sceneGrid.appendChild(stump);
      }
    }
  }

  // Pedido assíncrono para obter o estado atual.
  function refreshState() {
    fetch('/api/state')
      .then(function (response) {
        return response.json();
      })
      .then(function (payload) {
        renderState(payload);
      });
  }

  // Função genérica para enviar ações ao servidor através de fetch.
  function sendAction(url, body) {
    requestJson(url, body)
      .then(function (response) {
        if (!response.ok) {
          alert(response.payload.message || 'Ocorreu um erro.');
          return;
        }

        refreshState();
      });
  }

  // Remove recursos do inventário através da interface.
  function removeInventoryResource(resource, amount) {
    sendAction('/api/inventory/remove', {
      resource: resource,
      amount: amount
    });
  }

  // Inicia a construção de um slot na interface.
  function buildSlot(slotId) {
    sendAction('/api/build/' + slotId, { building_key: selectedBuildingKey });
  }

  // Inicia uma tarefa através do botão.
  function startTask(slotId) {
    sendAction('/api/task/' + slotId + '/start', {});
  }

  // Recolhe a recompensa através da interface.
  function collectTask(slotId) {
    sendAction('/api/task/' + slotId + '/collect', {});
  }

  // Ajustes finais do cenário.
  if (sceneFrame) {
    sceneFrame.style.width = '100%';
    sceneFrame.style.maxWidth = 'none';
  }

  if (steeve) {
    steeve.style.zIndex = '3';
  }

  // Primeiro desenho vazio; depois o estado vem do servidor.
  buildScene([]);
  setSteevePosition();

  // Seleção da construção ativa na interface.
  for (var bi = 0; bi < buildingButtons.length; bi++) {
    (function (button) {
      button.onclick = function () {
        for (var bj = 0; bj < buildingButtons.length; bj++) {
          buildingButtons[bj].classList.remove('selected');
        }

        button.classList.add('selected');
        selectedBuildingKey = button.getAttribute('data-building-key');
      };
    })(buildingButtons[bi]);
  }

  // Movimento do personagem pelo teclado.
  document.onkeydown = function (event) {
    if (event.key === 'ArrowLeft' || event.key === 'a' || event.key === 'A') {
      moveSteeve(-1);
    }

    if (event.key === 'ArrowRight' || event.key === 'd' || event.key === 'D') {
      moveSteeve(1);
    }
  };

  // Marca a primeira construção como selecionada por defeito.
  if (buildingButtons[0]) {
    buildingButtons[0].classList.add('selected');
  }

  // Redesenha o cenário quando a janela muda de tamanho.
  window.onresize = function () {
    if (!sceneFrame) {
      return;
    }

    if (latestStatePayload) {
      renderState(latestStatePayload);
      return;
    }

    buildScene([]);
    setSteevePosition();
  };

  // Carrega o estado inicial do jogo quando a página abre.
  refreshState();

  // Atualiza periodicamente o estado do jogo.
  setInterval(function () {
    refreshState();
  }, 1000);
}

initGame();
