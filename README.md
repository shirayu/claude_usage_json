
# Get claude usage as JSON

This is an experimental simple code

```console
# With pip
pip install 'git+https://github.com/shirayu/claude_usage_json'

# With uv
uv tool install 'git+https://github.com/shirayu/claude_usage_json'

# Run in 'trusted folder' where claude not asks you "Do you trust the files in this folder?"
$ claude_usage_json
{
  "session": {
    "reset_second": 5550,
    "resets": "2025-10-02T16:50:00+00:00",
    "usage_percent": 24
  },
  "time": "2025-10-02T15:26:29.272697",
  "week_all_models": {
    "reset_second": 574350,
    "resets": "2025-10-09T06:50:00+00:00",
    "usage_percent": 6
  },
  "week_opus": {
    "reset_second": null,
    "resets": null,
    "usage_percent": 0
  }
}

```

## Hint

You can also get information to visit [web usage info](https://claude.ai/settings/usage).

## License

Apache 2.0
