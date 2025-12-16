# Author: Zhuo Zhang <imzhuo@foxmail.com>
# Homepage: https://github.com/zchrissirhcz/bin2obj

include_guard()

set(_BIN2OBJ_MODULE_DIR "${CMAKE_CURRENT_LIST_DIR}")

# bin2obj — Convert binary files to platform-specific object files (.o / .obj)
#
# This function calls the Python script `scripts/bin2obj.py` to embed a given binary file
# into an object file and exports a specified symbol name for referencing in C/C++.
# Supports Windows (COFF), Linux/QNX (ELF), and macOS (Mach-O) platforms,
# as well as x86_64 and AArch64 architectures.
#
# Parameters:
#   input_path   - Input binary file path (required)
#   output_path  - Output object file path (required)
#   symbol_name  - Symbol name exported in the object file (required)
#
# Optional keyword arguments:
#   ALIGNMENT <n> - Specify the alignment in bytes for the embedded data (default is 4)
#
# Example usage:
#   bin2obj("test.bin" "test.obj" "test")
#
# Notes:
#   - The variable Python_EXECUTABLE (pointing to the Python interpreter) must be set in advance.
#   - Depends on the script ${CMAKE_SOURCE_DIR}/scripts/bin2obj.py.
#
function(bin2obj input_path output_path symbol_name)
  set(options "")
  set(oneValueArgs ALIGNMENT)
  set(multiValueArgs "")
  cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  # alignment
  if(DEFINED ARG_ALIGNMENT)
    set(alignment "${ARG_ALIGNMENT}")
  else()
    set(alignment 4)
  endif()

  # arch
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64)$")
    set(arch "x86_64")
  elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|ARM64)$")
    set(arch "arm64")
  else()
    message(FATAL_ERROR "Unsupported architecture: ${CMAKE_SYSTEM_PROCESSOR}")
  endif()

  # format
  if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(format "coff")
  elseif(CMAKE_SYSTEM_NAME MATCHES "^(Linux|QNX)$")
    set(format "elf")
  elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set(format "macho")
  else()
    message(FATAL_ERROR "Unsupported system: ${CMAKE_SYSTEM_NAME}")
  endif()

  # codegen
  set(Python_ARGS "${_BIN2OBJ_MODULE_DIR}/bin2obj.py -i ${input_path} -o ${output_path} -f ${format} -s ${symbol_name} -a ${alignment} --arch ${arch}")
  message(STATUS "[bin2obj.cmake] ${Python_ARGS}")
  string(REPLACE " " ";" Python_ARGS ${Python_ARGS})
  execute_process(
    COMMAND ${Python_EXECUTABLE} ${Python_ARGS}
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    RESULT_VARIABLE PY_RESULT
  )
  if(PY_RESULT EQUAL 0)
    message(STATUS "Generated object file: ${output_path}")
  else()
    message(FATAL_ERROR "Python script failed with exit code: ${PY_RESULT}")
  endif()
endfunction()