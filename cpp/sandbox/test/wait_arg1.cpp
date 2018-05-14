#include <stdlib.h>
#include <chrono>
#include <thread>
int main(int argc, char** argv) {
  std::this_thread::sleep_for(
      std::chrono::milliseconds((int)(1000 * atof(argv[1]))));
  return 0;
}
