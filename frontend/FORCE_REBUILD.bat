@echo off
echo ========================================
echo FORCE REBUILD FRONTEND
echo ========================================
echo.
echo This will:
echo 1. Clear Vite cache
echo 2. Rebuild the app
echo 3. Start dev server
echo.
pause

echo.
echo Step 1: Clearing Vite cache...
if exist "node_modules\.vite" (
    rmdir /s /q "node_modules\.vite"
    echo ✓ Vite cache cleared
) else (
    echo ✓ No cache to clear
)

if exist "dist" (
    rmdir /s /q "dist"
    echo ✓ Dist folder cleared
) else (
    echo ✓ No dist folder
)

echo.
echo Step 2: Starting dev server...
echo.
echo ========================================
echo Frontend will start now
echo Open: http://localhost:5173/statements
echo ========================================
echo.

npm run dev
