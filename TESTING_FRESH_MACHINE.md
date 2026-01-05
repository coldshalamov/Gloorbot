# Testing Worker on Fresh Machine

## ✅ What the Worker Bundles

The worker installer is **self-contained** and includes:

1. **Python Runtime**: PyInstaller bundles Python interpreter
2. **All Python Dependencies**: `playwright`, `httpx`, `requests`, etc.
3. **Playwright Chromium Browser**: Bundled in `_internal/ms-playwright/`
4. **PARALLEL Scraper Code**: Bundled in `_internal/PARALLEL/`

## 🧪 How to Test on Fresh Machine

### Option 1: Windows Sandbox (RECOMMENDED)

Windows Sandbox creates a completely isolated, temporary Windows environment:

```powershell
# 1. Enable Windows Sandbox (requires Windows 10/11 Pro)
# Settings → Apps → Optional Features → Add Feature → Windows Sandbox

# 2. Start Windows Sandbox
# Start Menu → Windows Sandbox

# 3. Copy the installer into the sandbox
# Drag and drop WorkerSetup.exe into the Sandbox window

# 4. Run the installer in the sandbox
# Double-click WorkerSetup.exe

# 5. Launch GloorbotWorker
# Start Menu → Gloorbot Worker

# 6. Watch it run - it should work without any dependencies!
```

**Pros**:
- ✅ Completely clean Windows environment
- ✅ No Chrome, no Python, no dependencies
- ✅ Resets on close (no cleanup needed)
- ✅ Safe - can't affect your main system

**Cons**:
- ❌ Requires Windows 10/11 Pro (not Home)
- ❌ Requires virtualization enabled in BIOS

### Option 2: Virtual Machine

Use VirtualBox or VMware with a fresh Windows ISO:

```powershell
# 1. Download Windows 10/11 ISO from Microsoft
# https://www.microsoft.com/software-download/windows10

# 2. Create VM in VirtualBox/VMware
# - 4GB RAM minimum
# - 50GB disk

# 3. Install Windows (no additional software)

# 4. Copy WorkerSetup.exe to VM

# 5. Run installer and test
```

**Pros**:
- ✅ Works on any Windows edition
- ✅ Can save snapshots
- ✅ Persistent for repeated testing

**Cons**:
- ❌ Requires VM software
- ❌ Slower than Sandbox
- ❌ Uses more disk space

### Option 3: Clean User Profile (Quick Test)

Create a new Windows user account:

```powershell
# 1. Create new local user
Settings → Accounts → Family & other users → Add someone else to this PC

# 2. Switch to new user

# 3. Copy and run WorkerSetup.exe

# 4. Test the worker
```

**Pros**:
- ✅ Quick and easy
- ✅ No VM required
- ✅ Works on any Windows

**Cons**:
- ⚠️ Still has system-level dependencies (if any)
- ⚠️ Not as isolated as Sandbox/VM

## 🔍 What to Check

When testing, verify:

### 1. Installation
- [ ] Installer runs without errors
- [ ] Creates Start Menu shortcut
- [ ] Installs to Program Files

### 2. First Launch
- [ ] GUI opens without errors
- [ ] No "missing DLL" or "Python not found" errors
- [ ] Shows coordinator connection status

### 3. Browser Launch
- [ ] Worker can launch browser
- [ ] Browser is Chromium (not Chrome)
- [ ] No "browser not found" errors

### 4. Scraping
- [ ] Can connect to coordinator
- [ ] Can lease a task
- [ ] Can navigate to Lowe's
- [ ] Can scrape products

## 🐛 Common Issues on Fresh Machines

### Issue: "VCRUNTIME140.dll not found"
**Cause**: Missing Visual C++ Redistributable  
**Fix**: Installer should bundle it, or download from Microsoft

### Issue: "Browser not found"
**Cause**: Bundled Chromium not detected  
**Fix**: Check `_internal/ms-playwright/` exists in install dir

### Issue: "Python not found"
**Cause**: PyInstaller didn't bundle Python properly  
**Fix**: Rebuild with `--onefile` or check build logs

## 📋 Pre-Flight Checklist

Before distributing to users:

- [ ] Test in Windows Sandbox (clean environment)
- [ ] Test on Windows 10 and Windows 11
- [ ] Test with no Chrome installed
- [ ] Test with no Python installed
- [ ] Test with no internet during install (offline install)
- [ ] Test uninstall and reinstall
- [ ] Check installer size (should be ~220MB with Chromium)
- [ ] Verify digital signature (if signed)

## 🎯 Current Status

Based on the code:

✅ **Should work on fresh machine** because:
- PyInstaller bundles Python runtime
- Build script bundles Playwright Chromium (`build.ps1` line 24)
- Worker auto-detects bundled browser (`slot_worker.py` lines 229-238)
- No external dependencies required

⚠️ **Potential issues**:
- Visual C++ Runtime might be needed (Windows usually has it)
- Antivirus might block unsigned exe
- Firewall might block network access

## 🚀 Recommended Test Script

```powershell
# Run this in Windows Sandbox to verify everything works

# 1. Install
Start-Process "WorkerSetup.exe" -Wait -ArgumentList "/SILENT"

# 2. Check installation
Test-Path "C:\\Program Files\\Gloorbot Worker\\GloorbotWorker.exe"

# 3. Launch worker
Start-Process "C:\\Program Files\\Gloorbot Worker\\GloorbotWorker.exe"

# 4. Wait and check if it's running
Start-Sleep -Seconds 30
Get-Process -Name "GloorbotWorker" -ErrorAction SilentlyContinue

# 5. Check logs
Get-Content "$env:LOCALAPPDATA\\GloorbotWorkerData\\logs\\*.log" -Tail 50
```

## 💡 Recommendation

**Test in Windows Sandbox first** - it's the fastest way to verify the worker is truly self-contained and works on a fresh machine with zero dependencies.

If you don't have Windows Pro, I can help you create a test script that simulates a fresh environment by temporarily hiding system dependencies.
