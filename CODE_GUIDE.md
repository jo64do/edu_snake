# Руководство по коду проекта Snake

Этот документ подробно объясняет, как работает каждая часть проекта — от точки входа до ИИ-алгоритмов.

---

## 1. Архитектура проекта (обзор)

```
snake/
├── main.py              — Точка входа. Разбирает CLI-аргументы, выбирает режим.
├── rl_train.py          — Точка входа для обучения RL-агента.
├── requirements.txt     — Зависимости: pygame, Pillow. (torch, numpy — для RL)
├── rl_model.pt          — Предобученная модель RL-агента.
├── src/
│   ├── __init__.py      — (пустой) Чтобы src был пакетом.
│   ├── cfg.py           — Глобальная конфигурация (размеры, цвета, начальные значения).
│   ├── cell.py          — Перечисления: CellValue, CellType, CellColor.
│   ├── direc.py         — Перечисление Direction с методами (left, right, opposite, index).
│   ├── mode.py          — Перечисление Mode (HUMAN, GRAPH, RL).
│   ├── pos.py           — Класс Pos — позиция на сетке (row, col).
│   ├── snake.py         — Класс Snake — игровая логика змеи (движение, столкновения, состояние).
│   ├── game.py          — Класс Game — отрисовка и главный цикл Pygame.
│   ├── bench.py         — Функции бенчмаркинга (run_bench, статистика).
│   └── agents/
│       ├── __init__.py  — Фабричная функция init_agent(mode) — создаёт нужного агента.
│       ├── base.py      — Протокол Agent (интерфейс: next_direc(snake) -> Direction).
│       ├── graph.py     — GraphAgent — ИИ на основе поиска в графе (Hamiltonian path + BFS).
│       └── rl.py        — RLAgent + RLNet — ИИ на основе усиления обучения (Double DQN).
└── docs/                — Анимации (gif) демонстрации работы.
```

---

## 2. Основные типы и конфигурация

### `src/cfg.py` — Config

Глобальная конфигурация проекта:

```python
class Config:
    FPS = 60                          # Кадровая частота игры
    SCREEN_SIZE = (330, 330)          # Размер окна в пикселях
    GRID_SIZE = 6                     # Размер сетки (6x6)
    CELL_SIZE = 55.0                  # Размер одной ячейки (330 / 6)
    CELL_PADDING = 12                 # Отступ внутри ячейки для отрисовки

    INIT_SNAKE_DIREC = RIGHT          # Начальное направление
    INIT_SNAKE_FOOD = Pos(4, 4)       # Начальная позиция еды
    INIT_SNAKE_POS = [Pos(1,1), Pos(1,2), Pos(1,3)]  # Начальные координаты тела
    INIT_SNAKE_CELLS = [BODY_HORZ, BODY_HORZ, HEAD_RIGHT]  # Типы ячеек тела

    LOG_DIR = "./logs"                # Где сохранять логи
    STATES_EXT = ".txt"               # Расширение для логов состояний
    RECORD_EXT = ".gif"              # Расширение для записей (анимаций)
```

Ключевые параметры:
- `GRID_SIZE = 6` — маленькое поле 6×6, максимальная длина змеи = 36.
- Изначально змея занимает 3 клетки: позиции (1,1), (1,2), (1,3), голова направлена вправо.
- Еда изначально в позиции (4,4).

### `src/cell.py` — CellValue, CellType, CellColor

Три перечисления для работы с ячейками сетки:

1. **CellValue** — числовые значения клеток в `grid`:
   - `EMPTY = 0` — пусто
   - `FOOD = -1` — еда

2. **CellType** — визуальные типы ячеек для отрисовки (какой спрайт рисовать):
   - `EMPTY`, `FOOD`
   - `HEAD_UP`, `HEAD_LEFT`, `HEAD_RIGHT`, `HEAD_DOWN` — голова в разных направлениях
   - `BODY_HORZ`, `BODY_VERT` — прямые части тела (горизонтальные/вертикальные)
   - `BODY_TURN_UL`, `BODY_TURN_UR`, `BODY_TURN_DL`, `BODY_TURN_DR` — изгибы тела

3. **CellColor** — RGB-цвета:
   - `BACKGROUND = (33, 33, 33)` — тёмно-серый фон
   - `GRID_LINE = (97, 97, 97)` — линии сетки
   - `FOOD = (255, 245, 157)` — жёлтая еда
   - `SNAKE_WALKING = (245, 245, 245)` — белая змея (живая)
   - `SNAKE_DEAD = (239, 83, 80)` — красная (мёртвая)
   - `SNAKE_FULL = (163, 255, 88)` — зелёная (доедела)

### `src/pos.py` — Pos

Простой класс позиции на сетке:

```python
class Pos:
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
    def adj(self, direc: Direction) -> Pos:  # Получить соседнюю позицию в направлении direc
        return Pos(self.row + direc.value[0], self.col + direc.value[1])
```

- `__hash__` и `__eq__` переопределены, чтобы Pos можно использовать в `set` и `list` как ключ.
- `adj(direc)` возвращает соседнюю позицию (например, если zмея движется RIGHT, adj даст Pos с col+1).

### `src/direc.py` — Direction

Перечисление направлений движения с методами:

```python
class Direction(Enum):
    UP = (-1, 0)      # row уменьшается (вверх по экрану)
    LEFT = (0, -1)    # col уменьшается
    DOWN = (1, 0)     # row увеличивается (вниз)
    RIGHT = (0, 1)    # col увеличивается
```

Методы:
- `is_opposite(other)` — проверяет, противоположно ли направление (нельзя двигаться назад).
- `opposite()` — возвращает противоположное направление.
- `left()` — поворот налево (например, UP → LEFT, LEFT → DOWN).
- `right()` — поворот направо (например, UP → RIGHT, RIGHT → DOWN).
- `index()` — числовой индекс (0-3), используется для one-hot кодирования в RL-агенте.

### `src/mode.py` — Mode

```python
class Mode(Enum):
    HUMAN = "This mode lets you play the game yourself."
    GRAPH = "This mode lets an AI play based on graph algorithms."
    RL = "This mode lets an AI play based on reinforcement learning."
```

---

## 3. Игровая логика — `src/snake.py`

Класс `Snake` инкапсулирует всю игровую логику без отображения:

### Состояние змеи

```python
class State(Enum):
    WALKING = auto()  # Живёт и движется
    DEAD = auto()     # Умерла (врезалась в стену или саму себя)
    FULL = auto()     # Доедела (достигла максимальной длины 36)
```

### Атрибуты

- `grid_size` — размер сетки.
- `coords: deque[Pos]` — координаты тела. `coords[-1]` — голова (последний элемент), `coords[0]` — хвост.
- `cells: deque[CellType]` — визуальные типы для каждой клетки тела (соответствуют `coords`).
- `direc` — текущее направление движения.
- `food: Pos | None` — позиция еды.
- `grid: list[list[int]]` — внутренняя сетка: 0 = пусто, -1 = еда, >0 = номер сегмента тела (голова = длина, хвост = 1).
- `rand` — `random.Random` для воспроизводимой генерации еды.

### Ключевые методы

#### `move(new_direc: Direction)`

Основной метод движения. Логика:

1. **Проверка направления**: если `new_direc` противоположно текущему, движение отменяется (змея не может развернуться на 180°).

2. **Вычисление новой головы**: `new_head = head().adj(new_direc)`.

3. **Проверка роста**: `will_grow = is_food(new_head)` — если новая позиция — еда, змея растёт.

4. **Проверка смерти**: `will_die = is_out_of_bound(new_head) or (is_snake(new_head) and not is_tail(new_head))` — умирает, если вышла за границы или врезалась в своё тело (кроме хвоста, который в этот момент может освободиться).

5. **Обновление ячеек**:
   - Старая голова (теперь первая секция тела) преобразуется в нужный тип тела через `old_head_cell_after_move(new_direc)` — учитывает, в каком направлении она шла и вошла, чтобы нарисовать прямую или изгиб.
   - Новая голова добавляется в конец `coords` и `cells` как `new_head_cell_after_move(new_direc)` (например, `HEAD_RIGHT`).

6. **Обновление хвоста**: если змея не растёт, удаляется первый элемент (хвост) из `coords` и `cells`.

7. **Генерация новой еды**: если змея съела еду (`will_grow`), вызывается `new_food()`, которая случайным образом выбирает пустую клетку.

8. **Проверка состояния**:
   - Если умерла → `State.DEAD`.
   - Если достигла макс. длины (36) → `State.FULL`.

9. `refresh_grid()` перестраивает внутреннюю числовую сетку.

#### `refresh_grid()`

Перестраивает `self.grid` из `self.coords`:
- Всё очищается (устанавливается в 0).
- Проходит по координатам в обратном порядке (от головы к хвосту), заполняя значениями 1, 2, 3... (голова = `len(coords)`, хвост = 1).
- Устанавливает еду (`CellValue.FOOD.value = -1`).

#### `is_reachable` (в Snake)

Методы проверок:
- `is_empty(pos)` — клетка пуста (grid[pos] == 0).
- `is_food(pos)` — клетка — еда (grid[pos] == -1).
- `is_snake(pos)` — клетка занята телом (grid[pos] > 0).
- `is_tail(pos)` — позиция — хвост (координаты совпадают с `coords[0]`).
- `is_out_of_bound(pos)` — выход за границы сетки.
- `len()` — длина змеи (количество сегментов).
- `max_len_reached()` — `len() >= grid_size²` (36 для 6×6).
- `is_stopped()` — состояние != WALKING (game over).
- `serialize_states()` — текстовое представление сетки для логирования.

---

## 4. Отображение и цикл игры — `src/game.py`

Класс `Game` отвечает за:
- Инициализацию Pygame.
- Главный цикл (loop).
- Обработку ввода (события клавиатуры).
- Отрисовку (pygame.draw).
- Запись кадров в GIF.

### Главный цикл `loop()`

```python
def loop(self):
    self.print_info()
    pygame.init()
    self.screen = pygame.display.set_mode(Config.SCREEN_SIZE, pygame.NOFRAME)
    clock = pygame.time.Clock()
    while True:
        if not self.handle_events():
            break
        self.move()
        self.refresh_screen()
        self.capture_frame()
        clock.tick(Config.FPS)
    self.save_recording()
    pygame.quit()
```

1. Запускается Pygame, создаётся окно.
2. Каждый кадр: обрабатываются события → змея двигается → экран перерисовывается → кадр сохраняется (если включена запись).
3. `clock.tick(FPS)` ограничивает частоту кадров 60 FPS.
4. При выходе — сохраняется запись (GIF) и завершается Pygame.

### Обработка ввода `handle_events()`

Обрабатывает pygame-события:
- `QUIT` — выход.
- `ESCAPE` — выход.
- `SPACE` — пауза/воспроизведение.
- `R` — перезапуск (с очисткой и сохранением записи).
- `W/A/S/D` — ручное управление змеей (только в режиме HUMAN).

### Логика движения `move()`

1. Проверка таймера: змея двигается только раз в `move_freq` миллисекунд (по умолчанию 80ms).
2. Если игра окончена — ничего не делает.
3. Если нет нового направления (`next_direc is None`):
   - Если пауза — сбрасывает.
   - Если есть агент — агент выбирает направление: `agent.next_direc(self.snake)`.
   - Иначе — змея продолжает движение в том же направлении.
4. Проверяется, что новое направление не противоположно текущему (`next_direc_valid()`).
5. Движение: `self.snake.move(self.next_direc)`.
6. Состояния логируются в файл (`save_states()`).

### Отрисовка `refresh_screen()`

1. Заливка фона (`CellColor.BACKGROUND`).
2. Если включена сетка (`-g`) — рисуются линии.
3. Проход по всем сегментам змеи (`coords` и `cells`) — каждая рисуется через `draw()`.
4. Рисуется еда.
5. `pygame.display.flip()` — обновление экрана.

### Метод `draw(pos, cell_type)`

Определяет, что рисовать:
- Для `FOOD` — вызывает `draw_food()`.
- Для остальных типов — вызывает `draw_snake()`.
- `draw_snake()` рассчитывает координаты прямоугольника для каждого типа тела, учитывая `CELL_PADDING`.

### Цвет змеи `snake_color()`

Цвет зависит от состояния:
- `WALKING` → белый (`SNAKE_WALKING`).
- `DEAD` → красный (`SNAKE_DEAD`).
- `FULL` → зелёный (`SNAKE_FULL`).

### Запись `capture_frame()` и `save_recording()`

Если `record_frames` включён:
- Каждый кадр преобразуется из Pygame-поверхности в изображение PIL и сохраняется в `self.frames`.
- При завершении — все кадры сохраняются как анимированный GIF (`Config.RECORD_EXT = ".gif"`).

---

## 5. ИИ-агенты

### Интерфейс — `src/agents/base.py`

```python
class Agent(Protocol):
    def next_direc(self, snake: Snake) -> Direction: ...
```

Это протокол (интерфейс). Любой агент должен реализовать метод `next_direc`, который принимает состояние змеи и возвращает направление движения.

### Фабрика — `src/agents/__init__.py`

```python
def init_agent(mode: Mode) -> Agent | None:
    if mode == Mode.GRAPH:
        return GraphAgent()
    if mode == Mode.RL:
        return RLAgent()
    return None  # HUMAN
```

### Бенчмарк — `src/bench.py`

`run_bench(mode, num_rounds, rand_seed, max_steps)`:
1. Создаёт агента нужного типа.
2. Для каждой партии:
   - Создаёт новую змею со стартовыми параметрами из Config.
   - Запускает цикл: пока змея не остановилась и не достигла `max_steps`, вызывает `snake.move(agent.next_direc(snake))`.
   - Записывает время, шаги, очки (длина).
3. Подсчитывает статистику: минимум, максимум, среднее по времени, шагам, очкам.
4. Success Rate = количество побед (достигли FULL) / общее число раундов.

---

## 6. GraphAgent — `src/agents/graph.py`

Это ИИ на основе **поиска в графе**. Алгоритм использует несколько стратегий в порядке приоритета:

### Параметры

- `HAMILTON_SEARCH_LIMIT = 10_000` — максимум шагов backtracking для поиска гамильтонова пути.
- `HAMILTON_THRESHOLD = 16` — минимальная длина змеи, при которой пытаемся построить гамильтонов цикл.

### Основной метод `next_direc(snake)`

Стратегия выбора хода (в порядке приоритета):

#### Шаг 1: Проверка соседей

```python
neighbors = self.neighbors(snake.head(), snake, set())
if not neighbors:
    return snake.direc  # Застряли — двигаемся вперёд (самоубийство)
```

Если нет доступных ходов — змея застряла, выбирается текущее направление.

#### Шаг 2: Следование гамильтонову циклу

Если гамильтонов индекс уже построен (`self.hamilton_index` непуст), то выбирается ход, который движется к предыдущей ячейке цикла (`hamilton_direc`).

#### Шаг 3: Построение гамильтонова пути

Если змея достаточно длинная (>= 16), пытаемся построить гамильтонов путь от хвоста к голове:

```python
if snake.len() >= HAMILTON_THRESHOLD:
    path_to_tail = self.hamilton_path(snake.tail(), snake)
    if path_to_tail:
        self.build_hamilton_index(path_to_tail, snake)
        return self.hamilton_direc(neighbors, snake)
```

**Гамильтонов путь** — путь, который посещает каждую вершину ровно один раз. Для змеи это гарантирует посетить все клетки без самозастревания.

**Поиск с backtracking + эвристика Уорндорфа**:
- `hamilton_backtrack()` — рекурсивно пытается построить путь.
- `hamilton_heuristic()` — сортирует соседей по количеству их соседей (чем меньше выходов — тем приоритетнее, чтобы не «запереть» себя в узком месте).

#### Шаг 4: Кратчайший путь к еде (BFS)

Если нет гамильтонова пути или змея короткая, ищем кратчайший путь к еде:

```python
path_to_food = self.shortest_path(food, snake)
if path_to_food:
    # Симулируем движение по пути
    snake_copy = snake.copy()
    for direc in path_to_food:
        snake_copy.move(direc)
    # Проверяем: после поедания еды можно ли добраться до хвоста
    path_to_tail = self.shortest_path(snake_copy.tail(), snake_copy)
    if path_to_tail:
        return path_to_food[0]  # Безопасно ехать к еде
```

Это ключевая проверка: змея съедает еду, растёт, и мы проверяем, не заперлась ли она. Если путь к хвосту существует после поедания — ходим к еде.

#### Шаг 5: Длинный путь к хвосту

Если к еде нельзя безопасно подойти, ищем "длинный путь" к хвосту:

```python
path_to_tail = self.longer_path(snake.tail(), snake)
if path_to_tail:
    return path_to_tail[0]
```

**`longer_path`** — это кратчайший путь с добавлением "змеевых" отклонений (влево-вправо-влево) вдоль каждого сегмента. Это создаёт зигзагообразный путь, который заполняет больше пустых клеток, освобождая место для будущих ходов.

#### Шаг 6: Уклонение от еды

Если ничего не сработало:
```python
neighbors.sort(key=lambda x: self.manhattan_dist(x[1], food), reverse=True)
return neighbors[0][0]  # Ходим в сторону, максимально удалённую от еды
```

Ходим туда, где дальше от еды (чтобы освободить пространство).

---

## 7. RLAgent — `src/agents/rl.py`

Это ИИ на основе **усиления обучения** (Deep Reinforcement Learning) с алгоритмом **Double DQN**.

### RLParams — параметры обучения

```python
class RLParams:
    MODEL_PATH = "./rl_model.pt"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    NUM_GRID_CHANNELS = 4         # Количество каналов сетки в состоянии
    NUM_1D_FEATURES = 9           # 4 (направление) + 4 (направление к еде) + 1 (расстояние)
    NUM_ACTIONS = 3               # Прямо / влево / вправо
    
    NUM_EPISODES = 100_000        # Количество эпизодов обучения
    NUM_EPISODES_FOR_AVG = 200    # Скользящее среднее за 200 эпизодов
    EPSILON_INIT = 1.0            # Начальная вероятность случайного действия
    EPSILON_MIN = 0.01            # Минимальная вероятность
    EPSILON_DECAY_EPISODES = 50_000  # За сколько эпизодов достичь MIN
    NUM_STEPS_PER_EPISODE = 500   # Максимум шагов за эпизод
    NUM_STEPS_PER_LEARNING = 4    # Как часто обучаться (каждые 4 шага)
    MAX_STEPS_WITHOUT_FOOD_BEFORE_STOP = 36  # Таймаут без еды
    
    MAX_MEM_SIZE = 100_000        # Размер replay-буфера
    BATCH_SIZE = 64               # Размер батча
    LEARNING_RATE = 0.001         # lr для Adam
    UPDATE_RATE = 0.005           # τ для soft update целевой сети
    DISCOUNT = 0.99               # γ (коэффициент дисконтирования)
    MAX_GRAD_NORM = 10.0          # Градиентный клиппинг
```

### RLNet — нейронная сеть

```python
class RLNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        # CNN для обработки 2D сетки (4 канала: еда, тело, голова, опасность)
        self.conv = nn.Sequential(
            nn.Conv2d(4, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        # MLP для объединения CNN-выхода с 1D признаками
        self.mlp = nn.Sequential(
            nn.Linear(64*6*6 + 9, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 3),  # 3 выхода: Q(s, go_straight), Q(s, turn_left), Q(s, turn_right)
        )
```

**Архитектура**: две сверточные слоя (для 2D сетки) + три полносвязных слоя (для объединения с 1D признаками).

### Состояние (state)

Состояние состоит из двух частей:

1. **4 канала 6×6 (2D сетка)**:
   - Канал 1: позиция еды (1.0 если еда, 0 иначе).
   - Канал 2: тело змеи (нормализованное: `val / snake_len`).
   - Канал 3: голова (1.0 на позиции головы).
   - Канал 4: опасность (1.0 для всех сегментов тела, кроме хвоста).

2. **1D вектор (9 чисел)**:
   - 4 числа: one-hot направления движения змеи.
   - 4 числа: one-hot направления к еде (вверх/влево/вниз/вправо).
   - 1 число: расстояние Мэнхэтена до еды (нормализованное: `dist / (2 * grid_size)`).

### Действия (action)

Действий три:
- `0` — **go straight** (продолжить в том же направлении).
- `1` — **turn left** (повернуть налево относительно текущего направления).
- `2` — **turn right** (повернуть направо).

`action_to_direc(action, snake)` преобразует действие в Direction:
- `0` → `snake.direc` (прямо)
- `1` → `snake.direc.left()` (влево)
- `2` → `snake.direc.right()` (вправо)

### Награды (reward)

```python
def move(self, snake, action):
    snake.move(self.action_to_direc(action, snake))
    ...
    reward = -0.01              # Малый штраф за каждый шаг (поощряет скорость)
    if snake.state == DEAD:
        reward = -100.0         # Большой штраф за смерть
    elif snake.state == FULL:
        reward = 100.0          # Большой бонус за победу
    elif snake.len() > self.prev_len:
        reward = 10.0           # Бонус за поедание еды
        self.steps_without_food = 0
    else:
        self.steps_without_food += 1
    
    if self.steps_without_food >= self.timeout_steps(snake):
        reward = -100.0         # Штраф за "залипание"
        done = True
    return next_state, reward, done
```

### Целевая функция (loss)

Используется **Double DQN**:

```python
def loss(self, experiences, q_net, q_net_target):
    states, actions, rewards, next_states, done_vals = ...
    
    with torch.no_grad():
        # 1. Q-значения для следующего состояния от ONLINE-сети (q_net)
        q_vals_next = q_net(next_states)
        best_actions_next = q_vals_next.argmax(-1, True)  # Лучшее действие от online
        
        # 2. Целевые Q-значения от TARGET-сети (q_net_target)
        q_target_vals = q_net_target(next_states)
        q_target_vals_max = q_target_vals.gather(1, best_actions_next).squeeze(1)
    
    # 3. Целевая функция: y = r + γ * max Q(s', a') * (1 - done)
    y_targets = rewards + (DISCOUNT * q_target_vals_max * (1 - done_vals))
    
    # 4. Q-значения для текущего состояния
    q_vals = q_net(states)
    q_vals = q_vals.gather(1, actions.long().unsqueeze(1)).squeeze(1)
    
    # 5. Huber loss (smooth L1)
    return torch.nn.functional.smooth_l1_loss(q_vals, y_targets)
```

**Почему Double DQN?** В обычном DQN целевая сеть используется и для выбора лучшего действия, и для оценки его Q-значения. Это приводит к переоценке. Double DQN разделяет эти роли: online-сеть выбирает лучшее действие, target-сеть оценивает его.

### Soft Update целевой сети

```python
def soft_update(self, q_net, q_net_target):
    for q_net_params, target_params in zip(q_net.parameters(), q_net_target.parameters()):
        target_params.data.copy_(
            UPDATE_RATE * q_net_params.data + (1.0 - UPDATE_RATE) * target_params.data
        )
```

Целевая сеть постепенно "смягчается" к online-сети с коэффициентом `τ = 0.005` (очень мало — почти не меняется за один шаг).

### Политика ε-жадного поиска

```python
def action(self, q_vals, epsilon=None):
    if epsilon is not None and torch.rand(1).item() < epsilon:
        return torch.randint(0, q_vals.shape[-1], (1,)).item()  # Случайно
    return q_vals.argmax().item()  # Жадно
```

- ε убывает линейно с 1.0 до 0.01 за 50 000 эпизодов.
- Сначала змея исследует (random), потом использует знания (greedy).

### Replay-буфер

```python
mem = deque(maxlen=MAX_MEM_SIZE)  # 100 000 опытов
```

Опыт `(state, action, reward, next_state, done)` сохраняется в буфер. Для обучения случайно выбираются 64 опыта (BATCH_SIZE), что разрушает корреляцию между последовательными состояниями.

### Цикл обучения

```python
def train(self):
    q_net = RLNet()          # Online-сеть
    q_net_target = RLNet(q_net)  # Целевая сеть (копия)
    optimizer = Adam(q_net.parameters(), lr=0.001)
    mem = deque(maxlen=100_000)
    
    for episode in range(100_000):
        snake = self.new_snake()
        state = self.state(snake)
        
        for step in range(500):
            q_vals = q_net(state)
            action = self.action(q_vals, epsilon)
            next_state, reward, done = self.move(snake, action)
            mem.append(RLExperience(state, action, reward, next_state, done))
            state = next_state
            
            if self.should_learn(step, mem):  # Каждые 4 шага
                experiences = random.sample(mem, 64)
                self.learn(experiences, q_net, q_net_target, optimizer)
            
            if done:
                break
        
        epsilon = self.next_epsilon(episode)  # Линейное убывание
        self.print_summary(episode, ...)      # Вывод прогресса
        
        if (episode + 1) % 200 == 0:
            print()  # Перенос строки каждые 200 эпизодов
    
    self.save(q_net)  # Сохранение модели
```

### Инференс (game mode)

```python
def next_direc(self, snake: Snake) -> Direction:
    if self.eval_net is None:
        self.eval_net = self.new_eval_net()  # Загрузка rl_model.pt
    state = self.state(snake)
    with torch.no_grad():
        q_vals = self.eval_net(state.to(DEVICE))
    action = self.action(q_vals)  # ε=0 → всегда жадно
    return self.action_to_direc(action, snake)
```

Для игры (`python main.py -m rl`) загружается предобученная модель из `rl_model.pt`.

---

## 8. Точка входа — `main.py`

```python
def main():
    args = parse_args()
    mode = Mode[args.mode.upper()]  # human / graph / rl
    
    if args.bench_rounds is None:
        # Игровой режим: открывается окно Pygame
        game = Game(mode, args.move_freq, args.show_grid, args.record_frames, args.seed)
        game.loop()
    else:
        # Бенчмарк-режим: нет окна, играет ИИ
        run_bench(mode, args.bench_rounds, args.seed)
```

CLI-аргументы:
- `-m {human,graph,rl}` — режим (по умолчанию graph).
- `-f <freq>` — частота ходов змеи в мс (по умолчанию 80).
- `-g` — показывать сетку.
- `-r` — записывать игру в GIF.
- `-s <seed>` — seed для воспроизводимости.
- `-b <rounds>` — количество раундов бенчмарка.

### `rl_train.py`

```python
def main():
    agent = RLAgent()
    agent.train()

if __name__ == "__main__":
    main()
```

Просто создаёт RLAgent и запускает обучение (требует PyTorch и видеокарту/CUDA).
