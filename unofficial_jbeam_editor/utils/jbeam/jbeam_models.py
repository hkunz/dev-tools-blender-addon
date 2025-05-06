from typing import Any, Union, TypedDict
from pathlib import Path

JbeamPartName = str
JbeamPartSectionName = str  # section names include: information, slotType, sounds, flexbodies, nodes, beams, triangles, quads, etc
JbeamPartData = dict[JbeamPartSectionName, Any]
JbeamJson = dict[JbeamPartName, JbeamPartData]

JbeamSlotType = str
JbeamPartID = str  # JbeamSlotType + ":" + JbeamPartName
PcJbeamParts = dict[JbeamSlotType, JbeamPartName]

class PcJson(TypedDict):
    format: int
    model: str
    parts: PcJbeamParts

NodeID = str
ElementID = str  # can be NodeID or beam id (i.e. [node_1|node_2]) or triangle id (i.e. [node_1|node_2|node_3])
ScopeModifierName = str
ScopeModifierValue = Union[str, int, float, bool, list]
JbeamElementProps = dict[ScopeModifierName, ScopeModifierValue]  # i.e. {"frictionCoef":"1.2","nodeMaterial":"|NM_RUBBER","nodeWeight":"1","collision":"true","selfCollision":"true","group":"mattress"}


class JBeamElement:
    """Base class for all JBeam elements (Node, Beam, Triangle)."""
    def __init__(self, instance, element_id, index, props=None):
        self.instance: int = instance  # you can have multiple instances of a beam or a triangle in jbeam
        self.id: ElementID  = element_id
        self.index: int = index  # vertex, edge, or face index
        self.props: JbeamElementProps = props if props is not None else {}
        self.source_jbeam = ""

    def __repr__(self):
        return f"{self.__class__.__name__}(instance={self.instance}, id={self.id}, index={self.index}, props={self.props}, source={self.source_jbeam})"

class Node(JBeamElement):
    def __init__(self, instance, node_id, index, position, props=None):
        super().__init__(instance, node_id, index, props)
        self.position = position

    def get_fixed(self):
        return self.props.get("fixed", False)

    def __repr__(self):
        return f"Node(instance={self.instance}, id={self.id}, index={self.index}, pos={self.position}, props={self.props}, source={self.source_jbeam})"

class Beam(JBeamElement):
    def __init__(self, instance, beam_id, node_id1, node_id2, index, props=None):
        super().__init__(instance, beam_id, index, props)
        self.node_id1: NodeID = node_id1
        self.node_id2: NodeID = node_id2

    def __repr__(self):
        return f"Beam(instance={self.instance}, id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, index={self.index}, props={self.props}, source={self.source_jbeam})"

class Triangle(JBeamElement):
    def __init__(self, instance, triangle_id, node_id1, node_id2, node_id3, index, props=None):
        super().__init__(instance, triangle_id, index, props)
        self.node_id1: NodeID = node_id1
        self.node_id2: NodeID = node_id2
        self.node_id3: NodeID = node_id3

    def __repr__(self):
        return f"Triangle(id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, node_id3={self.node_id3}, index={self.index}, props={self.props}, source={self.source_jbeam})"

JsonJbeamElement = list[Any]  # node i.e. ["n",  0, 0, 0], beam i.e. ["n1", "n2"], triangle i.e. ["n1", "n2", "n3"], or quad i.e. ["n1", "n2", "n3", "n4"]

class JbeamPart:
    def __init__(self):
        self.part_name: JbeamPartName = ""
        self.part_data: JbeamPartData = {}
        self.slots: list[JbeamSlotType] = []
        self.slot_type: JbeamSlotType = ""
        self.refnodes: dict[str, str] = {}
        self.nodes: dict[NodeID, Node] = {}
        self.nodes_list: list[Node] = []
        self.beams_list: list[Beam] = []
        self.triangles_list: list[Triangle] = []
        self.json_beams: list[Union[JbeamElementProps, JsonJbeamElement]] = []
        self.json_triangles: list[Union[JbeamElementProps, JsonJbeamElement]] = []
        self.json_quads: list[Union[JbeamElementProps, JsonJbeamElement]] = []

    @staticmethod
    def generate_id(slot_type: JbeamSlotType, part_name: JbeamPartName) -> JbeamPartID:
        return f"{slot_type}:{part_name}"

    @property
    def id(self) -> JbeamPartID:
        return JbeamPart.generate_id(self.slot_type, self.part_name)

    def __repr__(self):
        return f"JbeamPart(part_name={self.part_name}, slot_type={self.slot_type}, refnodes={self.refnodes})"

class JbeamLoadItem:
    def __init__(self, file_path: str, part_name: str="", slot_type: str=""):
        self.part_name = part_name
        self.slot_type = slot_type
        self.file_path = file_path

    @property
    def is_part_set(self) -> bool:
        return bool(self.part_name)

    @property
    def part_id(self) -> JbeamPartID:
        return JbeamPart.generate_id(self.slot_type, self.part_name)

    def __repr__(self):
        return f"{self.__class__.__name__}(part_name={self.part_name}, slot_type={self.slot_type}, file_path= 📄 {self.file_path})"
