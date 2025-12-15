#!/bin/bash
# Test script for Linux/macOS

echo "==================================="
echo "Testing bin2obj"
echo "==================================="
echo

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    FORMAT="elf"
    OBJDUMP="objdump"
    
    # Detect architecture on Linux
    MACHINE=$(uname -m)
    if [[ "$MACHINE" == "x86_64" ]]; then
        ARCH="x86_64"
    elif [[ "$MACHINE" == "i386" ]] || [[ "$MACHINE" == "i686" ]]; then
        ARCH="x86"
    elif [[ "$MACHINE" == "aarch64" ]] || [[ "$MACHINE" == "arm64" ]]; then
        ARCH="arm64"
    else
        echo "Unknown architecture: $MACHINE"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    FORMAT="mach-o"
    OBJDUMP="otool"
    
    # Detect architecture on macOS
    if [[ $(uname -m) == "arm64" ]]; then
        ARCH="arm64"
    else
        ARCH="x86_64"
    fi
else
    echo "Unknown platform: $OSTYPE"
    exit 1
fi

echo "Platform: $PLATFORM"
echo "Format: $FORMAT"
echo "Architecture: $ARCH"
echo

echo "Step 1: Creating test data..."
python3 -c "with open('test_data.bin', 'wb') as f: f.write(b'Hello, this is test binary data!')"
echo

echo "Step 2: Generating object file..."
python3 bin2obj.py -i test_data.bin -o test_data.o -f $FORMAT -s test --arch $ARCH

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to generate object file"
    exit 1
fi
echo

echo "Step 3: Compiling example.c..."
if [ "$PLATFORM" == "macos" ]; then
    clang example.c test_data.o -o test_program
else
    gcc example.c test_data.o -o test_program
fi

if [ $? -ne 0 ]; then
    echo "ERROR: Compilation failed"
    exit 1
fi
echo

echo "Step 4: Running the program..."
./test_program
echo

echo "Step 5: Inspecting object file..."
if [ "$PLATFORM" == "linux" ]; then
    echo "--- Symbol table (nm) ---"
    nm test_data.o
    echo
    echo "--- ELF header (readelf) ---"
    readelf -h test_data.o
elif [ "$PLATFORM" == "macos" ]; then
    echo "--- Symbol table (nm) ---"
    nm test_data.o
    echo
    echo "--- Mach-O header (otool) ---"
    otool -h test_data.o
fi
echo

echo "==================================="
echo "Test completed successfully!"
echo "==================================="
