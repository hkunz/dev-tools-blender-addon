import bpy
import json
import difflib
import unittest

import pprint
from dev_tools.utils.jbeam.jbeam_helper import PreJbeamStructureHelper, RedundancyReducerJbeamNodesGenerator # type: ignore

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

        vertices = [(x, 0.25 * x, 0.5 * x) for x in range(20)]
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
            0: "b3",
            1: "b4",
            2: "b12",
            3: "b15",
            4: "b13",
            5: "b9",
            6: "b5",
            7: "b14",
            8: "b8",
            9: "b1",
            10: "b19",
            11: "b17",
            12: "b18",
            13: "b16",
            14: "b6",
            15: "b2",
            16: "b11",
            17: "ref",
            18: "b10",
            19: "b7",
        }

        node_groups = {
            0: ["group_bouncer_spring", "group_bouncer_top"],
            1: ["group_bouncer_spring", "group_bouncer_top"],
            2: ["group_bouncer_base"],
            3: ["group_bouncer_base"],
            4: ["group_bouncer_base"],
            5: ["group_bouncer_base", "group_bouncer_spring"],
            6: ["group_bouncer_base", "group_bouncer_spring"],
            7: ["group_bouncer_base"],
            8: ["group_bouncer_base", "group_bouncer_spring"],
            9: ["group_bouncer_base", "group_bouncer_spring"],
            10: ["group_bouncer_top"],
            11: ["group_bouncer_top"],
            12: ["group_bouncer_top"],
            13: ["group_bouncer_top"],
            14: ["group_bouncer_spring", "group_bouncer_top"],
            15: ["group_bouncer_spring", "group_bouncer_top"],
            16: ["group_bouncer_spring"],
            17: [],
            18: [],
            19: [],
        }

        node_props = {
            0: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            1: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            2: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            3: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            4: {"collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            5: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            6: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            7: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            8: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            9: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            10: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            11: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "6.3", "selfCollision": "false"},
            12: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            13: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            14: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            15: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "2.3", "selfCollision": "false"},
            16: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            17: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            18: {"collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            19: {"collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
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
        print()
        print(f"===> Start Test {self} ==================================")
        print()
        test_obj = JbeamTestObject() # bpy.context.object
        test_obj.create_vertex_groups()
        self.obj = test_obj.get_obj()

    def test_pre_jbeam_structure(self):

        jbeam = PreJbeamStructureHelper(self.obj)
        data_actual = jbeam.structure_vertex_data()
        print()
        print("🔸 Actual Output:\n")
        for key, value in data_actual.items():
            print(f"{key}: {value}")

        data_expected = {
            5: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            6: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "1.3", "selfCollision": "true"},
            8: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            9: {"group": ["group_bouncer_base", "group_bouncer_spring"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "true"},
            7: {"group": ["group_bouncer_base"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            4: {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            2: {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            3: {"group": ["group_bouncer_base"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            15: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "2.3", "selfCollision": "false"},
            14: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            1: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "2.3", "selfCollision": "false"},
            0: {"group": ["group_bouncer_spring", "group_bouncer_top"], "collision": "true", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_RUBBER", "nodeWeight": "3.5", "selfCollision": "false"},
            16: {"group": ["group_bouncer_spring"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            10: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "3.5", "selfCollision": "false"},
            12: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            13: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            11: {"group": ["group_bouncer_top"], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "6.3", "selfCollision": "false"},
            19: {"group": [], "collision": "false", "fixed": "false", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            17: {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
            18: {"group": [], "collision": "false", "fixed": "true", "frictionCoef": "1.2", "nodeMaterial": "|NM_PLASTIC", "nodeWeight": "10", "selfCollision": "true"},
        }
        print()
        print("🔹 Expected Output:\n")
        for key, value in data_expected.items():
            print(f"{key}: {value}")
        print()

        actual_str = json.dumps(data_actual, indent=4, sort_keys=False).splitlines()
        expected_str = json.dumps(data_expected, indent=4, sort_keys=False).splitlines()

        diff = difflib.unified_diff(expected_str, actual_str, fromfile="Expected", tofile="Actual", lineterm="")
        diff_list = list(diff)
        
        if diff_list:
            print("❌ TEST FAILED: test_pre_jbeam_structure\n")
            print("🔍 Differences:")
            print("\n".join(diff_list))
            print()

        self.assertEqual(data_expected, data_actual, "Data does not match expected structure")
        self.assertFalse(diff_list, "Data does not match expected structure or order")
        
        print("✅ TEST PASSED: test_pre_jbeam_structure")

    def test_jbeam_structure(self):
    
        jbeam = PreJbeamStructureHelper(self.obj)
        data = jbeam.structure_vertex_data()
        reducer = RedundancyReducerJbeamNodesGenerator(bpy.context.object, data)
        data_actual = reducer.reduce_redundancy()

        data_expected = [
            {'selfCollision': 'true'},
            {'nodeWeight': '1.3'},
            {'nodeMaterial': '|NM_RUBBER'},
            {'frictionCoef': '1.2'},
            {'fixed': 'false'},
            {'collision': 'false'},
            {'group': ['group_bouncer_base', 'group_bouncer_spring']},
            ['b9', 5.0, 1.25, 2.5],
            ['b5', 6.0, 1.5, 3.0],
            {'nodeWeight': '2.3'},
            {'fixed': 'true'},
            ['b8', 8.0, 2.0, 4.0],
            ['b1', 9.0, 2.25, 4.5],
            {'selfCollision': 'false'},
            {'nodeWeight': '3.5'},
            {'nodeMaterial': '|NM_PLASTIC'},
            {'fixed': 'false'},
            {'group': ['group_bouncer_base']},
            ['b14', 7.0, 1.75, 3.5],
            {'collision': 'true'},
            ['b13', 4.0, 1.0, 2.0],
            {'nodeMaterial': '|NM_RUBBER'},
            ['b12', 2.0, 0.5, 1.0],
            ['b15', 3.0, 0.75, 1.5],
            {'nodeWeight': '2.3'},
            {'nodeMaterial': '|NM_PLASTIC'},
            {'collision': 'false'},
            {'group': ['group_bouncer_spring', 'group_bouncer_top']},
            ['b2', 15.0, 3.75, 7.5],
            {'nodeMaterial': '|NM_RUBBER'},
            ['b6', 14.0, 3.5, 7.0],
            {'fixed': 'true'},
            ['b4', 1.0, 0.25, 0.5],
            {'nodeWeight': '3.5'},
            {'fixed': 'false'},
            {'collision': 'true'},
            ['b3', 0.0, 0.0, 0.0],
            {'nodeMaterial': '|NM_PLASTIC'},
            {'collision': 'false'},
            {'group': ['group_bouncer_spring']},
            ['b11', 16.0, 4.0, 8.0],
            {'group': ['group_bouncer_top']},
            ['b19', 10.0, 2.5, 5.0],
            {'selfCollision': 'true'},
            {'nodeWeight': '10'},
            {'fixed': 'true'},
            ['b18', 12.0, 3.0, 6.0],
            ['b16', 13.0, 3.25, 6.5],
            {'selfCollision': 'false'},
            {'nodeWeight': '6.3'},
            ['b17', 11.0, 2.75, 5.5],
            {'selfCollision': 'true'},
            {'nodeWeight': '10'},
            {'fixed': 'false'},
            {'group': ''},
            ['b7', 19.0, 4.75, 9.5],
            {'fixed': 'true'},
            ['ref', 17.0, 4.25, 8.5],
            ['b10', 18.0, 4.5, 9.0]
        ]

        pp = pprint.PrettyPrinter(indent=4)
        print()
        print("🔸 Actual Output:\n")
        pp.pprint(data_actual)
        print()
        print("🔹 Expected Output:\n")
        pp.pprint(data_expected)
        print()

        expected_lines = [str(item) for item in data_expected]
        actual_lines = [str(item) for item in data_actual]
        diff = difflib.unified_diff(expected_lines, actual_lines, lineterm='')
        diff_list = list(diff)

        if diff_list:
            print("❌ TEST FAILED: test_jbeam_structure\n")
            print("🔍 Differences:")
            print("\n".join(diff_list))
            print()

        self.assertEqual(data_expected, data_actual, "Data does not match expected jbeam nodes list")
        self.assertFalse(list(diff), "Data does not match expected JBeam nodes list")

        print("✅ TEST PASSED: test_jbeam_structure")

    def tearDown(self):
        bpy.data.objects.remove(self.obj)

def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestJBeamHelper)
    unittest.TextTestRunner().run(suite)

run_tests()
