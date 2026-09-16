document.addEventListener('DOMContentLoaded', () => {
  const p = window.PRODUCT;
  if (!p) return;
  const qtyEl = document.getElementById('qtyValue');
  const min = 1;
  let qty = 1;
  let selectedColor = p.colors?.[0] || null;
  let blouse = p.has_blouse_option ? 'with' : null;
  const cart = JSON.parse(localStorage.getItem('shareeCraftlineCartLocal') || '[]');
  const save = () => localStorage.setItem('shareeCraftlineCartLocal', JSON.stringify(cart));
  const renderQty = () => qtyEl.textContent = qty;
  document.getElementById('qtyMinus')?.addEventListener('click', () => { qty = Math.max(min, qty - 1); renderQty(); });
  document.getElementById('qtyPlus')?.addEventListener('click', () => { qty = Math.min(Number(p.stock || 0), qty + 1); renderQty(); });
  document.querySelectorAll('[data-value]').forEach(btn => btn.addEventListener('click', () => { selectedColor = btn.dataset.value; document.querySelectorAll('[data-value]').forEach(b => b.classList.remove('selected')); btn.classList.add('selected'); }));
  document.querySelectorAll('[data-blouse]').forEach(btn => btn.addEventListener('click', () => { blouse = btn.dataset.blouse; document.querySelectorAll('[data-blouse]').forEach(b => b.classList.remove('selected')); btn.classList.add('selected'); }));
  document.querySelectorAll('.thumb').forEach(btn => btn.addEventListener('click', () => { document.querySelector('#mainImage img')?.setAttribute('src', btn.dataset.src); }));
  function add(goCheckout=false) {
    if (!p.stock) return;
    const existing = cart.find(i => i.id === p.id && i.color === selectedColor && i.blouse === blouse);
    if (existing) existing.qty = Math.min(Number(p.stock), existing.qty + qty);
    else cart.push({ id: p.id, name: p.name, price: Number(p.offer_price ?? p.price), qty, image: p.images?.[0] || '', color: selectedColor, blouse });
    save();
    if (goCheckout) location.href = '/checkout';
    else { const btn = document.getElementById('addToCart'); if (btn) { const old=btn.textContent; btn.textContent='কার্টে যোগ হয়েছে ✓'; setTimeout(()=>btn.textContent=old,1400); } }
  }
  document.getElementById('addToCart')?.addEventListener('click', () => add(false));
  document.getElementById('buyNow')?.addEventListener('click', () => add(true));
});
