#ifndef UTIL_UNION_PROMISE
#define UTIL_UNION_PROMISE
#include <kj/async.h>
#include <functional>
#include <vector>
#include <string>

namespace util {
namespace detail {
struct UnionPromiseBuilderInfo;
}

class UnionPromiseBuilder {
 public:
  explicit UnionPromiseBuilder(bool fatalFailure = true);
  void OnReady(std::function<void()> on_ready);
  void OnFailure(std::function<void(kj::Exception)> on_failure);
  kj::Promise<void> AddPromise(kj::Promise<void> p,
                               std::string what = "unanamed");
  kj::Promise<void> Finalize() && KJ_WARN_UNUSED_RESULT;

 private:
  kj::PromiseFulfillerPair<void> p_;
  detail::UnionPromiseBuilderInfo* info_ = nullptr;
  kj::PromiseFulfiller<void>* fulfiller_ = nullptr;
};

}  // namespace util
#endif
