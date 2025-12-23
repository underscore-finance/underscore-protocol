from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Lego Book")
    hq = migration.get_contract("UndyHq")

    lego_book = migration.deploy(
        'LegoBook',
        hq,
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    ripe_lego = migration.get_address("RipeLego")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, ripe_lego, "Ripe Protocol")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, ripe_lego) == migration.blueprint.LEGO_IDS.RIPE

    aave_v3 = migration.get_address("AaveV3")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aave_v3, "Aave v3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, aave_v3) == migration.blueprint.LEGO_IDS.AAVEV3

    compound_v3 = migration.get_address("CompoundV3")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, compound_v3, "Compound v3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             compound_v3) == migration.blueprint.LEGO_IDS.COMPOUNDV3

    euler = migration.get_address("Euler")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, euler, "Euler")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, euler) == migration.blueprint.LEGO_IDS.EULER

    fluid = migration.get_address("Fluid")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, fluid, "Fluid")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, fluid) == migration.blueprint.LEGO_IDS.FLUID

    moonwell = migration.get_address("Moonwell")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, moonwell, "Moonwell")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, moonwell) == migration.blueprint.LEGO_IDS.MOONWELL

    morpho = migration.get_address("Morpho")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, morpho, "Morpho")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, morpho) == migration.blueprint.LEGO_IDS.MORPHO

    aerodrome = migration.get_address("AeroClassic")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aerodrome, "Aero Classic")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             aerodrome) == migration.blueprint.LEGO_IDS.AERODROME

    aero_slip_stream = migration.get_address("AeroSlipstream")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aero_slip_stream, "Aero Slipstream")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             aero_slip_stream) == migration.blueprint.LEGO_IDS.AERODROME_SLIPSTREAM

    curve = migration.get_address("Curve")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, curve, "Curve")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             curve) == migration.blueprint.LEGO_IDS.CURVE

    uniswap_v2 = migration.get_address("UniswapV2")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, uniswap_v2, "Uniswap V2")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             uniswap_v2) == migration.blueprint.LEGO_IDS.UNISWAP_V2

    uniswap_v3 = migration.get_address("UniswapV3")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, uniswap_v3, "Uniswap V3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             uniswap_v3) == migration.blueprint.LEGO_IDS.UNISWAP_V3

    underyield_lego = migration.get_address("UnderscoreLego")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, underyield_lego, "Underscore Lego")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             underyield_lego) == migration.blueprint.LEGO_IDS.UNDERSCORE

    forty_acres_lego = migration.get_address("40Acres")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, forty_acres_lego, "40 Acres")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             forty_acres_lego) == migration.blueprint.LEGO_IDS.FORTY_ACRES

    wasabi_lego = migration.get_address("Wasabi")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, wasabi_lego, "Wasabi")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, wasabi_lego) == migration.blueprint.LEGO_IDS.WASABI

    avantis_lego = migration.get_address("Avantis")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, avantis_lego, "Avantis")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             avantis_lego) == migration.blueprint.LEGO_IDS.AVANTIS

    sky_lego = migration.get_address("SkyPsm")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, sky_lego, "Sky Psm")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, sky_lego) == migration.blueprint.LEGO_IDS.SKY_PSM

    extrafi_lego = migration.get_address("ExtraFi")
    assert migration.execute(lego_book.startAddNewAddressToRegistry, extrafi_lego, "ExtraFi")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             extrafi_lego) == migration.blueprint.LEGO_IDS.EXTRA_FI

    migration.log.h2("Helper")
    helpers = migration.deploy(
        'Helpers',
        hq,
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )
    assert migration.execute(helpers.startAddNewAddressToRegistry, migration.get_address("LegoTools"), "LegoTools")
    assert migration.execute(helpers.confirmNewAddressToRegistry, migration.get_address("LegoTools")) == 1

    lvg_vault_tools = migration.deploy(
        'LevgVaultTools',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["USDC"],
    )
    assert migration.execute(helpers.startAddNewAddressToRegistry, lvg_vault_tools, "LevgVaultTools")
    assert migration.execute(helpers.confirmNewAddressToRegistry, lvg_vault_tools) == 2

    lvg_vault_helper = migration.deploy(
        'LevgVaultHelper',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["USDC"],
    )

    migration.execute(lego_book.relinquishGov)
    migration.execute(helpers.relinquishGov)

    migration.log.h2("Done")
