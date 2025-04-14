from typing import Any

JbeamPartName = str
JbeamJsonSectionName = str  # section names include: information, slotType, sounds, flexbodies, nodes, beams, triangles, quads, etc
JbeamJsonSection = dict[JbeamJsonSectionName, Any]
JbeamJson = dict[JbeamPartName, JbeamJsonSection]


class JbeamLoadItem:
    def __init__(self, file_path: str, part_name: str="", slot_type: str=""):
        self.part_name = part_name
        self.slot_type = slot_type
        self.file_path = file_path

    def __repr__(self):
        return f"{self.__class__.__name__}(part_name={self.part_name}, slot_type={self.slot_type}, file_path={self.file_path})"


NodeID = str
ElementID = str  # can be NodeID or beam id (i.e. [node_1|node_2]) or triangle id (i.e. [node_1|node_2|node_3])
ScopeModifier = ScopeModifierValue = str
Props = dict[ScopeModifier, ScopeModifierValue]  # i.e. {"frictionCoef":"1.2","nodeMaterial":"|NM_RUBBER","nodeWeight":"1","collision":"true","selfCollision":"true","group":"mattress"}


class JBeamElement:
    """Base class for all JBeam elements (Node, Beam, Triangle)."""
    def __init__(self, instance, element_id, index, props=None):
        self.instance: int = instance  # you can have multiple instances of a beam or a triangle in jbeam
        self.id: ElementID  = element_id
        self.index: int = index  # vertex, edge, or face index
        self.props: Props = props if props is not None else {}

    def __repr__(self):
        return f"{self.__class__.__name__}(instance={self.instance}, id={self.id}, index={self.index}, props={self.props})"

class Node(JBeamElement):
    def __init__(self, instance, node_id, index, position, props=None):
        super().__init__(instance, node_id, index, props)
        self.position = position

    def get_fixed(self):
        return self.props.get("fixed", False)

    def __repr__(self):
        return f"Node(instance={self.instance}, id={self.id}, index={self.index}, pos={self.position}, props={self.props})"

class Beam(JBeamElement):
    def __init__(self, instance, beam_id, node_id1, node_id2, index, props=None):
        super().__init__(instance, beam_id, index, props)
        self.node_id1: str = node_id1
        self.node_id2: str = node_id2

    def __repr__(self):
        return f"Beam(instance={self.instance}, id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, index={self.index}, props={self.props})"

class Triangle(JBeamElement):
    def __init__(self, instance, triangle_id, node_id1, node_id2, node_id3, index, props=None):
        super().__init__(instance, triangle_id, index, props)
        self.node_id1: str = node_id1
        self.node_id2: str = node_id2
        self.node_id3: str = node_id3

    def __repr__(self):
        return f"Triangle(id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, node_id3={self.node_id3}, index={self.index}, props={self.props})"

class JbeamPart:
    def __init__(self):
        self.part_name: str = None
        self.part_data = None
        self.slot_type: str = None
        self.refnodes: dict[str, str] = {}
        self.nodes: dict[NodeID, Node] = {}
        self.nodes_list: list[Node] = []
        self.beams_list: list[Beam] = []
        self.triangles_list: list[Triangle] = []
        self.json_beams = None
        self.json_triangles = None
        self.json_quads = None