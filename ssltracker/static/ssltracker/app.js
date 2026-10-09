document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  const closeMenu = () => { document.body.classList.remove('nav-open'); if(toggle) toggle.setAttribute('aria-expanded','false'); };
  if(toggle) toggle.addEventListener('click', () => { const open = document.body.classList.toggle('nav-open'); toggle.setAttribute('aria-expanded', String(open)); });
  document.addEventListener('keydown', event => { if(event.key === 'Escape') { closeMenu(); if(toggle) toggle.focus(); } });
  document.addEventListener('click', event => { if(!event.target.closest('.sidebar, .menu-toggle')) closeMenu(); });
  document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
    if(!window.confirm(form.dataset.confirm)) event.preventDefault();
  }));
  const status = document.querySelector('[data-refresh]');
  if(status) setTimeout(() => window.location.reload(), 5000);
});
