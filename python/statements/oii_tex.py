#!/usr/bin/env python3

import glob
import os.path
import re
import ruamel.yaml
import shutil
import subprocess
from string import Template
from task_maker.args import Arch, CacheMode
from task_maker.config import Config
from task_maker.formats import IOITask
from task_maker.languages import Dependency
from task_maker.source_file import SourceFile
from task_maker.statements import Statement, StatementDepInfo
from task_maker.task_maker_frontend import Frontend, Execution, File
from typing import Optional, NamedTuple, List

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
    extra_packages = re.findall("\\\\usepackage.+", content)
    content = content.replace("\\usepackage", "% \\usepackage")
    return ExtractPackagesResult(content, extra_packages)


def build_tex_file(config: Config, task: IOITask,
                   tex: ExtractPackagesResult) -> str:
    """
    Build the main TeX file from the statement file, from the task template and
    using the information from task.yaml, contest.yaml and --set flags
    """
    template_dir = get_template_dir()
    template_file_path = os.path.join(template_dir, "task.tpl")
    template_defaults_path = os.path.join(template_dir, "defaults.yaml")
    contest_yaml_path = os.path.join(
        os.path.dirname(config.task_dir), "contest.yaml")
    with open(template_file_path) as f:
        template_content = f.read()
    with open(template_defaults_path) as f:
        defaults = ruamel.yaml.safe_load(f)

    template = Template(template_content)
    mapping = defaults
    # apply the options from contest.yaml
    if os.path.exists(contest_yaml_path):
        with open(contest_yaml_path) as f:
            contest_yaml = ruamel.yaml.safe_load(f)
        for k, v in contest_yaml.items():
            if v is not None and k in mapping:
                mapping[k] = v
    # apply the options from task.yaml
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

    showsummary = True if mapping["showsummary"] else False
    showsolutions = True if mapping["showsolutions"] else False

    mapping["__language"] = "english"
    mapping["__content"] = tex.content
    mapping["__packages"] = "\n".join(tex.packages)
    mapping["__showsummary"] = "showsummary" if showsummary else ""
    mapping["__showsolutions"] = "showsolutions" if showsolutions else ""

    return template.substitute(mapping)


def get_dependencies_via_latexmk(statement_dir: str,
                                 tex: str) -> List[Dependency]:
    """
    Assuming latexmk is present, the dependencies are found using latexmk -M
    In order to work latexmk needs all the files, to make this faster all the
    non-template files are created empty, in a temporary directory. The
    directory is kept for performance reasons, on my machine the first run takes
    ~900ms, from the second one it takes ~80ms.
    """
    files = [f[len(statement_dir) + 1:] for f in get_files(statement_dir)]
    tmpdir = "/tmp/task-maker-latexmk-" + os.path.basename(os.getcwd())
    # create all the files empty
    for f in files:
        path = os.path.join(tmpdir, f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as _:
            pass
    # copy the real template files
    data_dir = os.path.join(get_template_dir(), "data")
    for f in get_files(data_dir):
        path = os.path.join(tmpdir, f[len(data_dir) + 1:])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copy(f, path)
    # create the real statement.tex file
    with open(os.path.join(tmpdir, "statement.tex"), "w") as f:
        f.write(tex)
    # execute latexmk -M in non interactive mode
    proc = subprocess.run(
        ["latexmk", "-M", "-f", "-interaction=nonstopmode", "statement.tex"],
        cwd=tmpdir,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL)
    # the output is in this form:
    #
    #   ...random LaTeX stuff...
    #   #===Dependents, and related info, for statement.tex:
    #   statement.dvi :\
    #       /system/level/deps\
    #       user/level/deps\
    #       some/other/dep
    #   #===End dependents for statement.tex:
    #   ...other random stuff...
    #
    # Will search the indexes of #=== and keep only the lines between them
    stdout = proc.stdout.decode().split("\n")
    indexes = [i for i, v in enumerate(stdout) if v.startswith("#===")]
    # the output is malformed, will use the dumb method
    if len(indexes) != 2:
        return get_dependencies_dumb(statement_dir)
    deps = [
        d.strip().strip("\\") for d in stdout[indexes[0] + 2:indexes[1]]
        if not d.strip().startswith("/")
    ]
    return [
        Dependency(d, os.path.join(statement_dir, d)) for d in deps
        if d != "statement.tex"
    ]


def get_dependencies_dumb(statement_dir: str) -> List[Dependency]:
    """
    If latexmk is not preset on this system all the files in the statement
    folder are considered dependencies
    """
    return [
        Dependency(f[len(statement_dir) + 1:], f)
        for f in get_files(statement_dir)
    ]


def get_dependencies(statement_dir: str, tex: str) -> List[Dependency]:
    """
    Search for all the dependencies of the tex file, using latexmk if possible,
    otherwise a simpler but slower method is used.
    """
    if shutil.which("latexmk"):
        return get_dependencies_via_latexmk(statement_dir, tex)
    else:
        return get_dependencies_dumb(statement_dir)


class OIITexStatement(Statement):
    """
    Format of the OII-like tasks, a latex file with is embedded inside a
    template which uses a latex class. This is the default template of
    cmsbooklet.
    """

    def __init__(self, task: IOITask, path: str, write_pdf_to: Optional[str]):
        super().__init__(path, write_pdf_to)
        self.outfile = self.name.replace(".tex", ".pdf")
        self.task = task
        self.compilation = None  # type: Execution
        self.pdf_file = None  # type: File

    def compile(self, config: Config, frontend: Frontend):
        with open(self.path, "r") as f:
            content = f.read()
        process = extract_packages(content)
        final_tex_file = build_tex_file(config, self.task, process)
        deps = get_dependencies(os.path.dirname(self.path), final_tex_file)

        self.compilation = frontend.addExecution(
            "Compilation of statement %s" % self.name)
        file = frontend.provideFileContent(final_tex_file,
                                           "Statement file %s" % self.name)
        self.compilation.addInput(self.name, file)
        if config.cache == CacheMode.NOTHING:
            self.compilation.disableCache()
        self.pdf_file = self.compilation.output(self.outfile)
        self.compilation.setExecutablePath("latexmk")
        self.compilation.setArgs(
            ["-f", "-interaction=nonstopmode", "-pdf", self.name])
        self.pdf_file = self.pdf_file

        for dep in deps:
            if not os.path.exists(dep.path):
                continue
            # non asy files, like images or other tex files, they are just
            # copied inside the sandbox
            if "asy" not in dep.path:
                file = frontend.provideFile(
                    dep.path, "Statement dependency %s" % dep.name)
                self.compilation.addInput(dep.name, file)
                continue
            # the asymptote files needs to be compiled into pdf and then cropped
            path = dep.path.replace(".pdf", ".asy")
            name = dep.name.replace(".pdf", ".asy")
            # it's possible that a pdf file is in the asy directory but the
            # corresponding asy is not, in this skip the recompilation
            if not os.path.exists(path):
                pdf = frontend.provideFile(
                    dep.path, "Already compiled asy file %s" % dep.name)
                self.compilation.addInput(dep.name, pdf)
                continue

            # compile the asy file like a normal source file
            source_file = SourceFile.from_file(path, name, False, None,
                                               Arch.DEFAULT, dict())
            source_file.prepare(frontend, config)
            self.other_executions.append(
                StatementDepInfo(name, source_file.compilation))
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
            self.other_executions.append(
                StatementDepInfo("Crop %s" % source_file.exe_name, crop))
            self.compilation.addInput(dep.name, cropped_asy)

        # add the template files to the sandbox
        data_dir = os.path.join(get_template_dir(), "data")
        for path in get_files(data_dir):
            name = path[len(data_dir) + 1:]
            file = frontend.provideFile(path, "Template file %s" % name)
            self.compilation.addInput(name, file)
