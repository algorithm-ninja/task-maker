#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#pragma GCC diagnostic pop

#include "frontend/frontend.hpp"

PYBIND11_MODULE(task_maker_frontend, m) {
  m.doc() = "Task-maker frontend module";
  pybind11::class_<frontend::Resources>(m, "Resources")
      .def_readwrite("cpu_time", &frontend::Resources::cpu_time)
      .def_readwrite("sys_time", &frontend::Resources::sys_time)
      .def_readwrite("wall_time", &frontend::Resources::wall_time)
      .def_readwrite("memory", &frontend::Resources::memory)
      .def_readwrite("nproc", &frontend::Resources::nproc)
      .def_readwrite("nofiles", &frontend::Resources::nofiles)
      .def_readwrite("fsize", &frontend::Resources::fsize)
      .def_readwrite("memlock", &frontend::Resources::memlock)
      .def_readwrite("stack", &frontend::Resources::stack);

  pybind11::enum_<capnproto::Result::Status::Which>(m, "ResultStatus")
      .value("SUCCESS", capnproto::Result::Status::Which::SUCCESS)
      .value("SIGNAL", capnproto::Result::Status::Which::SIGNAL)
      .value("RETURN_CODE", capnproto::Result::Status::Which::RETURN_CODE)
      .value("TIME_LIMIT", capnproto::Result::Status::Which::TIME_LIMIT)
      .value("WALL_LIMIT", capnproto::Result::Status::Which::WALL_LIMIT)
      .value("MEMORY_LIMIT", capnproto::Result::Status::Which::MEMORY_LIMIT)
      .value("MISSING_FILES", capnproto::Result::Status::Which::MISSING_FILES)
      .value("INTERNAL_ERROR",
             capnproto::Result::Status::Which::INTERNAL_ERROR);

  pybind11::class_<frontend::Result>(m, "Result")
      .def_readonly("status", &frontend::Result::status)
      .def_readonly("signal", &frontend::Result::signal)
      .def_readonly("return_code", &frontend::Result::return_code)
      .def_readonly("error", &frontend::Result::error)
      .def_readonly("resources", &frontend::Result::resources);

  pybind11::class_<frontend::File>(m, "File");

  pybind11::class_<frontend::Execution>(m, "Execution")
      .def("setExecutablePath", &frontend::Execution::setExecutablePath)
      .def("setExecutable", &frontend::Execution::setExecutable)
      .def("setStdin", &frontend::Execution::setStdin)
      .def("addInput", &frontend::Execution::addInput)
      .def("setArgs", &frontend::Execution::setArgs)
      .def("disableCache", &frontend::Execution::disableCache)
      .def("makeExclusive", &frontend::Execution::makeExclusive)
      .def("setLimits", &frontend::Execution::setLimits)
      .def("stdout", &frontend::Execution::stdout)
      .def("stderr", &frontend::Execution::stderr)
      .def("output", &frontend::Execution::output)
      .def("notifyStart", &frontend::Execution::notifyStart)
      .def("getResult", &frontend::Execution::getResult);

  pybind11::class_<frontend::Frontend>(m, "Frontend")
      .def(pybind11::init<std::string, int>())
      .def("provideFile", &frontend::Frontend::provideFile)
      .def("addExecution", &frontend::Frontend::addExecution)
      .def("evaluate", &frontend::Frontend::evaluate)
      .def("stopEvaluation", &frontend::Frontend::stopEvaluation)
      .def("getFileContentsAsString",
           &frontend::Frontend::getFileContentsAsString)
      .def("getFileContentsToFile", &frontend::Frontend::getFileContentsToFile);
}
