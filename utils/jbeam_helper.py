import bpy
import json
from collections import OrderedDict

DEFAULT_SCOPE_MODIFIER_VALUES = {
    "frictionCoef": "1.0",
    "nodeMaterial": "|NM_METAL",
    "nodeWeight": "25",
    "collision": "true",
    "selfCollision": "false",
    "fixed": "false",
    "group": "",
    "disable": "",
    "beamPrecompression": "1",
    "beamType": "|NORMAL",
    "beamLongBound": "1",
    "beamShortBound": "1",
    "beamSpring": "10000000",
    "beamDamp": "0",
    "beamDeform": "FLT_MAX",
    "beamStrength": "FLT_MAX",
    "breakGroup": "",
    "groundModel": "asphalt"
}

class PreJbeamStructureHelper:
    def __init__(self, obj):
        self.obj = obj
        self.vertex_groups = self.get_vertex_groups()
        self.vertex_to_groups = self.get_vertex_group_memberships()
        self.node_props = self.get_node_properties()

    def get_vertex_groups(self):
        return {vg.index: vg.name for vg in self.obj.vertex_groups if vg.name.startswith("group_")}

    def get_vertex_group_memberships(self):
        return {
            v.index: sorted([self.vertex_groups[g.group] for g in v.groups if g.group in self.vertex_groups])
            for v in self.obj.data.vertices
        }

    def get_node_properties(self):
        attr = self.obj.data.attributes.get("jbeam_node_props")
        if attr:
            return {i: attr.data[i].value.decode("utf-8") for i in range(len(attr.data))}
        return {}

    def parse_properties(self, properties_str):
        if not properties_str:
            return {}
        return {
            k.strip(): v.strip()
            for item in properties_str.strip("{}").replace('"', '').split(",")
            if (parts := item.split(":", 1)) and len(parts) == 2
            for k, v in [parts]
        }

    def structure_vertex_data(self):
        node_data_dict = {
            #self.obj.data.attributes["jbeam_node_id"].data[v_idx].value.decode("utf-8"): { # use this if we want node_id as key in final dictionary
            v_idx: {
                "group": groups,
                **self.parse_properties(self.node_props.get(v_idx, "")),
            }
            for v_idx, groups in self.vertex_to_groups.items()
        }

        sorted_nodes = sorted(node_data_dict.items(), key=lambda x: (not x[1]["group"], x[0])) # x[0].lower()))

        unique_props = set()  # Collect all unique properties dynamically

        # First pass: Find all unique properties
        for node_info in node_data_dict.values():
            unique_props.update(node_info.keys())

        # Second pass: Ensure each node only has missing properties filled
        final_node_list = {}
        for node_id, node_info in sorted_nodes:
            cleaned_node_info = {k.strip(): v for k, v in node_info.items()}

            # Add only missing properties
            for prop in unique_props:
                if prop not in cleaned_node_info:
                    cleaned_node_info[prop] = DEFAULT_SCOPE_MODIFIER_VALUES.get(prop, "")

            # Ensure group is first, rest sorted alphabetically
            sorted_props = {"group": cleaned_node_info.pop("group")}
            sorted_props.update(dict(sorted(cleaned_node_info.items(), key=lambda x: x[0].lower())))

            formatted_props = ", ".join(
                f'"{k}": {json.dumps(v) if isinstance(v, (list, bool, int, float)) else json.dumps(str(v).strip())}'
                for k, v in sorted_props.items()
            )

            final_node_list[node_id] = f"{{{formatted_props}}}"

        # Sort first by 'group' length, then by group name, and then by all other properties' order
        data_sorted = dict(sorted(final_node_list.items(), key=lambda x: (
            -len(json.loads(x[1])['group']),
            json.loads(x[1])['group'],
            tuple(json.loads(x[1]).get(prop, "") for prop in unique_props)  # Sub-sort by the values of all properties in order
        )))

        data_sorted = {
            k: json.loads(v) for k, v in data_sorted.items()
        }

        #for key, value in data_sorted.items():
        #    print(f"{key}: {value}")
        #print("\n🔹 Unique Properties Used:\n", sorted(unique_props))

        return data_sorted

import bpy
from collections import defaultdict

class RedundancyReducerJbeamNodesGenerator:
    def __init__(self, obj, data):
        self.obj = obj
        self.data = data
    
    def reduce_redundancy(self):
        hierarchy = []
        
        # Initialize a defaultdict to keep track of nodes by each property
        property_dict = defaultdict(list)
        
        # Iterate over the data to group nodes by their properties
        for node, properties in self.data.items():
            for key, value in properties.items():
                if isinstance(value, list):
                    value = tuple(value)  # Use tuple for immutable storage in dictionary
                property_dict[(key, value)].append(node)

        # Start from the bottom of the hierarchy (reverse the order of nodes)
        nodes = list(self.data.keys())
        nodes.reverse()

        # Track the current hierarchy for each property to avoid redundancy
        current_properties = defaultdict(lambda: None)  # Default value for missing properties is None

        for node in nodes:
            properties = self.data[node]

            for key, value in properties.items():
                if isinstance(value, list):
                    value = tuple(value)  # Convert list to tuple to avoid redundancy in defaultdict
                    
                # If the property value has changed, push it up in the hierarchy
                if current_properties[key] != value:
                    if current_properties[key] is not None:
                        hierarchy.append({key: current_properties[key]})
                    current_properties[key] = value
            
            node_id = self.obj.data.attributes['jbeam_node_id'].data[node].value.decode("utf-8") if isinstance(node, int) else node
            hierarchy.append([node_id]) # Append the node itself to the hierarchy

        # Add the last property values
        for key, value in current_properties.items():
            if value is not None:
                hierarchy.append({key: value})

        hierarchy.reverse()  # Reverse to maintain the correct order
        
        return hierarchy
