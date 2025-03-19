import uuid

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

    def store_props(self, domain: str, key: str, props: dict) -> str:
        """Stores properties in the specified domain and returns a unique key."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        if not key or key in self.storage[domain]:
            key = uuid.uuid4().hex[:12]

        self.storage[domain][key] = props
        return key

    def fetch_props(self, domain: str, key: str) -> dict:
        """Retrieves properties from the specified domain by key."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        return self.storage[domain].get(key, {})

    def delete_props(self, domain: str, key: str):
        """Removes properties from the specified domain."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        if key in self.storage[domain]:
            del self.storage[domain][key]

    def cleanup(self, domain: str, unused_keys: set):
        """Removes unused keys from the specified domain."""
        domain = self.resolve_domain(domain)
        if domain not in self.storage:
            raise ValueError(f"Invalid domain: {domain}")

        for key in unused_keys:
            self.delete_props(domain, key)