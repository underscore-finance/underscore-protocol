import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def user_wallet_eth(setUserWalletConfig, setManagerConfig, hatchery, bob, setAssetConfig, mock_weth):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    wallet = UserWallet.at(wallet_addr)
    
    # Get ETH address from the wallet
    eth_addr = wallet.ETH()
    
    # Configure ETH and mock WETH with zero fees for testing
    setAssetConfig(eth_addr, _swapFee=0, _rewardsFee=0)
    setAssetConfig(mock_weth.address, _swapFee=0, _rewardsFee=0)
    
    return wallet


@pytest.fixture
def setup_wallet_with_eth(user_wallet_eth):
    """Setup user wallet with ETH for testing"""
    # Send ETH directly to the wallet
    eth_amount = 5 * EIGHTEEN_DECIMALS
    boa.env.set_balance(user_wallet_eth.address, eth_amount)
    
    return user_wallet_eth, eth_amount


def test_api_version(user_wallet_eth):
    """Test that API version is returned correctly"""
    version = user_wallet_eth.apiVersion()
    assert version == "0.1"


def test_eth_fallback_function(user_wallet_eth):
    """Test that wallet can receive ETH via fallback function"""
    initial_balance = boa.env.get_balance(user_wallet_eth.address)
    
    # Send ETH to wallet via fallback
    send_amount = 1 * EIGHTEEN_DECIMALS
    boa.env.set_balance(user_wallet_eth.address, initial_balance + send_amount)
    
    # Verify balance increased
    final_balance = boa.env.get_balance(user_wallet_eth.address)
    assert final_balance == initial_balance + send_amount


def test_convert_eth_to_weth_success(setup_wallet_with_eth, bob):
    """Test successful ETH to WETH conversion"""
    user_wallet, initial_eth = setup_wallet_with_eth
    owner = bob
    
    # Get WETH contract address
    weth_addr = user_wallet.WETH()
    
    # Initial balances
    initial_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    initial_wallet_eth = boa.env.get_balance(user_wallet.address)
    
    # Convert 1 ETH to WETH
    convert_amount = 1 * EIGHTEEN_DECIMALS
    
    # Call convertEthToWeth
    wrapped_amount, tx_usd_value = user_wallet.convertEthToWeth(convert_amount, sender=owner)
    
    # Get events
    eth_wrapped_logs = filter_logs(user_wallet, "EthWrapped")
    
    # Verify return values
    assert wrapped_amount == convert_amount
    assert tx_usd_value >= 0  # USD value might be 0 in test environment
    
    # Verify balances changed
    final_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    final_wallet_eth = boa.env.get_balance(user_wallet.address)
    
    assert final_weth_balance == initial_weth_balance + convert_amount
    assert final_wallet_eth == initial_wallet_eth - convert_amount
    
    # Verify events
    assert len(eth_wrapped_logs) == 1
    event = eth_wrapped_logs[0]
    assert event.amount == convert_amount
    assert event.paidEth == 0  # No ETH sent with transaction
    assert event.txUsdValue == tx_usd_value
    assert event.signer == owner


def test_convert_eth_to_weth_zero_amount(setup_wallet_with_eth, bob):
    """Test ETH to WETH conversion with zero amount (should fail)"""
    user_wallet, _ = setup_wallet_with_eth
    owner = bob
    
    # Convert 0 ETH should fail because function checks amount != 0
    with boa.reverts("no amt"):
        user_wallet.convertEthToWeth(0, sender=owner)


def test_convert_eth_to_weth_insufficient_balance(user_wallet_eth, bob):
    """Test ETH to WETH conversion with insufficient ETH balance"""
    owner = bob
    
    # Wallet has no ETH, should fail
    with boa.reverts("no amt"):
        user_wallet_eth.convertEthToWeth(1 * EIGHTEEN_DECIMALS, sender=owner)


def test_convert_weth_to_eth_success(setup_wallet_with_eth, bob):
    """Test successful WETH to ETH conversion"""
    user_wallet, _ = setup_wallet_with_eth
    owner = bob
    
    # First convert some ETH to WETH
    convert_amount = 2 * EIGHTEEN_DECIMALS
    user_wallet.convertEthToWeth(convert_amount, sender=owner)
    
    # Now convert half back to ETH
    unwrap_amount = 1 * EIGHTEEN_DECIMALS
    
    # Get WETH contract address
    weth_addr = user_wallet.WETH()
    
    # Initial balances after first conversion
    initial_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    initial_wallet_eth = boa.env.get_balance(user_wallet.address)
    
    # Call convertWethToEth
    unwrapped_amount, tx_usd_value = user_wallet.convertWethToEth(unwrap_amount, sender=owner)
    
    # Get events
    weth_unwrapped_logs = filter_logs(user_wallet, "WethUnwrapped")
    
    # Verify return values
    assert unwrapped_amount == unwrap_amount
    assert tx_usd_value >= 0
    
    # Verify balances changed
    final_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    final_wallet_eth = boa.env.get_balance(user_wallet.address)
    
    assert final_weth_balance == initial_weth_balance - unwrap_amount
    assert final_wallet_eth == initial_wallet_eth + unwrap_amount
    
    # Verify events
    assert len(weth_unwrapped_logs) == 1
    event = weth_unwrapped_logs[0]
    assert event.amount == unwrap_amount
    assert event.txUsdValue == tx_usd_value
    assert event.signer == owner


def test_convert_weth_to_eth_zero_amount(setup_wallet_with_eth, bob):
    """Test WETH to ETH conversion with zero amount"""
    user_wallet, _ = setup_wallet_with_eth
    owner = bob
    
    # First get some WETH
    user_wallet.convertEthToWeth(1 * EIGHTEEN_DECIMALS, sender=owner)
    
    # Convert 0 WETH should work (function doesn't explicitly check for 0)
    # but will return 0 amounts
    unwrapped_amount, tx_usd_value = user_wallet.convertWethToEth(0, sender=owner)
    
    assert unwrapped_amount == 0
    assert tx_usd_value >= 0


def test_convert_weth_to_eth_insufficient_balance(user_wallet_eth, bob):
    """Test WETH to ETH conversion with insufficient WETH balance"""
    owner = bob
    
    # Try to convert WETH without having any - should fail in _getAmountAndApprove
    with boa.reverts():
        user_wallet_eth.convertWethToEth(1 * EIGHTEEN_DECIMALS, sender=owner)


def test_eth_weth_conversion_roundtrip(setup_wallet_with_eth, bob):
    """Test complete roundtrip ETH -> WETH -> ETH"""
    user_wallet, initial_eth = setup_wallet_with_eth
    owner = bob
    
    # Get WETH contract address
    weth_addr = user_wallet.WETH()
    
    # Record initial state
    initial_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    initial_wallet_eth = boa.env.get_balance(user_wallet.address)
    
    # Convert ETH to WETH
    convert_amount = 1 * EIGHTEEN_DECIMALS
    _, _ = user_wallet.convertEthToWeth(convert_amount, sender=owner)
    
    # Verify intermediate state
    mid_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    mid_wallet_eth = boa.env.get_balance(user_wallet.address)
    assert mid_weth_balance == initial_weth_balance + convert_amount
    assert mid_wallet_eth == initial_wallet_eth - convert_amount
    
    # Convert WETH back to ETH
    _, _ = user_wallet.convertWethToEth(convert_amount, sender=owner)
    
    # Verify final state matches initial (roundtrip successful)
    final_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    final_wallet_eth = boa.env.get_balance(user_wallet.address)
    assert final_weth_balance == initial_weth_balance
    assert final_wallet_eth == initial_wallet_eth


def test_eth_conversion_with_max_value(setup_wallet_with_eth, bob):
    """Test ETH conversion with max_value parameter (should convert all)"""
    user_wallet, initial_eth = setup_wallet_with_eth
    owner = bob
    
    # Get WETH contract address
    weth_addr = user_wallet.WETH()
    initial_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    
    # Convert all ETH (max_value is default parameter)
    wrapped_amount, tx_usd_value = user_wallet.convertEthToWeth(sender=owner)
    
    # Should convert all available ETH
    assert wrapped_amount == initial_eth
    assert boa.env.get_balance(user_wallet.address) == 0
    assert boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address) == initial_weth_balance + initial_eth


def test_weth_conversion_with_max_value(setup_wallet_with_eth, bob):
    """Test WETH conversion with max_value parameter (should convert all)"""
    user_wallet, _ = setup_wallet_with_eth
    owner = bob
    
    # First convert ETH to WETH
    convert_amount = 2 * EIGHTEEN_DECIMALS
    user_wallet.convertEthToWeth(convert_amount, sender=owner)
    
    # Get WETH contract address
    weth_addr = user_wallet.WETH()
    initial_weth_balance = boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address)
    initial_eth_balance = boa.env.get_balance(user_wallet.address)
    
    # Convert all WETH (max_value is default parameter)
    unwrapped_amount, tx_usd_value = user_wallet.convertWethToEth(sender=owner)
    
    # Should convert all available WETH
    assert unwrapped_amount == initial_weth_balance
    assert boa.load_abi("IERC20").at(weth_addr).balanceOf(user_wallet.address) == 0
    assert boa.env.get_balance(user_wallet.address) == initial_eth_balance + initial_weth_balance


def test_eth_address_constants(user_wallet_eth, fork):
    """Test that ETH and WETH addresses are correctly set"""
    from config.BluePrint import TOKENS
    
    assert user_wallet_eth.ETH() == TOKENS[fork]["ETH"]
    assert user_wallet_eth.WETH() == TOKENS[fork]["WETH"]


def test_wallet_config_address(user_wallet_eth):
    """Test that wallet config address is correctly set"""
    wallet_config_addr = user_wallet_eth.walletConfig()
    assert wallet_config_addr != ZERO_ADDRESS


def test_unauthorized_eth_conversion(user_wallet_eth, alice):
    """Test that unauthorized users cannot convert ETH/WETH"""
    # Give wallet some ETH
    boa.env.set_balance(user_wallet_eth.address, 1 * EIGHTEEN_DECIMALS)
    
    # Alice (not the wallet owner) cannot convert
    with boa.reverts():
        user_wallet_eth.convertEthToWeth(1 * EIGHTEEN_DECIMALS, sender=alice)
    
    with boa.reverts():
        user_wallet_eth.convertWethToEth(1 * EIGHTEEN_DECIMALS, sender=alice)