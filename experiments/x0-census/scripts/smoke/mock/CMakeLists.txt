cmake_minimum_required(VERSION 3.20)
project(x0mock VERSION 0.1.0 LANGUAGES C)

# X0 census MOCK (x0final, 2026-10-16). NOT Hearth. Mirrors the flag logic of Hearth's CMakeLists.txt at
# b5d3f14 (C11 with extensions, per-file ISA options for the two SIMD files, an OBJECT library with
# POSITION_INDEPENDENT_CODE, a private DLL define, MSVC-like vs other FP options) so that the census driver can
# configure and build it under A, A-ninja, B-cmake, C and D exactly as it will build hearth_core.

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(SRC ${CMAKE_CURRENT_SOURCE_DIR}/engine/src)
set(CORE_SOURCES ${SRC}/other.c ${SRC}/quant.c ${SRC}/quant_avx2.c ${SRC}/quant_avx512.c)
if(MSVC)
  set_source_files_properties(${SRC}/quant_avx2.c PROPERTIES COMPILE_OPTIONS "/arch:AVX2")
  set_source_files_properties(${SRC}/quant_avx512.c PROPERTIES COMPILE_OPTIONS "/arch:AVX512")
else()
  set_source_files_properties(${SRC}/quant_avx2.c PROPERTIES COMPILE_OPTIONS "-mavx2;-mfma;-mf16c")
  set_source_files_properties(${SRC}/quant_avx512.c PROPERTIES COMPILE_OPTIONS "-mavx512f;-mavx512bw;-mavx512vl;-mavx512vnni;-mavx2;-mfma;-mf16c")
endif()

add_library(x0mock_core OBJECT ${CORE_SOURCES})
target_include_directories(x0mock_core PUBLIC ${SRC})
set_target_properties(x0mock_core PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_compile_definitions(x0mock_core PRIVATE X0MOCK_BUILD_DLL)
if(MSVC)
  target_compile_options(x0mock_core PUBLIC /experimental:c11atomics /fp:precise /utf-8 /W3)
  target_compile_definitions(x0mock_core PUBLIC _CRT_SECURE_NO_WARNINGS)
else()
  target_compile_options(x0mock_core PUBLIC -ffp-contract=off -Wall -Wextra -Wno-unused-parameter)
endif()
