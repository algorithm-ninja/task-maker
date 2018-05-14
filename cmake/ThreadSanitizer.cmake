OPTION(THREADSANITIZER "Enable ThreadSanitizer data race detector."
       OFF)

# TODO: give an error if TS does not work for this compiler
IF (THREADSANITIZER)
    SET(THREAD_SANITIZER_FLAG "-fsanitize=thread")

    SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${THREAD_SANITIZER_FLAG}")
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${THREAD_SANITIZER_FLAG}")
    SET(CMAKE_CGO_LDFLAGS "${CMAKE_CGO_LDFLAGS} ${THREAD_SANITIZER_FLAG}")

    # Configure CTest's MemCheck to ThreadSanitizer.
    SET(MEMORYCHECK_TYPE ThreadSanitizer)

    ADD_DEFINITIONS(-DTHREAD_SANITIZER)

    MESSAGE(STATUS "ThreadSanitizer enabled.")
ENDIF()
