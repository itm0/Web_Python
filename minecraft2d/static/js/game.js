document.addEventListener('DOMContentLoaded', function () {
  var steeve = document.querySelector('#steeve');
  var sceneFrame = document.querySelector('#scene-frame');
  var sceneGrid = document.querySelector('#scene-grid');
  var woodCount = document.querySelector('#wood-count');
  var stoneCount = document.querySelector('#stone-count');
  var inventoryMain = document.querySelector('#inventory-main');
  var inventoryHotbar = document.querySelector('#inventory-hotbar');
  var slotsGrid = document.querySelector('#slots-grid');
  var logsList = document.querySelector('#logs-list');
  var buildingButtons = document.querySelectorAll('.building-option[data-building-key]');
  var inventoryRemoveButtons = document.querySelectorAll('.inventory-remove');

  var tileSize = 96;
  var mapColumns = 12;
  var minimumColumns = 12;
  var mapRows = 2;
  var selectedBuildingKey = 'cabana';
  var steeveTile = Number(localStorage.getItem('steeve-tile')) || 2;
  var walkLimit = mapColumns - 1;
  var latestStatePayload = null;
  var previousInventory = {
    wood: -1,
    stone: -1
  };

  function getBaseTileSize() {
    if (window.innerWidth <= 720) {
      return 72;
    }

    return 96;
  }

  function updateSceneMetrics() {
    var frameWidth = 0;
    var computedColumns = 0;

    if (!sceneFrame) {
      tileSize = getBaseTileSize();
      walkLimit = mapColumns - 1;
      return;
    }

    frameWidth = sceneFrame.clientWidth || sceneFrame.getBoundingClientRect().width || (minimumColumns * tileSize);

    if (window.innerWidth <= 430) {
      // Keep all mandatory columns visible on narrow mobile viewports.
      tileSize = Math.max(32, Math.floor(frameWidth / minimumColumns));
    } else {
      tileSize = getBaseTileSize();
    }

    computedColumns = Math.ceil(frameWidth / tileSize);
    mapColumns = Math.max(minimumColumns, computedColumns);
    walkLimit = mapColumns - 1;

    if (steeveTile > walkLimit) {
      steeveTile = walkLimit;
    }
  }

  function buildScene(stones) {
    var row;
    var column;
    var stoneByColumn = {};

    if (!sceneGrid) {
      return;
    }

    updateSceneMetrics();

    sceneGrid.innerHTML = '';

    (stones || []).forEach(function (stone) {
      stoneByColumn[Number(stone.column)] = stone;
    });

    for (row = 0; row < mapRows; row += 1) {
      for (column = 0; column < mapColumns; column += 1) {
        var tile = document.createElement('img');
        var isGrassRow = row === mapRows - 1;
        var isDirtRow = row === 0;
        var stone = isDirtRow ? stoneByColumn[column] : null;

        tile.className = 'scene-tile';
        tile.src = isGrassRow ? '/img/relva.png' : (stone && stone.available ? '/img/stone.png' : '/img/terra.png');
        tile.alt = isGrassRow ? 'Relva' : (stone && stone.available ? 'Pedra' : 'Terra');
        tile.dataset.col = String(column);
        tile.style.left = (column * tileSize) + 'px';
        tile.style.bottom = (row * tileSize) + 'px';
        tile.style.width = tileSize + 'px';
        tile.style.height = tileSize + 'px';

        if (stone && stone.available) {
          tile.className = 'scene-tile scene-stone';
          tile.style.zIndex = '2';
          tile.style.pointerEvents = 'auto';
          tile.setAttribute('draggable', 'false');
          tile.setAttribute('tabindex', '-1');

          tile.addEventListener('click', function (ev) {
            ev.preventDefault();
            ev.stopPropagation();

            var clicked = ev.currentTarget || ev.target;
            if (!clicked) return;
            var col = Number(clicked.dataset.col);

            if (clicked.dataset.mined) return;

            var playerTile = (typeof steeveTile !== 'undefined') ? steeveTile : Number(localStorage.getItem('steeve-tile')) || 0;
            if (Math.abs(playerTile - col) > 1) {
              alert('Estás muito longe da pedra. Aproxima-te 1 tile.');
              return;
            }

            clicked.dataset.mined = '1';
            clicked.style.pointerEvents = 'none';

            fetch('/api/mine-stone', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ column: col })
            })
              .then(function (r) { return r.json(); })
              .then(function (payload) {
                if (!payload || !payload.ok) {
                  alert((payload && payload.message) || 'Não foi possível minerar a pedra.');
                  clicked.dataset.mined = '';
                  clicked.style.pointerEvents = 'auto';
                  return;
                }

                clicked.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                clicked.style.opacity = '0.35';
                clicked.style.transform = 'translateY(-12px) scale(0.95)';
                if (stoneCount) {
                  stoneCount.textContent = String(payload.stone);
                }

                setTimeout(function () {
                  refreshState();
                }, 250);
              }).catch(function () {
                alert('Erro de rede ao minerar a pedra.');
                clicked.dataset.mined = '';
                clicked.style.pointerEvents = 'auto';
              });
          });
        }

        if (stone && !stone.available) {
          var stoneBadge = document.createElement('div');
          stoneBadge.className = 'stone-timer-badge';
          stoneBadge.dataset.col = String(column);
          stoneBadge.style.position = 'absolute';
          stoneBadge.style.left = (column * tileSize + 6) + 'px';
          stoneBadge.style.bottom = (row * tileSize + (tileSize * 0.9) + 2) + 'px';
          stoneBadge.style.zIndex = '3';
          stoneBadge.style.background = 'rgba(0,0,0,0.6)';
          stoneBadge.style.color = '#fff';
          stoneBadge.style.padding = '4px 6px';
          stoneBadge.style.borderRadius = '6px';
          stoneBadge.style.fontSize = '12px';
          stoneBadge.textContent = String(stone.seconds_left || 0);
          sceneGrid.appendChild(stoneBadge);
        }

        sceneGrid.appendChild(tile);

        // trees are rendered by server-driven renderer (renderTrees)
      }
    }
  }

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
      try {
        node.remove();
      } catch (error) {
        if (node.parentNode) {
          node.parentNode.removeChild(node);
        }
      }
    }, delay);
  }

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
    steeve.style.bottom = ((tileSize * mapRows) - 8) + 'px';
    steeve.style.width = 'auto';
    steeve.style.height = (tileSize * 1.375) + 'px';
    localStorage.setItem('steeve-tile', String(steeveTile));
  }

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

  function renderLogs(logs) {
    if (!logsList) {
      return;
    }

    logsList.innerHTML = '';

    logs.forEach(function (log) {
      var card = document.createElement('article');
      var message = document.createElement('p');
      var time = document.createElement('time');

      card.className = 'log-card';
      message.textContent = log.message;
      time.textContent = new Date(log.created_at).toLocaleTimeString('pt-PT', {
        hour: '2-digit',
        minute: '2-digit'
      });

      card.appendChild(message);
      card.appendChild(time);
      logsList.appendChild(card);
    });
  }

  function renderSlots(slots, buildings) {
    if (!slotsGrid) {
      return;
    }

    slotsGrid.innerHTML = '';

    slots.forEach(function (slot) {
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

      if (slot.state === 'empty') {
        var buildButton = document.createElement('button');
        buildButton.className = 'slot-action build';
        buildButton.textContent = 'Construir aqui';
        buildButton.addEventListener('click', function () {
          buildSlot(slot.id);
        });
        actionBox.appendChild(buildButton);
      }

      if (slot.state === 'ready') {
        var taskButton = document.createElement('button');
        taskButton.className = 'slot-action task';
        taskButton.textContent = 'Iniciar tarefa';
        taskButton.addEventListener('click', function () {
          startTask(slot.id);
        });
        actionBox.appendChild(taskButton);
      }

      if (slot.state === 'collectable') {
        var collectButton = document.createElement('button');
        collectButton.className = 'slot-action collect';
        collectButton.textContent = 'Recolher recompensa';
        collectButton.addEventListener('click', function () {
          collectTask(slot.id);
        });
        actionBox.appendChild(collectButton);
      }

      card.appendChild(actionBox);
      slotsGrid.appendChild(card);
    });
  }

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
    amount.textContent = String(item.amount);

    itemNode.appendChild(icon);
    itemNode.appendChild(amount);
    slot.appendChild(itemNode);
    return slot;
  }

  function renderInventory(user) {
    var totalMainSlots = 27;
    var totalHotbarSlots = 9;
    var items = [
      {
        key: 'wood',
        label: 'Madeira',
        amount: Number(user.wood || 0),
        icon: 'https://gamepedia.cursecdn.com/minecraft_gamepedia/thumb/c/c5/Oak_Log_Axis_Y_JE5_BE3.png/150px-Oak_Log_Axis_Y_JE5_BE3.png?version=be4f749b0035ee90956bab6c5361eeb5'
      },
      {
        key: 'stone',
        label: 'Pedra',
        amount: Number(user.stone || 0),
        icon: 'https://gamepedia.cursecdn.com/minecraft_gamepedia/thumb/6/6a/Cobblestone_JE6_BE3.png/150px-Cobblestone_JE6_BE3.png?version=5d7e2cc3c7485a77f63449e05baecc65'
      }
    ];
    var index;

    if (!inventoryMain || !inventoryHotbar) {
      return;
    }

    inventoryMain.innerHTML = '';
    inventoryHotbar.innerHTML = '';

    items.forEach(function (item) {
      item.changed = previousInventory[item.key] !== item.amount;
      previousInventory[item.key] = item.amount;
    });

    for (index = 0; index < totalMainSlots; index += 1) {
      inventoryMain.appendChild(createInventorySlot(items[index] || null));
    }

    for (index = 0; index < totalHotbarSlots; index += 1) {
      inventoryHotbar.appendChild(createInventorySlot(items[totalMainSlots + index] || null));
    }
  }

  function renderState(payload) {
    latestStatePayload = payload;
    renderInventory(payload.user);

    if (woodCount) {
      woodCount.textContent = String(payload.user.wood);
    }

    if (stoneCount) {
      stoneCount.textContent = String(payload.user.stone);
    }

    renderSlots(payload.slots, payload.buildings);
    renderLogs(payload.logs);
    buildScene(payload.stones || []);
    if (payload.trees) {
      renderTrees(payload.trees);
    }
  }

  function renderTrees(trees) {
    if (!sceneGrid) return;
    // remove existing dynamic trees/stumps
    var existing = sceneGrid.querySelectorAll('.scene-tree, .scene-tree-stump');
    existing.forEach(function (n) { try { n.remove(); } catch (e) {} });

    trees.forEach(function (t) {
      var column = Number(t.column);
      var row = mapRows - 1;

      if (t.available) {
        var tree = document.createElement('img');
        tree.className = 'scene-tree';
        tree.src = '/img/tree.png';
        tree.alt = 'Árvore';
        tree.dataset.col = String(column);
        tree.style.left = (column * tileSize + (tileSize / 8)) + 'px';
        tree.style.bottom = (row * tileSize + (tileSize * 0.9) + 2) + 'px';
        tree.style.width = (tileSize * 1.8) + 'px';
        tree.style.height = 'auto';
        tree.style.pointerEvents = 'auto';
        tree.setAttribute('draggable', 'false');
        tree.setAttribute('tabindex', '-1');

        tree.addEventListener('click', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          var clicked = ev.currentTarget || ev.target;
          if (!clicked) return;
          var col = Number(clicked.dataset.col);

          if (clicked.dataset.chopped) return;

          var playerTile = (typeof steeveTile !== 'undefined') ? steeveTile : Number(localStorage.getItem('steeve-tile')) || 0;
          if (Math.abs(playerTile - col) > 1) {
            alert('Estás muito longe da árvore. Aproxima-te 1 tile.');
            return;
          }

          clicked.dataset.chopped = '1';
          clicked.style.pointerEvents = 'none';

          fetch('/api/chop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ column: col })
          })
            .then(function (r) { return r.json(); })
            .then(function (payload) {
              if (!payload || !payload.ok) {
                alert((payload && payload.message) || 'Não foi possível cortar a árvore.');
                clicked.dataset.chopped = '';
                clicked.style.pointerEvents = 'auto';
                return;
              }

              clicked.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
              clicked.style.opacity = '0.35';
              clicked.style.transform = 'translateY(-20px) scale(0.9)';
              var wc = document.querySelector('#wood-count');
              if (wc) wc.textContent = String(payload.wood);
              deleteItem(clicked, { delay: 300 });
              setTimeout(function () { try { clicked.remove(); } catch (e) {} }, 400);
            }).catch(function () {
              alert('Erro de rede ao cortar a árvore.');
              clicked.dataset.chopped = '';
              clicked.style.pointerEvents = 'auto';
            });
        });

        sceneGrid.appendChild(tree);
      } else {
        // render stump + timer badge
        var stump = document.createElement('div');
        stump.className = 'scene-tree-stump';
        stump.dataset.col = String(column);
        stump.style.position = 'absolute';
        stump.style.left = (column * tileSize + (tileSize / 8)) + 'px';
        stump.style.bottom = (row * tileSize + (tileSize * 0.9) + 2) + 'px';
        stump.style.width = (tileSize * 1.8) + 'px';
        stump.style.height = (tileSize * 1.0) + 'px';
        stump.style.pointerEvents = 'none';

        var badge = document.createElement('div');
        badge.className = 'tree-timer-badge';
        badge.dataset.col = String(column);
        badge.style.position = 'absolute';
        badge.style.right = '6px';
        badge.style.top = '-20px';
        badge.style.background = 'rgba(0,0,0,0.6)';
        badge.style.color = '#fff';
        badge.style.padding = '4px 6px';
        badge.style.borderRadius = '6px';
        badge.style.fontSize = '12px';
        badge.textContent = String(t.seconds_left || 0);

        stump.appendChild(badge);
        sceneGrid.appendChild(stump);
      }
    });
  }

  function refreshState() {
    fetch('/api/state')
      .then(function (response) {
        return response.json();
      })
      .then(function (payload) {
        renderState(payload);
      });
  }

  function sendAction(url, body) {
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body || {})
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          return { ok: response.ok, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          alert(result.payload.message || 'Ocorreu um erro.');
          return;
        }

        refreshState();
      });
  }

  function removeInventoryResource(resource, amount) {
    sendAction('/api/inventory/remove', {
      resource: resource,
      amount: amount
    });
  }

  function buildSlot(slotId) {
    sendAction('/api/build/' + slotId, { building_key: selectedBuildingKey });
  }

  function startTask(slotId) {
    sendAction('/api/task/' + slotId + '/start', {});
  }

  function collectTask(slotId) {
    sendAction('/api/task/' + slotId + '/collect', {});
  }

  if (sceneFrame) {
    sceneFrame.style.width = '100%';
    sceneFrame.style.maxWidth = 'none';
  }

  if (steeve) {
    steeve.style.zIndex = '3';
  }

  buildScene([]);
  setSteevePosition();

  buildingButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      buildingButtons.forEach(function (item) {
        item.classList.remove('selected');
      });

      button.classList.add('selected');
      selectedBuildingKey = button.getAttribute('data-building-key');
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'ArrowLeft' || event.key === 'a' || event.key === 'A') {
      moveSteeve(-1);
    }

    if (event.key === 'ArrowRight' || event.key === 'd' || event.key === 'D') {
      moveSteeve(1);
    }
  });

  if (buildingButtons[0]) {
    buildingButtons[0].classList.add('selected');
  }

  window.addEventListener('resize', function () {
    if (!sceneFrame) {
      return;
    }

    if (latestStatePayload) {
      renderState(latestStatePayload);
      return;
    }

    buildScene([]);
    setSteevePosition();
  });

  inventoryRemoveButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var resource = button.getAttribute('data-resource');
      var amount = Number(button.getAttribute('data-amount') || '1');
      removeInventoryResource(resource, amount);
    });
  });

  refreshState();
});
