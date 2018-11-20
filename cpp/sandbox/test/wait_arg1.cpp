#include <chrono>
#include <cstdlib>
#include <thread>

int main(int /*argc*/, char** argv) {
  std::this_thread::sleep_for(
      std::chrono::milliseconds(static_cast<int>(1000 * atof(argv[1]))));
  return 0;
}
