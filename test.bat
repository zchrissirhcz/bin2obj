@echo off
REM Test script for Windows

echo ===================================
echo Testing bin2obj - Windows (COFF)
echo ===================================
echo.

echo Step 1: Creating test data...
python -c "with open('test_data.bin', 'wb') as f: f.write(b'Hello, this is test binary data!')"
echo.

echo Step 2: Generating object file...
python bin2obj.py -i test_data.bin -o test_data.obj -f coff -s test
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate object file
    exit /b 1
)
echo.

echo Step 3: Compiling example.c with MSVC...
echo Note: Make sure you have MSVC installed and run this from Developer Command Prompt
cl /nologo example.c test_data.obj /Fe:test_program.exe
if %ERRORLEVEL% NEQ 0 (
    echo Trying with MinGW GCC...
    gcc example.c test_data.obj -o test_program.exe
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Compilation failed. Make sure MSVC or MinGW is installed.
        exit /b 1
    )
)
echo.

echo Step 4: Running the program...
test_program.exe
echo.

echo Step 5: Inspecting object file with dumpbin (if available)...
dumpbin /SYMBOLS test_data.obj 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo dumpbin not available, skipping inspection
)
echo.

echo ===================================
echo Test completed successfully!
echo ===================================
