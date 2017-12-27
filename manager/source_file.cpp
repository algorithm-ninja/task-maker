#include "manager/source_file.hpp"

namespace manager {

// static
std::unique_ptr<SourceFile> SourceFile::FromProto(
    EventQueue* queue, core::Core* core, const proto::SourceFile& source,
    const proto::GraderInfo& grader, bool fatal_failures) {
  switch (source.language()) {
    case proto::CPP:
    case proto::C:
    case proto::PASCAL:
      return absl::make_unique<CompiledSourceFile>(queue, core, source,
                                                   grader, fatal_failures);
    default:
      return absl::make_unique<NotCompiledSourceFile>(queue, core, source,
                                                      fatal_failures);
  }
}

CompiledSourceFile::CompiledSourceFile(
    EventQueue *queue, core::Core *core, const proto::SourceFile &source,
    const proto::GraderInfo& grader, bool fatal_failures)
    : SourceFile(core, queue, fatal_failures) {
  std::string compiler;
  std::vector<std::string> args;

  switch (source.language()) {
    case proto::CPP:
      compiler = "/usr/bin/g++";
      args = {"-O2", "-std=c++14", "-DEVAL", "-Wall", "-o", "compiled",
              source.path()};
      break;
    case proto::C:
      compiler = "/usr/bin/gcc";
      args = {"-O2", "-std=c11", "-DEVAL", "-Wall", "-o", "compiled",
              source.path()};
      break;
    case proto::PASCAL:
      compiler = "/usr/bin/fpc";
      args = {"-dEVAL", "-XS", "-O2", "-ocompiled", source.path()};
      break;
    default:
      throw std::domain_error("Cannot compiled " + source.path() + " because "
          "unknown compilation command");
  }
  for (auto dep : grader.files())
    args.push_back(dep.name());

  compilation_ = core->AddExecution(
      "Compilation of " + source.path(), compiler, args);

  compilation_->SetCallback([queue](const core::TaskStatus& status) -> bool {
    if (status.type == core::TaskStatus::FILE_LOAD)
      return true;

    if (status.event == core::TaskStatus::START) {
      queue->CompilationRunning(source.path());
      return true;
    }
    if (status.event == core::TaskStatus::SUCCESS) {
      queue->CompilationDone(source.path(), status.message + "\n"
        + status.execution_info->Stderr()->Contents(1024*1024));
      return true;
    }
    if (status.event == core::TaskStatus::FAILURE) {
      queue->CompilationFailure(source.path(), status.message + "\n"
          + status.execution_info->Stderr()->Contents(1024*1024));
      return !fatal_failures_;
    }
    return true;
  });

  for (auto dep : source.deps())
    compilation_->Input(dep.name(), core->LoadFile(dep.name(), dep.path()));
  for (auto dep : grader.files())
    compilation_->Input(dep.name(), core->LoadFile(dep.name(), dep.path()));

  compiled_ = compilation_->Output("compiled", "Compiled file of " +
      source.path());
  queue->CompilationWaiting(source.path());
}

core::Execution* CompiledSourceFile::execute(
    const std::string& description, const std::vector<std::string>& args) {
  core::Execution* execution = core_->AddExecution(description, "program", args);
  execution->Input("program", compiled_);
  return execution;
}

NotCompiledSourceFile::NotCompiledSourceFile(EventQueue *queue,
                                             core::Core *core,
                                             const proto::SourceFile &source,
                                             bool fatal_failures)
    : SourceFile(core, queue, fatal_failures) {
  core_ = core;
  queue_ = queue;
  for (auto dep : source.deps())
    runtime_deps_.push_back(core->LoadFile(dep.name(), dep.path()));
  program_ = core->LoadFile(source.path(), source.path());
}

core::Execution* NotCompiledSourceFile::execute(
    const std::string& description, const std::vector<std::string>& args) {
  core::Execution* execution = core_->AddExecution(description, "program", args);
  execution->Input("program", program_);
  for (auto dep : runtime_deps_)
    execution->Input(dep->Description(), dep);
  return execution;
}

}  // namespace manager
