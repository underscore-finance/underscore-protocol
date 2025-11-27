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

    ripe_lego = migration.deploy(
        'RipeLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["USDC"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, ripe_lego, "Ripe Protocol")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, ripe_lego) == migration.blueprint.LEGO_IDS.RIPE

    aave_v3 = migration.deploy(
        'AaveV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AAVE_V3_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["AAVE_V3_ADDRESS_PROVIDER"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aave_v3, "Aave v3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, aave_v3) == migration.blueprint.LEGO_IDS.AAVEV3

    compound_v3 = migration.deploy(
        'CompoundV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["COMPOUND_V3_CONFIGURATOR"],
        migration.blueprint.INTEGRATION_ADDYS["COMPOUND_V3_REWARDS"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, compound_v3, "Compound v3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             compound_v3) == migration.blueprint.LEGO_IDS.COMPOUNDV3

    euler = migration.deploy(
        'Euler',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["EULER_EVAULT_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["EULER_EARN_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["EULER_REWARDS"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, euler, "Euler")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, euler) == migration.blueprint.LEGO_IDS.EULER

    fluid = migration.deploy(
        'Fluid',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["FLUID_RESOLVER"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, fluid, "Fluid")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, fluid) == migration.blueprint.LEGO_IDS.FLUID

    moonwell = migration.deploy(
        'Moonwell',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["MOONWELL_COMPTROLLER"],
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, moonwell, "Moonwell")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, moonwell) == migration.blueprint.LEGO_IDS.MOONWELL

    morpho = migration.deploy(
        'Morpho',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_FACTORY_LEGACY"],
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_REWARDS"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, morpho, "Morpho")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, morpho) == migration.blueprint.LEGO_IDS.MORPHO

    aerodrome = migration.deploy(
        'AeroClassic',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_ROUTER"],
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_WETH_USDC_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aerodrome, "Aero Classic")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             aerodrome) == migration.blueprint.LEGO_IDS.AERODROME

    aero_slip_stream = migration.deploy(
        'AeroSlipstream',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_NFT_MANAGER"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_QUOTER"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_WETH_USDC_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aero_slip_stream, "Aero Slipstream")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             aero_slip_stream) == migration.blueprint.LEGO_IDS.AERODROME_SLIPSTREAM

    curve = migration.deploy(
        'Curve',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["CURVE_ADDRESS_PROVIDER"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, curve, "Curve")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, curve) == migration.blueprint.LEGO_IDS.CURVE

    uniswap_v2 = migration.deploy(
        'UniswapV2',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["UNISWAP_V2_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["UNISWAP_V2_ROUTER"],
        migration.blueprint.INTEGRATION_ADDYS["UNI_V2_WETH_USDC_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, uniswap_v2, "Uniswap V2")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             uniswap_v2) == migration.blueprint.LEGO_IDS.UNISWAP_V2

    uniswap_v3 = migration.deploy(
        'UniswapV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_NFT_MANAGER"],
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_QUOTER"],
        migration.blueprint.INTEGRATION_ADDYS["UNI_V3_WETH_USDC_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, uniswap_v3, "Uniswap V3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             uniswap_v3) == migration.blueprint.LEGO_IDS.UNISWAP_V3

    underyield_lego = migration.deploy(
        'UnderscoreLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],

    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, underyield_lego, "Underscore Lego")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             underyield_lego) == migration.blueprint.LEGO_IDS.UNDERSCORE

    forty_acres_lego = migration.deploy(
        '40Acres',
        hq,
        migration.blueprint.TOKENS["FORTY_ACRES_USDC"],
        migration.blueprint.INTEGRATION_ADDYS["FORTY_ACRES_LOANS"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, forty_acres_lego, "40 Acres")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             forty_acres_lego) == migration.blueprint.LEGO_IDS.FORTY_ACRES

    wasabi_lego = migration.deploy(
        'Wasabi',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["WASABI_LONG_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["WASABI_SHORT_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],

    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, wasabi_lego, "Wasabi")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, wasabi_lego) == migration.blueprint.LEGO_IDS.WASABI

    avantis_lego = migration.deploy(
        'Avantis',
        hq,
        migration.blueprint.TOKENS["AVANTIS_USDC"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],

    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, avantis_lego, "Avantis")
    assert migration.execute(lego_book.confirmNewAddressToRegistry,
                             avantis_lego) == migration.blueprint.LEGO_IDS.AVANTIS

    sky_lego = migration.deploy(
        'SkyPsm',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["SKY_PSM"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],

    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, sky_lego, "Sky Psm")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, sky_lego) == migration.blueprint.LEGO_IDS.SKY_PSM

    migration.deploy(
        'LegoTools',
        hq,
        migration.blueprint.TOKENS["USDC"],
        migration.blueprint.TOKENS["WETH"],
        lego_book.getRegId(aave_v3),
        lego_book.getRegId(compound_v3),
        lego_book.getRegId(euler),
        lego_book.getRegId(fluid),
        lego_book.getRegId(moonwell),
        lego_book.getRegId(morpho),
        lego_book.getRegId(uniswap_v2),
        lego_book.getRegId(uniswap_v3),
        lego_book.getRegId(aerodrome),
        lego_book.getRegId(aero_slip_stream),
        lego_book.getRegId(curve),
    )
