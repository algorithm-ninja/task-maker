#ifndef MANAGER_EVALUATION_HPP
#define MANAGER_EVALUATION_HPP

#include "manager/source_file.hpp"

namespace manager {

class Evaluation {
  virtual void Evaluate(SourceFile* solution) = 0;
};

}  // namespace manager

#endif  // MANAGER_EVALUATION_HPP
