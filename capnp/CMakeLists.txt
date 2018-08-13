capnp_generate_cpp(CAPNP_SOURCES CAPNP_HEADERS
  sha256.capnp
  file.capnp
  evaluation.capnp
  server.capnp
)

add_library(
  capnp_cpp
  ${CAPNP_SOURCES}
)

target_link_libraries(capnp_cpp PUBLIC CapnProto::capnp-rpc)
target_include_directories(capnp_cpp PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/..)
