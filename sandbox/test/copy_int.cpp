#include "glog/logging.h"
#include <cstdio>

int main() {
  int a = 0;
  CHECK(1 == scanf("%d", &a));  // NOLINT
  CHECK(0 <= printf("%d\n", a));  // NOLINT
  CHECK(0 <= fprintf(stderr, "%d\n", 2 * a));  // NOLINT
  return 0;
}
