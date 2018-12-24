#!/usr/bin/env python3

import glob
import os.path
import re
import ruamel.yaml
from string import Template
from task_maker.args import Arch, CacheMode
from task_maker.config import Config
from task_maker.formats import IOITask
from task_maker.languages import Dependency
from task_maker.source_file import SourceFile
from task_maker.statements import Statement, StatementDepInfo
from task_maker.task_maker_frontend import Frontend, Execution, File
from typing import Optional, NamedTuple, List, Set, Tuple

# Result of the extraction of the \\usepackage
ExtractPackagesResult = NamedTuple("ExtractPackagesResult",
                                   [("content", str), ("packages", List[str])])


def get_template_dir() -> str:
    """
    Find the directory where the template files are stored
    """
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates", "oii_tex")


def get_files(directory: str) -> List[str]:
    """
    List all the files in a directory
    """
    return [
        f for f in glob.glob(os.path.join(directory, "**"), recursive=True)
        if os.path.isfile(f)
    ]


def extract_packages(content: str) -> ExtractPackagesResult:
    """
    Extract the packages and remove them from the statement, they will be
    added later at the top of the final tex file
    """
    extra_packages = re.findall("^\\\\usepackage.+", content, re.MULTILINE)
    content = content.replace("\\usepackage", "% \\usepackage")
    return ExtractPackagesResult(content, extra_packages)


def get_template_parameters(config: Config,
                            task: Optional[IOITask],
                            language: str = None):
    """
    Build the mapping dict with the parameters to send to the task and contest
    templated. The __content, __packages and __tasks parameters are not set.
    """
    template_dir = get_template_dir()
    template_defaults_path = os.path.join(template_dir, "defaults.yaml")
    contest_yaml_path = os.path.join(
        os.path.dirname(config.task_dir), "contest.yaml")
    with open(template_defaults_path) as f:
        defaults = ruamel.yaml.safe_load(f)
    mapping = defaults
    # apply the options from contest.yaml
    if os.path.exists(contest_yaml_path):
        with open(contest_yaml_path) as f:
            contest_yaml = ruamel.yaml.safe_load(f)
        for k, v in contest_yaml.items():
            if v is not None and k in mapping:
                mapping[k] = v
    # apply the options from task.yaml
    if task:
        for k, v in task.yaml.items():
            if v is not None and k in mapping:
                mapping[k] = v
    # apply the options from --set
    for opt in config.set:
        if "=" in opt:
            key, value = opt.split("=", 1)
            if key in mapping:
                mapping[key] = value
        else:
            if opt in mapping:
                mapping[opt] = True

    # default values for infile/outfile
    if not mapping["infile"]:
        mapping["infile"] = "stdin"
    if not mapping["outfile"]:
        mapping["outfile"] = "stdout"
    if language:
        mapping["language"] = language

    showsummary = True if mapping["showsummary"] else False
    showsolutions = True if mapping["showsolutions"] else False

    mapping["__language"] = mapping["language"]
    mapping["__showsummary"] = "showsummary" if showsummary else ""
    mapping["__showsolutions"] = "showsolutions" if showsolutions else ""
    return mapping


def build_task_tex_file(config: Config,
                        task: IOITask,
                        tex: str,
                        language: Optional[str] = None) -> str:
    """
    Build the TeX file from the statement file, from the task template and
    using the information from task.yaml, contest.yaml and --set flags.
    """
    template_dir = get_template_dir()
    task_template_path = os.path.join(template_dir, "task.tpl")
    with open(task_template_path) as f:
        task_template_content = f.read()
    task_template = Template(task_template_content)

    template_parameters = get_template_parameters(config, task, language)
    return task_template.substitute(template_parameters, __content=tex)


def build_contest_tex_file(config: Config,
                           packages: Set[str],
                           statement_files: List[str],
                           language: Optional[str] = None) -> str:
    """
    Build the contest TeX file which will include all the statement files.
    """
    template_dir = get_template_dir()

    contest_template_path = os.path.join(template_dir, "contest.tpl")
    with open(contest_template_path) as f:
        contest_template_content = f.read()
    contest_template = Template(contest_template_content)
    tasks = ["\\input{%s}" % s for s in statement_files]
    template_parameters = get_template_parameters(config, None, language)
    return contest_template.substitute(
        template_parameters,
        __packages="\n".join(packages),
        __tasks="\n".join(tasks))


def get_dependencies(statement_dir: str, tex: str) -> List[Dependency]:
    """
    Search for all the dependencies of the tex file.
    """

    def is_valid_dep(path):
        ext = os.path.splitext(path)[1]
        if ext == ".asy":
            pdf = os.path.basename(path.replace(".asy", ".pdf"))
            return pdf in tex
        elif ext == ".pdf":
            pdf = os.path.basename(path)
            asy = path.replace(".pdf", ".asy")
            return pdf in tex and not os.path.exists(asy)
        else:
            return True

    return [
        Dependency(f[len(statement_dir) + 1:], f)
        for f in get_files(statement_dir) if is_valid_dep(f)
    ]


class OIITexStatement(Statement):
    """
    Format of the OII-like tasks, a latex file with is embedded inside a
    template which uses a latex class. This is the default template of
    cmsbooklet.
    """

    def __init__(self, task: IOITask, path: str):
        super().__init__(path)
        self.outfile = self.name.replace(".tex", ".pdf")
        self.task = task
        self.compilation = None  # type: Execution
        self.pdf_file = None  # type: File

    def compile(self,
                config: Config,
                frontend: Frontend,
                language: Optional[str] = None):
        compilation, pdf_file, other_executions = \
            OIITexStatement.compile_booklet(config, frontend,
                                            [self], language)
        self.compilation = compilation
        self.pdf_file = pdf_file
        self.other_executions = other_executions

    @staticmethod
    def compile_booklet(config: Config,
                        frontend: Frontend,
                        statements: List["OIITexStatement"],
                        language: Optional[str] = None
                        ) -> Tuple[Execution, File, List[StatementDepInfo]]:
        compilation = frontend.addExecution("Compilation of booklet")
        other_executions = []  # type: List[StatementDepInfo]

        data_dir = os.path.join(get_template_dir(), "data")
        template_files = set(get_files(data_dir))

        packages = set()  # type: Set[str]
        statement_files = []  # type: List[str]
        task_names = list()  # type: List[str]
        for statement in statements:
            task_name = statement.task.name
            task_names.append(task_name)
            with open(statement.path, "r") as f:
                content = f.read()
            tex = extract_packages(content)
            packages |= set(tex.packages)
            task_tex_file = build_task_tex_file(config, statement.task,
                                                tex.content, language)
            deps = get_dependencies(
                os.path.dirname(statement.path), task_tex_file)

            file = frontend.provideFileContent(
                task_tex_file, "Statement file %s" % statement.name)

            compilation.addInput(os.path.join(task_name, statement.name), file)
            statement_files.append(os.path.join(task_name, statement.name))

            for dep in deps:
                if os.path.join(data_dir, dep.name) in template_files:
                    # skip the template files
                    continue
                # non asy files, like images or other tex files, they are just
                # copied inside the sandbox
                if os.path.splitext(dep.path)[1] != ".asy":
                    file = frontend.provideFile(
                        dep.path, "Statement dependency %s" % dep.name)
                    compilation.addInput(
                        os.path.join(task_name, dep.name), file)
                    continue
                # the asymptote files needs to be compiled into pdf and then
                # cropped
                name = dep.name.replace(".asy", ".pdf")
                # compile the asy file like a normal source file
                source_file = SourceFile.from_file(dep.path, dep.name, False,
                                                   None, Arch.DEFAULT, dict())
                source_file.prepare(frontend, config)
                other_executions.append(
                    StatementDepInfo(dep.name, source_file.compilation))
                # crop the pdf using pdfcrop
                crop = frontend.addExecution(
                    "Crop compiled asy file %s" % dep.name)
                crop.addInput(
                    "file.pdf",
                    source_file.executable)  # the "executable" is the pdf file
                if config.cache == CacheMode.NOTHING:
                    crop.disableCache()
                cropped_asy = crop.output("file-crop.pdf")
                crop.setExecutablePath("pdfcrop")
                crop.setArgs(["file.pdf"])
                other_executions.append(
                    StatementDepInfo("Crop %s" % source_file.exe_name, crop))
                compilation.addInput(
                    os.path.join(task_name, name), cropped_asy)

        if config.cache == CacheMode.NOTHING:
            compilation.disableCache()

        pdf_file = compilation.output("booklet.pdf")
        # TODO eventually use directly latexmk when setting env vars will be
        #  supported
        compilation.setExecutablePath("env")
        compilation.setArgs([
            "TEXINPUTS=.:%s:" % ":".join(task_names), "latexmk", "-f",
            "-interaction=nonstopmode", "-pdf", "booklet.tex"
        ])
        booklet_tex = build_contest_tex_file(config, packages, statement_files,
                                             language)
        booklet = frontend.provideFileContent(booklet_tex,
                                              "Booklet source file")
        compilation.addInput("booklet.tex", booklet)

        # add the template files to the sandbox
        for path in template_files:
            name = path[len(data_dir) + 1:]
            file = frontend.provideFile(path, "Template file %s" % name)
            compilation.addInput(name, file)

        return compilation, pdf_file, other_executions
