class ObjectStore:
    """
    Object representing a configured conection to an external storage locaiton

    Attributes:
        name (str): The alias of the storage connection
        prefix (str): The directory that files are written back to in the storage location
        readonly (bool): Whether the storage configuration is read-only or not
        self.provider (str): The cloud provider (aws, azure, or gcp)
    """

    def __init__(
        self,
        name: str,
        prefix: str,
        readonly: bool,
        provider: str,
        default: bool,
    ) -> None:
        self.name = name
        self.prefix = prefix
        self.readonly = readonly
        self.provider = provider
        self.default = default

    def __str__(self) -> str:
        return f"Storage configuration:\n- Name: {self.name}\n- Prefix: {self.prefix}\n- Readonly: {self.readonly}\n- Provider: {self.provider}\n- Default: {self.default}"

    def __repr__(self) -> str:
        return f"ObjectStore(name={self.name}, prefix={self.prefix}, readonly={self.readonly}, provider={self.provider})"
