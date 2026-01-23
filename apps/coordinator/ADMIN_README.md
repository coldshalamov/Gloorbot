# Gloorbot Admin Interface

## Overview

The Gloorbot Admin Interface allows you to easily configure which stores to scrape by selecting different regions (states) and specific stores. This configuration works for both:

1. **Local Worker** - The Windows installer that runs on your machine
2. **Render Deployment** - The web-based coordinator

## Features

✅ **Simple Login** - Secure admin access with your credentials  
✅ **Region Selection** - Choose states (WA, OR, FL, etc.)  
✅ **Store Selection** - Pick specific stores or scrape all in a region  
✅ **Live Configuration** - Changes apply immediately to both local and cloud workers  
✅ **Beautiful UI** - Modern, responsive design with smooth animations  

## Access

### Login Credentials
Admin credentials are configured via environment variables:
- `GLOORBOT_ADMIN_EMAIL`
- `GLOORBOT_ADMIN_PASSWORD`

### URLs

**Local Development:**
```
http://localhost:8000/admin/login
```

**Render Production:**
```
https://your-app-name.onrender.com/admin/login
```

## How to Use

### 1. Login
1. Navigate to `/admin/login`
2. Enter your credentials
3. Click "Sign In"

### 2. Select Regions
1. On the dashboard, you'll see cards for each available state
2. Click on a state card to enable/disable it
3. Selected states will be highlighted with a gradient background

**Available States:**
- 🌲 **Washington** (35 stores)
- 🏔️ **Oregon** (14 stores)
- 🌴 **Florida** (76 stores)

### 3. Select Specific Stores (Optional)
1. After selecting states, a store list will appear
2. Check individual stores to scrape only those
3. Leave all unchecked to scrape ALL stores in selected states
4. Use "Select/Deselect All" for quick selection

### 4. Save Configuration
1. Click the green "Save Configuration" button
2. The system will:
   - Generate a new `urls.txt` file
   - Update the PARALLEL folder configuration
   - Re-seed tasks in the coordinator database
   - Apply changes to all connected workers

### 5. Reset to Default
- Click "Reset to Default" to restore WA/OR configuration

## How It Works

### Configuration Flow

```
Admin Dashboard
    ↓
Save Configuration
    ↓
Generate urls.txt
    ↓
Update PARALLEL/urls.txt ← Used by GitHub Actions
    ↓
Update coordinator database ← Used by Render deployment
    ↓
Workers pick up new tasks
```

### File Locations

**PARALLEL/urls.txt**
- Used by the local worker and GitHub Actions builds
- Contains store URLs and category URLs
- Auto-generated from your selections

**apps/coordinator/data/store_config.json**
- Stores your configuration preferences
- Persists across restarts
- JSON format for easy editing if needed

**apps/coordinator/data/urls.txt**
- Backup copy for the coordinator
- Used when re-seeding tasks

## Architecture

### Components

1. **admin_auth.py** - Session-based authentication
2. **store_config.py** - Store configuration management
3. **admin_login.html** - Beautiful login page
4. **admin_dashboard.html** - Interactive configuration UI
5. **web.py** - Admin API endpoints

### API Endpoints

```
POST /admin/api/login
  - Authenticate and get session token

GET /admin/api/config
  - Get current configuration
  - Requires: Bearer token

POST /admin/api/config
  - Save new configuration
  - Requires: Bearer token
  - Body: { enabled_states: [], enabled_stores: [] }

POST /admin/api/config/reset
  - Reset to default (WA/OR)
  - Requires: Bearer token

POST /admin/api/logout
  - Invalidate session
```

## Example: Switching to Florida

1. Login to admin dashboard
2. Click on the Florida (🌴) state card
3. Optionally select specific stores (e.g., only Miami, Tampa, Orlando)
4. Click "Save Configuration"
5. Workers will now scrape Florida stores instead of WA/OR

## Local Worker Integration

The local worker reads from `PARALLEL/urls.txt`, which is automatically updated when you save your configuration. If you have the worker running:

1. The worker will finish its current tasks
2. On the next task request, it will get tasks from the new stores
3. No restart required!

## Render Deployment Integration

The Render deployment uses the coordinator database, which is automatically re-seeded when you save configuration. Changes apply immediately to all connected workers.

## Security

- Session tokens expire after 24 hours
- Passwords are verified server-side
- Admin endpoints require Bearer token authentication
- Sessions stored in-memory (use Redis for production scale)

## Troubleshooting

### Can't Login
- Verify credentials are correct
- Check browser console for errors
- Ensure coordinator is running

### Configuration Not Saving
- Check coordinator logs for errors
- Verify file permissions on PARALLEL folder
- Ensure database is writable

### Workers Not Picking Up New Stores
- Wait for current tasks to complete
- Check coordinator `/api/v1/status` endpoint
- Verify urls.txt was updated

## Future Enhancements

- [ ] Category selection (currently scrapes all categories)
- [ ] Schedule-based configuration (different stores at different times)
- [ ] Multi-user support with different permission levels
- [ ] Configuration history and rollback
- [ ] Store performance analytics

## Support

For issues or questions, check the coordinator logs:
```bash
# Local
tail -f apps/coordinator/coordinator.log

# Render
View logs in Render dashboard
```

---

**Made with ❤️ for efficient deal hunting across all Lowe's locations**
