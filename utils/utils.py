import bpy

from typing import List, Callable, Any, Tuple

from dev_tools import bl_info # type: ignore

class Utils:

    @staticmethod
    def get_addon_module_name() -> str:
        return "dev_tools"

    @staticmethod
    def get_blender_version(prependv: bool=True, separator: str='.') -> str:
        v: Tuple[int, int, int] = bpy.app.version
        version: str = f"{v[0]}{separator}{v[1]}{separator}{v[2]}"
        return ('v' if prependv else '') + version

    @staticmethod
    def get_addon_version(prependv: bool=True, separator: str='.') -> str:
        return ('v' if prependv else '') + separator.join(map(str, bl_info['version']))

    @staticmethod
    def log_and_raise(msg: str, exc_type=Exception, cause: Exception = None):
        print(msg)
        if cause:
            raise exc_type(msg) from cause
        else:
            raise exc_type(msg)

    @staticmethod
    def log_and_report(msg: str, operator=None, level='INFO'):
        level = level.upper()
        print(f"{level}:", msg)
        if operator:
            if level not in {'INFO', 'WARNING', 'ERROR'}:
                level = 'INFO'
            operator.report({level}, msg)

    @staticmethod
    def get_gn_version():
        v: Tuple[int, int, int] = bpy.app.version
        if v >= (4, 0, 0):
            return '4_0'
        elif v >= (3, 4, 0):
            return '3_4'
        elif v >= (3, 3, 0):
            return '3_3'
        elif v >= (3, 1, 0):
            return '3_1'
        else:
            pass
        return '2_93'

    @staticmethod
    def is_class_registered(cls) -> bool:
        idname_py = cls.bl_idname
        module, op = idname_py.split(".")
        idname = module.upper() + "_" + "OT" + "_" + op
        return hasattr(bpy.types, idname)

    @staticmethod
    def try_register_operator(cls) -> None:
        if not Utils.is_class_registered(cls):
            bpy.utils.register_class(cls)

    @staticmethod
    def try_unregister_operator(cls) -> None:
        if Utils.is_class_registered(cls):
            bpy.utils.unregister_class(cls)

    @staticmethod
    def abstract_method(func: Callable) -> Callable[..., Any]:
        #@wraps(func)
        def wrapper(*args, **kwargs):
            raise NotImplementedError(f"{func.__name__} must be overridden in subclass.")
        return wrapper

    @staticmethod
    def get_bake_dimension(enum):
        if enum=="ONE_K": return "1024"
        elif enum=="TWO_K": return "2048"
        elif enum=="FOUR_K": return "4098"
        elif enum=="EIGHT_K": return "8192"
        print(f"Warning enum {enum} undefined! Using 2048 as fallback")
        return "2048"
    
    @staticmethod
    def create_collection_at_top(collection_name):
        col = bpy.data.collections.get(collection_name)
        if not col:
            col = bpy.data.collections.new(collection_name)
        scene_collections = bpy.context.scene.collection.children[:]
        for c in scene_collections:
            bpy.context.scene.collection.children.unlink(c)
        bpy.context.scene.collection.children.link(col)
        for c in scene_collections:
            bpy.context.scene.collection.children.link(c)
        return col