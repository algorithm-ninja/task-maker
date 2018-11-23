#ifndef UTIL_SHA256_H
#define UTIL_SHA256_H

#include <kj/array.h>
#include <array>
#include <string>
#include <vector>

#include "capnp/sha256.capnp.h"

namespace util {
static const constexpr uint32_t DIGEST_SIZE = (256 / 8);

// Represents a SHA256 hash of some string. May contain the string itself if it
// is small enough.
class SHA256_t {
  // Hash of the string.
  std::array<uint8_t, DIGEST_SIZE> hash_;

  // Contents of the string, if it is small enough.
  std::vector<uint8_t> contents_;
  bool has_contents_ = false;

 public:
  // Construct from an array of bytes representing the hash.
  explicit SHA256_t(const std::array<uint8_t, DIGEST_SIZE>& hash)
      : hash_(hash) {}

  // Construct from / convert to a hex string.
  explicit SHA256_t(const std::string& hash);
  std::string Hex() const;

  // Conversion from/to a capnproto SHA256 message.
  SHA256_t(capnproto::SHA256::Reader in);  // NOLINT
  void ToCapnp(capnproto::SHA256::Builder out) const;

  // True if the hash is all zeros.
  bool isZero() const {
    for (uint32_t i = 0; i < DIGEST_SIZE; i++) {
      if (hash_[i]) return false;
    }
    return true;
  }

  // Handles file contents.
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

  // Hashing implementation.
  friend class Hasher;
  struct Hasher {
    uint64_t operator()(const SHA256_t& h) const {
      uint64_t hash = 0;
      for (size_t i = 0; i < sizeof(uint64_t); i++) {
        hash <<= 8;
        hash |= h.hash_[i];
      }
      return hash;
    };
  };

  bool operator==(const SHA256_t& other) const { return hash_ == other.hash_; }

  static const SHA256_t ZERO;
};

// SHA256 hasher.
class SHA256 {
 public:
  SHA256() : m_block{}, m_h{} { init(); }

  // (Re)initializes the hasher.
  void init();

  // Updates the hasher with a chunk of data.
  void update(const unsigned char* message, unsigned int len);

  // Finalizes the hasher, writing the hash to digest or returning it.
  void finalize(unsigned char* digest);
  SHA256_t finalize();

  KJ_DISALLOW_COPY(SHA256);
  ~SHA256() = default;
  SHA256(SHA256&&) = default;
  SHA256& operator=(SHA256&&) = default;

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
