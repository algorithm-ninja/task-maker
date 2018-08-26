add_library(whereami
  whereami/whereami.c
  whereami/whereami++.cpp
)
target_include_directories(whereami PUBLIC whereami)

add_library(backward INTERFACE)
target_link_libraries(backward INTERFACE dw)
target_include_directories(backward INTERFACE backward)
target_compile_definitions(backward INTERFACE BACKWARD_HAS_DW=1)
