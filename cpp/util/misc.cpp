#include "util/misc.hpp"

namespace util {

std::vector<std::string> split(const std::string& s, char delim) {
  std::vector<std::string> elems;
  split(s, delim, std::back_inserter(elems));
  return elems;
}

std::function<bool()> setBool(bool& var) {
  return [&var]() {
    var = true;
    return true;
  };
};

std::function<bool(kj::StringPtr)> setString(std::string& var) {
  return [&var](kj::StringPtr p) {
    var = p;
    return true;
  };
};

std::function<bool(kj::StringPtr)> setInt(int& var) {
  return [&var](kj::StringPtr p) {
    var = std::stoi(std::string(p));
    return true;
  };
};

std::function<bool(kj::StringPtr)> setUint(uint32_t& var) {
  return [&var](kj::StringPtr p) {
    var = std::stoi(std::string(p));
    return true;
  };
};

void print_memory_chunk(const void* data, size_t size, size_t bytes_per_line) {
  const char* ptr = (const char*)data;
  for (size_t i = 0; i < size; i += bytes_per_line) {
    printf("%10lu\t", i);
    size_t j = 0;
    for (j = 0; j < bytes_per_line && i + j < size; j++) {
      printf("%02x ", ptr[i + j]);
    }
    for (; j < bytes_per_line; j++) {
      printf("   ");
    }
    printf("\t");
    for (j = 0; j < bytes_per_line && i + j < size; j++) {
      printf("%c", isprint(ptr[i + j]) ? ptr[i + j] : '.');
    }
    printf("\n");
  }
  printf("\n");
}

}  // namespace util
