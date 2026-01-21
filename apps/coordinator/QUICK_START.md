# Gloorbot Admin Interface - Quick Start Guide

## 🚀 Quick Start (3 Steps)

### Step 1: Start the Coordinator
```bash
cd apps/coordinator
uvicorn coordinator_app.main:app --reload
```

### Step 2: Open Admin Interface
Navigate to: **http://localhost:8000/admin/login**

### Step 3: Login
- **Email**: `93robingattis@gmail.com`
- **Password**: `Alphonse5150$`

---

## 📸 What You'll See

### Login Page
```
┌─────────────────────────────────────┐
│                                     │
│          🤖 Gloorbot                │
│          Admin Access               │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Email Address                 │ │
│  │ [93robingattis@gmail.com]     │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Password                      │ │
│  │ [••••••••••••]                │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │        Sign In                │ │
│  └───────────────────────────────┘ │
│                                     │
│      ← Back to Dashboard            │
└─────────────────────────────────────┘
```

### Admin Dashboard
```
┌────────────────────────────────────────────────────────────┐
│  🤖 Gloorbot Admin              [Dashboard] [Logout]       │
└────────────────────────────────────────────────────────────┘

┌──────────┐  ┌──────────┐  ┌──────────┐
│    2     │  │   49     │  │   225    │
│  States  │  │  Stores  │  │Categories│
│ Selected │  │ Selected │  │          │
└──────────┘  └──────────┘  └──────────┘

┌────────────────────────────────────────────────────────────┐
│  Select Regions to Scrape                                  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │    🌲    │  │    🏔️    │  │    🌴    │                │
│  │Washington│  │  Oregon  │  │  Florida │                │
│  │ 35 stores│  │ 14 stores│  │ 78 stores│                │
│  └──────────┘  └──────────┘  └──────────┘                │
│   (selected)    (selected)    (click me!)                 │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Select Specific Stores (Optional)                         │
│  Leave all unchecked to scrape all stores in selected      │
│  states                                                     │
│                                                             │
│  [✓] Select/Deselect All                                   │
│                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │☑ Arlington, WA │  │☑ Auburn, WA    │  │☑ Bellingham, │││
│  │   (#0061)      │  │   (#1089)      │  │   WA (#1631) │││
│  └────────────────┘  └────────────────┘  └──────────────┘│
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │☑ Albany, OR    │  │☑ Bend, OR      │  │☑ Eugene, OR  │││
│  │   (#3057)      │  │   (#1690)      │  │   (#2940)    │││
│  └────────────────┘  └────────────────┘  └──────────────┘│
│  ... (scrollable list)                                     │
└────────────────────────────────────────────────────────────┘

                    [Reset to Default] [Save Configuration]
```

---

## 🎯 Common Use Cases

### Use Case 1: Switch to Florida Only
1. Login to admin
2. **Uncheck** Washington and Oregon cards
3. **Click** Florida card
4. Click "Save Configuration"
5. ✅ Now scraping 78 Florida stores!

### Use Case 2: Scrape Specific Cities
1. Login to admin
2. Click Florida card
3. Scroll down to store list
4. **Uncheck** "Select All"
5. **Check** only Miami, Tampa, Orlando stores
6. Click "Save Configuration"
7. ✅ Now scraping only your selected cities!

### Use Case 3: Add More States
1. Click multiple state cards (WA + OR + FL)
2. Click "Save Configuration"
3. ✅ Now scraping all selected states!

---

## 🔧 What Happens When You Save

```
You Click "Save Configuration"
         ↓
┌────────────────────────────┐
│ System Updates:            │
│ ✅ PARALLEL/urls.txt       │
│ ✅ Coordinator database    │
│ ✅ Configuration file      │
│ ✅ Task queue re-seeded    │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ Workers Pick Up Changes:   │
│ 🖥️  Local Worker (next run)│
│ ☁️  Render Workers (now)   │
└────────────────────────────┘
         ↓
┌────────────────────────────┐
│ Result:                    │
│ 🎉 Scraping new stores!    │
└────────────────────────────┘
```

---

## 📊 Statistics Display

The dashboard shows real-time stats:

- **States Selected**: How many states you've chosen
- **Stores Selected**: Total stores (or specific selection)
- **Categories**: Always 225 (all product categories)

---

## 🎨 Design Features

### Beautiful Gradient UI
- Purple/violet gradient theme
- Smooth animations
- Responsive design
- Modern card-based layout

### Interactive Elements
- Hover effects on all cards
- Click to select/deselect
- Visual feedback (selected = gradient background)
- Toast notifications for actions

### User-Friendly
- Clear labels and instructions
- Intuitive controls
- No technical knowledge required
- Instant visual feedback

---

## 🔐 Security

- ✅ Login required for all admin functions
- ✅ Session tokens expire after 24 hours
- ✅ Protected API endpoints
- ✅ No plain-text password storage

---

## 🐛 Troubleshooting

### Can't Access Admin Page
```bash
# Make sure coordinator is running:
cd apps/coordinator
uvicorn coordinator_app.main:app --reload

# Then visit:
http://localhost:8000/admin/login
```

### Login Not Working
- Double-check email and password
- Check browser console (F12) for errors
- Verify coordinator is running

### Changes Not Applying
- Wait for current tasks to complete
- Check coordinator logs
- Verify PARALLEL/urls.txt was updated

---

## 📝 Example Workflow

### Scenario: Test Florida Stores for a Week

**Monday:**
```
1. Login to admin
2. Select Florida only
3. Save configuration
4. Workers start scraping FL stores
```

**Throughout Week:**
```
- Monitor deals at http://localhost:8000
- Check which FL stores have best deals
- Adjust store selection if needed
```

**Next Monday:**
```
1. Login to admin
2. Click "Reset to Default"
3. Back to WA/OR stores
```

---

## 🎓 Pro Tips

### Tip 1: Test Small First
Start with just a few stores to test:
1. Select one state
2. Choose 3-5 stores
3. Save and monitor
4. Expand if working well

### Tip 2: Use Store Stats
After running for a while:
- Check which stores have most deals
- Focus on high-performing stores
- Remove low-performing ones

### Tip 3: Schedule Changes
- Morning: Scrape local stores
- Evening: Scrape different region
- Weekend: Scrape all stores

---

## 📞 Need Help?

Check these resources:
1. **ADMIN_README.md** - Full documentation
2. **IMPLEMENTATION_SUMMARY.md** - Technical details
3. **Coordinator logs** - Error messages
4. **Browser console** - Frontend errors

---

## ✨ Enjoy Your New Admin Interface!

You can now easily manage your scraper configuration without touching any code files. Switch regions, select stores, and watch the deals roll in! 🎉

**Happy Deal Hunting!** 🛒💰
