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
        arches = ["arc", "arm", "arm64", "nios2", "posix", "riscv", "sparc", "x86", "xtensa"]
        number_options = ["0", "1" , "2", "3", "4+"]
        interesting_props = [
            { "name": "arch", "options": arches},
            # { "name": "cpu",,
            # { "name": "flash",,
            # { "name": "memory",,
            { "name": "timer", "options": number_options},
            { "name": "gpio", "options": number_options},
            { "name": "rtc", "options": number_options},
            { "name": "i2c", "options": number_options},
            { "name": "spi", "options": number_options},
            { "name": "uart", "options": number_options},
            { "name": "usart", "options": number_options},
            { "name": "adc", "options": number_options},
            { "name": "dac", "options": number_options},
            { "name": "pwm", "options": number_options},
            { "name": "usb", "options": number_options},
            { "name": "ethernet", "options": number_options},
            { "name": "can", "options": number_options},
            { "name": "timers", "options": number_options},
            { "name": "serial", "options": number_options},
            { "name": "sdmmc", "options": number_options},
            { "name": "wdg", "options": number_options},
            { "name": "quadspi", "options": number_options}
        ]

        close_option_str = "</option>"
        default_options = "\n".join(f'''
            <form id="filter-form-{i["name"]}" class="checkbox_select filter-form chip">
                <select name="{i["name"].upper()}" id="add-filters-{i["name"]}" multiple="multiple">
                    {"".join([f"<option value='{opt}'>{opt}{close_option_str}" for opt in i["options"]])}
                </select>
                <input type="submit" />
            </form>''' for i in interesting_props
        )
        filter_options = "\n".join(f'<option data-count="{i}" value="{p["name"]}">{p["name"].upper()}</option>' for i, p in enumerate(interesting_props))
        return f"""<div id="board-search">
            {default_options}
            <form id="filter-filter-checkboxes" class="checkbox_select">
                <select name="Add a Board filter" id="add-filters" multiple="multiple">
                    {filter_options}
                </select>

                <input type="submit" />
            </form>
            <hr>
            <div id="__board-search-results"></div>
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
        db = open(RESOURCES_DIR / "devices.json", "r").read()

        outdir = Path(app.outdir) / "board"
        outdir.mkdir(exist_ok=True)

        board_db_file = outdir / "board.json"

        with open(board_db_file, "w") as f:
            f.write(db)

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
