from src.direc import Direction


# Класс позиция на игровом поле: строка и столбец.
# Используется как ключ в структуре данных, поэтому у него есть hash/eq.
class Pos:
    def __init__(self, row: int, col: int):
        self.row: int = row
        self.col: int = col

    # Позволяет использовать объект Pos как элемент множества и ключ в словаре.
    def __hash__(self) -> int:
        return hash((self.row, self.col))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pos):
            return NotImplemented
        return self.row == other.row and self.col == other.col

    # Возвращает соседнюю позицию, сдвинутую на одну клетку в заданном направлении.
    def adj(self, direc: Direction) -> "Pos":
        return Pos(self.row + direc.value[0], self.col + direc.value[1])
