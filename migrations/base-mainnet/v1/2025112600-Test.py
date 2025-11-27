from scripts.utils.migration import Migration
owner = '0xf1A77E89a38843E95A1634A4EB16854D48d29709'
wallet = '0x4B309C4d37202A8C92704eda6e60F674d7934596'
agent = '0x9d3F593380875860cC18F5736373ae4B084Ba2F9'
wallet_owner = '0x5EDC5f7a80E95f3b314B41F72e59678901810e5c'


def migrate(migration: Migration):
    wallet_contract = migration.get_contract("UserWallet", wallet)
    wallet_contract.withdrawFromYield(13, '0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf', sender=wallet_owner)
