"""
Board Extension
#################

Copyright (c) 2022 Paul Würtz
SPDX-License-Identifier: Apache-2.0

Introduction
============

This extension adds a new domain (``boardselector``) for a selection of Boards.
Unlike many other domains, the Board options are not rendered by Sphinx directly but
on the client side using a database built by the extension. A special directive
``.. boardselector:boardsearch::`` can be inserted on any page to render a set of
filter options to allows to browse the database of boards and filter them by peripherals.
"""

from distutils.command.build import build
from itertools import chain
import json
from operator import mod
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterable, List, Optional, Tuple

from docutils import nodes
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.domains import Domain, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.errors import ExtensionError
from sphinx.roles import XRefRole
from sphinx.util import progress_message
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode


__version__ = "0.1.0"


RESOURCES_DIR = Path(__file__).parent / "static"
ZEPHYR_BASE = Path(__file__).parents[4]

SCRIPTS = ZEPHYR_BASE / "scripts"
sys.path.insert(0, str(SCRIPTS))

KCONFIGLIB = SCRIPTS / "kconfig"
sys.path.insert(0, str(KCONFIGLIB))

import zephyr_module
import kconfiglib


def board_load(app: Sphinx) -> Tuple[kconfiglib.Kconfig, Dict[str, str]]:
    """Load Kconfig"""
    with TemporaryDirectory() as td:
        projects = zephyr_module.west_projects()
        projects = [p.posixpath for p in projects["projects"]] if projects else None
        modules = zephyr_module.parse_modules(ZEPHYR_BASE, projects)

        # generate Kconfig.modules file
        kconfig = ""
        for module in modules:
            kconfig += zephyr_module.process_kconfig(module.project, module.meta)

        with open(Path(td) / "Kconfig.modules", "w") as f:
            f.write(kconfig)

        # generate dummy Kconfig.dts file
        kconfig = ""

        with open(Path(td) / "Kconfig.dts", "w") as f:
            f.write(kconfig)

        # base environment
        os.environ["ZEPHYR_BASE"] = str(ZEPHYR_BASE)
        os.environ["srctree"] = str(ZEPHYR_BASE)
        os.environ["KCONFIG_DOC_MODE"] = "1"
        os.environ["KCONFIG_BINARY_DIR"] = td

        # include all archs and boards
        os.environ["ARCH_DIR"] = "arch"
        os.environ["ARCH"] = "*"
        os.environ["BOARD_DIR"] = "boards/*/*"

        # insert external Kconfigs to the environment
        module_paths = dict()
        for module in modules:
            name = module.meta["name"]
            name_var = module.meta["name-sanitized"].upper()
            module_paths[name] = module.project

            build_conf = module.meta.get("build")
            if not build_conf:
                continue

            if build_conf.get("kconfig"):
                kconfig = Path(module.project) / build_conf["kconfig"]
                os.environ[f"ZEPHYR_{name_var}_KCONFIG"] = str(kconfig)
            elif build_conf.get("kconfig-ext"):
                for path in app.config.kconfig_ext_paths:
                    kconfig = Path(path) / "modules" / name / "Kconfig"
                    if kconfig.exists():
                        os.environ[f"ZEPHYR_{name_var}_KCONFIG"] = str(kconfig)

        return kconfiglib.Kconfig(ZEPHYR_BASE / "Kconfig"), module_paths


class BoardSearchNode(nodes.Element):
    @staticmethod
    def html():
        interesting_props = [
            { "name": "cpu", "default_selected": True},
            { "name": "flash", "default_selected": True},
            { "name": "memory", "default_selected": True},
            { "name": "timer", "default_selected": True},
            { "name": "gpio", "default_selected": True},
            { "name": "rtc", "default_selected": True},
            { "name": "i2c", "default_selected": True},
            { "name": "spi", "default_selected": True},
            { "name": "uart", "default_selected": True},
            { "name": "usart", "default_selected": True},
            { "name": "adc", "default_selected": True},
            { "name": "dac", "default_selected": True},
            { "name": "pwm", "default_selected": True},
            { "name": "usb", "default_selected": True},
            { "name": "ethernet", "default_selected": True},
            { "name": "can", "default_selected": True},
            { "name": "timers", "default_selected": True},
            { "name": "serial", "default_selected": True},
            { "name": "sdmmc"},
            { "name": "wdg"},
            { "name": "quadspi"}
        ]
        arches = ["arc", "arm", "arm64", "nios2", "posix", "riscv", "sparc", "x86", "xtensa"]

        default_options = "\n".join(f'''
            <form id="filter-form-{i["name"]}" class="checkbox_select filter-form chip">
                <select name="{i["name"].upper()}" id="add-filters" multiple="multiple">
                    <option value="0">0</option>
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="4+">4+</option>
                </select>

                <input type="submit" />
            </form>''' for i in interesting_props if "default_selected" in i and i["default_selected"]
        )
        filter_options = "\n".join(f'<option data-count="{i}" value="{p["name"]}">{p["name"].upper()}</option>' for i, p in enumerate(interesting_props))
        return f"""<div>
            {default_options}
            <form id="filter-filter-checkboxes" class="checkbox_select">
                <select name="Add a Board filter" id="add-filters" multiple="multiple">
                    {filter_options}
                </select>

                <input type="submit" />
            </form>
        </div>"""


def board_search_visit_html(self, node: nodes.Node) -> None:
    self.body.append(node.html())
    raise nodes.SkipNode


def board_search_visit_latex(self, node: nodes.Node) -> None:
    self.body.append("Board search is only available on HTML output")
    raise nodes.SkipNode


class BoardSearch(SphinxDirective):
    """Kconfig search directive"""

    has_content = False

    def run(self):
        return [BoardSearchNode()]


class _FindBoardSearchDirectiveVisitor(nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)
        self._found = False

    def unknown_visit(self, node: nodes.Node) -> None:
        if self._found:
            return

        self._found = isinstance(node, BoardSearchNode)

    @property
    def found_board_search_directive(self) -> bool:
        return self._found


class BoardSelectorDomain(Domain):
    """Board domain"""

    name = "boardselector"
    label = "Boardselector"
    object_types = {"option": ObjType("option", "option")}
    roles = {"option": XRefRole()}
    directives = {"boardsearch": BoardSearch}
    initial_data: Dict[str, Any] = {"options": []}

    def get_objects(self) -> Iterable[Tuple[str, str, str, str, str, int]]:
        for obj in self.data["options"]:
            yield obj

    def merge_domaindata(self, docnames: List[str], otherdata: Dict) -> None:
        self.data["options"] += otherdata["options"]

    def resolve_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        typ: str,
        target: str,
        node: pending_xref,
        contnode: nodes.Element,
    ) -> Optional[nodes.Element]:
        match = [
            (docname, anchor)
            for name, _, _, docname, anchor, _ in self.get_objects()
            if name == target
        ]

        if match:
            todocname, anchor = match[0]

            return make_refnode(
                builder, fromdocname, todocname, anchor, contnode, anchor
            )
        else:
            return None

    def add_option(self, option):
        """Register a new Board option to the domain."""

        self.data["options"].append(
            (option, option, "option", self.env.docname, option, -1)
        )


def sc_fmt(sc):
    if isinstance(sc, kconfiglib.Symbol):
        if sc.nodes:
            return f'<a href="#CONFIG_{sc.name}">CONFIG_{sc.name}</a>'
    elif isinstance(sc, kconfiglib.Choice):
        if not sc.name:
            return "&ltchoice&gt"
        return f'&ltchoice <a href="#CONFIG_{sc.name}">CONFIG_{sc.name}</a>&gt'

    return kconfiglib.standard_sc_expr_str(sc)


def board_build_resources(app: Sphinx) -> None:
    """Build the Board database and install HTML resources."""

    if not app.config.kconfig_generate_db:
        return

    with progress_message("Building Board database..."):
        board, module_paths = board_load(app)
        db = list()

        for sc in chain(board.unique_defined_syms, board.unique_choices):
            # skip nameless symbols
            if not sc.name:
                continue

            # store alternative defaults (from defconfig files)
            alt_defaults = list()
            for node in sc.nodes:
                if "defconfig" not in node.filename:
                    continue

                for value, cond in node.orig_defaults:
                    fmt = kconfiglib.expr_str(value, sc_fmt)
                    if cond is not sc.kconfig.y:
                        fmt += f" if {kconfiglib.expr_str(cond, sc_fmt)}"
                    alt_defaults.append([fmt, node.filename])

            # build list of symbols that select/imply the current one
            # note: all reverse dependencies are ORed together, and conditionals
            # (e.g. select/imply A if B) turns into A && B. So we first split
            # by OR to include all entries, and we split each one by AND to just
            # take the first entry.
            selected_by = list()
            if isinstance(sc, kconfiglib.Symbol) and sc.rev_dep != sc.kconfig.n:
                for select in kconfiglib.split_expr(sc.rev_dep, kconfiglib.OR):
                    sym = kconfiglib.split_expr(select, kconfiglib.AND)[0]
                    selected_by.append(f"CONFIG_{sym.name}")

            implied_by = list()
            if isinstance(sc, kconfiglib.Symbol) and sc.weak_rev_dep != sc.kconfig.n:
                for select in kconfiglib.split_expr(sc.weak_rev_dep, kconfiglib.OR):
                    sym = kconfiglib.split_expr(select, kconfiglib.AND)[0]
                    implied_by.append(f"CONFIG_{sym.name}")

            # only process nodes with prompt or help
            nodes = [node for node in sc.nodes if node.prompt or node.help]

            inserted_paths = list()
            for node in nodes:
                # avoid duplicate symbols by forcing unique paths. this can
                # happen due to dependencies on 0, a trick used by some modules
                path = f"{node.filename}:{node.linenr}"
                if path in inserted_paths:
                    continue
                inserted_paths.append(path)

                dependencies = None
                if node.dep is not sc.kconfig.y:
                    dependencies = kconfiglib.expr_str(node.dep, sc_fmt)

                defaults = list()
                for value, cond in node.orig_defaults:
                    fmt = kconfiglib.expr_str(value, sc_fmt)
                    if cond is not sc.kconfig.y:
                        fmt += f" if {kconfiglib.expr_str(cond, sc_fmt)}"
                    defaults.append(fmt)

                selects = list()
                for value, cond in node.orig_selects:
                    fmt = kconfiglib.expr_str(value, sc_fmt)
                    if cond is not sc.kconfig.y:
                        fmt += f" if {kconfiglib.expr_str(cond, sc_fmt)}"
                    selects.append(fmt)

                implies = list()
                for value, cond in node.orig_implies:
                    fmt = kconfiglib.expr_str(value, sc_fmt)
                    if cond is not sc.kconfig.y:
                        fmt += f" if {kconfiglib.expr_str(cond, sc_fmt)}"
                    implies.append(fmt)

                ranges = list()
                for min, max, cond in node.orig_ranges:
                    fmt = (
                        f"[{kconfiglib.expr_str(min, sc_fmt)}, "
                        f"{kconfiglib.expr_str(max, sc_fmt)}]"
                    )
                    if cond is not sc.kconfig.y:
                        fmt += f" if {kconfiglib.expr_str(cond, sc_fmt)}"
                    ranges.append(fmt)

                choices = list()
                if isinstance(sc, kconfiglib.Choice):
                    for sym in sc.syms:
                        choices.append(kconfiglib.expr_str(sym, sc_fmt))

                menupath = ""
                iternode = node
                while iternode.parent is not iternode.kconfig.top_node:
                    iternode = iternode.parent
                    if iternode.prompt:
                        title = iternode.prompt[0]
                    else:
                        title = kconfiglib.standard_sc_expr_str(iternode.item)
                    menupath = f" > {title}" + menupath

                menupath = "(Top)" + menupath

                filename = node.filename
                for name, path in module_paths.items():
                    if node.filename.startswith(path):
                        filename = node.filename.replace(path, f"<module:{name}>")
                        break

                db.append(
                    {
                        "name": f"CONFIG_{sc.name}",
                        "prompt": node.prompt[0] if node.prompt else None,
                        "type": kconfiglib.TYPE_TO_STR[sc.type],
                        "help": node.help,
                        "dependencies": dependencies,
                        "defaults": defaults,
                        "alt_defaults": alt_defaults,
                        "selects": selects,
                        "selected_by": selected_by,
                        "implies": implies,
                        "implied_by": implied_by,
                        "ranges": ranges,
                        "choices": choices,
                        "filename": filename,
                        "linenr": node.linenr,
                        "menupath": menupath,
                    }
                )

        app.env.kconfig_db = db  # type: ignore

        outdir = Path(app.outdir) / "board"
        outdir.mkdir(exist_ok=True)

        board_db_file = outdir / "board.json"

        with open(board_db_file, "w") as f:
            json.dump(db, f)

    app.config.html_extra_path.append(board_db_file.as_posix())
    app.config.html_static_path.append(RESOURCES_DIR.as_posix())


def board_install(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: Dict,
    doctree: Optional[nodes.Node],
) -> None:
    """Install the Board library files on pages that require it."""
    if (
        not app.config.kconfig_generate_db
        or app.builder.format != "html"
        or not doctree
    ):
        return

    visitor = _FindBoardSearchDirectiveVisitor(doctree)
    doctree.walk(visitor)


def setup(app: Sphinx):
    app.add_config_value("board_generate_db", True, "env")
    app.add_config_value("board_ext_paths", [], "env")

    app.add_node(
        BoardSearchNode,
        html=(board_search_visit_html, None),
        latex=(board_search_visit_latex, None),
    )

    app.add_domain(BoardSelectorDomain)

    app.connect("builder-inited", board_build_resources)
    app.connect("html-page-context", board_install)

    app.add_css_file("boardselector.css")
    app.add_js_file("boardselector.mjs", type="module")

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
