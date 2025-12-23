#!/usr/bin/env python3
"""
Output Lego Parameters Script for Underscore Protocol

Fetches and displays all lego-related configuration from Underscore Protocol
smart contracts on Base mainnet, formatted as markdown tables.

This includes:
- LegoBook registry configuration
- All registered legos and their YieldLegoData
- Registered assets and vault tokens for each lego

Usage:
    python scripts/params/lego_params.py
"""

import os
import sys
import time

import boa

# Import shared utilities
from params_utils import (
    UNDY_HQ,
    RPC_DELAY,
    LEGO_BOOK_ID,
    ZERO_ADDRESS,
    get_token_name,
    format_address,
    format_percent,
    format_blocks_to_time,
    print_table,
    setup_boa_etherscan,
    boa_fork_context,
    print_report_header,
    print_report_footer,
    output_to_file,
)

# ============================================================================
# Global State
# ============================================================================


class LegoState:
    """Holds all dynamically loaded lego contracts and addresses."""

    def __init__(self):
        self.hq = None
        self.lego_book = None
        self.lego_book_addr = None
        self.legos = {}
        self.yield_legos = {}  # Legos with YieldLegoData module
        self.dex_legos = {}  # DEX legos without YieldLegoData

    def get_known_addresses(self) -> dict:
        """Build a map of all known addresses for name resolution."""
        known = {}
        known[UNDY_HQ.lower()] = "UndyHq"
        if self.lego_book_addr:
            known[self.lego_book_addr.lower()] = "LegoBook"
        for lego_id, lego_info in self.legos.items():
            known[lego_info["address"].lower()] = lego_info.get("description", f"Lego_{lego_id}")
        return known


state = LegoState()


def _get_known_addresses():
    """Callback for address resolution."""
    return state.get_known_addresses()


# ============================================================================
# Contract Loading
# ============================================================================


def load_lego_book(hq):
    """Load LegoBook contract from UndyHq."""
    print("  Loading LegoBook from UndyHq...", file=sys.stderr)
    addr = str(hq.getAddr(LEGO_BOOK_ID))
    if addr != ZERO_ADDRESS:
        return boa.from_etherscan(addr, name="LegoBook"), addr
    return None, None


def load_legos(lb):
    """Load all legos from LegoBook registry."""
    print("  Loading legos from LegoBook...", file=sys.stderr)
    legos = {}
    num_legos = lb.numAddrs()

    for i in range(1, num_legos):
        time.sleep(RPC_DELAY)
        addr = str(lb.getAddr(i))
        if addr != ZERO_ADDRESS:
            addr_info = lb.addrInfo(i)
            legos[i] = {"address": addr, "description": addr_info.description}

    return legos


def classify_legos():
    """Classify legos as Yield or DEX based on YieldLegoData module presence."""
    print("  Classifying legos (Yield vs DEX)...", file=sys.stderr)

    for lego_id, lego_info in state.legos.items():
        lego_addr = lego_info["address"]
        lego_name = lego_info.get("description", f"Lego_{lego_id}")

        try:
            time.sleep(RPC_DELAY)
            lego_contract = boa.from_etherscan(lego_addr, name=lego_name)
            # Try to access YieldLegoData - if it has snapShotPriceConfig, it's a yield lego
            lego_contract.snapShotPriceConfig()
            state.yield_legos[lego_id] = lego_info
        except Exception:
            # No YieldLegoData module - it's a DEX lego
            state.dex_legos[lego_id] = lego_info


def initialize_legos():
    """Initialize LegoBook and all legos."""
    print("Loading contracts from Etherscan...", file=sys.stderr)

    # Load HQ first
    state.hq = boa.from_etherscan(UNDY_HQ, name="UndyHq")

    # Load LegoBook
    state.lego_book, state.lego_book_addr = load_lego_book(state.hq)

    # Load all legos
    if state.lego_book:
        state.legos = load_legos(state.lego_book)

    # Classify legos as Yield or DEX
    classify_legos()

    print("  All contracts loaded successfully.\n", file=sys.stderr)


# ============================================================================
# Data Fetching Functions
# ============================================================================


def print_table_of_contents():
    """Print a clickable table of contents."""
    print("""
## Table of Contents

1. [LegoBook Registry](#lego-book)
   - [Registry Config](#registry-config)
   - [Governance Settings](#governance-settings)
   - [Registered Legos](#registered-legos)
2. **Yield Legos**""")

    # Add yield legos to TOC
    for lego_id, lego_info in sorted(state.yield_legos.items()):
        lego_name = lego_info.get("description", f"Lego_{lego_id}")
        anchor = lego_name.lower().replace(" ", "-")
        print(f"   - [{lego_name}](#{anchor})")

    # Add DEX legos section
    print("3. **DEX Legos**")
    for lego_id, lego_info in sorted(state.dex_legos.items()):
        lego_name = lego_info.get("description", f"Lego_{lego_id}")
        anchor = lego_name.lower().replace(" ", "-")
        print(f"   - [{lego_name}](#{anchor})")

    print()


def fetch_lego_book_data():
    """Fetch and print LegoBook registry data."""
    lb = state.lego_book
    if not lb:
        return

    print("\n" + "=" * 80)
    print("\n<a id=\"lego-book\"></a>")
    print("# LegoBook - Lego Registry")
    print(f"Address: {state.lego_book_addr}")

    # Registry Config (AddressRegistry Module)
    num_addrs = lb.numAddrs()
    rows = [
        ("numAddrs (legos)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(lb.registryChangeTimeLock())),
    ]
    print_table("Registry Config (AddressRegistry Module)", ["Parameter", "Value"], rows)

    # LocalGov settings
    time.sleep(RPC_DELAY)
    governance = str(lb.governance())
    time.sleep(RPC_DELAY)
    gov_timelock = lb.govChangeTimeLock()
    time.sleep(RPC_DELAY)
    pending_gov = lb.pendingGov()

    gov_rows = [
        ("governance", format_address(governance, _get_known_addresses)),
        ("govChangeTimeLock", format_blocks_to_time(gov_timelock)),
    ]

    pending_new_gov = str(pending_gov[0]) if pending_gov else ZERO_ADDRESS
    if pending_new_gov != ZERO_ADDRESS:
        gov_rows.append(("pendingGov.newGov", format_address(pending_new_gov, _get_known_addresses)))
        gov_rows.append(("pendingGov.initiatedBlock", pending_gov[1]))
        gov_rows.append(("pendingGov.confirmBlock", pending_gov[2]))
    else:
        gov_rows.append(("pendingGov", "None"))

    print_table("Governance Settings (LocalGov Module)", ["Parameter", "Value"], gov_rows)

    # List registered legos
    if state.legos:
        print("\n### Registered Legos")
        headers = ["ID", "Description", "Address"]
        lego_rows = []
        for lego_id, lego_info in sorted(state.legos.items()):
            lego_rows.append([
                lego_id,
                lego_info["description"],
                f"`{lego_info['address']}`",
            ])

        if lego_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in lego_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")


def fetch_lego_yield_data(lego_id: int, lego_info: dict):
    """Fetch and print YieldLegoData storage for a yield lego contract."""
    lego_addr = lego_info["address"]
    lego_name = lego_info.get("description", f"Lego_{lego_id}")
    anchor = lego_name.lower().replace(" ", "-")

    print("\n" + "=" * 80)
    print(f"\n<a id=\"{anchor}\"></a>")
    print(f"# {lego_name}")
    print(f"Address: `{lego_addr}`")

    lego_contract = boa.from_etherscan(lego_addr, name=lego_name)

    # Check isPaused
    try:
        time.sleep(RPC_DELAY)
        is_paused = lego_contract.isPaused()
        print(f"\n**Status:** {'⚠️ PAUSED' if is_paused else '✅ Active'}")
    except Exception:
        print("\n**Status:** Unknown (no isPaused)")

    # YieldLegoData storage - snapShotPriceConfig
    time.sleep(RPC_DELAY)
    config = lego_contract.snapShotPriceConfig()

    config_rows = [
        ("minSnapshotDelay", f"{config[0]:,} seconds ({config[0] // 60} min)"),
        ("maxNumSnapshots", config[1]),
        ("maxUpsideDeviation", format_percent(config[2])),
        ("staleTime", f"{config[3]:,} seconds ({config[3] // 3600} hours)"),
    ]
    print_table("Snapshot Price Config (YieldLegoData Module)", ["Parameter", "Value"], config_rows)

    # Fetch registered assets and vault tokens with deep storage
    fetch_lego_registered_assets_deep(lego_contract, lego_name)


def fetch_dex_lego_data(lego_id: int, lego_info: dict):
    """Fetch and print basic info for a DEX lego contract."""
    lego_addr = lego_info["address"]
    lego_name = lego_info.get("description", f"Lego_{lego_id}")
    anchor = lego_name.lower().replace(" ", "-")

    print("\n" + "=" * 80)
    print(f"\n<a id=\"{anchor}\"></a>")
    print(f"# {lego_name}")
    print(f"Address: `{lego_addr}`")
    print("\n*DEX Lego - used for swaps, not yield generation*")

    # Check isPaused for DEX legos too
    try:
        time.sleep(RPC_DELAY)
        lego_contract = boa.from_etherscan(lego_addr, name=lego_name)
        time.sleep(RPC_DELAY)
        is_paused = lego_contract.isPaused()
        print(f"\n**Status:** {'⚠️ PAUSED' if is_paused else '✅ Active'}")
    except Exception:
        print("\n**Status:** Unknown")


def fetch_lego_registered_assets_deep(lego_contract, lego_name: str):
    """Fetch and print registered assets, vault tokens, and deep YieldLegoData storage."""
    try:
        # Get all registered assets
        time.sleep(RPC_DELAY)
        assets = lego_contract.getAssets()

        if not assets:
            print("\n*No registered assets*")
            return

        print(f"\n### Registered Assets ({len(assets)})")

        for asset in assets:
            asset_display = format_address(str(asset), _get_known_addresses, try_fetch=True)

            # Get number of opportunities for this asset
            time.sleep(RPC_DELAY)
            try:
                num_opps = lego_contract.numAssetOpportunities(asset)
            except Exception:
                num_opps = "N/A"

            print(f"\n#### {asset_display}")
            print(f"**Opportunities:** {num_opps}")

            time.sleep(RPC_DELAY)
            vaults = lego_contract.getAssetOpportunities(asset)

            if vaults:
                print("\n| Vault Token | Decimals | Avg Price/Share | Last Snapshot | Next Index |")
                print("| --- | --- | --- | --- | --- |")

                for vault in vaults:
                    if str(vault) == ZERO_ADDRESS:
                        continue

                    time.sleep(RPC_DELAY)
                    vault_info = lego_contract.vaultToAsset(vault)

                    # Get snapshot data for this vault
                    try:
                        time.sleep(RPC_DELAY)
                        snapshot_data = lego_contract.snapShotData(vault)
                        last_snapshot = snapshot_data[0]  # SingleSnapShot struct
                        next_index = snapshot_data[1]

                        # Format last snapshot info
                        last_update_timestamp = last_snapshot[2] if len(last_snapshot) > 2 else 0
                        if last_update_timestamp > 0:
                            from datetime import datetime
                            last_update_str = datetime.fromtimestamp(last_update_timestamp).strftime('%Y-%m-%d %H:%M')
                        else:
                            last_update_str = "Never"
                    except Exception:
                        last_update_str = "N/A"
                        next_index = "N/A"

                    vault_display = format_address(str(vault), _get_known_addresses, try_fetch=True)
                    decimals = vault_info[1]

                    # Format average price per share
                    try:
                        avg_pps = vault_info[2]  # lastAveragePricePerShare
                        avg_pps_formatted = f"{avg_pps / 10**decimals:.6f}" if decimals else str(avg_pps)
                    except Exception:
                        avg_pps_formatted = "N/A"

                    print(f"| {vault_display} | {decimals} | {avg_pps_formatted} | {last_update_str} | {next_index} |")
            else:
                print("\n*No vault tokens for this asset*")

    except Exception as e:
        print(f"\n*Could not fetch registered assets for {lego_name}: {e}*")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point."""
    # Output file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "lego_params_output.md")

    print("Connecting to Base mainnet via Alchemy...", file=sys.stderr)

    # Set etherscan API
    setup_boa_etherscan()

    # Fork at latest block
    with boa_fork_context() as block_number:
        print(f"Connected. Block: {block_number}\n", file=sys.stderr)

        # Initialize lego contracts
        initialize_legos()

        print(f"Writing output to {output_file}...", file=sys.stderr)

        # Write report to file
        with output_to_file(output_file):
            # Header
            print_report_header("Underscore Protocol Lego Parameters", block_number)

            # Table of Contents
            print_table_of_contents()

            # LegoBook Registry
            fetch_lego_book_data()

            # Yield Legos (with YieldLegoData module)
            if state.yield_legos:
                print("\n" + "=" * 80)
                print("\n# Yield Legos")
                print("\nLegos that generate yield through lending protocols and yield vaults.")
                for lego_id, lego_info in sorted(state.yield_legos.items()):
                    time.sleep(RPC_DELAY)
                    fetch_lego_yield_data(lego_id, lego_info)

            # DEX Legos (without YieldLegoData module)
            if state.dex_legos:
                print("\n" + "=" * 80)
                print("\n# DEX Legos")
                print("\nLegos for decentralized exchange swaps. These do not have yield data.")
                for lego_id, lego_info in sorted(state.dex_legos.items()):
                    fetch_dex_lego_data(lego_id, lego_info)

            # Footer
            print_report_footer(block_number)

        print(f"Done! Output saved to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
