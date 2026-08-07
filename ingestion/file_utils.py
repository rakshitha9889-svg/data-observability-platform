from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ENTITY_ORDER = {
    "customers": 1,
    "products": 2,
    "orders": 3,
    "order_items": 4,
    "payments": 5,
    "shipments": 6,
    "inventory": 7,
}


TRANSACTIONAL_FILENAME_PATTERN = re.compile(
    r"^(orders|order_items|payments|shipments|inventory)"
    r"_(\d{4}-\d{2}-\d{2})\.csv$"
)


MASTER_FILENAME_PATTERN = re.compile(
    r"^(customers|products)\.csv$"
)


@dataclass(frozen=True)
class SourceFile:
    path: Path
    entity_name: str
    batch_date: date | None
    checksum: str
    size_bytes: int


class InvalidFilenameError(ValueError):
    pass


def calculate_file_checksum(file_path: Path) -> str:
    sha256 = hashlib.sha256()

    with file_path.open("rb") as source_file:
        for block in iter(
            lambda: source_file.read(1024 * 1024),
            b"",
        ):
            sha256.update(block)

    return sha256.hexdigest()


def parse_source_filename(
    file_path: Path,
) -> tuple[str, date | None]:
    master_match = MASTER_FILENAME_PATTERN.fullmatch(
        file_path.name
    )

    if master_match:
        return master_match.group(1), None

    transactional_match = (
        TRANSACTIONAL_FILENAME_PATTERN.fullmatch(file_path.name)
    )

    if transactional_match:
        entity_name = transactional_match.group(1)

        batch_date = datetime.strptime(
            transactional_match.group(2),
            "%Y-%m-%d",
        ).date()

        return entity_name, batch_date

    raise InvalidFilenameError(
        f"Unsupported filename: {file_path.name}"
    )


def discover_source_files(
    incoming_directory: Path,
) -> tuple[list[SourceFile], list[Path]]:
    supported_files = []
    invalid_files = []

    for file_path in incoming_directory.iterdir():
        if not file_path.is_file():
            continue

        if file_path.name == ".gitkeep":
            continue

        try:
            entity_name, batch_date = parse_source_filename(
                file_path
            )
        except InvalidFilenameError:
            invalid_files.append(file_path)
            continue

        supported_files.append(
            SourceFile(
                path=file_path,
                entity_name=entity_name,
                batch_date=batch_date,
                checksum=calculate_file_checksum(file_path),
                size_bytes=file_path.stat().st_size,
            )
        )

    supported_files.sort(
        key=lambda source_file: (
            ENTITY_ORDER[source_file.entity_name],
            source_file.path.name,
        )
    )

    return supported_files, invalid_files


def archive_source_file(
    source_file: SourceFile,
    archive_directory: Path,
) -> Path:
    if source_file.batch_date:
        destination_directory = (
            archive_directory
            / source_file.entity_name
            / source_file.batch_date.isoformat()
        )
    else:
        destination_directory = (
            archive_directory
            / source_file.entity_name
            / "master"
        )

    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_path = destination_directory / source_file.path.name

    if destination_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        destination_path = destination_directory / (
            f"{source_file.path.stem}_{timestamp}"
            f"{source_file.path.suffix}"
        )

    shutil.move(
        str(source_file.path),
        str(destination_path),
    )

    return destination_path


def move_rejected_file(
    file_path: Path,
    rejected_directory: Path,
) -> Path:
    destination_directory = (
        rejected_directory
        / datetime.now().strftime("%Y-%m-%d")
    )

    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_path = destination_directory / file_path.name

    if destination_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        destination_path = destination_directory / (
            f"{file_path.stem}_{timestamp}{file_path.suffix}"
        )

    shutil.move(
        str(file_path),
        str(destination_path),
    )

    return destination_path