import curses
import asyncio
import argparse
from random import randint, choice
from curses_tools import draw_frame, read_controls, get_frame_size
from game_scenario import PHRASES, get_garbage_delay_tics
from obstacles import Obstacle
from physics import update_speed
from explosion import explode
from itertools import cycle

COROUTINES = []
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISIONS = []
YEAR = 1957


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


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def show_game_over(canvas, height_window, width_window):
    with open('animations/game_over.txt', 'r') as file:
        game_over_frame = file.read()
    game_over_frame_rows, game_over_frame_columns = get_frame_size(game_over_frame)
    while True:
        draw_frame(
            canvas,
            height_window // 2 - game_over_frame_rows // 2,
            width_window // 2 - game_over_frame_columns // 2,
            game_over_frame
        )
        await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()
    frame_rows, frame_columns = get_frame_size(garbage_frame)

    column = max(column, 2)
    column = min(column, columns_number - frame_columns - 1)

    row = 1
    global OBSTACLES, COROUTINES, OBSTACLES_IN_LAST_COLLISIONS

    new_obstacle = Obstacle(row, column, frame_rows, frame_columns)
    OBSTACLES.append(new_obstacle)

    try:
        while row < rows_number:
            if new_obstacle in OBSTACLES_IN_LAST_COLLISIONS:
                OBSTACLES_IN_LAST_COLLISIONS.remove(new_obstacle)
                await explode(canvas, row + frame_rows // 2, column + frame_columns // 2)
                return
            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
            new_obstacle.row = row
    finally:
        OBSTACLES.remove(new_obstacle)


async def fill_orbit_with_garbage(canvas, width_window, garbage_frames):
    while True:
        global YEAR
        delay_tics = get_garbage_delay_tics(YEAR)
        if delay_tics:
            global COROUTINES
            garbage_frame = choice(garbage_frames)
            column = randint(1, width_window)
            garbage_coroutine = fly_garbage(canvas, column, garbage_frame)
            COROUTINES.append(garbage_coroutine)
            await sleep(delay_tics)
        await asyncio.sleep(0)


async def fire(canvas, start_row, start_column, rows_speed=-2, columns_speed=0):
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
    global OBSTACLES, OBSTACLES_IN_LAST_COLLISIONS

    while 1 < row < max_row and 0 < column < max_column:
        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column):
                OBSTACLES_IN_LAST_COLLISIONS.append(obstacle)
                return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def run_spaceship(canvas, row, column):
    global COROUTINES
    COROUTINES.append(fire(canvas, row, column + 2))


async def animate_spaceship(canvas, row, column, rocket_frames):
    rocket_frames = cycle(rocket_frames)
    row_speed = column_speed = 0
    global OBSTACLES, COROUTINES

    while True:
        rocket_frame = next(rocket_frames)
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        frame_rows, frame_columns = get_frame_size(rocket_frame)
        height_window, width_window = curses.window.getmaxyx(canvas)

        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column, frame_rows, frame_columns):
                await explode(canvas, row + frame_rows // 2, column + frame_columns // 2)
                COROUTINES.append(show_game_over(canvas, height_window, width_window))
                return

        draw_frame(canvas, row, column, rocket_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, rocket_frame, negative=True)

        global YEAR
        if space_pressed and YEAR >= 2020:
            COROUTINES.append(fire(canvas, row, column + 2))

        row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)
        row += row_speed
        column += column_speed

        row = min(max(row + rows_direction, 1), height_window - frame_rows - 1)
        column = min(max(column + columns_direction, 1), width_window - frame_columns - 1)


async def blink(canvas, row, column, offset_tics, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(offset_tics)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def display_year(canvas, width_window):
    global YEAR, PHRASES
    len_year_string = 60
    phrase = ''
    derwin = canvas.derwin(1, len_year_string, 0, width_window - len_year_string)
    while True:
        if YEAR in PHRASES.keys():
            phrase = PHRASES[YEAR]
        derwin.clear()
        derwin.addstr(0, 0, f'YEAR {YEAR} | {phrase}', curses.A_BOLD)
        derwin.refresh()
        await asyncio.sleep(0)


async def increase_year():
    global YEAR
    while True:
        await sleep(15)
        YEAR += 1


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

    COROUTINES = [
        blink(
            canvas,
            randint(1, height_window - height_indent),
            randint(1, width_window - width_indent),
            offset_tics,
            choice(stars)
        ) for _ in range(0, number_stars)
    ]
    COROUTINES.append(animate_spaceship(canvas, height_window // 2, width_window // 2, rocket_frames))

    garbage_frames = []
    for file in garbage_files:
        with open(f'animations/{file}', 'r') as garbage_file:
            frame = garbage_file.read()
        garbage_frames.append(frame)

    COROUTINES.extend(
        [
            fill_orbit_with_garbage(canvas, width_window, garbage_frames),
            increase_year(),
            display_year(canvas, width_window)
        ]
    )

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
