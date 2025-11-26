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
LEGO_BOOK = "0x9788f0D9D1A6577F685972B066b4Db2D73fEd8e3"
SWITCHBOARD = "0xe52A6790fC8210DE16847f1FaF55A6146c0BfC7e"
VAULT_REGISTRY = "0xC64A779FE55673F93F647F1E2A30B3C3a9A25b64"

# Config Contracts
SWITCHBOARD_ALPHA = "0xb7622CB741C2B26E59e262604d941C50D309C358"
SWITCHBOARD_BRAVO = "0xf1F5938559884D3c54400b417292B93cd81C368c"
MISSION_CONTROL = "0x910FE9484540fa21B092eE04a478A30A6B342006"

# Wallet Backpack
WALLET_BACKPACK = "0x0E8D974Cdea08BcAa43421A15B7947Ec901f5CcD"
CHEQUE_BOOK = "0xF8009A583A82077c81A2c10C45Bd0122a26C0318"
HIGH_COMMAND = "0x84c54F4801FBf5c189E49d7CE5B1CB4378BE4372"
KERNEL = "0xcb91C738E301bDf8Ee5354f0Ef2692B41145D217"
MIGRATOR = "0x99bf2C624C02082C16bD12a241bfC4cA1659b22C"
PAYMASTER = "0x5aDc5a2b5018426243C98Aa52E4696F614274946"
SENTINEL = "0xA9A71c4eA67f8ff41A4639f71CFc5E79611BBf30"

# Templates
USER_WALLET_TEMPLATE = "0x4C4D1a888a0b49eA217a8F41f207CFe59Ab03a40"
USER_WALLET_CONFIG_TEMPLATE = "0x0E7064202c4F906Adc4D9F6D3C92470b62F624F1"
AGENT_WRAPPER_TEMPLATE = "0xe1d877C9160878F83EB8e996428C44e898BF414B"

# Core
APPRAISER = "0x212652d44EA7A1642c4F8c9De6F7F3a62ff639E5"
BILLING = "0x413962eCe8652A0FAfd14d1dC141A421E3DcC73E"
HATCHERY = "0xCCE416b5050F628C85A57a817F168C1a7Af8D4d2"
LOOT_DISTRIBUTOR = "0x2D775AfA205729b8e74F9215611Ed700f564910C"
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
    "AaveV3": "0x256f0f254B44C69e431C5eaFbB9A86F85DA1d1D3",
    "CompoundV3": "0xAB7518D8b69067AC82F50B29867B24cA0a911f58",
    "Euler": "0x6669A47A105d3c9F17b428838f3dD18A7D44E069",
    "Fluid": "0x7C619b4d396BB4802B31738F9F1ef69d94D9DF45",
    "Moonwell": "0x3F42489Ed3836DCBaF1A722c8403F4a6CB56fEc1",
    "Morpho": "0x77EDfc58AF0C52D8a77B1d0630a4284cB1752e1E",
    "40Acres": "0xea19B48ae835CC6198ecfCb36Fe710f6dAAdFA91",
    "Wasabi": "0x2b993B00B44095ec52c5BA456551022f0B9ca6D4",
    "Avantis": "0x0b6DF4b22891139a17588523cc1AF068Ecf03D35",
    "SkyPsm": "0x8cC1729066d5fEaDe4C9326C3f001c42bEFD57EB",
}

# DEX Legos
DEX_LEGOS = {
    "AeroClassic": "0x5Decf97EA12AaBFF0e4E5810F6fa2C920d640245",
    "AeroSlipstream": "0xC626C1DaEbe71CC4e51028eDABE69f13b6362248",
    "Curve": "0x4e0C4B96FAdc84D41144C1aE868aA1411c1d0743",
    "UniswapV2": "0x33F73b46Ba59cC8B7a1fC807076d4686A8364ce6",
    "UniswapV3": "0xda8C08B95B79E450BDE507a33C0BdcF5562691cB",
}

# Other Contracts
LEGO_TOOLS = "0x9236af092494C91Da80364C8Df3557FB05C0094E"
RIPE_LEGO = "0xf8190935c8682d5f802A0b4AF0C782AcEb9ecb56"
UNDERSCORE_LEGO = "0xB3a04D48a85d052496a6ee3Fad28A557717C220a"
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

    try:
        rows = []

        # User wallets
        try:
            num_wallets = ledger.numUserWallets()
            rows.append(("Total User Wallets", num_wallets - 1 if num_wallets > 0 else 0))
        except Exception:
            rows.append(("Total User Wallets", "N/A"))

        # Registered legos
        try:
            num_legos = lego_book.numAddrs()
            rows.append(("Registered Legos", num_legos - 1 if num_legos > 0 else 0))
        except Exception:
            rows.append(("Registered Legos", "N/A"))

        # Earn vaults
        rows.append(("Earn Vaults", len(EARN_VAULTS)))

        print("| Metric | Value |")
        print("| --- | --- |")
        for row in rows:
            print(f"| **{row[0]}** | {row[1]} |")

    except Exception as e:
        print(f"*Error generating summary: {e}*")


def fetch_undy_hq_data(hq):
    """Fetch and print UndyHq configuration data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"undy-hq\"></a>")
    print("# UndyHq - Main Registry & Governance")
    print(f"Address: {UNDY_HQ}")

    rows = []

    # undyToken
    try:
        undy_token = hq.undyToken()
        rows.append(("undyToken", format_address(str(undy_token))))
    except Exception:
        rows.append(("undyToken", "N/A"))

    # mintEnabled
    try:
        mint_enabled = hq.mintEnabled()
        rows.append(("mintEnabled", mint_enabled))
    except Exception:
        rows.append(("mintEnabled", "N/A"))

    # numAddrs
    try:
        num_addrs = hq.numAddrs()
        rows.append(("numAddrs (departments)", num_addrs - 1 if num_addrs > 0 else 0))
    except Exception:
        rows.append(("numAddrs", "N/A"))

    # registryChangeTimeLock
    try:
        timelock = hq.registryChangeTimeLock()
        rows.append(("registryChangeTimeLock", format_blocks_to_time(timelock)))
    except Exception:
        rows.append(("registryChangeTimeLock", "N/A"))

    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered departments
    try:
        num_addrs = hq.numAddrs()
        if num_addrs > 1:
            print("\n### Registered Departments")
            headers = ["ID", "Description", "Address", "Can Mint UNDY", "Can Set Blacklist"]
            dept_rows = []
            for i in range(1, num_addrs):
                try:
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
                except Exception:
                    continue

            if dept_rows:
                print(f"| {' | '.join(headers)} |")
                print(f"| {' | '.join(['---' for _ in headers])} |")
                for row in dept_rows:
                    print(f"| {' | '.join(str(cell) for cell in row)} |")
    except Exception as e:
        print(f"*Error fetching departments: {e}*")


def fetch_mission_control_data(mc):
    """Fetch and print MissionControl configuration data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"mission-control\"></a>")
    print("# MissionControl - Core Protocol Configuration")
    print(f"Address: {MISSION_CONTROL}")

    # User Wallet Config
    print("\n<a id=\"user-wallet-config\"></a>")
    try:
        uwc = mc.userWalletConfig()
        rows = []

        try:
            rows.append(("walletTemplate", format_address(str(uwc.walletTemplate))))
        except Exception:
            rows.append(("walletTemplate", "N/A"))

        try:
            rows.append(("configTemplate", format_address(str(uwc.configTemplate))))
        except Exception:
            rows.append(("configTemplate", "N/A"))

        try:
            rows.append(("numUserWalletsAllowed", uwc.numUserWalletsAllowed))
        except Exception:
            rows.append(("numUserWalletsAllowed", "N/A"))

        try:
            rows.append(("enforceCreatorWhitelist", uwc.enforceCreatorWhitelist))
        except Exception:
            rows.append(("enforceCreatorWhitelist", "N/A"))

        try:
            rows.append(("minKeyActionTimeLock", format_blocks_to_time(uwc.minKeyActionTimeLock)))
        except Exception:
            rows.append(("minKeyActionTimeLock", "N/A"))

        try:
            rows.append(("maxKeyActionTimeLock", format_blocks_to_time(uwc.maxKeyActionTimeLock)))
        except Exception:
            rows.append(("maxKeyActionTimeLock", "N/A"))

        try:
            rows.append(("depositRewardsAsset", format_address(str(uwc.depositRewardsAsset))))
        except Exception:
            rows.append(("depositRewardsAsset", "N/A"))

        try:
            rows.append(("lootClaimCoolOffPeriod", format_blocks_to_time(uwc.lootClaimCoolOffPeriod)))
        except Exception:
            rows.append(("lootClaimCoolOffPeriod", "N/A"))

        print_table("User Wallet Config", ["Parameter", "Value"], rows)

        # Tx Fees
        try:
            tx_fees = uwc.txFees
            fee_rows = [
                ("swapFee", format_percent(tx_fees.swapFee)),
                ("stableSwapFee", format_percent(tx_fees.stableSwapFee)),
                ("rewardsFee", format_percent(tx_fees.rewardsFee)),
            ]
            print_table("Default Transaction Fees", ["Parameter", "Value"], fee_rows)
        except Exception:
            pass

        # Ambassador Rev Share
        try:
            rev_share = uwc.ambassadorRevShare
            rev_rows = [
                ("swapRatio", format_percent(rev_share.swapRatio)),
                ("rewardsRatio", format_percent(rev_share.rewardsRatio)),
                ("yieldRatio", format_percent(rev_share.yieldRatio)),
            ]
            print_table("Default Ambassador Revenue Share", ["Parameter", "Value"], rev_rows)
        except Exception:
            pass

        # Yield Config
        try:
            yield_config = uwc.yieldConfig
            yield_rows = [
                ("maxYieldIncrease", format_percent(yield_config.maxYieldIncrease)),
                ("performanceFee", format_percent(yield_config.performanceFee)),
                ("ambassadorBonusRatio", format_percent(yield_config.ambassadorBonusRatio)),
                ("bonusRatio", format_percent(yield_config.bonusRatio)),
                ("bonusAsset", format_address(str(yield_config.bonusAsset))),
            ]
            print_table("Default Yield Config", ["Parameter", "Value"], yield_rows)
        except Exception:
            pass

    except Exception as e:
        print(f"*Error fetching User Wallet Config: {e}*")

    # Agent Config
    print("\n<a id=\"agent-config\"></a>")
    try:
        ac = mc.agentConfig()
        rows = [
            ("startingAgent", format_address(str(ac.startingAgent))),
            ("startingAgentActivationLength", format_blocks_to_time(ac.startingAgentActivationLength)),
        ]
        print_table("Agent Config", ["Parameter", "Value"], rows)
    except Exception as e:
        print(f"\n## Agent Config")
        print(f"*Error fetching: {e}*")

    # Manager Config
    print("\n<a id=\"manager-config\"></a>")
    try:
        mgr = mc.managerConfig()
        rows = []

        try:
            rows.append(("managerPeriod", format_blocks_to_time(mgr.managerPeriod)))
        except Exception:
            rows.append(("managerPeriod", "N/A"))

        try:
            rows.append(("managerActivationLength", format_blocks_to_time(mgr.managerActivationLength)))
        except Exception:
            rows.append(("managerActivationLength", "N/A"))

        try:
            rows.append(("mustHaveUsdValueOnSwaps", mgr.mustHaveUsdValueOnSwaps))
        except Exception:
            rows.append(("mustHaveUsdValueOnSwaps", "N/A"))

        try:
            rows.append(("maxNumSwapsPerPeriod", mgr.maxNumSwapsPerPeriod))
        except Exception:
            rows.append(("maxNumSwapsPerPeriod", "N/A"))

        try:
            rows.append(("maxSlippageOnSwaps", format_percent(mgr.maxSlippageOnSwaps)))
        except Exception:
            rows.append(("maxSlippageOnSwaps", "N/A"))

        try:
            rows.append(("onlyApprovedYieldOpps", mgr.onlyApprovedYieldOpps))
        except Exception:
            rows.append(("onlyApprovedYieldOpps", "N/A"))

        print_table("Manager Config", ["Parameter", "Value"], rows)
    except Exception as e:
        print(f"\n## Manager Config")
        print(f"*Error fetching: {e}*")

    # Payee Config
    print("\n<a id=\"payee-config\"></a>")
    try:
        payee = mc.payeeConfig()
        rows = [
            ("payeePeriod", format_blocks_to_time(payee.payeePeriod)),
            ("payeeActivationLength", format_blocks_to_time(payee.payeeActivationLength)),
        ]
        print_table("Payee Config", ["Parameter", "Value"], rows)
    except Exception as e:
        print(f"\n## Payee Config")
        print(f"*Error fetching: {e}*")

    # Cheque Config
    print("\n<a id=\"cheque-config\"></a>")
    try:
        cheque = mc.chequeConfig()
        rows = [
            ("maxNumActiveCheques", cheque.maxNumActiveCheques),
            ("instantUsdThreshold", format_token_amount(cheque.instantUsdThreshold, 6, "USD")),
            ("periodLength", format_blocks_to_time(cheque.periodLength)),
            ("expensiveDelayBlocks", format_blocks_to_time(cheque.expensiveDelayBlocks)),
            ("defaultExpiryBlocks", format_blocks_to_time(cheque.defaultExpiryBlocks)),
        ]
        print_table("Cheque Config", ["Parameter", "Value"], rows)
    except Exception as e:
        print(f"\n## Cheque Config")
        print(f"*Error fetching: {e}*")


def fetch_vault_registry_data(vr):
    """Fetch and print VaultRegistry configuration data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"vault-registry\"></a>")
    print("# VaultRegistry - Vault Configuration")
    print(f"Address: {VAULT_REGISTRY}")

    # Global settings
    rows = []
    try:
        num_addrs = vr.numAddrs()
        rows.append(("numAddrs (vaults)", num_addrs - 1 if num_addrs > 0 else 0))
    except Exception:
        rows.append(("numAddrs", "N/A"))

    try:
        timelock = vr.registryChangeTimeLock()
        rows.append(("registryChangeTimeLock", format_blocks_to_time(timelock)))
    except Exception:
        rows.append(("registryChangeTimeLock", "N/A"))

    if rows:
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

        try:
            vault_config = vr.vaultConfigs(vault_addr)
            rows = []

            try:
                rows.append(("canDeposit", vault_config.canDeposit))
            except Exception:
                rows.append(("canDeposit", "N/A"))

            try:
                rows.append(("canWithdraw", vault_config.canWithdraw))
            except Exception:
                rows.append(("canWithdraw", "N/A"))

            try:
                max_deposit = vault_config.maxDepositAmount
                if max_deposit == 0:
                    rows.append(("maxDepositAmount", "Unlimited"))
                else:
                    rows.append(("maxDepositAmount", format_token_amount(max_deposit, decimals)))
            except Exception:
                rows.append(("maxDepositAmount", "N/A"))

            try:
                rows.append(("isVaultOpsFrozen", vault_config.isVaultOpsFrozen))
            except Exception:
                rows.append(("isVaultOpsFrozen", "N/A"))

            try:
                rows.append(("redemptionBuffer", format_percent(vault_config.redemptionBuffer)))
            except Exception:
                rows.append(("redemptionBuffer", "N/A"))

            try:
                min_yield = vault_config.minYieldWithdrawAmount
                rows.append(("minYieldWithdrawAmount", format_token_amount(min_yield, decimals)))
            except Exception:
                rows.append(("minYieldWithdrawAmount", "N/A"))

            try:
                rows.append(("performanceFee", format_percent(vault_config.performanceFee)))
            except Exception:
                rows.append(("performanceFee", "N/A"))

            try:
                rows.append(("shouldAutoDeposit", vault_config.shouldAutoDeposit))
            except Exception:
                rows.append(("shouldAutoDeposit", "N/A"))

            try:
                rows.append(("defaultTargetVaultToken", format_address(str(vault_config.defaultTargetVaultToken))))
            except Exception:
                rows.append(("defaultTargetVaultToken", "N/A"))

            try:
                rows.append(("isLeveragedVault", vault_config.isLeveragedVault))
            except Exception:
                rows.append(("isLeveragedVault", "N/A"))

            try:
                rows.append(("shouldEnforceAllowlist", vault_config.shouldEnforceAllowlist))
            except Exception:
                rows.append(("shouldEnforceAllowlist", "N/A"))

            print_table(f"{vault_name} Config", ["Parameter", "Value"], rows)

            # Approved vault tokens
            try:
                num_tokens = vr.numApprovedVaultTokens(vault_addr)
                if num_tokens > 0:
                    print(f"\n**Approved Vault Tokens ({num_tokens}):**")
                    token_rows = []
                    for i in range(1, num_tokens + 1):
                        try:
                            token_addr = vr.approvedVaultTokens(vault_addr, i)
                            if str(token_addr) != "0x0000000000000000000000000000000000000000":
                                token_rows.append([i, format_address(str(token_addr))])
                        except Exception:
                            continue
                    if token_rows:
                        print("| Index | Token |")
                        print("| --- | --- |")
                        for row in token_rows:
                            print(f"| {row[0]} | {row[1]} |")
            except Exception:
                pass

        except Exception as e:
            print(f"*Error fetching vault config: {e}*")


def fetch_wallet_backpack_data(wb):
    """Fetch and print WalletBackpack components."""
    print("\n" + "=" * 80)
    print("\n<a id=\"wallet-backpack\"></a>")
    print("# WalletBackpack - Wallet Components")
    print(f"Address: {WALLET_BACKPACK}")

    rows = []

    try:
        rows.append(("kernel", format_address(str(wb.kernel()))))
    except Exception:
        rows.append(("kernel", "N/A"))

    try:
        rows.append(("sentinel", format_address(str(wb.sentinel()))))
    except Exception:
        rows.append(("sentinel", "N/A"))

    try:
        rows.append(("highCommand", format_address(str(wb.highCommand()))))
    except Exception:
        rows.append(("highCommand", "N/A"))

    try:
        rows.append(("paymaster", format_address(str(wb.paymaster()))))
    except Exception:
        rows.append(("paymaster", "N/A"))

    try:
        rows.append(("chequeBook", format_address(str(wb.chequeBook()))))
    except Exception:
        rows.append(("chequeBook", "N/A"))

    try:
        rows.append(("migrator", format_address(str(wb.migrator()))))
    except Exception:
        rows.append(("migrator", "N/A"))

    print_table("Wallet Components", ["Component", "Address"], rows)


def fetch_lego_book_data(lb):
    """Fetch and print LegoBook registry data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"lego-book\"></a>")
    print("# LegoBook - Lego Registry")
    print(f"Address: {LEGO_BOOK}")

    rows = []

    try:
        lego_tools = lb.legoTools()
        rows.append(("legoTools", format_address(str(lego_tools))))
    except Exception:
        rows.append(("legoTools", "N/A"))

    try:
        num_addrs = lb.numAddrs()
        rows.append(("numAddrs (legos)", num_addrs - 1 if num_addrs > 0 else 0))
    except Exception:
        rows.append(("numAddrs", "N/A"))

    try:
        timelock = lb.registryChangeTimeLock()
        rows.append(("registryChangeTimeLock", format_blocks_to_time(timelock)))
    except Exception:
        rows.append(("registryChangeTimeLock", "N/A"))

    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered legos
    try:
        num_addrs = lb.numAddrs()
        if num_addrs > 1:
            print("\n### Registered Legos")
            headers = ["ID", "Description", "Address"]
            lego_rows = []
            for i in range(1, num_addrs):
                try:
                    addr_info = lb.addrInfo(i)
                    contract_addr = str(addr_info.addr)
                    if contract_addr == "0x0000000000000000000000000000000000000000":
                        continue
                    lego_rows.append([
                        i,
                        addr_info.description,
                        format_address(contract_addr),
                    ])
                except Exception:
                    continue

            if lego_rows:
                print(f"| {' | '.join(headers)} |")
                print(f"| {' | '.join(['---' for _ in headers])} |")
                for row in lego_rows:
                    print(f"| {' | '.join(str(cell) for cell in row)} |")
    except Exception as e:
        print(f"*Error fetching legos: {e}*")


def fetch_switchboard_data(sb):
    """Fetch and print Switchboard registry data."""
    print("\n" + "=" * 80)
    print("\n<a id=\"switchboard-registry\"></a>")
    print("# Switchboard - Config Contracts Registry")
    print(f"Address: {SWITCHBOARD}")

    rows = []

    try:
        num_addrs = sb.numAddrs()
        rows.append(("numAddrs (config contracts)", num_addrs - 1 if num_addrs > 0 else 0))
    except Exception:
        rows.append(("numAddrs", "N/A"))

    try:
        timelock = sb.registryChangeTimeLock()
        rows.append(("registryChangeTimeLock", format_blocks_to_time(timelock)))
    except Exception:
        rows.append(("registryChangeTimeLock", "N/A"))

    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered config contracts
    try:
        num_addrs = sb.numAddrs()
        if num_addrs > 1:
            print("\n### Registered Config Contracts")
            headers = ["ID", "Description", "Address"]
            config_rows = []
            for i in range(1, num_addrs):
                try:
                    addr_info = sb.addrInfo(i)
                    contract_addr = str(addr_info.addr)
                    if contract_addr == "0x0000000000000000000000000000000000000000":
                        continue
                    config_rows.append([
                        i,
                        addr_info.description,
                        format_address(contract_addr),
                    ])
                except Exception:
                    continue

            if config_rows:
                print(f"| {' | '.join(headers)} |")
                print(f"| {' | '.join(['---' for _ in headers])} |")
                for row in config_rows:
                    print(f"| {' | '.join(str(cell) for cell in row)} |")
    except Exception as e:
        print(f"*Error fetching config contracts: {e}*")


def fetch_ledger_data(ledger):
    """Fetch and print Ledger statistics."""
    print("\n" + "=" * 80)
    print("\n<a id=\"ledger\"></a>")
    print("# Ledger - Protocol Data")
    print(f"Address: {LEDGER}")

    rows = []

    try:
        num_wallets = ledger.numUserWallets()
        rows.append(("numUserWallets", num_wallets - 1 if num_wallets > 0 else 0))
    except Exception:
        rows.append(("numUserWallets", "N/A"))

    print_table("Protocol Statistics", ["Parameter", "Value"], rows)

    # Global points
    try:
        points = ledger.globalPoints()
        points_rows = [
            ("usdValue", format_token_amount(points.usdValue, 18, "USD")),
            ("depositPoints", f"{points.depositPoints:,}"),
            ("lastUpdate (block)", f"{points.lastUpdate:,}"),
        ]
        print_table("Global Points", ["Parameter", "Value"], points_rows)
    except Exception as e:
        print(f"\n## Global Points")
        print(f"*Error fetching: {e}*")


def fetch_loot_distributor_data():
    """Fetch and print LootDistributor configuration."""
    print("\n" + "=" * 80)
    print("\n<a id=\"loot-distributor\"></a>")
    print("# LootDistributor - Rewards Configuration")
    print(f"Address: {LOOT_DISTRIBUTOR}")

    try:
        loot = boa.from_etherscan(LOOT_DISTRIBUTOR, name="LootDistributor")
        rows = []

        # Deposit Rewards
        try:
            deposit_rewards = loot.depositRewards()
            rows.append(("depositRewards.asset", format_address(str(deposit_rewards.asset))))
            rows.append(("depositRewards.amount", format_token_amount(deposit_rewards.amount, 18)))
        except Exception:
            rows.append(("depositRewards", "N/A"))

        # RIPE staking config
        try:
            rows.append(("ripeStakeRatio", format_percent(loot.ripeStakeRatio())))
        except Exception:
            rows.append(("ripeStakeRatio", "N/A"))

        try:
            rows.append(("ripeLockDuration", format_blocks_to_time(loot.ripeLockDuration())))
        except Exception:
            rows.append(("ripeLockDuration", "N/A"))

        # Immutable addresses
        try:
            rows.append(("RIPE_TOKEN", format_address(str(loot.RIPE_TOKEN()))))
        except Exception:
            rows.append(("RIPE_TOKEN", "N/A"))

        try:
            rows.append(("RIPE_REGISTRY", format_address(str(loot.RIPE_REGISTRY()))))
        except Exception:
            rows.append(("RIPE_REGISTRY", "N/A"))

        print_table("Loot Config", ["Parameter", "Value"], rows)

    except Exception as e:
        print(f"*Error fetching LootDistributor: {e}*")


def fetch_switchboard_alpha_timelock():
    """Fetch SwitchboardAlpha timelock settings."""
    print("\n" + "=" * 80)
    print("\n<a id=\"switchboard-alpha\"></a>")
    print("# SwitchboardAlpha - Timelock Settings")
    print(f"Address: {SWITCHBOARD_ALPHA}")

    try:
        sba = boa.from_etherscan(SWITCHBOARD_ALPHA, name="SwitchboardAlpha")
        rows = []

        try:
            rows.append(("minConfigTimeLock", format_blocks_to_time(sba.minConfigTimeLock())))
        except Exception:
            rows.append(("minConfigTimeLock", "N/A"))

        try:
            rows.append(("maxConfigTimeLock", format_blocks_to_time(sba.maxConfigTimeLock())))
        except Exception:
            rows.append(("maxConfigTimeLock", "N/A"))

        try:
            rows.append(("configTimeLock", format_blocks_to_time(sba.configTimeLock())))
        except Exception:
            rows.append(("configTimeLock", "N/A"))

        try:
            rows.append(("numActions (total)", sba.numActions()))
        except Exception:
            rows.append(("numActions", "N/A"))

        print_table("Timelock Config", ["Parameter", "Value"], rows)

    except Exception as e:
        print(f"*Error fetching SwitchboardAlpha: {e}*")


def fetch_earn_vault_details():
    """Fetch per-vault detailed configuration including managers."""
    print("\n" + "=" * 80)
    print("\n<a id=\"earn-vault-details\"></a>")
    print("# Earn Vault Details - Managers & Assets")

    for vault_name, vault_addr in EARN_VAULTS.items():
        print(f"\n### {vault_name} Details")
        print(f"Address: {vault_addr}")

        try:
            vault = boa.from_etherscan(vault_addr, name=f"EarnVault_{vault_name}")

            rows = []

            # Asset
            try:
                asset = vault.asset()
                rows.append(("asset", format_address(str(asset))))
            except Exception:
                rows.append(("asset", "N/A"))

            # Total assets
            try:
                total = vault.totalAssets()
                decimals = VAULT_DECIMALS.get(vault_name, 18)
                rows.append(("totalAssets", format_token_amount(total, decimals)))
            except Exception:
                rows.append(("totalAssets", "N/A"))

            # Total supply (shares)
            try:
                supply = vault.totalSupply()
                rows.append(("totalSupply (shares)", format_token_amount(supply, 18)))
            except Exception:
                rows.append(("totalSupply", "N/A"))

            # Number of managers
            try:
                num_managers = vault.numManagers()
                rows.append(("numManagers", num_managers - 1 if num_managers > 0 else 0))
            except Exception:
                rows.append(("numManagers", "N/A"))

            # Number of assets
            try:
                num_assets = vault.numAssets()
                rows.append(("numAssets (yield positions)", num_assets - 1 if num_assets > 0 else 0))
            except Exception:
                rows.append(("numAssets", "N/A"))

            # Yield tracking
            try:
                rows.append(("lastUnderlyingBal", format_token_amount(vault.lastUnderlyingBal(), VAULT_DECIMALS.get(vault_name, 18))))
            except Exception:
                pass

            try:
                rows.append(("pendingYieldRealized", format_token_amount(vault.pendingYieldRealized(), VAULT_DECIMALS.get(vault_name, 18))))
            except Exception:
                pass

            if rows:
                print_table(f"{vault_name} Stats", ["Parameter", "Value"], rows)

            # List managers
            try:
                num_managers = vault.numManagers()
                if num_managers > 1:
                    print(f"\n**Managers ({num_managers - 1}):**")
                    manager_rows = []
                    for i in range(1, min(num_managers, 11)):  # Limit to 10 for output
                        try:
                            mgr = vault.managers(i)
                            if str(mgr) != "0x0000000000000000000000000000000000000000":
                                manager_rows.append([i, format_address(str(mgr))])
                        except Exception:
                            continue
                    if manager_rows:
                        print("| Index | Manager |")
                        print("| --- | --- |")
                        for row in manager_rows:
                            print(f"| {row[0]} | {row[1]} |")
            except Exception:
                pass

        except Exception as e:
            print(f"*Error fetching vault details: {e}*")


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
