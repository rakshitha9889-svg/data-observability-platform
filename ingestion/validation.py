from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "customers": [
        "customer_id",
        "customer_name",
        "email",
        "country",
        "registration_date",
        "status",
    ],
    "products": [
        "product_id",
        "product_name",
        "category",
        "supplier_id",
        "unit_price",
        "active",
    ],
    "orders": [
        "order_id",
        "customer_id",
        "order_date",
        "status",
        "currency",
        "order_total",
    ],
    "order_items": [
        "item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount",
        "line_total",
    ],
    "payments": [
        "payment_id",
        "order_id",
        "payment_date",
        "amount",
        "status",
        "method",
    ],
    "shipments": [
        "shipment_id",
        "order_id",
        "expected_delivery_date",
        "actual_delivery_date",
        "status",
        "warehouse_id",
    ],
    "inventory": [
        "inventory_date",
        "warehouse_id",
        "product_id",
        "stock_quantity",
        "reorder_level",
    ],
}


PRIMARY_KEY_COLUMNS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "item_id",
    "payments": "payment_id",
    "shipments": "shipment_id",
}


ACCEPTED_VALUES = {
    "customers": {
        "status": {
            "active",
            "inactive",
            "suspended",
        }
    },
    "orders": {
        "status": {
            "completed",
            "shipped",
            "cancelled",
            "processing",
        },
        "currency": {
            "EUR",
        },
    },
    "payments": {
        "status": {
            "successful",
            "failed",
            "pending",
            "refunded",
        },
        "method": {
            "credit_card",
            "paypal",
            "bank_transfer",
            "gift_card",
        },
    },
    "shipments": {
        "status": {
            "delivered",
            "in_transit",
            "delayed",
            "cancelled",
        }
    },
}


DATE_COLUMNS = {
    "customers": [
        "registration_date",
    ],
    "orders": [
        "order_date",
    ],
    "payments": [
        "payment_date",
    ],
    "shipments": [
        "expected_delivery_date",
        "actual_delivery_date",
    ],
    "inventory": [
        "inventory_date",
    ],
}


NUMERIC_COLUMNS = {
    "products": [
        "unit_price",
    ],
    "orders": [
        "order_total",
    ],
    "order_items": [
        "quantity",
        "unit_price",
        "discount",
        "line_total",
    ],
    "payments": [
        "amount",
    ],
    "inventory": [
        "stock_quantity",
        "reorder_level",
    ],
}


NULLABLE_COLUMNS = {
    "shipments": {
        "actual_delivery_date",
    }
}


@dataclass
class ValidationFailure:
    row_number: int
    failed_rule: str
    failure_type: str
    failure_reason: str
    record_data: dict[str, Any]


@dataclass
class ValidationResult:
    valid_records: pd.DataFrame
    invalid_records: list[ValidationFailure]
    received_count: int

    @property
    def valid_count(self) -> int:
        return len(self.valid_records)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_records)


class FileSchemaError(ValueError):
    pass


def validate_file_schema(
    dataframe: pd.DataFrame,
    entity_name: str,
) -> None:
    expected_columns = REQUIRED_COLUMNS[entity_name]
    received_columns = dataframe.columns.tolist()

    missing_columns = sorted(
        set(expected_columns) - set(received_columns)
    )

    unexpected_columns = sorted(
        set(received_columns) - set(expected_columns)
    )

    if missing_columns:
        raise FileSchemaError(
            f"Missing required columns for {entity_name}: "
            f"{missing_columns}"
        )

    if unexpected_columns:
        raise FileSchemaError(
            f"Unexpected columns for {entity_name}: "
            f"{unexpected_columns}"
        )


def normalize_boolean(value: Any) -> bool | None:
    if pd.isna(value):
        return None

    if isinstance(value, bool):
        return value

    normalized_value = str(value).strip().lower()

    if normalized_value in {"true", "1", "yes"}:
        return True

    if normalized_value in {"false", "0", "no"}:
        return False

    return None


def clean_record_for_json(
    record: dict[str, Any],
) -> dict[str, Any]:
    cleaned_record = {}

    for column_name, value in record.items():
        if pd.isna(value):
            cleaned_record[column_name] = None
        elif isinstance(value, pd.Timestamp):
            cleaned_record[column_name] = value.isoformat()
        elif hasattr(value, "item"):
            cleaned_record[column_name] = value.item()
        else:
            cleaned_record[column_name] = value

    return cleaned_record


def validate_dataframe(
    dataframe: pd.DataFrame,
    entity_name: str,
) -> ValidationResult:
    validate_file_schema(dataframe, entity_name)

    working_dataframe = dataframe.copy()

    working_dataframe["_source_row_number"] = (
        working_dataframe.index + 2
    )

    failures_by_index: dict[int, list[str]] = {}

    def add_failure(
        row_index: int,
        message: str,
    ) -> None:
        failures_by_index.setdefault(row_index, []).append(message)

    nullable_columns = NULLABLE_COLUMNS.get(
        entity_name,
        set(),
    )

    for column_name in REQUIRED_COLUMNS[entity_name]:
        if column_name in nullable_columns:
            continue

        null_mask = (
            working_dataframe[column_name].isna()
            | working_dataframe[column_name]
            .astype(str)
            .str.strip()
            .eq("")
        )

        for row_index in working_dataframe.index[null_mask]:
            add_failure(
                row_index,
                f"{column_name} must not be null or empty",
            )

    primary_key_column = PRIMARY_KEY_COLUMNS.get(entity_name)

    if primary_key_column:
        duplicate_mask = working_dataframe[
            primary_key_column
        ].duplicated(keep=False)

        for row_index in working_dataframe.index[duplicate_mask]:
            add_failure(
                row_index,
                f"{primary_key_column} must be unique "
                "within the source file",
            )

    for column_name in DATE_COLUMNS.get(entity_name, []):
        original_values = working_dataframe[column_name].copy()

        working_dataframe[column_name] = pd.to_datetime(
            working_dataframe[column_name],
            errors="coerce",
        )

        invalid_date_mask = (
            original_values.notna()
            & original_values.astype(str).str.strip().ne("")
            & working_dataframe[column_name].isna()
        )

        for row_index in working_dataframe.index[
            invalid_date_mask
        ]:
            add_failure(
                row_index,
                f"{column_name} must contain a valid date",
            )

    for column_name in NUMERIC_COLUMNS.get(entity_name, []):
        original_values = working_dataframe[column_name].copy()

        working_dataframe[column_name] = pd.to_numeric(
            working_dataframe[column_name],
            errors="coerce",
        )

        invalid_numeric_mask = (
            original_values.notna()
            & original_values.astype(str).str.strip().ne("")
            & working_dataframe[column_name].isna()
        )

        for row_index in working_dataframe.index[
            invalid_numeric_mask
        ]:
            add_failure(
                row_index,
                f"{column_name} must contain a valid number",
            )

    for column_name, accepted_values in ACCEPTED_VALUES.get(
        entity_name,
        {},
    ).items():
        normalized_values = (
            working_dataframe[column_name]
            .astype("string")
            .str.strip()
        )

        working_dataframe[column_name] = normalized_values

        invalid_value_mask = (
            normalized_values.notna()
            & ~normalized_values.isin(accepted_values)
        )

        for row_index in working_dataframe.index[
            invalid_value_mask
        ]:
            add_failure(
                row_index,
                f"{column_name} contains an unsupported value: "
                f"{normalized_values.loc[row_index]}",
            )

    if entity_name == "products":
        normalized_active = working_dataframe["active"].apply(
            normalize_boolean
        )

        invalid_boolean_mask = normalized_active.isna()

        for row_index in working_dataframe.index[
            invalid_boolean_mask
        ]:
            add_failure(
                row_index,
                "active must be a valid boolean",
            )

        working_dataframe["active"] = normalized_active

    non_negative_rules = {
        "products": [
            "unit_price",
        ],
        "orders": [
            "order_total",
        ],
        "order_items": [
            "unit_price",
            "discount",
            "line_total",
        ],
        "payments": [
            "amount",
        ],
        "inventory": [
            "stock_quantity",
            "reorder_level",
        ],
    }

    for column_name in non_negative_rules.get(
        entity_name,
        [],
    ):
        negative_mask = (
            working_dataframe[column_name].notna()
            & (working_dataframe[column_name] < 0)
        )

        for row_index in working_dataframe.index[negative_mask]:
            add_failure(
                row_index,
                f"{column_name} must not be negative",
            )

    if entity_name == "order_items":
        invalid_quantity_mask = (
            working_dataframe["quantity"].notna()
            & (working_dataframe["quantity"] <= 0)
        )

        for row_index in working_dataframe.index[
            invalid_quantity_mask
        ]:
            add_failure(
                row_index,
                "quantity must be greater than zero",
            )

        invalid_discount_mask = (
            working_dataframe["discount"].notna()
            & (
                (working_dataframe["discount"] < 0)
                | (working_dataframe["discount"] > 1)
            )
        )

        for row_index in working_dataframe.index[
            invalid_discount_mask
        ]:
            add_failure(
                row_index,
                "discount must be between 0 and 1",
            )

    invalid_records = []

    for row_index, messages in failures_by_index.items():
        source_row_number = int(
            working_dataframe.loc[
                row_index,
                "_source_row_number",
            ]
        )

        original_record = dataframe.loc[row_index].to_dict()

        invalid_records.append(
            ValidationFailure(
                row_number=source_row_number,
                failed_rule="; ".join(messages),
                failure_type="record_validation",
                failure_reason="; ".join(messages),
                record_data=clean_record_for_json(
                    original_record
                ),
            )
        )

    invalid_indexes = set(failures_by_index)

    valid_records = working_dataframe.loc[
        ~working_dataframe.index.isin(invalid_indexes)
    ].copy()

    return ValidationResult(
        valid_records=valid_records,
        invalid_records=invalid_records,
        received_count=len(dataframe),
    )