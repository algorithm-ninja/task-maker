#ifndef UTIL_SHA256_H
#define UTIL_SHA256_H

#include <array>
#include <string>

#include "proto/sha256.pb.h"

namespace util {

class SHA256_t;

class SHA256 {
  static const constexpr uint32_t DIGEST_SIZE = (256 / 8);
  static const constexpr uint32_t SHA224_256_BLOCK_SIZE = (512 / 8);

 public:
  SHA256() : m_block{}, m_h{} { init(); }
  void init();
  void update(const unsigned char* message, unsigned int len);
  void finalize(unsigned char* digest);
  void finalize(SHA256_t* digest);

 private:
  void transform(const unsigned char* message, unsigned int block_nb);
  unsigned int m_tot_len{0};
  unsigned int m_len{0};
  unsigned char m_block[2 * SHA224_256_BLOCK_SIZE];
  uint32_t m_h[8];
  friend class SHA256_t;
};

class SHA256_t : public std::array<uint8_t, SHA256::DIGEST_SIZE> {
 public:
  std::string Hex() const;
};

void SHA256ToProto(const SHA256_t& in, proto::SHA256* out);
void ProtoToSHA256(const proto::SHA256& in, SHA256_t* out);

}  // namespace util
#endif
