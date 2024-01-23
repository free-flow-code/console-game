import curses
import asyncio
import argparse
from random import randint, choice
from curses_tools import draw_frame, read_controls, get_frame_size
from itertools import cycle

COROUTINES = []


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


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 2)
    column = min(column, columns_number - 2)

    row = 1

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


async def fill_orbit_with_garbage(canvas, width_window, garbage_frames):
    while True:
        global COROUTINES
        garbage_frame = choice(garbage_frames)
        frame_rows, frame_columns = get_frame_size(garbage_frame)
        column = randint(1, width_window - frame_columns)
        garbage_coroutine = fly_garbage(canvas, column, garbage_frame)
        COROUTINES.append(garbage_coroutine)
        for _ in range(15):
            await asyncio.sleep(0)


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
    garbage_files = [
        'duck.txt',
        'hubble.txt',
        'lamp.txt',
        'trash_large.txt',
        'trash_small.txt',
        'trash_xl.txt'
    ]
    tic_timeout = 0.1
    stars = '+*.:'
    height_indent = 2
    width_indent = 2
    offset_tics = randint(1, 20)
    global COROUTINES

    with (open('animations/rocket_frame_1.txt', 'r') as file1,
          open('animations/rocket_frame_2.txt', 'r') as file2):
        rocket_frame1 = file1.read()
        rocket_frame2 = file2.read()
        rocket_frames = [rocket_frame1, rocket_frame1, rocket_frame2, rocket_frame2]
    fire_coroutine = fire(canvas, height_window / 2, width_window / 2)
    COROUTINES = [
        blink(
            canvas,
            randint(1, height_window - height_indent),
            randint(1, width_window - width_indent),
            offset_tics,
            choice(stars)
        ) for _ in range(0, number_stars)
    ]
    COROUTINES.extend([fire_coroutine, animate_spaceship(canvas, height_window / 2, width_window / 2, rocket_frames)])

    garbage_frames = []
    for file in garbage_files:
        with open(f'animations/{file}', 'r') as garbage_file:
            frame = garbage_file.read()
        garbage_frames.append(frame)
    COROUTINES.append(fill_orbit_with_garbage(canvas, width_window, garbage_frames))

    while True:
        for coroutine in COROUTINES.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)
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
