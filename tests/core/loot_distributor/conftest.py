"""
Shared fixtures for LootDistributor tests
"""
import pytest
import boa
from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import ZERO_ADDRESS


@pytest.fixture(scope="module")
def setup_wallets(setUserWalletConfig, setManagerConfig, setPayeeConfig, createAmbassadorRevShare, hatchery, bob, alice, sally):
    """Setup user wallets for testing"""
    # Configure without starting agent for clean wallets
    setManagerConfig(_startingAgent=ZERO_ADDRESS)
    setUserWalletConfig()
    setPayeeConfig()
    
    # First create a wallet for Sally so she can be an ambassador
    sally_wallet_addr = hatchery.createUserWallet(
        sally,  # owner
        ZERO_ADDRESS,  # no ambassador
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=sally
    )
    
    # Create wallets for testing with Sally's wallet as ambassador
    bob_wallet_addr = hatchery.createUserWallet(
        bob,  # owner
        sally_wallet_addr,  # ambassador (Sally's wallet)
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=bob
    )
    
    alice_wallet_addr = hatchery.createUserWallet(
        alice,  # owner
        sally_wallet_addr,  # same ambassador (Sally's wallet)
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=alice
    )
    
    # Create wallet without ambassador
    no_ambassador_wallet_addr = hatchery.createUserWallet(
        bob,  # owner
        ZERO_ADDRESS,  # no ambassador
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=bob
    )
    
    return {
        'bob_wallet': UserWallet.at(bob_wallet_addr),
        'alice_wallet': UserWallet.at(alice_wallet_addr),
        'sally_wallet': UserWallet.at(sally_wallet_addr),
        'no_ambassador_wallet': UserWallet.at(no_ambassador_wallet_addr),
        'bob_wallet_config': UserWalletConfig.at(UserWallet.at(bob_wallet_addr).walletConfig()),
        'alice_wallet_config': UserWalletConfig.at(UserWallet.at(alice_wallet_addr).walletConfig()),
    }


@pytest.fixture(scope="module")
def setup_contracts(setup_wallets, mission_control, loot_distributor, setUserWalletConfig, setAssetConfig, createTxFees, createAssetYieldConfig, createAmbassadorRevShare, alpha_token, bravo_token, charlie_token, governance, bob, alice, sally, hatchery, yearn_vault_v3, lego_book, mock_lego):
    """Setup contracts and configurations"""
    wallets = setup_wallets
    
    # Set deposit rewards asset through user wallet config
    # This also sets default ambassador fee ratios
    setUserWalletConfig(
        _depositRewardsAsset=alpha_token.address,
        _ambassadorRevShare=createAmbassadorRevShare(
            _swapRatio=100_00,  # 100% of swap fees go to ambassador
            _rewardsRatio=100_00,  # 100% of rewards fees go to ambassador  
            _yieldRatio=100_00  # 100% of yield profit fees go to ambassador
        )
    )
    
    # Set up asset configs with specific fees
    # Alpha token: 10% swap fee, 5% rewards fee
    setAssetConfig(
        _asset=alpha_token,
        _txFees=createTxFees(
            _swapFee=10_00,  # 10%
            _rewardsFee=5_00  # 5%
        ),
        _ambassadorRevShare=createAmbassadorRevShare(
            _swapRatio=100_00,  # 100% of swap fees go to ambassador
            _rewardsRatio=100_00,  # 100% of rewards fees go to ambassador  
            _yieldRatio=100_00  # 100% of yield profit fees go to ambassador
        )
    )
    
    # Bravo token: 15% swap fee, 20% rewards fee, 25% yield profit fee
    setAssetConfig(
        _asset=bravo_token,
        _txFees=createTxFees(
            _swapFee=15_00,  # 15%
            _rewardsFee=20_00  # 20%
        ),
        _ambassadorRevShare=createAmbassadorRevShare(
            _swapRatio=100_00,  # 100% of swap fees go to ambassador
            _rewardsRatio=100_00,  # 100% of rewards fees go to ambassador  
            _yieldRatio=100_00  # 100% of yield profit fees go to ambassador
        ),
        _yieldConfig=createAssetYieldConfig(
            _performanceFee=25_00  # 25%
        )
    )
    
    # Charlie token: Uses defaults from setAssetConfig
    setAssetConfig(
        _asset=charlie_token
    )
    
    return {
        **wallets,
        'mission_control': mission_control,
        'loot_distributor': loot_distributor,
        'alpha_token': alpha_token,
        'bravo_token': bravo_token,
        'charlie_token': charlie_token,
        'governance': governance,
        'bob': bob,
        'alice': alice,
        'sally': sally,
        'sally_wallet': wallets['sally_wallet'],  # Add sally_wallet for easy access
        'setAssetConfig': setAssetConfig,
        'setUserWalletConfig': setUserWalletConfig,
        'hatchery': hatchery,
        'yearn_vault_v3': yearn_vault_v3,
        'lego_book': lego_book,
        'mock_lego': mock_lego
    }


@pytest.fixture(scope="module")
def yearn_vault_v3(alpha_token):
    """Mock Yearn V3 Vault for testing yield assets"""
    return boa.load("contracts/mock/MockErc4626Vault.vy", alpha_token)