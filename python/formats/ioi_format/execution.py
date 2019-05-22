#!/usr/bin/env python3
import os
from task_maker.args import UIS
from task_maker.config import Config
from task_maker.formats import IOITask, list_files, VALIDATION_INPUT_NAME, \
    TaskType
from task_maker.remote import ExecutionPool, Execution
from task_maker.sanity_checks.ioi import sanity_pre_checks, sanity_post_checks
from task_maker.solution import Solution
from task_maker.source_file import SourceFile
from task_maker.statements.oii_tex import OIITexStatement
from task_maker.task_maker_frontend import File, Frontend
from task_maker.uis.ioi import IOIUIInterface, TestcaseGenerationStatus
from task_maker.uis.ioi_curses_ui import IOICursesUI
from task_maker.uis.ioi_finish_ui import IOIFinishUI
from task_maker.uis.ioi_finish_ui_json import IOIFinishUIJSON
from typing import Dict, List, Tuple


def evaluate_task(frontend: Frontend, task: IOITask, solutions: List[Solution],
                  config: Config) -> IOIUIInterface:
    """
    Build the computation DAG and run the evaluation of the task. All the sanity
    checks are also run and a IOIUIInterface with all the results is returned.
    """
    ui_interface = IOIUIInterface(
        task,
        dict((st_num, [tc for tc in st.testcases.keys()])
             for st_num, st in task.subtasks.items()),
        config.ui in [UIS.PRINT, UIS.JSON], config.ui == UIS.JSON)
    pool = ExecutionPool(config, frontend, ui_interface.ui_printer)
    ui_interface.pool = pool
    curses_ui = None
    finish_ui = None
    if config.ui == UIS.CURSES:
        curses_ui = IOICursesUI(config, ui_interface)
    if config.ui != UIS.SILENT and config.bulk_number is None:
        if config.ui in [UIS.PRINT, UIS.CURSES]:
            finish_ui = IOIFinishUI(config, ui_interface)
        elif config.ui == UIS.JSON:
            finish_ui = IOIFinishUIJSON(config, ui_interface)
        else:
            raise ValueError("Unsupported UI %s" % str(config.ui))

    with ui_interface.run_in_ui(curses_ui, finish_ui):
        ins, outs, vals = generate_inputs(pool, task, ui_interface)
        evaluate_solutions(pool, ins, outs, vals, solutions, ui_interface)
        if not config.no_statement:
            compile_statements(pool, task, ui_interface)
        for warning in task.warnings:
            ui_interface.add_warning(warning)
        if not config.no_sanity_checks:
            sanity_pre_checks(task, solutions, pool, ui_interface)
        pool.start()
        if not config.no_sanity_checks:
            sanity_post_checks(task, solutions, ui_interface)

    return ui_interface


def generate_inputs(
        pool: ExecutionPool, task: IOITask, interface: IOIUIInterface
) -> (Dict[Tuple[int, int], File], Dict[Tuple[int, int], File],
      Dict[Tuple[int, int], File]):
    """
    Create the part of the DAG responsible for the input and output files. Will
    return 3 dicts: one for input, one for output and one for validations.
    Each dict has (subtask number, test case number) -> File
    """

    def add_non_solution(source: SourceFile):
        if not source.prepared:
            source.prepare(pool)
            interface.add_non_solution(source)

    inputs = dict()  # type: Dict[Tuple[int, int], File]
    outputs = dict()  # type: Dict[Tuple[int, int], File]
    validations = dict()  # type: Dict[Tuple[int, int], File]
    for st_num, subtask in task.subtasks.items():
        for tc_num, testcase in subtask.testcases.items():
            testcase_id = (st_num, tc_num)

            if testcase.validator:
                add_non_solution(testcase.validator.source_file)

            # static input file
            if testcase.input_file:
                try:
                    inputs[testcase_id] = pool.frontend.provideFile(
                        testcase.input_file, "Static input %d" % tc_num, False)

                    if testcase.validator:
                        val = Execution(
                            "Validation of input %d" % tc_num,
                            pool,
                            testcase.validator.source_file,
                            testcase.validator.get_args(
                                testcase, subtask, tc_num, st_num + 1),
                            "validation", {
                                "subtask": st_num,
                                "testcase": tc_num
                            },
                            inputs={
                                VALIDATION_INPUT_NAME: inputs[testcase_id]
                            },
                            store_stderr=True)
                        validations[testcase_id] = val.stdout

                        interface.add_validation(st_num, tc_num, val)
                except RuntimeError as ex:
                    interface.add_error(str(ex))
                    interface.subtasks[st_num][
                        tc_num].status = TestcaseGenerationStatus.FAILURE
                    continue
            # generate input file
            else:
                add_non_solution(testcase.generator.source_file)

                deps = dict()
                for dep in testcase.extra_deps:
                    deps[dep.name] = pool.frontend.provideFile(
                        dep.path, dep.path, False)
                gen = Execution(
                    "Generation of input %d" % tc_num,
                    pool,
                    testcase.generator.source_file,
                    testcase.generator_args,
                    "generation", {
                        "subtask": st_num,
                        "testcase": tc_num
                    },
                    inputs=deps,
                    store_stderr=True)
                inputs[testcase_id] = gen.stdout

                interface.add_generation(st_num, tc_num, gen)

                val = Execution(
                    "Validation of input %d" % tc_num,
                    pool,
                    testcase.validator.source_file,
                    testcase.validator.get_args(testcase, subtask, tc_num,
                                                st_num + 1),
                    "validation", {
                        "subtask": st_num,
                        "testcase": tc_num
                    },
                    inputs={VALIDATION_INPUT_NAME: inputs[testcase_id]},
                    store_stderr=True)
                validations[testcase_id] = val.stdout

                interface.add_validation(st_num, tc_num, val)

            if testcase.write_input_to and not pool.config.dry_run:
                inputs[testcase_id].getContentsToFile(testcase.write_input_to)

            if task.task_type == TaskType.Batch:
                # static output file
                if testcase.output_file:
                    outputs[testcase_id] = pool.frontend.provideFile(
                        testcase.output_file, "Static output %d" % tc_num,
                        False)
                else:
                    add_non_solution(task.official_solution)
                    deps = {"wait_for_validation": validations[testcase_id]}
                    if task.input_file:
                        deps[task.input_file] = inputs[testcase_id]
                        stdin = None
                    else:
                        stdin = inputs[testcase_id]
                    outs = []
                    if task.output_file:
                        outs.append(task.output_file)

                    sol = Execution(
                        "Generation of output %d" % tc_num,
                        pool,
                        task.official_solution, [],
                        "solution", {
                            "subtask": st_num,
                            "testcase": tc_num
                        },
                        inputs=deps,
                        outputs=outs,
                        stdin=stdin,
                        store_stderr=True)
                    if task.output_file:
                        outputs[testcase_id] = sol.output(task.output_file)
                    else:
                        outputs[testcase_id] = sol.stdout

                    interface.add_solving(st_num, tc_num, sol)

                if testcase.write_output_to and not pool.config.dry_run:
                    outputs[testcase_id].getContentsToFile(
                        testcase.write_output_to, True, True)
    if task.checker:
        add_non_solution(task.checker)
    return inputs, outputs, validations


def evaluate_solutions(pool: ExecutionPool,
                       inputs: Dict[Tuple[int, int], File],
                       outputs: Dict[Tuple[int, int], File],
                       validations: Dict[Tuple[int, int], File],
                       solutions: List[Solution], interface: IOIUIInterface):
    """
    Create the evaluation part of the DAG, for each solution at least 2
    executions will be run: the evaluation that produces an output file and
    the checking that produces a score.
    """
    for solution in solutions:
        solution.solution.prepare(pool)
        interface.add_solution(solution.solution)
        for testcase_id, input in inputs.items():
            st_num, tc_num = testcase_id
            evals, check = solution.evaluate(tc_num, st_num,
                                             inputs[testcase_id],
                                             validations.get(testcase_id),
                                             outputs.get(testcase_id))
            interface.add_evaluate_solution(st_num, tc_num,
                                            solution.solution.name, evals)
            interface.add_evaluate_checking(st_num, tc_num,
                                            solution.solution.name, check)


def compile_statements(pool: ExecutionPool, task: IOITask,
                       interface: IOIUIInterface):
    """
    Create the statement compilation part of the DAG
    """
    tex_files = list_files(["statement/*.tex", "testo/*.tex"],
                           valid_extensions=[".tex"])
    for tex_file in tex_files:
        pdf_file = tex_file.replace(".tex", ".pdf")
        language = os.path.split(os.path.splitext(tex_file)[0])[1]
        statement = OIITexStatement(task, os.path.abspath(tex_file))
        statement.compile(pool, language)
        if not pool.config.dry_run:
            statement.pdf_file.getContentsToFile(pdf_file, True, True)
        interface.add_statement(statement)
