import io

class JbeamExportProcessor:
    def __init__(self, json_data):
        self.json_data = json_data
        self.input_stream = None
        self.output_stream = io.StringIO()
        self.modified_data = json_data

    def remove_node_contents(self, key):
        self.output_stream = io.StringIO()
        self.input_stream = io.StringIO(self.modified_data)

        depth = 0
        skipping = False
        key_buffer = []
        inside_string = False

        while True:
            ch = self.input_stream.read(1)
            if not ch:
                break

            if ch == '"':
                inside_string = not inside_string

            if inside_string and depth == 0:
                key_buffer.append(ch)
                if len(key_buffer) > 255:
                    key_buffer = key_buffer[:255]

            if not inside_string and key_buffer:
                key_str = ''.join(key_buffer)
                key_buffer = []
                if key_str[1:] == key:
                    skipping = True
                    self.output_stream.write('"' + ':' + ' ')

            if ch == '[' and not inside_string:
                if skipping:
                    depth += 1
                    if depth == 1:
                        self.output_stream.write('[')
                    continue

            if ch == ']' and not inside_string:
                if depth > 0:
                    depth -= 1
                    if depth == 0:
                        skipping = False

            if not skipping:
                self.output_stream.write(ch)

        return self.output_stream.getvalue()


    def get_key_indent(self, key):
        current_pos = self.input_stream.tell()
        self.input_stream.seek(0)

        for line in self.input_stream:
            stripped_line = line.lstrip()
            if stripped_line.startswith(f'"{key}"'):
                indent = len(line) - len(stripped_line)
                self.input_stream.seek(current_pos)
                return indent

        self.input_stream.seek(current_pos) 
        return -1

    def insert_node_contents(self, key, new_contents):
        self.remove_node_contents(key)
        spaces = self.get_key_indent(key)
        indent = " " * spaces
        result = self.get_result()
        if spaces < 0:
            return result
        indented_contents = "\n".join(indent + line for line in new_contents.splitlines())
        result = result.replace(f'"{key}": []', f'"{key}": [\n    {indented_contents}\n{indent}]')
        self.modified_data = result
        return result

    def get_result(self):
        return self.output_stream.getvalue()

# Test

json_data = """
{
    "manual_datfa_file": "you need to manually copy these nodes to the .jbeam file",
    "partname": {
        "refNodes": [
            ["ref:", "back:", "left:", "up:", "leftCorner:", "rightCorner:"],
            ["ref", "", "", "", "", ""]
        ],
        "nodes": [
            ["id", "posX", "posY", "posZ"],
            {"asdf":"asdf"},
            {"asdf":"asdf2"},
            ["ref", 0, 0, 0],
            ["b7", -1.0, -1.0, 1.0],
            ["b8", -1.0, -1.0, -1.0],
            {"asdf":"asdf"},
            {"asdf":"asdf3"}
        ]
    }
}
"""
#processor = JbeamExportProcessor(json_data)
#result = processor.remove_node_contents("nodes")
#print("Processed JSON:\n", result)