project(task-maker-cpp-sandbox-test)

SET(TESTS busywait_arg1 copy_int malloc_arg1 return_arg1 signal_arg1 wait_arg1)

foreach(test ${TESTS})
  add_executable(${test} ${test}.cpp)
  apply_global_cxx_flags_to_all_targets()
  remove_flag_from_file(${test} ${test}.cpp -fsanitize=address)
endforeach()
