#ifndef MANAGER_TERRY_FORMAT_HPP
#define MANAGER_TERRY_FORMAT_HPP

#include <map>
#include "manager/evaluation_info.hpp"
#include "proto/manager.grpc.pb.h"

namespace manager {

EvaluationInfo setup_request(const proto::EvaluateTerryTaskRequest& request);
void run_core(const proto::EvaluateTerryTaskRequest& request,
              int64_t current_id, std::map<int64_t, EvaluationInfo>* running);
}  // namespace manager

#endif  // MANAGER_TERRY_FORMAT_HPP