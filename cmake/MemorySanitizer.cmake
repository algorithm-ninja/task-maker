OPTION(MEMORYSANITIZER "Enable MemorySanitizer data race detector."
       OFF)

# TODO: give an error if TS does not work for this compiler
IF (MEMORYSANITIZER)
    SET(MEMORY_SANITIZER_FLAG "-fsanitize=memory")

    SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${MEMORY_SANITIZER_FLAG}")
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${MEMORY_SANITIZER_FLAG}")
    SET(CMAKE_CGO_LDFLAGS "${CMAKE_CGO_LDFLAGS} ${MEMORY_SANITIZER_FLAG}")

    # Configure CTest's MemCheck to ThreadSanitizer.
    SET(MEMORYCHECK_TYPE MemorySanitizer)

    ADD_DEFINITIONS(-DMEMORY_SANITIZER)

    MESSAGE(STATUS "MemorySanitizer enabled.")
ENDIF()
