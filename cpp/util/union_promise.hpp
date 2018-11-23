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

// Utility class for dependency management.
// One or more promises can be added to the builder with AddPromise before
// calling Finalize. Finalize then returns a promise that resolves when all the
// added promises resolve (or some resolve and some others fail, if fatalFailure
// is set to false), or fails if any promise fails and fatalFailure is true.
class UnionPromiseBuilder {
 public:
  explicit UnionPromiseBuilder(bool fatalFailure = true);

  // Define callbacks that will be called when the promise returned by Finalize
  // is ready/fails. Equivalent to calling .then(on_ready, on_failure) on the
  // promise returned by Finalize, except that they can only be called before
  // calling Finalize.
  void OnReady(const std::function<void()>& on_ready);
  void OnFailure(const std::function<void(kj::Exception)>& on_failure);

  // Adds a promise as a dependency to this builder, possibly having a name for
  // debugging purposes.
  kj::Promise<void> AddPromise(kj::Promise<void> p,
                               const std::string& what = "unanamed");

  // Finalizes the builder and returns the "union" promise. Calling any other
  // method of the builder after Finalize() triggers undefined behaviour.
  kj::Promise<void> Finalize() && KJ_WARN_UNUSED_RESULT;

 private:
  kj::PromiseFulfillerPair<void> p_;
  detail::UnionPromiseBuilderInfo* info_ = nullptr;
  kj::PromiseFulfiller<void>* fulfiller_ = nullptr;
};

}  // namespace util
#endif
