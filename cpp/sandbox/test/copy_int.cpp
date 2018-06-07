#include "plog/Log.h"
#include <cstdio>

int main() {
  int a = 0;
  scanf("%d", &a);
  printf("%d\n", a);
  fprintf(stderr, "%d\n", 2 * a);
  return 0;
}
