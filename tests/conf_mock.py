import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from config.BluePrint import TOKENS
from contracts.core.userWallet import UserWallet


# generic user wallets


@pytest.fixture(scope="session")
def ambassador_wallet(hatchery, alice):
    wallet_addr = hatchery.createUserWallet(alice, ZERO_ADDRESS, False, 1, sender=alice)
    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="session")
def user_wallet(hatchery, bob, ambassador_wallet):
    wallet_addr = hatchery.createUserWallet(bob, ambassador_wallet, False, 1, sender=bob)
    return UserWallet.at(wallet_addr)


############
# Accounts #
############


@pytest.fixture(scope="session")
def deploy3r(env):
    return env.eoa


@pytest.fixture(scope="session")
def sally(env):
    return env.generate_address("sally")


@pytest.fixture(scope="session")
def bob(env):
    return env.generate_address("bob")


@pytest.fixture(scope="session")
def alice(env):
    return env.generate_address("alice")


@pytest.fixture(scope="session")
def charlie(env):
    return env.generate_address("charlie")


@pytest.fixture(scope="session")
def governance():
    # cannot be EOA
    return boa.load("contracts/mock/MockRando.vy", name="mock_gov")


@pytest.fixture(scope="session")
def whale(env):
    return env.generate_address("whale")


@pytest.fixture(scope="session")
def agent_eoa(env):
    return env.generate_address("agent")


########
# WETH #
########


@pytest.fixture(scope="session")
def mock_weth():
    return boa.load("contracts/mock/MockWeth.vy", name="mock_weth")


@pytest.fixture(scope="session")
def weth(fork, mock_weth):
    if fork == "local":
        return mock_weth
    return boa.from_etherscan(TOKENS[fork]["WETH"], name="weth")


##########
# Assets #
##########


# alpha token


@pytest.fixture(scope="session")
def alpha_token(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Alpha Token", "ALPHA", 18, 1_000_000_000, name="alpha_token")


@pytest.fixture(scope="session")
def alpha_token_vault(alpha_token):
    return boa.load("contracts/mock/MockErc4626Vault.vy", alpha_token, name="alpha_erc4626_vault")


@pytest.fixture(scope="session")
def alpha_token_whale(env, alpha_token, governance):
    whale = env.generate_address("alpha_token_whale")
    alpha_token.mint(whale, 100_000_000 * EIGHTEEN_DECIMALS, sender=governance.address)
    return whale


# bravo token


@pytest.fixture(scope="session")
def bravo_token(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Bravo Token", "BRAVO", 18, 1_000_000_000, name="bravo_token")


@pytest.fixture(scope="session")
def bravo_token_vault(bravo_token):
    return boa.load("contracts/mock/MockErc4626Vault.vy", bravo_token, name="bravo_erc4626_vault")


@pytest.fixture(scope="session")
def bravo_token_whale(env, bravo_token, governance):
    whale = env.generate_address("bravo_token_whale")
    bravo_token.mint(whale, 100_000_000 * EIGHTEEN_DECIMALS, sender=governance.address)
    return whale


# charlie token (6 decimals)


@pytest.fixture(scope="session")
def charlie_token(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Charlie Token", "CHARLIE", 6, 1_000_000_000, name="charlie_token")


@pytest.fixture(scope="session")
def charlie_token_vault(charlie_token):
    return boa.load("contracts/mock/MockErc4626Vault.vy", charlie_token, name="charlie_erc4626_vault")


@pytest.fixture(scope="session")
def charlie_token_whale(env, charlie_token, governance):
    whale = env.generate_address("charlie_token_whale")
    charlie_token.mint(whale, 100_000_000 * (10 ** charlie_token.decimals()), sender=governance.address)
    return whale


# delta token (8 decimals)


@pytest.fixture(scope="session")
def delta_token(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Delta Token", "DELTA", 8, 1_000_000_000, name="delta_token")


@pytest.fixture(scope="session")
def delta_token_vault(delta_token):
    return boa.load("contracts/mock/MockErc4626Vault.vy", delta_token, name="delta_erc4626_vault")


@pytest.fixture(scope="session")
def delta_token_whale(env, delta_token, governance):
    whale = env.generate_address("delta_token_whale")
    delta_token.mint(whale, 100_000_000 * (10 ** delta_token.decimals()), sender=governance.address)
    return whale


#################
# Mock Dex Lego #
#################


@pytest.fixture(scope="session")
def mock_dex_lego(mock_dex_asset, mock_dex_asset_alt, undy_hq_deploy, mock_dex_lp_token, mock_dex_debt_token, governance, whale):
    mdl = boa.load(
        "contracts/mock/MockDexLego.vy",
        undy_hq_deploy,
        mock_dex_asset,
        mock_dex_asset_alt,
        mock_dex_lp_token,
        mock_dex_debt_token,
        name="mock_dex_lego",
    )
    for a in [mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token, mock_dex_debt_token]:
        a.setMinter(mdl, True, sender=governance.address)
        a.mint(whale, 10_000_000 * EIGHTEEN_DECIMALS, sender=governance.address)
    return mdl


@pytest.fixture(scope="session")
def mock_dex_asset(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Mock Asset", "MOCK", 18, 1_000_000_000, name="mock_dex_asset")


@pytest.fixture(scope="session")
def mock_dex_asset_alt(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Mock Asset Alt", "MOCK ALT", 18, 1_000_000_000, name="mock_dex_asset_alt")


@pytest.fixture(scope="session")
def mock_dex_lp_token(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Mock LP Token", "MOCK LP", 18, 1_000_000_000, name="mock_dex_lp_token")


@pytest.fixture(scope="session")
def mock_dex_debt_token(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Mock Debt Token", "MOCK DEBT", 18, 1_000_000_000, name="mock_dex_debt_token")


###################
# Mock Yield Lego #
###################


@pytest.fixture(scope="session")
def mock_yield_lego(undy_hq_deploy):
    return boa.load(
        "contracts/mock/MockYieldLego.vy",
        undy_hq_deploy,
        name="mock_yield_lego",
    )


@pytest.fixture(scope="session")
def yield_underlying_token(governance):
    return boa.load("contracts/mock/MockErc20.vy", governance, "Yield Underlying Token", "YUT", 18, 1_000_000_000, name="yield_underlying_token")


@pytest.fixture(scope="session")
def yield_vault_token(yield_underlying_token):
    return boa.load("contracts/mock/MockErc4626Vault.vy", yield_underlying_token, name="yield_vault_token")


@pytest.fixture(scope="session")
def yield_underlying_token_whale(env, yield_underlying_token, governance):
    whale = env.generate_address("yield_underlying_token_whale")
    yield_underlying_token.mint(whale, 100_000_000 * (10 ** yield_underlying_token.decimals()), sender=governance.address)
    return whale


################
# Integrations #
################


@pytest.fixture(scope="session")
def mock_ripe():
    return boa.load("contracts/mock/MockRipe.vy", name="mock_ripe")


@pytest.fixture(scope="session")
def mock_weth():
    return boa.load("contracts/mock/MockWeth.vy", name="mock_weth")


# mock lego integrations


@pytest.fixture(scope="session")
def alpha_token_comp_vault(alpha_token):
    return boa.load("contracts/mock/MockCompVault.vy", alpha_token, name="alpha_comp_vault")


@pytest.fixture(scope="session")
def mock_lego_registry(alpha_token_vault, alpha_token_comp_vault):
    return boa.load("contracts/mock/MockLegoRegistry.vy", [alpha_token_vault, alpha_token_comp_vault], name="mock_registry")


@pytest.fixture(scope="session")
def mock_aave_v3_pool():
    return boa.load("contracts/mock/MockAaveV3Pool.vy", name="mock_aave_v3_pool")


###############
# Other Mocks #
###############


@pytest.fixture(scope="session")
def mock_rando_contract():
    return boa.load("contracts/mock/MockRando.vy", name="rando_contract")


@pytest.fixture(scope="session")
def another_rando_contract():
    return boa.load("contracts/mock/MockRando.vy", name="another_rando_contract")
