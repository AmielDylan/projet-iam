# Deployment Guide - Railway

This guide explains how to deploy Projet IAM to Railway.

## Prerequisites

- GitHub account (to host your code)
- Railway account (free at [railway.app](https://railway.app))
- Your local MySQL database with data

## Step 1: Export Your Database

Run the export script to create a backup of your database:

```bash
./scripts/export_database.sh
```

This creates `database_export.sql` with all your data.

## Step 2: Push Code to GitHub

```bash
git init  # if not already a git repo
git add .
git commit -m "Prepare for Railway deployment"
git remote add origin https://github.com/YOUR_USERNAME/projet-iam.git
git push -u origin main
```

## Step 3: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `projet-iam` repository
5. Railway will auto-detect it's a Python app

## Step 4: Add MySQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"MySQL"**
3. Railway creates a MySQL instance automatically

## Step 5: Import Your Data

1. Click on the MySQL service in Railway
2. Go to **"Data"** tab
3. Click **"Import"** and upload your `database_export.sql`

Or use the Railway CLI:
```bash
railway link  # connect to your project
railway run mysql -h $MYSQLHOST -u $MYSQLUSER -p$MYSQLPASSWORD $MYSQLDATABASE < database_export.sql
```

## Step 6: Set Environment Variables

In Railway, click on your web service and go to **"Variables"**:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | (generate a random string) |
| `FLASK_ENV` | `production` |

The MySQL variables (`MYSQLHOST`, `MYSQLUSER`, etc.) are automatically shared from the MySQL service.

### Generate a Secret Key

```python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Step 7: Deploy

Railway deploys automatically when you push to GitHub. Check the **"Deployments"** tab for logs.

## Step 8: Access Your App

1. Go to **"Settings"** → **"Networking"**
2. Click **"Generate Domain"**
3. Your app is now live at `https://your-app.up.railway.app`

## Troubleshooting

### Database Connection Issues
- Ensure the MySQL service is running
- Check that variables are shared: Click MySQL → **"Variables"** → **"Share"** with your web service

### App Won't Start
- Check deployment logs for errors
- Verify all environment variables are set
- Ensure `gunicorn` is in requirements.txt

### Migrations
Run the SQL migrations on Railway MySQL:
```bash
railway run mysql -h $MYSQLHOST -u $MYSQLUSER -p$MYSQLPASSWORD $MYSQLDATABASE < migrations/003_fix_boolean_functions.sql
```

## Costs

Railway free tier includes:
- $5 credit/month
- Enough for small apps with low traffic
- MySQL included

For higher traffic, upgrade to paid plan (~$5-20/month).

## Alternative: Custom Domain

1. Go to **"Settings"** → **"Networking"**
2. Add your custom domain
3. Update DNS records as shown
