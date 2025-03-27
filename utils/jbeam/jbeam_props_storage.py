import uuid
import bpy
import json
import copy

class JbeamPropsStorage:
    _instance = None

    DOMAIN_ALIASES = {
        "vertices": "verts",
        "polygons": "faces"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.storage = {
                "verts": {},
                "edges": {},
                "faces": {}
            }
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls._instance or cls()

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
        self.storage[domain][key][f"instance_{instance}"] = copy.deepcopy(props)
        return key

    def fetch_props(self, domain: str, key: str, instance: int = 1) -> dict:
        """Retrieves properties for a specific instance in the specified domain."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        if key not in self.storage[domain]:
            return {}

        return copy.deepcopy(self.storage[domain][key].get(f"instance_{instance}", {}))

    def delete_props(self, domain: str, key: str, instance: int = None):
        """Removes properties from the specified domain. Optionally deletes a specific instance."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        if key not in self.storage[domain]:
            return

        if instance is None:
            # Delete the entire key
            del self.storage[domain][key]
        else:
            # Delete only the instance-specific properties
            instance_key = f"instance_{instance}"
            if instance_key in self.storage[domain][key]:
                del self.storage[domain][key][instance_key]

            # Clean up the key if no instances remain
            if not self.storage[domain][key]:
                del self.storage[domain][key]

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
        """Save JbeamPropsStorage data to mesh custom properties for all objects."""
        print("Saving file... Storing JbeamPropsStorage data.")
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            obj.data["saved_jbeam_props"] = json.dumps(self.storage)
            print(f"Saved JbeamPropsStorage to {obj.name}'s mesh.")

    def load_jbeam_props_from_mesh(self):
        """Load JbeamPropsStorage data from mesh custom properties for all objects."""
        print("Loading file... Restoring JbeamPropsStorage data.")
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or "saved_jbeam_props" not in obj.data:
                continue
            try:
                # Restore storage from the JSON data in the mesh
                restored_data = json.loads(obj.data["saved_jbeam_props"])
                self.storage.update(restored_data)
                print(f"Restored JbeamPropsStorage from {obj.name}'s mesh.")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Failed to restore JbeamPropsStorage from {obj.name}: {e}")

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