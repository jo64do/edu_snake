## PyGame — детальный обзор использования в проекте Snake

<FILE>/home/jk/mSr/heRmm/snake/src/game.py</FILE>

```python
import os
import time
from datetime import datetime, timezone

# NOTE: SDL_AUDIODRIVER="dummy" — отключаем аудио (в серверной/CI среде нет звуковой карты).
#       Без этого pygame.mixer может падать при инициализации.
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# NOTE: PYGAME_HIDE_SUPPORT_PROMPT="1" — скрываем "Hello from the pygame community" при импорте.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# NOTE: pygame — библиотека для создания 2D-игр на Python.
#       Основана на SDL (Simple DirectMedia Layer). Предоставляет:
#       - Окно и OpenGL-контекст (pygame.display)
#       - Обработку событий ввода (pygame.event)
#       - Рисование примитивов (pygame.draw)
#       - Работу с поверхностями (pygame.Surface)
#       - Таймер/клок (pygame.time.Clock)
#       - Работу с изображениями и аудио (pygame.image, pygame.mixer)
#       Подробнее: https://www.pygame.org/docs/
import pygame
from PIL import Image

from src.agents import init_agent
from src.agents.base import Agent
from src.cell import CellColor, CellType
from src.cfg import Config
from src.direc import Direction
from src.mode import Mode
from src.pos import Pos
from src.snake import Snake
```

<SUMMARY>
Файл game.py содержит класс Game, который реализует отображение и главный цикл игры Snake с помощью библиотеки pygame. 
Основные функции: инициализация Pygame, создание окна, обработка клавиш (W/A/S/D для управления, SPACE для паузы, R для перезаписи, ESC для выхода), 
отрисовка змеи и еды на экране, рисование отдельных ячеей через pygame.draw.rect с учётом направления и изгибов тела, 
а также запись кадров в анимированный GIF с помощью Pillow (PIL).
</SUMMARY>

<LIB>pygame</LIB> — основной графический движок для создания окна, обработки ввода и отрисовки.  
<LIB>PIL (Pillow)</LIB> — используется для захвата кадров (pygame.image.tobytes → Image.frombytes) и сохранения их как GIF.  
<LIB>os</LIB> — для установки SDL_AUDIODRIVER и создания директории логов.  
<LIB>time</LIB> — time.monotonic() для измерения времени между ходами змеи.  
<LIB>datetime</LIB> — для генерации уникальных имён файлов логов.

---

### 1. Инициализация Pygame

```python
def loop(self) -> None:
    self.print_info()
    pygame.init()  # NOTE: инициализирует ВСЕ модули pygame (display, event, draw, font, mixer, и т.д.)
    self.screen: pygame.Surface = pygame.display.set_mode(Config.SCREEN_SIZE, pygame.NOFRAME)
    clock = pygame.time.Clock()
```

**Что делает `pygame.init()`:**
- Инициализирует все подсистемы Pygame: видео (`display`), ввод (`event`, `key`, `mouse`), звуковую систему (`mixer`), шрифты (`font`), таймеры (`time`).
- После `init()` можно создавать окно через `display.set_mode()`.
- `Config.SCREEN_SIZE = (330, 330)` — размер окна в пикселях.
- `pygame.NOFRAME` — окно без рамок (нет заголовка, кнопок minimize/close). Это типично для демонстраций.

---

### 2. Главный цикл (Game Loop)

```python
while True:
    if not self.handle_events():  # Обработка событий ввода
        break
    self.move()                   # Логика движения змеи
    self.refresh_screen()         # Отрисовка кадра
    self.capture_frame()          # Захват кадра для записи
    clock.tick(Config.FPS)        # Ограничение FPS до 60
```

**Цикл игры (game loop)** — фундаментальный паттерн в большинстве игр. Схема:
1. Обработка ввода (polling events)
2. Обновление состояния (логика движения, столкновений)
3. Рендеринг (отрисовка на экран)
4. Ожидание до следующего кадра (tick Clock)

`clock.tick(Config.FPS)` задаёт задержку, чтобы цикл не работал слишком быстро (ограничение 60 кадров/сек).

---

### 3. Обработка событий (pygame.event)

```python
def handle_events(self) -> bool:
    for event in pygame.event.get():  # NOTE: .get() возвращает список всех накопившихся событий
        if event.type == pygame.QUIT:        # Закрытие окна (кнопка X)
            return False
        if event.type == pygame.KEYDOWN:     # NOTE: KEYDOWN = нажатие клавиши (не удерживание)
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_r:
                self.save_recording()
                self.reset()
            elif event.key == pygame.K_w:
                self.next_direc = Direction.UP
            elif event.key == pygame.K_a:
                self.next_direc = Direction.LEFT
            elif event.key == pygame.K_s:
                self.next_direc = Direction.DOWN
            elif event.key == pygame.K_d:
                self.next_direc = Direction.RIGHT
    return True
```

**pygame.event.get()** — возвращает список всех событий, произошедших с момента последнего вызова.  
**event.type** — тип события:
- `pygame.QUIT` — пользователь закрыл окно.
- `pygame.KEYDOWN` — нажатие клавиши. Событие приходит один раз на нажатие.
- (Ещё: `KEYUP`, `MOUSEMOTION`, `MOUSEBUTTONDOWN`, `MOUSEBUTTONUP`, `ACTIVEEVENT`, `WINDOWRESIZED` и др.)

**pygame.K_ESCAPE, K_SPACE, K_w, ...** — константы клавиш (аналог `pygame.K_UP`, `K_DOWN`).

---

### 4. Отрисовка (pygame.draw + Surface)

#### Основной принцип: Surface

```python
self.screen: pygame.Surface = pygame.display.set_mode(Config.SCREEN_SIZE, pygame.NOFRAME)
```

**pygame.Surface** — это "поверхность" (canvas), на которую можно рисовать. Главная поверхность — `self.screen` (создаётся из `set_mode`). Другие поверхности создаются для спрайтов, текстур и т.п.

#### Заливка фона

```python
def refresh_screen(self) -> None:
    self.screen.fill(CellColor.BACKGROUND.value)  # NOTE: fill() заливает всю поверхность одним цветом
    # ... рисование объектов ...
    pygame.display.flip()  # NOTE: flip() обновляет экран — показывает всё нарисованное
```

- `Surface.fill(color)` — заливка всей поверхности цветом.
- `pygame.display.flip()` — "переворачивает" экран: всё, что нарисовано в памяти в `screen`, становится видимым на мониторе.
- (Можно использовать `pygame.display.update()` для обновления только части экрана, но `flip()` проще.)

#### Рисование сетки

```python
if self.show_grid:
    for row in range(Config.GRID_SIZE):
        for col in range(Config.GRID_SIZE):
            self.draw(Pos(row, col), CellType.EMPTY)
```

Когда флаг `-g` включён, сначала рисуется сетка (линии между клетками), потом поверх неё — змея и еда.

#### Рисование прямоугольников (pygame.draw.rect)

```python
def draw_food(self, pos: Pos) -> None:
    row, col = pos.row, pos.col
    x = col * Config.CELL_SIZE + Config.CELL_PADDING
    y = row * Config.CELL_SIZE + Config.CELL_PADDING
    w = h = Config.CELL_SIZE - 2 * Config.CELL_PADDING
    pygame.draw.rect(self.screen, CellColor.FOOD.value, (x, y, w, h))
```

**pygame.draw.rect(surface, color, rect, width=0)**:
- `surface` — куда рисуем (обычно `self.screen`).
- `color` — RGB-кортеж, например `(255, 245, 157)`.
- `rect` — кортеж `(x, y, width, height)` или `pygame.Rect(x, y, w, h)`.
- `width` — если 0 (по умолчанию), прямоугольник **заполнен**. Если > 0, это толщина границы.

**Координаты**: в Pygame начало координат (0, 0) — в **левом-верхнем** углу. `x` — горизонталь (вправо), `y` — вертикаль (вниз).

---

### 5. Сложная отрисовка змеи (draw_snake)

```python
def draw_snake(self, pos: Pos, cell_type: CellType) -> None:
    row, col = pos.row, pos.col
    color = self.snake_color()  # Цвет зависит от состояния (живая/мёртвая/доеддена)
    x = y = w = h = 0

    if cell_type in (HEAD_UP, BODY_TURN_DL, BODY_TURN_DR):
        # Голова вверх или изгиб вниз-влево/вниз-вправо
        x = col * CELL_SIZE + CELL_PADDING
        y = row * CELL_SIZE + CELL_PADDING
        w = CELL_SIZE - 2 * CELL_PADDING
        h = CELL_SIZE - CELL_PADDING
    elif ...
    # ... много elif для каждого типа CellType ...
    
    if w * h > 0:
        pygame.draw.rect(self.screen, color, (x, y, w, h))
```

Этот метод сложный, потому что змея состоит из разных "кубиков", каждый из которых может быть:
- Головой (4 направления)
- Прямой частью тела (горизонтальная/вертикальная)
- Изгибом (4 типа)

Для каждого типа рассчитываются координаты и размеры прямоугольника, чтобы получился правильный визуальный вид.

---

### 6. Цикл с ограничением FPS (pygame.time.Clock)

```python
clock = pygame.time.Clock()
# В цикле:
clock.tick(Config.FPS)  # Config.FPS = 60
```

**pygame.time.Clock** — таймер. `clock.tick(fps)`:
- Ждёт, чтобы прошла достаточная задержка для поддержания `fps` кадров в секунду.
- Возвращает количество миллисекунд, прошедших с предыдущего вызова.
- Без `tick()` цикл работает на полной скорости (1000+ FPS), расходуя CPU.

---

### 7. Захват и запись кадров (pygame.image + PIL)

```python
def capture_frame(self) -> None:
    if not self.record_frames:
        return
    data = pygame.image.tobytes(self.screen, "RGB")  # NOTE: tobytes() — это pygame.image.Surface.tobytes()
    size = self.screen.get_size()
    self.frames.append(Image.frombytes("RGB", size, data))
```

**pygame.image.tobytes(surface, "RGB")**:
- Превращает содержимое поверхности `screen` в байтовый массив.
- `"RGB"` — формат пикселей (красный, зелёный, синий, по 1 байту на канал).

**PIL.Image.frombytes("RGB", size, data)**:
- Создаёт объект изображения из байтового массива.
- `size` — кортеж (width, height).
- `data` — сырые пиксели.

Все кадры сохраняются в список `self.frames` и позже становятся анимированным GIF:

```python
def save_recording(self) -> None:
    if not self.record_frames or not self.frames:
        return
    self.frames[0].save(
        self.log_path_pfx + Config.RECORD_EXT,
        save_all=True,
        append_images=self.frames[1:],
        duration=int(1000 / Config.FPS),
        loop=0,
    )
```

**Image.save(..., save_all=True, append_images=...)** — специфичная функция Pillow для сохранения анимированного GIF:
- `save_all=True` — сохраняет все кадры.
- `append_images` — список остальных кадров.
- `duration` — время показа каждого кадра в миллисекундах.
- `loop=0` — зацикливание GIF бесконечно.

---

### 8. Цикл движения с таймером

```python
def move(self) -> None:
    now = time.monotonic()
    if (now - self.last_move_time) * 1000 < self.move_freq:  # move_freq = 80ms по умолчанию
        return
    self.last_move_time = now
    ...
    self.snake.move(self.next_direc)
```

Pygame-цикл работает на 60 FPS (~16.6 мс на кадр). Но змея должна двигаться реже (каждые 80ms по умолчанию). Используется `time.monotonic()` — монотонные часы, которые не зависят от изменения системного времени.

---

### 9. Управление без PyGame (бенчмарк)

В бенчмарк-режиме (`-b N`) окно Pygame НЕ открывается. Вместо `Game.loop()` вызывается `run_bench()`, который напрямую управляет объектом `Snake`:

```python
# Из bench.py
while not snake.is_stopped() and steps < max_steps:
    snake.move(agent.next_direc(snake))
    steps += 1
```

---

<INDEX>
{
  "/home/jk/mSr/heRmm/snake/src/game.py": {
    "summary": "Класс Game: инициализация Pygame, главный цикл, обработка ввода (W/A/S/D, SPACE, R, ESC), отрисовка змеи/еды через pygame.draw.rect, запись кадров в GIF через PIL.",
    "libraries": ["pygame", "PIL (Pillow)"],
    "key_pygame_features": ["pygame.init()", "pygame.display.set_mode()", "pygame.event.get()", "pygame.time.Clock.tick()", "pygame.draw.rect()", "pygame.Surface.fill()", "pygame.display.flip()", "pygame.image.tobytes()", "pygame.Surface.get_size()", "pygame.NOFRAME"]
  },
  "/home/jk/mSr/heRmm/snake/src/snake.py": {
    "summary": "Класс Snake: чистая игровая логика (без графики), движение, столкновения, состояния (WALKING/DEAD/FULL), генерация еды.",
    "libraries": ["random", "time", "collections.deque", "enum"]
  }
}
</INDEX>
