#include "util/flags.hpp"

bool Flags::daemon = false;
std::string Flags::pidfile;

std::string Flags::server;
std::string Flags::name = "unnamed_worker";
int32_t Flags::num_cores = 0;

std::string Flags::store_directory = "files";
std::string Flags::temp_directory = "temp";

std::string Flags::listen_address = "0.0.0.0";
int32_t Flags::listen_port = 7070;

/*void parse_flags(int argc, char** argv) {
  app.require_subcommand(1);
  app.add_flag("-v,--verbose", FLAGS_verbose, "Enable verbose logs");
  app.add_flag("-d,--daemon", FLAGS_daemon, "Become a daemon");
  app.add_option("-P,--pidfile", FLAGS_pidfile,
                 "Path where to store the pidfile")
      ->set_type_name("PATH");

  manager_parser = app.add_subcommand("manager", "Local manager");
  manager_parser->fallthrough();
  manager_parser
      ->add_option("-p,--port", FLAGS_manager_port, "Port to listen on")
      ->set_type_name("PORT");

  server_parser = app.add_subcommand("server", "Remote server");
  server_parser->fallthrough();
  server_parser
      ->add_option("-l,--address", FLAGS_address, "Address to listen on")
      ->set_type_name("ADDR");
  server_parser->add_option("-p,--port", FLAGS_server_port, "Port to listen on")
      ->set_type_name("PORT");
  server_parser
      ->add_option("-s,--store", FLAGS_store_directory,
                   "Where files should be stored")
      ->set_type_name("PATH");
  server_parser
      ->add_option("-t,--temp", FLAGS_temp_directory,
                   "Where the sandboxes should be created")
      ->set_type_name("PATH");

  worker_parser = app.add_subcommand("worker", "Remote worker");
  worker_parser->fallthrough();
  worker_parser
      ->add_option("-s,--store", FLAGS_store_directory,
                   "Where files should be stored")
      ->set_type_name("PATH");
  worker_parser
      ->add_option("-t,--temp", FLAGS_temp_directory,
                   "Where the sandboxes should be created")
      ->set_type_name("PATH");
  auto* server =
      worker_parser->add_option("server", FLAGS_server, "Server to connect to");
  server->set_type_name("ADDR");
  server->required();

  try {
    app.parse(argc, argv);
  } catch (const CLI::ParseError& e) {
    exit(app.exit(e));
  }
}*/
