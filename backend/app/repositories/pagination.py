from dataclasses import dataclass
from math import ceil


@dataclass(slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return ceil(self.total / self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1


def build_offset_limit(*, page: int, page_size: int) -> tuple[int, int]:
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")

    offset = (page - 1) * page_size
    return offset, page_size
