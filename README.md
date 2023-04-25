# IsekaiLocalizer
Create localization using ChatGPT.

## Usage
Requirements:
- [Python 3.11](https://www.python.org/downloads/) or above
- [Poetry](https://python-poetry.org/docs/#installation)

1. Place your `LocalizationPack.json` in the `data` folder.
2. Install dependencies using `poetry install` in your terminal.
3. Run `main.py` using `python main.py` in your terminal.

## TODO
- Bad translations
- Bad prompt for ChatGPT
- Invalid response from ChatGPT
- Timeout from API after `max_retries=3`
- 1000 character limitation for ora.sh endpoint
- Missing `Override` and `fill missing` options for localized string.