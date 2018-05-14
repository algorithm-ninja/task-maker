# enable -fPIC to ZLib because gRPC needs it to link
hunter_config(ZLIB VERSION ${HUNTER_ZLIB_VERSION}
              CMAKE_ARGS CMAKE_POSITION_INDEPENDENT_CODE=TRUE)

hunter_config(glog VERSION ${HUNTER_glog_VERSION}
              CMAKE_ARGS WITH_GFLAGS=ON)

hunter_config(c-ares VERSION ${HUNTER_c-ares_VERSION}
              CMAKE_ARGS CARES_STATIC=ON CARES_SHARED=OFF CARES_STATIC_PIC=ON)