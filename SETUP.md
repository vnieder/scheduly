# Scheduly Setup Guide

This guide will help you set up the complete Scheduly application with OAuth authentication, user management, and schedule history using Auth0 and PostgreSQL.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- PostgreSQL database
- Auth0 account

### 1. Backend Setup

#### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
pip install sqlalchemy psycopg2-binary cryptography pyjwt requests
```

#### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/scheduly

# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=your-api-identifier

# Existing Configuration
APP_MODE=development
GEMINI_API_KEY=your_gemini_api_key_here
```

#### Initialize Database

```bash
cd backend
python scripts/init_database.py
```

#### Start Backend Server

```bash
cd backend
uvicorn app:app --reload --port 8000
```

### 2. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Environment Variables

Create a `.env.local` file in the frontend directory:

```bash
# Auth0 Configuration
AUTH0_SECRET='use [openssl rand -hex 32] to generate a 32 bytes value'
AUTH0_BASE_URL='http://localhost:3000'
AUTH0_ISSUER_BASE_URL='https://your-tenant.auth0.com'
AUTH0_CLIENT_ID='your-client-id'
AUTH0_CLIENT_SECRET='your-client-secret'

# Backend API URL
NEXT_PUBLIC_API_URL='http://localhost:8000'
```

#### Start Frontend Server

```bash
cd frontend
npm run dev
```

## 🔧 Auth0 Configuration

### 1. Create Auth0 Application

1. Go to [Auth0 Dashboard](https://manage.auth0.com/)
2. Create a new Application
3. Choose "Regular Web Applications"
4. Configure the following settings:

**Application Settings:**

- Allowed Callback URLs: `http://localhost:3000/api/auth/callback`
- Allowed Logout URLs: `http://localhost:3000`
- Allowed Web Origins: `http://localhost:3000`

### 2. Configure Social Connections

1. Go to Authentication > Social
2. Enable Google and GitHub connections
3. Configure OAuth credentials for each provider

### 3. Create API

1. Go to Applications > APIs
2. Create a new API
3. Set Identifier (this is your `AUTH0_AUDIENCE`)
4. Configure scopes if needed

### 4. Configure Rules (Optional)

Create a rule to add custom claims to the JWT token:

```javascript
function addUserMetadata(user, context, callback) {
  const namespace = "https://scheduly.com/";
  context.idToken[namespace + "user_metadata"] = user.user_metadata;
  context.accessToken[namespace + "user_metadata"] = user.user_metadata;
  callback(null, user, context);
}
```

## 🗄️ Database Setup

### PostgreSQL Setup

1. Install PostgreSQL
2. Create a database:

```sql
CREATE DATABASE scheduly;
CREATE USER scheduly_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE scheduly TO scheduly_user;
```

### Database Schema

The application will automatically create these tables:

- `users` - User accounts linked to Auth0
- `schedule_history` - Saved user schedules

## 🎯 Features Implemented

### ✅ Authentication & User Management

- Auth0 OAuth integration with Google/GitHub
- JWT token validation in backend
- User profile management
- Secure API endpoints

### ✅ Schedule Management

- Save schedules to PostgreSQL
- Load previous schedules
- Schedule history with metadata
- Favorite schedules
- Schedule deletion and updates

### ✅ Frontend Features

- Clean signup/login page
- History sidebar in schedule view
- User authentication state management
- Responsive design with animations

### ✅ Backend API Endpoints

**Authentication Required:**

- `POST /schedules` - Save a schedule
- `GET /schedules` - Get user's schedule history
- `GET /schedules/{id}` - Get specific schedule
- `PUT /schedules/{id}` - Update schedule
- `DELETE /schedules/{id}` - Delete schedule
- `GET /user/profile` - Get user profile

## 🔒 Security Features

- JWT token validation
- User isolation (users can only access their own schedules)
- Secure database connections
- CORS configuration
- Input validation and sanitization

## 🚀 Deployment

### Railway Deployment

1. **Backend:**

   - Connect your GitHub repository
   - Set environment variables in Railway dashboard
   - Deploy automatically

2. **Frontend:**
   - Deploy to Vercel or similar
   - Update `AUTH0_BASE_URL` to production URL
   - Update `NEXT_PUBLIC_API_URL` to production backend URL

### Environment Variables for Production

**Backend:**

```bash
DATABASE_URL=postgresql://user:password@host:port/db
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=your-api-identifier
APP_MODE=production
GEMINI_API_KEY=your_gemini_api_key
```

**Frontend:**

```bash
AUTH0_SECRET=your-secret-key
AUTH0_BASE_URL=https://your-domain.com
AUTH0_ISSUER_BASE_URL=https://your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Issues:**

   - Verify DATABASE_URL format
   - Check PostgreSQL is running
   - Ensure database exists

2. **Auth0 Issues:**

   - Verify all environment variables
   - Check callback URLs in Auth0 dashboard
   - Ensure JWT audience matches

3. **CORS Issues:**
   - Verify backend CORS configuration
   - Check frontend API URL

### Debug Mode

Enable debug logging:

```bash
# Backend
export LOG_LEVEL=DEBUG
uvicorn app:app --reload --port 8000

# Frontend
npm run dev
```

## 📚 API Documentation

Once running, visit:

- Backend API: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

## 🎉 You're Ready!

Your Scheduly application now has:

- ✅ OAuth authentication with Auth0
- ✅ User management and profiles
- ✅ Schedule history and storage
- ✅ Beautiful UI with animations
- ✅ Secure API endpoints
- ✅ PostgreSQL database integration

Start building your dream schedules! 🚀

