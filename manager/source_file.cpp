#include "manager/source_file.hpp"

namespace manager {

// static
std::unique_ptr<SourceFile> SourceFile::FromProto(
    EventQueue* queue, core::Core* core, const proto::SourceFile& source,
    bool fatal_failures) {
  // return absl::make_unique<...>();
  return nullptr;
}
}  // namespace manager
