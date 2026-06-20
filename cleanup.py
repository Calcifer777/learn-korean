import sys
import re

fn = sys.argv[1]


with open(fn) as fp:
    text = fp.read()


# 1: remove \\n

text = text.replace("\\n", "\n")
text = text.replace(r"\"", r'"')

skip_count = 0
lines = []
for line in text.split("\n"):
    # 2: remove (This is brought to you by TalkToMeInKorean ...)
    if skip_count > 0:
        skip_count -= 1
        continue
    if line.startswith("This is brought to you by TalkToMeInKorean"):
        skip_count = 3
        continue
    skip_count = 0
    # Replace "<name> :" with "<name>:"
    if re.match(pattern=r"^[\w]+ :", string=line):
        line = re.sub(pattern=" :", repl=":", string=line)
        lines.append(line)
    elif len(lines) > 0:
        # Join consecutive lines of same voice actor
        lines[-1] = lines[-1] + " " + line
    else:
        lines.append(line)

lines2 = []
for lid, line in enumerate(lines):
    if "(" not in line:
        lines2.append(line)
        continue
    comments = list(re.finditer(r"\([^\(]+\)", line))
    buffer = line
    prev_end = 0
    name_prev_match = list(re.finditer(pattern="^[\w]+:", string=lines[lid - 1]))[0]
    name_prev = lines[lid - 1][: name_prev_match.span()[1]]
    name_match = list(re.finditer(pattern="^[\w]+:", string=lines[lid]))[0]
    name = lines[lid][: name_match.span()[1]]
    lines2.append(line[: comments[0].span()[0] - 1])
    for cid, c in enumerate(comments):
        comment = line[c.span()[0] + 1 : c.span()[1] - 1]
        lines2.append(name_prev + " " + comment)
        last_idx = (
            len(line) if cid == len(comments) - 1 else comments[cid + 1].span()[0]
        )
        lines2.append(name + " " + line[c.span()[1] + 1 : last_idx])

text = "\n\n".join(lines2)
print(text)
