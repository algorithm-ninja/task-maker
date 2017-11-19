#include "sandbox/sandbox.hpp"

#include <iostream>

namespace sandbox {

Sandbox::store_t* Sandbox::Boxes_() {
  static store_t* boxes = new store_t;
  return boxes;
}

void Sandbox::Register_(Sandbox::create_t create, Sandbox::score_t score) {
  Boxes_()->emplace_back(create, score);
}

std::unique_ptr<Sandbox> Sandbox::Create() {
  static unsigned best_sandbox = -1U;
  const store_t& boxes = *Boxes_();
  if (best_sandbox == -1U) {
    int best_score = 0;
    for (unsigned i = 0; i < boxes.size(); i++) {
      int score = boxes[i].second();
      if (score > best_score) {
        best_score = score;
        best_sandbox = i;
      }
    }
  }
  if (best_sandbox == -1U) {
    std::cerr << "No sandbox could be found" << std::endl;
    return nullptr;
  }
  return std::unique_ptr<Sandbox>(boxes[best_sandbox].first());
}

}  // namespace sandbox
