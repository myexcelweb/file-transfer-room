# push.ps1
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "    FILE TRANSFER ROOM - GIT PUSH UTILITY" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Check git status
Write-Host "[1/4] Current git status:" -ForegroundColor Green
git status --short
Write-Host ""

# Add all changes
Write-Host "[2/4] Adding changes..." -ForegroundColor Green
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to add changes" -ForegroundColor Red
    pause
    exit
}
Write-Host "[OK] Changes added" -ForegroundColor Green
Write-Host ""

# Check if there are changes to commit
$changes = git diff --cached --name-only
if ($changes) {
    # Commit changes
    Write-Host "[3/4] Committing changes..." -ForegroundColor Green
    $commit_msg = Read-Host "Enter commit message (or press Enter for auto)"
    if ([string]::IsNullOrWhiteSpace($commit_msg)) {
        $commit_msg = "Update File Transfer Room $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    }
    git commit -m "$commit_msg"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to commit" -ForegroundColor Red
        pause
        exit
    }
    Write-Host "[OK] Changes committed" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[OK] No changes to commit" -ForegroundColor Green
    Write-Host ""
}

# Push to GitHub
Write-Host "[4/4] Pushing to GitHub..." -ForegroundColor Green
Write-Host ""
Write-Host "Repository: https://github.com/myexcelweb/file-transfer-room.git" -ForegroundColor Yellow
Write-Host "Branch: master" -ForegroundColor Yellow
Write-Host ""

git push origin master
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Push completed!" -ForegroundColor Green
    Write-Host "Your code is now on GitHub" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Push failed" -ForegroundColor Red
    Write-Host "Trying to pull first..." -ForegroundColor Yellow
    git pull origin master --rebase
    if ($LASTEXITCODE -eq 0) {
        git push origin master
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCCESS] Push completed after pull!" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Push still failed" -ForegroundColor Red
            pause
            exit
        }
    } else {
        Write-Host "[ERROR] Failed to pull" -ForegroundColor Red
        pause
        exit
    }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "    OPERATION COMPLETED SUCCESSFULLY" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Repository: https://github.com/myexcelweb/file-transfer-room.git" -ForegroundColor Yellow
Write-Host "Branch: master" -ForegroundColor Yellow
Write-Host ""
Write-Host "View online: https://github.com/myexcelweb/file-transfer-room" -ForegroundColor Yellow
Write-Host ""
pause