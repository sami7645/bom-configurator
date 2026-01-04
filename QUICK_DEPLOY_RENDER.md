# 🚀 Quick Deploy to Render (5 Minutes)

## Step-by-Step Guide

### 1. Push to GitHub (if not already)
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### 2. Deploy on Render

1. **Go to:** https://render.com
2. **Sign up/Login** with GitHub
3. **Click:** "New +" → "Blueprint"
4. **Connect GitHub repo** → Select `bom-configurator`
5. **Render will auto-detect** `render.yaml` ✅
6. **Click:** "Apply"

**OR Manual Setup:**

1. **New +** → **Web Service**
2. **Connect GitHub** → Select repo
3. **Settings:**
   - **Name:** `bom-configurator`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn --env DJANGO_SETTINGS_MODULE=bom_configurator.settings_production bom_configurator.wsgi:application`
4. **Add PostgreSQL:**
   - **New +** → **PostgreSQL**
   - Copy the **Internal Database URL**
5. **Environment Variables:**
   - `DATABASE_URL` = (paste PostgreSQL URL)
   - `SECRET_KEY` = (generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
   - `DEBUG` = `False`
   - `DJANGO_SETTINGS_MODULE` = `bom_configurator.settings_production`
6. **Click:** "Create Web Service"

### 3. Migrations & Seeding

**Automatic!** The `migrate_and_seed` command in the release phase will:
- Run migrations
- Automatically seed the database with CSV data
- Add missing probe combinations

**No manual steps needed!** ✅

If you need to manually re-seed later, use the Shell tab:
```bash
python manage.py migrate_and_seed
```

### 4. Done! 🎉

Your app is live at: `https://bom-configurator.onrender.com`

---

## ⚠️ Important Notes

- **First request** may take 30-60 seconds (wakes up from sleep)
- **Free tier spins down** after 15 min inactivity
- **PostgreSQL is free** and included
- **HTTPS is automatic** ✅

---

## 🔄 Auto-Deploy

Render automatically deploys when you push to GitHub! Just:
```bash
git push origin main
```

---

## 🆘 Troubleshooting

**Build fails?**
- Check build logs in Render dashboard
- Ensure `requirements.txt` is correct

**Database errors?**
- Make sure PostgreSQL is created and `DATABASE_URL` is set
- Run migrations in Shell tab

**Static files not loading?**
- Check `collectstatic` ran in build command
- Verify WhiteNoise is in middleware (already done ✅)

