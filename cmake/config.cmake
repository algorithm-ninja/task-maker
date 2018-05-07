# enable -fPIC to ZLib because gRPC needs it to link
hunter_config(ZLIB VERSION ${HUNTER_ZLIB_VERSION}
              CMAKE_ARGS CMAKE_POSITION_INDEPENDENT_CODE=TRUE)
