#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "core/core.hpp"

namespace py = pybind11;

PYBIND11_MODULE(core, m) {
    py::class_<core::Core>(m, "core")
            .def("load_file", &core::Core::LoadFile, py::return_value_policy::reference_internal)
            .def("add_execution", &core::Core::AddExecution, py::return_value_policy::reference_internal)
            .def("run", &core::Core::Run);
}
