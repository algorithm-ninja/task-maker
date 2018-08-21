OPTION(UNDEFINEDSANITIZER "Enable UndefinedSanitizer memory bug detector."
       OFF)

# TODO: give an error if TS does not work for this compiler
IF (UNDEFINEDSANITIZER)
    SET(UNDEFINED_SANITIZER_FLAG "-fsanitize=undefined")

    SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${UNDEFINED_SANITIZER_FLAG}")
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${UNDEFINED_SANITIZER_FLAG}")
    SET(CMAKE_CGO_LDFLAGS "${CMAKE_CGO_LDFLAGS} ${UNDEFINED_SANITIZER_FLAG}")

    # Configure CTest's MemCheck to ThreadSanitizer.
    SET(MEMORYCHECK_TYPE UndefinedSanitizer)

    ADD_DEFINITIONS(-DUNDEFINED_SANITIZER)

    MESSAGE(STATUS "UndefinedSanitizer enabled.")
ENDIF()
