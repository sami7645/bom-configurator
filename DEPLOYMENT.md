# 🚀 Easy Deployment Guide - BOM Konfigurator

## Option 1: Railway (Recommended - Easiest)

### Step 1: Prepare Code
1. **Upload to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial BOM Configurator"
   git branch -M main
   git remote add origin https://github.com/yourusername/bom-configurator.git
   git push -u origin main
   ```

### Step 2: Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your BOM Configurator repo
5. Railway automatically detects Django and deploys!
6. Get your URL: `https://yourapp.railway.app`

**That's it! 🎉**

---

## Option 2: Render

### Step 1: Same GitHub Upload (as above)

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repo
5. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn bom_configurator.wsgi:application`
6. Click "Create Web Service"

---

## Option 3: PythonAnywhere

### Step 1: Upload Code
1. Create account at [pythonanywhere.com](https://pythonanywhere.com)
2. Upload your project files via Files tab

### Step 2: Setup Web App
1. Go to Web tab
2. Click "Add a new web app"
3. Choose Django
4. Point to your project
5. Configure static files

---

## 🔧 Environment Variables (if needed)

For production, set these environment variables:
- `DEBUG=False`
- `SECRET_KEY=your-secret-key`
- `DATABASE_URL=your-database-url` (optional)

---

## 📱 Share with Client

Once deployed, share the URL with your client:
- **Railway:** `https://yourapp.railway.app`
- **Render:** `https://yourapp.onrender.com`
- **PythonAnywhere:** `https://yourusername.pythonanywhere.com`

## 🎯 Quick Test Checklist

After deployment, test:
- [ ] Homepage loads
- [ ] Configurator wizard works
- [ ] CSV data is imported
- [ ] BOM generation works
- [ ] Admin panel accessible

## 💡 Tips

1. **Railway** is fastest for demos (1-click deploy)
2. **Render** has better free tier limits
3. **PythonAnywhere** is most Django-friendly
4. All options provide HTTPS automatically
5. Custom domains available on all platforms

## 🆘 Troubleshooting

**Common issues:**
- Static files not loading → Check STATIC_ROOT setting
- Database errors → Migrations need to run
- CSV import fails → Check file paths

**Quick fixes:**
- Railway: Check build logs in dashboard
- Render: Check deploy logs
- All: Ensure requirements.txt is complete
