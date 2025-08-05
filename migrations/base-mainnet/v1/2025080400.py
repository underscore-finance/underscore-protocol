from scripts.utils.migration import Migration


def migrate(migration: Migration):
    lego_book = migration.get_contract("LegoBook")
    hq = migration.get_address("UndyHq")

    migration.deploy(
        'LegoTools',
        hq,
        migration.blueprint.TOKENS["USDC"],
        migration.blueprint.TOKENS["WETH"],
        lego_book.getRegId(migration.get_address("AaveV3")),
        lego_book.getRegId(migration.get_address("CompoundV3")),
        lego_book.getRegId(migration.get_address("Euler")),
        lego_book.getRegId(migration.get_address("Fluid")),
        lego_book.getRegId(migration.get_address("Moonwell")),
        lego_book.getRegId(migration.get_address("Morpho")),
        lego_book.getRegId(migration.get_address("UniswapV2")),
        lego_book.getRegId(migration.get_address("UniswapV3")),
        lego_book.getRegId(migration.get_address("AeroClassic")),
        lego_book.getRegId(migration.get_address("AeroSlipstream")),
        lego_book.getRegId(migration.get_address("Curve")),
    )
