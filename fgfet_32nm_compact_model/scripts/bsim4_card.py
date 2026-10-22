"""Read / write BSIM4 .model cards in the PTM layout (one `+name = value` grid)."""
import re
from collections import OrderedDict


def parse_card(path, model_name):
    """Return (device_type, OrderedDict(param -> value-string)) for `.model model_name`."""
    text = open(path).read()
    blocks = re.split(r"(?im)^\s*\.model\s+", text)[1:]
    for blk in blocks:
        head, *rest = blk.split("\n", 1)
        name, dtype = head.split()[:2]
        if name.lower() != model_name.lower():
            continue
        body = head + "\n" + (rest[0] if rest else "")
        params = OrderedDict()
        for k, v in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)", body):
            params[k.lower()] = v
        return dtype.lower(), params
    raise KeyError(f"model {model_name} not found in {path}")


def fmt(v):
    if isinstance(v, str):
        return v
    if float(v).is_integer() and abs(v) < 1e6:
        return str(int(v))
    return f"{v:.6g}"


def card_text(name, dtype, params, comment=""):
    lines = []
    if comment:
        lines += ["* " + c for c in comment.strip().splitlines()]
    lines.append(f".model  {name}  {dtype}  level = 54")
    items = [f"{k:<8s}= {fmt(v):<16s}" for k, v in params.items() if k != "level"]
    for i in range(0, len(items), 4):
        lines.append("+" + "  ".join(items[i:i + 4]).rstrip())
    return "\n".join(lines) + "\n"


def write_card(path, cards, header=""):
    """cards: list of (name, dtype, params, comment)."""
    with open(path, "w") as f:
        if header:
            f.write("".join("* " + h + "\n" for h in header.strip().splitlines()) + "\n")
        for name, dtype, params, comment in cards:
            f.write(card_text(name, dtype, params, comment) + "\n")
