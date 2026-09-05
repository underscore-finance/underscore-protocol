from pathlib import Path
from types import SimpleNamespace

import boa
import pytest

from config.BluePrint import BLOCK_TIME_CONSTANTS, INTEGRATION_ADDYS, PARAMS, TOKENS
from scripts.params import regenerate_defaults
from scripts.utils.deploy_args import BluePrint
from tests.constants import ZERO_ADDRESS


ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.always


@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None

BLOCK_DENOMINATED_PARAMS = {
    "UNDY_HQ_MIN_GOV_TIMELOCK",
    "UNDY_HQ_MAX_GOV_TIMELOCK",
    "UNDY_HQ_MIN_REG_TIMELOCK",
    "UNDY_HQ_MAX_REG_TIMELOCK",
    "GEN_MIN_CONFIG_TIMELOCK",
    "GEN_MAX_CONFIG_TIMELOCK",
    "BOSS_MIN_MANAGER_PERIOD",
    "BOSS_MAX_MANAGER_PERIOD",
    "BOSS_MIN_ACTIVATION_LENGTH",
    "BOSS_MAX_ACTIVATION_LENGTH",
    "BOSS_MAX_START_DELAY",
    "PAYMASTER_MIN_PAYEE_PERIOD",
    "PAYMASTER_MAX_PAYEE_PERIOD",
    "PAYMASTER_MIN_ACTIVATION_LENGTH",
    "PAYMASTER_MAX_ACTIVATION_LENGTH",
    "PAYMASTER_MAX_START_DELAY",
    "CHEQUE_MIN_PERIOD",
    "CHEQUE_MAX_PERIOD",
    "CHEQUE_MIN_EXPENSIVE_DELAY",
    "CHEQUE_MAX_UNLOCK_BLOCKS",
    "CHEQUE_MAX_EXPIRY_BLOCKS",
}


def _config_values():
    tx_fees = SimpleNamespace(swapFee=25, stableSwapFee=25, rewardsFee=2_000)
    rev_share = SimpleNamespace(swapRatio=0, rewardsRatio=0, yieldRatio=0)
    yield_config = SimpleNamespace(
        maxYieldIncrease=500,
        performanceFee=2_000,
        ambassadorBonusRatio=10_000,
        bonusRatio=10_000,
        bonusAsset=ZERO_ADDRESS,
    )
    user_wallet = SimpleNamespace(
        walletTemplate="0x0000000000000000000000000000000000000011",
        configTemplate="0x0000000000000000000000000000000000000022",
        numUserWalletsAllowed=100_000,
        enforceCreatorWhitelist=True,
        minKeyActionTimeLock=3_600,
        maxKeyActionTimeLock=100_800,
        depositRewardsAsset=ZERO_ADDRESS,
        lootClaimCoolOffPeriod=0,
        txFees=tx_fees,
        ambassadorRevShare=rev_share,
        yieldConfig=yield_config,
    )
    agent = SimpleNamespace(
        startingAgent=ZERO_ADDRESS,
        startingAgentActivationLength=0,
    )
    manager = SimpleNamespace(
        managerPeriod=7_200,
        managerActivationLength=216_000,
        mustHaveUsdValueOnSwaps=True,
        maxNumSwapsPerPeriod=2,
        maxSlippageOnSwaps=500,
        onlyApprovedYieldOpps=True,
    )
    payee = SimpleNamespace(payeePeriod=216_000, payeeActivationLength=2_628_000)
    cheque = SimpleNamespace(
        maxNumActiveCheques=3,
        instantUsdThreshold=100 * 10**18,
        periodLength=7_200,
        expensiveDelayBlocks=7_200,
        defaultExpiryBlocks=14_400,
    )
    ripe_rewards = SimpleNamespace(stakeRatio=8_000, lockDuration=1_296_000)
    return user_wallet, agent, manager, payee, cheque, ripe_rewards


def test_robinhood_profile_uses_l1_ancestor_block_clock():
    assert BLOCK_TIME_CONSTANTS["robinhood"] == {
        "BLOCKS_PER_MINUTE": 5,
        "HOUR_IN_BLOCKS": 300,
        "DAY_IN_BLOCKS": 7_200,
        "WEEK_IN_BLOCKS": 50_400,
        "MONTH_IN_BLOCKS": 216_000,
        "YEAR_IN_BLOCKS": 2_628_000,
    }

    profile = BluePrint("robinhood")
    assert profile.BLOCKS.HOUR == 300
    assert profile.BLOCKS.DAY == 7_200
    assert profile.BLOCKS.MONTH == 216_000
    assert profile.BLOCKS.YEAR == 2_628_000


def test_every_block_denominated_robinhood_param_is_base_divided_by_six():
    base = PARAMS["base"]
    robinhood = PARAMS["robinhood"]

    assert set(robinhood) == set(base)
    for name in BLOCK_DENOMINATED_PARAMS:
        assert robinhood[name] == base[name] // 6, name
    for name in set(base) - BLOCK_DENOMINATED_PARAMS:
        assert robinhood[name] == base[name], name


def test_robinhood_profile_records_verified_ripe_and_weth_addresses():
    assert INTEGRATION_ADDYS["robinhood"] == {
        "RIPE_HQ_V1": "0xD4e82AE1De673bba3B53386A2D2C630AE6630940",
        "RIPE_HQ_V1_CODEHASH": "0x695dbca5482e0f02ab1361963a5114fd48812c7fc09ce8e5c3b9b32ee9c859b0",
        "RIPE_PRICE_DESK": "0x56Db9c2322e009189049bC57385751fc7922AAb0",
        "RIPE_PRICE_DESK_CODEHASH": "0xab49032edcd52353df64533b26d30c3cd1b446a4d0e1fbd4e7cffa39e051995e",
        "RIPE_TOKEN_CODEHASH": "0xff93dfc1dc8887dc7b376e04fc9c13d173c21697d50bc0298c2111e0587f3264",
        "RIPE_TELLER": "0x2d3cB2B39289f402187D7Dc9B609EAD6646F2506",
        "RIPE_TELLER_CODEHASH": "0x544d20b6ba5b31e9102f2e64706bc9d5c53939845d4f14a6f90bb2d3d8d42366",
        "WETH_CODEHASH": "0x5706be52f64875fee65a2cec0d80e47a23d8793cbe85d214b48445e2d05f5353",
    }
    assert TOKENS["robinhood"]["RIPE"] == "0x4D3f37a965b21aB4122e92Dd41D2693E742c883b"
    assert TOKENS["robinhood"]["WETH"] == "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73"


def test_defaults_robinhood_compiles_and_disables_unpriced_rewards():
    template_source = """
# @version 0.4.3
@view
@external
def marker() -> bool:
    return True
"""
    wallet_template = boa.loads(template_source, name="rh_wallet_template")
    config_template = boa.loads(template_source, name="rh_config_template")
    defaults = boa.load(
        "contracts/config/DefaultsRobinhood.vy",
        wallet_template,
        config_template,
    )

    wallet = defaults.userWalletConfig()
    assert wallet.walletTemplate == wallet_template.address
    assert wallet.configTemplate == config_template.address
    assert wallet.enforceCreatorWhitelist
    assert wallet.minKeyActionTimeLock == 3_600
    assert wallet.maxKeyActionTimeLock == 100_800
    assert wallet.depositRewardsAsset == ZERO_ADDRESS
    assert wallet.yieldConfig.bonusAsset == ZERO_ADDRESS

    assert defaults.agentConfig().startingAgent == ZERO_ADDRESS
    assert defaults.agentConfig().startingAgentActivationLength == 0
    assert defaults.managerConfig().managerPeriod == 7_200
    assert defaults.managerConfig().managerActivationLength == 216_000
    assert defaults.payeeConfig().payeePeriod == 216_000
    assert defaults.payeeConfig().payeeActivationLength == 2_628_000
    assert defaults.chequeConfig().periodLength == 7_200
    assert defaults.ripeRewardsConfig().lockDuration == 1_296_000
    assert defaults.securitySigners() == []
    assert defaults.whitelistedCreators() == []


def test_generator_emits_selected_clock_and_uses_existing_local_sources():
    for relative_path in regenerate_defaults.LOCAL_CONTRACT_SOURCES.values():
        assert (ROOT / relative_path).is_file(), relative_path

    source = regenerate_defaults.generate_defaults_vy(
        *_config_values(),
        security_signers=[],
        whitelisted_creators=[],
        profile="robinhood",
    )

    assert "BLOCKS_PER_MINUTE: constant(uint256) = 5" in source
    assert "DAY_IN_BLOCKS: constant(uint256) = 24 * HOUR_IN_BLOCKS" in source
    assert "minKeyActionTimeLock = DAY_IN_BLOCKS // 2" in source
    assert "maxKeyActionTimeLock = 2 * WEEK_IN_BLOCKS" in source
    assert "DAY_IN_BLOCKS: constant(uint256) = 43_200" not in source
    boa.loads(source, name="generated_defaults_robinhood")
