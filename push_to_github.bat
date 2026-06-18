@echo off
echo === Hermes QuantDinger - Push to GitHub ===
echo.
echo Step 1: Login to GitHub CLI
gh auth login --hostname github.com --git-protocol https --web --scopes repo,workflow,gist,read:org
echo.
echo Step 2: Push
git push origin main
echo.
echo Done! Check https://github.com/Y-wln/QuantDinger
pause
