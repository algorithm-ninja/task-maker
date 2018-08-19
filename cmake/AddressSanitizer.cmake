OPTION(ADDRESSSANITIZER "Enable AddressSanitizer memory bug detector."
       OFF)

# TODO: give an error if TS does not work for this compiler
IF (ADDRESSSANITIZER)
    SET(ADDRESS_SANITIZER_FLAG "-fsanitize=address")

    SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${ADDRESS_SANITIZER_FLAG}")
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${ADDRESS_SANITIZER_FLAG}")
    SET(CMAKE_CGO_LDFLAGS "${CMAKE_CGO_LDFLAGS} ${ADDRESS_SANITIZER_FLAG}")

    # Configure CTest's MemCheck to ThreadSanitizer.
    SET(MEMORYCHECK_TYPE AddressSanitizer)

    ADD_DEFINITIONS(-DADDRESS_SANITIZER)

    MESSAGE(STATUS "AddressSanitizer enabled.")
ENDIF()
