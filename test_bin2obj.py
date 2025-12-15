#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin2obj - Unit Tests

Tests for all platforms (ELF, COFF, Mach-O) and architectures (x86, x86_64, ARM64)
"""

from __future__ import print_function
import unittest
import os
import sys
import struct
import tempfile
import shutil

# Import the generators
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bin2obj import ELFGenerator, COFFGenerator, MachOGenerator


class TestDataGenerator:
    """Generate test data for unit tests"""
    
    @staticmethod
    def generate_simple_data():
        """Simple ASCII text data"""
        return b"Hello, this is test binary data!"
    
    @staticmethod
    def generate_binary_data():
        """Binary data with various byte values"""
        return bytes(bytearray(range(256)))
    
    @staticmethod
    def generate_large_data(size=1024):
        """Generate larger test data"""
        return b"TEST" * (size // 4)
    
    @staticmethod
    def generate_aligned_data(size, alignment):
        """Generate data that tests alignment"""
        return b"A" * size
    
    @staticmethod
    def generate_empty_data():
        """Empty data (edge case)"""
        return b""


class TestELFGenerator(unittest.TestCase):
    """Test ELF format generation"""
    
    def setUp(self):
        self.test_data = TestDataGenerator.generate_simple_data()
        self.symbol_name = "test"
    
    def test_elf_x86_64_generation(self):
        """Test ELF 64-bit x86_64 generation"""
        generator = ELFGenerator(self.test_data, self.symbol_name, 4, 'x86_64')
        obj_data = generator.generate()
        
        # Check ELF magic
        self.assertEqual(obj_data[:4], b'\x7fELF')
        # Check 64-bit
        self.assertEqual(obj_data[4], 2)
        # Check little endian
        self.assertEqual(obj_data[5], 1)
        # Check machine type (x86_64 = 0x3e)
        machine = struct.unpack('<H', obj_data[18:20])[0]
        self.assertEqual(machine, 0x003e)
    
    def test_elf_arm64_generation(self):
        """Test ELF ARM64 generation"""
        generator = ELFGenerator(self.test_data, self.symbol_name, 4, 'arm64')
        obj_data = generator.generate()
        
        self.assertEqual(obj_data[:4], b'\x7fELF')
        # Check machine type (ARM64 = 0xb7)
        machine = struct.unpack('<H', obj_data[18:20])[0]
        self.assertEqual(machine, 0x00b7)
    
    def test_elf_x86_generation(self):
        """Test ELF 32-bit x86 generation"""
        generator = ELFGenerator(self.test_data, self.symbol_name, 4, 'x86')
        obj_data = generator.generate()
        
        self.assertEqual(obj_data[:4], b'\x7fELF')
        # Check 32-bit
        self.assertEqual(obj_data[4], 1)
        # Check machine type (x86 = 0x03)
        machine = struct.unpack('<H', obj_data[18:20])[0]
        self.assertEqual(machine, 0x0003)
    
    def test_elf_alignment(self):
        """Test different alignment values"""
        for alignment in [1, 2, 4, 8, 16, 32, 64]:
            generator = ELFGenerator(self.test_data, self.symbol_name, alignment, 'x86_64')
            obj_data = generator.generate()
            self.assertGreater(len(obj_data), 0)
    
    def test_elf_large_data(self):
        """Test with larger data"""
        large_data = TestDataGenerator.generate_large_data(64 * 1024)  # 64KB
        generator = ELFGenerator(large_data, self.symbol_name, 4, 'x86_64')
        obj_data = generator.generate()
        self.assertGreater(len(obj_data), len(large_data))


class TestCOFFGenerator(unittest.TestCase):
    """Test COFF/PE format generation"""
    
    def setUp(self):
        self.test_data = TestDataGenerator.generate_simple_data()
        self.symbol_name = "test"
    
    def test_coff_x86_64_generation(self):
        """Test COFF 64-bit x86_64 generation"""
        generator = COFFGenerator(self.test_data, self.symbol_name, 4, 'x86_64')
        obj_data = generator.generate()
        
        # Check machine type (AMD64 = 0x8664)
        machine = struct.unpack('<H', obj_data[0:2])[0]
        self.assertEqual(machine, 0x8664)
        
        # Check number of sections
        num_sections = struct.unpack('<H', obj_data[2:4])[0]
        self.assertEqual(num_sections, 1)
    
    def test_coff_arm64_generation(self):
        """Test COFF ARM64 generation"""
        generator = COFFGenerator(self.test_data, self.symbol_name, 4, 'arm64')
        obj_data = generator.generate()
        
        # Check machine type (ARM64 = 0xAA64)
        machine = struct.unpack('<H', obj_data[0:2])[0]
        self.assertEqual(machine, 0xAA64)
    
    def test_coff_x86_generation(self):
        """Test COFF 32-bit x86 generation"""
        generator = COFFGenerator(self.test_data, self.symbol_name, 4, 'x86')
        obj_data = generator.generate()
        
        # Check machine type (x86 = 0x14c)
        machine = struct.unpack('<H', obj_data[0:2])[0]
        self.assertEqual(machine, 0x014c)
    
    def test_coff_rdata_section(self):
        """Test that COFF uses .rdata (read-only) section"""
        generator = COFFGenerator(self.test_data, self.symbol_name, 4, 'x86_64')
        obj_data = generator.generate()
        
        # Section header starts at offset 20 (COFF header size)
        section_name = obj_data[20:28]
        self.assertEqual(section_name, b'.rdata\x00\x00')
    
    def test_coff_alignment_flags(self):
        """Test alignment flags in section characteristics"""
        alignment_flags = {
            1: 0x00100000,
            2: 0x00200000,
            4: 0x00300000,
            8: 0x00400000,
            16: 0x00500000,
        }
        
        for alignment, expected_flag in alignment_flags.items():
            generator = COFFGenerator(self.test_data, self.symbol_name, alignment, 'x86_64')
            obj_data = generator.generate()
            
            # Read characteristics from section header (offset 20 + 36)
            characteristics = struct.unpack('<I', obj_data[56:60])[0]
            # Check alignment flag is present
            self.assertTrue(characteristics & expected_flag)


class TestMachOGenerator(unittest.TestCase):
    """Test Mach-O format generation"""
    
    def setUp(self):
        self.test_data = TestDataGenerator.generate_simple_data()
        self.symbol_name = "test"
    
    def test_macho_x86_64_generation(self):
        """Test Mach-O 64-bit x86_64 generation"""
        generator = MachOGenerator(self.test_data, self.symbol_name, 4, 'x86_64')
        obj_data = generator.generate()
        
        # Check magic (64-bit = 0xFEEDFACF)
        magic = struct.unpack('<I', obj_data[0:4])[0]
        self.assertEqual(magic, 0xFEEDFACF)
        
        # Check CPU type (x86_64 = 0x01000007)
        cputype = struct.unpack('<I', obj_data[4:8])[0]
        self.assertEqual(cputype, 0x01000007)
    
    def test_macho_arm64_generation(self):
        """Test Mach-O ARM64 generation"""
        generator = MachOGenerator(self.test_data, self.symbol_name, 4, 'arm64')
        obj_data = generator.generate()
        
        magic = struct.unpack('<I', obj_data[0:4])[0]
        self.assertEqual(magic, 0xFEEDFACF)
        
        # Check CPU type (ARM64 = 0x0100000C)
        cputype = struct.unpack('<I', obj_data[4:8])[0]
        self.assertEqual(cputype, 0x0100000C)
    
    def test_macho_x86_generation(self):
        """Test Mach-O 32-bit x86 generation"""
        generator = MachOGenerator(self.test_data, self.symbol_name, 4, 'x86')
        obj_data = generator.generate()
        
        # Check magic (32-bit = 0xFEEDFACE)
        magic = struct.unpack('<I', obj_data[0:4])[0]
        self.assertEqual(magic, 0xFEEDFACE)
    
    def test_macho_text_const_section(self):
        """Test that Mach-O uses __TEXT,__const section"""
        generator = MachOGenerator(self.test_data, self.symbol_name, 4, 'x86_64')
        obj_data = generator.generate()
        
        # Find segment name in LC_SEGMENT_64 command
        # Skip mach header (32 bytes) and command info (8 bytes)
        segname = obj_data[40:56]
        self.assertTrue(segname.startswith(b'__TEXT'))
        
        # Section name follows
        sectname = obj_data[104:120]
        self.assertTrue(sectname.startswith(b'__const'))


class TestSymbolGeneration(unittest.TestCase):
    """Test symbol naming and generation"""
    
    def test_symbol_names(self):
        """Test that correct symbol names are generated"""
        test_data = TestDataGenerator.generate_simple_data()
        symbol_name = "test"
        
        # ELF symbols
        generator = ELFGenerator(test_data, symbol_name, 4, 'x86_64')
        obj_data = generator.generate()
        
        # Check symbol string table contains correct names
        self.assertIn(b'test_data\x00', obj_data)
        self.assertIn(b'test_end\x00', obj_data)
        self.assertIn(b'test_size\x00', obj_data)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_empty_data(self):
        """Test with empty data"""
        empty_data = TestDataGenerator.generate_empty_data()
        
        # ELF should handle empty data
        generator = ELFGenerator(empty_data, "empty", 4, 'x86_64')
        obj_data = generator.generate()
        self.assertGreater(len(obj_data), 0)
        
        # COFF should handle empty data
        generator = COFFGenerator(empty_data, "empty", 4, 'x86_64')
        obj_data = generator.generate()
        self.assertGreater(len(obj_data), 0)
    
    def test_binary_data_with_nulls(self):
        """Test with binary data containing null bytes"""
        binary_data = TestDataGenerator.generate_binary_data()
        
        generator = ELFGenerator(binary_data, "binary", 4, 'x86_64')
        obj_data = generator.generate()
        self.assertGreater(len(obj_data), 0)
    
    def test_alignment_padding(self):
        """Test that alignment padding is correctly applied"""
        # 33 bytes with 4-byte alignment should pad to 36 bytes
        data = b"A" * 33
        
        generator = ELFGenerator(data, "aligned", 4, 'x86_64')
        # Check that data is padded
        aligned = generator.align_data(data, 4)
        self.assertEqual(len(aligned) % 4, 0)
        self.assertEqual(len(aligned), 36)


class TestIntegration(unittest.TestCase):
    """Integration tests with file I/O"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_data = TestDataGenerator.generate_simple_data()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """Test complete workflow: data -> generate -> save"""
        output_path = os.path.join(self.temp_dir, "test.o")
        
        generator = ELFGenerator(self.test_data, "test", 4, 'x86_64')
        obj_data = generator.generate()
        
        with open(output_path, 'wb') as f:
            f.write(obj_data)
        
        # Verify file was created and has content
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
        
        # Read back and verify
        with open(output_path, 'rb') as f:
            read_data = f.read()
        
        self.assertEqual(read_data, obj_data)


def run_tests():
    """Run all tests"""
    print("=" * 70)
    print("bin2obj - Unit Tests")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestELFGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestCOFFGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestMachOGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSymbolGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print("Tests run: {}".format(result.testsRun))
    print("Successes: {}".format(result.testsRun - len(result.failures) - len(result.errors)))
    print("Failures: {}".format(len(result.failures)))
    print("Errors: {}".format(len(result.errors)))
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
