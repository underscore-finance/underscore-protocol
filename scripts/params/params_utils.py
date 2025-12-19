#!/usr/bin/env python3
"""
Shared utilities for Underscore Protocol params scripts.

This module provides common constants, formatting functions, address resolution,
and utility functions used across production_params.py, vaults_params.py, and lego_params.py.
"""

import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Callable

import boa

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.BluePrint import TOKENS
from tests.constants import ZERO_ADDRESS

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

UNDY_HQ = "0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9"
RPC_URL = f"https://base-mainnet.g.alchemy.com/v2/{os.environ.get('WEB3_ALCHEMY_API_KEY')}"
RPC_DELAY = 0.25  # seconds between RPC batches

# Formatting constants
HUNDRED_PERCENT = 100_00  # 100.00%
DECIMALS_18 = 10**18
DECIMALS_6 = 10**6

# Registry IDs (from contracts/modules/Addys.vy)
LEDGER_ID = 1
MISSION_CONTROL_ID = 2
LEGO_BOOK_ID = 3
SWITCHBOARD_ID = 4
HATCHERY_ID = 5
LOOT_DISTRIBUTOR_ID = 6
APPRAISER_ID = 7
WALLET_BACKPACK_ID = 8
BILLING_ID = 9
VAULT_REGISTRY_ID = 10
HELPERS_ID = 11

# Build KNOWN_TOKENS from BluePrint (invert address -> symbol mapping)
KNOWN_TOKENS = {addr.lower(): symbol for symbol, addr in TOKENS.get("base", {}).items()}

# ============================================================================
# ADDRESS RESOLUTION (with shared cache)
# ============================================================================

_token_symbol_cache = {}


def get_token_name(
    address: str,
    known_addresses_fn: Callable[[], dict] = None,
    try_fetch: bool = True,
) -> str:
    """Resolve address to token symbol or return full address.

    Args:
        address: The address to resolve
        known_addresses_fn: Optional callback to get protocol-specific known addresses
        try_fetch: Whether to try fetching symbol from contract if not found
    """
    if address == ZERO_ADDRESS:
        return "None"

    addr_lower = address.lower()

    # Check cache first
    if addr_lower in _token_symbol_cache:
        return _token_symbol_cache[addr_lower]

    # Check known external tokens (from BluePrint)
    if addr_lower in KNOWN_TOKENS:
        _token_symbol_cache[addr_lower] = KNOWN_TOKENS[addr_lower]
        return KNOWN_TOKENS[addr_lower]

    # Check dynamically loaded protocol addresses
    if known_addresses_fn:
        known_addresses = known_addresses_fn()
        if addr_lower in known_addresses:
            _token_symbol_cache[addr_lower] = known_addresses[addr_lower]
            return known_addresses[addr_lower]

    # Try to fetch symbol from contract
    if try_fetch:
        try:
            time.sleep(RPC_DELAY)
            token_contract = boa.from_etherscan(address, name=f"Token_{address[:8]}")
            symbol = token_contract.symbol()
            if symbol:
                _token_symbol_cache[addr_lower] = symbol
                return symbol
        except Exception:
            pass

    # Return full address if no name found
    _token_symbol_cache[addr_lower] = address
    return address


def format_address(
    address: str,
    known_addresses_fn: Callable[[], dict] = None,
    try_fetch: bool = False,
) -> str:
    """Format address with resolved name and full address.

    Args:
        address: The address to format
        known_addresses_fn: Optional callback to get protocol-specific known addresses
        try_fetch: Whether to try fetching symbol from contract if not found
    """
    if address == ZERO_ADDRESS:
        return "None"
    name = get_token_name(address, known_addresses_fn=known_addresses_fn, try_fetch=try_fetch)
    # Check if we got a real name (not just the address)
    if name and not name.startswith("0x"):
        return f"{name} ({address})"
    return f"`{address}`"


# ============================================================================
# FORMATTING HELPERS
# ============================================================================


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
    """Format token amount with human-readable units (K, M, B)."""
    amount = raw_value / (10**decimals)
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


def format_token_amount_precise(raw_value: int, decimals: int = 18, symbol: str = "") -> str:
    """Format token amount with full precision (all decimal places)."""
    amount = raw_value / (10**decimals)
    # Show up to `decimals` decimal places, but strip trailing zeros
    formatted = f"{amount:,.{decimals}f}".rstrip('0').rstrip('.')
    return f"{formatted} {symbol}" if symbol else formatted


# ============================================================================
# TABLE PRINTING
# ============================================================================


def print_table(title: str, headers: list, rows: list, anchor: str = None):
    """Print a markdown table with optional anchor.

    Uses ### header level for consistency across all scripts.
    """
    if anchor:
        print(f"\n<a id=\"{anchor}\"></a>")
    print(f"\n### {title}")
    print(f"| {' | '.join(headers)} |")
    print(f"| {' | '.join(['---' for _ in headers])} |")
    for row in rows:
        print(f"| {' | '.join(str(cell) for cell in row)} |")


# ============================================================================
# BOA SETUP HELPERS
# ============================================================================


def setup_boa_etherscan():
    """Configure boa for Etherscan API access on Base mainnet."""
    boa.set_etherscan(
        api_key=os.environ["ETHERSCAN_API_KEY"],
        uri="https://api.etherscan.io/v2/api?chainid=8453"
    )


@contextmanager
def boa_fork_context(rpc_url: str = None):
    """Context manager for boa fork connection.

    Yields the block number for convenience.

    Usage:
        with boa_fork_context() as block_number:
            # do stuff with forked state
    """
    url = rpc_url or RPC_URL
    with boa.fork(url):
        block_number = boa.env.evm.patch.block_number
        yield block_number


# ============================================================================
# REPORT UTILITIES
# ============================================================================


def print_report_header(title: str, block_number: int):
    """Print standard report header with title, timestamp, and block info."""
    print("=" * 80)
    print(f"# {title}")
    print(f"\n**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"**Block:** {block_number}")
    print(f"**Network:** Base Mainnet")


def print_report_footer(block_number: int):
    """Print standard report footer."""
    print("\n" + "=" * 80)
    print("\n---")
    print(f"*Report generated at block {block_number} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC*")


@contextmanager
def output_to_file(output_file: str):
    """Context manager to redirect stdout to a file.

    Usage:
        with output_to_file("output.md"):
            print("This goes to the file")
    """
    with open(output_file, "w") as f:
        old_stdout = sys.stdout
        sys.stdout = f
        try:
            yield f
        finally:
            sys.stdout = old_stdout
