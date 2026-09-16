# Sharee Craftline — Local Flask + SQLite E-commerce

এই version-এ Supabase নেই। Product, category, stock, order ও tracking data **SQLite database-এ** এবং product/category images **আপনার PC-র `static/uploads/` folder-এ** থাকবে।

## কী আছে

- Mobile-first glassmorphism storefront
- Home page + best selling slider
- Category bubbles + category pages
- Product detail page
- Quantity selector + cart (browser localStorage)
- Checkout with Bangladesh delivery charge options
- Local SQLite order storage
- Tracking ID generation + tracking page
- Admin login
- Admin dashboard: products, stock, categories, orders, order status
- Multiple product image upload
- Offer price, colors, blouse option
- Search
- Homepage price filter through menu
- Responsive left-side menu

## Run

1. Python 3.10+ install করুন।
2. Terminal খুলে project folder-এ যান।
3. চালান:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\\Scripts\\activate
```

তারপর:

```bash
pip install -r requirements.txt
python app.py
```

Browser-এ খুলুন: `http://127.0.0.1:5000`

## Admin

প্রথমবার নিরাপদ credential সেট করতে `.env` ব্যবহার করুন। `.env.example` কপি করে `.env` করুন এবং `ADMIN_PASSWORD` বদলান। এই starter-এ fallback password ইচ্ছাকৃতভাবে `change-me-now`, তাই production-এ অবশ্যই পরিবর্তন করবেন।

Admin: `http://127.0.0.1:5000/admin/login`

## GitHub + deployment note

GitHub repository শুধু Python code সংরক্ষণ করবে; Python Flask app চালানোর জন্য Python-capable hosting দরকার। শুধু GitHub Pages-এ Flask backend চলবে না। Local PC-তে চালালে database ও uploaded images আপনার PC-তেই থাকবে।

## নিরাপত্তা

API token, bot token, password বা secret কখনো source code-এ commit করবেন না। `.env` ব্যবহার করুন।
