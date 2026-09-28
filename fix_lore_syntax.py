import py_compile

with open("backend/routers/lore.py", "r") as f:
    code = f.read()

lines = code.splitlines()
fixed_lines = []
skip = False

for i, line in enumerate(lines):
    if skip:
        skip = False
        continue
    # Catch the broken string literal split across two lines
    if 'context_blocks = "' in line and i + 1 < len(lines) and '".join([' in lines[i+1]:
        fixed_lines.append('    context_blocks = chr(10).join([f"--- Excerpt from {r[\'title\']} ---\\n{r[\'content\'][:1000]}" for r in results])')
        skip = True
    else:
        fixed_lines.append(line)

fixed_code = "\n".join(fixed_lines)

with open("backend/routers/lore.py", "w") as f:
    f.write(fixed_code)

# Verify zero syntax errors
py_compile.compile("backend/routers/lore.py", doraise=True)
print("✅ backend/routers/lore.py repaired and compiled with 0 syntax errors.")
