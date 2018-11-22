#include "util/union_promise.hpp"
#include <kj/debug.h>

#ifdef DEBUG_UPB
#include <set>
#endif

namespace util {

namespace detail {
struct UnionPromiseBuilderInfo {
  bool fatalFailure = true;
  size_t resolved = 0;
  std::vector<kj::Promise<void>> promises;
  std::vector<kj::PromiseFulfiller<void>*> fulfillers;
  bool finalized = false;
  std::vector<std::function<void()>> on_ready;
  std::vector<std::function<void(kj::Exception)>> on_failure;
#ifdef DEBUG_UPB
  std::multiset<std::string> pending;
#endif
};
}  // namespace detail

#ifdef DEBUG_UPB
namespace {
void PrintRemaining(detail::UnionPromiseBuilderInfo* info) {
  KJ_DBG("YYY Pending promises:");
  int i = 0;
  for (std::string w : info->pending) {
    KJ_DBG("YYY    ", w);
    if (i++ > 5) break;
  }
}
}  // namespace
#endif

UnionPromiseBuilder::UnionPromiseBuilder(bool fatalFailure)
    : p_(kj::newPromiseAndFulfiller<void>()) {
  auto info = kj::heap<detail::UnionPromiseBuilderInfo>();
  info_ = info.get();
  info_->fatalFailure = fatalFailure;
  fulfiller_ = p_.fulfiller.get();
  p_.promise = p_.promise.attach(std::move(info), std::move(p_.fulfiller));
}

void UnionPromiseBuilder::OnReady(const std::function<void()>& on_ready) {
  info_->on_ready.push_back(on_ready);
}
void UnionPromiseBuilder::OnFailure(
    const std::function<void(kj::Exception)>& on_failure) {
  info_->on_failure.push_back(on_failure);
}

kj::Promise<void> UnionPromiseBuilder::AddPromise(kj::Promise<void> p,
                                                  const std::string& what) {
  KJ_LOG(INFO, "Adding promise " + what);
  kj::PromiseFulfillerPair<void> pf = kj::newPromiseAndFulfiller<void>();
  auto ff = pf.fulfiller.get();
  info_->fulfillers.push_back(ff);
#ifdef DEBUG_UPB
  info_->pending.insert(what);
#endif
  info_->promises.push_back(
      std::move(p)
          .then(
              [info = info_, fulfiller = fulfiller_, what,
               index = info_->promises.size(),
               propagate_fulfiller = std::move(pf.fulfiller)]() mutable {
                info->resolved++;
#ifdef DEBUG_UPB
                info->pending.erase(info->pending.find(what));
                if (!info->fatalFailure) {
                  KJ_DBG("XXX Promise success", info->resolved,
                         info->promises.size(), what);
                  PrintRemaining(info);
                }
#endif
                if (info->finalized &&
                    info->resolved == info->promises.size()) {
                  fulfiller->fulfill();
                  for (const auto& f : info->on_ready) f();
                }
                propagate_fulfiller->fulfill();
                info->fulfillers[index] = nullptr;
              },
              [fulfiller = fulfiller_, info = info_, ff,
               index = info_->promises.size(), idx = info_->promises.size(),
               what](kj::Exception exc) mutable {
#ifdef DEBUG_UPB
                info->pending.erase(info->pending.find(what));
#endif
                if (info->fatalFailure) {
                  fulfiller->reject(kj::cp(exc));
                  for (const auto& f : info->on_failure) f(kj::cp(exc));
                  for (auto off : info->fulfillers) {
                    if (off) off->fulfill();
                  }
                } else {
                  info->resolved++;
#ifdef DEBUG_UPB
                  KJ_DBG("XXX Promise failed", info->resolved,
                         info->promises.size(), what);
                  PrintRemaining(info);
#endif
                  if (info->finalized &&
                      info->resolved == info->promises.size()) {
                    fulfiller->fulfill();
                    for (const auto& f : info->on_ready) f();
                  }
                }
                ff->fulfill();
                info->fulfillers[index] = nullptr;
                return exc;
              })
          .eagerlyEvaluate(nullptr));
  return std::move(pf.promise);
}

kj::Promise<void> UnionPromiseBuilder::Finalize() && {
  info_->finalized = true;
  if (info_->resolved == info_->promises.size()) {
    fulfiller_->fulfill();
    for (const auto& f : info_->on_ready) f();
  }
  return std::move(p_.promise);
}

}  // namespace util
