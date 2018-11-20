set(ZSH_AUTOCOMP "${CMAKE_CURRENT_BINARY_DIR}/autocomp/zsh")
file(MAKE_DIRECTORY "${ZSH_AUTOCOMP}")

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/DEBIAN/control.in
    ${CMAKE_BINARY_DIR}/DEBIAN/control)

add_custom_command(OUTPUT ${ZSH_AUTOCOMP}/_task_maker
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py zsh -o ${CMAKE_CURRENT_BINARY_DIR}/autocomp/zsh/_task_maker
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py ${CMAKE_CURRENT_SOURCE_DIR}/../python/args.py)
add_custom_command(OUTPUT ${ZSH_AUTOCOMP}/_contest_maker
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py --contest-maker zsh -o ${CMAKE_CURRENT_BINARY_DIR}/autocomp/zsh/_contest_maker
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/autocomplete.py ${CMAKE_CURRENT_SOURCE_DIR}/../python/args.py)

add_custom_target(autocomp ALL DEPENDS ${ZSH_AUTOCOMP}/_task_maker ${ZSH_AUTOCOMP}/_contest_maker)
