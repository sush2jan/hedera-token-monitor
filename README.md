# Hedera Token and Transaction Monitoring Script

This submission implements a small Python monitoring tool for Hedera **Testnet** that:
- Fetches the HBAR balance for a Hedera Testnet account using the `hiero-sdk-python` community SDK.
- Polls every 30 seconds for 10 minutes by default.
- Logs balances with timestamps to `balance_log.txt`.
- Retries transient failures up to 3 times with exponential backoff starting at 1 second.
- Triggers a low-balance alert when the balance drops below a configured HBAR threshold.
- Fetches the last `N` `CRYPTOTRANSFER` transactions for a configured account using the Hedera Mirror Node REST API.

## Files

- `monitor.py` — Main monitoring script.
- `config.json` — Runtime configuration.
- `README.md` — Setup, execution and assumptions.

## Requirements

- Python 3.10+
- `hiero-sdk-python`

Install dependencies in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install hiero-sdk-python
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install hiero-sdk-python
```

## Configuration

The script reads `config.json` relative to the location of `monitor.py` unless `HEDERA_CONFIG_FILE` is explicitly set.

Example configuration:

```json
{
  "operator_account_id": "0.0.8857486",
  "operator_private_key": "3030020100300706052b8104000a0422042076e74c9867237f43bdf50273c0cbe126a701XXXXXXXXXXXXXXXXXXXXXX",
  "account_id": "0.0.12345",
  "poll_interval_seconds": 30,
  "low_balance_threshold_hbar": 10,
  "duration_minutes": 10,
  "history_limit": 5,
  "history_account_id": "0.0.7230975",
  "mirror_node_timeout_seconds": 10,
  "log_file": "balance_log.txt"
}
```

### Config field usage

- `operator_account_id` — The actual Hedera Testnet account used as the SDK operator and the account currently being monitored.
- `operator_private_key` — The private key for the Testnet operator account used to initialize the SDK client.
- `account_id` — Retained as the placeholder account ID mentioned in the assignment prompt.
- `history_account_id` — The account whose recent `CRYPTOTRANSFER` history is fetched from the Mirror Node API.
- `poll_interval_seconds` — Polling interval for balance checks.
- `low_balance_threshold_hbar` — Alert threshold in HBAR.
- `duration_minutes` — Total monitoring duration.
- `mirror_node_timeout_seconds` — Timeout used for Mirror Node REST calls.
- `log_file` — Output log file path.

Because a real Hedera Testnet account was created for this submission, `operator_account_id` is used for balance monitoring instead of the placeholder `0.0.12345`.

## How it works

### Balance monitoring

The script creates a Hedera Testnet client with:

- `Client.for_testnet()`
- `client.set_operator(...)`
- `CryptoGetAccountBalanceQuery(account_id=...).execute(client)`

It then polls the configured account balance, logs the result and raises a low-balance alert if the threshold is crossed.

### Transaction history

The script uses the Hedera Testnet Mirror Node REST API to fetch the last `N` `CRYPTOTRANSFER` transactions for `history_account_id` using query parameters such as:

- `account.id`
- `transactiontype=CRYPTOTRANSFER`
- `limit`
- `order=desc`

This is used only for historical transaction lookup; the balance monitoring path uses the SDK.

## Run

From the project root:

```bash
python ./TokenMonitoring/monitor.py
```

You can also override the config file path:

```bash
HEDERA_CONFIG_FILE=./TokenMonitoring/config.json python ./TokenMonitoring/monitor.py
```

## Expected behavior

1. The script loads configuration from `config.json`.
2. It creates a Hedera Testnet SDK client using the configured operator account ID and private key.
3. It monitors the HBAR balance of `operator_account_id` using `CryptoGetAccountBalanceQuery`.
4. It polls for the configured duration at the configured interval.
5. Each balance is written to the console and `balance_log.txt` with timestamps.
6. If a network or request failure occurs, the script makes up to 3 total attempts with exponential backoff delays of 1s and 2s between retries.
7. If the balance falls below the configured threshold, the script prints and logs a low-balance alert.
8. After monitoring completes, it queries the Hedera Testnet Mirror Node `transactions` endpoint and prints the latest `CRYPTOTRANSFER` history for `history_account_id`.

## Notes on design choices

- The monitoring loop intentionally uses `time.sleep()` because the exercise explicitly allows it.
- Runtime settings are externalized into `config.json` so peers can change behavior without editing code.
- The implementation uses the `hiero-sdk-python` community SDK for live balance queries and the Mirror Node REST API for historical transaction lookup.
- The code stays well under the requested 350-line limit.

## Assumptions

- The assignment suggested `0.0.12345` as a placeholder account ID if a real Testnet account was not available.
- Since a valid Hedera Testnet account was created for this submission, the script monitors `operator_account_id`.
- `account_id` is retained in the config for reference to the original prompt, but the current code monitors `operator_account_id`.
- The transaction history feature reads from the public Hedera Testnet Mirror Node REST endpoint.
- A valid operator private key is required because the balance query path uses the SDK client.

## Error handling

The script retries transient errors around both:
- SDK-based balance queries.
- Mirror Node transaction history requests.

After the final retry fails, the error is logged and the script continues or exits depending on where the error occurred.

## Demo: retry mechanism

To demonstrate the retry and exponential backoff logic during a live demo, the Mirror Node base URL can be temporarily changed to an invalid hostname:

```python
# MIRROR_NODE_BASE_URL = "https://testnet.mirrornode.hedera.invalid/api/v1"
```

That intentionally causes the Mirror Node transaction history request to fail and triggers the retry mechanism. After the demo, restore the normal endpoint:

```python
MIRROR_NODE_BASE_URL = "https://testnet.mirrornode.hedera.com/api/v1"
```

## Suggested PR summary

Implemented a Python-based Hedera Testnet monitoring tool with configurable polling, timestamped logging, exponential-backoff retries, low-balance alerts, and Mirror Node transaction history lookup for recent crypto transfers. The current implementation uses the `hiero-sdk-python` community SDK for balance monitoring and the Hedera Mirror Node REST API for transaction history retrieval.