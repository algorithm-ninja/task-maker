with open("input.txt") as f:
    print(int(f.read().splitlines()[0]), file=open("output.txt", "w"))
