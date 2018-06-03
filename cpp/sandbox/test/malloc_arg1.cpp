#include <chrono>
#include <cstdlib>

int main(int argc, char** argv) {
  std::clock_t startcputime = std::clock();
  const size_t size = atoi(argv[1]) * 1024 * 1024LL;
  const size_t per_iter = 1024;
  size_t to_alloc = size;
  int* data;
  size_t num_iterations = size / per_iter;
  while ((std::clock() - startcputime) < 1 * CLOCKS_PER_SEC) {
    size_t alloc = per_iter;
    if (alloc > to_alloc) alloc = to_alloc;
    if (alloc > 0)
      data = (int*)malloc(alloc * sizeof(int));
    to_alloc -= alloc;
    std::clock_t start = std::clock();
    while ((std::clock() - start) < 0.5/num_iterations * CLOCKS_PER_SEC)
      for (size_t i = 0; i < alloc; i++)
        data[i] = data[i/3+2];
  }
  return 0;
}
