# Scheduly CORS Proxy

This is a CORS proxy service to bypass Railway's platform-level CORS restrictions.

## Deployment

1. Deploy this to Railway as a new project
2. Get the Railway URL (e.g., `https://scheduly-cors-proxy-production.railway.app`)
3. Update your frontend to use this proxy URL

## Usage

Instead of calling:

```
https://scheduly-backend-production.railway.app/build
```

Call:

```
https://scheduly-cors-proxy-production.railway.app/https://scheduly-backend-production.railway.app/build
```

The CORS proxy will add the necessary CORS headers to bypass browser restrictions.
