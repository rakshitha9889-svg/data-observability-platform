from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from faker import Faker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "generation_config.yaml"


def load_config(config_path: Path) -> dict:
    """Load the YAML generation configuration."""

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def initialize_random_generators(seed: int) -> Faker:
    """Set all random seeds so generation is reproducible."""

    random.seed(seed)
    np.random.seed(seed)

    faker = Faker()
    faker.seed_instance(seed)

    return faker


def create_output_directories(output_directory: Path) -> None:
    """Create one output folder for every source entity."""

    entities = [
        "customers",
        "products",
        "orders",
        "order_items",
        "payments",
        "shipments",
        "inventory",
    ]

    output_directory.mkdir(parents=True, exist_ok=True)

    for entity in entities:
        (output_directory / entity).mkdir(parents=True, exist_ok=True)


def generate_customers(
    number_of_customers: int,
    start_date: pd.Timestamp,
    countries: list[str],
    faker: Faker,
) -> pd.DataFrame:
    """Generate synthetic customers."""

    customers = []

    for customer_number in range(1, number_of_customers + 1):
        customer_id = f"CUST_{customer_number:06d}"

        registration_date = faker.date_between(
            start_date="-3y",
            end_date=start_date.date(),
        )

        customers.append(
            {
                "customer_id": customer_id,
                "customer_name": faker.name(),
                "email": f"customer{customer_number}@example.com",
                "country": random.choice(countries),
                "registration_date": registration_date,
                "status": random.choices(
                    ["active", "inactive", "suspended"],
                    weights=[0.90, 0.08, 0.02],
                    k=1,
                )[0],
            }
        )

    return pd.DataFrame(customers)


def generate_products(
    number_of_products: int,
    categories: list[str],
    faker: Faker,
) -> pd.DataFrame:
    """Generate synthetic products."""

    products = []

    for product_number in range(1, number_of_products + 1):
        product_id = f"PROD_{product_number:05d}"

        products.append(
            {
                "product_id": product_id,
                "product_name": f"{faker.word().title()} {faker.word().title()}",
                "category": random.choice(categories),
                "supplier_id": f"SUP_{random.randint(1, 40):04d}",
                "unit_price": round(random.uniform(5.0, 500.0), 2),
                "active": random.choices(
                    [True, False],
                    weights=[0.95, 0.05],
                    k=1,
                )[0],
            }
        )

    return pd.DataFrame(products)


def generate_daily_orders(
    batch_date: pd.Timestamp,
    average_orders_per_day: int,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    payment_methods: list[str],
    warehouses: list[str],
    order_counter: int,
    item_counter: int,
    payment_counter: int,
    shipment_counter: int,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    int,
    int,
    int,
    int,
]:
    """Generate orders and related records for one date."""

    active_customers = customers.loc[
        customers["status"] == "active",
        "customer_id",
    ].tolist()

    active_products = products.loc[
        products["active"],
        ["product_id", "unit_price"],
    ].copy()

    product_price_lookup = dict(
        zip(
            active_products["product_id"],
            active_products["unit_price"],
            strict=True,
        )
    )

    number_of_orders = max(
        1,
        int(np.random.poisson(average_orders_per_day)),
    )

    orders = []
    order_items = []
    payments = []
    shipments = []

    for _ in range(number_of_orders):
        order_counter += 1
        order_id = f"ORD_{order_counter:08d}"
        customer_id = random.choice(active_customers)

        order_time = pd.Timestamp(batch_date) + pd.Timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        order_status = random.choices(
            ["completed", "shipped", "cancelled", "processing"],
            weights=[0.60, 0.25, 0.08, 0.07],
            k=1,
        )[0]

        number_of_items = random.randint(1, 5)
        selected_products = random.sample(
            list(product_price_lookup.keys()),
            k=number_of_items,
        )

        order_total = 0.0

        for product_id in selected_products:
            item_counter += 1
            quantity = random.randint(1, 4)
            unit_price = float(product_price_lookup[product_id])

            discount = random.choices(
                [0.00, 0.05, 0.10, 0.15, 0.20],
                weights=[0.50, 0.15, 0.15, 0.10, 0.10],
                k=1,
            )[0]

            line_total = round(
                quantity * unit_price * (1 - discount),
                2,
            )

            order_total += line_total

            order_items.append(
                {
                    "item_id": f"ITEM_{item_counter:09d}",
                    "order_id": order_id,
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "line_total": line_total,
                }
            )

        order_total = round(order_total, 2)

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_date": order_time,
                "status": order_status,
                "currency": "EUR",
                "order_total": order_total,
            }
        )

        payment_counter += 1

        if order_status == "cancelled":
            payment_status = random.choice(["failed", "refunded"])
        else:
            payment_status = random.choices(
                ["successful", "failed", "pending"],
                weights=[0.90, 0.06, 0.04],
                k=1,
            )[0]

        payments.append(
            {
                "payment_id": f"PAY_{payment_counter:08d}",
                "order_id": order_id,
                "payment_date": order_time + pd.Timedelta(
                    minutes=random.randint(1, 30)
                ),
                "amount": order_total,
                "status": payment_status,
                "method": random.choice(payment_methods),
            }
        )

        shipment_counter += 1
        expected_delivery_date = (
            batch_date + pd.Timedelta(days=random.randint(2, 6))
        ).date()

        if order_status == "cancelled":
            shipment_status = "cancelled"
            actual_delivery_date = None
        elif order_status == "processing":
            shipment_status = "in_transit"
            actual_delivery_date = None
        else:
            delivery_delay = random.choices(
                [-1, 0, 1, 2, 3],
                weights=[0.10, 0.55, 0.15, 0.12, 0.08],
                k=1,
            )[0]

            actual_delivery_date = (
                pd.Timestamp(expected_delivery_date)
                + pd.Timedelta(days=delivery_delay)
            ).date()

            if delivery_delay > 0:
                shipment_status = "delayed"
            else:
                shipment_status = "delivered"

        shipments.append(
            {
                "shipment_id": f"SHIP_{shipment_counter:08d}",
                "order_id": order_id,
                "expected_delivery_date": expected_delivery_date,
                "actual_delivery_date": actual_delivery_date,
                "status": shipment_status,
                "warehouse_id": random.choice(warehouses),
            }
        )

    return (
        pd.DataFrame(orders),
        pd.DataFrame(order_items),
        pd.DataFrame(payments),
        pd.DataFrame(shipments),
        order_counter,
        item_counter,
        payment_counter,
        shipment_counter,
    )


def generate_daily_inventory(
    batch_date: pd.Timestamp,
    products: pd.DataFrame,
    warehouses: list[str],
) -> pd.DataFrame:
    """Generate a daily inventory snapshot."""

    inventory_records = []

    active_product_ids = products.loc[
        products["active"],
        "product_id",
    ].tolist()

    for warehouse_id in warehouses:
        for product_id in active_product_ids:
            reorder_level = random.randint(10, 40)

            inventory_records.append(
                {
                    "inventory_date": batch_date.date(),
                    "warehouse_id": warehouse_id,
                    "product_id": product_id,
                    "stock_quantity": random.randint(0, 250),
                    "reorder_level": reorder_level,
                }
            )

    return pd.DataFrame(inventory_records)


def write_csv(
    dataframe: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write a dataframe to CSV without its pandas index."""

    dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8",
        date_format="%Y-%m-%d %H:%M:%S",
    )


def generate_data(config: dict) -> None:
    """Generate all configured source data."""

    seed = int(config["random_seed"])
    faker = initialize_random_generators(seed)

    generation_config = config["generation"]
    business_config = config["business"]

    start_date = pd.Timestamp(generation_config["start_date"])
    number_of_days = int(generation_config["number_of_days"])

    output_directory = (
        PROJECT_ROOT / config["output"]["directory"]
    )

    create_output_directories(output_directory)

    customers = generate_customers(
        number_of_customers=int(
            generation_config["number_of_customers"]
        ),
        start_date=start_date,
        countries=business_config["countries"],
        faker=faker,
    )

    products = generate_products(
        number_of_products=int(
            generation_config["number_of_products"]
        ),
        categories=business_config["categories"],
        faker=faker,
    )

    write_csv(
        customers,
        output_directory / "customers" / "customers.csv",
    )

    write_csv(
        products,
        output_directory / "products" / "products.csv",
    )

    order_counter = 0
    item_counter = 0
    payment_counter = 0
    shipment_counter = 0

    total_orders = 0
    total_items = 0
    total_payments = 0
    total_shipments = 0
    total_inventory_rows = 0

    for day_offset in range(number_of_days):
        batch_date = start_date + pd.Timedelta(days=day_offset)
        date_string = batch_date.strftime("%Y-%m-%d")

        (
            orders,
            order_items,
            payments,
            shipments,
            order_counter,
            item_counter,
            payment_counter,
            shipment_counter,
        ) = generate_daily_orders(
            batch_date=batch_date,
            average_orders_per_day=int(
                generation_config["average_orders_per_day"]
            ),
            customers=customers,
            products=products,
            payment_methods=business_config["payment_methods"],
            warehouses=business_config["warehouses"],
            order_counter=order_counter,
            item_counter=item_counter,
            payment_counter=payment_counter,
            shipment_counter=shipment_counter,
        )

        inventory = generate_daily_inventory(
            batch_date=batch_date,
            products=products,
            warehouses=business_config["warehouses"],
        )

        write_csv(
            orders,
            output_directory
            / "orders"
            / f"orders_{date_string}.csv",
        )

        write_csv(
            order_items,
            output_directory
            / "order_items"
            / f"order_items_{date_string}.csv",
        )

        write_csv(
            payments,
            output_directory
            / "payments"
            / f"payments_{date_string}.csv",
        )

        write_csv(
            shipments,
            output_directory
            / "shipments"
            / f"shipments_{date_string}.csv",
        )

        write_csv(
            inventory,
            output_directory
            / "inventory"
            / f"inventory_{date_string}.csv",
        )

        total_orders += len(orders)
        total_items += len(order_items)
        total_payments += len(payments)
        total_shipments += len(shipments)
        total_inventory_rows += len(inventory)

    print("Data generation completed successfully.")
    print(f"Output directory: {output_directory}")
    print(f"Customers generated: {len(customers):,}")
    print(f"Products generated: {len(products):,}")
    print(f"Orders generated: {total_orders:,}")
    print(f"Order items generated: {total_items:,}")
    print(f"Payments generated: {total_payments:,}")
    print(f"Shipments generated: {total_shipments:,}")
    print(f"Inventory rows generated: {total_inventory_rows:,}")


def parse_arguments() -> argparse.Namespace:
    """Read command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate synthetic e-commerce source data."
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the YAML configuration file.",
    )

    return parser.parse_args()


def main() -> None:
    """Program entry point."""

    arguments = parse_arguments()
    config = load_config(arguments.config)
    generate_data(config)


if __name__ == "__main__":
    main()