
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
  "current_session": {
    "resets": "2025-10-01T17:00:00+00:00",
    "usage_percent": 12
  },
  "current_time": "2025-10-01T15:05:54.157692",
  "current_week_all_models": {
    "resets": "2025-10-08T07:00:00+00:00",
    "usage_percent": 5
  },
  "current_week_opus": {
    "resets": null,
    "usage_percent": 0
  }
}
```

## Hint

You can also get information to visit [web usage info](https://claude.ai/settings/usage).

## License

Apache 2.0
