#include <iostream>

int main(int argc, char** argv) {
  std::cout << argv[1] << std::endl;
  std::cerr << "This string should not appear in the input.txt" << std::endl;
}
