# merge-jules-prs.ps1
# This script finds and merges all open Pull Requests created by Jules AI.
# Requirements: GitHub CLI (gh) must be installed and authenticated.

echo "Checking for Jules PRs..."

# 1. Find PRs that match Jules criteria (Author, Title, or Branch name contains "jules")
$prsJson = gh pr list --state open --json number,title,author,headRefName | ConvertFrom-Json

$julesPrs = $prsJson | Where-Object {
    ($_.author.login -like "*jules*") -or 
    ($_.title -like "*Jules*") -or 
    ($_.headRefName -like "*jules*")
}

if (-not $julesPrs) {
    Write-Host "No matching Jules PRs found." -ForegroundColor Yellow
    exit
}

foreach ($pr in $julesPrs) {
    $prNumber = $pr.number
    Write-Host "Processing PR #$prNumber : $($pr.title)" -ForegroundColor Cyan
    
    # 2. Check if it's a draft
    $prDetails = gh pr view $prNumber --json isDraft | ConvertFrom-Json
    if ($prDetails.isDraft) {
        Write-Host "PR #$prNumber is a draft. Marking as ready for review..."
        gh pr ready $prNumber
    }
    
    # 3. Attempt to merge
    Write-Host "Merging PR #$prNumber..." -ForegroundColor Green
    
    # Try merging with --auto (waits for checks) and --merge (standard merge)
    # We also use --delete-branch to keep things clean.
    gh pr merge $prNumber --merge --delete-branch --auto
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Auto-merge failed or not available. Attempting immediate merge..." -ForegroundColor Magenta
        gh pr merge $prNumber --merge --delete-branch
    }
}

Write-Host "Done!" -ForegroundColor Green
