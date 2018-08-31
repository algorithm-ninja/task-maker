#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#pragma GCC diagnostic pop

#include "frontend/frontend.hpp"

using namespace pybind11::literals;

template <typename T>
class DestroyWithGIL {
 public:
  explicit DestroyWithGIL(T t) : t_(t) {}
  T& operator*() { return t_; }
  ~DestroyWithGIL() {
    pybind11::gil_scoped_acquire acquire;
    t_ = T();
  }

 private:
  T t_;
};

template <typename T>
DestroyWithGIL<T> destroy_with_gil(T t) {
  return DestroyWithGIL<T>(t);
}

PYBIND11_MODULE(task_maker_frontend, m) {
  m.doc() = "Task-maker frontend module";
  pybind11::class_<frontend::Resources>(m, "Resources")
      .def(pybind11::init<>())
      .def_readwrite("cpu_time", &frontend::Resources::cpu_time)
      .def_readwrite("sys_time", &frontend::Resources::sys_time)
      .def_readwrite("wall_time", &frontend::Resources::wall_time)
      .def_readwrite("memory", &frontend::Resources::memory)
      .def_readwrite("nproc", &frontend::Resources::nproc)
      .def_readwrite("nofiles", &frontend::Resources::nofiles)
      .def_readwrite("fsize", &frontend::Resources::fsize)
      .def_readwrite("memlock", &frontend::Resources::memlock)
      .def_readwrite("stack", &frontend::Resources::stack);

  pybind11::enum_<capnproto::ProcessResult::Status::Which>(m, "ResultStatus")
      .value("SUCCESS", capnproto::ProcessResult::Status::Which::SUCCESS)
      .value("SIGNAL", capnproto::ProcessResult::Status::Which::SIGNAL)
      .value("RETURN_CODE",
             capnproto::ProcessResult::Status::Which::RETURN_CODE)
      .value("TIME_LIMIT", capnproto::ProcessResult::Status::Which::TIME_LIMIT)
      .value("WALL_LIMIT", capnproto::ProcessResult::Status::Which::WALL_LIMIT)
      .value("MEMORY_LIMIT",
             capnproto::ProcessResult::Status::Which::MEMORY_LIMIT)
      .value("MISSING_FILES",
             capnproto::ProcessResult::Status::Which::MISSING_FILES)
      .value("INTERNAL_ERROR",
             capnproto::ProcessResult::Status::Which::INTERNAL_ERROR)
      .value("INVALID_REQUEST",
             capnproto::ProcessResult::Status::Which::INVALID_REQUEST);

  pybind11::class_<frontend::Result>(m, "Result")
      .def_readonly("status", &frontend::Result::status)
      .def_readonly("signal", &frontend::Result::signal)
      .def_readonly("return_code", &frontend::Result::return_code)
      .def_readonly("error", &frontend::Result::error)
      .def_readonly("resources", &frontend::Result::resources)
      .def_readonly("was_cached", &frontend::Result::was_cached)
      .def_readonly("was_killed", &frontend::Result::was_killed)
      .def("__repr__", [](const frontend::Result& res) {
        std::string message = "<Result ";
        if (res.status == capnproto::ProcessResult::Status::Which::SUCCESS)
          message += "SUCCESS";
        else if (res.status == capnproto::ProcessResult::Status::Which::SIGNAL)
          message += "SIGNAL " + std::to_string(res.signal);
        else if (res.status ==
                 capnproto::ProcessResult::Status::Which::RETURN_CODE)
          message += "RETURN_CODE " + std::to_string(res.return_code);
        else if (res.status ==
                 capnproto::ProcessResult::Status::Which::TIME_LIMIT)
          message += "TIME_LIMIT";
        else if (res.status ==
                 capnproto::ProcessResult::Status::Which::WALL_LIMIT)
          message += "WALL_LIMIT";
        else if (res.status ==
                 capnproto::ProcessResult::Status::Which::MEMORY_LIMIT)
          message += "MEMORY_LIMIT";
        else if (res.status ==
                 capnproto::ProcessResult::Status::Which::MISSING_FILES)
          message += "MISSING_FILES";
        else if (res.status ==
                 capnproto::ProcessResult::Status::Which::INTERNAL_ERROR)
          message += "INTERNAL_ERROR";
        else
          message += "UNKNOWN";
        message += ">";
        return message;
      });

  pybind11::class_<frontend::File>(m, "File")
      .def("getContentsAsString",
           [](frontend::File& f, std::function<void(std::string)> cb) {
             f.getContentsAsString(
                 [cb = destroy_with_gil(cb)](std::string s) mutable {
                   pybind11::gil_scoped_acquire acquire;
                   try {
                     (*cb)(s);
                   } catch (pybind11::error_already_set& exc) {
                     std::cerr << __FILE__ << ":" << __LINE__ << " "
                               << exc.what() << std::endl;
                     _Exit(1);
                   }
                 });
           },
           "callback"_a)
      .def("getContentsToFile", &frontend::File::getContentsToFile, "path"_a,
           "overwrite"_a = true, "exist_ok"_a = true);

  pybind11::class_<frontend::Fifo>(m, "Fifo");

  pybind11::class_<frontend::Execution>(m, "Execution")
      .def("setExecutablePath", &frontend::Execution::setExecutablePath,
           "path"_a)
      .def("setExecutable", &frontend::Execution::setExecutable, "name"_a,
           "file"_a)
      .def("setStdin", &frontend::Execution::setStdin, "file"_a)
      .def("addInput", &frontend::Execution::addInput, "name"_a, "file"_a)
      .def("addFifo", &frontend::Execution::addFifo, "name"_a, "fifo"_a)
      .def("setStdinFifo", &frontend::Execution::setStdinFifo, "fifo"_a)
      .def("setStdoutFifo", &frontend::Execution::setStdoutFifo, "fifo"_a)
      .def("setStderrFifo", &frontend::Execution::setStderrFifo, "fifo"_a)
      .def("setArgs", &frontend::Execution::setArgs, "args"_a)
      .def("disableCache", &frontend::Execution::disableCache)
      .def("makeExclusive", &frontend::Execution::makeExclusive)
      .def("setLimits", &frontend::Execution::setLimits, "limits"_a)
      .def("setExtraTime", &frontend::Execution::setExtraTime, "extra_time"_a)
      .def("stdout", &frontend::Execution::stdout,
           pybind11::return_value_policy::reference, "is_executable"_a = false)
      .def("stderr", &frontend::Execution::stderr,
           pybind11::return_value_policy::reference, "is_executable"_a = false)
      .def("output", &frontend::Execution::output,
           pybind11::return_value_policy::reference, "name"_a,
           "is_executable"_a = false)
      .def("notifyStart",
           [](frontend::Execution& f, std::function<void()> cb) {
             f.notifyStart([cb = destroy_with_gil(cb)]() mutable {
               pybind11::gil_scoped_acquire acquire;
               try {
                 (*cb)();
               } catch (pybind11::error_already_set& exc) {
                 std::cerr << __FILE__ << ":" << __LINE__ << " " << exc.what()
                           << std::endl;
                 _Exit(1);
               }
             });
           },
           "callback"_a)
      .def("getResult",
           [](frontend::Execution& f, std::function<void(frontend::Result)> cb,
              std::function<void()> err = nullptr) {
             f.getResult(
                 [cb = destroy_with_gil(cb)](frontend::Result res) mutable {
                   pybind11::gil_scoped_acquire acquire;
                   try {
                     (*cb)(res);
                   } catch (pybind11::error_already_set& exc) {
                     std::cerr << __FILE__ << ":" << __LINE__ << " "
                               << exc.what() << std::endl;
                     _Exit(1);
                   }
                 },
                 [err = destroy_with_gil(err)]() mutable {
                   pybind11::gil_scoped_acquire acquire;
                   try {
                     if (*err) (*err)();
                   } catch (pybind11::error_already_set& exc) {
                     std::cerr << __FILE__ << ":" << __LINE__ << " "
                               << exc.what() << std::endl;
                     _Exit(1);
                   }
                 });
           },
           "callback"_a, "error"_a = nullptr);

  pybind11::class_<frontend::ExecutionGroup>(m, "ExecutionGroup")
      .def("addExecution", &frontend::ExecutionGroup::addExecution,
           pybind11::return_value_policy::reference, "description"_a)
      .def("createFifo", &frontend::ExecutionGroup::createFifo,
           pybind11::return_value_policy::reference);

  pybind11::class_<frontend::Frontend>(m, "Frontend")
      .def(pybind11::init<std::string, int>())
      .def("provideFile", &frontend::Frontend::provideFile,
           pybind11::return_value_policy::reference, "path"_a, "description"_a,
           "is_executable"_a = false)
      .def("addExecution", &frontend::Frontend::addExecution,
           pybind11::return_value_policy::reference, "description"_a)
      .def("addExecutionGroup", &frontend::Frontend::addExecutionGroup,
           pybind11::return_value_policy::reference)
      .def("evaluate", &frontend::Frontend::evaluate,
           pybind11::call_guard<pybind11::gil_scoped_release>())
      .def("stopEvaluation", &frontend::Frontend::stopEvaluation);
}
