#ifndef UTIL_UNION_PROMISE
#define UTIL_UNION_PROMISE
#include <kj/async.h>
#include <functional>
#include <string>
#include <vector>

namespace util {
namespace detail {
struct UnionPromiseBuilderInfo;
}  // namespace detail

class UnionPromiseBuilder {
 public:
  explicit UnionPromiseBuilder(bool fatalFailure = true);
  void OnReady(const std::function<void()>& on_ready);
  void OnFailure(const std::function<void(kj::Exception)>& on_failure);
  kj::Promise<void> AddPromise(kj::Promise<void> p,
                               const std::string& what = "unanamed");
  kj::Promise<void> Finalize() && KJ_WARN_UNUSED_RESULT;

 private:
  kj::PromiseFulfillerPair<void> p_;
  detail::UnionPromiseBuilderInfo* info_ = nullptr;
  kj::PromiseFulfiller<void>* fulfiller_ = nullptr;
};

}  // namespace util
#endif
