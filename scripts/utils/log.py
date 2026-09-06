from urllib.parse import urlsplit

from colorama import Fore, Style


def rpc_log_label(rpc_url):
    """Return an endpoint label without credentials, path tokens, or query data."""
    if rpc_url == "boa":
        return rpc_url
    parsed = urlsplit(rpc_url)
    if not parsed.scheme or not parsed.hostname:
        return "<configured RPC>"
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{host}{port}"


def h1(msg):
    print(
        f"\n\n{Fore.CYAN}-------------------------------------------------------------------------")
    print(f"{Fore.CYAN}{msg}{Style.RESET_ALL}\n")


def h2(msg):
    print(f"\n{Fore.LIGHTBLUE_EX}▸ {msg}{Style.RESET_ALL}\n")


def h3(msg):
    print(f"\t{Fore.GREEN}{msg}{Style.RESET_ALL}")


def error(msg):
    print(f"{Fore.RED}{msg}{Style.RESET_ALL}")


def info(msg):
    print(msg)
