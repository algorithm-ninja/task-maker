#include <iostream>
#include <fstream>

int main() {
	std::ofstream("output.txt") << 42 << std::endl;
}
