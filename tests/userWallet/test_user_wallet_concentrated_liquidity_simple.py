import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


@pytest.fixture(scope="module")
def user_wallet_cl_simple(setUserWalletConfig, setManagerConfig, hatchery, bob):
    setUserWalletConfig()
    setManagerConfig()
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


def test_concentrated_liquidity_functions_exist(user_wallet_cl_simple):
    """Test that concentrated liquidity functions exist and have correct signatures"""
    wallet = user_wallet_cl_simple
    
    # Verify functions exist by checking they are callable
    assert hasattr(wallet, 'addLiquidityConcentrated')
    assert hasattr(wallet, 'removeLiquidityConcentrated')
    
    # These functions should fail due to missing lego setup, but not due to missing functions
    with boa.reverts():
        wallet.addLiquidityConcentrated(
            1,  # legoId
            ZERO_ADDRESS,  # nftAddr
            0,  # nftTokenId
            ZERO_ADDRESS,  # pool
            ZERO_ADDRESS,  # tokenA
            ZERO_ADDRESS,  # tokenB
            sender=boa.env.eoa
        )
    
    with boa.reverts():
        wallet.removeLiquidityConcentrated(
            1,  # legoId
            ZERO_ADDRESS,  # nftAddr
            0,  # nftTokenId
            ZERO_ADDRESS,  # pool
            ZERO_ADDRESS,  # tokenA
            ZERO_ADDRESS,  # tokenB
            sender=boa.env.eoa
        )


def test_concentrated_liquidity_unauthorized_caller(user_wallet_cl_simple, alice):
    """Test that unauthorized callers cannot call concentrated liquidity functions"""
    wallet = user_wallet_cl_simple
    
    # Alice (not the wallet owner) cannot call these functions
    with boa.reverts():
        wallet.addLiquidityConcentrated(
            1,  # legoId
            ZERO_ADDRESS,  # nftAddr
            0,  # nftTokenId
            ZERO_ADDRESS,  # pool
            ZERO_ADDRESS,  # tokenA
            ZERO_ADDRESS,  # tokenB
            sender=alice
        )
    
    with boa.reverts():
        wallet.removeLiquidityConcentrated(
            1,  # legoId
            ZERO_ADDRESS,  # nftAddr
            0,  # nftTokenId
            ZERO_ADDRESS,  # pool
            ZERO_ADDRESS,  # tokenA
            ZERO_ADDRESS,  # tokenB
            sender=alice
        )


def test_concentrated_liquidity_with_invalid_lego_id(user_wallet_cl_simple, bob):
    """Test concentrated liquidity functions with invalid lego ID"""
    wallet = user_wallet_cl_simple
    owner = bob
    
    # Using lego ID 999 (doesn't exist) should fail
    with boa.reverts():
        wallet.addLiquidityConcentrated(
            999,  # invalid legoId
            ZERO_ADDRESS,  # nftAddr
            0,  # nftTokenId
            ZERO_ADDRESS,  # pool
            ZERO_ADDRESS,  # tokenA
            ZERO_ADDRESS,  # tokenB
            sender=owner
        )
    
    with boa.reverts():
        wallet.removeLiquidityConcentrated(
            999,  # invalid legoId
            ZERO_ADDRESS,  # nftAddr
            0,  # nftTokenId
            ZERO_ADDRESS,  # pool
            ZERO_ADDRESS,  # tokenA
            ZERO_ADDRESS,  # tokenB
            sender=owner
        )