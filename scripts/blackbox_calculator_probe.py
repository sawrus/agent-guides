#!/usr/bin/env python3
"""Independent arithmetic probe for delivered Python calculator modules.

Unsupported interfaces fail explicitly; native traces or self-reported tests cannot pass this check.
"""
import ast
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
import subprocess
import shutil

CASES = [('addition', '9 + 4', 9, '+', 4, 13), ('subtraction', '9 - 4', 9, '-', 4, 5),
         ('multiplication', '9 * 4', 9, '*', 4, 36), ('division', '9 / 4', 9, '/', 4, 2.25)]


def main(project):
    project = Path(project)
    sys.path.insert(0, str(project))
    sys.path.insert(0, str(project / 'src'))
    for path in project.rglob('*.py'):
        if any(p.startswith('.') or p in ('node_modules', 'venv', 'tests') for p in path.relative_to(project).parts):
            continue
        if path.name.startswith('test') or path.stat().st_size > 65536:
            continue
        try:
            tree = ast.parse(path.read_text())
            names = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
            candidates = [name for name in names if any(word in name.lower() for word in ('calculate', 'evaluate', 'compute'))]
            classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef) and any(isinstance(method, ast.FunctionDef) and method.name == 'press' for method in node.body)]
            if not candidates and not classes:
                continue
            spec = importlib.util.spec_from_file_location('blackbox_calculator', path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            for name in classes:
                cls = getattr(module, name)
                def press_expression(expression):
                    engine = cls()
                    for key in expression.replace(' ', '') + '=':
                        display = engine.press(key)
                    return display if display is not None else engine.display
                verified = {}
                try:
                    for label, expr, _, _, _, expected in CASES:
                        verified[label] = math.isclose(float(press_expression(expr)), expected)
                    try:
                        zero = press_expression('9/0')
                        verified['division_by_zero'] = isinstance(zero, str) and any(word in zero.lower() for word in ('error', 'ошиб', 'zero', 'нол'))
                    except (ZeroDivisionError, ValueError):
                        verified['division_by_zero'] = True
                    if all(verified.values()):
                        return {'verified': True, 'checks': verified, 'entrypoint': str(path.relative_to(project)) + ':' + name + '.press'}
                except (TypeError, ValueError, AttributeError):
                    pass
            for name in candidates:
                function = getattr(module, name)
                params = list(inspect.signature(function).parameters)
                if len(params) == 1:
                    invoke = lambda expr, a, op, b: function(expr)
                elif len(params) == 3:
                    op_index = next((i for i, p in enumerate(params) if p.lower() in ('op', 'operator', 'operation')), None)
                    if op_index is None:
                        continue
                    def invoke(expr, a, op, b):
                        args = [a, b]
                        args.insert(op_index, op)
                        return function(*args)
                else:
                    continue
                verified = {}
                for label, expr, a, op, b, expected in CASES:
                    actual = invoke(expr, a, op, b)
                    verified[label] = isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isclose(actual, expected)
                try:
                    zero = invoke('9 / 0', 9, '/', 0)
                    verified['division_by_zero'] = zero is None or isinstance(zero, str) and any(word in zero.lower() for word in ('zero', 'ноль', 'нуль', 'ошиб', 'error'))
                except (ZeroDivisionError, ValueError):
                    verified['division_by_zero'] = True
                if all(verified.values()):
                    return {'verified': True, 'checks': verified, 'entrypoint': str(path.relative_to(project)) + ':' + name}
        except (Exception, SystemExit):
            continue
    if shutil.which('node'):
        modules = [str(p) for pattern in ('*.js', '*.mjs') for p in project.rglob(pattern)
                   if not any(part.startswith('.') or part in ('node_modules', 'tests', 'dist') for part in p.relative_to(project).parts)
                   and p.stat().st_size < 65536]
        if modules:
            try:
                result = subprocess.run(['node', str(Path(__file__).with_suffix('.mjs')), *modules], capture_output=True, text=True, timeout=15)
                evidence = json.loads(result.stdout)
                if result.returncode == 0 and evidence.get('verified') is True:
                    return evidence
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
    return {'verified': False, 'reason': 'No supported public Python/JavaScript calculator interface; supply an independent verifier for this stack.'}


if __name__ == '__main__':
    result = main(sys.argv[1])
    print(json.dumps(result))
    raise SystemExit(0 if result['verified'] else 1)
