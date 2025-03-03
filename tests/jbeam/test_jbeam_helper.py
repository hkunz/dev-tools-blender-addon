import bpy
import json
import difflib
import unittest

from dev_tools.utils.jbeam_helper import PreJbeamStructureHelper, RedundancyReducerJbeamNodesGenerator # type: ignore

class JbeamTestObject:
    def __init__(self, name="jbeam_test_object"):
        self.name = name
        self.obj = self.create_test_line_object()
        self.set_jbeam_attributes()

    def get_obj(self):
        return self.obj

    def create_test_line_object(self):

        mesh = bpy.data.meshes.new(f"{self.name}_mesh")
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        vertices = [(x, 0, 0) for x in range(20)] # 20 vertices sample object
        edges = [(i, i+1) for i in range(19)]
        
        faces = []
        mesh.from_pydata(vertices, edges, faces)
        mesh.update()
        
        return obj

    def set_jbeam_attributes(self):

        self.obj.data.attributes.new("jbeam_node_id", 'STRING', 'POINT')
        self.obj.data.attributes.new("jbeam_node_group", 'STRING', 'POINT')
        self.obj.data.attributes.new("jbeam_node_props", 'STRING', 'POINT')

        node_ids = {
            5: "b9", 6: "b5", 8: "b8", 9: "b1", 15: "b2", 14: "b6",
            0: "b3", 1: "b4", 7: "b14", 4: "b13", 2: "b12", 3: "b15",
            16: "b11", 10: "b19", 11: "b17", 12: "b18", 13: "b16", 19: "b7",
            17: "ref", 18: "b10"
        }

        node_groups = {
            5: ["group_bouncer_base", "group_bouncer_spring"],
            6: ["group_bouncer_base", "group_bouncer_spring"],
            8: ["group_bouncer_base", "group_bouncer_spring"],
            9: ["group_bouncer_base", "group_bouncer_spring"],
            15: ["group_bouncer_spring", "group_bouncer_top"],
            14: ["group_bouncer_spring", "group_bouncer_top"],
            0: ["group_bouncer_spring", "group_bouncer_top"],
            1: ["group_bouncer_spring", "group_bouncer_top"],
            7: ["group_bouncer_base"],
            4: ["group_bouncer_base"],
            2: ["group_bouncer_base"],
            3: ["group_bouncer_base"],
            16: ["group_bouncer_spring"],
            10: ["group_bouncer_top"],
            11: ["group_bouncer_top"],
            12: ["group_bouncer_top"],
            13: ["group_bouncer_top"],
            19: [],
            17: [],
            18: []
        }

        node_props = {
            5: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            6: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            8: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            9: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            15: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "2.3", "selfCollision": "false"},
            14: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            0: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            1: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            7: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            4: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            2: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            3: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            16: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            10: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            11: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "6.3", "selfCollision": "false"},
            12: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            13: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            19: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            17: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            18: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"}
        }

        for vertex_idx in range(20):
            self.obj.data.attributes['jbeam_node_id'].data[vertex_idx].value = node_ids.get(vertex_idx, "").encode('utf-8')
            self.obj.data.attributes['jbeam_node_group'].data[vertex_idx].value = ",".join(node_groups.get(vertex_idx, [])).encode('utf-8')
            self.obj.data.attributes['jbeam_node_props'].data[vertex_idx].value = json.dumps(node_props.get(vertex_idx, {})).encode('utf-8')

    def create_vertex_groups(self):

        vertex_groups_data = {
            'group_bouncer_base': [2, 3, 4, 5, 6, 7, 8, 9],
            'group_bouncer_spring': [0, 1, 5, 6, 8, 9, 14, 15, 16],
            'group_bouncer_top': [0, 1, 10, 11, 12, 13, 14, 15]
        }

        for group_name, vertex_indices in vertex_groups_data.items():
            group = self.obj.vertex_groups.new(name=group_name)

            for vertex_index in vertex_indices:
                group.add([vertex_index], 1.0, 'REPLACE')


class TestJBeamHelper(unittest.TestCase):
    
    def setUp(self):

        test_obj = JbeamTestObject() # bpy.context.object
        test_obj.create_vertex_groups()
        self.obj = test_obj.get_obj()
        self.data = None

    def test_pre_jbeam_structure(self):

        jbeam = PreJbeamStructureHelper(self.obj)
        data = jbeam.structure_vertex_data()
        for key, value in data.items():
            print(f"{key}: {value}")
        self.data = data


        # Sample Output can be node_id or index, it is currently index:
        '''
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
        '''

        assert_data = {
            5: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            6: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            8: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            9: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            15: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "2.3", "selfCollision": "false"},
            14: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            0: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            1: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            7: {"group": ["group_bouncer_base"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            4: {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            2: {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            3: {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            16: {"group": ["group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            10: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            12: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            13: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            11: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "6.3", "selfCollision": "false"},
            19: {"group": [], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            17: {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            18: {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"}

        }

        d1_str = json.dumps(assert_data, indent=4)  # No sort_keys=True
        d2_str = json.dumps(data, indent=4)

        diff = difflib.unified_diff(
            d1_str.splitlines(),
            d2_str.splitlines(),
            fromfile="Expected",
            tofile="Actual",
            lineterm=""
        )
        
        print("\n".join(diff))
        diff_list = list(difflib.unified_diff(d1_str, d2_str, fromfile="Expected", tofile="Actual", lineterm=""))

        self.assertEqual(assert_data, data, "Data does not match expected structure")
        self.assertFalse(diff_list, "Data does not match expected structure or order")
        
        
        print("test_pre_jbeam_structure: Test Passed!")

    def test_jbeam_structure(self):
        jbeam = PreJbeamStructureHelper(self.obj)
        data = jbeam.structure_vertex_data()
        print("\n\n")
        for key, value in data.items():
            print(f"{key}: {value}")
        self.data = data
        print("\n")

        reducer = RedundancyReducerJbeamNodesGenerator(bpy.context.object, self.data)
        reduced_hierarchy = reducer.reduce_redundancy()

        for item in reduced_hierarchy:
            print(item)

        print("test_jbeam_structure: Test Passed!")

    def tearDown(self):
        bpy.data.objects.remove(self.obj)

def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestJBeamHelper)
    unittest.TextTestRunner().run(suite)

run_tests()
