#include "core/core.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

namespace py = pybind11;

PYBIND11_MODULE(core, m) {
  auto core = py::class_<core::Core>(m, "Core")
      .def(py::init<>())
      .def("load_file", &core::Core::LoadFile,
           py::return_value_policy::reference_internal)
      .def("add_execution", &core::Core::AddExecution,
           py::return_value_policy::reference_internal)
      .def("set_callback", &core::Core::SetCallback)
      .def("run", &core::Core::Run, py::call_guard<py::gil_scoped_release>())
      .def_static("set_num_cores", &core::Core::SetNumCores)
      .def_static("set_temp_directory", &core::Core::SetTempDirectory)
      .def_static("set_store_directory", &core::Core::SetStoreDirectory);

  auto task_status = py::class_<core::Core::TaskStatus>(core, "TaskStatus")
      .def_readwrite("event", &core::Core::TaskStatus::event)
      .def_readwrite("message", &core::Core::TaskStatus::message)
      .def_readwrite("type", &core::Core::TaskStatus::type)
      .def_readonly("file_info", &core::Core::TaskStatus::file_info)
      .def_readonly("execution_info", &core::Core::TaskStatus::execution_info);

  py::enum_<core::Core::TaskStatus::Event>(task_status, "Event")
      .value("START", core::Core::TaskStatus::Event::START)
      .value("SUCCESS", core::Core::TaskStatus::Event::SUCCESS)
      .value("BUSY", core::Core::TaskStatus::Event::BUSY)
      .value("FAILURE", core::Core::TaskStatus::Event::FAILURE)
      .export_values();

  py::enum_<core::Core::TaskStatus::Type>(task_status, "Type")
      .value("FILE_LOAD", core::Core::TaskStatus::Type::FILE_LOAD)
      .value("EXECUTION", core::Core::TaskStatus::Type::EXECUTION);
}
