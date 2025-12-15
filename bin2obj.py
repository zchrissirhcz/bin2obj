# coding: utf-8
# Author: Zhuo Zhang <imzhuo@foxmail.com>

from __future__ import print_function
import argparse
import struct
import sys
import re


class ObjectFileGenerator(object):
    """Base class for object file generation"""

    def __init__(self, binary_data, symbol_name, alignment=4):
        self.binary_data = binary_data
        self.symbol_name = symbol_name
        self.alignment = alignment
        self.size = len(binary_data)

    def align_data(self, data, alignment):
        """Align data to specified boundary"""
        padding = (alignment - len(data) % alignment) % alignment
        return data + b'\x00' * padding

    def generate(self):
        """Generate object file - must be implemented by subclasses"""
        raise NotImplementedError


class ELFGenerator(ObjectFileGenerator):
    """Generate ELF object files for Linux"""

    def __init__(self, binary_data, symbol_name, alignment=4, arch='x86_64'):
        super(ELFGenerator, self).__init__(binary_data, symbol_name, alignment)
        self.arch = arch

    def generate(self):
        """Generate ELF object file"""
        # Determine architecture parameters
        is_64bit = (self.arch in ['x86_64', 'arm64'])

        if self.arch == 'x86_64':
            machine = 0x003e  # EM_X86_64
        elif self.arch == 'arm64':
            machine = 0x00b7  # EM_AARCH64
        else:  # x86
            machine = 0x0003  # EM_386

        # Build ELF header using struct.pack
        if is_64bit:
            # 64-bit ELF header
            elf_header = bytearray(
                b'\x7fELF' +              # ELF magic
                struct.pack('<BBBB',
                            2,                    # 64-bit
                            1,                    # Little endian
                            1,                    # ELF version
                            0) +                  # System V ABI
                b'\x00' * 8 +             # Padding
                struct.pack('<HHIQQQIHHHHHH',
                            1,                    # ET_REL (Relocatable file)
                            machine,              # Machine type
                            1,                    # Version
                            0,                    # Entry point
                            0,                    # Program header offset
                            64,                   # Section header offset (will update)
                            0,                    # Flags
                            64,                   # ELF header size
                            0,                    # Program header entry size
                            0,                    # Program header count
                            64,                   # Section header entry size
                            6,                    # Section header count
                            3)                    # String table section index
            )
        else:
            # 32-bit ELF header
            elf_header = bytearray(
                b'\x7fELF' +
                struct.pack('<BBBB',
                            1,                    # 32-bit
                    1,                    # Little endian
                    1,                    # ELF version
                    0) +                  # System V ABI
                b'\x00' * 8 +             # Padding
                struct.pack('<HHIIIIIHHHHHH',
                    1,                    # ET_REL
                    machine,              # Machine type
                    1,                    # Version
                    0,                    # Entry point
                    0,                    # Program header offset
                    52,                   # Section header offset (will update)
                    0,                    # Flags
                    52,                   # ELF header size
                    0,                    # Program header entry size
                    0,                    # Program header count
                    40,                   # Section header entry size
                    6,                    # Section header count
                    3)                    # String table section index
            )
        
        # Align data section
        aligned_data = self.align_data(self.binary_data, self.alignment)
        
        # Append size constant (8 bytes for x64, 4 bytes for x86)
        if self.arch == 'x86_64' or self.arch == 'arm64':
            size_bytes = struct.pack('<Q', self.size)
        else:
            size_bytes = struct.pack('<I', self.size)
        
        # Combined data: aligned_data + size_constant
        combined_data = aligned_data + size_bytes
        data_size_offset = len(aligned_data)  # Offset where size constant starts
        
        # Build sections
        sections = []
        
        # Section 0: NULL
        sections.append(b'')
        
        # Section 1: .data
        sections.append(aligned_data)
        
        # Section 2: .rodata (for size constant)
        if is_64bit:
            size_data = struct.pack('<Q', self.size)
        else:
            size_data = struct.pack('<I', self.size)
        sections.append(size_data)
        
        # Section 3: .shstrtab (section name string table)
        shstrtab = b'\x00.data\x00.rodata\x00.shstrtab\x00.symtab\x00.strtab\x00'
        sections.append(shstrtab)
        
        # Section 4: .symtab (symbol table)
        # Symbol 0: NULL
        # Symbol 1: section symbol for .data
        # Symbol 2: section symbol for .rodata
        # Symbol 3: data start symbol
        # Symbol 4: data end symbol
        # Symbol 5: size symbol
        if is_64bit:
            symtab = bytearray()
            # NULL symbol
            symtab += struct.pack('<IBBHQQ', 0, 0, 0, 0, 0, 0)
            # .data section symbol
            symtab += struct.pack('<IBBHQQ', 0, 3, 0, 1, 0, 0)  # STT_SECTION
            # .rodata section symbol
            symtab += struct.pack('<IBBHQQ', 0, 3, 0, 2, 0, 0)  # STT_SECTION
            # Data start symbol (global)
            symtab += struct.pack('<IBBHQQ', 1, 0x11, 0, 1, 0, len(aligned_data))  # STB_GLOBAL, STT_OBJECT
            # Data end symbol (global, points to end of data)
            data_name_len = len(self.symbol_name.encode()) + len("_data".encode())
            symtab += struct.pack('<IBBHQQ', 
                                1 + data_name_len + 1,
                                0x11, 0, 1, len(aligned_data), 0)  # STB_GLOBAL, STT_OBJECT, at end
            # Size symbol (global, in .rodata)
            end_name_len = len(self.symbol_name.encode()) + len("_end".encode())
            symtab += struct.pack('<IBBHQQ', 
                                1 + data_name_len + 1 + end_name_len + 1,
                                0x11, 0, 2, 0, 8)  # STB_GLOBAL, STT_OBJECT, section 2
        else:  # x86 (32-bit)
            symtab = bytearray()
            # NULL symbol
            symtab += struct.pack('<IIIBBH', 0, 0, 0, 0, 0, 0)
            # .data section symbol
            symtab += struct.pack('<IIIBBH', 0, 0, 0, 3, 0, 1)
            # .rodata section symbol
            symtab += struct.pack('<IIIBBH', 0, 0, 0, 3, 0, 2)
            # Data start symbol
            symtab += struct.pack('<IIIBBH', 1, 0, len(aligned_data), 0x11, 0, 1)
            # Data end symbol
            data_name_len = len(self.symbol_name.encode()) + len("_data".encode())
            symtab += struct.pack('<IIIBBH', 
                                1 + data_name_len + 1,
                                len(aligned_data), 0, 0x11, 0, 1)
            # Size symbol (in .rodata)
            end_name_len = len(self.symbol_name.encode()) + len("_end".encode())
            symtab += struct.pack('<IIIBBH', 
                                1 + data_name_len + 1 + end_name_len + 1,
                                0, 4, 0x11, 0, 2)
        sections.append(bytes(symtab))
        
        # Section 5: .strtab (symbol name string table)
        strtab = b'\x00' + self.symbol_name.encode() + b'_data\x00'
        strtab += self.symbol_name.encode() + b'_end\x00'
        strtab += self.symbol_name.encode() + b'_size\x00'
        sections.append(strtab)
        
        # Calculate offsets
        # is_64bit already defined at the beginning of generate()
        header_size = 64 if is_64bit else 52
        section_header_size = 64 if is_64bit else 40
        
        offset = header_size
        section_offsets = []
        for section in sections:
            section_offsets.append(offset)
            offset += len(section)
        
        # Update section header offset in ELF header
        sh_offset = offset
        if is_64bit:
            struct.pack_into('<Q', elf_header, 40, sh_offset)
        else:
            struct.pack_into('<I', elf_header, 32, sh_offset)
        
        # Build section headers
        section_headers = bytearray()
        
        if is_64bit:
            # Section 0: NULL
            section_headers += struct.pack('<IIQQQQIIQQ', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            # Section 1: .data
            section_headers += struct.pack('<IIQQQQIIQQ',
                                          1,           # name offset in shstrtab
                                          1,           # SHT_PROGBITS
                                          3,           # SHF_WRITE | SHF_ALLOC
                                          0,           # address
                                          section_offsets[1],  # offset
                                          len(sections[1]),    # size
                                          0,           # link
                                          0,           # info
                                          self.alignment,      # addralign
                                          0)           # entsize
            
            # Section 2: .rodata
            section_headers += struct.pack('<IIQQQQIIQQ',
                                          7,           # name offset (.rodata)
                                          1,           # SHT_PROGBITS
                                          2,           # SHF_ALLOC
                                          0,           # address
                                          section_offsets[2],  # offset
                                          len(sections[2]),    # size
                                          0,           # link
                                          0,           # info
                                          8,           # addralign
                                          0)           # entsize
            
            # Section 3: .shstrtab
            section_headers += struct.pack('<IIQQQQIIQQ',
                                          15, 3, 0, 0, section_offsets[3], len(sections[3]),
                                          0, 0, 1, 0)
            
            # Section 4: .symtab
            section_headers += struct.pack('<IIQQQQIIQQ',
                                          25, 2, 0, 0, section_offsets[4], len(sections[4]),
                                          5, 3, 8, 24)
            
            # Section 5: .strtab
            section_headers += struct.pack('<IIQQQQIIQQ',
                                          33, 3, 0, 0, section_offsets[5], len(sections[5]),
                                          0, 0, 1, 0)
        else:
            # Section 0: NULL
            section_headers += struct.pack('<IIIIIIIIII', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            # Section 1: .data
            section_headers += struct.pack('<IIIIIIIIII',
                                          1, 1, 3, 0, section_offsets[1], len(sections[1]),
                                          0, 0, self.alignment, 0)
            
            # Section 2: .rodata
            section_headers += struct.pack('<IIIIIIIIII',
                                          7, 1, 2, 0, section_offsets[2], len(sections[2]),
                                          0, 0, 4, 0)
            
            # Section 3: .shstrtab
            section_headers += struct.pack('<IIIIIIIIII',
                                          15, 3, 0, 0, section_offsets[3], len(sections[3]),
                                          0, 0, 1, 0)
            
            # Section 4: .symtab
            section_headers += struct.pack('<IIIIIIIIII',
                                          25, 2, 0, 0, section_offsets[4], len(sections[4]),
                                          5, 3, 4, 16)
            
            # Section 5: .strtab
            section_headers += struct.pack('<IIIIIIIIII',
                                          33, 3, 0, 0, section_offsets[5], len(sections[5]),
                                          0, 0, 1, 0)
        
        # Assemble final object file
        obj_file = bytes(elf_header)
        for section in sections:
            obj_file += section
        obj_file += bytes(section_headers)
        
        return obj_file


class COFFGenerator(ObjectFileGenerator):
    """Generate COFF object files for Windows"""
    
    def __init__(self, binary_data, symbol_name, alignment=4, arch='x86_64'):
        super(COFFGenerator, self).__init__(binary_data, symbol_name, alignment)
        self.arch = arch
    
    def generate(self):
        """Generate COFF object file"""
        # Align data
        aligned_data = self.align_data(self.binary_data, self.alignment)
                # Append size constant (8 bytes for x64, 4 bytes for x86)
        if self.arch == 'x86_64' or self.arch == 'arm64':
            size_bytes = struct.pack('<Q', self.size)
        else:
            size_bytes = struct.pack('<I', self.size)
        
        # Combined data: aligned_data + size_constant
        combined_data = aligned_data + size_bytes
        data_size_offset = len(aligned_data)  # Offset where size constant starts
                # Machine type
        if self.arch == 'x86_64':
            machine = 0x8664  # IMAGE_FILE_MACHINE_AMD64
        elif self.arch == 'arm64':
            machine = 0xAA64  # IMAGE_FILE_MACHINE_ARM64
        else:
            machine = 0x14c   # IMAGE_FILE_MACHINE_I386
        
        # Alignment flag for section characteristics
        alignment_flags = {
            1:  0x00100000,  # IMAGE_SCN_ALIGN_1BYTES
            2:  0x00200000,  # IMAGE_SCN_ALIGN_2BYTES
            4:  0x00300000,  # IMAGE_SCN_ALIGN_4BYTES
            8:  0x00400000,  # IMAGE_SCN_ALIGN_8BYTES
            16: 0x00500000,  # IMAGE_SCN_ALIGN_16BYTES
            32: 0x00600000,  # IMAGE_SCN_ALIGN_32BYTES
            64: 0x00700000,  # IMAGE_SCN_ALIGN_64BYTES
        }
        alignment_flag = alignment_flags.get(self.alignment, 0x00300000)  # Default to 4-byte
        
        # COFF Header
        num_sections = 1
        num_symbols = 4  # section symbol, data symbol, end symbol, size symbol
        
        coff_header = struct.pack('<HHIIIHH',
                                 machine,           # Machine
                                 num_sections,      # NumberOfSections
                                 0,                 # TimeDateStamp
                                 0,                 # PointerToSymbolTable (will update)
                                 num_symbols,       # NumberOfSymbols
                                 0,                 # SizeOfOptionalHeader
                                 0)                 # Characteristics
        
        # Section Header for .rdata (read-only data)
        section_name = b'.rdata\x00\x00'
        
        # Section characteristics:
        # IMAGE_SCN_CNT_INITIALIZED_DATA (0x00000040) - Contains initialized data
        # IMAGE_SCN_MEM_READ             (0x40000000) - Readable
        # Plus alignment flag
        characteristics = 0x00000040 | 0x40000000 | alignment_flag
        
        section_header = struct.pack('<8sIIIIIIHHI',
                                    section_name,
                                    0,                    # VirtualSize
                                    0,                    # VirtualAddress
                                    len(combined_data),   # SizeOfRawData
                                    0,                    # PointerToRawData (will update)
                                    0,                    # PointerToRelocations
                                    0,                    # PointerToLinenumbers
                                    0,                    # NumberOfRelocations
                                    0,                    # NumberOfLinenumbers
                                    characteristics)      # Characteristics
        
        # Calculate offsets
        header_size = len(coff_header) + len(section_header)
        data_offset = header_size
        
        # Update PointerToRawData in section header
        section_header = struct.pack('<8sIIIIIIHHI',
                                    section_name,
                                    0,
                                    0,
                                    len(combined_data),
                                    data_offset,
                                    0, 0, 0, 0,
                                    characteristics)
        
        # Symbol table offset
        symbol_table_offset = data_offset + len(combined_data)
        
        # Update PointerToSymbolTable in COFF header
        coff_header = struct.pack('<HHIIIHH',
                                 machine,
                                 num_sections,
                                 0,
                                 symbol_table_offset,
                                 num_symbols,
                                 0,
                                 0)
        
        # Build symbol table
        symbol_table = bytearray()
        
        # Symbol 1: .rdata section
        symbol_table += struct.pack('<8sIHHBB',
                                   b'.rdata\x00\x00',
                                   0,        # Value
                                   1,        # SectionNumber
                                   0,        # Type
                                   3,        # StorageClass: IMAGE_SYM_CLASS_STATIC
                                   0)        # NumberOfAuxSymbols
        
        # On x86 Windows, C symbols have leading underscore
        prefix = '_' if self.arch == 'x86' else ''
        
        # Symbol 2: data symbol (external)
        sym_name = (prefix + self.symbol_name + '_data').encode()[:8]
        if len(sym_name) < 8:
            sym_name = sym_name.ljust(8, b'\x00')
        
        data_name_str = prefix + self.symbol_name + '_data'
        if len(data_name_str.encode()) > 8:
            # Long name: use string table
            symbol_table += struct.pack('<IIIhHBB',
                                       0,           # Zeroes
                                       4,           # String table offset
                                       0,           # Value
                                       1,           # SectionNumber
                                       0,           # Type
                                       2,           # StorageClass: IMAGE_SYM_CLASS_EXTERNAL
                                       0)           # NumberOfAuxSymbols
        else:
            symbol_table += struct.pack('<8sIHHBB',
                                       sym_name,
                                       0,           # Value
                                       1,           # SectionNumber
                                       0,           # Type
                                       2,           # StorageClass: IMAGE_SYM_CLASS_EXTERNAL
                                       0)           # NumberOfAuxSymbols
        
        # Symbol 3: data end symbol (external, points to end)
        size_offset = 4 + len(data_name_str.encode()) + 1  # Offset after prefix+"name_data\0"
        
        end_name_str = prefix + self.symbol_name + '_end'
        if len(end_name_str.encode()) > 8:
            symbol_table += struct.pack('<IIIhHBB',
                                       0,
                                       size_offset,
                                       len(aligned_data),  # Points to end
                                       1,           # SectionNumber
                                       0,           # Type
                                       2,           # StorageClass: IMAGE_SYM_CLASS_EXTERNAL
                                       0)           # NumberOfAuxSymbols
            end_in_string_table = True
        else:
            end_sym_name = end_name_str.encode()[:8].ljust(8, b'\x00')
            symbol_table += struct.pack('<8sIHHBB',
                                       end_sym_name,
                                       len(aligned_data),
                                       1,
                                       0,
                                       2,
                                       0)
            end_in_string_table = False
        
        # Symbol 4: size symbol (external, in data section)
        size_name_str = prefix + self.symbol_name + '_size'
        size_sym_name = size_name_str.encode()[:8]
        if len(size_sym_name) < 8:
            size_sym_name = size_sym_name.ljust(8, b'\x00')
        
        # Calculate offset for size symbol in string table
        if end_in_string_table:
            size_offset_2 = size_offset + len(end_name_str.encode()) + 1
        else:
            size_offset_2 = size_offset  # "_end" not in string table, so "_size" follows "_data"
        
        if len(size_name_str.encode()) > 8:
            symbol_table += struct.pack('<IIIhHBB',
                                       0,
                                       size_offset_2,
                                       data_size_offset,  # Points to size constant in data section
                                       1,           # SectionNumber: in .rdata section
                                       0,           # Type
                                       2,           # StorageClass: IMAGE_SYM_CLASS_EXTERNAL
                                       0)           # NumberOfAuxSymbols
        else:
            symbol_table += struct.pack('<8sIhHBB',
                                       size_sym_name,
                                       data_size_offset,
                                       1,           # SectionNumber: in .rdata section
                                       0,
                                       2,
                                       0)
        
        # String table
        string_table = bytearray()
        string_table += struct.pack('<I', 4)  # String table size (will update)
        
        if len(data_name_str.encode()) > 8:
            string_table += data_name_str.encode() + b'\x00'
        
        if len(end_name_str.encode()) > 8:
            string_table += end_name_str.encode() + b'\x00'
        
        if len(size_name_str.encode()) > 8:
            string_table += size_name_str.encode() + b'\x00'
        
        # Update string table size
        struct.pack_into('<I', string_table, 0, len(string_table))
        
        # Assemble object file
        obj_file = coff_header + section_header + combined_data + bytes(symbol_table) + bytes(string_table)
        
        return obj_file


class MachOGenerator(ObjectFileGenerator):
    """Generate Mach-O object files for macOS"""
    
    def __init__(self, binary_data, symbol_name, alignment=4, arch='x86_64'):
        super(MachOGenerator, self).__init__(binary_data, symbol_name, alignment)
        self.arch = arch
    
    def generate(self):
        """Generate Mach-O object file"""
        # Align data
        aligned_data = self.align_data(self.binary_data, self.alignment)
        
        # Append size constant (8 bytes for 64-bit, 4 bytes for 32-bit)
        is_64bit_check = (self.arch in ['x86_64', 'arm64'])
        if is_64bit_check:
            size_bytes = struct.pack('<Q', self.size)
        else:
            size_bytes = struct.pack('<I', self.size)
        aligned_data_with_size = aligned_data + size_bytes
        
        # Mach-O header
        if self.arch == 'x86_64':
            magic = 0xFEEDFACF  # MH_MAGIC_64
            cputype = 0x01000007  # CPU_TYPE_X86_64
            cpusubtype = 0x00000003  # CPU_SUBTYPE_X86_64_ALL
            is_64bit = True
        elif self.arch == 'arm64':
            magic = 0xFEEDFACF  # MH_MAGIC_64
            cputype = 0x0100000C  # CPU_TYPE_ARM64
            cpusubtype = 0x00000000  # CPU_SUBTYPE_ARM64_ALL
            is_64bit = True
        else:  # x86
            magic = 0xFEEDFACE  # MH_MAGIC
            cputype = 0x00000007  # CPU_TYPE_X86
            cpusubtype = 0x00000003  # CPU_SUBTYPE_X86_ALL
            is_64bit = False
        
        filetype = 0x1  # MH_OBJECT
        ncmds = 2  # LC_SEGMENT and LC_SYMTAB
        sizeofcmds = 0  # Will calculate
        flags = 0x00002000  # MH_SUBSECTIONS_VIA_SYMBOLS
        
        # Build segment command
        if is_64bit:
            # Use __TEXT,__const for read-only data (same as incbin)
            segname = b'__TEXT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            sectname = b'__const\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            
            # Section structure (64-bit)
            # S_REGULAR (0x00000000) for regular section
            section = struct.pack('<16s16sQQIIIIIIII',
                                 sectname,              # sectname
                                 segname,               # segname
                                 0,                     # addr
                                 len(aligned_data_with_size),     # size (include size constant)
                                 0,                     # offset (will update)
                                 self.alignment.bit_length() - 1,  # align (log2)
                                 0,                     # reloff
                                 0,                     # nreloc
                                 0x00000000,           # flags: S_REGULAR
                                 0, 0, 0)              # reserved
            
            # Segment command (64-bit)
            cmd = 0x19  # LC_SEGMENT_64
            cmdsize = 72 + len(section)
            
            segment_cmd = struct.pack('<II16sQQQQIIII',
                                     cmd,
                                     cmdsize,
                                     segname,
                                     0,              # vmaddr
                                     len(aligned_data_with_size),  # vmsize (include size constant)
                                     0,              # fileoff (will update)
                                     len(aligned_data_with_size),  # filesize (include size constant)
                                     7,              # maxprot (VM_PROT_ALL)
                                     3,              # initprot (VM_PROT_READ | VM_PROT_WRITE)
                                     1,              # nsects
                                     0)              # flags
            
            segment_cmd += section
            header_size = 32
        else:
            segname = b'__TEXT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            sectname = b'__const\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            
            # Section structure (32-bit)
            # Format: sectname(16), segname(16), addr(I), size(I), offset(I), align(I), reloff(I), nreloc(I), flags(I), reserved1(I), reserved2(I)
            section = struct.pack('<16s16sIIIIIIIII',
                                 sectname,
                                 segname,
                                 0,                     # addr
                                 len(aligned_data_with_size),     # size (include size constant)
                                 0,                     # offset (will update)
                                 self.alignment.bit_length() - 1,
                                 0,                     # reloff
                                 0,                     # nreloc
                                 0x00000000,           # flags
                                 0, 0)                 # reserved1, reserved2
            
            # Segment command (32-bit)
            cmd = 0x1  # LC_SEGMENT
            cmdsize = 56 + len(section)
            
            segment_cmd = struct.pack('<II16sIIIIIIII',
                                     cmd,
                                     cmdsize,
                                     segname,
                                     0,
                                     len(aligned_data_with_size),  # vmsize (include size constant)
                                     0,
                                     len(aligned_data_with_size),  # filesize (include size constant)
                                     7,
                                     3,
                                     1,
                                     0)
            
            segment_cmd += section
            header_size = 28
        
        # Symbol table command
        symtab_cmd = struct.pack('<IIIIII',
                                0x2,   # LC_SYMTAB
                                24,    # cmdsize
                                0,     # symoff (will update)
                                3,     # nsyms (data, end, size)
                                0,     # stroff (will update)
                                0)     # strsize (will update)
        
        sizeofcmds = len(segment_cmd) + len(symtab_cmd)
        
        # Mach-O header
        if is_64bit:
            mach_header = struct.pack('<IIIIIIII',
                                     magic,
                                     cputype,
                                     cpusubtype,
                                     filetype,
                                     ncmds,
                                     sizeofcmds,
                                     flags,
                                     0)  # reserved
        else:
            mach_header = struct.pack('<IIIIIII',
                                     magic,
                                     cputype,
                                     cpusubtype,
                                     filetype,
                                     ncmds,
                                     sizeofcmds,
                                     flags)
        
        # Calculate offsets
        data_offset = header_size + sizeofcmds
        
        # Update segment and section offsets
        segment_cmd = bytearray(segment_cmd)
        if is_64bit:
            # 64-bit LC_SEGMENT_64 structure:
            # cmd(4) + cmdsize(4) + segname(16) + vmaddr(8) + vmsize(8) + fileoff(8) + ...
            # fileoff is at offset 32 from start of command
            struct.pack_into('<Q', segment_cmd, 32, data_offset)
            # Section is after the segment command header (72 bytes)
            # Section structure: sectname(16) + segname(16) + addr(8) + size(8) + offset(4) + ...
            # offset is at 48 bytes from section start, which is 72 bytes into segment_cmd
            struct.pack_into('<I', segment_cmd, 72 + 48, data_offset)
        else:
            # 32-bit LC_SEGMENT structure:
            # cmd(4) + cmdsize(4) + segname(16) + vmaddr(4) + vmsize(4) + fileoff(4) + ...
            # fileoff is at offset 24 from start of command
            struct.pack_into('<I', segment_cmd, 24, data_offset)
            # Section is after the segment command header (56 bytes)
            # Section structure: sectname(16) + segname(16) + addr(4) + size(4) + offset(4) + ...
            # offset is at 40 bytes from section start, which is 56 bytes into segment_cmd
            struct.pack_into('<I', segment_cmd, 56 + 40, data_offset)
        segment_cmd = bytes(segment_cmd)
        
        # Build symbol table
        symtab = bytearray()
        strtab = bytearray(b'\x00')  # String table starts with null byte
        
        # Add symbol names to string table
        strtab += b'_' + self.symbol_name.encode() + b'_data\x00'
        data_sym_strx = 1
        
        strtab += b'_' + self.symbol_name.encode() + b'_end\x00'
        end_sym_strx = 1 + len(self.symbol_name.encode()) + len("_data".encode()) + 1 + 1
        
        strtab += b'_' + self.symbol_name.encode() + b'_size\x00'
        size_sym_strx = end_sym_strx + len(self.symbol_name.encode()) + len("_end".encode()) + 1 + 1
        
        # Symbol 1: data symbol (external, section 1)
        if is_64bit:
            symtab += struct.pack('<IBBHQ',
                                 data_sym_strx,  # n_strx
                                 0x0F,           # n_type: N_SECT | N_EXT
                                 1,              # n_sect
                                 0x0000,         # n_desc
                                 0)              # n_value
        else:
            symtab += struct.pack('<IBBHI',
                                 data_sym_strx,
                                 0x0F,
                                 1,
                                 0x0000,
                                 0)
        
        # Symbol 2: data end symbol (external, section 1, points to end)
        if is_64bit:
            symtab += struct.pack('<IBBHQ',
                                 end_sym_strx,
                                 0x0F,           # N_SECT | N_EXT
                                 1,              # n_sect
                                 0x0000,
                                 len(aligned_data))  # Points to end (before size constant)
        else:
            symtab += struct.pack('<IBBHI',
                                 end_sym_strx,
                                 0x0F,
                                 1,
                                 0x0000,
                                 len(aligned_data))
        
        # Symbol 3: size symbol (external, section 1, points to size constant location)
        if is_64bit:
            symtab += struct.pack('<IBBHQ',
                                 size_sym_strx,
                                 0x0F,           # N_SECT | N_EXT
                                 1,              # n_sect (section 1)
                                 0x0000,
                                 len(aligned_data))  # Points to size constant location
        else:
            symtab += struct.pack('<IBBHI',
                                 size_sym_strx,
                                 0x0F,
                                 1,
                                 0x0000,
                                 len(aligned_data))
        
        # Calculate symbol table and string table offsets
        symoff = data_offset + len(aligned_data_with_size)
        stroff = symoff + len(symtab)
        strsize = len(strtab)
        
        # Update symtab command
        symtab_cmd = struct.pack('<IIIIII',
                                0x2,
                                24,
                                symoff,
                                3,
                                stroff,
                                strsize)
        
        # Assemble object file
        obj_file = mach_header + segment_cmd + symtab_cmd + aligned_data_with_size + bytes(symtab) + bytes(strtab)
        
        return obj_file


def main():
    parser = argparse.ArgumentParser(
        description='Convert binary files to object files for linking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i data.bin -o data.o -f elf -s my_data
  %(prog)s -i image.png -o image.obj -f coff -s image_data -a 32
  %(prog)s -i asset.bin -o asset.o -f macho -s asset_data --arch arm64
        """
    )
    
    parser.add_argument('-i', '--input', required=True,
                       help='Input binary file')
    parser.add_argument('-o', '--output', required=True,
                       help='Output object file')
    parser.add_argument('-f', '--format', required=True,
                       choices=['elf', 'coff', 'mach-o'],
                       help='Output format: elf (Linux), coff (Windows), mach-o (macOS)')
    parser.add_argument('-s', '--symbol', required=True,
                       help='Symbol name for the embedded data')
    parser.add_argument('-a', '--alignment', type=int, default=4,
                       help='Data alignment in bytes (default: 4, same as incbin)')
    parser.add_argument('--arch', default='x86_64',
                       choices=['x86', 'x86_64', 'arm64'],
                       help='Target architecture (default: x86_64)')
    
    args = parser.parse_args()
    
    # Validate symbol name (must be a valid C identifier)
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', args.symbol):
        print("Error: Invalid symbol name '{}'".format(args.symbol), file=sys.stderr)
        print("Symbol name must be a valid C identifier (start with letter or underscore, contain only letters, digits, and underscores)", file=sys.stderr)
        sys.exit(1)
    
    # Validate alignment (must be power of 2)
    if args.alignment <= 0 or (args.alignment & (args.alignment - 1)) != 0:
        print("Error: Alignment must be a power of 2, got {}".format(args.alignment), file=sys.stderr)
        sys.exit(1)
    
    # Read input file
    try:
        with open(args.input, 'rb') as f:
            binary_data = f.read()
    except IOError as e:
        print("Error reading input file: {}".format(e), file=sys.stderr)
        sys.exit(1)
    
    if len(binary_data) == 0:
        print("Warning: Input file is empty", file=sys.stderr)
    
    # Check file size (warn if very large)
    file_size_mb = len(binary_data) / (1024.0 * 1024.0)
    if file_size_mb > 2048:
        print("Error: Input file is too large ({:.1f} MB, max recommended: 2 GB)".format(file_size_mb), file=sys.stderr)
        print("Files larger than 2 GB may exceed object format limitations", file=sys.stderr)
        sys.exit(1)
    elif file_size_mb > 500:
        print("Warning: Input file is large ({:.1f} MB)".format(file_size_mb), file=sys.stderr)
        print("This may increase link time and executable size", file=sys.stderr)
    
    # Generate object file
    fmt = args.format.lower()
    if fmt == 'elf':
        generator = ELFGenerator(binary_data, args.symbol, args.alignment, args.arch)
    elif fmt in ['coff', 'pe']:
        generator = COFFGenerator(binary_data, args.symbol, args.alignment, args.arch)
    elif fmt in ['macho', 'mach-o']:
        generator = MachOGenerator(binary_data, args.symbol, args.alignment, args.arch)
    else:
        print("Error: Unknown format '{}'".format(args.format), file=sys.stderr)
        sys.exit(1)
    
    try:
        obj_data = generator.generate()
    except Exception as e:
        print("Error generating object file: {}".format(e), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Write output file
    try:
        with open(args.output, 'wb') as f:
            f.write(obj_data)
    except IOError as e:
        print("Error writing output file: {}".format(e), file=sys.stderr)
        sys.exit(1)
    
    print("Successfully created {}".format(args.output))
    print("  Format: {}".format(args.format.upper()))
    print("  Architecture: {}".format(args.arch))
    print("  Symbol: {} (size: {} bytes)".format(args.symbol, len(binary_data)))
    print("  Alignment: {} bytes".format(args.alignment))
    print("  Symbols generated:")
    print("    - {}_data".format(args.symbol))
    print("    - {}_end".format(args.symbol))
    print("    - {}_size".format(args.symbol))


if __name__ == '__main__':
    main()
