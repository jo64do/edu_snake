import argparse

from src.bench import run_bench
from src.game import Game
from src.mode import Mode


# Точка входа в приложение: сначала читаются параметры запуска,
# затем выбирается режим игры и выполняется либо игровой цикл,
# либо запуск бенчмарка.
def main() -> None:
    # Получаем аргументы командной строки из терминала.
    args = parse_args()

    # Преобразуем строковый режим в перечисление Mode.
    mode = Mode[args.mode.upper()]

    # Если количество раундов для бенчмарка не задано,
    # запускаем обычную игру; иначе запускаем бенчмарк.
    if args.bench_rounds is None:
        game = Game(mode, args.move_freq, args.show_grid, args.record_frames, args.seed)
        game.loop()
    else:
        run_bench(mode, args.bench_rounds, args.seed)


# Настройка и разбор аргументов командной строки.
def parse_args() -> argparse.Namespace:
    # Создаём объект для обработки переданных параметров.
    parser = argparse.ArgumentParser()

    # Выбор режима игры: человек, графический агент или RL-агент.
    # За что отвечает каждый флаг (-m, -f, -g, -r, -s, -b):
    #   -m: режим игры
    #   -f: частота обновления движения змейки
    #   -g: показывать сетку
    #   -r: записывать кадры
    #   -s: зерно генератора случайных чисел
    #   -b: количество раундов для бенчмарка
    parser.add_argument(
        "-m",
        choices=["human", "graph", "rl"],
        default="graph",
        help="set game mode (default: graph)",
        type=str,
        dest="mode",
    )

    # Частота обновления движения змейки в миллисекундах.
    parser.add_argument(
        "-f",
        metavar="<freq>",
        default=80,
        help="set snake move frequency in milliseconds (default: 80)",
        type=int,
        dest="move_freq",
    )

    # Показывать ли сетку на игровом поле.
    parser.add_argument(
        "-g",
        help="show grid lines",
        action="store_true",
        dest="show_grid",
    )

    # Включить запись игрового процесса в видео/кадры.
    parser.add_argument(
        "-r",
        help="record game play",
        action="store_true",
        dest="record_frames",
    )

    # Значение зерна генератора случайных чисел для воспроизводимости.
    parser.add_argument(
        "-s",
        metavar="<seed>",
        default=None,
        help="set random seed for food generation",
        type=int,
        dest="seed",
    )

    # Количество раундов для запуска бенчмарка.
    parser.add_argument(
        "-b",
        metavar="<rounds>",
        default=None,
        help="run benchmark for the given number of rounds",
        type=int,
        dest="bench_rounds",
    )

    # Возвращаем собранные значения аргументов.
    return parser.parse_args()


# Защита от автоматического запуска при импорте файла.
if __name__ == "__main__":
    main()
