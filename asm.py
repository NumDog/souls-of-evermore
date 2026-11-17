# Winziger 65816-Assembler fuer Patches: Liste aus Bytes/Strings; "name:" = Marke, ("bra8", op, "marke") / ("abs16", "marke")
def assemble(base, items):
    labels = {}; pc = base
    for it in items:                       # 1. Durchlauf: Marken
        if isinstance(it, str) and it.endswith(':'): labels[it[:-1]] = pc
        elif isinstance(it, tuple): pc += 2 if it[0]=='bra8' else 3 if it[0] in ('jmp','jsr') else 0
        else: pc += len(it)
    out = bytearray(); pc = base
    for it in items:
        if isinstance(it, str) and it.endswith(':'): continue
        if isinstance(it, tuple):
            if it[0]=='bra8':
                d = labels[it[2]] - (pc+2); assert -128 <= d < 128, (it, d); out += bytes([it[1], d & 0xFF]); pc += 2
            elif it[0] in ('jmp','jsr'):
                t = labels[it[1]]; out += bytes([0x4C if it[0]=='jmp' else 0x20, t & 0xFF, (t>>8) & 0xFF]); pc += 3
        else:
            out += bytes(it); pc += len(it)
    return bytes(out), labels
