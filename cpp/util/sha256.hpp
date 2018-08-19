#ifndef UTIL_SHA256_H
#define UTIL_SHA256_H

#include <array>
#include <string>

#include "capnp/sha256.capnp.h"

namespace util {
namespace {
static const constexpr uint32_t DIGEST_SIZE = (256 / 8);
}

class SHA256_t {
  std::array<uint8_t, DIGEST_SIZE> hash_;

 public:
  explicit SHA256_t(const std::array<uint8_t, DIGEST_SIZE>& hash)
      : hash_(hash) {}
  SHA256_t(capnproto::SHA256::Reader in);
  void ToCapnp(capnproto::SHA256::Builder out) const;

  std::string Hex() const;

  bool isZero() const {
    for (uint32_t i = 0; i < DIGEST_SIZE; i++)
      if (hash_[i]) return false;
    return true;
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
