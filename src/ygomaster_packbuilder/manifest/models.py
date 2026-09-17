from dataclasses import dataclass, field

@dataclass(slots=True)
class ManifestPackSource:
    provider: str
    external_id: str

@dataclass(slots=True)
class ManifestPack:
    key: str
    source: ManifestPackSource
    opening_policy: str | None

@dataclass(slots=True)
class ManifestSharedPack:
    key: str
    type: str
    source: ManifestPackSource
    opening_policy: str | None

@dataclass(slots=True)
class ManifestPlayer:
    key: str
    display_name: str
    main_pack: ManifestPack
    mini_packs: list[ManifestPack] = field(default_factory=list)

@dataclass(slots=True)
class ManifestProjectSettings:
    name: str
    default_opening_policy: str

@dataclass(slots=True)
class ProjectManifest:
    settings: ManifestProjectSettings
    players: list[ManifestPlayer] = field(default_factory=list)
    shared_packs: list[ManifestSharedPack] = field(default_factory=list)