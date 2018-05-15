# External commands
find_program(PIP_EXE NAMES pip)
find_program(STRIP_EXE NAMES strip)
find_program(XARGS_EXE NAMES xargs)
find_program(FIND_EXE NAMES find)

# Sources
file(GLOB SOURCES_PY "${CMAKE_CURRENT_SOURCE_DIR}/*.py")
file(GLOB UIS_PY "${CMAKE_CURRENT_SOURCE_DIR}/uis/*.py")
file(GLOB TESTS_PY "${CMAKE_CURRENT_SOURCE_DIR}/tests/test.py" "${CMAKE_CURRENT_SOURCE_DIR}/tests/utils.py")
file(GLOB TESTS_TASKS "${CMAKE_CURRENT_SOURCE_DIR}/tests/task_*")
SET(REQUIREMENTS_TXT "${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt")

# Install directories
SET(SOURCES_MODULE "${CMAKE_CURRENT_BINARY_DIR}/task_maker")
SET(UIS_MODULE "${SOURCES_MODULE}/uis")
SET(TESTS_MODULE "${SOURCES_MODULE}/tests")
SET(PROTOS_MODULE "${SOURCES_MODULE}/proto")
SET(BIN_DIRECTORY "${SOURCES_MODULE}/bin")
SET(VENV_DIRECTORY "${SOURCES_MODULE}/venv")

# Create the install directories
file(MAKE_DIRECTORY ${SOURCES_MODULE})
file(MAKE_DIRECTORY ${UIS_MODULE})
file(MAKE_DIRECTORY ${TESTS_MODULE})
file(MAKE_DIRECTORY ${PROTOS_MODULE})
file(MAKE_DIRECTORY ${BIN_DIRECTORY})
file(MAKE_DIRECTORY ${VENV_DIRECTORY})
file(WRITE "${PROTOS_MODULE}/__init__.py" "")
file(WRITE "${TESTS_MODULE}/__init__.py" "")
file(WRITE "${BIN_DIRECTORY}/__init__.py" "")

# Compute the target file paths
string(REGEX REPLACE "[^;]*/" "${PROTOS_MODULE}/" PROTOS_PY_TGT "${PROTOS_PY}")
string(REGEX REPLACE "[^;]*/" "${PROTOS_MODULE}/" GRPC_PY_TGT "${GRPC_PY}")
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}" "${SOURCES_MODULE}" SOURCES_PY_TGT "${SOURCES_PY}")
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/uis" "${UIS_MODULE}" UIS_PY_TGT "${UIS_PY}")
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/tests" "${TESTS_MODULE}" TESTS_PY_TGT "${TESTS_PY}")
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/tests" "${TESTS_MODULE}" TESTS_TASKS_TGT "${TESTS_TASKS}")
SET(SETUP_PY ${CMAKE_CURRENT_BINARY_DIR}/setup.py)
SET(VERSION_PY ${SOURCES_MODULE}/version.py)
SET(REQUIREMENTS_TXT_TGT "${CMAKE_CURRENT_BINARY_DIR}/requirements.txt")
SET(CPP_EXECUTABLES
  "${BIN_DIRECTORY}/manager"
  "${BIN_DIRECTORY}/server"
  "${BIN_DIRECTORY}/worker"
)

# Copy all the files
add_custom_command(OUTPUT ${PROTOS_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${PROTOS_PY} ${PROTOS_MODULE}
  DEPENDS protos_py
)

add_custom_command(OUTPUT ${GRPC_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${GRPC_PY} ${PROTOS_MODULE}
  DEPENDS grpc_py
)

add_custom_command(OUTPUT ${SOURCES_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${SOURCES_PY} ${SOURCES_MODULE}
  DEPENDS "${SOURCES_PY}"
)

add_custom_command(OUTPUT ${UIS_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${UIS_PY} ${UIS_MODULE}
  DEPENDS "${UIS_PY}"
)

add_custom_command(OUTPUT ${TESTS_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${TESTS_PY} ${TESTS_MODULE}
  DEPENDS "${TESTS_PY}"
)

add_custom_command(OUTPUT ${REQUIREMENTS_TXT_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${REQUIREMENTS_TXT} ${REQUIREMENTS_TXT_TGT}
  DEPENDS ${REQUIREMENTS_TXT}
)

foreach(task ${TESTS_TASKS})
  string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/tests/task_" "" task_name "${task}")
  set(TEST_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/tests")
  set(TEST_DST_DIR "${TESTS_MODULE}")

  add_custom_command(OUTPUT ${TEST_DST_DIR}/task_${task_name}
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${TEST_SRC_DIR}/task_${task_name} ${TEST_DST_DIR}/task_${task_name}
    DEPENDS "${TEST_SRC_DIR}/task_${task_name}"
  )

  file(COPY ${TEST_SRC_DIR}/${task_name}.py DESTINATION ${TEST_DST_DIR} FILE_PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ)

  add_test(NAME pytest.${task_name} COMMAND env PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR} "${TEST_DST_DIR}/${task_name}.py")
endforeach(task)

add_custom_command(OUTPUT ${BIN_DIRECTORY}/server ${BIN_DIRECTORY}/worker ${BIN_DIRECTORY}/manager
  COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:server> $<TARGET_FILE:worker> $<TARGET_FILE:manager> ${BIN_DIRECTORY}
  DEPENDS server worker manager
)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/setup.py.in ${SETUP_PY})
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/version.py.in ${VERSION_PY})

# Install the python dependencies
execute_process(
  COMMAND ${PIP_EXE} install --ignore-installed --target=${VENV_DIRECTORY} -r ${REQUIREMENTS_TXT}
)

# Strip away the symbols from the python modules
execute_process(
  COMMAND ${FIND_EXE} -name "*.so"
  COMMAND ${XARGS_EXE} ${STRIP_EXE} -s
  WORKING_DIRECTORY ${VENV_DIRECTORY}
)

add_custom_target(module_files ALL
  DEPENDS ${PROTOS_PY_TGT} ${GRPC_PY_TGT} ${UIS_PY_TGT} ${REQUIREMENTS_TXT_TGT} ${TESTS_PY_TGT} "${TESTS_TASKS_TGT}" ${SOURCES_PY_TGT} ${CPP_EXECUTABLES}
)

add_custom_target(develop
  COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} develop
  DEPENDS module_files
)

install(CODE "execute_process(COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} install)")
