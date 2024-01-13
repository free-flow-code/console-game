import curses
import asyncio
import argparse
from random import randint, choice
from curses_tools import draw_frame, read_controls, get_frame_size
from itertools import cycle


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Console wars. Simple game about space.'
    )
    parser.add_argument(
        'stars',
        help='number of stars in the background',
        type=int,
        nargs='?',
        default=50
    )
    return parser.parse_args()


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(canvas, row, column, rocket_frames):
    rocket_frames = cycle(rocket_frames)
    while True:
        rocket_frame = next(rocket_frames)
        draw_frame(canvas, row, column, rocket_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, rocket_frame, negative=True)

        rows_direction, columns_direction, _ = read_controls(canvas)
        row += rows_direction
        column += columns_direction
        frame_rows, frame_columns = get_frame_size(rocket_frame)
        height_window, width_window = curses.window.getmaxyx(canvas)

        row = min(max(row + rows_direction, 1), height_window - frame_rows - 1)
        column = min(max(column + columns_direction, 1), width_window - frame_columns - 1)


async def blink(canvas, row, column, offset_tics, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(offset_tics):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(0, 3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(0, 5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(0, 3):
            await asyncio.sleep(0)


async def draw(canvas, number_stars):
    height_window, width_window = curses.window.getmaxyx(canvas)
    tic_timeout = 0.1
    stars = '+*.:'
    height_indent = 2
    width_indent = 2
    offset_tics = randint(1, 20)
    with (open('animations/rocket_frame_1.txt', 'r') as file1,
          open('animations/rocket_frame_2.txt', 'r') as file2):
        rocket_frame1 = file1.read()
        rocket_frame2 = file2.read()
        rocket_frames = [rocket_frame1, rocket_frame2]
    fire_coroutine = fire(canvas, height_window / 2, width_window / 2)
    coroutines = [
        blink(
            canvas,
            randint(1, height_window - height_indent),
            randint(1, width_window - width_indent),
            offset_tics,
            choice(stars)
        ) for _ in range(0, number_stars)
    ]
    coroutines.extend([fire_coroutine, animate_spaceship(canvas, height_window / 2, width_window / 2, rocket_frames)])

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        await asyncio.sleep(tic_timeout)


def main(canvas):
    args = parse_arguments()
    number_stars = args.stars

    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    asyncio.run(draw(canvas, number_stars))


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(main)
