set(ZSH_AUTOCOMP "${CMAKE_CURRENT_BINARY_DIR}/autocomp/zsh")
file(MAKE_DIRECTORY "${ZSH_AUTOCOMP}")
set(BASH_AUTOCOMP "${CMAKE_CURRENT_BINARY_DIR}/autocomp/bash")
file(MAKE_DIRECTORY "${BASH_AUTOCOMP}")

# .deb metadata
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/DEBIAN/control.in
               ${CMAKE_BINARY_DIR}/DEBIAN/control)

# zsh autocompletion
add_custom_command(OUTPUT ${ZSH_AUTOCOMP}/_task_maker
                   COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
                           zsh -o
                           ${CMAKE_CURRENT_BINARY_DIR}/autocomp/zsh/_task_maker
                   DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
                           ${CMAKE_CURRENT_SOURCE_DIR}/../python/args.py)
add_custom_command(
  OUTPUT ${ZSH_AUTOCOMP}/_contest_maker
  COMMAND
    python3 ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
    --contest-maker zsh -o
                    ${CMAKE_CURRENT_BINARY_DIR}/autocomp/zsh/_contest_maker
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../python/args.py)

# bash autocompletion
add_custom_command(OUTPUT ${BASH_AUTOCOMP}/task-maker
                   COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
                           bash -o
                           ${CMAKE_CURRENT_BINARY_DIR}/autocomp/bash/task-maker
                   DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
                           ${CMAKE_CURRENT_SOURCE_DIR}/../python/args.py)
add_custom_command(
  OUTPUT ${BASH_AUTOCOMP}/contest-maker
  COMMAND
    python3 ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
    --contest-maker bash -o
                    ${CMAKE_CURRENT_BINARY_DIR}/autocomp/bash/contest-maker
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../python/args.py)

add_custom_target(autocomp ALL
                  DEPENDS ${ZSH_AUTOCOMP}/_task_maker
                          ${ZSH_AUTOCOMP}/_contest_maker
                          ${BASH_AUTOCOMP}/task-maker
                          ${BASH_AUTOCOMP}/contest-maker)
