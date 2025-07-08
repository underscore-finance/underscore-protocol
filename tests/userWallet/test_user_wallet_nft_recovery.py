import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def user_wallet_nft(setUserWalletConfig, setManagerConfig, hatchery, bob, setAssetConfig, alpha_token):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent
    
    # Configure asset with zero fees for testing
    setAssetConfig(alpha_token, _swapFee=0, _rewardsFee=0)
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture
def mock_nft_contract(deploy3r):
    """Deploy a simple mock NFT contract for testing"""
    mock_nft_source = """
# @version 0.4.3

from ethereum.ercs import IERC721

implements: IERC721

# NFT state
owner_of: public(HashMap[uint256, address])
token_approvals: public(HashMap[uint256, address])
balances: public(HashMap[address, uint256])
next_token_id: public(uint256)

@deploy
def __init__():
    self.next_token_id = 1

@external
def mint(_to: address) -> uint256:
    token_id: uint256 = self.next_token_id
    self.next_token_id = token_id + 1
    self.owner_of[token_id] = _to
    self.balances[_to] += 1
    return token_id

@view
@external
def ownerOf(_tokenId: uint256) -> address:
    return self.owner_of[_tokenId]

@view
@external
def balanceOf(_owner: address) -> uint256:
    return self.balances[_owner]

@external
def approve(_approved: address, _tokenId: uint256):
    assert msg.sender == self.owner_of[_tokenId]
    self.token_approvals[_tokenId] = _approved

@view
@external
def getApproved(_tokenId: uint256) -> address:
    return self.token_approvals[_tokenId]

@external
def transferFrom(_from: address, _to: address, _tokenId: uint256):
    assert msg.sender == self.owner_of[_tokenId] or msg.sender == self.token_approvals[_tokenId]
    assert self.owner_of[_tokenId] == _from
    
    self.owner_of[_tokenId] = _to
    self.balances[_from] -= 1
    self.balances[_to] += 1
    self.token_approvals[_tokenId] = empty(address)

@external
def safeTransferFrom(_from: address, _to: address, _tokenId: uint256, _data: Bytes[1024] = b""):
    self.transferFrom(_from, _to, _tokenId)

@view
@external
def supportsInterface(_interfaceId: bytes4) -> bool:
    return _interfaceId == 0x80ac58cd  # ERC721 interface ID
"""
    
    return boa.loads(mock_nft_source, name="MockNFT")


def test_on_erc721_received(user_wallet_nft):
    """Test that wallet properly implements ERC721 receiver"""
    # Call onERC721Received
    operator = boa.env.eoa
    owner = boa.env.eoa  
    token_id = 123
    data = b"test_data"
    
    selector = user_wallet_nft.onERC721Received(operator, owner, token_id, data)
    
    # Should return the correct ERC721 receiver selector
    expected_selector = 0x150b7a02  # bytes4(keccak256("onERC721Received(address,address,uint256,bytes)"))
    assert selector == expected_selector.to_bytes(4, 'big')


def test_on_erc721_received_with_empty_data(user_wallet_nft):
    """Test ERC721 receiver with empty data"""
    operator = boa.env.eoa
    owner = boa.env.eoa
    token_id = 456
    data = b""
    
    selector = user_wallet_nft.onERC721Received(operator, owner, token_id, data)
    
    # Should still return the correct selector
    expected_selector = 0x150b7a02
    assert selector == expected_selector.to_bytes(4, 'big')


def test_on_erc721_received_with_large_data(user_wallet_nft):
    """Test ERC721 receiver with large data payload"""
    operator = boa.env.eoa
    owner = boa.env.eoa
    token_id = 789
    # Create 1024 bytes of data (max allowed)
    data = b"a" * 1024
    
    selector = user_wallet_nft.onERC721Received(operator, owner, token_id, data)
    
    # Should handle large data correctly
    expected_selector = 0x150b7a02
    assert selector == expected_selector.to_bytes(4, 'big')


def test_receive_nft_safely(user_wallet_nft, mock_nft_contract, bob):
    """Test that wallet can receive NFTs via safeTransferFrom"""
    # Mint NFT to bob first
    token_id = mock_nft_contract.mint(bob, sender=bob)
    
    # Bob transfers NFT to wallet
    mock_nft_contract.safeTransferFrom(bob, user_wallet_nft.address, token_id, sender=bob)
    
    # Verify wallet now owns the NFT
    assert mock_nft_contract.ownerOf(token_id) == user_wallet_nft.address
    assert mock_nft_contract.balanceOf(user_wallet_nft.address) == 1


def test_recover_nft_success(user_wallet_nft, mock_nft_contract, bob, alice, wallet_config):
    """Test successful NFT recovery by wallet config"""
    # Mint NFT to wallet
    token_id = mock_nft_contract.mint(user_wallet_nft.address, sender=bob)
    
    # Verify wallet owns the NFT
    assert mock_nft_contract.ownerOf(token_id) == user_wallet_nft.address
    
    # Wallet config recovers NFT to alice
    user_wallet_nft.recoverNft(mock_nft_contract.address, token_id, alice, sender=wallet_config.address)
    
    # Verify alice now owns the NFT
    assert mock_nft_contract.ownerOf(token_id) == alice
    assert mock_nft_contract.balanceOf(user_wallet_nft.address) == 0
    assert mock_nft_contract.balanceOf(alice) == 1


def test_recover_nft_unauthorized_caller(user_wallet_nft, mock_nft_contract, bob, alice):
    """Test that unauthorized callers cannot recover NFTs"""
    # Mint NFT to wallet
    token_id = mock_nft_contract.mint(user_wallet_nft.address, sender=bob)
    
    # Bob (wallet owner) tries to recover NFT directly - should fail
    with boa.reverts("perms"):
        user_wallet_nft.recoverNft(mock_nft_contract.address, token_id, alice, sender=bob)
    
    # Alice (random user) tries to recover NFT - should fail
    with boa.reverts("perms"):
        user_wallet_nft.recoverNft(mock_nft_contract.address, token_id, alice, sender=alice)
    
    # Verify wallet still owns the NFT
    assert mock_nft_contract.ownerOf(token_id) == user_wallet_nft.address


def test_recover_nft_nonexistent_token(user_wallet_nft, mock_nft_contract, alice, wallet_config):
    """Test recovering a nonexistent NFT token"""
    nonexistent_token_id = 99999
    
    # Try to recover nonexistent token - should revert from NFT contract
    with boa.reverts():
        user_wallet_nft.recoverNft(mock_nft_contract.address, nonexistent_token_id, alice, sender=wallet_config.address)


def test_recover_nft_not_owned_by_wallet(user_wallet_nft, mock_nft_contract, bob, alice, wallet_config):
    """Test recovering an NFT not owned by the wallet"""
    # Mint NFT to bob (not the wallet)
    token_id = mock_nft_contract.mint(bob, sender=bob)
    
    # Try to recover NFT that wallet doesn't own - should revert
    with boa.reverts():
        user_wallet_nft.recoverNft(mock_nft_contract.address, token_id, alice, sender=wallet_config.address)


def test_recover_multiple_nfts(user_wallet_nft, mock_nft_contract, bob, alice, charlie, wallet_config):
    """Test recovering multiple NFTs"""
    # Mint multiple NFTs to wallet
    token_ids = []
    for i in range(3):
        token_id = mock_nft_contract.mint(user_wallet_nft.address, sender=bob)
        token_ids.append(token_id)
    
    # Verify wallet owns all NFTs
    assert mock_nft_contract.balanceOf(user_wallet_nft.address) == 3
    
    # Recover NFTs to different recipients
    recipients = [alice, charlie, bob]
    for i, (token_id, recipient) in enumerate(zip(token_ids, recipients)):
        user_wallet_nft.recoverNft(mock_nft_contract.address, token_id, recipient, sender=wallet_config.address)
        
        # Verify NFT was transferred
        assert mock_nft_contract.ownerOf(token_id) == recipient
        assert mock_nft_contract.balanceOf(user_wallet_nft.address) == 3 - (i + 1)
    
    # Verify wallet has no NFTs left
    assert mock_nft_contract.balanceOf(user_wallet_nft.address) == 0


def test_nft_recovery_with_zero_address_recipient(user_wallet_nft, mock_nft_contract, bob, wallet_config):
    """Test NFT recovery with zero address as recipient"""
    # Mint NFT to wallet
    token_id = mock_nft_contract.mint(user_wallet_nft.address, sender=bob)
    
    # Try to recover to zero address - should revert from NFT contract
    with boa.reverts():
        user_wallet_nft.recoverNft(mock_nft_contract.address, token_id, ZERO_ADDRESS, sender=wallet_config.address)


def test_nft_recovery_emergency_scenario(user_wallet_nft, mock_nft_contract, bob, alice, wallet_config):
    """Test NFT recovery in emergency scenario"""
    # Simulate emergency: wallet receives valuable NFT accidentally
    token_id = mock_nft_contract.mint(user_wallet_nft.address, sender=bob)
    
    # Emergency recovery by wallet config to original owner
    user_wallet_nft.recoverNft(mock_nft_contract.address, token_id, bob, sender=wallet_config.address)
    
    # Verify NFT was safely returned
    assert mock_nft_contract.ownerOf(token_id) == bob


def test_nft_data_in_transfer(user_wallet_nft, mock_nft_contract, bob):
    """Test NFT transfer with custom data"""
    # Mint NFT to bob
    token_id = mock_nft_contract.mint(bob, sender=bob)
    
    # Transfer with custom data
    custom_data = b"custom_transfer_data"
    mock_nft_contract.safeTransferFrom(bob, user_wallet_nft.address, token_id, custom_data, sender=bob)
    
    # Verify transfer succeeded despite custom data
    assert mock_nft_contract.ownerOf(token_id) == user_wallet_nft.address


def test_multiple_nft_contracts(user_wallet_nft, bob, alice, wallet_config):
    """Test receiving and recovering NFTs from multiple contracts"""
    # Deploy multiple mock NFT contracts
    nft_contracts = []
    token_ids = []
    
    for i in range(2):
        mock_nft_source = """
# @version 0.4.3
from ethereum.ercs import IERC721
implements: IERC721

owner_of: public(HashMap[uint256, address])
balances: public(HashMap[address, uint256])
next_token_id: public(uint256)

@deploy
def __init__():
    self.next_token_id = 1

@external
def mint(_to: address) -> uint256:
    token_id: uint256 = self.next_token_id
    self.next_token_id = token_id + 1
    self.owner_of[token_id] = _to
    self.balances[_to] += 1
    return token_id

@view
@external
def ownerOf(_tokenId: uint256) -> address:
    return self.owner_of[_tokenId]

@view
@external
def balanceOf(_owner: address) -> uint256:
    return self.balances[_owner]

@external
def safeTransferFrom(_from: address, _to: address, _tokenId: uint256, _data: Bytes[1024] = b""):
    assert self.owner_of[_tokenId] == _from
    self.owner_of[_tokenId] = _to
    self.balances[_from] -= 1
    self.balances[_to] += 1

@view
@external
def supportsInterface(_interfaceId: bytes4) -> bool:
    return _interfaceId == 0x80ac58cd
"""
        nft_contract = boa.loads(mock_nft_source, name=f"MockNFT{i}")
        nft_contracts.append(nft_contract)
        
        # Mint NFT to wallet
        token_id = nft_contract.mint(user_wallet_nft.address, sender=bob)
        token_ids.append(token_id)
    
    # Verify wallet has NFTs from both contracts
    for i, nft_contract in enumerate(nft_contracts):
        assert nft_contract.balanceOf(user_wallet_nft.address) == 1
        assert nft_contract.ownerOf(token_ids[i]) == user_wallet_nft.address
    
    # Recover NFTs from different contracts
    for i, (nft_contract, token_id) in enumerate(zip(nft_contracts, token_ids)):
        recipient = alice if i == 0 else bob
        user_wallet_nft.recoverNft(nft_contract.address, token_id, recipient, sender=wallet_config.address)
        
        # Verify recovery
        assert nft_contract.ownerOf(token_id) == recipient
        assert nft_contract.balanceOf(user_wallet_nft.address) == 0


def test_nft_constants_check(user_wallet_nft):
    """Test NFT-related constants in the contract"""
    # The contract should have ERC721_RECEIVE_DATA constant
    # This is internal but we can verify the onERC721Received function works
    selector = user_wallet_nft.onERC721Received(boa.env.eoa, boa.env.eoa, 1, b"UE721")
    expected_selector = 0x150b7a02
    assert selector == expected_selector.to_bytes(4, 'big')