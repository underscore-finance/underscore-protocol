from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    lego_book = migration.get_contract(
        'LegoBook',
    )

    ripe_lego = migration.deploy(
        'RipeLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 1, ripe_lego)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 1)

    aave_v3 = migration.deploy(
        'AaveV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AAVE_V3_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["AAVE_V3_ADDRESS_PROVIDER"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 2, aave_v3)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 2)

    compound_v3 = migration.deploy(
        'CompoundV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["COMPOUND_V3_CONFIGURATOR"],
        migration.blueprint.INTEGRATION_ADDYS["COMPOUND_V3_REWARDS"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 3, compound_v3)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 3)

    euler = migration.deploy(
        'Euler',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["EULER_EVAULT_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["EULER_EARN_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["EULER_REWARDS"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 4, euler)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 4)

    fluid = migration.deploy(
        'Fluid',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["FLUID_RESOLVER"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 5, fluid)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 5)

    moonwell = migration.deploy(
        'Moonwell',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["MOONWELL_COMPTROLLER"],
        migration.blueprint.TOKENS["WETH"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 6, moonwell)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 6)

    morpho = migration.deploy(
        'Morpho',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_FACTORY_LEGACY"],
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_REWARDS"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 7, morpho)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 7)

    aerodrome = migration.deploy(
        'AeroClassic',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_ROUTER"],
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 8, aerodrome)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 8)

    aero_slip_stream = migration.deploy(
        'AeroSlipstream',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_NFT_MANAGER"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_QUOTER"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 9, aero_slip_stream)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 9)

    curve = migration.deploy(
        'Curve',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["CURVE_ADDRESS_PROVIDER"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 10, curve)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 10)

    uniswap_v2 = migration.deploy(
        'UniswapV2',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["UNISWAP_V2_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["UNISWAP_V2_ROUTER"],
        migration.blueprint.INTEGRATION_ADDYS["UNI_V2_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 11, uniswap_v2)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 11)

    uniswap_v3 = migration.deploy(
        'UniswapV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_NFT_MANAGER"],
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_QUOTER"],
        migration.blueprint.INTEGRATION_ADDYS["UNI_V3_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 12, uniswap_v3)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 12)

    underyield_lego = migration.deploy(
        'UnderscoreLego',
        hq,
        migration.blueprint.TOKENS["RIPE"],

    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 13, underyield_lego)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 13)

    forty_acres_lego = migration.deploy(
        '40Acres',
        hq,
        migration.blueprint.TOKENS["FORTY_ACRES_USDC"],
    )
    assert migration.execute(lego_book.startAddressUpdateToRegistry, 14, forty_acres_lego)
    assert migration.execute(lego_book.confirmAddressUpdateToRegistry, 14)

    wasabi_lego = migration.deploy(
        'Wasabi',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["WASABI_LONG_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["WASABI_SHORT_POOL"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, wasabi_lego, "Wasabi")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, wasabi_lego) == 15

    avantis_lego = migration.deploy(
        'Avantis',
        hq,
        migration.blueprint.TOKENS["AVANTIS_USDC"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, avantis_lego, "Avantis")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, avantis_lego) == 16

    sky_lego = migration.deploy(
        'SkyPsm',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["SKY_PSM"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, sky_lego, "Sky Psm")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, sky_lego) == 17
