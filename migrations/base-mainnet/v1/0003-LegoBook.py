from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Lego Book")
    hq = migration.get_contract("UndyHq")

    lego_book = migration.deploy(
        'LegoBook',
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, lego_book, "Lego Book")
    assert migration.execute(hq.confirmNewAddressToRegistry, lego_book) == 3

    ripe_lego = migration.deploy(
        'RipeLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, ripe_lego, "Ripe Protocol")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, ripe_lego) == 1

    aave_v3 = migration.deploy(
        'AaveV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AAVE_V3_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["AAVE_V3_ADDRESS_PROVIDER"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aave_v3, "Aave v3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, aave_v3) == 2

    compound_v3 = migration.deploy(
        'CompoundV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["COMPOUND_V3_CONFIGURATOR"],
        migration.blueprint.INTEGRATION_ADDYS["COMPOUND_V3_REWARDS"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, compound_v3, "Compound v3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, compound_v3) == 3

    euler = migration.deploy(
        'Euler',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["EULER_EVAULT_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["EULER_EARN_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["EULER_REWARDS"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, euler, "Euler")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, euler) == 4

    fluid = migration.deploy(
        'Fluid',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["FLUID_RESOLVER"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, fluid, "Fluid")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, fluid) == 5

    moonwell = migration.deploy(
        'Moonwell',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["MOONWELL_COMPTROLLER"],
        migration.blueprint.TOKENS["WETH"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, moonwell, "Moonwell")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, moonwell) == 6

    morpho = migration.deploy(
        'Morpho',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_FACTORY_LEGACY"],
        migration.blueprint.INTEGRATION_ADDYS["MORPHO_REWARDS"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, morpho, "Morpho")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, morpho) == 7

    aerodrome = migration.deploy(
        'AeroClassic',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_ROUTER"],
        migration.blueprint.INTEGRATION_ADDYS["AERODROME_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aerodrome, "Aero Classic")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, aerodrome) == 8

    aero_slip_stream = migration.deploy(
        'AeroSlipstream',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_NFT_MANAGER"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_QUOTER"],
        migration.blueprint.INTEGRATION_ADDYS["AERO_SLIPSTREAM_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, aero_slip_stream, "Aero Slipstream")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, aero_slip_stream) == 9

    curve = migration.deploy(
        'Curve',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["CURVE_ADDRESS_PROVIDER"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, curve, "Curve")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, curve) == 10

    uniswap_v2 = migration.deploy(
        'UniswapV2',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["UNISWAP_V2_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["UNISWAP_V2_ROUTER"],
        migration.blueprint.INTEGRATION_ADDYS["UNI_V2_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, uniswap_v2, "Uniswap v2")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, uniswap_v2) == 11

    uniswap_v3 = migration.deploy(
        'UniswapV3',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_FACTORY"],
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_NFT_MANAGER"],
        migration.blueprint.INTEGRATION_ADDYS["UNIV3_QUOTER"],
        migration.blueprint.INTEGRATION_ADDYS["UNI_V3_WETH_USDC_POOL"],
    )
    assert migration.execute(lego_book.startAddNewAddressToRegistry, uniswap_v3, "Uniswap v3")
    assert migration.execute(lego_book.confirmNewAddressToRegistry, uniswap_v3) == 12

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
