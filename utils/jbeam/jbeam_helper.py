import json
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
        self.check()
        if self.domain == "vertex":
            self.vertex_groups = self.get_vertex_groups()
            self.vertex_to_groups = self.get_vertex_group_memberships()
            self.props = self.get_node_properties()
        elif self.domain == "edge":
            self.props = self.get_beam_properties()

    def check(self):
        if not j.has_jbeam_node_id(self.obj):
            raise ValueError(f"ERROR: Required attributes \"jbeam_node_id\" and \"jbeam_node_props\" not found in mesh")
        group_map = {g.index: g.name for g in self.obj.vertex_groups if g.name.startswith("group_")}
        print(f"Vertex Groups Found: {group_map}")

    def get_vertex_groups(self):
        return {vg.index: vg.name for vg in self.obj.vertex_groups if vg.name.startswith("group_")}

    def get_vertex_group_memberships(self):
        return {
            v.index: sorted([self.vertex_groups[g.group] for g in v.groups if g.group in self.vertex_groups])
            for v in self.obj.data.vertices
        }

    def get_node_properties(self):
        return {i: j.get_node_props_str(self.obj, i) for i in range(len(self.obj.data.vertices))}

    def get_beam_properties(self):
        return {i: j.get_beam_props_str(self.obj, i) for i in range(len(self.obj.data.edges))}

    def parse_properties(self, properties_str):
        if not properties_str:
            return {}
        return {
            k.strip(): v.strip()
            for item in properties_str.strip("{}").replace('"', '').split(",")
            if (parts := item.split(":", 1)) and len(parts) == 2
            for k, v in [parts]
        }

    def structure_data(self):
        if self.domain == "vertex":
            data_dict = {
                v_idx: {
                    "group": sorted(groups),  # Ensure groups are sorted
                    **self.parse_properties(self.props.get(v_idx, "")),
                }
                for v_idx, groups in self.vertex_to_groups.items()
            }
        elif self.domain =="edge":
            data_dict = {
                v_idx: self.parse_properties(self.props.get(v_idx, ""))
                for v_idx in self.props
            }
        print("data_dict: ==== ", data_dict)

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

            # Keep "group" first, then sort everything else alphabetically
            sorted_props = OrderedDict()
            if self.domain == "vertex" and "group" in cleaned_node_info:
                sorted_props["group"] = cleaned_node_info.pop("group")

            sorted_props.update(dict(sorted(cleaned_node_info.items(), key=lambda x: x[0].lower())))

            # Convert to JSON string for stable sorting
            formatted_json = json.dumps(sorted_props, separators=(",", ":"), sort_keys=False)
            final_list[node_id] = formatted_json

        # Sort based on JSON string to ensure determinism
        sorted_items = sorted(final_list.items(), key=lambda x: x[1])

        return OrderedDict((k, json.loads(v)) for k, v in sorted_items)


class RedundancyReducerJbeamNodesGenerator:
    def __init__(self, obj, data, domain="vertex"):
        self.obj = obj
        self.data = data
        self.domain = domain
    
    def reduce_redundancy(self):
        hierarchy = []
        property_dict = defaultdict(list) # Initialize a defaultdict to keep track of nodes by each property
        
        # Iterate over the data to group nodes by their properties
        for item_idx, properties in self.data.items():
            for key, value in properties.items():
                if isinstance(value, list):
                    value = tuple(value)  # Use tuple for immutable storage in dictionary
                property_dict[(key, value)].append(item_idx)

        # Start from the bottom of the hierarchy (reverse the order of nodes)
        list_item = list(self.data.keys())
        list_item.reverse()

        # Track the current hierarchy for each property to avoid redundancy
        curr_props = defaultdict(lambda: None)  # Default value for missing properties is None

        for item_idx in list_item: # node = vertex index
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
            
            index = item_idx
            if self.domain == "vertex":
                node_id = j.get_node_id(self.obj, index) if isinstance(item_idx, int) else item_idx
                v = self.obj.data.vertices[index].co
                hierarchy.append([node_id, round(v.x, 2), round(v.y, 2), round(v.z, 2)])  # Append the node itself to the hierarchy
            elif self.domain == "edge":
                node_id1, node_id2 = j.get_beam_node_ids(self.obj, index)
                hierarchy.append([node_id1, node_id2])  # Append the beam itself to the hierarchy

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

