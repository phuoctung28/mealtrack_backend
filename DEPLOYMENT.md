# Railway Deployment Guide

## 🚀 Deploy to Railway

### Prerequisites
1. [Railway account](https://railway.app/) 
2. GitHub repository connected to Railway

### Environment Variables
Set these environment variables in Railway dashboard:

**Required:**
```
DATABASE_URL=mysql://user:password@host:port/database
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
```

**Optional (Cloudinary):**
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
USE_MOCK_STORAGE=0
```

**Development:**
```
USE_MOCK_STORAGE=1
```

### Database Setup

#### Option 1: Railway MySQL
1. In Railway dashboard, click "New" → "Database" → "MySQL"
2. Copy the connection string from Railway MySQL service
3. Set `DATABASE_URL` environment variable

#### Option 2: External MySQL (PlanetScale, etc.)
1. Create MySQL database on your preferred provider
2. Get connection string 
3. Set `DATABASE_URL` environment variable

### Deployment Steps

1. **Connect Repository**
   ```bash
   # Push your code to GitHub (already done!)
   git push origin main
   ```

2. **Create Railway Project**
   - Go to [Railway](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select `phuoctung28/mealtrack_backend`

3. **Configure Environment Variables**
   - In Railway dashboard, go to your service
   - Click "Variables" tab
   - Add all required environment variables

4. **Deploy**
   - Railway will automatically detect Python app
   - Build and deploy using our configuration files
   - Monitor logs for any issues

### Database Migration
After first deployment, run migrations:

1. **Using Railway CLI** (recommended):
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login and link project
   railway login
   railway link
   
   # Run migrations
   railway run alembic upgrade head
   ```

2. **Using Railway Shell**:
   - In Railway dashboard, go to your service
   - Click "Shell" tab
   - Run: `alembic upgrade head`

### Health Check
After deployment, verify:
- Visit: `https://your-app.railway.app/health`
- Should return: `{"status": "healthy"}`
- API docs: `https://your-app.railway.app/docs`

### Monitoring
- **Logs**: Railway dashboard → Service → Logs
- **Metrics**: Railway dashboard → Service → Metrics
- **Health**: `/health` endpoint

### Troubleshooting

**Common Issues:**
1. **Database connection** - Check `DATABASE_URL` format
2. **Missing env vars** - Verify all required variables are set
3. **Port binding** - Railway sets `$PORT` automatically
4. **Build failures** - Check requirements.txt and Python version

**Logs Access:**
```bash
# Using Railway CLI
railway logs
```

### Custom Domain (Optional)
1. Railway dashboard → Service → Settings
2. Click "Generate Domain" or add custom domain
3. Configure DNS if using custom domain 