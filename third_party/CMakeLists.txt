add_library(whereami
  whereami/whereami.c
  whereami/whereami++.cpp
)
target_include_directories(whereami PUBLIC whereami)
