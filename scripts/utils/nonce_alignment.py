from contextlib import contextmanager

import boa
import rlp
from boa.util.abi import Address
from eth_utils import keccak, to_canonical_address, to_checksum_address


def _active_env(env=None):
    return boa.env if env is None else env


def _is_network_env(env) -> bool:
    return hasattr(env, "_rpc") and callable(getattr(env._rpc, "fetch", None))


def _quantity(value) -> int:
    return int(value, 16) if isinstance(value, str) else int(value)


def _network_account_nonces(env, address: str) -> tuple[int, int, object]:
    latest_raw = env._rpc.fetch(
        "eth_getTransactionCount",
        [str(Address(address)), "latest"],
    )
    pending_raw = env._rpc.fetch(
        "eth_getTransactionCount",
        [str(Address(address)), "pending"],
    )
    return _quantity(latest_raw), _quantity(pending_raw), latest_raw


def get_account_nonces(address: str, env=None) -> tuple[int, int]:
    """Return latest and pending nonces from the active execution environment."""
    target_env = _active_env(env)
    if _is_network_env(target_env):
        latest, pending, _ = _network_account_nonces(target_env, address)
        return latest, pending

    canonical_address = Address(address).canonical_address
    nonce = target_env.evm.vm.state.get_nonce(canonical_address)
    return nonce, nonce


def require_account_nonce(address: str, expected: int | None = None, env=None) -> int:
    """Require no pending nonce gap and, optionally, an exact next nonce."""
    latest, pending = get_account_nonces(address, env)
    if latest != pending:
        raise RuntimeError(
            f"deployer has pending transactions: latest nonce {latest}, "
            f"pending nonce {pending}"
        )
    if expected is not None and latest != expected:
        raise RuntimeError(
            f"deployer nonce changed: expected {expected}, got {latest}"
        )
    return latest


def get_account_nonce(address: str) -> int:
    """Return the stable nonce, rejecting an outstanding pending transaction."""
    return require_account_nonce(address)


def assert_chain_id(expected_chain_id: int, env=None) -> int:
    """Require the active fork/RPC to be the expected chain."""
    target_env = _active_env(env)
    local_chain_id = None
    if hasattr(target_env, "evm") and hasattr(target_env.evm, "patch"):
        local_chain_id = int(target_env.evm.patch.chain_id)

    rpc_chain_id = None
    if _is_network_env(target_env):
        rpc_chain_id = _quantity(target_env._rpc.fetch("eth_chainId", []))
        if local_chain_id is not None and local_chain_id != rpc_chain_id:
            raise RuntimeError(
                f"active RPC chain id {rpc_chain_id} does not match Boa state "
                f"chain id {local_chain_id}"
            )

    actual_chain_id = rpc_chain_id if rpc_chain_id is not None else local_chain_id
    if actual_chain_id != expected_chain_id:
        raise RuntimeError(
            f"wrong chain id: expected {expected_chain_id}, got {actual_chain_id}"
        )
    return actual_chain_id


@contextmanager
def guard_transaction_nonce(address: str, expected: int, env=None):
    """Pin one address-critical transaction to an exact signing nonce.

    NetworkEnv normally asks the RPC for ``latest`` immediately before signing.
    Replace that lookup for the duration of one transaction so it also checks
    ``pending`` and can return only the committed nonce. A concurrent use of the
    deployer can therefore make this transaction fail, but can never make it
    silently sign a later nonce and deploy to the wrong CREATE address.
    """
    target_env = _active_env(env)
    require_account_nonce(address, expected, target_env)

    had_instance_override = False
    previous_instance_override = None
    if _is_network_env(target_env):
        had_instance_override = "_get_nonce" in target_env.__dict__
        previous_instance_override = target_env.__dict__.get("_get_nonce")
        expected_address = Address(address).canonical_address

        def guarded_get_nonce(from_address):
            if Address(from_address).canonical_address != expected_address:
                raise RuntimeError(
                    f"unexpected transaction sender {from_address}; expected {address}"
                )
            latest, pending, latest_raw = _network_account_nonces(
                target_env,
                address,
            )
            if latest != pending:
                raise RuntimeError(
                    "deployer has pending transactions at signing boundary: "
                    f"latest nonce {latest}, pending nonce {pending}"
                )
            if latest != expected:
                raise RuntimeError(
                    "deployer nonce changed at signing boundary: "
                    f"expected {expected}, got {latest}"
                )
            return latest_raw

        target_env._get_nonce = guarded_get_nonce

    try:
        yield
    except Exception:
        raise
    else:
        require_account_nonce(address, expected + 1, target_env)
    finally:
        if _is_network_env(target_env):
            if had_instance_override:
                target_env._get_nonce = previous_instance_override
            else:
                del target_env._get_nonce


def predict_create_address(deployer: str, nonce: int) -> str:
    """Predict the address created by ``deployer`` at ``nonce`` via CREATE."""
    encoded = rlp.encode([to_canonical_address(deployer), nonce])
    return to_checksum_address(keccak(encoded)[-20:])


def _send_zero_value_self_transaction(*, sender: str):
    """Send one nonce-consuming transaction without transferring value.

    A production transaction still pays its normal gas fee. Local and fork
    environments do not model that fee when this helper advances their nonce.
    """
    nonce_before = require_account_nonce(sender)
    computation = boa.env.raw_call(sender, sender=sender, value=0)
    nonce_after, pending_after = get_account_nonces(sender)

    # NetworkEnv broadcasts a real transaction and refreshes its forked state,
    # which advances the nonce. Local/fork Boa calls execute only an EVM message,
    # so model the enclosing transaction's nonce increment explicitly there.
    if (
        not _is_network_env(boa.env)
        and nonce_after == nonce_before
        and pending_after == nonce_before
    ):
        boa.env.evm.vm.state.increment_nonce(Address(sender).canonical_address)
        nonce_after, pending_after = get_account_nonces(sender)

    if nonce_after != nonce_before + 1 or pending_after != nonce_after:
        raise RuntimeError(
            "nonce padding transaction did not increment the deployer nonce "
            f"exactly once: {nonce_before} -> latest {nonce_after}, "
            f"pending {pending_after}"
        )

    return computation


def align_account_nonce(migration, target_nonce: int) -> int:
    """Pad an account to ``target_nonce`` or fail if it has passed the target."""
    sender = str(migration.account.address)
    current_nonce = require_account_nonce(sender)

    if current_nonce > target_nonce:
        raise RuntimeError(
            f"deployer nonce {current_nonce} exceeds required nonce {target_nonce}; "
            "the target CREATE address is permanently unreachable"
        )

    while current_nonce < target_nonce:
        migration.log.h3(
            f"Padding deployer nonce {current_nonce} with a zero-value self-send"
        )
        # A blind retry after an ambiguous broadcast could consume more than
        # one nonce and permanently make the target CREATE address unreachable.
        with guard_transaction_nonce(sender, current_nonce):
            migration.execute(_send_zero_value_self_transaction, no_retry=True)
        current_nonce += 1

    return require_account_nonce(sender, target_nonce)
