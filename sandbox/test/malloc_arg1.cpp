#include <stdlib.h>
int main(int argc, char** argv) {
  int* data = (int*)malloc(atoi(argv[1]) * sizeof(int) * 1024 * 1024LL);
  for (long long i = 0; i < atoi(argv[1]) * 1024 * 1024LL; i++) data[i] = i;
  return 0;
}
