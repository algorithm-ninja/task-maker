add_subdirectory(python)

add_library(cpp_frontend frontend.cpp)
target_link_libraries(cpp_frontend cpp_util)
