#include <stdlib.h>
#include <chrono>
#include <vector>

int main(int argc, char** argv) {
  const constexpr int sz = 10240;
  std::clock_t startcputime = std::clock();
  std::vector<int> v;
  v.resize(sz, 0);
  int i = 0;
  while ((std::clock() - startcputime) < atof(argv[1]) * CLOCKS_PER_SEC) {
    for (int j = 0; j < i; j++) {
      v[j] += i;
    }
    i = (i + 1) % sz;
  }
  return 0;
}
