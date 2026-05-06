# Hedera Token and Transaction Monitoring Script

This repository contains a Python-based monitoring tool for Hedera **Testnet**.  
It monitors the HBAR balance of a configured Hedera account using the `hiero-sdk-python` community SDK and fetches recent crypto transfer history using the Hedera Mirror Node REST API.

## Features

- Polls HBAR balance for a Hedera Testnet account every 30 seconds for 10 minutes by default.
- Logs balances with timestamps to `balance_log.txt`.
- Retries transient failures with exponential backoff.
- Prints and logs a low-balance alert when the balance drops below a configured threshold.
- Fetches the latest `CRYPTOTRANSFER` transactions for a configured account using Mirror Node.

## Repository contents

- `monitor.py` — Main monitoring script.
- `config.json` — Runtime configuration file.
- `README.md` — Setup, run instructions and assumptions.

## Setup

### 1. Clone the repository

```bash
git clone <your-private-repo-url>
cd hedera-token-monitor
```

### 2. Create a virtual environment

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install hiero-sdk-python
```

The balance monitoring implementation uses the `hiero-sdk-python` community SDK, while transaction history lookup uses the Hedera Mirror Node REST API.

## Configuration

Create or update `config.json` in the same folder as `monitor.py`.

Example:

```json
{
  "operator_account_id": "0.0.YOUR_PRIVATE_ACCOUNT_ID_HERE",
  "operator_private_key": "302e020100300506032b657004220420YOUR_PRIVATE_KEY_HERE",
  "account_id": "0.0.12345",
  "poll_interval_seconds": 30,
  "low_balance_threshold_hbar": 10,
  "duration_minutes": 10,
  "history_account_id": "0.0.7230975",
  "history_limit": 5,
  "mirror_node_timeout_seconds": 10,
  "log_file": "balance_log.txt"
}
```

### Config field notes

- `operator_account_id` — Hedera Testnet operator account used to initialize the SDK client and the account currently monitored for balance.
- `operator_private_key` — Private key for the operator account.
- `account_id` — Retained as the placeholder account from the assignment prompt.
- `history_account_id` — Account used for transaction history lookup.
- `poll_interval_seconds` — Balance polling interval.
- `low_balance_threshold_hbar` — Low-balance alert threshold.
- `duration_minutes` — Total monitoring duration.
- `history_limit` — Number of recent transactions to display.
- `mirror_node_timeout_seconds` — Timeout for Mirror Node HTTP requests.
- `log_file` — Output log filename.

## Run

From the repository root:

```bash
python ./monitor.py
```

You can also override the config path with an environment variable:

```bash
HEDERA_CONFIG_FILE=./config.json python ./monitor.py
```

On Windows PowerShell:

```powershell
$env:HEDERA_CONFIG_FILE=".\config.json"
python .\monitor.py
```

## Expected behavior

1. The script loads configuration from `config.json`.
2. It creates a Hedera Testnet client using `Client.for_testnet()` and `set_operator(...)`.
3. It queries the HBAR balance of the monitored account using `CryptoGetAccountBalanceQuery`.
4. It polls for the configured duration at the configured interval.
5. Each balance is written to the console and `balance_log.txt`.
6. If a transient failure occurs, the script retries up to 3 total attempts with exponential backoff delays of 1s and 2s between retries.
7. If the balance falls below the configured threshold, the script prints and logs a low-balance alert.
8. After monitoring completes, the script queries the Hedera Mirror Node `transactions` endpoint and prints the last `N` `CRYPTOTRANSFER` transactions for `history_account_id`.

## Assumptions

- The assignment suggested `0.0.12345` as a placeholder account ID if a real Testnet account was not available.
- A real Hedera Testnet account was created for this submission, so `operator_account_id` is used as the monitored account.
- `account_id` is retained in `config.json` to reflect the original prompt, but the current code monitors `operator_account_id`.
- `history_account_id` is used for the transaction history feature.
- A valid private key is required because the balance monitoring path uses the SDK.
- The transaction history feature uses the public Hedera Testnet Mirror Node REST API.

## Retry demo

To demonstrate the retry mechanism for the Mirror Node transaction-history path, temporarily change the Mirror Node base URL in `monitor.py` to an invalid hostname:

```python
# MIRROR_NODE_BASE_URL = "https://testnet.mirrornode.hedera.invalid/api/v1"
```

This causes the request to fail and triggers the retry logging. After the demo, restore the correct value:

```python
MIRROR_NODE_BASE_URL = "https://testnet.mirrornode.hedera.com/api/v1"
```

With the current implementation, retry behavior is:
- Attempt 1 fails, wait 1 second.
- Attempt 2 fails, wait 2 seconds.
- Attempt 3 fails, stop.

## Notes

- The monitoring loop intentionally uses `time.sleep()` because the assignment allows it.
- Runtime settings are externalized into `config.json` so peers can change behavior without editing code.
- The implementation uses the SDK for balance monitoring and Mirror Node for transaction history, which aligns well with how historical queries are commonly handled on Hedera.
