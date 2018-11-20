add_subdirectory(python)

add_library(cpp_frontend frontend.cpp)
target_link_libraries(cpp_frontend cpp_util)
apply_global_cxx_flags_to_all_targets()
remove_flag_from_file(cpp_frontend frontend.cpp -fsanitize=address)
