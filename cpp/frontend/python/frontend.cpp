#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#include <pybind11/pybind11.h>
#pragma GCC diagnostic pop

int add(int i, int j) { return i + j; }

PYBIND11_MODULE(task_maker_frontend, m) {
  m.doc() = "pybind11 example plugin";  // optional module docstring

  m.def("add", &add, "A function which adds two numbers");
}
