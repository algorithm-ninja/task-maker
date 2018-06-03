# External commands
find_program(PIP_EXE NAMES pip3 pip)
find_program(STRIP_EXE NAMES strip)
find_program(XARGS_EXE NAMES xargs)
find_program(FIND_EXE NAMES find)
find_program(CP_EXE NAMES cp)
find_program(SED_EXE NAMES sed)
find_program(TR_EXE NAMES tr)
find_program(LS_EXE NAMES ls)
find_program(RM_EXE NAMES rm)

# Sources
file(GLOB SOURCES_PY "${CMAKE_CURRENT_SOURCE_DIR}/*.py")
file(GLOB UIS_PY "${CMAKE_CURRENT_SOURCE_DIR}/uis/*.py")
file(GLOB TESTS_PY "${CMAKE_CURRENT_SOURCE_DIR}/tests/test.py" "${CMAKE_CURRENT_SOURCE_DIR}/tests/utils.py")
file(GLOB TESTS_TASKS "${CMAKE_CURRENT_SOURCE_DIR}/tests/task_*")
set(REQUIREMENTS_TXT "${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt")

# Install directories
set(SOURCES_MODULE "${CMAKE_CURRENT_BINARY_DIR}/task_maker")
set(UIS_MODULE "${SOURCES_MODULE}/uis")
set(TESTS_MODULE "${SOURCES_MODULE}/tests")
set(PROTOS_MODULE "${SOURCES_MODULE}/proto")
set(BIN_DIRECTORY "${SOURCES_MODULE}/bin")
set(VENV_DIRECTORY "${SOURCES_MODULE}/venv")
set(TEMP_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/temp")

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
set(SETUP_PY ${CMAKE_CURRENT_BINARY_DIR}/setup.py)
set(VERSION_PY ${SOURCES_MODULE}/version.py)
set(REQUIREMENTS_TXT_TGT "${CMAKE_CURRENT_BINARY_DIR}/requirements.txt")
set(CPP_EXECUTABLES
  "${BIN_DIRECTORY}/task-maker"
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

  file(COPY ${TEST_SRC_DIR}/${task_name}.py DESTINATION ${TEST_DST_DIR}
    FILE_PERMISSIONS OWNER_EXECUTE OWNER_READ GROUP_EXECUTE GROUP_READ WORLD_READ WORLD_EXECUTE
  )

  add_test(NAME pytest.${task_name} COMMAND env PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR} "${TEST_DST_DIR}/${task_name}.py")
endforeach(task)

add_custom_command(OUTPUT ${BIN_DIRECTORY}/task-maker
  COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:task-maker> ${BIN_DIRECTORY}
  DEPENDS task-maker
)

# generate setup.py
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/setup.py.in ${SETUP_PY})
execute_process(COMMAND chmod 555 ${SETUP_PY})

# generate version.py
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/version.py.in ${VERSION_PY})

# Install the python dependencies, it would be nice to use --user and --prefix but
# if python is installed with brew on mac it doesn't work...
# An entire linux root is created in TEMP_DIRECTORY and then the site-packages files
# are copied to the venv directory
add_custom_command(
  OUTPUT ${TEMP_DIRECTORY}/root
  COMMAND ${PIP_EXE}
  ARGS install --ignore-installed --no-warn-script-location --root=${TEMP_DIRECTORY}/root -r ${REQUIREMENTS_TXT}
  DEPENDS ${REQUIREMENTS_TXT}
  COMMENT "Installing python dependencies"
  VERBATIM
)

add_custom_command(
  OUTPUT ${TEMP_DIRECTORY}/not_stripped
  COMMAND bash
  ARGS -c "cp -rf $(ls $(find ${TEMP_DIRECTORY} -name site-packages) | sed \"s|^|$(find ${TEMP_DIRECTORY} -name site-packages)/|g\") ${VENV_DIRECTORY} && touch ${TEMP_DIRECTORY}/not_stripped"
  WORKING_DIRECTORY ${VENV_DIRECTORY}
  COMMENT "Fixing python dependencies path"
  DEPENDS ${TEMP_DIRECTORY}/root
  VERBATIM
)

# Strip away the symbols from the python modules
if (NOT APPLE)
  add_custom_command(
    OUTPUT ${TEMP_DIRECTORY}/stripped
    COMMAND bash
    ARGS -c "strip -s $(find . -name '*.so') || true && touch ${TEMP_DIRECTORY}/stripped"
    WORKING_DIRECTORY ${VENV_DIRECTORY}
    COMMENT "Stripping .so of python dependencies"
    DEPENDS ${TEMP_DIRECTORY}/not_stripped
    VERBATIM
  )
else ()
  add_custom_command(
    OUTPUT ${TEMP_DIRECTORY}/stripped
    COMMAND bash
    ARGS -c "touch ${TEMP_DIRECTORY}/stripped"
    DEPENDS ${TEMP_DIRECTORY}/not_stripped
    VERBATIM
  )
endif()

add_custom_target(module_files ALL
  DEPENDS ${PROTOS_PY_TGT} ${GRPC_PY_TGT} ${UIS_PY_TGT} ${REQUIREMENTS_TXT_TGT} ${TESTS_PY_TGT} "${TESTS_TASKS_TGT}" ${SOURCES_PY_TGT} ${CPP_EXECUTABLES}
  ${TEMP_DIRECTORY}/stripped
)

add_custom_target(develop
  COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} develop
  DEPENDS module_files
)

install(CODE "execute_process(COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} install)")
