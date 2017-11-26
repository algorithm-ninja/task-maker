#include <pybind11/pybind11.h>
#include "core/execution.hpp"

namespace py = pybind11;

PYBIND11_MODULE(execution, m) {
    py::register_exception<core::execution_failure>(m, "execution_failure");
    py::class_<core::Execution>(m, "execution")
            .def("description", &core::Execution::Description)
            .def("stdin", &core::Execution::Stdin)
            .def("input", &core::Execution::Input)
            .def("stdout", &core::Execution::Stdout, py::return_value_policy::reference_internal)
            .def("stderr", &core::Execution::Stderr, py::return_value_policy::reference_internal)
            .def("output", (const core::FileID&(core::Execution::*)(const std::string&))&core::Execution::Output, py::return_value_policy::reference_internal)
            .def("output", (const core::FileID&(core::Execution::*)(const std::string&,const std::string&))&core::Execution::Output, py::return_value_policy::reference_internal)

            .def("cpu_limit", &core::Execution::CpuLimit)
            .def("wall_limit", &core::Execution::WallLimit)
            .def("memory_limit", &core::Execution::MemoryLimit)
            .def("process_limit", &core::Execution::ProcessLimit)
            .def("file_limit", &core::Execution::FileLimit)
            .def("file_size_limit", &core::Execution::FileSizeLimit)
            .def("memory_lock_limit", &core::Execution::MemoryLockLimit)
            .def("stack_limit", &core::Execution::StackLimit)

            .def("die_on_error", &core::Execution::DieOnError)
            .def("exclusive", &core::Execution::Exclusive)

            .def("success", &core::Execution::Success)
            .def("cpu_time", &core::Execution::CpuTime)
            .def("sys_time", &core::Execution::SysTime)
            .def("wall_time", &core::Execution::WallTime)
            .def("memory", &core::Execution::Memory)

            .def("status_code", &core::Execution::StatusCode)
            .def("signal", &core::Execution::Signal);
}
