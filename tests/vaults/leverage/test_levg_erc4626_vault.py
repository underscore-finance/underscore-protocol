import boa


def test_levg_vault_erc4626_initialization(undy_levg_vault_local, mock_usdc):
    """Test ERC4626 initialization"""
    assert undy_levg_vault_local.asset() == mock_usdc.address
    assert undy_levg_vault_local.totalAssets() == 0