# Scheduly Deployment Guide

This guide covers deploying your complete Scheduly application with Auth0 authentication and PostgreSQL database.

## 🚀 Quick Deployment Checklist

### Prerequisites

- [ ] Auth0 account with application configured
- [ ] PostgreSQL database (Railway, Supabase, or local)
- [ ] Railway account for backend deployment
- [ ] Vercel account for frontend deployment

### Backend Deployment (Railway)

1. **Connect Repository**

   ```bash
   # Push your code to GitHub
   git add .
   git commit -m "Add OAuth authentication and schedule history"
   git push origin main
   ```

2. **Deploy to Railway**

   - Go to [Railway](https://railway.app)
   - Create new project from GitHub repository
   - Select your backend folder

3. **Set Environment Variables**

   ```bash
   DATABASE_URL=postgresql://user:password@host:port/db
   AUTH0_DOMAIN=your-tenant.auth0.com
   AUTH0_AUDIENCE=your-api-identifier
   APP_MODE=production
   GEMINI_API_KEY=your_gemini_api_key
   ```

4. **Initialize Database**
   ```bash
   # Run this in Railway console or locally
   python scripts/init_database.py
   ```

### Frontend Deployment (Vercel)

1. **Connect Repository**

   - Go to [Vercel](https://vercel.com)
   - Import your GitHub repository
   - Set root directory to `frontend`

2. **Set Environment Variables**

   ```bash
   AUTH0_SECRET=your-secret-key
   AUTH0_BASE_URL=https://your-domain.vercel.app
   AUTH0_ISSUER_BASE_URL=https://your-tenant.auth0.com
   AUTH0_CLIENT_ID=your-client-id
   AUTH0_CLIENT_SECRET=your-client-secret
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```

3. **Deploy**
   - Vercel will automatically deploy on push
   - Update Auth0 callback URLs to production domain

## 🔧 Auth0 Production Configuration

### 1. Update Application Settings

**Allowed Callback URLs:**

```
https://your-domain.vercel.app/api/auth/callback
```

**Allowed Logout URLs:**

```
https://your-domain.vercel.app
```

**Allowed Web Origins:**

```
https://your-domain.vercel.app
```

### 2. API Configuration

**Identifier:** `https://your-backend.railway.app`
**Signing Algorithm:** RS256

### 3. Rules (Optional)

Add this rule for custom claims:

```javascript
function addUserMetadata(user, context, callback) {
  const namespace = "https://scheduly.com/";
  context.idToken[namespace + "user_metadata"] = user.user_metadata;
  context.accessToken[namespace + "user_metadata"] = user.user_metadata;
  callback(null, user, context);
}
```

## 🗄️ Database Setup

### Option 1: Railway PostgreSQL

1. Add PostgreSQL service in Railway
2. Copy connection string to `DATABASE_URL`
3. Run initialization script

### Option 2: Supabase

1. Create project at [Supabase](https://supabase.com)
2. Get connection string from Settings > Database
3. Set as `DATABASE_URL`

### Option 3: Local PostgreSQL

```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt install postgresql  # Ubuntu

# Create database
createdb scheduly
```

## 🧪 Testing Your Deployment

### 1. Backend Health Check

```bash
curl https://your-backend.railway.app/health
```

### 2. Frontend Access

Visit your Vercel domain and test:

- [ ] Sign up/login with Auth0
- [ ] Create a schedule
- [ ] Save schedule to history
- [ ] Load previous schedules
- [ ] Delete schedules

### 3. Database Verification

```bash
# Run the test script
python scripts/test_setup.py
```

## 🔒 Security Checklist

- [ ] Auth0 JWT validation working
- [ ] User data isolation verified
- [ ] HTTPS enabled on all domains
- [ ] Environment variables secured
- [ ] Database connection encrypted
- [ ] CORS properly configured

## 📊 Monitoring & Analytics

### Railway Monitoring

- View logs in Railway dashboard
- Monitor database connections
- Set up alerts for errors

### Vercel Analytics

- Enable Vercel Analytics
- Monitor performance metrics
- Track user interactions

## 🚨 Troubleshooting

### Common Issues

**1. Auth0 Redirect Issues**

- Check callback URLs in Auth0 dashboard
- Verify `AUTH0_BASE_URL` matches your domain
- Ensure HTTPS is enabled

**2. Database Connection Issues**

- Verify `DATABASE_URL` format
- Check database is accessible
- Run database initialization script

**3. CORS Issues**

- Check backend CORS configuration
- Verify frontend API URL
- Test with browser dev tools

**4. JWT Validation Issues**

- Verify `AUTH0_DOMAIN` and `AUTH0_AUDIENCE`
- Check token format in browser
- Test with Postman/curl

### Debug Commands

```bash
# Test backend locally
cd backend
uvicorn app:app --reload --port 8000

# Test frontend locally
cd frontend
npm run dev

# Check database
python scripts/test_setup.py

# View logs
railway logs
vercel logs
```

## 🎯 Performance Optimization

### Backend

- Enable database connection pooling
- Add Redis caching for sessions
- Implement rate limiting
- Add request logging

### Frontend

- Enable Next.js optimizations
- Add image optimization
- Implement code splitting
- Add service worker caching

## 📈 Scaling Considerations

### Database

- Set up read replicas
- Implement connection pooling
- Add database monitoring
- Plan for backup strategy

### Application

- Use CDN for static assets
- Implement horizontal scaling
- Add load balancing
- Monitor resource usage

## 🎉 Success!

Your Scheduly application is now deployed with:

- ✅ OAuth authentication
- ✅ User management
- ✅ Schedule history
- ✅ PostgreSQL database
- ✅ Production-ready security

Users can now:

- Sign up with Google/GitHub
- Create and save schedules
- Access their schedule history
- Manage their account

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section
2. Review Railway/Vercel logs
3. Test with the provided scripts
4. Verify Auth0 configuration

Happy scheduling! 🚀

