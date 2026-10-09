import ast
import importlib
import inspect
import pkgutil
import warnings
from pathlib import Path
from unittest.mock import MagicMock

import discord

import black_bloc

SHORT = 45
LONG = 100
SELECT_PLACEHOLDER = 150
TEXT_INPUT = 4
PACKAGE = Path(black_bloc.__file__).parent
SKIP = {"black_bloc.__main__"}

FIELD_LIMITS = {
    "Label": {"text": SHORT, "description": LONG},
    "TextInput": {"label": SHORT, "placeholder": LONG},
    "SelectOption": {"label": LONG, "description": LONG},
    "CheckboxGroupOption": {"label": LONG, "description": LONG},
    "RadioGroupOption": {"label": LONG, "description": LONG},
}
MODAL_LIMITS = {"title": SHORT, "label": SHORT, "placeholder": LONG}


def modules():
    found = []
    for info in pkgutil.walk_packages(black_bloc.__path__, "black_bloc."):
        if info.name in SKIP:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            found.append(importlib.import_module(info.name))
    return found


def modal_classes(mods):
    found = {}
    for mod in mods:
        for value in vars(mod).values():
            if (
                inspect.isclass(value)
                and issubclass(value, discord.ui.Modal)
                and value.__module__ == mod.__name__
            ):
                found[f"{value.__module__}.{value.__qualname__}"] = value
    return found


def build(cls):
    args, kwargs = [], {}
    for param in list(inspect.signature(cls.__init__).parameters.values())[1:]:
        if param.default is not param.empty or param.kind in (
            param.VAR_POSITIONAL,
            param.VAR_KEYWORD,
        ):
            continue
        if param.kind == param.KEYWORD_ONLY:
            kwargs[param.name] = MagicMock()
        else:
            args.append(MagicMock())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return cls(*args, **kwargs)


def overs(node, where, in_options=False, kind=None):
    found = []
    if isinstance(node, list):
        for i, item in enumerate(node):
            found += overs(item, f"{where}[{i}]", in_options, kind)
        return found
    if not isinstance(node, dict):
        return found
    kind = node.get("type", kind)
    for key, value in node.items():
        if not isinstance(value, str):
            found += overs(value, f"{where}.{key}", in_options or key == "options", kind)
            continue
        if key in ("title", "label"):
            cap = LONG if in_options else SHORT
        elif key == "description":
            cap = LONG
        elif key == "placeholder":
            cap = LONG if kind == TEXT_INPUT else SELECT_PLACEHOLDER
        else:
            continue
        if len(value) > cap:
            found.append(f"{where}.{key} is {len(value)} > {cap}: {value!r}")
    return found


def terminal(func):
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def is_super_init(call):
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "__init__"
        and isinstance(func.value, ast.Call)
        and terminal(func.value.func) == "super"
    )


def words(expr, names):
    if not any(isinstance(node, ast.Call) for node in ast.walk(expr)):
        try:
            value = eval(compile(ast.Expression(expr), "<label>", "eval"), dict(names))
        except Exception:
            value = None
        if isinstance(value, str):
            return [value]
    if isinstance(expr, ast.IfExp):
        return words(expr.body, names) + words(expr.orelse, names)
    if isinstance(expr, ast.BoolOp):
        return [one for part in expr.values for one in words(part, names)]
    return []


def literal_overs(mod, modal_names):
    path = Path(mod.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = vars(mod)
    found = []

    def check(expr, cap, what):
        for value in words(expr, names):
            if len(value) > cap:
                spot = f"{path.relative_to(PACKAGE.parent).as_posix()}:{expr.lineno}"
                found.append(f"{spot} {what} is {len(value)} > {cap}: {value!r}")

    def visit(node, in_modal):
        if isinstance(node, ast.ClassDef):
            in_modal = node.name in modal_names
            for keyword in node.keywords if in_modal else []:
                if keyword.arg == "title":
                    check(keyword.value, SHORT, "class title=")
        if isinstance(node, ast.Call):
            name = terminal(node.func)
            limits = FIELD_LIMITS.get(name)
            if limits is None and (
                name in modal_names or name == "Modal" or (in_modal and is_super_init(node))
            ):
                limits = MODAL_LIMITS
            for keyword in node.keywords:
                if limits and keyword.arg in limits:
                    check(keyword.value, limits[keyword.arg], f"{name}({keyword.arg}=)")
        if in_modal and isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr in ("label", "placeholder")
                    and not (isinstance(target.value, ast.Name) and target.value.id == "self")
                ):
                    check(node.value, MODAL_LIMITS[target.attr], f".{target.attr} =")
        for child in ast.iter_child_nodes(node):
            visit(child, in_modal)

    visit(tree, False)
    return found


async def test_every_modal_that_builds_fits_discords_length_limits():
    """Discord refuses the whole modal with a 400 when one word is too long."""
    classes = modal_classes(modules())
    built, found = 0, []
    for name, cls in sorted(classes.items()):
        try:
            payload = build(cls).to_dict()
        except Exception:
            continue
        built += 1
        found += [f"{name}{line}" for line in overs(payload, "")]
    assert built >= 90, f"only {built} of {len(classes)} modals built"
    assert not found, "\n".join(found)


def test_every_literal_modal_word_fits_discords_length_limits():
    """Covers branches and constructors the built modals never reach."""
    mods = modules()
    modal_names = {cls.__name__ for cls in modal_classes(mods).values()}
    found = []
    for mod in mods:
        if getattr(mod, "__file__", "").endswith(".py"):
            found += literal_overs(mod, modal_names)
    assert not found, "\n".join(found)
