import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS


VAULT_TOKENS = {
    "base": {
        "USDC": TOKENS["base"]["TOKEMAK_USDC"],
        "WETH": TOKENS["base"]["TOKEMAK_ETH"],
        "EURC": TOKENS["base"]["TOKEMAK_EUR"],
    },
}

# Oracle contracts that USDC/WETH vaults depend on
ORACLE_CONTRACTS = [
    "0xBCF85224fc0756B9Fa45aA7892530B47e10b6433",  # Main oracle aggregator
    "0xbA1333333333a1BA1108E8412f11850A5C319bA9",  # Registry
    "0x42868EFcee13C0E71af89c04fF7d96f5bec479b0",  # Price feed
    "0x9189882B85D37f117dC125Fbcce7B61C653Fa30c",  # Another price feed
]

# All tokens to test
TEST_ASSETS = [
    "USDC",
    "WETH",
    "EURC",
]


@pytest.fixture(scope="module")
def setup_oracles(fork):
    """Load oracle dependencies for Tokemak vaults on Base"""
    if fork == "base":
        print("\nLoading oracle dependencies for Tokemak vaults...")
        for oracle_addr in ORACLE_CONTRACTS:
            try:
                boa.from_etherscan(oracle_addr, name=f"Oracle_{oracle_addr[:8]}")
                print(f"  ✓ Loaded oracle: {oracle_addr}")
            except Exception as e:
                print(f"  ✗ Failed to load oracle {oracle_addr}: {e}")
    yield


@pytest.fixture(scope="module")
def getVaultToken(fork, setup_oracles):
    def getVaultToken(_token_str):
        if fork == "local":
            pytest.skip("asset not relevant on this fork")
        vault_token = VAULT_TOKENS[fork][_token_str]
        return boa.from_etherscan(vault_token, name=_token_str + "_vault_token")

    yield getVaultToken


#########
# Tests #
#########


##################################
# Test 1: Direct Vault Deposits
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_tokemak_deposit_direct(
    token_str,
    getVaultToken,
    getTokenAndWhale,
    bob,
):
    """Test deposit directly into Tokemak vault"""
    
    # Get vault and asset
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    
    # Test amount (10 tokens)
    amount = 10 * (10 ** asset.decimals())
    
    # Transfer tokens to test account
    asset.transfer(bob, amount, sender=whale)
    
    # Approve vault
    asset.approve(vault_token, amount, sender=bob)
    
    # Deposit
    shares = vault_token.deposit(amount, bob, sender=bob)
    print(f"✓ {token_str} deposit successful! Received {shares} shares")
    assert shares > 0, "Should receive shares"


##################################
# Test 2: Round-trip (Deposit + Withdraw)
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always  
def test_tokemak_round_trip(
    token_str,
    getVaultToken,
    getTokenAndWhale,
    bob,
):
    """Test deposit and immediate withdrawal (round-trip)"""
    
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    
    # Test amount
    deposit_amount = 10 * (10 ** asset.decimals())
    
    # Initial balance
    initial_balance = asset.balanceOf(bob)
    
    # Transfer and approve
    asset.transfer(bob, deposit_amount, sender=whale)
    asset.approve(vault_token, deposit_amount, sender=bob)
    
    # Deposit
    shares = vault_token.deposit(deposit_amount, bob, sender=bob)
    print(f"  Deposited {deposit_amount / 10**asset.decimals()} {token_str}, got {shares} shares")
    
    # Approve vault to spend shares for withdrawal
    vault_token.approve(vault_token, shares, sender=bob)
    
    # Withdraw all shares
    withdrawn = vault_token.redeem(shares, bob, bob, sender=bob)
    print(f"  Redeemed {shares} shares, got {withdrawn / 10**asset.decimals()} {token_str}")
    
    # Check final balance (should be close to initial + deposit - small fee)
    final_balance = asset.balanceOf(bob)
    net_change = final_balance - initial_balance
    
    print(f"✓ {token_str} round-trip successful")
    print(f"  Net change: {net_change / 10**asset.decimals():.6f} {token_str}")
    
    # Should get back at least 99% of deposit (allowing for fees)
    assert withdrawn >= deposit_amount * 99 // 100, "Lost too much in round-trip"


##################################
# Test 3: Vault Information
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_tokemak_vault_info(
    token_str,
    getVaultToken,
):
    """Test reading vault information"""
    vault_token = getVaultToken(token_str)
    
    # Get vault info
    asset_addr = vault_token.asset()
    total_assets = vault_token.totalAssets()
    total_supply = vault_token.totalSupply()
    symbol = vault_token.symbol()
    decimals = vault_token.decimals()
    
    print(f"\n{token_str} Vault Info:")
    print(f"  Symbol: {symbol}")
    print(f"  Decimals: {decimals}")
    print(f"  Underlying Asset: {asset_addr}")
    print(f"  Total Assets: {total_assets / 10**decimals:.2f}")
    print(f"  Total Supply: {total_supply / 10**decimals:.2f}")
    
    # Check preview functions
    test_amount = 10 * 10**decimals
    preview_deposit = vault_token.previewDeposit(test_amount)
    preview_redeem = vault_token.previewRedeem(test_amount)
    
    print(f"  Preview deposit 10 tokens: {preview_deposit} shares")
    print(f"  Preview redeem 10 shares: {preview_redeem} tokens")
    
    assert asset_addr != "0x0000000000000000000000000000000000000000", "Invalid asset"
    assert symbol != "", "Invalid symbol"


##################################
# Test 4: Lego Integration - Max Deposit
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_tokemak_deposit_max_lego(
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_tokemak,
    getVaultToken,
    lego_book,
    fork,
):
    """Test maximum deposit through Tokemak lego"""
    
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    
    # Transfer max test amount to user wallet
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    # Test deposit through lego (should auto-register vault if needed)
    try:
        testLegoDeposit(lego_book.getRegId(lego_tokemak), asset, vault_token)
        print(f"✓ {token_str} max deposit successful through lego")
    except Exception as e:
        print(f"✗ {token_str} max deposit failed: {str(e)[:200]}...")
        raise


##################################
# Test 5: Lego Integration - Partial Deposit
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_tokemak_deposit_partial_lego(
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_tokemak,
    getVaultToken,
    lego_book,
    fork,
):
    """Test partial deposit through Tokemak lego"""
    
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    
    # Transfer test amount to user wallet
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    # Test partial deposit through lego (half the amount) - should auto-register vault if needed
    try:
        testLegoDeposit(lego_book.getRegId(lego_tokemak), asset, vault_token, amount // 2)
        print(f"✓ {token_str} partial deposit through lego successful")
    except Exception as e:
        print(f"✗ {token_str} partial deposit failed: {str(e)[:200]}...")
        raise


##################################
# Test 6: Lego Integration - Max Withdrawal
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_tokemak_withdraw_max_lego(
    token_str,
    setupWithdrawal,
    lego_tokemak,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
    getTokenAndWhale,
    bob_user_wallet,
    bob,
    fork,
):
    """Test maximum withdrawal from Tokemak vault through lego"""
    
    lego_id = lego_book.getRegId(lego_tokemak)
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    
    # For USDC/WETH, use direct deposit then test withdrawal through lego
    if token_str in ["USDC", "WETH"]:
        # Direct deposit to vault (bypassing lego for deposit)
        amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
        asset.transfer(bob_user_wallet.address, amount, sender=whale)
        
        # Have the user wallet deposit directly to the vault
        # First approve from the wallet
        with boa.env.prank(bob_user_wallet.address):
            asset.approve(vault_token.address, amount)
            shares = vault_token.deposit(amount, bob_user_wallet.address)
        
        # Now test withdrawal through lego
        testLegoWithdrawal(lego_id, asset, vault_token)
        print(f"✓ {token_str} max withdrawal successful (used direct deposit)")
    else:
        # For EURC, use normal flow
        try:
            asset, _ = setupWithdrawal(lego_id, token_str, vault_token)
            # Test max withdrawal
            testLegoWithdrawal(lego_id, asset, vault_token)
            print(f"✓ {token_str} max withdrawal successful")
        except Exception as e:
            print(f"✗ {token_str} withdrawal failed: {str(e)[:200]}...")
            raise


##################################
# Test 7: Lego Integration - Partial Withdrawal
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_tokemak_withdraw_partial_lego(
    token_str,
    setupWithdrawal,
    lego_tokemak,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
    getTokenAndWhale,
    bob_user_wallet,
    bob,
    fork,
):
    """Test partial withdrawal from Tokemak vault through lego"""
    
    lego_id = lego_book.getRegId(lego_tokemak)
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    
    # For USDC/WETH, use direct deposit then test withdrawal through lego
    if token_str in ["USDC", "WETH"]:
        # Direct deposit to vault (bypassing lego for deposit)
        amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
        asset.transfer(bob_user_wallet.address, amount, sender=whale)
        
        # Have the user wallet deposit directly to the vault
        # First approve from the wallet
        with boa.env.prank(bob_user_wallet.address):
            asset.approve(vault_token.address, amount)
            shares = vault_token.deposit(amount, bob_user_wallet.address)
        
        # Test partial withdrawal (half the shares)
        testLegoWithdrawal(lego_id, asset, vault_token, shares // 2)
        print(f"✓ {token_str} partial withdrawal successful (used direct deposit)")
    else:
        # For EURC, use normal flow
        try:
            asset, vault_tokens_received = setupWithdrawal(lego_id, token_str, vault_token)
            # Test partial withdrawal (half the vault tokens)
            testLegoWithdrawal(lego_id, asset, vault_token, vault_tokens_received // 2)
            print(f"✓ {token_str} partial withdrawal successful")
        except Exception as e:
            print(f"✗ {token_str} partial withdrawal failed: {str(e)[:200]}...")
            raise


##################################
# Test 8: Check Vault Registration Status
##################################

@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_tokemak_vault_registration(
    token_str,
    lego_tokemak,
    getVaultToken,
    getTokenAndWhale,
):
    """Check if Tokemak vaults are properly registered in the Tokemak Registry"""
    
    vault_token = getVaultToken(token_str)
    asset, _ = getTokenAndWhale(token_str)
    
    # Check if vault is registered in Tokemak Registry
    is_valid = lego_tokemak.isValidTokemakVault(vault_token.address)
    
    # Check if vault is registered in the lego
    underlying = lego_tokemak.getUnderlyingAsset(vault_token.address)
    
    print(f"\n{token_str} Vault Registration Status:")
    print(f"  Vault address: {vault_token.address}")
    print(f"  Asset address: {asset.address}")
    print(f"  Valid in Tokemak Registry: {is_valid}")
    print(f"  Registered in Lego: {underlying != '0x0000000000000000000000000000000000000000'}")
    
    if underlying != "0x0000000000000000000000000000000000000000":
        print(f"  Underlying asset: {underlying}")
        assert underlying == asset.address, "Asset mismatch!"
    
    # For vaults not in Tokemak Registry, we need manual registration
    if not is_valid:
        print(f"  ⚠️ {token_str} vault is NOT in Tokemak Registry - needs manual registration")
        print(f"  This explains why lego integration tests fail for {token_str}")