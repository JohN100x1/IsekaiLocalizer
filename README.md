# IsekaiLocalizer
![Tests](https://github.com/JohN100x1/IsekaiLocalizer/actions/workflows/python-workflow.yml/badge.svg)
[![Python](https://img.shields.io/badge/python-3.11%2B-brightgreen)](https://www.python.org/)
[![Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Create localization using ChatGPT. For an input `LocalizationPack.json`,
the output will have `null` values filled using the translated English value.
Currently only supports translation from English to the other languages.

**Disclaimer**: the results are from ChatGPT, so you may not get accurate results.
### Example
Input `LocalizationPack.json`
```json
{
  "LocalizedStrings": [
    {
      "Key": "714b99be4cc74d8ea02500d4c7cffa4e",
      "SimpleName": "$IsekaiProtagonistSpellbook.Name",
      "ProcessTemplates": false,
      "enGB": "Isekai Protagonist",
      "ruRU": null,
      "deDE": null,
      "frFR": null,
      "zhCN": null,
      "esES": null
    }
  ]
}
```
Output `LocalizationPack.json`
```json
{
  "LocalizedStrings": [
    {
      "Key": "714b99be4cc74d8ea02500d4c7cffa4e",
      "SimpleName": "$IsekaiProtagonistSpellbook.Name",
      "ProcessTemplates": false,
      "enGB": "Isekai Protagonist",
      "ruRU": "Исекай Протагонист",
      "deDE": "Isekai-Protagonist",
      "frFR": "Protagoniste d'Isekai",
      "zhCN": "异世界主角",
      "esES": "Protagonista de Isekai"
    }
  ]
}
```
## Usage
Requirements:
- [Python 3.11](https://www.python.org/downloads/) or above
- [Poetry](https://python-poetry.org/docs/#installation)

1. Place your `LocalizationPack.json` in the `data` folder.
2. Install dependencies using `poetry install` in your terminal.
3. Create Open AI account and get your access token from here https://chat.openai.com/api/auth/session.
4. Rename `example.env` to `.env` and set `OPENAI_ACCESS_TOKEN` to your access token.
5. Run `main.py` using `poetry run python src/main.py` in your terminal.

## TODO
- Address Bad translations
- Address Bad prompt for ChatGPT
- Address incomplete translations
- Address long text translations
