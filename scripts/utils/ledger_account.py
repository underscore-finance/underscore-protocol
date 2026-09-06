from web3 import Web3
import atexit
from functools import cached_property
import hid
from ledgerblue.comm import HIDDongleHIDAPI, getDongle
from ledgereth.accounts import get_account_by_path
from ledgereth.transactions import create_transaction
from ledgereth.utils import is_bip32_path
from hexbytes import HexBytes

from scripts.utils.log import rpc_log_label


LEDGER_PATH_CONVENTIONS = (
    ("BIP44 address index", lambda index: f"44'/60'/0'/0/{index}"),
    ("Ledger Live account", lambda index: f"44'/60'/{index}'/0/0"),
    ("Ledger Legacy", lambda index: f"44'/60'/0'/{index}"),
)


def normalize_ledger_path(path: str) -> str:
    """Return the path format ledgereth expects, accepting a leading ``m/``."""
    normalized = path.strip()
    if normalized.startswith("m/"):
        normalized = normalized[2:]
    if not normalized or not is_bip32_path(normalized):
        raise ValueError(f"Invalid Ledger derivation path: {path!r}")
    return normalized


def iter_ledger_derivation_paths(count: int = 5):
    """Yield the common Ethereum Ledger paths for indexes ``0..count-1``."""
    for convention, build_path in LEDGER_PATH_CONVENTIONS:
        for index in range(count):
            yield convention, index, build_path(index)


def get_dongle(debug: bool = False, reopen_on_fail: bool = True) -> HIDDongleHIDAPI:
    """
    Get Ledger dongle with proper error handling and reconnection logic.
    """
    try:
        return getDongle(debug=debug)
    except (OSError, RuntimeError) as err:
        if str(err).lower().strip() in ("open failed", "already open") and reopen_on_fail:
            # Device was not closed properly.
            device = hid.device()
            device.close()
            return get_dongle(debug=debug, reopen_on_fail=False)
        raise


class LedgerAccount:
    """
    Ledger hardware wallet integration using ledgerblue and ledgereth.
    Only implements transaction signing for Titanoboa compatibility.
    """

    def __init__(self, rpc_url, account_index=0, derivation_path=None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account_index = account_index
        self.address = None
        self._sender_path = normalize_ledger_path(
            derivation_path
            if derivation_path is not None
            else f"44'/60'/0'/0/{self.account_index}"
        )
        self._connect_ledger()

    @cached_property
    def dongle(self):
        """
        Get Ledger dongle with proper cleanup.
        """
        debug = False  # Set to True for debug output
        device = get_dongle(debug=debug)

        def close():
            print("🔗 Closing Ledger device connection.")
            device.close()

        atexit.register(close)
        return device

    @property
    def private_key(self):
        """
        Titanoboa expects this property to exist.
        For Ledger accounts, we don't have access to the private key.
        """
        raise NotImplementedError("Private key not available for Ledger accounts")

    def _connect_ledger(self):
        """
        Connect to Ledger device and get the account address.
        """
        try:
            print("🔗 Connecting to Ledger device...")

            # Get the account address from Ledger
            self.address = self.get_address()
            print(f"🔗 Connected to Ledger: {self.address}")

            # Verify network connection
            try:
                chain_id = self.w3.eth.chain_id
                print(f"🌐 Connected to network with Chain ID: {chain_id}")
                print(
                    "🔗 RPC endpoint: "
                    f"{rpc_log_label(str(self.w3.provider.endpoint_uri))}"
                )

                # Check balance
                balance = self.w3.eth.get_balance(self.address)
                balance_eth = self.w3.from_wei(balance, 'ether')
                print(f"💰 Account balance: {balance} wei ({balance_eth} ETH)")

                if balance == 0:
                    print("⚠️  WARNING: Account has zero balance!")
                    print("   This will cause 'insufficient funds' errors.")
                    print("   Please fund this account or use a different account index.")

                    # Scan the same conventions used by the preflight path
                    # discovery. Showing only address-index paths here would
                    # mislabel Ledger Live or legacy accounts as unavailable.
                    print("\n📋 Common Ethereum derivation paths:")
                    for convention, index, path in iter_ledger_derivation_paths():
                        try:
                            acc = get_account_by_path(path, dongle=self.dongle)
                            acc_balance = self.w3.eth.get_balance(acc.address)
                            acc_balance_eth = self.w3.from_wei(acc_balance, 'ether')
                            marker = " ← CURRENT" if path == self._sender_path else ""
                            print(
                                f"   {convention} {index}: m/{path} -> "
                                f"{acc.address} - {acc_balance_eth} ETH{marker}"
                            )
                        except Exception:
                            print(
                                f"   {convention} {index}: m/{path} -> "
                                "Error getting address or balance (details redacted)"
                            )

            except Exception:
                print(
                    "⚠️  Could not check network or balance "
                    "(RPC/provider error details redacted)"
                )

        except ImportError as e:
            raise ImportError(f"Required libraries not found: {e}. Install with: pip install ledgerblue ledgereth")
        except Exception as e:
            raise Exception(f"Failed to connect to Ledger: {e}")

    def get_address(self) -> str:
        """
        Get the account address from Ledger device.
        """
        return get_account_by_path(self._sender_path, dongle=self.dongle).address

    def sign_transaction(self, tx_data):
        """
        Sign a transaction using the Ledger device.

        Titanoboa broadcasts the returned raw transaction only after this
        method succeeds.

        Args:
            tx_data (dict): Transaction data to send

        Returns:
            dict: Transaction receipt with hash
        """

        # Ensure 'from' field is a string
        if "from" in tx_data and not isinstance(tx_data["from"], str):
            tx_data["from"] = str(tx_data["from"])

        # Sign the transaction. Titanoboa owns the later RPC broadcast.
        try:
            def to_int(val):
                if isinstance(val, str) and val.startswith("0x"):
                    return int(val, 16)
                return val

            # Prepare transaction parameters for ledgereth
            params = {
                "destination": tx_data.get("to", b''),
                "amount": to_int(tx_data.get("value", 0)),
                "gas": to_int(tx_data.get("gas", 21000)),
                "nonce": to_int(tx_data.get("nonce", 0)),
                "data": tx_data.get("data", ""),
                "chain_id": to_int(tx_data.get("chainId", 1)),
                "sender_path": self._sender_path,
                "dongle": self.dongle
            }

            if "maxPriorityFeePerGas" in tx_data and "maxFeePerGas" in tx_data:
                params["max_priority_fee_per_gas"] = to_int(tx_data["maxPriorityFeePerGas"])
                params["max_fee_per_gas"] = to_int(tx_data["maxFeePerGas"])
            else:
                params["gas_price"] = to_int(tx_data.get("gasPrice", 20000000000))

            # Sign with ledgereth using the dongle
            print("🔑 Signing transaction with Ledger...")
            signed_tx = create_transaction(**params)
            print("✅ Transaction signed on Ledger!")

            class SignedTx:
                def __init__(self, rawTransaction):
                    self.raw_transaction = HexBytes(rawTransaction)

            return SignedTx(signed_tx.rawTransaction)

        except Exception as e:
            raise Exception(f"Failed to sign transaction with Ledger: {e}")

    def __repr__(self):
        return (
            f"LedgerAccount(address={self.address}, "
            f"derivation_path=m/{self._sender_path})"
        )
