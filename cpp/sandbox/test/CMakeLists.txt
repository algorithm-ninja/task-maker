project(task-maker-cpp-sandbox-test)

add_executable(busywait_arg1 busywait_arg1.cpp)
add_executable(copy_int copy_int.cpp)
target_link_libraries(copy_int glog::glog)
add_executable(malloc_arg1 malloc_arg1.cpp)
add_executable(return_arg1 return_arg1.cpp)
add_executable(signal_arg1 signal_arg1.cpp)
add_executable(wait_arg1 wait_arg1.cpp)
