#!/usr/bin/env python3
"""
Output Production Parameters Script for Underscore Protocol

Fetches and displays all current production configuration from Underscore Protocol
smart contracts on Base mainnet, formatted as markdown tables.

Usage:
    python scripts/output_production_params.py
"""

import os
import sys
from datetime import datetime, timezone

import boa

# Contract addresses (Base Mainnet)
# Registries
UNDY_HQ = "0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9"
LEGO_BOOK = "0x2fD67d572806Fc43B55aFE2ad032702d826450EB"
SWITCHBOARD = "0xd6B83538214B7e7d57Cd9faCd260E284a5fe4e11"
VAULT_REGISTRY = "0x1C17ef5Ef2AefcEE958E7e3dC345e96aBfF4e3Cf"

# Config Contracts
SWITCHBOARD_ALPHA = "0xB7d32916c8E7F74f70aF7ECFcb35B04358E50bAc"
SWITCHBOARD_BRAVO = "0x5ed80D2F832da36CCCCd26F856C72b1AdD359B84"
SWITCHBOARD_CHARLIE = "0xDd7507f7FC1845Ba0f07C3f0164D7b114C150117"
MISSION_CONTROL = "0x89c8A842CD9428024294cB6a52c28D5EB23e2cBE"

# Wallet Backpack
WALLET_BACKPACK = "0x10099b1386b434Ea4da1967d952931b645Df6250"
CHEQUE_BOOK = "0xcC939d6b16C6a5f07cde6Bc2bD23cb9B8b7a0Dc9"
HIGH_COMMAND = "0x06492EA8F83B3a61d71B61FEEF7F167aDD9A78EC"
KERNEL = "0xAdED981a6Dfc6C3e3E4DbBa54362375FDcF7B389"
MIGRATOR = "0xe008114992187138a7C341Db0CD900F88BC0169a"
PAYMASTER = "0x80bf71E098Dc328D87456c34675C2B4C10a1AFCb"
SENTINEL = "0xCCe9B58b7d377631e58d3Bd95f12a35cF49F667b"

# Templates
USER_WALLET_TEMPLATE = "0x880E453Ec494FB17bffba537BeaB4Cc6CD1B7C12"
USER_WALLET_CONFIG_TEMPLATE = "0xbF7bAdf4c71102cA49b3f82D50348256cE6C10Fb"
AGENT_WRAPPER = "0x761fCDFfF8B187901eA11415237632A3F7E0203B"

# Core
APPRAISER = "0x8C6521e6f2676a7AdC8484444f161c3538e545e2"
BILLING = "0xB61dDF5a56b4a008f072087BBe411A9B6F576E4e"
HATCHERY = "0x95B85a88200b33C64f9935750C2Ea62fB54141E7"
LOOT_DISTRIBUTOR = "0x23d69D99061acf04c6e86f58692F533E4f039dE8"
LEDGER = "0x9e97A2e527890E690c7FA978696A88EFA868c5D0"

# Earn Vaults
EARN_VAULTS = {
    "UndyUsd": "0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf",
    "UndyEth": "0x02981DB1a99A14912b204437e7a2E02679B57668",
    "UndyBtc": "0x3fb0fC9D3Ddd543AD1b748Ed2286a022f4638493",
    "UndyAero": "0x96F1a7ce331F40afe866F3b707c223e377661087",
    "UndyEurc": "0x1cb8DAB80f19fC5Aca06C2552AECd79015008eA8",
    "UndyUsds": "0xaA0C35937a193ca81A64b3cFd5892dac384d22bB",
    "UndyCbeth": "0xFe75aD75AD59a5c80de5AE0726Feee89567F080d",
    "UndyGho": "0x220b8B08c8CfD6975ed203AA26887c0AA5a8cf44",
}

# Yield Legos
YIELD_LEGOS = {
    "AaveV3": "0xac80b9465d70AAFBe492A08baeA5c6e9d77b1478",
    "CompoundV3": "0x590FB39919c5F0323a93B54f2634d010b6ECfbA7",
    "Euler": "0x7f52A8bCF7589e157961dbc072e1C5E45A3F4fd6",
    "Fluid": "0x67E7bcC1deBd060251a9ECeA37002a3986E74f93",
    "Moonwell": "0x0657CF4683870b8420bB8Da57db83e5F9A1ad804",
    "Morpho": "0x14852dcEEA98d5E781335bA8ea8d4B3a14508868",
    "40Acres": "0x39F5EDd73ce1682Da63C92C34fBbBEdB07156514",
    "Wasabi": "0xe67Ef17B6c82a555CB040173273FB271fcc43BEd",
    "Avantis": "0xc88CD884bdFa8F2D93e32a13EE16543b8a2CF1f0",
    "SkyPsm": "0xEe7B4F2338389A6453E85a65976F3241986492CF",
}

# DEX Legos
DEX_LEGOS = {
    "AeroClassic": "0x43B2a72595016D765E2A66e4c2Cf3026619784D1",
    "AeroSlipstream": "0x2DD267Ab1BA631E93e7c6a9EA6fbcc48882770bd",
    "Curve": "0x7192867D67329800345750f5A281Ce1352C3dF65",
    "UniswapV2": "0x95979aEF0F70887f31701944b658948890F56fd7",
    "UniswapV3": "0xEa1f7604E751b54AF321636DBc2dc75C0045e7A5",
}

# Other Contracts
LEGO_TOOLS = "0x8c76F6e2151CE6794AE3F400C1cB07136058DF72"
RIPE_LEGO = "0x272812fC816a6a8C1A2988b24D06878493459A54"
UNDERSCORE_LEGO = "0x0f79a5A21dC0829ce3B4C72d75a94f67927Af9E9"
EARN_VAULT_AGENT = "0x6B014c7BE0fCA7801133Db96737378CCE85230a7"

# RPC URL
RPC_URL = f"https://base-mainnet.g.alchemy.com/v2/{os.environ.get('WEB3_ALCHEMY_API_KEY')}"

# Constants for formatting
HUNDRED_PERCENT = 100_00  # 100.00%
DECIMALS_18 = 10**18
DECIMALS_6 = 10**6

# Known token addresses for resolution
KNOWN_TOKENS = {
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913".lower(): "USDC",
    "0x4200000000000000000000000000000000000006".lower(): "WETH",
    "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf".lower(): "cbBTC",
    "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22".lower(): "cbETH",
    "0x940181a94A35A4569E4529A3CDfB74e38FD98631".lower(): "AERO",
    "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42".lower(): "EURC",
    "0x820C137fa70C8691f0e44Dc420a5e53c168921Dc".lower(): "USDS",
    "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf".lower(): "cbBTC",
    "0x6Bb7a212910682DCFdbd5BCBb3e28FB4E8da10Ee".lower(): "GHO",
}

# Cache for resolved token symbols
_token_symbol_cache = {}


def get_token_name(address: str, try_fetch: bool = True) -> str:
    """Resolve address to token symbol or return truncated address."""
    if address == "0x0000000000000000000000000000000000000000":
        return "None"

    addr_lower = address.lower()

    # Check cache first
    if addr_lower in _token_symbol_cache:
        return _token_symbol_cache[addr_lower]

    # Check known tokens
    if addr_lower in KNOWN_TOKENS:
        _token_symbol_cache[addr_lower] = KNOWN_TOKENS[addr_lower]
        return KNOWN_TOKENS[addr_lower]

    # Check known protocol addresses
    known_addresses = {
        UNDY_HQ.lower(): "UndyHq",
        MISSION_CONTROL.lower(): "MissionControl",
        VAULT_REGISTRY.lower(): "VaultRegistry",
        LEGO_BOOK.lower(): "LegoBook",
        LEDGER.lower(): "Ledger",
        WALLET_BACKPACK.lower(): "WalletBackpack",
        SWITCHBOARD.lower(): "Switchboard",
        SWITCHBOARD_ALPHA.lower(): "SwitchboardAlpha",
        SWITCHBOARD_BRAVO.lower(): "SwitchboardBravo",
        SWITCHBOARD_CHARLIE.lower(): "SwitchboardCharlie",
        APPRAISER.lower(): "Appraiser",
        BILLING.lower(): "Billing",
        HATCHERY.lower(): "Hatchery",
        LOOT_DISTRIBUTOR.lower(): "LootDistributor",
        KERNEL.lower(): "Kernel",
        SENTINEL.lower(): "Sentinel",
        HIGH_COMMAND.lower(): "HighCommand",
        PAYMASTER.lower(): "Paymaster",
        CHEQUE_BOOK.lower(): "ChequeBook",
        MIGRATOR.lower(): "Migrator",
        EARN_VAULT_AGENT.lower(): "EarnVaultAgent",
        LEGO_TOOLS.lower(): "LegoTools",
    }
    if addr_lower in known_addresses:
        _token_symbol_cache[addr_lower] = known_addresses[addr_lower]
        return known_addresses[addr_lower]

    # Try to fetch symbol from contract
    if try_fetch:
        try:
            token_contract = boa.from_etherscan(address, name=f"Token_{address[:8]}")
            symbol = token_contract.symbol()
            if symbol:
                _token_symbol_cache[addr_lower] = symbol
                return symbol
        except Exception:
            pass

    truncated = f"{address[:6]}...{address[-4:]}"
    _token_symbol_cache[addr_lower] = truncated
    return truncated


def format_address(address: str) -> str:
    """Format address with resolved name."""
    if address == "0x0000000000000000000000000000000000000000":
        return "None"
    name = get_token_name(address, try_fetch=False)
    if name != f"{address[:6]}...{address[-4:]}":
        return f"{name} ({address[:6]}...{address[-4:]})"
    return f"{address[:6]}...{address[-4:]}"


def format_percent(value: int, base: int = HUNDRED_PERCENT) -> str:
    """Format a percentage value."""
    return f"{value / base * 100:.2f}%"


def format_wei(value: int, decimals: int = 18) -> str:
    """Format a wei value with appropriate decimals."""
    return f"{value / 10**decimals:,.6f}"


def format_blocks_to_time(blocks: int, block_time: float = 2.0) -> str:
    """Convert blocks to approximate time (Base ~2s blocks)."""
    seconds = blocks * block_time
    if seconds < 60:
        return f"{blocks} blocks (~{seconds:.0f}s)"
    elif seconds < 3600:
        return f"{blocks} blocks (~{seconds/60:.1f}m)"
    elif seconds < 86400:
        return f"{blocks} blocks (~{seconds/3600:.1f}h)"
    else:
        return f"{blocks} blocks (~{seconds/86400:.1f}d)"


def format_token_amount(raw_value: int, decimals: int = 18, symbol: str = "") -> str:
    """Format token amount with human-readable units."""
    amount = raw_value / (10 ** decimals)
    if amount >= 1_000_000_000_000:
        return f"Very High ({amount:.2e} {symbol})"
    elif amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:,.2f}B {symbol}"
    elif amount >= 1_000_000:
        return f"{amount / 1_000_000:,.2f}M {symbol}"
    elif amount >= 1_000:
        return f"{amount / 1_000:,.2f}K {symbol}"
    else:
        return f"{amount:,.2f} {symbol}"


def print_table(title: str, headers: list, rows: list, anchor: str = None):
    """Print a markdown table with optional anchor."""
    if anchor:
        print(f"\n<a id=\"{anchor}\"></a>")
    print(f"\n## {title}")
    print(f"| {' | '.join(headers)} |")
    print(f"| {' | '.join(['---' for _ in headers])} |")
    for row in rows:
        print(f"| {' | '.join(str(cell) for cell in row)} |")


def print_table_of_contents():
    """Print a clickable table of contents."""
    print("""
## Table of Contents

1. [Executive Summary](#executive-summary)
2. [UndyHq Configuration](#undy-hq)
3. [MissionControl Configuration](#mission-control)
   - [User Wallet Config](#user-wallet-config)
   - [Agent Config](#agent-config)
   - [Manager Config](#manager-config)
   - [Payee Config](#payee-config)
   - [Cheque Config](#cheque-config)
4. [SwitchboardAlpha Timelock](#switchboard-alpha)
5. [VaultRegistry Configuration](#vault-registry)
6. [Earn Vaults](#earn-vaults)
7. [Earn Vault Details](#earn-vault-details)
8. [WalletBackpack Components](#wallet-backpack)
9. [LegoBook Registry](#lego-book)
10. [Switchboard Registry](#switchboard-registry)
11. [LootDistributor Config](#loot-distributor)
12. [Ledger Statistics](#ledger)
""")


def print_executive_summary(ledger, lego_book, vault_registry):
    """Print an executive summary with key protocol metrics."""
    print("\n<a id=\"executive-summary\"></a>")
    print("## Executive Summary\n")

    num_wallets = ledger.numUserWallets()
    num_legos = lego_book.numAddrs()

    rows = [
        ("Total User Wallets", num_wallets - 1 if num_wallets > 0 else 0),
        ("Registered Legos", num_legos - 1 if num_legos > 0 else 0),
        ("Earn Vaults", len(EARN_VAULTS)),
    ]

    print("| Metric | Value |")
    print("| --- | --- |")
    for row in rows:
        print(f"| **{row[0]}** | {row[1]} |")


def fetch_undy_hq_data(hq):
    """Fetch and print UndyHq configuration data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"undy-hq\"></a>")
    print("# UndyHq - Main Registry & Governance")
    print(f"Address: {UNDY_HQ}")

    num_addrs = hq.numAddrs()
    rows = [
        ("undyToken", format_address(str(hq.undyToken()))),
        ("mintEnabled", hq.mintEnabled()),
        ("numAddrs (departments)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(hq.registryChangeTimeLock())),
    ]

    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered departments
    if num_addrs > 1:
        print("\n### Registered Departments")
        headers = ["ID", "Description", "Address", "Can Mint UNDY", "Can Set Blacklist"]
        dept_rows = []
        for i in range(1, num_addrs):
            addr_info = hq.addrInfo(i)
            contract_addr = str(addr_info.addr)
            if contract_addr == "0x0000000000000000000000000000000000000000":
                continue

            hq_config = hq.hqConfig(i)
            dept_rows.append([
                i,
                addr_info.description,
                format_address(contract_addr),
                "Yes" if hq_config.canMintUndy else "No",
                "Yes" if hq_config.canSetTokenBlacklist else "No",
            ])

        if dept_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in dept_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")


def fetch_mission_control_data(mc):
    """Fetch and print MissionControl configuration data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"mission-control\"></a>")
    print("# MissionControl - Core Protocol Configuration")
    print(f"Address: {MISSION_CONTROL}")

    # User Wallet Config
    print("\n<a id=\"user-wallet-config\"></a>")
    uwc = mc.userWalletConfig()
    rows = [
        ("walletTemplate", format_address(str(uwc.walletTemplate))),
        ("configTemplate", format_address(str(uwc.configTemplate))),
        ("numUserWalletsAllowed", uwc.numUserWalletsAllowed),
        ("enforceCreatorWhitelist", uwc.enforceCreatorWhitelist),
        ("minKeyActionTimeLock", format_blocks_to_time(uwc.minKeyActionTimeLock)),
        ("maxKeyActionTimeLock", format_blocks_to_time(uwc.maxKeyActionTimeLock)),
        ("depositRewardsAsset", format_address(str(uwc.depositRewardsAsset))),
        ("lootClaimCoolOffPeriod", format_blocks_to_time(uwc.lootClaimCoolOffPeriod)),
    ]
    print_table("User Wallet Config", ["Parameter", "Value"], rows)

    # Tx Fees
    tx_fees = uwc.txFees
    fee_rows = [
        ("swapFee", format_percent(tx_fees.swapFee)),
        ("stableSwapFee", format_percent(tx_fees.stableSwapFee)),
        ("rewardsFee", format_percent(tx_fees.rewardsFee)),
    ]
    print_table("Default Transaction Fees", ["Parameter", "Value"], fee_rows)

    # Ambassador Rev Share
    rev_share = uwc.ambassadorRevShare
    rev_rows = [
        ("swapRatio", format_percent(rev_share.swapRatio)),
        ("rewardsRatio", format_percent(rev_share.rewardsRatio)),
        ("yieldRatio", format_percent(rev_share.yieldRatio)),
    ]
    print_table("Default Ambassador Revenue Share", ["Parameter", "Value"], rev_rows)

    # Yield Config
    yield_config = uwc.yieldConfig
    yield_rows = [
        ("maxYieldIncrease", format_percent(yield_config.maxYieldIncrease)),
        ("performanceFee", format_percent(yield_config.performanceFee)),
        ("ambassadorBonusRatio", format_percent(yield_config.ambassadorBonusRatio)),
        ("bonusRatio", format_percent(yield_config.bonusRatio)),
        ("bonusAsset", format_address(str(yield_config.bonusAsset))),
    ]
    print_table("Default Yield Config", ["Parameter", "Value"], yield_rows)

    # Agent Config
    print("\n<a id=\"agent-config\"></a>")
    ac = mc.agentConfig()
    agent_rows = [
        ("startingAgent", format_address(str(ac.startingAgent))),
        ("startingAgentActivationLength", format_blocks_to_time(ac.startingAgentActivationLength)),
    ]
    print_table("Agent Config", ["Parameter", "Value"], agent_rows)

    # Manager Config
    print("\n<a id=\"manager-config\"></a>")
    mgr = mc.managerConfig()
    mgr_rows = [
        ("managerPeriod", format_blocks_to_time(mgr.managerPeriod)),
        ("managerActivationLength", format_blocks_to_time(mgr.managerActivationLength)),
        ("mustHaveUsdValueOnSwaps", mgr.mustHaveUsdValueOnSwaps),
        ("maxNumSwapsPerPeriod", mgr.maxNumSwapsPerPeriod),
        ("maxSlippageOnSwaps", format_percent(mgr.maxSlippageOnSwaps)),
        ("onlyApprovedYieldOpps", mgr.onlyApprovedYieldOpps),
    ]
    print_table("Manager Config", ["Parameter", "Value"], mgr_rows)

    # Payee Config
    print("\n<a id=\"payee-config\"></a>")
    payee = mc.payeeConfig()
    payee_rows = [
        ("payeePeriod", format_blocks_to_time(payee.payeePeriod)),
        ("payeeActivationLength", format_blocks_to_time(payee.payeeActivationLength)),
    ]
    print_table("Payee Config", ["Parameter", "Value"], payee_rows)

    # Cheque Config
    print("\n<a id=\"cheque-config\"></a>")
    cheque = mc.chequeConfig()
    cheque_rows = [
        ("maxNumActiveCheques", cheque.maxNumActiveCheques),
        ("instantUsdThreshold", format_token_amount(cheque.instantUsdThreshold, 6, "USD")),
        ("periodLength", format_blocks_to_time(cheque.periodLength)),
        ("expensiveDelayBlocks", format_blocks_to_time(cheque.expensiveDelayBlocks)),
        ("defaultExpiryBlocks", format_blocks_to_time(cheque.defaultExpiryBlocks)),
    ]
    print_table("Cheque Config", ["Parameter", "Value"], cheque_rows)


def fetch_vault_registry_data(vr):
    """Fetch and print VaultRegistry configuration data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"vault-registry\"></a>")
    print("# VaultRegistry - Vault Configuration")
    print(f"Address: {VAULT_REGISTRY}")

    num_addrs = vr.numAddrs()
    rows = [
        ("numAddrs (vaults)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(vr.registryChangeTimeLock())),
    ]
    print_table("Registry Config", ["Parameter", "Value"], rows)


# Vault asset decimals mapping
VAULT_DECIMALS = {
    "UndyUsd": 6,    # USDC has 6 decimals
    "UndyEth": 18,   # WETH has 18 decimals
    "UndyBtc": 8,    # cbBTC has 8 decimals
    "UndyAero": 18,  # AERO has 18 decimals
    "UndyEurc": 6,   # EURC has 6 decimals
    "UndyUsds": 18,  # USDS has 18 decimals
    "UndyCbeth": 18, # cbETH has 18 decimals
    "UndyGho": 18,   # GHO has 18 decimals
}


def fetch_earn_vault_data(vr):
    """Fetch and print per-vault configuration data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"earn-vaults\"></a>")
    print("# Earn Vaults - Per-Vault Configuration")

    for vault_name, vault_addr in EARN_VAULTS.items():
        print(f"\n### {vault_name}")
        print(f"Address: {vault_addr}")

        decimals = VAULT_DECIMALS.get(vault_name, 18)
        vault_config = vr.vaultConfigs(vault_addr)

        max_deposit = vault_config.maxDepositAmount
        rows = [
            ("canDeposit", vault_config.canDeposit),
            ("canWithdraw", vault_config.canWithdraw),
            ("maxDepositAmount", "Unlimited" if max_deposit == 0 else format_token_amount(max_deposit, decimals)),
            ("isVaultOpsFrozen", vault_config.isVaultOpsFrozen),
            ("redemptionBuffer", format_percent(vault_config.redemptionBuffer)),
            ("minYieldWithdrawAmount", format_token_amount(vault_config.minYieldWithdrawAmount, decimals)),
            ("performanceFee", format_percent(vault_config.performanceFee)),
            ("shouldAutoDeposit", vault_config.shouldAutoDeposit),
            ("defaultTargetVaultToken", format_address(str(vault_config.defaultTargetVaultToken))),
            ("isLeveragedVault", vault_config.isLeveragedVault),
            ("shouldEnforceAllowlist", vault_config.shouldEnforceAllowlist),
        ]
        print_table(f"{vault_name} Config", ["Parameter", "Value"], rows)

        # Approved vault tokens
        num_tokens = vr.numApprovedVaultTokens(vault_addr)
        if num_tokens > 0:
            print(f"\n**Approved Vault Tokens ({num_tokens}):**")
            token_rows = []
            for i in range(1, num_tokens + 1):
                token_addr = vr.approvedVaultTokens(vault_addr, i)
                if str(token_addr) != "0x0000000000000000000000000000000000000000":
                    token_rows.append([i, format_address(str(token_addr))])
            if token_rows:
                print("| Index | Token |")
                print("| --- | --- |")
                for row in token_rows:
                    print(f"| {row[0]} | {row[1]} |")


def fetch_wallet_backpack_data(wb):
    """Fetch and print WalletBackpack components."""
    print("\n" + "=" * 80)
    print("\n<a id=\"wallet-backpack\"></a>")
    print("# WalletBackpack - Wallet Components")
    print(f"Address: {WALLET_BACKPACK}")

    rows = [
        ("kernel", format_address(str(wb.kernel()))),
        ("sentinel", format_address(str(wb.sentinel()))),
        ("highCommand", format_address(str(wb.highCommand()))),
        ("paymaster", format_address(str(wb.paymaster()))),
        ("chequeBook", format_address(str(wb.chequeBook()))),
        ("migrator", format_address(str(wb.migrator()))),
    ]
    print_table("Wallet Components", ["Component", "Address"], rows)


def fetch_lego_book_data(lb):
    """Fetch and print LegoBook registry data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"lego-book\"></a>")
    print("# LegoBook - Lego Registry")
    print(f"Address: {LEGO_BOOK}")

    num_addrs = lb.numAddrs()
    rows = [
        ("legoTools", format_address(str(lb.legoTools()))),
        ("numAddrs (legos)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(lb.registryChangeTimeLock())),
    ]
    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered legos
    if num_addrs > 1:
        print("\n### Registered Legos")
        headers = ["ID", "Description", "Address"]
        lego_rows = []
        for i in range(1, num_addrs):
            addr_info = lb.addrInfo(i)
            contract_addr = str(addr_info.addr)
            if contract_addr == "0x0000000000000000000000000000000000000000":
                continue
            lego_rows.append([
                i,
                addr_info.description,
                format_address(contract_addr),
            ])

        if lego_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in lego_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")


def fetch_switchboard_data(sb):
    """Fetch and print Switchboard registry data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"switchboard-registry\"></a>")
    print("# Switchboard - Config Contracts Registry")
    print(f"Address: {SWITCHBOARD}")

    num_addrs = sb.numAddrs()
    rows = [
        ("numAddrs (config contracts)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(sb.registryChangeTimeLock())),
    ]
    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered config contracts
    if num_addrs > 1:
        print("\n### Registered Config Contracts")
        headers = ["ID", "Description", "Address"]
        config_rows = []
        for i in range(1, num_addrs):
            addr_info = sb.addrInfo(i)
            contract_addr = str(addr_info.addr)
            if contract_addr == "0x0000000000000000000000000000000000000000":
                continue
            config_rows.append([
                i,
                addr_info.description,
                format_address(contract_addr),
            ])

        if config_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in config_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")


def fetch_ledger_data(ledger):
    """Fetch and print Ledger statistics."""
    print("\n" + "=" * 80)
    print("\n<a id=\"ledger\"></a>")
    print("# Ledger - Protocol Data")
    print(f"Address: {LEDGER}")

    num_wallets = ledger.numUserWallets()
    rows = [
        ("numUserWallets", num_wallets - 1 if num_wallets > 0 else 0),
    ]
    print_table("Protocol Statistics", ["Parameter", "Value"], rows)

    # Global points
    points = ledger.globalPoints()
    points_rows = [
        ("usdValue", format_token_amount(points.usdValue, 18, "USD")),
        ("depositPoints", f"{points.depositPoints:,}"),
        ("lastUpdate (block)", f"{points.lastUpdate:,}"),
    ]
    print_table("Global Points", ["Parameter", "Value"], points_rows)


def fetch_loot_distributor_data():
    """Fetch and print LootDistributor configuration."""
    print("\n" + "=" * 80)
    print("\n<a id=\"loot-distributor\"></a>")
    print("# LootDistributor - Rewards Configuration")
    print(f"Address: {LOOT_DISTRIBUTOR}")

    loot = boa.from_etherscan(LOOT_DISTRIBUTOR, name="LootDistributor")
    deposit_rewards = loot.depositRewards()

    rows = [
        ("depositRewards.asset", format_address(str(deposit_rewards.asset))),
        ("depositRewards.amount", format_token_amount(deposit_rewards.amount, 18)),
        ("ripeStakeRatio", format_percent(loot.ripeStakeRatio())),
        ("ripeLockDuration", format_blocks_to_time(loot.ripeLockDuration())),
        ("RIPE_TOKEN", format_address(str(loot.RIPE_TOKEN()))),
        ("RIPE_REGISTRY", format_address(str(loot.RIPE_REGISTRY()))),
    ]
    print_table("Loot Config", ["Parameter", "Value"], rows)


def fetch_switchboard_alpha_timelock():
    """Fetch SwitchboardAlpha timelock settings."""
    print("\n" + "=" * 80)
    print("\n<a id=\"switchboard-alpha\"></a>")
    print("# SwitchboardAlpha - Timelock Settings")
    print(f"Address: {SWITCHBOARD_ALPHA}")

    sba = boa.from_etherscan(SWITCHBOARD_ALPHA, name="SwitchboardAlpha")
    rows = [
        ("minActionTimeLock", format_blocks_to_time(sba.minActionTimeLock())),
        ("maxActionTimeLock", format_blocks_to_time(sba.maxActionTimeLock())),
        ("actionTimeLock", format_blocks_to_time(sba.actionTimeLock())),
    ]
    print_table("Timelock Config", ["Parameter", "Value"], rows)


def fetch_earn_vault_details():
    """Fetch per-vault detailed configuration including managers."""
    print("\n" + "=" * 80)
    print("\n<a id=\"earn-vault-details\"></a>")
    print("# Earn Vault Details - Managers & Assets")

    for vault_name, vault_addr in EARN_VAULTS.items():
        print(f"\n### {vault_name} Details")
        print(f"Address: {vault_addr}")

        vault = boa.from_etherscan(vault_addr, name=f"EarnVault_{vault_name}")
        decimals = VAULT_DECIMALS.get(vault_name, 18)
        num_managers = vault.numManagers()
        num_assets = vault.numAssets()

        rows = [
            ("asset", format_address(str(vault.asset()))),
            ("totalAssets", format_token_amount(vault.totalAssets(), decimals)),
            ("totalSupply (shares)", format_token_amount(vault.totalSupply(), 18)),
            ("numManagers", num_managers - 1 if num_managers > 0 else 0),
            ("numAssets (yield positions)", num_assets - 1 if num_assets > 0 else 0),
            ("lastUnderlyingBal", format_token_amount(vault.lastUnderlyingBal(), decimals)),
            ("pendingYieldRealized", format_token_amount(vault.pendingYieldRealized(), decimals)),
        ]
        print_table(f"{vault_name} Stats", ["Parameter", "Value"], rows)

        # List managers
        if num_managers > 1:
            print(f"\n**Managers ({num_managers - 1}):**")
            manager_rows = []
            for i in range(1, min(num_managers, 11)):  # Limit to 10 for output
                mgr = vault.managers(i)
                if str(mgr) != "0x0000000000000000000000000000000000000000":
                    manager_rows.append([i, format_address(str(mgr))])
            if manager_rows:
                print("| Index | Manager |")
                print("| --- | --- |")
                for row in manager_rows:
                    print(f"| {row[0]} | {row[1]} |")


def main():
    """Main entry point."""
    print("Connecting to Base mainnet via Alchemy...")

    # Set etherscan API for contract loading
    boa.set_etherscan(
        api_key=os.environ["ETHERSCAN_API_KEY"],
        uri="https://api.etherscan.io/v2/api?chainid=8453"
    )

    # Fork at latest block
    with boa.fork(RPC_URL):
        block_number = boa.env.evm.patch.block_number
        print(f"Connected. Block: {block_number}\n")

        # Load contracts from Etherscan
        print("Loading contracts from Etherscan...")
        hq = boa.from_etherscan(UNDY_HQ, name="UndyHq")
        mc = boa.from_etherscan(MISSION_CONTROL, name="MissionControl")
        vr = boa.from_etherscan(VAULT_REGISTRY, name="VaultRegistry")
        wb = boa.from_etherscan(WALLET_BACKPACK, name="WalletBackpack")
        lb = boa.from_etherscan(LEGO_BOOK, name="LegoBook")
        sb = boa.from_etherscan(SWITCHBOARD, name="Switchboard")
        ledger = boa.from_etherscan(LEDGER, name="Ledger")

        print("Fetching configuration data...\n")
        print("=" * 80)

        # Header
        print("# Underscore Protocol Production Parameters")
        print(f"\n**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"**Block:** {block_number}")
        print(f"**Network:** Base Mainnet")

        # Table of Contents
        print_table_of_contents()

        # Executive Summary
        print_executive_summary(ledger, lb, vr)

        # Fetch and display all data
        fetch_undy_hq_data(hq)
        fetch_mission_control_data(mc)
        fetch_switchboard_alpha_timelock()
        fetch_vault_registry_data(vr)
        fetch_earn_vault_data(vr)
        fetch_earn_vault_details()
        fetch_wallet_backpack_data(wb)
        fetch_lego_book_data(lb)
        fetch_switchboard_data(sb)
        fetch_loot_distributor_data()
        fetch_ledger_data(ledger)

        print("\n" + "=" * 80)
        print("\n---")
        print(f"*Report generated at block {block_number} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC*")


if __name__ == "__main__":
    main()
