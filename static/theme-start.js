// Apply the saved theme before the browser paints the workspace.
(() => {
  let theme = 'dark';
  try { theme = localStorage.getItem('any_theme') || theme; } catch {}
  if (theme !== 'system') {
    theme = theme === 'light' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
  }
  document.querySelector('meta[name="color-scheme"]').content = theme === 'system' ? 'light dark' : theme;
})();
