from typing import Any


def read_configuration_file(filename: str) -> dict[str, str]:
    configurations = {}
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" not in line:
                    raise ValueError("invalid line")
                key, value = line.split("=", 1)
                configurations[key.strip()] = value.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"{filename} not found")
    return configurations


def valid_pos_int(config: dict[str, str], key: str) -> int:
    try:
        value = int(config[key])
    except ValueError:
        raise ValueError(f"{key} must be a number")
    if value <= 0:
        raise ValueError(f"{key} must be greater than 0")
    return value


def validate_coordinates(
    config: dict[str, str], key: str, width: int, height: int
) -> tuple[int, int]:
    try:
        x, y = map(int, config[key].split(","))
    except ValueError:
        raise ValueError(f"{key} must be x,y")
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(f"{key} out of bounds")
    return (x, y)


def validate_perfect(config: dict[str, str]) -> bool:
    value = config["PERFECT"]
    if value not in ("True", "False"):
        raise ValueError("PERFECT must be True or False")
    return value == "True"


def validate_configurations(config: dict[str, str]) -> dict[str, Any]:
    mandatory_keys = [
        "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"
    ]
    for key in mandatory_keys:
        if key not in config:
            raise ValueError(f"missing {key}")

    width = valid_pos_int(config, "WIDTH")
    height = valid_pos_int(config, "HEIGHT")
    entry = validate_coordinates(config, "ENTRY", width, height)
    exit_point = validate_coordinates(config, "EXIT", width, height)
    if entry == exit_point:
        raise ValueError("ENTRY and EXIT must be different")
    perfect = validate_perfect(config)

    seed = None
    if "SEED" in config:
        try:
            seed = int(config["SEED"])
        except ValueError:
            raise ValueError("SEED must be an integer")

    return {
        "width": width,
        "height": height,
        "entry": entry,
        "exit": exit_point,
        "output_file": config["OUTPUT_FILE"],
        "perfect": perfect,
        "seed": seed,
    }
