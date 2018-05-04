project(task-maker-proto)

set(PROTOS
  ${CMAKE_CURRENT_SOURCE_DIR}/cache_entry.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/event.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/file.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/manager.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/request.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/resources.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/response.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/server.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/sha256.proto
  ${CMAKE_CURRENT_SOURCE_DIR}/task.proto
)

set(PROTO_SRC_DIR ${CMAKE_CURRENT_BINARY_DIR}/proto)
file(MAKE_DIRECTORY ${PROTO_SRC_DIR})

set(PROTO_PY_DIR ${CMAKE_CURRENT_BINARY_DIR}/python/proto)
file(MAKE_DIRECTORY ${PROTO_PY_DIR})

string(REPLACE ".proto"
  "_pb2.py" PROTO_PY_OUT "${PROTOS}")
string(REPLACE ".proto"
  "_pb2_grpc.py" GRPC_PY_OUT "${PROTOS}")

string(REPLACE "${CMAKE_CURRENT_SOURCE_DIR}" "${PROTO_PY_DIR}" PROTOS_PY_TMP "${PROTO_PY_OUT} ${GRPC_PY_OUT}")

SET(PROTOS_PY ${PROTOS_PY_TMP} PARENT_SCOPE)

add_custom_command(OUTPUT ${PROTOS_PY_TMP}
  COMMAND ${PYTHON_EXECUTABLE} -m grpc_tools.protoc -I${CMAKE_CURRENT_SOURCE_DIR} --python_out=${PROTO_PY_DIR} --grpc_python_out=${PROTO_PY_DIR} ${PROTOS}
  DEPENDS ${PROTOS}
)

protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS ${PROTO_SRC_DIR} ${PROTOS})
grpc_generate_cpp(GRPC_SRCS GRPC_HDRS ${PROTO_SRC_DIR} ${PROTOS})

add_library(
  proto_cpp
  ${PROTO_SRCS}
  ${GRPC_SRCS}
)

target_include_directories(proto_cpp PUBLIC ${PROTO_SRC_DIR}/..)

target_link_libraries(proto_cpp
    gRPC::grpc++_reflection
    protobuf::libprotobuf
)
