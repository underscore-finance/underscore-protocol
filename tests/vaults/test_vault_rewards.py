import pytest
import boa

from constants import EIGHTEEN_DECIMALS, MAX_UINT256
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_rewards_test(
    undy_usd_vault,
    mock_dex_lego,
    mock_dex_asset,
    lego_book,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
):
    def setup_rewards_test():
        lego_id = lego_book.getRegId(mock_dex_lego.address)

        mock_ripe.setPrice(mock_dex_asset, 5 * EIGHTEEN_DECIMALS)

        mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=undy_usd_vault.address)

        undy_usd_vault.addManager(starter_agent.address, sender=switchboard_alpha.address)

        return lego_id

    yield setup_rewards_test


def test_claim_rewards_basic(
    setup_rewards_test,
    undy_usd_vault,
    starter_agent,
    mock_dex_asset,
    mock_dex_lego,
):
    lego_id = setup_rewards_test()

    initial_balance = mock_dex_asset.balanceOf(undy_usd_vault)
    assert initial_balance == 0

    reward_amount = 100 * EIGHTEEN_DECIMALS
    amount_claimed, usd_value = undy_usd_vault.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount,
        b"",
        sender=starter_agent.address,
    )

    assert amount_claimed == reward_amount
    assert usd_value == 500 * EIGHTEEN_DECIMALS

    assert mock_dex_asset.balanceOf(undy_usd_vault) == reward_amount

    log = filter_logs(undy_usd_vault, "EarnVaultAction")[0]
    assert log.op == 50
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_lego.address
    assert log.amount1 == reward_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == starter_agent.address


def test_claim_rewards_multiple_claims(
    setup_rewards_test,
    undy_usd_vault,
    starter_agent,
    mock_dex_asset,
):
    lego_id = setup_rewards_test()

    reward_amount_1 = 100 * EIGHTEEN_DECIMALS
    amount_1, usd_1 = undy_usd_vault.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount_1,
        b"",
        sender=starter_agent.address,
    )

    assert amount_1 == reward_amount_1
    assert mock_dex_asset.balanceOf(undy_usd_vault) == reward_amount_1

    reward_amount_2 = 50 * EIGHTEEN_DECIMALS
    amount_2, usd_2 = undy_usd_vault.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount_2,
        b"",
        sender=starter_agent.address,
    )

    assert amount_2 == reward_amount_2
    assert (
        mock_dex_asset.balanceOf(undy_usd_vault)
        == reward_amount_1 + reward_amount_2
    )


def test_claim_rewards_with_amount(
    setup_rewards_test,
    undy_usd_vault,
    starter_agent,
    mock_dex_asset,
):
    lego_id = setup_rewards_test()

    reward_amount = 250 * EIGHTEEN_DECIMALS
    amount_claimed, usd_value = undy_usd_vault.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount,
        b"",
        sender=starter_agent.address,
    )

    assert amount_claimed == reward_amount
    assert usd_value == 1250 * EIGHTEEN_DECIMALS


def test_claim_rewards_no_manager_perms(
    setup_rewards_test,
    undy_usd_vault,
    bob,
    mock_dex_asset,
):
    lego_id = setup_rewards_test()

    with boa.reverts("not manager"):
        undy_usd_vault.claimRewards(
            lego_id,
            mock_dex_asset.address,
            100 * EIGHTEEN_DECIMALS,
            b"",
            sender=bob,
        )


def test_claim_rewards_unregistered_lego(
    setup_rewards_test,
    undy_usd_vault,
    starter_agent,
    mock_dex_asset,
):
    setup_rewards_test()

    invalid_lego_id = 999

    with boa.reverts():
        undy_usd_vault.claimRewards(
            invalid_lego_id,
            mock_dex_asset.address,
            100 * EIGHTEEN_DECIMALS,
            b"",
            sender=starter_agent.address,
        )


def test_claim_rewards_different_reward_tokens(
    setup_rewards_test,
    undy_usd_vault,
    starter_agent,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_ripe,
):
    lego_id = setup_rewards_test()

    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)

    reward_amount_1 = 100 * EIGHTEEN_DECIMALS
    amount_1, usd_1 = undy_usd_vault.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount_1,
        b"",
        sender=starter_agent.address,
    )

    assert amount_1 == reward_amount_1
    assert usd_1 == 500 * EIGHTEEN_DECIMALS
    assert mock_dex_asset.balanceOf(undy_usd_vault) == reward_amount_1

    reward_amount_2 = 200 * EIGHTEEN_DECIMALS
    amount_2, usd_2 = undy_usd_vault.claimRewards(
        lego_id,
        mock_dex_asset_alt.address,
        reward_amount_2,
        b"",
        sender=starter_agent.address,
    )

    assert amount_2 == reward_amount_2
    assert usd_2 == 600 * EIGHTEEN_DECIMALS
    assert mock_dex_asset_alt.balanceOf(undy_usd_vault) == reward_amount_2


def test_claim_rewards_event_details(
    setup_rewards_test,
    undy_usd_vault,
    starter_agent,
    mock_dex_asset,
    mock_dex_lego,
):
    lego_id = setup_rewards_test()

    reward_amount = 250 * EIGHTEEN_DECIMALS
    undy_usd_vault.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount,
        b"test_data",
        sender=starter_agent.address,
    )

    log = filter_logs(undy_usd_vault, "EarnVaultAction")[0]
    assert log.op == 50
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_lego.address
    assert log.amount1 == reward_amount
    assert log.amount2 == 0
    assert log.usdValue == 1250 * EIGHTEEN_DECIMALS
    assert log.legoId == lego_id
    assert log.signer == starter_agent.address