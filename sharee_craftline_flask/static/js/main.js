const CART_KEY = 'shareeCraftlineCartLocal';
let cart = JSON.parse(localStorage.getItem(CART_KEY) || '[]');
const products = window.PRODUCTS || [];
const categories = window.CATEGORIES || [];

function money(v) {
  return `৳${Number(v || 0).toLocaleString('en-BD')}`;
}

function saveCart() {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartBadge();
}

function updateCartBadge() {
  document.querySelectorAll('#cartBadge').forEach(el => {
    const count = cart.reduce((sum, item) => sum + Number(item.qty || 0), 0);
    el.textContent = count;
    el.classList.toggle('show', count > 0);
  });
}

function priceOf(p) {
  return Number(p.offer_price ?? p.price ?? 0);
}

function productImage(p) {
  return p.images?.[0] ? `/static/${p.images[0]}` : '';
}

function renderSearchResults(query) {
  const box = document.getElementById('siteSearchResults');
  if (!box) return;
  const q = query.trim().toLowerCase();
  if (!q) {
    box.classList.remove('show');
    box.innerHTML = '';
    return;
  }
  const matches = products.filter(p => {
    const cat = categories.find(c => c.id === p.category_id)?.name || '';
    return [p.name, p.description, cat].some(v => String(v || '').toLowerCase().includes(q));
  }).slice(0, 8);
  box.innerHTML = matches.length ? matches.map(p => `
    <a class="search-result" href="/product/${encodeURIComponent(p.id)}">
      <div class="search-thumb">${productImage(p) ? `<img src="${productImage(p)}" alt="">` : '<span>SC</span>'}</div>
      <div><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(categories.find(c => c.id === p.category_id)?.name || 'Collection')}</small></div>
      <b>${money(priceOf(p))}</b>
    </a>`).join('') : '<div class="search-empty">কোনো প্রোডাক্ট পাওয়া যায়নি।</div>';
  box.classList.add('show');
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = String(value ?? '');
  return div.innerHTML;
}

function applyCatalogFilter(min, max) {
  document.querySelectorAll('#catalogGrid .product-card').forEach(card => {
    const price = Number(card.dataset.price || 0);
    const okMin = Number.isNaN(min) || min === null || price >= min;
    const okMax = Number.isNaN(max) || max === null || price <= max;
    card.hidden = !(okMin && okMax);
  });
}

function renderSideCategories() {
  const box = document.getElementById('sideMenuCategories');
  if (!box) return;
  box.innerHTML = categories.length ? categories.map(c => `
    <a class="side-category" href="/category/${encodeURIComponent(c.id)}">
      <span>${c.image ? `<img src="/static/${c.image}" alt="">` : `<i>${escapeHtml((c.name || '?')[0])}</i>`}</span>
      <strong>${escapeHtml(c.name)}</strong><em>→</em>
    </a>`).join('') : '<p class="muted">কোনো ক্যাটাগরি নেই।</p>';
}

function setupMenu() {
  const toggle = document.getElementById('menuToggle');
  const menu = document.getElementById('sideMenu');
  const close = document.getElementById('sideMenuClose');
  const overlay = document.getElementById('menuOverlay');
  if (!toggle || !menu || !close || !overlay) return;
  const open = () => { menu.classList.add('open'); overlay.classList.add('open'); document.body.classList.add('menu-open'); };
  const shut = () => { menu.classList.remove('open'); overlay.classList.remove('open'); document.body.classList.remove('menu-open'); };
  toggle.addEventListener('click', e => { e.stopPropagation(); menu.classList.contains('open') ? shut() : open(); });
  close.addEventListener('click', shut);
  overlay.addEventListener('click', shut);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') shut(); });
  renderSideCategories();

  const apply = document.getElementById('applyFilter');
  const reset = document.getElementById('resetFilter');
  const minEl = document.getElementById('minPrice');
  const maxEl = document.getElementById('maxPrice');
  if (apply) apply.addEventListener('click', () => {
    const min = minEl?.value === '' ? null : Number(minEl.value);
    const max = maxEl?.value === '' ? null : Number(maxEl.value);
    if (min !== null && min < 0 || max !== null && max < 0 || (min !== null && max !== null && min > max)) {
      alert('দামের সীমা সঠিকভাবে দিন।');
      return;
    }
    applyCatalogFilter(min, max);
    shut();
    document.getElementById('collection')?.scrollIntoView({ behavior: 'smooth' });
  });
  if (reset) reset.addEventListener('click', () => {
    if (minEl) minEl.value = '';
    if (maxEl) maxEl.value = '';
    applyCatalogFilter(null, null);
  });

  const trackBtn = document.getElementById('sideMenuTracking');
  if (trackBtn) trackBtn.addEventListener('click', shut);
}

function setupSearch() {
  const input = document.getElementById('siteSearchInput');
  const clear = document.getElementById('searchClear');
  if (!input) return;
  input.addEventListener('input', () => renderSearchResults(input.value));
  clear?.addEventListener('click', () => { input.value = ''; renderSearchResults(''); input.focus(); });
  document.addEventListener('click', e => {
    const area = document.querySelector('.header-search');
    if (area && !area.contains(e.target)) document.getElementById('siteSearchResults')?.classList.remove('show');
  });
}

function setupSlider() {
  const slider = document.getElementById('bestSlider');
  if (!slider) return;
  let index = 0;
  let timer;
  const cards = [...slider.querySelectorAll('.slider-card')];
  if (cards.length < 2) return;
  const render = () => cards.forEach((card, i) => {
    const offset = (i - index + cards.length) % cards.length;
    card.className = 'slider-card ' + (offset === 0 ? 'active' : offset === 1 ? 'next' : offset === cards.length - 1 ? 'prev' : 'far');
  });
  const next = () => { index = (index + 1) % cards.length; render(); };
  const start = () => { clearInterval(timer); timer = setInterval(next, 4200); };
  let startX = 0;
  slider.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, { passive: true });
  slider.addEventListener('touchend', e => { const dx = e.changedTouches[0].clientX - startX; if (Math.abs(dx) > 45) { index = dx < 0 ? (index + 1) % cards.length : (index - 1 + cards.length) % cards.length; render(); start(); } });
  render(); start();
}

function updateHeaderOnScroll() {
  const header = document.getElementById('siteHeader');
  if (!header) return;
  let last = window.scrollY;
  window.addEventListener('scroll', () => {
    const now = window.scrollY;
    if (now > last && now > 90) header.classList.add('hidden');
    else header.classList.remove('hidden');
    last = now;
  }, { passive: true });
}

document.addEventListener('DOMContentLoaded', () => {
  updateCartBadge();
  setupMenu();
  setupSearch();
  setupSlider();
  updateHeaderOnScroll();
});
