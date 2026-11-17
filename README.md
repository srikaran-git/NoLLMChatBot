# Jev Tool Router

An interactive terminal tool that uses Jev to choose among calculator, weather,
and Google web-search tools. Jev is a typed decision model, not a text-generating
chatbot.

## Setup

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
Copy-Item .env.example .env
```

Set `API_KEY` in `.env`. For web-search results, set `GOOGLE_API_KEY` and
`GOOGLE_CSE_ID` (your Programmable Search Engine ID). Google requires both for
the Custom Search JSON API.
`BASE_URL` and `MODEL` are optional overrides. The default model is
`typesafe/jev-1.13.0`.

## Run

```powershell
uv run python main.py
```

The app sends Jev's required `response_format.questions` schema, reads its tool
choice, then calls that tool. Use ordinary requests such as `what is 2 + 5`,
`weather in Mumbai`, or `search Python release notes`. Type `quit` or `exit` to
end the session.

## Development

```powershell
uv run python -m py_compile main.py calculator.py weather.py web_search.py
uv run python -m unittest discover -s tests -v
```
