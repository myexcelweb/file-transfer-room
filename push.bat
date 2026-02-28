@echo off
setlocal enabledelayedexpansion
title File Transfer Room - Git Push
color 0A

:: ========================================
:: CONFIGURATION - EDIT THESE VALUES
:: ========================================
set "GIT_REPO_URL=https://github.com/myexcelweb/file-transfer-room.git"
set "BRANCH_NAME=main"
:: ========================================

echo ===============================================
echo     FILE TRANSFER ROOM - GIT PUSH UTILITY
echo ===============================================
echo.

:: Navigate to project folder
cd /d "%~dp0"
echo Current directory: %CD%
echo.

:: Check if git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH!
    echo Please install Git from: https://git-scm.com/
    pause
    exit /b 1
)

:: Check if this is a git repository
if not exist ".git" (
    echo [NEW REPOSITORY] First time setup...
    echo.
    
    :: Initialize git
    echo [1/6] Initializing git repository...
    git init
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to initialize git
        pause
        exit /b 1
    )
    echo [OK] Git initialized
    echo.
    
    :: Create .gitignore if it doesn't exist
    if not exist ".gitignore" (
        echo [2/6] Creating .gitignore file...
        echo # Python > .gitignore
        echo __pycache__/ >> .gitignore
        echo *.pyc >> .gitignore
        echo *.pyo >> .gitignore
        echo *.pyd >> .gitignore
        echo *.db >> .gitignore
        echo *.sqlite >> .gitignore
        echo .DS_Store >> .gitignore
        echo. >> .gitignore
        echo # Virtual Environment >> .gitignore
        echo venv/ >> .gitignore
        echo env/ >> .gitignore
        echo ENV/ >> .gitignore
        echo myenv/ >> .gitignore
        echo. >> .gitignore
        echo # Uploads >> .gitignore
        echo uploads/ >> .gitignore
        echo. >> .gitignore
        echo # IDE >> .gitignore
        echo .vscode/ >> .gitignore
        echo .idea/ >> .gitignore
        echo *.swp >> .gitignore
        echo *.swo >> .gitignore
        echo. >> .gitignore
        echo # Environment >> .gitignore
        echo .env >> .gitignore
        echo *.env >> .gitignore
        echo. >> .gitignore
        echo # Logs >> .gitignore
        echo *.log >> .gitignore
        echo logs/ >> .gitignore
        echo [OK] .gitignore created
    ) else (
        echo [OK] .gitignore already exists
    )
    echo.
    
    :: Create uploads folder
    if not exist "uploads" mkdir uploads
    echo [OK] Uploads folder ready
    echo.
    
    :: Add all files
    echo [3/6] Adding files to git...
    git add .
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to add files
        pause
        exit /b 1
    )
    echo [OK] Files added
    echo.
    
    :: Create initial commit
    echo [4/6] Creating initial commit...
    git commit -m "Initial commit - File Transfer Room"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to commit
        pause
        exit /b 1
    )
    echo [OK] Initial commit created
    echo.
    
    :: Add remote
    echo [5/6] Adding remote repository...
    git remote add origin %GIT_REPO_URL% 2>nul
    if %errorlevel% neq 0 (
        echo Updating existing remote...
        git remote set-url origin %GIT_REPO_URL%
    )
    echo [OK] Remote configured: %GIT_REPO_URL%
    echo.
    
    :: Push to GitHub
    echo [6/6] Pushing to GitHub...
    echo.
    echo Repository: %GIT_REPO_URL%
    echo Branch: %BRANCH_NAME%
    echo.
    
    git push -u origin %BRANCH_NAME%
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] Push completed!
    ) else (
        echo.
        echo [WARNING] Push failed. Trying 'master' branch...
        git push -u origin master
        if %errorlevel% equ 0 (
            echo [SUCCESS] Push completed using 'master' branch!
            set "BRANCH_NAME=master"
        ) else (
            echo [ERROR] Push failed.
            echo.
            echo Possible solutions:
            echo 1. Check if repository exists: %GIT_REPO_URL%
            echo 2. Run: git pull origin main --rebase
            echo 3. Check GitHub authentication
            pause
            exit /b 1
        )
    )
    
) else (
    :: ========================================
    :: EXISTING REPOSITORY - UPDATE
    :: ========================================
    echo [EXISTING REPOSITORY] Updating...
    echo.
    
    :: Show current status
    echo [1/4] Current git status:
    git status --short
    echo.
    
    :: Add changes
    echo [2/4] Adding changes...
    git add .
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to add changes
        pause
        exit /b 1
    )
    echo [OK] Changes added
    echo.
    
    :: Check if there are changes to commit
    git diff --cached --quiet
    if %errorlevel% equ 0 (
        echo [OK] No changes to commit
    ) else (
        :: Commit changes
        echo [3/4] Committing changes...
        set /p "commit_msg=Enter commit message (or press Enter for auto): "
        if "!commit_msg!"=="" (
            set "commit_msg=Update File Transfer Room %date% %time%"
        )
        git commit -m "!commit_msg!"
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to commit
            pause
            exit /b 1
        )
        echo [OK] Changes committed
        echo.
    )
    
    :: Push to GitHub
    echo [4/4] Pushing to GitHub...
    echo.
    
    git push origin %BRANCH_NAME%
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] Push completed!
    ) else (
        echo.
        echo [WARNING] Push failed. Trying to pull first...
        git pull origin %BRANCH_NAME% --rebase
        if %errorlevel% equ 0 (
            git push origin %BRANCH_NAME%
            if %errorlevel% equ 0 (
                echo [SUCCESS] Push completed after pull!
            ) else (
                echo [ERROR] Push still failed
                pause
                exit /b 1
            )
        ) else (
            echo [ERROR] Failed to pull
            pause
            exit /b 1
        )
    )
)

:: ========================================
:: SUCCESS MESSAGE
:: ========================================
echo.
echo ===============================================
echo     OPERATION COMPLETED SUCCESSFULLY
echo ===============================================
echo.
echo Repository: %GIT_REPO_URL%
echo Branch: %BRANCH_NAME%
echo.
echo View online: https://github.com/myexcelweb/file-transfer-room
echo.
pause