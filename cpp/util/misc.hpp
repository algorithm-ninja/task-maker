#ifndef UTIL_MISC_HPP
#define UTIL_MISC_HPP
#include <functional>
#include <sstream>
#include <string>
#include <vector>

#include <kj/async.h>
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

class UnionPromiseBuilder {
  struct Info {
    size_t resolved = 0;
    std::vector<kj::Promise<void>> promises;
    bool finalized = false;
  };

 public:
  UnionPromiseBuilder() : p_(kj::newPromiseAndFulfiller<void>()) {
    auto info = kj::heap<Info>();
    info_ = info.get();
    fulfiller_ = p_.fulfiller.get();
    p_.promise = p_.promise.attach(std::move(info), std::move(p_.fulfiller));
  }

  void AddPromise(kj::Promise<void> p) {
    info_->promises.push_back(std::move(p).eagerlyEvaluate(nullptr).then(
        [info = info_, fulfiller = fulfiller_]() {
          info->resolved++;
          if (info->finalized && info->resolved == info->promises.size()) {
            fulfiller->fulfill();
          }
        }));
  }

  kj::Promise<void> Finalize() && {
    info_->finalized = true;
    if (info_->resolved == info_->promises.size()) {
      fulfiller_->fulfill();
    }
    return std::move(p_.promise);
  }

 private:
  kj::PromiseFulfillerPair<void> p_;
  Info* info_ = nullptr;
  kj::PromiseFulfiller<void>* fulfiller_ = nullptr;
};

}  // namespace util
#endif
