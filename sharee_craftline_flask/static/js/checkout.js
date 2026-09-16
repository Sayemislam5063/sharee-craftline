document.addEventListener('DOMContentLoaded', () => {
  const cart = JSON.parse(localStorage.getItem('shareeCraftlineCartLocal') || '[]');
  const itemsEl = document.getElementById('checkoutItems');
  const productTotalEl = document.getElementById('summaryProduct');
  const deliveryEl = document.getElementById('summaryDelivery');
  const totalEl = document.getElementById('summaryTotal');
  const form = document.getElementById('checkoutForm');
  const result = document.getElementById('orderResult');
  const deliveryInput = form?.elements.delivery_charge;

  function money(v) { return `৳${Number(v || 0).toLocaleString('en-BD')}`; }
  function save() { localStorage.setItem('shareeCraftlineCartLocal', JSON.stringify(cart)); }
  function render() {
    if (!itemsEl) return;
    if (!cart.length) { itemsEl.innerHTML = '<div class="empty-state">আপনার কার্ট খালি।</div>'; form?.querySelector('button[type="submit"]')?.setAttribute('disabled','disabled'); }
    else {
      form?.querySelector('button[type="submit"]')?.removeAttribute('disabled');
      itemsEl.innerHTML = cart.map((i, idx) => `
      <div class="checkout-item"><div class="checkout-item-info"><strong>${escapeHtml(i.name)}</strong><small>${money(i.price)} × ${i.qty}</small></div><div class="checkout-qty"><button type="button" data-i="${idx}" data-a="-">−</button><span>${i.qty}</span><button type="button" data-i="${idx}" data-a="+">+</button><button class="remove" type="button" data-i="${idx}" data-a="x">×</button></div></div>`).join('');
      itemsEl.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => { const idx=Number(btn.dataset.i); const a=btn.dataset.a; if(a==='+') cart[idx].qty += 1; if(a==='-' ) cart[idx].qty = Math.max(1, cart[idx].qty-1); if(a==='x') cart.splice(idx,1); save(); render(); });
    }
    const productTotal = cart.reduce((s,i)=>s+Number(i.price)*Number(i.qty),0);
    const delivery = Number(deliveryInput?.value || 0);
    productTotalEl.textContent = money(productTotal); deliveryEl.textContent = money(delivery); totalEl.textContent = money(productTotal+delivery);
  }
  deliveryInput?.addEventListener('change', render);
  form?.addEventListener('submit', async e => {
    e.preventDefault();
    if (!cart.length) return;
    const btn = form.querySelector('button[type="submit"]'); btn.disabled=true; btn.textContent='অর্ডার পাঠানো হচ্ছে...';
    const payload = Object.fromEntries(new FormData(form).entries()); payload.items=cart; payload.delivery_charge=Number(payload.delivery_charge||0);
    const res = await fetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data = await res.json();
    if (!res.ok || !data.ok) { result.innerHTML = `<div class="error-box">${escapeHtml(data.error || 'অর্ডার করা যায়নি।')}</div>`; btn.disabled=false; btn.textContent='অর্ডার কনফার্ম করুন'; return; }
    localStorage.removeItem('shareeCraftlineCartLocal'); cart.length=0; render(); form.style.display='none'; result.innerHTML=`<div class="success-box"><h3>অর্ডার সফল হয়েছে 🎉</h3><p>আপনার Tracking ID:</p><strong>${escapeHtml(data.tracking_id)}</strong><a class="solid-btn" href="/track?tracking=${encodeURIComponent(data.tracking_id)}">অর্ডার ট্র্যাক করুন</a></div>`;
  });
  render();
});
function escapeHtml(v){const d=document.createElement('div');d.textContent=String(v??'');return d.innerHTML;}
