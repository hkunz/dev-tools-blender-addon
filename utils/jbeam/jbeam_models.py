class JbeamLoadItem:
    def __init__(self, file_path: str, part_name: str="", slot_type: str=""):
        self.part_name = part_name
        self.slot_type = slot_type
        self.file_path = file_path

    def __repr__(self):
        return f"{self.__class__.__name__}(part_name={self.part_name}, slot_type={self.slot_type}, file_path={self.file_path})"