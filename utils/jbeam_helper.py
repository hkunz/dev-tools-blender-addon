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
            #self.obj.data.attributes["jbeam_node_id"].data[v_idx].value.decode("utf-8"): {
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

# Usage
#jbeam = PreJbeamStructureHelper(bpy.context.object)
#data = jbeam.structure_vertex_data()
#print("\n\n")
#for key, value in data.items():
#    print(f"\"{key}\": {value}")

# Sample Output:

data = {
    "b5": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
    "b9": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
    "b1": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
    "b8": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
    "b2": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "2.3", "selfCollision": "false"},
    "b6": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
    "b4": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
    "b3": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
    "b14": {"group": ["group_bouncer_base"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "b13": {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "b12": {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
    "b15": {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
    "b11": {"group": ["group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "b19": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "b17": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "6.3", "selfCollision": "false"},
    "b16": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "b18": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "b7": {"group": [], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "b10": {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "ref": {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
}

data = {
    "5": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
    "6": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
    "8": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
    "9": {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
    "15": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "2.3", "selfCollision": "false"},
    "14": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
    "0": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
    "1": {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
    "7": {"group": ["group_bouncer_base"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "4": {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "2": {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
    "3": {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
    "16": {"group": ["group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "10": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
    "11": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "6.3", "selfCollision": "false"},
    "12": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "13": {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "19": {"group": [], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "17": {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
    "18": {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"}
}