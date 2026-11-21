const views = [...document.querySelectorAll('.download-view')];
const navigation = [...document.querySelectorAll('[data-view]')];

function showView() {
  const requested = window.location.hash.slice(1);
  const selected = requested === 'cli' ? 'cli' : 'desktop';
  for (const view of views) view.hidden = view.id !== selected;
  for (const link of navigation) {
    if (link.dataset.view === selected) link.setAttribute('aria-current', 'true');
    else link.removeAttribute('aria-current');
  }
}

showView();
window.addEventListener('hashchange', showView);

const installer = document.querySelector('[data-installer]');
if (installer) {
  const command = installer.querySelector('[data-command]');
  const status = document.querySelector('[data-copy-status]');
  const platformButtons = [...installer.querySelectorAll('[data-platform]')];
  const posixCommand = command.textContent;

  function selectPlatform(platform) {
    command.textContent = platform === 'windows' ? posixCommand.replace(/^python3/, 'py -3') : posixCommand;
    for (const button of platformButtons) button.setAttribute('aria-pressed', String(button.dataset.platform === platform));
    status.textContent = '';
  }

  const device = navigator.userAgentData?.platform || navigator.userAgent;
  selectPlatform(/Windows/i.test(device) ? 'windows' : 'posix');
  for (const button of platformButtons) button.addEventListener('click', () => selectPlatform(button.dataset.platform));
  installer.querySelector('[data-copy]').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(command.textContent);
      status.textContent = '已复制。粘贴到终端后按回车。';
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(command);
      selection?.removeAllRanges();
      selection?.addRange(range);
      status.textContent = '命令已选中，可手动复制。';
    }
  });
}
