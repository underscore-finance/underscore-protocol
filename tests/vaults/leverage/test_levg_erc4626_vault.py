import boa


def test_levg_vault_erc4626_initialization(undy_levg_vault_usdc, mock_usdc):
    """Test ERC4626 initialization"""
    assert undy_levg_vault_usdc.asset() == mock_usdc.address
    assert undy_levg_vault_usdc.totalAssets() == 0