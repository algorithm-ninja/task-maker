#ifndef MANAGER_IOI_FORMAT_HPP
#define MANAGER_IOI_FORMAT_HPP

#include <map>
#include "manager/evaluation_info.hpp"
#include "proto/manager.grpc.pb.h"

namespace manager {

EvaluationInfo setup_request(const proto::EvaluateTaskRequest& request);
void run_core(const proto::EvaluateTaskRequest& request, int64_t current_id,
              std::map<int64_t, EvaluationInfo>* running);
}  // namespace manager

#endif  // MANAGER_IOI_FORMAT_HPP