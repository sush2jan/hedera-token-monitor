import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib import parse, request

from hiero_sdk_python import Client, CryptoGetAccountBalanceQuery, AccountId, PrivateKey

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = Path(os.environ.get("HEDERA_CONFIG_FILE", BASE_DIR / "config.json"))
LOG_FILE_DEFAULT = BASE_DIR / "balance_log.txt"
MIRROR_NODE_BASE_URL = "https://testnet.mirrornode.hedera.com/api/v1"
#MIRROR_NODE_BASE_URL = "https://testnet.mirrornode.hedera.invalid/api/v1"

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_logger(log_file):
    logger = logging.getLogger("hedera_monitor")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def retry_with_backoff(fn, logger, retries=3, initial_delay=1):
    delay = initial_delay
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            logger.warning("Attempt %s/%s failed: %s", attempt, retries, exc)
            if attempt < retries:
                logger.info("Retrying in %s second(s)...", delay)
                time.sleep(delay)
                delay *= 2
    raise last_exc


def create_client(operator_account_id, operator_private_key):
    client = Client.for_testnet()
    client.set_operator(
        AccountId.from_string(operator_account_id),
        PrivateKey.from_string(operator_private_key),
    )
    return client


def get_hbar_balance(client, target_account_id):
    account_id = AccountId.from_string(target_account_id)
    balance = CryptoGetAccountBalanceQuery(account_id=account_id).execute(client)
    return balance.hbars.to_hbars()


def log_balance(logger, account_id, balance_hbar):
    logger.info("Account %s balance: %.8f HBAR", account_id, balance_hbar)


def alert_low_balance(logger, account_id, balance_hbar, threshold_hbar):
    msg = (
        f"LOW BALANCE ALERT: account {account_id} balance {balance_hbar:.8f} HBAR "
        f"is below threshold {threshold_hbar:.8f} HBAR"
    )
    print(msg)
    logger.warning(msg)


def fetch_json(url, timeout, logger):
    def _do():
        with request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} for {url}")
            return json.loads(resp.read().decode("utf-8"))

    return retry_with_backoff(_do, logger)


def fetch_transaction_history(account_id, limit, timeout, logger):
    qs = parse.urlencode(
        {
            "account.id": account_id,
            "transactiontype": "CRYPTOTRANSFER",
            "limit": limit,
            "order": "desc",
        }
    )
    url = f"{MIRROR_NODE_BASE_URL}/transactions?{qs}"
    data = fetch_json(url, timeout, logger)
    return data.get("transactions", [])


def print_transaction_history(transactions, account_id, logger):
    logger.info(
        "Last %s CRYPTOTRANSFER transaction(s) for account %s",
        len(transactions),
        account_id,
    )
    if not transactions:
        print(f"No CRYPTOTRANSFER transactions found for {account_id}.")
        return

    for i, txn in enumerate(transactions, 1):
        print(f"\n[{i}] Transaction ID: {txn.get('transaction_id')}")
        print(f"    Consensus Time : {txn.get('consensus_timestamp')}")
        print(f"    Result         : {txn.get('result')}")
        print(f"    Fee            : {txn.get('charged_tx_fee')} tinybar")
        print("    Transfers:")
        for t in txn.get("transfers", []):
            print(
                f"      - account={t.get('account')} "
                f"amount={t.get('amount')} tinybar "
                f"is_approval={t.get('is_approval', False)}"
            )


def validate_config(config):
    required = [
        "operator_account_id",
        "operator_private_key",
        "account_id",
        "poll_interval_seconds",
        "low_balance_threshold_hbar",
        "duration_minutes",
        "history_limit",
        "mirror_node_timeout_seconds",
    ]
    for key in required:
        if key not in config:
            raise KeyError(key)


def monitor_balance(config, logger):
    client = create_client(
        config["operator_account_id"],
        config["operator_private_key"],
    )
    interval = int(config.get("poll_interval_seconds", 30))
    threshold = float(config.get("low_balance_threshold_hbar", 10))
    duration_minutes = int(config.get("duration_minutes", 10))
    iterations = max(1, int((duration_minutes * 60) / interval))
    account_id = config["operator_account_id"]
    timeout = int(config.get("mirror_node_timeout_seconds", 10))

    logger.info(
        "Starting balance monitoring for account %s every %s second(s) for %s minute(s)",
        account_id,
        interval,
        duration_minutes,
    )

    for idx in range(iterations):
        try:
            balance = retry_with_backoff(
                lambda: get_hbar_balance(client, account_id),
                logger,
            )
            log_balance(logger, account_id, balance)
            if balance < threshold:
                alert_low_balance(logger, account_id, balance, threshold)
        except Exception as exc:
            logger.error("Failed to fetch balance after retries: %s", exc)

        if idx < iterations - 1:
            time.sleep(interval)

    logger.info("Monitoring complete.")


def main():
    try:
        config = load_config(CONFIG_FILE)
        validate_config(config)

        log_file = Path(config.get("log_file", str(LOG_FILE_DEFAULT)))
        if not log_file.is_absolute():
            log_file = BASE_DIR / log_file

        logger = setup_logger(log_file)

        monitor_balance(config, logger)

        history_account_id = config["history_account_id"]
        history_limit = int(config.get("history_limit", 5))
        timeout = int(config.get("mirror_node_timeout_seconds", 10))
        history = fetch_transaction_history(
            history_account_id, history_limit, timeout, logger
        )
        print_transaction_history(history, history_account_id, logger)

    except FileNotFoundError as exc:
        print(f"Missing file: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyError as exc:
        print(f"Missing required config key: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()