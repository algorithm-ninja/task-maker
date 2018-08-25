#ifndef UTIL_MISC_HPP
#define UTIL_MISC_HPP
#include <functional>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include <kj/async.h>
#include <kj/debug.h>
#include <kj/string.h>

namespace util {
template <typename Out>
void split(const std::string& s, char delim, Out result) {
  std::stringstream ss(s);
  std::string item;
  while (std::getline(ss, item, delim)) {
    if (!item.empty()) *(result++) = item;
  }
}

inline std::vector<std::string> split(const std::string& s, char delim) {
  std::vector<std::string> elems;
  split(s, delim, std::back_inserter(elems));
  return elems;
}

inline std::function<bool()> setBool(bool& var) {
  return [&var]() {
    var = true;
    return true;
  };
};

inline std::function<bool(kj::StringPtr)> setString(std::string& var) {
  return [&var](kj::StringPtr p) {
    var = p;
    return true;
  };
};

inline std::function<bool(kj::StringPtr)> setInt(int& var) {
  return [&var](kj::StringPtr p) {
    var = std::stoi(std::string(p));
    return true;
  };
};

inline std::function<bool(kj::StringPtr)> setUint(uint32_t& var) {
  return [&var](kj::StringPtr p) {
    var = std::stoi(std::string(p));
    return true;
  };
};

class UnionPromiseBuilder {
  struct Info {
    bool fatalFailure;
    size_t resolved = 0;
    std::vector<kj::Promise<void>> promises;
    std::vector<kj::PromiseFulfiller<void>*> fulfillers;
    bool finalized = false;
    std::function<void()> on_ready;
    std::function<void(kj::Exception)> on_failure;
#ifdef DEBUG_UPB
    std::multiset<std::string> pending;
#endif
  };

 public:
  UnionPromiseBuilder(bool fatalFailure = true)
      : p_(kj::newPromiseAndFulfiller<void>()) {
    auto info = kj::heap<Info>();
    info_ = info.get();
    info_->fatalFailure = fatalFailure;
    fulfiller_ = p_.fulfiller.get();
    p_.promise = p_.promise.attach(std::move(info), std::move(p_.fulfiller));
  }

  void OnReady(std::function<void()> on_ready) { info_->on_ready = on_ready; }
  void OnFailure(std::function<void(kj::Exception)> on_failure) {
    info_->on_failure = on_failure;
  }

  kj::Promise<void> AddPromise(kj::Promise<void> p,
                               std::string what = "unanamed") {
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
                [
#ifdef DEBUG_UPB
                    this,
#endif
                    info = info_, fulfiller = fulfiller_, what,
                    index = info_->promises.size(),
                    propagate_fulfiller = std::move(pf.fulfiller)]() mutable {
                  info->resolved++;
#ifdef DEBUG_UPB
                  info->pending.erase(info->pending.find(what));
                  if (!info->fatalFailure) {
                    KJ_DBG("XXX Promise success", info->resolved,
                           info->promises.size(), what);
                    PrintRemaining();
                  }
#endif
                  if (info->finalized &&
                      info->resolved == info->promises.size()) {
                    fulfiller->fulfill();
                    if (info->on_ready) info->on_ready();
                  }
                  propagate_fulfiller->fulfill();
                  info->fulfillers[index] = nullptr;
                },
                [
#ifdef DEBUG_UPB
                    this,
#endif
                    fulfiller = fulfiller_, info = info_, ff,
                    index = info_->promises.size(),
                    idx = info_->promises.size(),
                    what](kj::Exception exc) mutable {
#ifdef DEBUG_UPB
                  info->pending.erase(info->pending.find(what));
#endif
                  if (info->fatalFailure) {
                    fulfiller->reject(kj::cp(exc));
                    if (info->on_failure) info->on_failure(kj::cp(exc));
                    for (auto off : info->fulfillers)
                      if (off) off->fulfill();
                  } else {
                    info->resolved++;
#ifdef DEBUG_UPB
                    KJ_DBG("XXX Promise failed", info->resolved,
                           info->promises.size(), what);
                    PrintRemaining();
#endif
                    if (info->finalized &&
                        info->resolved == info->promises.size()) {
                      fulfiller->fulfill();
                      if (info->on_ready) info->on_ready();
                    }
                  }
                  ff->fulfill();
                  info->fulfillers[index] = nullptr;
                  return exc;
                })
            .eagerlyEvaluate(nullptr));
    return std::move(pf.promise);
  }

  kj::Promise<void> Finalize() && KJ_WARN_UNUSED_RESULT {
    info_->finalized = true;
    if (info_->resolved == info_->promises.size()) {
      fulfiller_->fulfill();
      if (info_->on_ready) info_->on_ready();
    }
    return std::move(p_.promise);
  }

  int GetMissing() { return info_->promises.size() - info_->resolved; }

#ifdef DEBUG_UPB
  void PrintRemaining() {
    KJ_DBG("YYY Pending promises:");
    int i = 0;
    for (std::string w : info_->pending) {
      KJ_DBG("YYY    ", w);
      if (i++ > 5) break;
    }
  }
#endif

 private:
  kj::PromiseFulfillerPair<void> p_;
  // TODO use std::move(this) rather that kj::heap
  Info* info_ = nullptr;
  kj::PromiseFulfiller<void>* fulfiller_ = nullptr;
};

}  // namespace util
#endif
