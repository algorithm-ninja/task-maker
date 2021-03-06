#include "util/daemon.hpp"

#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <fstream>

namespace util {

void daemonize(const std::string& scope, std::string pidfile) {
  // first fork
  pid_t pid = fork();
  if (pid == -1) {
    perror("fork");
    exit(1);
  }

  // terminate parent process
  if (pid > 0) exit(EXIT_SUCCESS);

  // become the session leader
  if (setsid() == -1) {
    perror("setsid");
    exit(1);
  }

  // fork again
  pid = fork();
  if (pid == -1) {
    perror("fork");
    exit(1);
  }

  if (pid > 0) exit(EXIT_SUCCESS);

  umask(0);

  // save the pid to a pidfile
  if (pidfile.empty()) {
    uid_t uid = getuid();
    pidfile = "/tmp/task-maker-" + scope + "-" + std::to_string(uid) + ".pid";
  }

  remove(pidfile.c_str());
  pid = getpid();
  std::ofstream file(pidfile);
  file << pid << std::endl;
  file.close();
  chmod(pidfile.c_str(), S_IRUSR | S_IRGRP | S_IROTH);
}

}  // namespace util
