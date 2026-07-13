from dataclasses import dataclass

@dataclass
class ZonType:
    num: int
    name: str
    size: int = None

    def get_array_element_type(self) -> tuple[int, str]:
        match self.num:
            case 8: return 1, "int64"