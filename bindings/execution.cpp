#include "core/execution.hpp"
#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(execution, m) {
  auto execution =
      py::class_<core::Execution>(m, "Execution")
          .def("description", &core::Execution::Description)
          .def("id", &core::Execution::ID)
          .def("stdin", &core::Execution::Stdin)
          .def("input", &core::Execution::Input)
          .def("stdout", &core::Execution::Stdout,
               py::return_value_policy::reference_internal)
          .def("stderr", &core::Execution::Stderr,
               py::return_value_policy::reference_internal)
          .def("output",
               (core::FileID * (core::Execution::*)(const std::string&)) &
                   core::Execution::Output,
               py::return_value_policy::reference_internal)
          .def("output",
               (core::FileID *
                (core::Execution::*)(const std::string&, const std::string&)) &
                   core::Execution::Output,
               py::return_value_policy::reference_internal)

          .def("cpu_limit", &core::Execution::CpuLimit)
          .def("wall_limit", &core::Execution::WallLimit)
          .def("memory_limit", &core::Execution::MemoryLimit)
          .def("process_limit", &core::Execution::ProcessLimit)
          .def("file_limit", &core::Execution::FileLimit)
          .def("file_size_limit", &core::Execution::FileSizeLimit)
          .def("memory_lock_limit", &core::Execution::MemoryLockLimit)
          .def("stack_limit", &core::Execution::StackLimit)

          .def("set_exclusive", &core::Execution::SetExclusive)

          .def("set_caching_mode", &core::Execution::SetCachingMode)

          .def("set_executor", &core::Execution::SetExecutor)

          .def("success", &core::Execution::Success)
          .def("cpu_time", &core::Execution::CpuTime)
          .def("sys_time", &core::Execution::SysTime)
          .def("wall_time", &core::Execution::WallTime)
          .def("memory", &core::Execution::Memory)

          .def("status_code", &core::Execution::StatusCode)
          .def("signal", &core::Execution::Signal);

  py::enum_<core::Execution::CachingMode>(execution, "CachingMode")
      .value("ALWAYS", core::Execution::CachingMode::ALWAYS)
      .value("SAME_EXECUTOR", core::Execution::CachingMode::SAME_EXECUTOR)
      .value("NEVER", core::Execution::CachingMode::NEVER)
      .export_values();
}
