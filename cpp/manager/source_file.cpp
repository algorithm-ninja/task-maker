#include <sys/stat.h>

#include "glog/logging.h"
#include "manager/source_file.hpp"
#include "util/which.hpp"

namespace manager {

namespace {

class CompiledSourceFile : public SourceFile {
 public:
  CompiledSourceFile(EventQueue* queue, core::Core* core,
                     const proto::SourceFile& source, const std::string& name,
                     const std::string& exe_name, bool fatal_failures,
                     bool keep_sandbox, proto::CacheMode cache_mode,
                     const std::string& executor,
                     const proto::GraderInfo* grader = nullptr);

  core::Execution* execute(const std::string& description,
                           const std::vector<std::string>& args,
                           bool keep_sandbox) override;

  void WriteTo(const std::string& path, bool overwrite,
               bool exist_ok) override {
    executable_->WriteTo(path, overwrite, exist_ok);
  }

 protected:
  core::Execution* compilation_;
};

class NotCompiledSourceFile : public SourceFile {
 public:
  NotCompiledSourceFile(EventQueue* queue, core::Core* core,
                        const proto::SourceFile& source,
                        const std::string& name, const std::string& exe_name,
                        bool fatal_failures);

  core::Execution* execute(const std::string& description,
                           const std::vector<std::string>& args,
                           bool keep_sandbox) override;

  void WriteTo(const std::string& path, bool overwrite,
               bool exist_ok) override {
    executable_->WriteTo(path, overwrite, exist_ok);
  }

 protected:
  std::vector<core::FileID*> runtime_deps_;
};

}  // namespace

// static
std::unique_ptr<SourceFile> SourceFile::FromProto(
    EventQueue* queue, core::Core* core, const proto::SourceFile& source,
    bool fatal_failures, bool keep_sandbox, proto::CacheMode cache_mode,
    const std::string& executor, const proto::GraderInfo* grader) {
  // the name of the source file is mainly used in the evaluation process, it
  // will be sent to the queue
  std::string name =
      source.path().substr(source.path().find_last_of("/\\") + 1);
  std::string exe_name;
  if (source.write_bin_to().empty())
    exe_name = name.substr(0, name.find_last_of('.'));
  else
    exe_name = source.write_bin_to().substr(
        source.write_bin_to().find_last_of("/\\") + 1);
  switch (source.language()) {
    case proto::CPP:
    case proto::C:
    case proto::PASCAL:
    case proto::RUST:
      return std::make_unique<CompiledSourceFile>(
          queue, core, source, std::move(name), std::move(exe_name),
          fatal_failures, keep_sandbox, cache_mode, executor, grader);
    default:
      return std::make_unique<NotCompiledSourceFile>(
          queue, core, source, std::move(name), std::move(exe_name),
          fatal_failures);
  }
}

CompiledSourceFile::CompiledSourceFile(
    EventQueue* queue, core::Core* core, const proto::SourceFile& source,
    const std::string& name, const std::string& exe_name, bool fatal_failures,
    bool keep_sandbox, proto::CacheMode cache_mode, const std::string& executor,
    const proto::GraderInfo* grader)
    : SourceFile(core, queue, name, exe_name, fatal_failures) {
  std::string compiler;
  std::vector<std::string> args;

  core::FileID* input_file =
      core->LoadFile("Source file for " + name_, source.path());

  bool use_compiler_cache = cache_mode == proto::CacheMode::ALL;

  switch (source.language()) {
    // TODO(edomora97) use $CXX $CC $CFLAGS and $CXXFLAGS if provided
    case proto::CPP:
      compiler = util::which("c++", use_compiler_cache);
      args = {"-O2", "-std=c++14", "-DEVAL", "-Wall", "-o", exe_name, name_};
      switch (source.target_arch()) {
        case proto::Arch::I686:
          args.emplace_back("-m32");
          break;
        default:
          break;
      }
      break;
    case proto::C:
      compiler = util::which("cc", use_compiler_cache);
      args = {"-O2", "-std=c11", "-DEVAL", "-Wall", "-o", exe_name, name_};
      switch (source.target_arch()) {
        case proto::Arch::I686:
          args.emplace_back("-m32");
          break;
        default:
          break;
      }
      break;
    case proto::PASCAL:
      compiler = util::which("fpc", use_compiler_cache);
      args = {"-dEVAL", "-XS", "-O2", "-o" + exe_name, name_};
      if (source.target_arch() != proto::Arch::DEFAULT)
        throw std::domain_error(
            "Cannot target a Pascal executable to a specific architecture yet");
      break;
    case proto::RUST:
      compiler = util::which("rustc", use_compiler_cache);
      args = {"--cfg", "EVAL", "-O", "-o", exe_name, name_};
      if (source.target_arch() != proto::Arch::DEFAULT)
        throw std::domain_error(
            "Cannot target a Rust executable to a specific architecture yet");
      break;
    default:
      throw std::domain_error("Cannot compile " + source.path() +
                              ": unknown language");
  }
  if (compiler.empty()) {
    throw std::domain_error(
        "Cannot compile " + source.path() + ": compiler for " +
        proto::Language_Name(source.language()) + " not found");
  }
  if (grader) {
    switch (source.language()) {
      case proto::CPP:
      case proto::C:
      case proto::PASCAL:
        for (const auto& dep : grader->files()) args.push_back(dep.name());
        break;
      default:
        break;
    }
  }
  compilation_ = core->AddExecution("Compilation of " + source.path(), compiler,
                                    args, keep_sandbox);
  if (cache_mode == proto::ALL)
    compilation_->SetCachingMode(core::Execution::SAME_EXECUTOR);
  else
    compilation_->SetCachingMode(core::Execution::NEVER);
  if (!executor.empty()) compilation_->SetExecutor(executor);
  compilation_->Input(name_, input_file);
  executable_ =
      compilation_->Output(exe_name, "Compiled file of " + source.path());
  executable_->MarkExecutable();
  queue->CompilationWaiting(name_);

  compilation_->SetCallback([this, queue, source,
                             name](const core::TaskStatus& status) -> bool {
    if (status.event == core::TaskStatus::FAILURE) {
      queue->CompilationFailure(name_, status.message,
                                status.execution_info->Cached());
      return false;
    }
    if (status.type == core::TaskStatus::FILE_LOAD) return true;

    if (status.event == core::TaskStatus::START)
      queue->CompilationRunning(name_);
    if (status.event == core::TaskStatus::SUCCESS) {
      if (status.execution_info->Success()) {
        queue->CompilationDone(
            name_, status.execution_info->Stderr()->Contents(1024 * 1024),
            status.execution_info->Cached());
      } else {
        queue->CompilationFailure(
            name_,
            status.message + "\n" +
                status.execution_info->Stderr()->Contents(1024 * 1024),
            status.execution_info->Cached());
        return !fatal_failures_;
      }
    }
    if (status.event == core::TaskStatus::FINISH_SUCCESS) {
      if (status.execution_info->Success()) {
        if (!source.write_bin_to().empty()) {
          executable_->WriteTo(source.write_bin_to());
          chmod(source.write_bin_to().c_str(), S_IRUSR | S_IXUSR);
          LOG(INFO) << "Compiled program copied to " << source.write_bin_to();
        }
      }
    }
    return true;
  });

  for (const auto& dep : source.deps())
    compilation_->Input(dep.name(), core->LoadFile(dep.name(), dep.path()));
  if (grader) {
    for (const auto& dep : grader->files())
      compilation_->Input(dep.name(), core->LoadFile(dep.name(), dep.path()));
  }
}

core::Execution* CompiledSourceFile::execute(
    const std::string& description, const std::vector<std::string>& args,
    bool keep_sandbox) {
  core::Execution* execution =
      core_->AddExecution(description, exe_name_, args, keep_sandbox);
  execution->Input(exe_name_, executable_);
  return execution;
}

NotCompiledSourceFile::NotCompiledSourceFile(
    EventQueue* queue, core::Core* core, const proto::SourceFile& source,
    const std::string& name, const std::string& exe_name, bool fatal_failures)
    : SourceFile(core, queue, name, exe_name, fatal_failures) {
  core_ = core;
  queue_ = queue;
  for (const auto& dep : source.deps())
    runtime_deps_.push_back(core->LoadFile(dep.name(), dep.path()));
  executable_ = core->LoadFile(source.path(), source.path());
  executable_->MarkExecutable();
  executable_->SetCallback(
      [this, queue, source](const core::TaskStatus& status) -> bool {
        if (status.event == core::TaskStatus::FAILURE) {
          queue->CompilationFailure(name_, "Error loading file",
                                    status.execution_info->Cached());
          return false;
        }
        if (status.event == core::TaskStatus::SUCCESS) {
          // the file is not compiled so it doesn't came from the cache
          queue->CompilationDone(name_, "", false);
        }
        if (status.event == core::TaskStatus::FINISH_SUCCESS) {
          if (!source.write_bin_to().empty()) {
            executable_->WriteTo(source.write_bin_to());
            chmod(source.write_bin_to().c_str(), S_IRUSR | S_IXUSR);
            LOG(INFO) << "Source program copied to " << source.write_bin_to();
          }
        }
        return true;
      });
  queue->CompilationWaiting(name_);
}

core::Execution* NotCompiledSourceFile::execute(
    const std::string& description, const std::vector<std::string>& args,
    bool keep_sandbox) {
  core::Execution* execution =
      core_->AddExecution(description, exe_name_, args, keep_sandbox);
  execution->Input(exe_name_, executable_);
  for (auto dep : runtime_deps_) execution->Input(dep->Description(), dep);
  return execution;
}

}  // namespace manager
