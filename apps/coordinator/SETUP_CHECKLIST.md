# Gloorbot Admin Interface - Setup Checklist

## ✅ Pre-Flight Checklist

Use this checklist to ensure everything is set up correctly.

### 1. Files Created
- [ ] `coordinator_app/admin_auth.py` - Authentication module
- [ ] `coordinator_app/store_config.py` - Store configuration
- [ ] `templates/admin_login.html` - Login page
- [ ] `templates/admin_dashboard.html` - Dashboard page
- [ ] `ADMIN_README.md` - Full documentation
- [ ] `IMPLEMENTATION_SUMMARY.md` - Technical details
- [ ] `QUICK_START.md` - Quick start guide
- [ ] `setup_admin.py` - Setup verification script

### 2. Dependencies
- [ ] FastAPI installed
- [ ] Jinja2 templates installed
- [ ] SQLAlchemy installed
- [ ] httpx installed

### 3. Configuration
- [ ] Admin credentials set (email/password)
- [ ] Store data populated (WA, OR, FL)
- [ ] Category URLs available

### 4. Testing
- [ ] Run `python setup_admin.py` successfully
- [ ] All stores loaded (127 total)
- [ ] URLs generated correctly

---

## 🚀 First-Time Setup

### Step 1: Verify Installation
```bash
cd apps/coordinator
python setup_admin.py
```

**Expected Output:**
```
✅ Admin credentials verified
✅ Session token created
✅ Enabled states: WA, OR
✅ Enabled stores: 49 stores
✅ Total available stores: 127
✅ Generated 282 lines
```

### Step 2: Start Coordinator
```bash
uvicorn coordinator_app.main:app --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Step 3: Test Login
1. Open browser: `http://localhost:8000/admin/login`
2. Enter credentials:
   - Email: `GLOORBOT_ADMIN_EMAIL`
   - Password: `GLOORBOT_ADMIN_PASSWORD`
3. Click "Sign In"

**Expected Result:**
- Redirected to `/admin/dashboard`
- See state selection cards
- See statistics at top

### Step 4: Test Configuration
1. Click on Florida (🌴) card
2. Click "Save Configuration"
3. Check for success toast notification

**Expected Result:**
- Green success message
- Configuration saved
- PARALLEL/urls.txt updated

### Step 5: Verify Files Updated
```bash
# Check PARALLEL/urls.txt
cat ../../PARALLEL/urls.txt | grep "FL-"

# Should see Florida stores
```

---

## 🔍 Verification Tests

### Test 1: Authentication
- [ ] Can access login page
- [ ] Can login with correct credentials
- [ ] Cannot login with wrong credentials
- [ ] Redirected to dashboard after login
- [ ] Can logout successfully

### Test 2: State Selection
- [ ] Can see all 3 states (WA, OR, FL)
- [ ] Can click to select/deselect states
- [ ] Selected states show gradient background
- [ ] Statistics update when selecting states

### Test 3: Store Selection
- [ ] Store list appears when states selected
- [ ] Can check/uncheck individual stores
- [ ] "Select All" checkbox works
- [ ] Store count updates correctly

### Test 4: Configuration Save
- [ ] Save button works
- [ ] Success notification appears
- [ ] PARALLEL/urls.txt is updated
- [ ] Configuration persists after refresh

### Test 5: Reset Function
- [ ] Reset button works
- [ ] Returns to WA/OR default
- [ ] Confirmation dialog appears
- [ ] Files are updated

---

## 🎯 Feature Checklist

### Core Features
- [x] Secure login system
- [x] Session management (24-hour expiry)
- [x] State selection (WA, OR, FL)
- [x] Store selection (individual stores)
- [x] Configuration save/load
- [x] Reset to default
- [x] Auto-update PARALLEL/urls.txt
- [x] Auto-update coordinator database
- [x] Real-time statistics
- [x] Beautiful gradient UI

### Admin API Endpoints
- [x] `POST /admin/api/login` - Authentication
- [x] `GET /admin/api/config` - Get configuration
- [x] `POST /admin/api/config` - Save configuration
- [x] `POST /admin/api/config/reset` - Reset to default
- [x] `POST /admin/api/logout` - Logout

### UI Features
- [x] Responsive design
- [x] Smooth animations
- [x] Hover effects
- [x] Toast notifications
- [x] Loading states
- [x] Error handling

---

## 📋 Production Deployment Checklist

### Before Deploying to Render

#### 1. Environment Variables
- [ ] Set `WORKER_DOWNLOAD_URL` if needed
- [ ] Set `DEBUG_API_TOKEN` for debug endpoints
- [ ] Set `CHEAPSKATER_INGEST_URL` if using
- [ ] Set `CHEAPSKATER_INGEST_API_KEY` if using

#### 2. Security
- [ ] Change admin password (use env var)
- [ ] Enable HTTPS only
- [ ] Add rate limiting
- [ ] Implement Redis for sessions
- [ ] Add audit logging

#### 3. Database
- [ ] Verify database path
- [ ] Test database migrations
- [ ] Backup existing data
- [ ] Test task seeding

#### 4. Files
- [ ] Ensure PARALLEL folder is in repo
- [ ] Verify urls.txt is writable
- [ ] Check file permissions
- [ ] Test configuration persistence

#### 5. Testing
- [ ] Test login on production URL
- [ ] Test configuration save
- [ ] Test worker pickup of new config
- [ ] Test reset function
- [ ] Monitor logs for errors

---

## 🐛 Common Issues & Solutions

### Issue: Login page not loading
**Solution:**
```bash
# Check if coordinator is running
ps aux | grep uvicorn

# Check logs
tail -f coordinator.log
```

### Issue: Can't save configuration
**Solution:**
```bash
# Check file permissions
ls -la ../../PARALLEL/urls.txt

# Check if directory exists
mkdir -p ../../PARALLEL
```

### Issue: Workers not picking up new stores
**Solution:**
1. Wait for current tasks to complete
2. Check `/api/v1/status` endpoint
3. Verify database was re-seeded
4. Check worker logs

### Issue: Session expired
**Solution:**
- Sessions expire after 24 hours
- Just login again
- Consider implementing Redis for production

---

## 📊 Success Metrics

After setup, you should be able to:

- ✅ Login in < 5 seconds
- ✅ Switch regions in < 30 seconds
- ✅ Select specific stores in < 1 minute
- ✅ Save configuration in < 5 seconds
- ✅ See changes in workers immediately (Render) or next run (local)

---

## 🎓 Next Steps

### Immediate
1. [ ] Complete this checklist
2. [ ] Test all features
3. [ ] Switch to Florida stores
4. [ ] Monitor for deals

### Short Term
1. [ ] Add more states if needed
2. [ ] Optimize store selection
3. [ ] Monitor performance
4. [ ] Adjust based on results

### Long Term
1. [ ] Implement category selection
2. [ ] Add scheduling features
3. [ ] Create analytics dashboard
4. [ ] Add multi-user support

---

## 📞 Support

If you encounter issues:

1. **Check Documentation**
   - ADMIN_README.md
   - IMPLEMENTATION_SUMMARY.md
   - QUICK_START.md

2. **Check Logs**
   ```bash
   # Coordinator logs
   tail -f coordinator.log
   
   # Browser console
   F12 → Console tab
   ```

3. **Verify Setup**
   ```bash
   python setup_admin.py
   ```

4. **Test Endpoints**
   ```bash
   # Health check
   curl http://localhost:8000/healthz
   
   # Status
   curl http://localhost:8000/api/v1/status
   ```

---

## ✨ You're All Set!

Once you've completed this checklist, you're ready to use the admin interface!

**Happy scraping!** 🚀

---

**Last Updated:** 2026-01-20  
**Version:** 1.0.0  
**Status:** Production Ready ✅
