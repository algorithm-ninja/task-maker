#ifndef MANAGER_EVALUATION_INFO_HPP
#define MANAGER_EVALUATION_INFO_HPP

#include <map>
#include <string>
#include <thread>
#include "core/core.hpp"
#include "manager/evaluation.hpp"
#include "manager/event_queue.hpp"
#include "manager/generation.hpp"
#include "manager/source_file.hpp"

namespace manager {

struct EvaluationInfo {
  std::unique_ptr<core::Core> core;
  std::unique_ptr<manager::EventQueue> queue;
  std::unique_ptr<manager::Generation> generation;
  std::unique_ptr<manager::Evaluation> evaluation;
  std::map<std::string, std::unique_ptr<manager::SourceFile>> source_files;
  bool is_remote;

  std::thread running_thread;
};
}  // namespace manager

#endif  // MANAGER_EVALUATION_INFO_HPP