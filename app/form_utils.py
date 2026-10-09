"""Safe parsing of numeric form fields.

`request.form.get('x', 12.0)` only falls back to the default when the key is
absent. A field the user cleared is submitted as an empty string, so the
default is skipped and float('') raises ValueError - a 500 that discards the
whole submission. These helpers treat blank, whitespace and unparseable input
as "not supplied" and return the default instead.
"""


def form_float(form, key, default=0.0):
    """Read a float from a form, falling back to default on blank/bad input."""
    raw = form.get(key)
    if raw is None:
        return float(default)
    try:
        raw = raw.strip()
    except AttributeError:
        pass
    if raw == '':
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def form_int(form, key, default=0):
    """Read an int from a form, falling back to default on blank/bad input."""
    raw = form.get(key)
    if raw is None:
        return int(default)
    try:
        raw = raw.strip()
    except AttributeError:
        pass
    if raw == '':
        return int(default)
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return int(default)


def form_opt_float(form, key):
    """Read an optional float - returns None when blank, for nullable columns."""
    raw = form.get(key)
    if raw is None:
        return None
    try:
        raw = raw.strip()
    except AttributeError:
        pass
    if raw == '':
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def form_opt_int(form, key):
    """Read an optional int - returns None when blank, for nullable FK columns."""
    raw = form.get(key)
    if raw is None:
        return None
    try:
        raw = raw.strip()
    except AttributeError:
        pass
    if raw == '':
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def form_date(form, key, default=None):
    """Read an ISO date from a form, falling back to default (or today) on blank/bad input."""
    from datetime import date as _date
    if default is None:
        default = _date.today()
    raw = form.get(key)
    if raw is None:
        return default
    try:
        raw = raw.strip()
    except AttributeError:
        pass
    if raw == '':
        return default
    try:
        return _date.fromisoformat(raw)
    except (TypeError, ValueError):
        return default
