import sys
from pathlib import Path

from tools.feature_catalog import InvalidFeatureError, feature_files, parse_feature


def invalid_features(root: Path) -> list[str]:
    return [problem for path in feature_files(root) if (problem := _problem_in(path))]


def _problem_in(path: Path) -> str | None:
    try:
        parse_feature(path)
    except InvalidFeatureError as error:
        return str(error)
    return None


def main(arguments: list[str]) -> int:
    problems = invalid_features(Path(arguments[0]))
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
