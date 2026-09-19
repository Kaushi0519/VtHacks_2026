from fnmatch import fnmatchcase


def scope_matches(pattern: str, scope: str) -> bool:
    """fnmatch semantics: "payroll.*" matches "payroll.salary.read"."""
    return fnmatchcase(scope, pattern)


def any_match(patterns: list[str], scope: str) -> bool:
    return any(scope_matches(p, scope) for p in patterns)
