import random
from collections import deque

from src.agents.base import Agent
from src.direc import Direction
from src.pos import Pos
from src.snake import Snake


# Графовый агент выбирает следующий ход через поиск путей на сетке.
# Он сначала пытается построить безопасный цикл по всей доске,
# затем ищет кратчайший путь к еде и только после этого откладывает
# действия, если безопасный путь к еде невозможен.
class GraphAgent(Agent):
    HAMILTON_SEARCH_LIMIT: int = 10_000
    HAMILTON_THRESHOLD: int = 16

    def __init__(self):
        self.rand = random.Random()

        self.snake: Snake | None
        self.hamilton_index: list[list[int]]
        self.hamilton_search_count: int
        self.reset()

    # Сбрасывает внутреннее состояние агента при смене текущей игры.
    def reset(self, snake: Snake | None = None) -> None:
        self.snake = snake
        self.hamilton_index = []
        self.hamilton_search_count = 0

    # Основной выбор хода агента: сначала проверка тупика,
    # затем безопасный гамильтонов цикл, потом путь к еде и, в конце,
    # обходные шаги для освобождения пространства.
    def next_direc(self, snake: Snake) -> Direction:
        if self.snake != snake:
            self.reset(snake)

        food = snake.food
        assert food is not None

        neighbors = self.neighbors(snake.head(), snake, set())
        if not neighbors:
            # змея застряла, движемся в текущем направлении, чтобы завершить игру
            return snake.direc

        # если существует гамильтонов цикл, следуем ему
        if self.hamilton_index:
            return self.hamilton_direc(neighbors, snake)

        # пытаемся построить гамильтонов цикл, если змея достаточно длинная
        if snake.len() >= GraphAgent.HAMILTON_THRESHOLD:
            path_to_tail = self.hamilton_path(snake.tail(), snake)
            if path_to_tail:
                self.build_hamilton_index(path_to_tail, snake)
                return self.hamilton_direc(neighbors, snake)

        # ищем кратчайший путь к еде
        path_to_food = self.shortest_path(food, snake)
        if path_to_food:
            # пытаемся провести змею по кратчайшему пути, чтобы съесть еду
            snake_copy = snake.copy()
            for direc in path_to_food:
                snake_copy.move(direc)
            path_to_tail = self.shortest_path(snake_copy.tail(), snake_copy)
            # если после поедания еды змея всё ещё может достичь хвоста, следуем пути к еде
            if path_to_tail:
                return path_to_food[0]

        # безопасного пути к еде нет, пробуем двигаться по более длинному пути к хвосту
        path_to_tail = self.longer_path(snake.tail(), snake)
        if path_to_tail:
            return path_to_tail[0]

        # пути к хвосту тоже нет, просто уводим голову дальше от еды
        neighbors.sort(
            key=lambda x: self.manhattan_dist(x[1], food),
            reverse=True,
        )
        return neighbors[0][0]

    # Находит кратчайший путь по направлению от головы к цели через BFS.
    def shortest_path(self, dst: Pos, snake: Snake) -> list[Direction]:
        src = snake.head()
        visited = {src}
        queue: deque[tuple[Pos, list[Direction]]] = deque([(src, [])])
        while queue:
            pos, path = queue.popleft()
            if pos == dst:
                return path
            for direc, pos in self.neighbors(pos, snake, visited):
                queue.append((pos, path + [direc]))
                visited.add(pos)
        return []

    # Строит чуть более длинный маршрут, чтобы избежать зацикливания
    # у хвоста и дать змейке запас свободы для будущих ходов.
    def longer_path(self, dst: Pos, snake: Snake) -> list[Direction]:
        """Строит путь чуть длиннее кратчайшего."""
        shortest = self.shortest_path(dst, snake)
        longest: list[Direction] = []
        cur = snake.head()

        for direc in shortest:
            nxt = cur.adj(direc)
            extended = False

            test_direcs = []
            if direc in (Direction.UP, Direction.DOWN):
                test_direcs = [Direction.LEFT, Direction.RIGHT]
            else:
                test_direcs = [Direction.UP, Direction.DOWN]

            for test_direc in test_direcs:
                cur_extended = cur.adj(test_direc)
                nxt_extended = nxt.adj(test_direc)

                cur_extendable = (
                    self.is_reachable(cur_extended, snake)
                    # поедание еды может запереть змею, поэтому не расширяем маршрут, если там есть еда
                    and not snake.is_food(cur_extended)
                )

                nxt_extendable = (
                    self.is_reachable(nxt_extended, snake)
                    # coords[1] — предпоследняя клетка тела, которая станет новым хвостом
                    # после хода, поэтому расширение здесь безопасно
                    or nxt_extended == snake.coords[1]
                )

                if cur_extendable and nxt_extendable:
                    longest.append(test_direc)
                    longest.append(direc)
                    longest.append(test_direc.opposite())
                    extended = True
                    break

            if not extended:
                longest.append(direc)

            cur = nxt

        return longest

    # Подготавливает индекс по найденному гамильтонову пути,
    # чтобы затем быстро выбирать следующий шаг по порядку обхода.
    def build_hamilton_index(self, path: list[Direction], snake: Snake) -> None:
        self.hamilton_index = [list(row) for row in snake.grid]
        cur = snake.head()
        val = snake.grid_size**2
        for direc in path:
            nxt = cur.adj(direc)
            self.hamilton_index[nxt.row][nxt.col] = val
            cur = nxt
            val -= 1

    # Выбирает следующее направление по сохранённому порядку
    # обхода клеток в найденном гамильтоновом цикле.
    def hamilton_direc(
        self,
        neighbors: list[tuple[Direction, Pos]],
        snake: Snake,
    ) -> Direction:
        assert self.hamilton_index
        head = snake.head()
        head_index = self.hamilton_index[head.row][head.col]
        target_index = head_index - 1 if head_index > 1 else len(snake.grid) ** 2
        for direc, nbr in neighbors:
            if self.hamilton_index[nbr.row][nbr.col] == target_index:
                return direc
        assert False, "Invalid hamilton index"

    # Ищет гамильтонов путь от головы до хвоста, если поле достаточно большое
    # и в нём ещё существует потенциально безопасная схема обхода.
    def hamilton_path(self, dst: Pos, snake: Snake) -> list[Direction]:
        self.hamilton_search_count = 0
        src = snake.head()
        visited = {src}
        path: list[Direction] = []
        target_len = self.num_reachable(snake)
        if self.hamilton_backtrack(src, dst, snake, visited, path, target_len):
            return path
        return []

    # Поиск в глубину с отсечением и эвристикой Warnsdorf для
    # построения гамильтонова пути на маленькой сетке.
    def hamilton_backtrack(
        self,
        cur: Pos,
        dst: Pos,
        snake: Snake,
        visited: set[Pos],
        path: list[Direction],
        target_len: int,
    ) -> bool:
        if len(path) == target_len:
            return cur == dst

        if self.hamilton_search_count >= GraphAgent.HAMILTON_SEARCH_LIMIT:
            return False
        self.hamilton_search_count += 1

        # сначала исследуем соседей с меньшим числом возможных дальнейших ходов
        # (эвристика Warnsdorf)
        neighbors = self.neighbors(cur, snake, visited)
        neighbors.sort(key=lambda x: self.hamilton_heuristic(x[1], snake, visited))

        for direc, nbr in neighbors:
            # не посещаем dst слишком рано, если это не завершает путь целиком (отсечение)
            if nbr == dst and len(path) < target_len - 1:
                continue

            visited.add(nbr)
            path.append(direc)

            if self.hamilton_backtrack(nbr, dst, snake, visited, path, target_len):
                return True

            path.pop()
            visited.remove(nbr)

        return False

    def hamilton_heuristic(self, pos: Pos, snake: Snake, visited: set[Pos]) -> int:
        return len(self.neighbors(pos, snake, visited))

    def manhattan_dist(self, p1: Pos, p2: Pos) -> int:
        return abs(p1.row - p2.row) + abs(p1.col - p2.col)

    def neighbors(
        self,
        pos: Pos,
        snake: Snake,
        visited: set[Pos],
    ) -> list[tuple[Direction, Pos]]:
        result: list[tuple[Direction, Pos]] = []
        for direc in Direction:
            nbr = pos.adj(direc)
            if self.is_reachable(nbr, snake) and nbr not in visited:
                result.append((direc, nbr))
        self.rand.shuffle(result)  # перемешиваем соседей, чтобы уменьшить смещение в выборе пути
        return result

    # Считает, сколько клеток на поле доступны для обхода с учётом тела змеи.
    def num_reachable(self, snake: Snake) -> int:
        m, n = len(snake.grid), len(snake.grid[0])
        cnt = 0
        for row in range(m):
            for col in range(n):
                if self.is_reachable(Pos(row, col), snake):
                    cnt += 1
        return cnt

    # Проверяет, можно ли безопасно зайти в клетку: она не должна выходить
    # за границы и не должна быть занята телом змеи, кроме хвоста.
    def is_reachable(self, pos: Pos, snake: Snake) -> bool:
        # fmt: off
        return (
            not snake.is_out_of_bound(pos)
            and (snake.is_empty(pos) or snake.is_food(pos) or snake.is_tail(pos))
        )
        # fmt: on
