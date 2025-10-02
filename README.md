
# Get claude usage as JSON

This is an experimental simple code

```bash
# With pip
pip install 'git+https://github.com/shirayu/claude_usage_json'

# With uv
uv tool install 'git+https://github.com/shirayu/claude_usage_json'

$ claude_usage_json
{
  "Current session": {
    "resets": "2025-10-02T13:00:00+00:00",
    "usage_percent": 6
  },
  "Current week (Opus)": {
    "resets": null,
    "usage_percent": 0
  },
  "Current week (all models)": {
    "resets": "2025-10-09T03:00:00+00:00",
    "usage_percent": 3
  }
}
```

## Hint

You can also get information to visit [web usage info](https://claude.ai/settings/usage).

## License

Apache 2.0
