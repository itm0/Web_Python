document.addEventListener('DOMContentLoaded', function () {
  var themeToggle = document.querySelector('#theme-toggle');
  var storageKey = 'minecraft2d-theme';

  function applyTheme(theme) {
    var isDark = theme === 'dark';

    document.body.classList.toggle('dark-mode', isDark);

    if (themeToggle) {
      themeToggle.textContent = isDark ? 'Modo claro' : 'Modo escuro';
      themeToggle.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    }
  }

  function getInitialTheme() {
    var saved = localStorage.getItem(storageKey);
    if (saved === 'dark' || saved === 'light') {
      return saved;
    }
    return 'light';
  }

  applyTheme(getInitialTheme());

  if (!themeToggle) {
    return;
  }

  themeToggle.addEventListener('click', function () {
    var nextTheme = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
    localStorage.setItem(storageKey, nextTheme);
    applyTheme(nextTheme);
  });
});
