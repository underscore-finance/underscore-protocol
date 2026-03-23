import pytest
import boa

from contracts.core.userWallet import UserWallet
from conf_utils import filter_logs
from constants import MAX_UINT256, ZERO_ADDRESS
from config.BluePrint import TOKENS, TEST_AMOUNTS


VAULT_TOKENS = {
    "base": {
        "USDC": TOKENS["base"]["FORTY_ACRES_USDC"],
    },
}


TEST_ASSETS = [
    "USDC",
]

LOCAL_DEPOSIT_AMOUNT = 100 * 10 ** 6
LOCAL_BORROW_AMOUNT = 60 * 10 ** 6


@pytest.fixture(scope="module")
def getVaultToken(fork):
    def getVaultToken(_token_str):
        if fork == "local":
            pytest.skip("asset not relevant on this fork")
        vault_token = VAULT_TOKENS[fork][_token_str]
        return boa.from_etherscan(vault_token, name=_token_str + "_vault_token")

    yield getVaultToken


@pytest.fixture
def local_40_acres_wallet(fork, setUserWalletConfig, setManagerConfig, hatchery):
    if fork != "local":
        pytest.skip("local only")

    setUserWalletConfig(_defaultYieldPerformanceFee=0)
    setManagerConfig()

    owner = boa.env.generate_address()
    wallet_addr = hatchery.createUserWallet(owner, ZERO_ADDRESS, 1, sender=owner)
    return owner, UserWallet.at(wallet_addr)


def _deposit_to_40_acres(_owner, _wallet, _asset, _vault, _lego_id, _amount, _governance):
    _asset.transfer(_wallet.address, _amount, sender=_governance.address)
    return _wallet.depositForYield(_lego_id, _asset, _vault, _amount, sender=_owner)


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_40_acres_deposit_max(
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_40_acres,
    getVaultToken,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)

    testLegoDeposit(lego_40_acres, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_40_acres_deposit_partial(
    token_str,
    testLegoDeposit,
    getVaultToken,
    bob_user_wallet,
    lego_40_acres,
    getTokenAndWhale,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    testLegoDeposit(lego_40_acres, asset, vault_token, amount // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_40_acres_withdraw_max(
    token_str,
    setupWithdrawal,
    lego_40_acres,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_40_acres)
    vault_token = getVaultToken(token_str)
    asset, _ = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_40_acres_withdraw_partial(
    token_str,
    setupWithdrawal,
    lego_40_acres,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_40_acres)
    vault_token = getVaultToken(token_str)
    asset, vault_tokens_received = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token, vault_tokens_received // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_40_acres_view_functions(
    token_str,
    getVaultToken,
    lego_40_acres,
    testLegoViewFunctions,
):
    vault_token = getVaultToken(token_str)
    testLegoViewFunctions(lego_40_acres, vault_token, token_str)


@pytest.local
def test_40_acres_withdraw_full_liquidity_local(
    local_40_acres_wallet,
    lego_40_acres,
    lego_book,
    governance,
    mock_usdc,
    mock_40_acres_usdc_vault,
):
    owner, wallet = local_40_acres_wallet
    lego_id = lego_book.getRegId(lego_40_acres)

    deposited, vault_token, vault_tokens_received, _ = _deposit_to_40_acres(
        owner,
        wallet,
        mock_usdc,
        mock_40_acres_usdc_vault,
        lego_id,
        LOCAL_DEPOSIT_AMOUNT,
        governance,
    )

    assert deposited == LOCAL_DEPOSIT_AMOUNT
    assert vault_token == mock_40_acres_usdc_vault.address
    assert vault_tokens_received == LOCAL_DEPOSIT_AMOUNT
    assert lego_40_acres.totalAssets(mock_40_acres_usdc_vault) == LOCAL_DEPOSIT_AMOUNT
    assert lego_40_acres.totalBorrows(mock_40_acres_usdc_vault) == 0
    assert lego_40_acres.getAvailLiquidity(mock_40_acres_usdc_vault) == LOCAL_DEPOSIT_AMOUNT

    vault_burned, underlying_asset, underlying_received, _ = wallet.withdrawFromYield(
        lego_id,
        mock_40_acres_usdc_vault,
        MAX_UINT256,
        sender=owner,
    )

    assert vault_burned == LOCAL_DEPOSIT_AMOUNT
    assert underlying_asset == mock_usdc.address
    assert underlying_received == LOCAL_DEPOSIT_AMOUNT
    assert mock_40_acres_usdc_vault.balanceOf(wallet.address) == 0
    assert mock_40_acres_usdc_vault.balanceOf(lego_40_acres.address) == 0
    assert mock_usdc.balanceOf(wallet.address) == LOCAL_DEPOSIT_AMOUNT


@pytest.local
def test_40_acres_withdraw_partial_liquidity_local(
    local_40_acres_wallet,
    lego_40_acres,
    lego_book,
    governance,
    mock_usdc,
    mock_40_acres_usdc_vault,
    mock_40_acres_loans,
):
    owner, wallet = local_40_acres_wallet
    lego_id = lego_book.getRegId(lego_40_acres)

    _, _, vault_tokens_received, _ = _deposit_to_40_acres(
        owner,
        wallet,
        mock_usdc,
        mock_40_acres_usdc_vault,
        lego_id,
        LOCAL_DEPOSIT_AMOUNT,
        governance,
    )

    mock_40_acres_usdc_vault.transferAssetOut(governance.address, LOCAL_BORROW_AMOUNT, sender=governance.address)
    mock_40_acres_loans.setActiveAssets(LOCAL_BORROW_AMOUNT, sender=governance.address)

    expected_liquidity = LOCAL_DEPOSIT_AMOUNT - LOCAL_BORROW_AMOUNT
    expected_burned = mock_40_acres_usdc_vault.convertToShares(expected_liquidity)

    assert lego_40_acres.totalAssets(mock_40_acres_usdc_vault) == LOCAL_DEPOSIT_AMOUNT
    assert lego_40_acres.totalBorrows(mock_40_acres_usdc_vault) == LOCAL_BORROW_AMOUNT
    assert lego_40_acres.getAvailLiquidity(mock_40_acres_usdc_vault) == expected_liquidity

    vault_burned, underlying_asset, underlying_received, _ = wallet.withdrawFromYield(
        lego_id,
        mock_40_acres_usdc_vault,
        MAX_UINT256,
        sender=owner,
    )

    assert vault_burned == expected_burned
    assert underlying_asset == mock_usdc.address
    assert underlying_received == expected_liquidity
    assert mock_40_acres_usdc_vault.balanceOf(wallet.address) == vault_tokens_received - expected_burned
    assert mock_40_acres_usdc_vault.balanceOf(lego_40_acres.address) == 0
    assert mock_usdc.balanceOf(wallet.address) == expected_liquidity

    mock_usdc.transfer(mock_40_acres_usdc_vault.address, LOCAL_BORROW_AMOUNT, sender=governance.address)
    mock_40_acres_loans.setActiveAssets(0, sender=governance.address)

    remaining_burned, _, remaining_received, _ = wallet.withdrawFromYield(
        lego_id,
        mock_40_acres_usdc_vault,
        MAX_UINT256,
        sender=owner,
    )

    assert remaining_burned == vault_tokens_received - expected_burned
    assert remaining_received == LOCAL_BORROW_AMOUNT
    assert mock_40_acres_usdc_vault.balanceOf(wallet.address) == 0
    assert mock_usdc.balanceOf(wallet.address) == LOCAL_DEPOSIT_AMOUNT


@pytest.local
def test_40_acres_withdraw_zero_liquidity_local(
    local_40_acres_wallet,
    lego_40_acres,
    lego_book,
    governance,
    mock_usdc,
    mock_40_acres_usdc_vault,
    mock_40_acres_loans,
):
    owner, wallet = local_40_acres_wallet
    lego_id = lego_book.getRegId(lego_40_acres)

    _, _, vault_tokens_received, _ = _deposit_to_40_acres(
        owner,
        wallet,
        mock_usdc,
        mock_40_acres_usdc_vault,
        lego_id,
        LOCAL_DEPOSIT_AMOUNT,
        governance,
    )

    mock_40_acres_usdc_vault.transferAssetOut(governance.address, LOCAL_DEPOSIT_AMOUNT, sender=governance.address)
    mock_40_acres_loans.setActiveAssets(LOCAL_DEPOSIT_AMOUNT, sender=governance.address)

    assert lego_40_acres.totalAssets(mock_40_acres_usdc_vault) == LOCAL_DEPOSIT_AMOUNT
    assert lego_40_acres.totalBorrows(mock_40_acres_usdc_vault) == LOCAL_DEPOSIT_AMOUNT
    assert lego_40_acres.getAvailLiquidity(mock_40_acres_usdc_vault) == 0

    vault_burned, underlying_asset, underlying_received, usd_value = wallet.withdrawFromYield(
        lego_id,
        mock_40_acres_usdc_vault,
        MAX_UINT256,
        sender=owner,
    )

    assert vault_burned == 0
    assert underlying_asset == mock_usdc.address
    assert underlying_received == 0
    assert usd_value == 0
    assert mock_40_acres_usdc_vault.balanceOf(wallet.address) == vault_tokens_received
    assert mock_40_acres_usdc_vault.balanceOf(lego_40_acres.address) == 0
    assert mock_usdc.balanceOf(wallet.address) == 0

    log_wallet = filter_logs(wallet, "WalletAction")[-1]
    assert log_wallet.op == 11
    assert log_wallet.asset1 == mock_40_acres_usdc_vault.address
    assert log_wallet.asset2 == mock_usdc.address
    assert log_wallet.amount1 == 0
    assert log_wallet.amount2 == 0
    assert log_wallet.legoId == lego_id
    assert log_wallet.signer == owner

    mock_usdc.transfer(mock_40_acres_usdc_vault.address, LOCAL_DEPOSIT_AMOUNT, sender=governance.address)
    mock_40_acres_loans.setActiveAssets(0, sender=governance.address)

    remaining_burned, remaining_asset, remaining_received, _ = wallet.withdrawFromYield(
        lego_id,
        mock_40_acres_usdc_vault,
        MAX_UINT256,
        sender=owner,
    )

    assert remaining_burned == LOCAL_DEPOSIT_AMOUNT
    assert remaining_asset == mock_usdc.address
    assert remaining_received == LOCAL_DEPOSIT_AMOUNT
    assert mock_40_acres_usdc_vault.balanceOf(wallet.address) == 0
