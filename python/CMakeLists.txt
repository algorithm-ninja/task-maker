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
set(PY_MODULES formats tests uis languages)
foreach(module_name ${PY_MODULES})
  file(GLOB SOURCES_PY_${module_name} "${CMAKE_CURRENT_SOURCE_DIR}/${module_name}/*.py")
endforeach()
file(GLOB TESTS_TASKS "${CMAKE_CURRENT_SOURCE_DIR}/tests/task_*")
file(GLOB CAPNP_FILES "${CMAKE_CURRENT_SOURCE_DIR}/../capnp/*.capnp")
set(REQUIREMENTS_TXT "${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt")

# Install directories
set(SOURCES_MODULE "${CMAKE_CURRENT_BINARY_DIR}/task_maker")
foreach(module_name ${PY_MODULES})
  set(SOURCES_${module_name}_MODULE "${SOURCES_MODULE}/${module_name}")
endforeach()
set(CAPNP_MODULE "${SOURCES_MODULE}/capnp")
set(BIN_DIRECTORY "${SOURCES_MODULE}/bin")
set(VENV_DIRECTORY "${SOURCES_MODULE}/venv")
set(TEMP_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/temp")

# Create the install directories
file(MAKE_DIRECTORY ${SOURCES_MODULE})
foreach(module_name ${PY_MODULES})
  file(MAKE_DIRECTORY ${SOURCES_${module_name}_MODULE})
endforeach()
file(MAKE_DIRECTORY ${CAPNP_MODULE})
file(MAKE_DIRECTORY ${BIN_DIRECTORY})
file(MAKE_DIRECTORY ${VENV_DIRECTORY})
file(WRITE "${CAPNP_MODULE}/__init__.py" "")
file(WRITE "${BIN_DIRECTORY}/__init__.py" "")

# Compute the target file paths
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/../capnp" "${CAPNP_MODULE}" CAPNP_TGT "${CAPNP_FILES}")
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}" "${SOURCES_MODULE}" SOURCES_PY_TGT "${SOURCES_PY}")
foreach(module_name ${PY_MODULES})
  string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/${module_name}" "${SOURCES_${module_name}_MODULE}" SOURCES_PY_${module_name}_TGT "SOURCES_PY_${module_name}")
  file(MAKE_DIRECTORY ${SOURCES_${module_name}_MODULE})
  list(APPEND MODULES_TGT ${SOURCES_PY_${module_name}_TGT})
endforeach()
string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/tests" "${SOURCES_tests_MODULE}" TESTS_TASKS_TGT "${TESTS_TASKS}")
set(SETUP_PY ${CMAKE_CURRENT_BINARY_DIR}/setup.py)
set(VERSION_PY ${SOURCES_MODULE}/version.py)
set(REQUIREMENTS_TXT_TGT "${CMAKE_CURRENT_BINARY_DIR}/requirements.txt")
set(CPP_EXECUTABLES
  "${BIN_DIRECTORY}/task-maker"
)
set(FRONTEND_LIB "${SOURCES_MODULE}/task_maker_frontend.so")

# Copy all the files
add_custom_command(OUTPUT ${CAPNP_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${CAPNP_FILES} ${CAPNP_MODULE}
  DEPENDS "${CAPNP_FILES}"
)

add_custom_command(OUTPUT ${SOURCES_PY_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${SOURCES_PY} ${SOURCES_MODULE}
  DEPENDS "${SOURCES_PY}"
)

foreach(module_name ${PY_MODULES})
  add_custom_command(OUTPUT ${SOURCES_PY_${module_name}_TGT}
    COMMAND ${CMAKE_COMMAND} -E copy ${SOURCES_PY_${module_name}} ${SOURCES_${module_name}_MODULE}
    DEPENDS "${SOURCES_PY_${module_name}}"
  )
endforeach()

add_custom_command(OUTPUT ${REQUIREMENTS_TXT_TGT}
  COMMAND ${CMAKE_COMMAND} -E copy ${REQUIREMENTS_TXT} ${REQUIREMENTS_TXT_TGT}
  DEPENDS ${REQUIREMENTS_TXT}
)

add_custom_command(OUTPUT "${FRONTEND_LIB}"
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:task_maker_frontend> ${FRONTEND_LIB}
    DEPENDS task_maker_frontend
)

foreach(task ${TESTS_TASKS})
  string(REGEX REPLACE "${CMAKE_CURRENT_SOURCE_DIR}/tests/task_" "" task_name "${task}")
  set(TEST_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/tests")
  set(TEST_DST_DIR "${SOURCES_tests_MODULE}")

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
  ARGS install --ignore-installed --root=${TEMP_DIRECTORY}/root -r ${REQUIREMENTS_TXT}
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
  DEPENDS ${CAPNP_TGT} ${MODULES_TGT} ${REQUIREMENTS_TXT_TGT}
    "${TESTS_TASKS_TGT}" ${SOURCES_PY_TGT} ${CPP_EXECUTABLES} ${FRONTEND_LIB}
  ${TEMP_DIRECTORY}/stripped
)

add_custom_target(develop
  COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} develop
  DEPENDS module_files
)

install(CODE "execute_process(COMMAND ${PYTHON_EXECUTABLE} ${SETUP_PY} install)")
