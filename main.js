// Alternar tema claro/escuro e persistir
const themeToggle = document.getElementById('themeToggle');
themeToggle?.addEventListener('click', () => {
  const root = document.documentElement;
  const current = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', current);
  try { localStorage.setItem('theme', current); } catch (e) {}
});

// Menu mobile (hambúrguer)
const menuBtn = document.getElementById('menuBtn');
const mobileMenu = document.getElementById('mobileMenu');
menuBtn?.addEventListener('click', () => {
  const isOpen = mobileMenu.style.display === 'block';
  mobileMenu.style.display = isOpen ? 'none' : 'block';
});
// Fecha menu mobile ao clicar em um link
Array.from(document.querySelectorAll('.mobile-link')).forEach(a => {
  a.addEventListener('click', () => { mobileMenu.style.display = 'none'; });
});

// Rolagem suave para âncoras
Array.from(document.querySelectorAll('a[href^="#"]')).forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const id = this.getAttribute('href');
    if (!id || id === '#') return;
    const target = document.querySelector(id);
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// Formulário de contato (validação simples + simulação)
const form = document.getElementById('contactForm');
const statusEl = document.getElementById('formStatus');
form?.addEventListener('submit', (e) => {
  e.preventDefault();
  statusEl.textContent = '';

  const data = Object.fromEntries(new FormData(form).entries());

  if (!data.name || data.name.trim().length < 3) {
    statusEl.textContent = 'Por favor, informe um nome válido (≥ 3 caracteres).';
    return;
  }
  if (!data.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    statusEl.textContent = 'Digite um email válido.';
    return;
  }
  if (!data.message || data.message.trim().length < 10) {
    statusEl.textContent = 'Conte um pouco mais sobre o projeto (≥ 10 caracteres).';
    return;
  }

  statusEl.textContent = 'Enviando…';
  setTimeout(() => {
    statusEl.textContent = 'Mensagem enviada! Eu retorno em breve.';
    form.reset();
  }, 800);
});

// Ano automático
const y = document.getElementById('year');
if (y) y.textContent = new Date().getFullYear();
