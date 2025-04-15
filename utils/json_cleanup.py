# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Context: https://stackoverflow.com/a/56701174/149900

from io import StringIO


WHITESPACE = " \t\r\n"
DANGLING_COMMA = {',]', ',}'}
MALFORMED_NUMBER = {':.', '[.', ',.', '-.'}


def json_cleanup(dirty_json: str) -> str:
    """
    Takes a "dirty" JSON (having comments, dangling comma, and other horrors)
    and clean it up.
    Warning: Will totally remove whitespace outside strings, effectively
    flattening the JSON into something non-human-readable (but perfectly
    machine-parseable).
    If you need pretty JSON, parse the result of this function, then feed it
    through json.dumps() with indent=2

    :param dirty_json: "Dirty" JSON string
    :return: "Clean" JSON string that won't blow up json.loads()
    """
    # Step 0: Remove leading/trailing spaces
    dirtylst = []
    for ln in dirty_json.split('\n'):
        ln = ln.strip()
        if ln:
            dirtylst.append(ln)

    # Step 1: Strip block-comments
    # Need to keep the newlines for easier parsing here AND in the next step
    dirty = '\n'.join(dirtylst) + '\n'
    with StringIO() as cmtless:
        block_cmt = False
        pos = 0
        while pos < len(dirty):
            diph = dirty[pos:pos+2]
            if block_cmt:
                if diph == "*/":
                    block_cmt = False
                    pos += 1
                pos += 1
                continue
            elif diph == "/*":
                block_cmt = True
                pos += 2
                continue
            cmtless.write(diph[0])
            pos += 1
        dirty = cmtless.getvalue()

    # Step 2: Strip end-of-line comments & whitespace-outside-string
    clnlist = []
    escaped = False
    for ln in dirty.split('\n'):
        ln = ln.strip()
        if not ln:
            continue
        in_str = False
        with StringIO() as cln:
            for pos in range(0, len(ln)):
                c = ln[pos]
                if escaped:
                    escaped = False
                    cln.write(c)
                    continue
                diph = ln[pos:pos+2]
                if not in_str:
                    if diph == '//':  # JS-style comment
                        break
                    if c == '#':  # Python-style comment
                        break
                    if c in WHITESPACE:
                        continue
                    if c == '"':
                        in_str = True
                else:
                    if c == "\\":  # Actually a single backslash
                        escaped = True
                    if c == '"':
                        in_str = False
                cln.write(c)
            cleaned = cln.getvalue().strip()
        if cleaned:
            clnlist.append(cleaned)
    # Now we collapse the separate lines into one, to detect dangling commas &
    # malformed numbers
    mini = "".join(clnlist)

    # Step 4: Remove dangling commas, fix malformed numbers
    in_str = False
    escaped = False
    with StringIO() as cln:
        for pos in range(0, len(mini)):
            c = mini[pos]
            if escaped:
                escaped = False
                cln.write(c)
                continue
            if in_str:
                cln.write(c)
                if c == "\\":
                    escaped = True
                if c == '"':
                    in_str = False
                continue
            diph = mini[pos:pos+2]
            if diph in DANGLING_COMMA:
                # Since we don't append c to cleaned, we're practically
                # skipping over the dangling comma
                continue
            if diph in MALFORMED_NUMBER:
                # Commit the first char, prepare "0" as the next; this will
                # add a leading "0" to the malformed number
                cln.write(c)
                c = "0"
            cln.write(c)
            if c == '"':
                in_str = True
        cleaned = cln.getvalue()

    # Step 5: Remove trailing comma, if any
    if cleaned.endswith(","):
        return cleaned[:-1]
    else:
        return cleaned
