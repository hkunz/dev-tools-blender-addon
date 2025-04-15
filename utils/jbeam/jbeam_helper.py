import ast
import json
import re
from collections import defaultdict, OrderedDict

from dev_tools.utils.number_utils import NumberUtils # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

DEFAULT_SCOPE_MODIFIER_VALUES = {
    "frictionCoef": 1.0,
    "nodeMaterial": "|NM_METAL",
    "nodeWeight": 25,
    "collision": "true",
    "selfCollision": "false",
    "fixed": "false",
    "group": "",
    "disable": "",
    "beamPrecompression": 1,
    "beamType": "|NORMAL",
    "beamLongBound": 1,
    "beamShortBound": 1,
    "beamSpring": 10000000,
    "beamDamp": 0,
    "beamDeform": "FLT_MAX",
    "beamStrength": "FLT_MAX",
    "breakGroup": "",
    "groundModel": "asphalt"
}

class PreJbeamStructureHelper:
    def __init__(self, obj, domain="vertex"):
        self.obj = obj
        self.domain = domain

    def get_props(self):
        if not j.has_jbeam_node_id(self.obj):
            raise ValueError(f"❌ ERROR: Required attributes \"jbeam_node_id\" and \"jbeam_node_props\" not found in mesh")

        props = None
        if self.domain == "vertex":
            props = self._get_node_properties()
        elif self.domain == "edge":
            props = self._get_beam_properties()
        elif self.domain == "face":
            props = self._get_triangle_properties()
        return props

    def _get_node_properties(self):
        #return {i: json.dumps(j.get_node_props(self.obj, i)) for i in range(len(self.obj.data.vertices))}
        return {
            i: {
                instance + 1: json.dumps(j.get_node_props(self.obj, i, instance+1))
                for instance in range(j.get_total_node_instances(self.obj, i))  # Instances per vertex
            }
            for i in range(len(self.obj.data.vertices))  # Iterate through each vertex
        }

    def _get_beam_properties(self):
        #return {i: json.dumps(j.get_beam_props(self.obj, i)) for i in range(len(self.obj.data.edges))}
        return {
            i: {
                instance: json.dumps(j.get_beam_props(self.obj, i, instance+1))
                for instance in range(j.get_total_beam_instances(self.obj, i))  # Instances per edge
            } or {1:{}}  # if no data, then use default 1st instance empty props
            for i in range(len(self.obj.data.edges))  # Iterate through each edge
        }

    def _get_triangle_properties(self):
        #return {i: json.dumps(j.get_triangle_props(self.obj, i)) for i in range(len(self.obj.data.polygons))}
        return {
            i: {
                instance: json.dumps(j.get_triangle_props(self.obj, i, instance+1))
                for instance in range(j.get_total_triangle_instances(self.obj, i))  # Instances per edge
            } or {1:{}}  # if no data, then use default 1st instance empty props
            for i in range(len(self.obj.data.polygons))  # Iterate through each face
        }

    def _parse_properties(self, properties_str):
        if not properties_str:
            return {}

        try:
            properties_dict = ast.literal_eval(properties_str)
            if isinstance(properties_dict, dict):
                return {k.strip(): v for k, v in properties_dict.items()}
        except (SyntaxError, ValueError):
            pass  # Handle invalid cases gracefully

        return {}

    def structure_data(self):
        props = self.get_props()
        data_dict = {}
        for v_idx, instances in props.items():
            for instance, prop in instances.items():  # Iterate over the instances in each vertex/edge/face
                data_dict[f"{v_idx}_{instance+1}"] = self._parse_properties(prop)
        unique_props = set()  # Collect all unique properties dynamically
        for node_info in data_dict.values():
            unique_props.update(node_info.keys())

        final_list = {}
        for node_id, node_info in data_dict.items():
            cleaned_node_info = {k.strip(): v for k, v in node_info.items()}

            # Fill in missing properties with defaults
            for prop in unique_props:
                if prop not in cleaned_node_info:
                    cleaned_node_info[prop] = DEFAULT_SCOPE_MODIFIER_VALUES.get(prop, "")

            for prop, value in cleaned_node_info.items():
                if not isinstance(value, str):
                    continue
                if value.isdigit():
                    cleaned_node_info[prop] = int(value)
                elif NumberUtils.is_float(value):
                    cleaned_node_info[prop] = float(value)
                elif not value.lstrip().startswith("["):
                    cleaned_node_info[prop] = value.replace('"', '').replace("'", '') # Properties with quotes in the UI are acceptable; they will automatically be sanitized here and converted to use double quotes in the JBeam file for consistency.

            sorted_props = OrderedDict()
            for key in ["group", "deformGroup", "breakGroup"]:
                if not key in cleaned_node_info:
                    continue
                value = cleaned_node_info.pop(key) # make group properties display first in the dictionary
                # Try convert from string to list if it's a JSON string so we can sort the elements for groups
                if isinstance(value, str):
                    try:
                        cleaned_json_str = re.sub(r",\s*]", "]", value)
                        value = json.loads(cleaned_json_str.strip())  # Strip spaces and load JSON
                    except json.JSONDecodeError:
                        pass  # If not a JSON string, keep as-is
                if isinstance(value, list):
                    value = sorted(value)
                sorted_props[key] = value

            sorted_props.update(dict(sorted(cleaned_node_info.items(), key=lambda x: x[0].lower())))
            
            # Convert to JSON string for stable sorting
            formatted_json = json.dumps(sorted_props, separators=(",", ":"), sort_keys=False)
            final_list[node_id] = formatted_json

        # Sort based on JSON string to ensure determinism
        sorted_items = sorted(final_list.items(), key=lambda x: x[1])

        return OrderedDict((k, json.loads(v)) for k, v in sorted_items)


class RedundancyReducerJbeamGenerator:
    def __init__(self, obj, data, domain="vertex"):
        self.obj = obj
        self.data = data
        self.domain = domain
    
    def reduce_redundancy(self):
        # Start from the bottom of the hierarchy (reverse the order of nodes)
        hierarchy = []
        items: list[str] = list(self.data.keys())  # list of element format {index}_{instance} ex: ['0_1', '1_1', '2_1', '3_1', '4_1', '5_1', '6_1', '7_1']
        items.reverse()
        curr_props = defaultdict(lambda: None)  # Track the current hierarchy for each property to avoid redundancy

        for item_idx in items:
            properties = self.data[item_idx]

            for key, value in properties.items():
                if isinstance(value, list):
                    value = tuple(value)  # Convert list to tuple to avoid redundancy in defaultdict

                # If the property value has changed, push it up in the hierarchy
                if curr_props[key] != value:
                    if curr_props[key] is not None:
                        processed_value = list(curr_props[key]) if isinstance(curr_props[key], tuple) else curr_props[key]
                        if key == "group" and processed_value == []:
                            processed_value = ""  # Convert empty list to empty string
                        hierarchy.append({key: processed_value})
                    curr_props[key] = value

            # Split item_idx into element_index and instance
            idx_str, instance_str = item_idx.split("_")
            idx = int(idx_str)
            instance = int(instance_str)

            if self.domain == "vertex":
                node_id = j.get_node_id(self.obj, idx)  # Get the node ID based on idx
                v = self.obj.data.vertices[idx].co
                hierarchy.append([node_id, round(v.x, 2), round(v.y, 2), round(v.z, 2)])  # Append the node itself to the hierarchy
            elif self.domain == "edge":
                node_id1, node_id2 = j.get_beam_node_ids(self.obj, idx)
                hierarchy.append([node_id1, node_id2])  # Append the beam itself to the hierarchy
            elif self.domain == "face":
                node_id1, node_id2, node_id3 = j.get_triangle_node_ids(self.obj, idx)
                hierarchy.append([node_id1, node_id2, node_id3])  # Append the triangle itself to the hierarchy

        # Add the last property values
        for key, value in curr_props.items():
            if value is not None:
                processed_value = list(value) if isinstance(value, tuple) else value
                if key == "group" and processed_value == []:
                    processed_value = ""  # Convert empty list to empty string
                hierarchy.append({key: processed_value})

        hierarchy.reverse()
        used_properties = sorted(set(key for node, properties in self.data.items() for key in properties))

        for key in used_properties:
            hierarchy.append({key: DEFAULT_SCOPE_MODIFIER_VALUES.get(key, '')})

        return hierarchy

class JbeamFileHelper:
    
    RE_LINE_COMMENT = re.compile(r'(?<!:)\s*//.*$')
    RE_DOUBLE_COMMAS = re.compile(r'(,\s*){2,}')
    RE_QUOTED_DICT = re.compile(r'"\s*\{')
    RE_ARRAY_DICT = re.compile(r'\]\s*\{')
    RE_CURLY_DICT = re.compile(r'\}\s*\{')
    RE_MISSING_COMMA_BEFORE_KEY = re.compile(r'(?<=[}\]0-9"e])\s*(?="[^"]+"\s*:)')
    RE_QUOTED_STRING_NUMBER = re.compile(r'(\[\s*"[^"]*")(?=\s*-?\d)')
    RE_SPACE_SEPARATED_NUMBERS_1 = re.compile(r'(-?\d+(?:\.\d+)?)(\s+)(?=-?\d)')
    RE_SPACE_SEPARATED_NUMBERS_2 = re.compile(r'(-?\d+(?:\.\d+)?)(?=\s+-?\d)')
    RE_FLOAT_DICT = re.compile(r'(\d+\.\d+)\s*(\{)')
    RE_KEY_DICT = re.compile(r'(".*?")\s*(?=[\{\[])')
    RE_NUMBER_STRING = re.compile(r'(-?\d+(?:\.\d+)?)(\s+)(")')
    RE_NUMBER_STRING_NO_SPACE = re.compile(r'(\d(?:\.\d+)?)(?="\w)')

    @staticmethod
    def attempt_fix_jbeam_commas(content: str, is_jbeam=True) -> str:
        print("🩹 Fixing syntax errors in content...")
        lines = JbeamFileHelper.remove_block_and_line_comments(content)
        fixed_lines = []

        # Precompute next significant line for each line
        next_lines = [''] * len(lines)
        for i in range(len(lines) - 1):
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line:
                    next_lines[i] = next_line
                    break

        for i, line in enumerate(lines):
            s = line.rstrip()
            while s.lstrip().startswith(","):
                s = s.lstrip().lstrip(",")

            s = JbeamFileHelper.RE_LINE_COMMENT.sub('', s)
            s = JbeamFileHelper.RE_DOUBLE_COMMAS.sub(',', s)
            s = s.rstrip()

            if not s.strip():
                continue

            # Check if this line should have a comma
            if not s.endswith((',', '{', '[', ':')):
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
                if next_line and not next_line.startswith(('}', ']')):
                    s += ','

            # Remove comma if line ends with ',' but next significant line is a closing bracket
            next_line = next_lines[i]
            if s.endswith(',') and next_line.startswith(('}', ']')):
                s = s.rstrip(',')

            if is_jbeam:
                s = JbeamFileHelper.RE_QUOTED_DICT.sub('",{', s)
                s = JbeamFileHelper.RE_ARRAY_DICT.sub('],{', s)
                s = JbeamFileHelper.RE_CURLY_DICT.sub('}, {', s)
                s = JbeamFileHelper.RE_MISSING_COMMA_BEFORE_KEY.sub(', ', s)
                s = JbeamFileHelper.RE_QUOTED_STRING_NUMBER.sub(r'\1,', s)
                s = JbeamFileHelper.RE_SPACE_SEPARATED_NUMBERS_1.sub(r'\1, ', s)
                s = JbeamFileHelper.RE_SPACE_SEPARATED_NUMBERS_2.sub(r'\1, ', s)
                s = JbeamFileHelper.RE_FLOAT_DICT.sub(r'\1,\2', s)
                s = JbeamFileHelper.RE_KEY_DICT.sub(r'\1, ', s)
                s = JbeamFileHelper.RE_NUMBER_STRING.sub(r'\1, \3', s)
                s = JbeamFileHelper.RE_NUMBER_STRING_NO_SPACE.sub(r'\1,', s)

            fixed_lines.append(s)

        return '\n'.join(fixed_lines)

    @staticmethod
    def extract_json_error_snippet(e, raw_content):
        error_message = str(e)
        if 'Expecting' in error_message:
            parts = error_message.split('char')
            char_position = parts[1].strip().split()[0]  # Get the first part before any non-numeric characters
            char_position = ''.join(filter(str.isdigit, char_position))  # Remove non-numeric characters (like ')') from char_position
            try:
                char_position = int(char_position)  # Convert char_position to an integer
            except ValueError:
                print("❌ Failed to extract valid character position.")
                return

            snippet_start = max(0, char_position - 40)  # 40 characters before the error
            snippet_end = min(len(raw_content), char_position + 40)  # 40 characters after
            error_text = raw_content[snippet_start:snippet_end]
            print(f"Error position: {char_position}")
            return error_text
        return
    
    @staticmethod
    def remove_block_and_line_comments(content: str) -> list[str]:
        lines = content.splitlines()
        cleaned_lines = []
        in_block_comment = False

        for line in lines:
            if not in_block_comment:
                if '/*' in line:
                    before_comment = line.split('/*', 1)[0].rstrip()
                    if before_comment:
                        cleaned_lines.append(before_comment)
                    in_block_comment = True
                    continue
                stripped = line.strip()
                if not stripped or stripped.startswith('//'):
                    continue
                cleaned_lines.append(line)
            else:
                if '*/' in line:
                    after_comment = line.split('*/', 1)[1].strip()
                    in_block_comment = False
                    if after_comment:
                        cleaned_lines.append(after_comment)
                # else: still inside a block comment, skip
        return cleaned_lines
