# bin2obj

[![Cross-Platform Tests](https://github.com/zchrissirhcz/bin2obj/actions/workflows/test.yml/badge.svg)](https://github.com/zchrissirhcz/bin2obj/actions)

Convert binary file into object file (input of linker) when building C/C++. Compared with bin2c tools (such as incbin), using bin2obj reduce compilation time from minutes/hours to seconds!

## Features

- multi-platform, multi-architecture, read-only section

| platform | format | arch | data section |
|------|------|------|--------|
| Linux/Android/QNX | elf | x86, x86_64, ARM64 | `.rodata` |
| Windows | coff | x86, x86_64, ARM64 | `.rdata` |
| macOS | mach-o | x86_64, ARM64 | `__TEXT,__const` |
| iOS | mach-O | ARM64 | `__TEXT,__const` |

- similar interface with incbin, but compile **much faster**

| Feature | incbin.c + incbin.h | bin2obj.py + bin2obj.h |
|------|------------|------------|
| Implementation | ❌ Generates C array + Inline assembly | ✅ Generates object file |
| Symbol naming | ✅ Compatible | ✅ Compatible | ✅ Fully compatible |
| Compiler dependency | ✅ GCC; ❌ MSVC | ✅ **Any Compiler, Any linker** |
| Compile time cost | ✅ GCC is fast; ❌ MSVC is slow(minutes ~ hours) | ✅ **< 5 seconds** |

## Usage

### bin2obj.py

Generate object file from input binary file.

```bash
python bin2obj.py [options]

required arguments：
-i, --input FILE      path of input binary file
-o, --output FILE     path of output object file
-f, --format FORMAT   format of output object file：elf, coff (pe), macho (mach-o)
-s, --symbol NAME     symbol name (must be valid C identifier)

optional arguments：
-a, --alignment N     data alignment (default: 4, must being power of 2)
--arch ARCH           target architecture：x86, x86_64, arm64（default：x86_64）
```


Examples:

```bash
# Windows (COFF)
python bin2obj.py -i data.bin -o data.obj -f coff -s test

# Linux (ELF)
python bin2obj.py -i data.bin -o data.o -f elf -s test

# macOS (Mach-O)
python bin2obj.py -i data.bin -o data.o -f macho -s test

# Specify alignment (default is 4)
python bin2obj.py -i data.bin -o data.o -f elf -s test -a 16

# Specify architecture
python bin2obj.py -i data.bin -o data.o -f elf -s test --arch arm64
```

### bin2obj.h

Macro definitions for using symbols in object file.

In client code:
```c
#include "bin2obj.h"

BIN2OBJ_EXTERN(test);
```

For C code, it expands to:
```c
const unsigned char test_data[];
const unsigned char test_end[];
const unsigned long test_size;
```

For C++ code, it expands to:
```c
extern "C" {
    const unsigned char test_data[];
    const unsigned char test_end[];
    const unsigned long test_size;
}
```

Full minimal example:
```c
#include <stdio.h>
#include "bin2obj.h"
BIN2OBJ_EXTERN(test);

int main(void)
{
    // using macro
    printf("test_data: %p\n", BIN2OBJ_DATA(test));
    printf("test_end: %p\n", BIN2OBJ_END(test));
    printf("test_size: %zu\n", BIN2OBJ_SIZE(test));

    // using symbol name
    printf("test_data: %p\n", test_data);
    printf("test_end: %p\n", test_end);
    printf("test_size: %zu\n", test_size);

    return 0;
}
```

compile:

```bash
gcc main.c data.o -o program
```

### bin2obj.cmake

Helper cmake utility to integrate bin2obj.py with existing CMakeLists.txt.

Example:
```cmake
include(/path/to/bin2obj.cmake)
add_executable(example example.c)
bin2obj("test_data.bin" "${CMAKE_BINARY_DIR}/test_data.obj" "test"
    ALIGNMENT 4 # optional
)
target_sources(example PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/test_data.obj")
```

## Testing

Full unittest:

```bash
python test_bin2obj.py
```

Platform-specific test:

```bash
# Linux/macOS
./test.sh

# Windows
test.bat
```

## References

- [incbin](https://github.com/graphitemaster/incbin), the famous tool
- object file specs:
  - [ELF Format](http://www.skyfree.org/linux/references/ELF_Format.pdf)
  - [Microsoft PE/COFF](https://docs.microsoft.com/en-us/windows/win32/debug/pe-format)
  - [OS X ABI Mach-O](https://github.com/aidansteele/osx-abi-macho-file-format-reference)
- xmake build tool:
  - https://github.com/xmake-io/xmake/issues/7099
  - https://github.com/xmake-io/xmake/pull/7103
- https://github.com/vector-of-bool/cmrc