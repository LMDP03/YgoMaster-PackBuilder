from dataclasses import dataclass, field

@dataclass(slots=True)
class PlayerDefinition:
    key: str
    display_name: str
    main_pack_key: str
    mini_pack_keys: list[str] = field(default_factory=list)