import uuid
import bpy
import json
import copy
import logging

class JbeamPropsStorage:

    SAVED_JBEAM_PROPS = "saved_jbeam_props"

    DOMAIN_ALIASES = {
        "vertices": "verts",
        "polygons": "faces"
    }

    def __init__(self, obj):
        self.obj_id = obj[JbeamPropsStorageManager.JBEAM_OBJECT_ID]
        self.storage = {
            "verts": {},
            "edges": {},
            "faces": {}
        }

    @property
    def owner(self):
        for obj in bpy.data.objects:
            if obj.get(JbeamPropsStorageManager.JBEAM_OBJECT_ID) == self.obj_id:
                return obj
        logging.error("Invalid owner object:", self.obj_id)
        return None

    def resolve_domain(self, domain: str) -> str:
        return self.DOMAIN_ALIASES.get(domain, domain)

    def store_props(self, domain: str, key: str, props: dict, instance: int = 1) -> str:
        """Stores properties in the specified domain for a specific instance."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        # Generate a new key if necessary
        if not key or key not in self.storage[domain]:
            key = uuid.uuid4().hex[:12]

        # Ensure instance storage is initialized
        if key not in self.storage[domain]:
            self.storage[domain][key] = {}

        # Store a deep copy of the instance-specific properties
        self.storage[domain][key][f"{instance}"] = copy.deepcopy(props)
        return key

    def fetch_props(self, domain: str, key: str, instance: int = 1) -> dict:
        """Retrieves properties for a specific instance in the specified domain."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        if key not in self.storage[domain]:
            return {}

        return copy.deepcopy(self.storage[domain][key].get(f"{instance}", {}))

    def delete_props(self, domain: str, key: str, instance: int = None):

        domain = self.resolve_domain(domain)

        if domain not in self.storage:
            raise KeyError(f"Invalid domain: {domain}")

        if key not in self.storage[domain]:
            # raise KeyError(f"Key '{key}' not found in domain '{domain}'")
            logging.debug(f"Key '{key}' not found in domain '{domain}'. Ignore")
            return

        if instance is None:
            # Delete all instances for the key
            del self.storage[domain][key]
        else:
            instance_key = str(instance)

            if instance_key not in self.storage[domain][key]:
                # raise KeyError(f"Instance {instance} not found for key '{key}' in domain '{domain}'")
                logging.debug(f"Instance {instance} not found for key '{key}' in domain '{domain}'. Ignore")
                return

            del self.storage[domain][key][instance_key]  # Delete the specific instance

            # Renumber remaining instances
            remaining_instances = sorted(
                self.storage[domain][key].items(), key=lambda x: int(x[0])
            )
            self.storage[domain][key] = {
                str(i + 1): props for i, (_, props) in enumerate(remaining_instances)
            }

            # Remove key if all instances are deleted
            if not self.storage[domain][key]:
                del self.storage[domain][key]

        logging.debug(f"Deleted instance {instance} from key '{key}' in domain '{domain}'.")


    def get_total_instances(self, domain: str, key: str) -> int:
        """Returns the total number of instances for the given key in the specified domain."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        if key not in self.storage[domain]:
            return 0

        return len(self.storage[domain][key])

    def cleanup(self, domain: str, unused_keys: set):
        """Removes unused keys from the specified domain."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        for key in unused_keys:
            if key in self.storage[domain]:
                del self.storage[domain][key]

    def save_jbeam_props_to_mesh(self):
        """Save this object's properties to its mesh's custom properties."""
        logging.debug("Saving file... Storing JbeamPropsStorage data.")
        obj = self.owner
        try:
            obj[self.SAVED_JBEAM_PROPS] = json.dumps(self.storage)
            logging.debug(f"💾 Saved/Updated JbeamPropsStorage data for {obj.name}.")
        except Exception as e:
            logging.error(f"❌ Failed to save JbeamPropsStorage for {obj.name}: {e}")

    def load_jbeam_props_from_mesh(self):
        """Load the properties from the mesh's custom properties into the JbeamPropsStorage."""
        obj = self.owner
        if self.SAVED_JBEAM_PROPS not in obj:
            logging.debug(f"No saved Jbeam props found in {obj.name}'s mesh. Skipping.")
            return
        try:
            restored_data = json.loads(obj[self.SAVED_JBEAM_PROPS])
            self.storage.update(restored_data)
            logging.debug(f"🔄 Restored JbeamPropsStorage data from {obj.name}'s mesh.")
        except (json.JSONDecodeError, TypeError, Exception) as e:
            logging.debug(f"❌ Failed to restore JbeamPropsStorage from {obj.name}: {e}")


''' 
# Storage will look something like this:
{
    "edges": {
        "uuid_key": {  # Key for edge 17
            "instance_1": {"stiffness": 1000},
            "instance_2": {"stiffness": 1200}
        }
    }
}
'''
class JbeamPropsStorageManager:
    """Manager class to register and manage JbeamPropsStorage instances."""
    JBEAM_OBJECT_ID = "jbeam_object_id"
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.objects = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls._instance or cls()

    def register_object(self, obj):
        """Register an object with a unique JbeamPropsStorage ID."""
        id_key = self.JBEAM_OBJECT_ID
        if id_key not in obj:
            obj_id = uuid.uuid4().hex
            obj[id_key] = obj_id
            self.objects[obj_id] = JbeamPropsStorage(obj)
            logging.debug(f"Registered jbeam object '{obj.name}' with '{id_key}' = {obj_id}")
        else:
            obj_id = obj[id_key]
            if obj_id not in self.objects:
                self.objects[obj_id] = JbeamPropsStorage(obj)
            logging.debug(f"Object {obj.name} already registered with '{id_key}' = {obj_id}")

    def get_props_storage(self, obj):
        """Get the JbeamPropsStorage instance for a registered object."""
        id_key = self.JBEAM_OBJECT_ID
        if id_key not in obj:
            raise ValueError(f"Object {obj.name} is not registered.")
        obj_id = obj[id_key]
        return self.objects.get(obj_id)

    def save_all_jbeam_props_to_mesh(self):
        """Save all registered object's properties to their meshes."""
        for obj_id, storage in self.objects.items():
            obj = storage.owner
            if obj and obj.type == 'MESH':
                storage.save_jbeam_props_to_mesh()

    def load_all_jbeam_props_from_mesh(self):
        """Rebuild registry and load JBeam props from mesh safely after file load."""
        for obj in list(bpy.data.objects):
            try:
                if obj.type != 'MESH' or self.JBEAM_OBJECT_ID not in obj:
                    continue
                obj_id = obj[self.JBEAM_OBJECT_ID]
                if obj_id not in self.objects:
                    self.objects[obj_id] = JbeamPropsStorage(obj)
                    logging.debug(f"Rebuilt jbeam storage for '{obj.name}' with ID {obj_id}")
                storage = self.objects[obj_id]
                storage.load_jbeam_props_from_mesh()
            except ReferenceError:
                logging.warning(f"Skipped invalid object during load: {getattr(obj, 'name', '[unknown]')}")
            except Exception as e:
                logging.error(f"Error restoring jbeam props for {getattr(obj, 'name', '[unknown]')}: {e}")
