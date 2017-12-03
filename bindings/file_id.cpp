#include "core/file_id.hpp"
#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(file_id, m) {
  py::class_<core::FileID>(m, "FileID")
      .def("description", &core::FileID::Description)
      .def("id", &core::FileID::ID)
      .def("write_to", &core::FileID::WriteTo)
      .def("contents", &core::FileID::Contents);
}
