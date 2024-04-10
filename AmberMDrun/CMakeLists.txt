include(CheckCXXCompilerFlag)
CHECK_CXX_COMPILER_FLAG("-std=c++23" COMPILER_SUPPORTS_CXX23)
CHECK_CXX_COMPILER_FLAG("-std=c++20" COMPILER_SUPPORTS_CXX20)
CHECK_CXX_COMPILER_FLAG("-std=c++17" COMPILER_SUPPORTS_CXX17)
if(COMPILER_SUPPORTS_CXX23)
set(CMAKE_CXX_STANDARD 23)
elseif(COMPILER_SUPPORTS_CXX20)
set(CMAKE_CXX_STANDARD 20)
elseif(COMPILER_SUPPORTS_CXX17)
set(CMAKE_CXX_STANDARD 17)
else()
message(FATAL_ERROR "Need a c++17 complier") 
endif()
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_FLAGS "-static-libstdc++ -static-libgcc")
IF (CMAKE_SYSTEM_NAME MATCHES "Linux")
    MESSAGE(STATUS "current platform: Linux")
ELSEIF (CMAKE_SYSTEM_NAME MATCHES "Windows")
    MESSAGE(FATAL_ERROR  "Windows is not supported")
ELSEIF (CMAKE_SYSTEM_NAME MATCHES "Darwin")
    MESSAGE(FATAL_ERROR  "Mac OS X is not supported")
ELSE ()
    MESSAGE(FATAL_ERROR "${CMAKE_SYSTEM_NAME} is not supported")
ENDIF (CMAKE_SYSTEM_NAME MATCHES "Linux")


find_package(Threads REQUIRED)
include_directories(include)
include_directories(extern)
add_subdirectory(extern/pybind11)
aux_source_directory(src SOURCE)
#add_library(ambermd SHARED ${SOURCE})
add_library(ambermd STATIC ${SOURCE})
target_link_libraries(ambermd PUBLIC pybind11::module)
target_link_libraries(ambermd PUBLIC pybind11::embed)
add_executable(amberMd
        main.cpp
        )
target_link_libraries(amberMd PRIVATE ambermd)
pybind11_add_module(_pyamber
        pyamber.cpp
        )
target_link_libraries(_pyamber PUBLIC ambermd)
target_link_libraries(amberMd PRIVATE ${CMAKE_THREAD_LIBS_INIT})
target_link_libraries(_pyamber PUBLIC ${CMAKE_THREAD_LIBS_INIT})
install(
  TARGETS _pyamber ambermd
  LIBRARY DESTINATION ${CMAKE_BINARY_DIR}/AmberMDrun
  )
