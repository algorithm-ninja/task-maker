#ifndef UTIL_SHA256_H
#define UTIL_SHA256_H

#include <kj/array.h>
#include <array>
#include <string>
#include <vector>

#include "capnp/sha256.capnp.h"

namespace util {
namespace {
static const constexpr uint32_t DIGEST_SIZE = (256 / 8);
}

class SHA256_t {
  std::array<uint8_t, DIGEST_SIZE> hash_;
  std::vector<uint8_t> contents_;
  bool has_contents_ = false;

 public:
  explicit SHA256_t(const std::array<uint8_t, DIGEST_SIZE>& hash)
      : hash_(hash) {}
  explicit SHA256_t(const std::string& hash);
  SHA256_t(capnproto::SHA256::Reader in);
  void ToCapnp(capnproto::SHA256::Builder out) const;

  std::string Hex() const;

  bool isZero() const {
    for (uint32_t i = 0; i < DIGEST_SIZE; i++)
      if (hash_[i]) return false;
    return true;
  }

  kj::ArrayPtr<const uint8_t> getContents() const {
    return {contents_.data(), contents_.size()};
  }

  bool hasContents() const { return has_contents_; }

  void setContents(const uint8_t* ptr, size_t size) {
    contents_.assign(ptr, ptr + size);
    has_contents_ = true;
  }

  void setContents(kj::ArrayPtr<const uint8_t> data) {
    return setContents(data.begin(), data.size());
  }

  void setContents(const std::vector<uint8_t>& data) {
    return setContents(data.data(), data.size());
  }

  friend class Hasher;
  struct Hasher {
    uint64_t operator()(const SHA256_t& h) const {
      uint64_t hash = 0;
      for (int i = 0; i < 8; i++) {
        hash <<= 8;
        hash |= h.hash_[i];
      }
      return hash;
    };
  };

  bool operator==(const SHA256_t& other) const { return hash_ == other.hash_; }

  static const SHA256_t ZERO;
};

class SHA256 {
 public:
  SHA256() : m_block{}, m_h{} { init(); }
  void init();
  void update(const unsigned char* message, unsigned int len);
  void finalize(unsigned char* digest);
  SHA256_t finalize();
  KJ_DISALLOW_COPY(SHA256);

 private:
  static const constexpr uint32_t SHA224_256_BLOCK_SIZE = (512 / 8);
  void transform(const unsigned char* message, unsigned int block_nb);
  unsigned int m_tot_len{0};
  unsigned int m_len{0};
  unsigned char m_block[2 * SHA224_256_BLOCK_SIZE];
  uint32_t m_h[8];
};

}  // namespace util
#endif
