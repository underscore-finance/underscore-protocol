import pytest
import boa

from config.BluePrint import INTEGRATION_ADDYS, TOKENS

@pytest.fixture(scope="session")
def lego_tools(
    undy_hq_deploy,
    lego_aave_v3,
    lego_compound_v3,
    lego_euler,
    lego_fluid,
    lego_moonwell,
    lego_morpho,
    lego_uniswap_v2,
    lego_uniswap_v3,
    lego_aero_classic,
    lego_aero_slipstream,
    lego_curve,
    fork,
    alpha_token,
    weth,
    lego_book,
    switchboard_alpha,
):
    usdc = alpha_token
    if fork != "local":
        usdc = TOKENS[fork]["USDC"]

    h = boa.load(
        "contracts/legos/LegoTools.vy",
        undy_hq_deploy,
        usdc,
        weth,
        lego_book.getRegId(lego_aave_v3),
        lego_book.getRegId(lego_compound_v3),
        lego_book.getRegId(lego_euler),
        lego_book.getRegId(lego_fluid),
        lego_book.getRegId(lego_moonwell),
        lego_book.getRegId(lego_morpho),
        lego_book.getRegId(lego_uniswap_v2),
        lego_book.getRegId(lego_uniswap_v3),
        lego_book.getRegId(lego_aero_classic),
        lego_book.getRegId(lego_aero_slipstream),
        lego_book.getRegId(lego_curve),
        name="lego_tools",
    )
    assert lego_book.setLegoTools(h, sender=switchboard_alpha)
    return h


#######################
# Yield Opportunities #
#######################


@pytest.fixture(scope="session")
def lego_aave_v3(fork, lego_book, undy_hq_deploy, governance, mock_aave_v3_pool):
    AAVE_V3_POOL = mock_aave_v3_pool if fork == "local" else INTEGRATION_ADDYS[fork]["AAVE_V3_POOL"]
    AAVE_V3_ADDRESS_PROVIDER = mock_aave_v3_pool if fork == "local" else INTEGRATION_ADDYS[fork]["AAVE_V3_ADDRESS_PROVIDER"]

    addr = boa.load("contracts/legos/yield/AaveV3.vy", undy_hq_deploy, AAVE_V3_POOL, AAVE_V3_ADDRESS_PROVIDER, name="lego_aave_v3")
    lego_book.startAddNewAddressToRegistry(addr, "Aave V3", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_fluid(mock_lego_registry, fork, lego_book, undy_hq_deploy, governance):
    FLUID_RESOLVER = mock_lego_registry if fork == "local" else INTEGRATION_ADDYS[fork]["FLUID_RESOLVER"]
    addr = boa.load("contracts/legos/yield/Fluid.vy", undy_hq_deploy, FLUID_RESOLVER, name="lego_fluid")
    lego_book.startAddNewAddressToRegistry(addr, "Fluid", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_moonwell(mock_lego_registry, fork, lego_book, undy_hq_deploy, weth, governance):
    MOONWELL_COMPTROLLER = mock_lego_registry if fork == "local" else INTEGRATION_ADDYS[fork]["MOONWELL_COMPTROLLER"]
    addr = boa.load("contracts/legos/yield/Moonwell.vy", undy_hq_deploy, MOONWELL_COMPTROLLER, weth, name="lego_moonwell")
    lego_book.startAddNewAddressToRegistry(addr, "Moonwell", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_compound_v3(mock_lego_registry, fork, lego_book, undy_hq_deploy, governance):
    COMPOUND_V3_CONFIGURATOR = mock_lego_registry if fork == "local" else INTEGRATION_ADDYS[fork]["COMPOUND_V3_CONFIGURATOR"]
    addr = boa.load("contracts/legos/yield/CompoundV3.vy", undy_hq_deploy, COMPOUND_V3_CONFIGURATOR, name="lego_compound_v3")
    lego_book.startAddNewAddressToRegistry(addr, "Compound V3", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_morpho(fork, lego_book, undy_hq_deploy, governance, mock_lego_registry):
    MORPHO_FACTORY = mock_lego_registry if fork == "local" else INTEGRATION_ADDYS[fork]["MORPHO_FACTORY"]
    MORPHO_FACTORY_LEGACY = mock_lego_registry if fork == "local" else INTEGRATION_ADDYS[fork]["MORPHO_FACTORY_LEGACY"]
    addr = boa.load("contracts/legos/yield/Morpho.vy", undy_hq_deploy, MORPHO_FACTORY, MORPHO_FACTORY_LEGACY, name="lego_morpho")
    lego_book.startAddNewAddressToRegistry(addr, "Morpho", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_euler(fork, lego_book, undy_hq_deploy, governance, mock_lego_registry):
    EULER_EVAULT_FACTORY = mock_lego_registry if fork == "local" else INTEGRATION_ADDYS[fork]["EULER_EVAULT_FACTORY"]
    EULER_EARN_FACTORY = mock_lego_registry if fork == "local" else INTEGRATION_ADDYS[fork]["EULER_EARN_FACTORY"]
    addr = boa.load("contracts/legos/yield/Euler.vy", undy_hq_deploy, EULER_EVAULT_FACTORY, EULER_EARN_FACTORY, name="lego_euler")
    lego_book.startAddNewAddressToRegistry(addr, "Euler", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


########
# DEXs #
########


@pytest.fixture(scope="session")
def lego_uniswap_v2(fork, lego_book, undy_hq_deploy, governance):
    if fork == "local":
        pytest.skip("asset not relevant on this fork")
    addr = boa.load("contracts/legos/dexes/UniswapV2.vy", undy_hq_deploy, INTEGRATION_ADDYS[fork]["UNISWAP_V2_FACTORY"], INTEGRATION_ADDYS[fork]["UNISWAP_V2_ROUTER"], INTEGRATION_ADDYS[fork]["UNI_V2_WETH_USDC_POOL"], name="lego_uniswap_v2")
    lego_book.startAddNewAddressToRegistry(addr, "Uniswap V2", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_uniswap_v3(fork, lego_book, undy_hq_deploy, governance):
    if fork == "local":
        pytest.skip("asset not relevant on this fork")
    addr = boa.load("contracts/legos/dexes/UniswapV3.vy", undy_hq_deploy, INTEGRATION_ADDYS[fork]["UNIV3_FACTORY"], INTEGRATION_ADDYS[fork]["UNIV3_NFT_MANAGER"], INTEGRATION_ADDYS[fork]["UNIV3_QUOTER"], INTEGRATION_ADDYS[fork]["UNI_V3_WETH_USDC_POOL"], name="lego_uniswap_v3")
    lego_book.startAddNewAddressToRegistry(addr, "Uniswap V3", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_aero_classic(fork, lego_book, undy_hq_deploy, governance):
    if fork == "local":
        pytest.skip("asset not relevant on this fork")
    addr = boa.load("contracts/legos/dexes/AeroClassic.vy", undy_hq_deploy, INTEGRATION_ADDYS[fork]["AERODROME_FACTORY"], INTEGRATION_ADDYS[fork]["AERODROME_ROUTER"], INTEGRATION_ADDYS[fork]["AERODROME_WETH_USDC_POOL"], name="lego_aero_classic")
    lego_book.startAddNewAddressToRegistry(addr, "aero_classic", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_aero_slipstream(fork, lego_book, undy_hq_deploy, governance):
    if fork == "local":
        pytest.skip("asset not relevant on this fork")
    addr = boa.load("contracts/legos/dexes/AeroSlipstream.vy", undy_hq_deploy, INTEGRATION_ADDYS[fork]["AERO_SLIPSTREAM_FACTORY"], INTEGRATION_ADDYS[fork]["AERO_SLIPSTREAM_NFT_MANAGER"], INTEGRATION_ADDYS[fork]["AERO_SLIPSTREAM_QUOTER"], INTEGRATION_ADDYS[fork]["AERO_SLIPSTREAM_WETH_USDC_POOL"], name="lego_aero_slipstream")
    lego_book.startAddNewAddressToRegistry(addr, "aero_slipstream", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr


@pytest.fixture(scope="session")
def lego_curve(fork, lego_book, undy_hq_deploy, governance):
    if fork == "local":
        pytest.skip("asset not relevant on this fork")
    addr = boa.load("contracts/legos/dexes/Curve.vy", undy_hq_deploy, INTEGRATION_ADDYS[fork]["CURVE_ADDRESS_PROVIDER"], name="lego_curve")
    lego_book.startAddNewAddressToRegistry(addr, "Curve", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    assert lego_book.confirmNewAddressToRegistry(addr, sender=governance.address) != 0
    return addr