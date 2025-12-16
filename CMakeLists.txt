cmake_minimum_required(VERSION 3.10)
project(bin2obj_example C)

# Include bin2obj module
include(bin2obj.cmake)

# Create a test binary file
set(TEST_BIN_FILE "${CMAKE_CURRENT_BINARY_DIR}/test.bin")
file(WRITE "${TEST_BIN_FILE}" "Hello from bin2obj! This is embedded binary data.\n")

# Use bin2obj to convert test.bin to test.o
set(TEST_OBJ_FILE "${CMAKE_CURRENT_BINARY_DIR}/test.o")
bin2obj(
    "${TEST_BIN_FILE}"
    "${TEST_OBJ_FILE}"
    "test"
    ALIGNMENT 16
)

# Create executable
add_executable(example example.c)
target_include_directories(example PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Link the generated object file
target_link_libraries(example PRIVATE "${TEST_OBJ_FILE}")

# Custom target to regenerate object file if needed
add_custom_target(regenerate_obj
    COMMAND ${CMAKE_COMMAND} -E echo "Regenerating object file..."
    DEPENDS "${TEST_OBJ_FILE}"
)
add_dependencies(example regenerate_obj)
