@echo off
echo ========================================
echo Uploading to GitHub: exp_2 repository
echo ========================================
echo.

REM Kill any stuck vim processes
taskkill /F /IM vim.exe 2>nul

REM Remove git folder to start fresh
echo Removing old git configuration...
rd /s /q .git 2>nul

REM Initialize new git repository
echo Initializing new git repository...
git init

REM Set the correct remote URL
echo Setting remote to: https://github.com/lailakaddoura953-max/exp_2.git
git remote add origin https://github.com/lailakaddoura953-max/exp_2.git

REM Add all files
echo Adding all files...
git add .

REM Commit with message
echo Creating commit...
git commit -m "Complete camera misalignment detection system with LEAN proof-of-concept"

REM Rename branch to main
echo Renaming branch to main...
git branch -M main

REM Push to GitHub
echo Pushing to GitHub...
git push -u origin main --force

echo.
echo ========================================
echo Upload complete!
echo Repository: https://github.com/lailakaddoura953-max/exp_2
echo ========================================
pause
