#include <iostream>
#include <fstream>
#include <ctime>
#include <vector>

volatile unsigned int x;

int main() {
	int N;
	std::ifstream in("input.txt");
	std::ofstream out("output.txt");
	in >> N;

    const constexpr int sz = 10240;
    std::clock_t startcputime = std::clock();
    std::vector<int> v;
    v.resize(sz, 0);
    int i = 0;
    while ((std::clock() - startcputime) * 1000 < N * CLOCKS_PER_SEC) {
        for (int j = 0; j < i; j++) {
            v[j] += i;
        }
        i = (i + 1) % sz;
    }
    out << N << std::endl;
    return 0;
}
