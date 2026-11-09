document.querySelectorAll('[data-password-toggle]').forEach((toggle) => {
  const input = document.getElementById(toggle.getAttribute('aria-controls'));
  if (!input) return;

  toggle.hidden = false;
  toggle.addEventListener('click', () => {
    const showPassword = input.type === 'password';
    input.type = showPassword ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', String(showPassword));
    toggle.setAttribute('aria-label', showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña');
    toggle.querySelector('span').textContent = showPassword ? 'Ocultar' : 'Mostrar';
    toggle.querySelector('i').className = showPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
  });
});
