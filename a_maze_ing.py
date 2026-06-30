import sys
from config import read_configuration_file, validate_configurations
from mazegen.generator import MazeGenerator


def write_output(
        mg: MazeGenerator,
        path: str,
        entry: tuple[int, int],
        exit_: tuple[int, int]
        ) -> None:
    try:
        with open(path, 'w') as f:
            for y in range(mg.height):
                row = ''
                for x in range(mg.width):
                    row += mg.cell_to_hex(x, y)
                f.write(row + '\n')

            f.write('\n')
            f.write(f"{entry[0]},{entry[1]}\n")
            f.write(f"{exit_[0]},{exit_[1]}\n")
            f.write(''.join(mg.get_solution()) + '\n')

    except OSError as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


def display_maze(
    mg: MazeGenerator,
    entry: tuple[int, int],
    exit_: tuple[int, int],
    show_path: bool = False,
    wall_char: str = '█'
) -> None:
    EAST = 2
    SOUTH = 4

    grid = mg.get_grid()
    width = mg.width
    height = mg.height

    path_cells: set[tuple[int, int]] = set()
    if show_path:
        x, y = entry
        path_cells.add((x, y))
        dir_move = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
        for step in mg.get_solution():
            dx, dy = dir_move[step]
            x, y = x + dx, y + dy
            path_cells.add((x, y))

    top = wall_char * (width * 2 + 1)
    print(top)

    for y in range(height):
        row = wall_char
        for x in range(width):
            cell = grid[y][x]
            if (x, y) == entry:
                content = 'E'
            elif (x, y) == exit_:
                content = 'X'
            elif (x, y) in path_cells:
                content = '·'
            else:
                content = ' '
            row += content
            row += wall_char if (cell & EAST) else ' '
        print(row)

        bottom = wall_char
        for x in range(width):
            cell = grid[y][x]
            bottom += wall_char if (cell & SOUTH) else ' '
            bottom += wall_char
        print(bottom)


def show_menu() -> str:
    print("\n=== A-Maze-ing ===")
    print("1. Re-generate a new maze")
    print("2. Show/Hide path from entry to exit")
    print("3. Change wall character")
    print("4. Quit")
    try:
        return input("Choice? (1-4): ").strip()
    except EOFError:
        return '4'


def safe_generate(
    width: int,
    height: int,
    seed: int | None,
    perfect: bool,
    entry: tuple[int, int],
    exit_: tuple[int, int]
) -> MazeGenerator:
    try:
        mg = MazeGenerator(width, height, seed=seed, perfect=perfect)
        mg.generate(entry=entry, exit=exit_)
    except ValueError as e:
        print(f"Error: cannot generate maze: {e}")
        sys.exit(1)
    return mg


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt")
        sys.exit(1)

    try:
        raw_config = read_configuration_file(sys.argv[1])
        cfg = validate_configurations(raw_config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    width = cfg["width"]
    height = cfg["height"]
    entry = cfg["entry"]
    exit_ = cfg["exit"]
    output = cfg["output_file"]
    perfect = cfg["perfect"]
    seed = cfg["seed"]

    mg = safe_generate(width, height, seed, perfect, entry, exit_)
    write_output(mg, output, entry, exit_)

    show_path = False
    wall_char = '█'
    current_seed = seed

    while True:
        display_maze(mg, entry, exit_,
                     show_path=show_path,
                     wall_char=wall_char)

        choice = show_menu()

        if choice == '1':
            if current_seed is not None:
                current_seed += 1
            mg = safe_generate(
                width, height, current_seed, perfect, entry, exit_
            )
            write_output(mg, output, entry, exit_)
            show_path = False

        elif choice == '2':
            show_path = not show_path

        elif choice == '3':
            try:
                wall_char = input("Enter wall character: ").strip() or '█'
            except EOFError:
                pass

        elif choice == '4':
            print("Goodbye!")
            break

        else:
            print("Invalid choice, try again.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
