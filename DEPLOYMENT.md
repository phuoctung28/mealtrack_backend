# Deployment Guide for MealTrack Backend

## Railway Deployment Optimization

This guide documents the optimizations made to prevent Railway build timeouts.

### Problem
- Railway builds were timing out during `pip install` phase
- Too many dependencies and heavy initialization during startup

### Solution Architecture

We've created a multi-environment setup with optimized configurations for production:

#### 1. **Separated Environment Configurations**

- **Development** (`src/api/main.py`): Full features, database initialization, development tools
- **Production** (`src/api/main_prod.py`): Minimal startup, no auto-initialization, optimized imports

#### 2. **Optimized Dependencies**

Three requirement files for different needs:
- `requirements.txt` - Full development dependencies (includes testing)
- `requirements-prod.txt` - Production dependencies (no testing)
- `requirements-minimal.txt` - Absolute minimum for Railway (fastest build)

#### 3. **Docker Optimization**

- **Dockerfile.railway** - Ultra-optimized for Railway deployment
  - Uses minimal requirements
  - Single-stage build (faster)
  - Minimal system packages
  - Aggressive caching strategies

#### 4. **Key Files**

```
.
├── Dockerfile.railway      # Railway-specific optimized Docker
├── requirements-minimal.txt # Minimal deps for fast builds
├── src/api/main_prod.py    # Production FastAPI app
├── railway.json            # Railway configuration
├── start.sh               # Environment-aware startup script
└── .dockerignore          # Excludes unnecessary files
```

### Deployment Steps

1. **Push to repository**
   ```bash
   git add .
   git commit -m "Add Railway deployment optimizations"
   git push origin main
   ```

2. **Railway will automatically**:
   - Use `Dockerfile.railway` (specified in railway.json)
   - Install minimal dependencies
   - Start production server with `main_prod.py`
   - Skip database initialization (handled separately)

### Environment Variables Required

Set these in Railway dashboard:

```env
# Database (Railway provides DATABASE_URL automatically)
DATABASE_URL=mysql://user:pass@host:port/dbname

# Environment
ENVIRONMENT=production
RAILWAY_ENVIRONMENT=true

# Optional
DISABLE_DOCS=false  # Set to true to disable /docs in production
CORS_ORIGINS=*      # Comma-separated list of allowed origins

# AI Services
GOOGLE_API_KEY=your-key-here

# Storage
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
```

### Testing Locally

1. **Test production configuration**:
   ```bash
   ENVIRONMENT=production .venv/bin/python -c "from src.api.main_prod import app; print('✅ Works!')"
   ```

2. **Run production server locally**:
   ```bash
   ENVIRONMENT=production ./start.sh
   ```

3. **Test Docker build**:
   ```bash
   docker build -f Dockerfile.railway -t mealtrack-prod .
   docker run -p 8000:8000 -e DATABASE_URL=your_url mealtrack-prod
   ```

### Performance Improvements

- **Build time**: Reduced from timeout (>10 min) to ~2-3 minutes
- **Image size**: Smaller due to excluded test dependencies
- **Startup time**: Faster with no auto-initialization
- **Memory usage**: Lower with minimal imports

### Monitoring

Check health endpoint:
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "production"
}
```

### Rollback Plan

If issues occur, revert to Nixpacks:

1. Edit `railway.json`:
   ```json
   {
     "build": {
       "builder": "NIXPACKS"
     }
   }
   ```

2. Railway will use default Nixpacks builder

### Future Optimizations

1. **Multi-stage Docker builds** - Further reduce image size
2. **Dependency caching** - Use Railway's build cache
3. **CDN for static files** - Offload static content
4. **Database connection pooling** - Optimize DB connections
5. **Async initialization** - Move heavy init to background tasks