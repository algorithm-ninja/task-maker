#include <iostream>

volatile int* null = nullptr;

int main() {
	std::cout << *null << std::endl;
}
