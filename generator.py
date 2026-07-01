"""Maze generation module.

This module exposes the :class:`MazeGenerator` class, which builds a maze
on a rectangular grid using a randomized depth-first search (recursive
backtracker) algorithm, optionally adds extra loops to make it an
"imperfect" maze, embeds a visible "42" pattern made of fully closed
cells, and can compute the shortest path between an entry and an exit.

Wall encoding (per cell), matching the output-file specification:
    bit 0 (1)  -> North wall closed
    bit 1 (2)  -> East  wall closed
    bit 2 (4)  -> South wall closed
    bit 3 (8)  -> West  wall closed
A bit set to 1 means the wall is CLOSED, 0 means OPEN (passable).
"""

import random
from typing import Optional

NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8
ALL_WALLS = NORTH | EAST | SOUTH | WEST

_DIRECTIONS: dict[str, tuple[int, int, int, int]] = {
    "N": (0, -1, NORTH, SOUTH),
    "S": (0, 1, SOUTH, NORTH),
    "E": (1, 0, EAST, WEST),
    "W": (-1, 0, WEST, EAST),
}

_DIGIT_4 = [
    [1, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 0, 1],
    [0, 0, 1],
]
_DIGIT_2 = [
    [1, 1, 1],
    [0, 0, 1],
    [1, 1, 1],
    [1, 0, 0],
    [1, 1, 1],
]
 


class MazeGenerator:
    """Generate, store and solve a rectangular maze.

    The maze is represented internally as a 2D grid of integers, one per
    cell, where each integer is a bitmask of the four cardinal walls
    (see module docstring for the bit layout).

    Attributes:
        width: Number of cells horizontally.
        height: Number of cells vertically.
        seed: Seed used for the random generator (``None`` means a
            non-reproducible random maze).
        perfect: Whether the generated maze must have exactly one path
            between any two cells (a spanning tree, no loops).
    """
    def __init__(
            self,
            width: int,
            height: int,
            seed: Optional[int] = None,
            perfect: bool = True,
    ) -> None:
        """Initialize the generator.

        Args:
            width: Maze width in cells. Must be strictly positive.
            height: Maze height in cells. Must be strictly positive.
            seed: Optional seed for reproducible generation.
            perfect: If True, the maze will be a perfect maze (single
                unique path between any two cells). If False, extra
                passages (loops) may be added.

        Raises:
            ValueError: If width or height are not strictly positive.
        """
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be strictly positive")

        self.width = width
        self.height = height
        self.seed = seed
        self.perfect = perfect

        self._rng = random.Random(seed)
        self._grid: list[list[int]] = [
            [ALL_WALLS for _ in range(width)] for _ in range(height)
        ]
        self._blocked: set[tuple[int, int]] = set()
        self._entry: tuple[int, int] = (0, 0)
        self._exit: tuple[int, int] = (0, 0)
        self._solution: list[str] = []
        self._generated = False


    def generate(
        self,
        entry: tuple[int, int],
        exit: tuple[int, int],
    ) -> None:
        """Generate the maze structure.

        Builds the "42" pattern (if the maze is large enough), carves a
        spanning tree with a randomized depth-first search, optionally
        adds extra loops when ``self.perfect`` is False, and computes the
        shortest solution path from ``entry`` to ``exit``.

        Args:
            entry: (x, y) coordinates of the entry cell.
            exit: (x, y) coordinates of the exit cell.

        Raises:
            ValueError: If entry/exit are out of bounds, identical, or
                fall inside the reserved "42" pattern area.
        """
        self._validate_point(entry, "entry")
        self._validate_point(exit, "exit")
        if entry == exit:
            raise ValueError("entry and exit must be different cells")

        self._entry = entry
        self._exit = exit
        self._grid = [
            [ALL_WALLS for _ in range(self.width)] for _ in range(self.height)
        ]

        self._blocked = self._compute_pattern_cells()
        if entry in self._blocked or exit in self._blocked:
            raise ValueError("entry or exit falls inside the '42' pattern")

        self._carve_spanning_tree(entry)

        if not self.perfect:
            self._add_loops()

        self._solution = self._compute_shortest_path(entry, exit)
        self._generated = True

    def get_grid(self) -> list[list[int]]:
        """Return the raw maze grid.

        Returns:
            A list indexed as ``grid[y][x]``, where each value is the
            wall bitmask of that cell (see module docstring).
        """
        return self._grid

    def cell_to_hex(self, x: int, y: int) -> str:
        """Return the single hexadecimal digit representing a cell.

        Args:
            x: Column index of the cell.
            y: Row index of the cell.

        Returns:
            A single uppercase hexadecimal character encoding which
            walls of the cell are closed.
        """
        return format(self._grid[y][x], "X")

    def get_solution(self) -> list[str]:
        """Return the shortest path from entry to exit.

        Returns:
            A list of single-letter moves ('N', 'S', 'E', 'W') to walk
            from the entry cell to the exit cell.
        """
        return self._solution


    def _validate_point(self, point: tuple[int, int], name: str) -> None:
        """Validate that a coordinate lies within the maze bounds.

        Args:
            point: (x, y) coordinates to validate.
            name: Human readable name used in the error message.

        Raises:
            ValueError: If the point is outside the maze bounds.
        """
        x, y = point
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"{name} {point} is out of maze bounds")


    def _compute_pattern_cells(self) -> set[tuple[int, int]]:
        """Compute the set of cells forming the visible "42" pattern.

        The pattern is a 5-row by 7-column block ("4", one empty column,
        "2"), centered in the maze with a margin from the outer border
        so it never touches it. If the maze is too small to fit the
        pattern with margin, the pattern is skipped and a message is
        printed, as allowed by the subject.

        Returns:
            A set of (x, y) cell coordinates that must stay fully
            closed (all four walls) and excluded from the carved paths.
        """
        pattern_w, pattern_h = 7, 5
        margin = 1
        if self.width < pattern_w + 2 * margin or (
            self.height < pattern_h + 2 * margin
        ):
            print("Warning: maze too small to draw the '42' pattern, "
                  "skipping it.")
            return set()

        offset_x = (self.width - pattern_w) // 2
        offset_y = (self.height - pattern_h) // 2

        blocked: set[tuple[int, int]] = set()
        for row in range(pattern_h):
            for col in range(3):
                if _DIGIT_4[row][col]:
                    blocked.add((offset_x + col, offset_y + row))
                if _DIGIT_2[row][col]:
                    blocked.add((offset_x + 4 + col, offset_y + row))

        for (x, y) in blocked:
            self._grid[y][x] = ALL_WALLS

        return blocked


    def _neighbors(self, x: int, y: int) -> list[tuple[int, int, str]]:
        """List in-bounds, non-blocked neighbors of a cell.

        Args:
            x: Column index of the cell.
            y: Row index of the cell.

        Returns:
            A list of (nx, ny, direction) tuples for every neighboring
            cell that exists within the maze and is not part of the
            reserved "42" pattern.
        """
        result = []
        for direction, (dx, dy, _, _) in _DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < self.width
                and 0 <= ny < self.height
                and (nx, ny) not in self._blocked
            ):
                result.append((nx, ny, direction))
        return result

    def _remove_wall(
        self, x: int, y: int, nx: int, ny: int, direction: str
    ) -> None:
        """Open the wall between two adjacent cells.

        Clears the matching bit on both cells so the two sides stay
        coherent (a wall is either closed on both cells or open on
        both cells).

        Args:
            x: Column index of the first cell.
            y: Row index of the first cell.
            nx: Column index of the neighboring cell.
            ny: Row index of the neighboring cell.
            direction: Direction ('N', 'S', 'E', 'W') from (x, y) to
                (nx, ny).
        """
        _, _, this_bit, opposite_bit = _DIRECTIONS[direction]
        self._grid[y][x] &= ~this_bit
        self._grid[ny][nx] &= ~opposite_bit

    def _carve_spanning_tree(self, start: tuple[int, int]) -> None:
        """Carve a perfect maze using a randomized depth-first search.

        This is the classic "recursive backtracker" algorithm,
        implemented with an explicit stack (instead of real recursion)
        to avoid Python's recursion-depth limit on large mazes:

        1. Start at ``start`` and mark it visited.
        2. Look at the current cell's unvisited neighbors.
        3. If there is at least one, pick one at random, knock down the
           wall between the two cells, mark it visited, and push it on
           the stack (it becomes the new current cell).
        4. If there is none, pop the stack (backtrack) to the previous
           cell and repeat from step 2.
        5. Stop when the stack is empty.

        Because a wall is only ever removed once, between two cells
        that are not yet connected, the result is a spanning tree: there
        is exactly one path between any two carvable cells.

        Args:
            start: (x, y) cell to start carving from.
        """
        visited: set[tuple[int, int]] = {start}
        stack: list[tuple[int, int]] = [start]

        while stack:
            x, y = stack[-1]
            candidates = [
                n for n in self._neighbors(x, y) if (n[0], n[1]) not in visited
            ]
            if not candidates:
                stack.pop()
                continue

            nx, ny, direction = self._rng.choice(candidates)
            self._remove_wall(x, y, nx, ny, direction)
            visited.add((nx, ny))
            stack.append((nx, ny))


    def _creates_open_3x3(self, x: int, y: int) -> bool:
        """Check whether any 3x3 block touching (x, y) is fully open.

        A 3x3 block of cells is considered "fully open" when every
        internal wall between adjacent cells inside the block is open,
        which would form a forbidden open area wider than 2 cells.

        Args:
            x: Column index of a cell that was just modified.
            y: Row index of a cell that was just modified.

        Returns:
            True if opening the last wall created a fully open 3x3
            area, False otherwise.
        """
        for top_x in range(x - 2, x + 1):
            for top_y in range(y - 2, y + 1):
                if not (
                    0 <= top_x <= self.width - 3
                    and 0 <= top_y <= self.height - 3
                ):
                    continue
                if self._block_is_fully_open(top_x, top_y):
                    return True
        return False

    def _block_is_fully_open(self, top_x: int, top_y: int) -> bool:
        """Check whether a 3x3 block starting at (top_x, top_y) is open.

        Args:
            top_x: Column index of the block's top-left cell.
            top_y: Row index of the block's top-left cell.

        Returns:
            True if all 9 cells of the block exist, are not part of the
            "42" pattern, and every internal wall between them is open.
        """
        cells = [
            (top_x + dx, top_y + dy) for dy in range(3) for dx in range(3)
        ]
        if any(c in self._blocked for c in cells):
            return False

        for dy in range(3):
            for dx in range(2):
                x1, y1 = top_x + dx, top_y + dy
                if self._grid[y1][x1] & EAST:
                    return False

        for dx in range(3):
            for dy in range(2):
                x1, y1 = top_x + dx, top_y + dy
                if self._grid[y1][x1] & SOUTH:
                    return False

        return True

    def _add_loops(self, extra_ratio: float = 0.15) -> None:
        """Add extra open passages to turn the perfect maze into one
        with loops (multiple possible paths), while respecting the
        "no corridor wider than 2 cells" constraint.

        Args:
            extra_ratio: Probability of trying to open each remaining
                closed internal wall.
        """
        candidates: list[tuple[int, int, int, int, str]] = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in self._blocked:
                    continue
                for nx, ny, direction in self._neighbors(x, y):
                    _, _, this_bit, _ = _DIRECTIONS[direction]
                    if self._grid[y][x] & this_bit:
                        candidates.append((x, y, nx, ny, direction))

        self._rng.shuffle(candidates)

        for x, y, nx, ny, direction in candidates:
            if self._rng.random() > extra_ratio:
                continue
            _, _, this_bit, opposite_bit = _DIRECTIONS[direction]
            if not (self._grid[y][x] & this_bit):
                continue 

            self._remove_wall(x, y, nx, ny, direction)
            if self._creates_open_3x3(x, y) or self._creates_open_3x3(nx, ny):
                self._grid[y][x] |= this_bit
                self._grid[ny][nx] |= opposite_bit
