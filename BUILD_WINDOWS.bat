@echo off
call scripts\build_windows.bat
set build_result=%errorlevel%

echo.
if not "%build_result%"=="0" (
    echo Windows build failed with exit code %build_result%.
) else (
    echo Windows build and startup test completed successfully.
)
echo Press any key to close this window.
pause >nul
exit /b %build_result%
