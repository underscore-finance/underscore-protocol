import boa.deployments
import click
import boa

from scripts.utils import log
from scripts.utils.migration_helpers import get_account, load_vyper_files
from scripts.utils.migration_runner import MigrationRunner
from scripts.utils.deploy_args import DeployArgs
from boa.environment import Env
from scripts.utils.mock_account import MockAccount
# from scripts.utils.safe_account import SafeAccount
# from scripts.utils.ledger_account import LedgerAccount
import json
import os
import urllib.request


MIGRATION_SCRIPTS_DIR = "./migrations"
MIGRATION_HISTORY_DIR = "./migration_history"


CLICK_PROMPTS = {
    "safe": {
        "prompt": "What is the safe address?",
        "default": "",
        "help": "Safe address to use for the migration. Defaults to ``.",
    },
    "rpc": {
        "prompt": "What is the desired rpc?",
        "default": "",
        "help": "RPC url for the chain to deploy to. Defaults to ``.",
    },
    "environment": {
        "prompt": "Inform the environment name",
        "default": "v1.1",
        "help": f"Environment of manifests that are written and read by migration scripts to pass state from previous migrations. Defaults to `v1.1`.",
    },
    "start_timestamp": {
        "prompt": "Start timestamp",
        "default": "0",
        "help": "Timestamp at which to start running migrations. If none is provided, the timestamp of the first manifest is used.",
    },
    "single": {
        "prompt": "Is single migration?",
        "default": False,
        "help": "Runs only the specified migration. If false, runs all the migrations starting from the specified timestamp."
    },
    "end_timestamp": {
        "prompt": "End timestamp",
        "default": "0",
        "help": "Last timestamp migration that will run. If none is provided, the timestamp of the most recent manifest is used.",
        "depends": {
            "single": False
        }
    },
    "blueprint": {
        "prompt": "Blueprint",
        "default": "base",
        "help": "Blueprint to use for the migration. Defaults to `base`.",
    },
    "chain": {
        "prompt": "Chain name",
        "default": "base-mainnet",
        "help": "Chain name for custom configuration on the deployment (ex: eth-mainnet, eth-sepolia, base-mainnet, base-sepolia).  Defaults to `base-mainnet`",
        "type": click.Choice(["local", "base-mainnet", "base-sepolia", "eth-sepolia", "eth-mainnet", "base-mainnet", "base-sepolia"], case_sensitive=False),

    },
    "account": {
        "prompt": "Deployer account name",
        "default": "DEPLOYER",
        "help": "Account name for deployment. Defaults to `DEPLOYER`"
    },
    "is_retry": {
        "prompt": "Use previous logs?",
        "help": "Use previous logs instead of running transactions again.",
        "default": False,
    },
    "manifest": {
        "prompt": "Manifest",
        "default": "current",
        "help": "Manifest to use for the migration. Defaults to `current`.",
    },
    "block": {
        "prompt": "Block",
        "default": "0",
        "help": "Block to use for the fork. Defaults to `0` for latest block.",
    },
}


ETHERSCAN_API_KEYS = {
    "base-mainnet": os.environ["ETHERSCAN_API_KEY"],
    "base-sepolia": os.environ["ETHERSCAN_API_KEY"],
}
ETHERSCAN_URLS = {
    "eth-mainnet": "https://api.etherscan.io/v2/api?chainid=1",
    "eth-goerli": "https://api-goerli.etherscan.io/api",
    "eth-sepolia": "https://api-sepolia.etherscan.io/api",
    "base-mainnet": "https://api.etherscan.io/v2/api?chainid=8453",
    "base-goerli": "https://api-goerli.basescan.org/api",
    "base-sepolia": "https://api-sepolia.basescan.org/api",
}


ETH_MAINNET_CHAIN_ID = 1
ALLOW_ETH_MAINNET_ENV = "ALLOW_ETH_MAINNET_DEPLOY"


def resolve_chain_id(rpc_url, attempts=2):
    """`eth_chainId` lookup. Returns None if it cannot be determined.

    Sends an explicit User-Agent: some public RPC providers reject urllib's
    default one with a 403, which would otherwise look like an unreachable node.
    """
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}).encode()
    request = urllib.request.Request(rpc_url, data=payload, headers={
        "Content-Type": "application/json",
        "User-Agent": "underscore-migrate/1.0",
    })
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return int(json.load(response)["result"], 16)
        except Exception:
            if attempt == attempts - 1:
                return None
    return None


def assert_eth_mainnet_allowed(chain, rpc_url, fork):
    """Refuse to run a live migration against Ethereum mainnet by accident.

    A Hightop user wallet address is `CREATE(hatchery, nonce)`, and a hatchery
    address is `CREATE(deployer, nonce)`. When a user sends a deposit to their
    wallet address on Ethereum mainnet instead of Base, the only way to recover
    it is to reproduce that exact CREATE chain on mainnet -- which requires the
    deployer account to still be at the right mainnet nonce. Any real mainnet
    transaction from a deployer account burns nonces and permanently destroys
    that recovery path for every affected user.

    Deploying to Ethereum mainnet must therefore be a deliberate, reviewed act.
    Set `ALLOW_ETH_MAINNET_DEPLOY=1` to override once the nonce impact on
    outstanding recoveries has been signed off.
    """
    if fork or chain == "local" or rpc_url == "boa":
        return

    if chain == "eth-mainnet":
        chain_id = ETH_MAINNET_CHAIN_ID
    else:
        chain_id = resolve_chain_id(rpc_url)
        if chain_id is None and os.environ.get(ALLOW_ETH_MAINNET_ENV) != "1":
            # Fail closed: a blocked deploy costs minutes, but an unnoticed
            # mainnet deploy permanently destroys user recovery. `--chain` alone
            # is not trustworthy here, since `--rpc` overrides where we connect.
            raise click.ClickException(
                f"Could not verify the chain id of `{rpc_url}`, so this run "
                "cannot rule out Ethereum mainnet.\n"
                f"Re-run with {ALLOW_ETH_MAINNET_ENV}=1 once you have confirmed "
                "the target chain.")
    if chain_id != ETH_MAINNET_CHAIN_ID:
        return

    if os.environ.get(ALLOW_ETH_MAINNET_ENV) == "1":
        log.error(
            f"{ALLOW_ETH_MAINNET_ENV}=1 -- proceeding on Ethereum mainnet. "
            "This burns deployer nonces and may permanently destroy "
            "misdirected-deposit recovery for existing users.")
        return

    raise click.ClickException(
        "Refusing to migrate against Ethereum mainnet (chainId 1).\n"
        "Deployer nonces on mainnet are the only recovery lever for deposits "
        "misdirected to a user wallet address, and this run would burn them "
        "irreversibly.\n"
        f"If this is intended and signed off, re-run with {ALLOW_ETH_MAINNET_ENV}=1.")


def param_prompt(ctx, param, value):
    param_config = CLICK_PROMPTS[param.name]
    is_configured_param = not (param_config is None)

    if not is_configured_param:
        return value

    default_val = None if "default" not in param_config.keys(
    ) else param_config["default"]
    prompt = None if "prompt" not in param_config.keys(
    ) else param_config["prompt"]
    optional = not default_val is None if "optional" not in param_config.keys(
    ) else param_config["optional"]

    if value != default_val:
        return value

    if prompt is None or (not ctx.params.get("should-ask") and optional):
        return value

    should_prompt = True

    depends = None if "depends" not in param_config.keys(
    ) else param_config["depends"]

    if not (depends is None):
        should_prompt = False
        for key in param_config["depends"].keys():
            dependency_val = ctx.params.get(key)
            if dependency_val == param_config["depends"][key]:
                should_prompt = True
                break

    if not should_prompt:
        return value

    type = None if "type" not in param_config.keys() else param_config["type"]

    value = click.prompt(
        f"{prompt} --{param.name.replace('_', '-')}",
        default=default_val,
        hide_input=param.name == "password",
        type=type,
    )

    return value


@click.command()
@click.option("--should-ask", is_flag=True, default=False, help="Should ask values for prompts not specified instead of using default values.")
@click.option(
    "--safe",
    default=CLICK_PROMPTS["safe"]["default"],
    help=CLICK_PROMPTS["safe"]["help"],
    callback=param_prompt,
)
@click.option("--fork", is_flag=True, default=False, help="Declare that the migration is running on a fork.")
@click.option(
    "--rpc",
    default=CLICK_PROMPTS["rpc"]["default"],
    help=CLICK_PROMPTS["rpc"]["help"],
    callback=param_prompt,
)
@click.option(
    "--environment",
    default=CLICK_PROMPTS["environment"]["default"],
    help=CLICK_PROMPTS["environment"]["help"],
    callback=param_prompt,
)
@click.option(
    "--start-timestamp", "-t",
    default=CLICK_PROMPTS["start_timestamp"]["default"],
    help=CLICK_PROMPTS["start_timestamp"]["help"],
    callback=param_prompt,
)
@click.option(
    "--single", "-s",
    is_flag=True,
    default=CLICK_PROMPTS["single"]["default"],
    help=CLICK_PROMPTS["single"]["help"],
    callback=param_prompt,
)
@click.option(
    "--end-timestamp", "-e",
    default=CLICK_PROMPTS["end_timestamp"]["default"],
    help=CLICK_PROMPTS["end_timestamp"]["help"],
    callback=param_prompt,
)
@click.option(
    "--chain", "-f",
    default=CLICK_PROMPTS["chain"]["default"],
    help=CLICK_PROMPTS["chain"]["help"],
    callback=param_prompt,
)
@click.option(
    "--blueprint", "-b",
    default=CLICK_PROMPTS["blueprint"]["default"],
    help=CLICK_PROMPTS["blueprint"]["help"],
    callback=param_prompt,
)
@click.option(
    "--account", "-a",
    default=CLICK_PROMPTS["account"]["default"],
    help=CLICK_PROMPTS["account"]["help"],
    callback=param_prompt,
)
@click.option(
    "--ledger",
    default=-1,
    help="Ledger account index to use (default: -1 = Not using Ledger)",
    type=int,
)
@click.option(
    "--is-retry",
    is_flag=True,
    default=CLICK_PROMPTS["is_retry"]["default"],
    help=CLICK_PROMPTS["is_retry"]["help"],
    callback=param_prompt,
)
@click.option(
    "--block",
    default=CLICK_PROMPTS["block"]["default"],
    help=CLICK_PROMPTS["block"]["help"],
    callback=param_prompt,
)
def cli(
    should_ask,
    safe,
    fork,
    is_retry,
    rpc,
    single,
    environment,
    start_timestamp,
    end_timestamp,
    chain,
    blueprint,
    account,
    ledger,
    block,
):
    """
    Deploys the protocol by running migration scripts.

    Migrations scripts are located in the `./migrations` directory.
    Migration script filenames are prefixed with a numeric timestamp
    that is used to set the order in which the scripts are run, and
    to determine which scripts to continue from in future migrations.

    Each migration script returns an object that is stored in a JSON
    manifest file in the directory specified by `--environment`. The
    manifest filename includes the timestamp of the migration that
    created it. Future migrations resume from the first migration
    script with a timestamp greater than that of the most recent
    manifest file.

    The contents of the most recent manifest file are parsed into an
    object and passed to the `migrate` function of the next migration
    script. This enables each migration script to access data from
    previous migrations, such as the addresses of deployed contracts.

    Different history directories should be used to record the
    manifests for different networks/environments,
    under a subfolder named with the network ID, e.g.,
    `.migration_history/network/v1`.
    """

    final_rpc = rpc if rpc else (
        'boa' if chain == 'local' else f"https://{chain}.g.alchemy.com/v2/{os.environ.get('WEB3_ALCHEMY_API_KEY')}")

    assert_eth_mainnet_allowed(chain, final_rpc, fork)

    if safe != "":
        if fork:
            sender = MockAccount(safe)
        # else:
        #     sender = SafeAccount(
        #         safe_address=safe,
        #         rpc_url=final_rpc
        #     )
    elif ledger != -1:
        # sender = LedgerAccount(final_rpc, ledger)
        if fork:
            sender = MockAccount(sender.address)
    else:
        sender = get_account(account)

    deploy_args = DeployArgs(
        sender, chain, ignore_logs=not is_retry, blueprint=blueprint, rpc=final_rpc)

    log.h1("Contract Migration")
    log.info(f"Connected to rpc `{final_rpc}`.")
    log.info(f"Deployer account `{sender.address}`.")
    log.info(f"Manifests are stored in `{environment}`.")
    log.info(f"Deployment arguments: {deploy_args}")
    log.info(f"Running migrations starting with timestamp {start_timestamp}.")
    log.info(f"Chain: {chain}.")
    log.info(f"Fork: {fork}.")
    log.info("")
    vyper_files = load_vyper_files()
    log.info(f"Loaded {len(vyper_files)} Vyper files.")

    migrations = MigrationRunner(
        f"{MIGRATION_SCRIPTS_DIR}/{chain}/{environment}",
        f"{MIGRATION_HISTORY_DIR}/{chain}/{environment}",
        vyper_files
    )

    boa.deployments.set_deployments_db(
        boa.deployments.DeploymentsDB(":memory:"))
    boa.set_etherscan(
        api_key=ETHERSCAN_API_KEYS[chain], uri=ETHERSCAN_URLS[chain])

    if final_rpc == 'boa':
        with boa.set_env(Env()) as env:
            total_gas = migrations.run(
                deploy_args, start_timestamp, end_timestamp, not single)

    elif fork:
        kwargs = {
            "allow_dirty": True,
        }
        if block != '0':
            kwargs["block_identifier"] = int(block)

        label = f"block {block}" if block != '0' else "latest block"
        with boa.fork(final_rpc, **kwargs) as env:
            try:
                env.set_balance(sender.address, 10*10**18)
                log.h2('Deployer wallet funded with 10 ETH')
            except:
                log.h2('Cannot fund deployer wallet')
            log.h2(f"Running migrations on fork from {label}...")
            total_gas = migrations.run(
                deploy_args, start_timestamp, end_timestamp, not single)
    else:
        with boa.set_network_env(final_rpc) as env:
            env.add_account(sender)
            log.h2("Running migrations in production...")
            total_gas = migrations.run(
                deploy_args, start_timestamp, end_timestamp, not single)

    log.info(f'Total gas used: {total_gas}')

    log.info("Done.")
    log.info("")


if __name__ == "__main__":
    cli()
