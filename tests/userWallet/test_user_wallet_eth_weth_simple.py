import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


@pytest.fixture(scope="module")
def user_wallet_simple(setUserWalletConfig, setManagerConfig, hatchery, bob):
    setUserWalletConfig()
    setManagerConfig()
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    wallet = UserWallet.at(wallet_addr)
    
    return wallet


def test_eth_weth_addresses_set(user_wallet_simple):
    """Test that ETH and WETH addresses are set correctly"""
    eth_addr = user_wallet_simple.ETH()
    weth_addr = user_wallet_simple.WETH()
    
    assert eth_addr != ZERO_ADDRESS
    assert weth_addr != ZERO_ADDRESS
    assert eth_addr != weth_addr


def test_wallet_config_address(user_wallet_simple):
    """Test that wallet config address is set"""
    config_addr = user_wallet_simple.walletConfig()
    assert config_addr != ZERO_ADDRESS


def test_api_version(user_wallet_simple):
    """Test that API version is returned correctly"""
    version = user_wallet_simple.apiVersion()
    assert version == "0.1"


def test_eth_fallback_function(user_wallet_simple):
    """Test that wallet can receive ETH via fallback"""
    initial_balance = boa.env.get_balance(user_wallet_simple.address)
    
    # Send ETH to wallet
    send_amount = 1 * EIGHTEEN_DECIMALS
    boa.env.set_balance(user_wallet_simple.address, initial_balance + send_amount)
    
    # Verify balance increased
    final_balance = boa.env.get_balance(user_wallet_simple.address)
    assert final_balance == initial_balance + send_amount


def test_convert_eth_to_weth_insufficient_balance(user_wallet_simple, bob):
    """Test ETH to WETH conversion with insufficient balance"""
    # Wallet has no ETH, should fail
    with boa.reverts("no amt"):
        user_wallet_simple.convertEthToWeth(1 * EIGHTEEN_DECIMALS, sender=bob)


def test_convert_eth_to_weth_zero_amount(user_wallet_simple, bob):
    """Test ETH to WETH conversion with zero amount"""
    # Convert 0 ETH should fail
    with boa.reverts("no amt"):
        user_wallet_simple.convertEthToWeth(0, sender=bob)


def test_convert_weth_to_eth_insufficient_balance(user_wallet_simple, bob):
    """Test WETH to ETH conversion with insufficient WETH balance"""
    # Try to convert WETH without having any
    with boa.reverts():
        user_wallet_simple.convertWethToEth(1 * EIGHTEEN_DECIMALS, sender=bob)


def test_unauthorized_eth_conversion(user_wallet_simple, alice):
    """Test that unauthorized users cannot convert ETH/WETH"""
    # Give wallet some ETH
    boa.env.set_balance(user_wallet_simple.address, 1 * EIGHTEEN_DECIMALS)
    
    # Alice (not the wallet owner) cannot convert
    with boa.reverts():
        user_wallet_simple.convertEthToWeth(1 * EIGHTEEN_DECIMALS, sender=alice)
    
    with boa.reverts():
        user_wallet_simple.convertWethToEth(1 * EIGHTEEN_DECIMALS, sender=alice)