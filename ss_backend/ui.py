from typing import Protocol


class UI(Protocol):
    def draw_grid(self) -> None:
        raise NotImplementedError()

    def draw_screen(self) -> None:
        raise NotImplementedError()

    def undraw_screen(self) -> None:
        raise NotImplementedError()

    def refresh(self) -> None:
        raise NotImplementedError()
