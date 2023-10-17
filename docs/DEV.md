# Development Environment
This doesn't represent the only way to develop on darwin-py, but does represent an easy and configurable way to manage things like underlying dependencies and python versions
## Shell environment
No requirement for any particular shell, [zsh](https://github.com/ohmyzsh/ohmyzsh/wiki/Installing-ZSH) + [oh my zsh](https://ohmyz.sh/) is a good setup commonly used, but whatever environment you use make sure to install the recommended alias's and path exports that the below systems require for your particular shell environment, particularly pertinent for poetry which has an added step that it prints to console but isn't included on the webpage. 
## Pyenv
Pyenv manages system python versions, install instructions can be found [here](https://github.com/pyenv/pyenv). 
After installation of pyenv, install a python version that is compatible with darwin-py (3.8-3.10 as of writing)

`pyenv install 3.10`

If the command `pyenv` isn't recognized, it hasn't installed to your shell environemnt config file correctly .zshrc .bashrc etc. 
## Poetry
Poetry manages project level dependencies and local python versions. Install instructions [here](https://python-poetry.org/docs/). Make sure to follow the printed instructions and add the path to your shell environment, if running the command `poetry --version` after installation doesn't work, it means your path hasn't been updated

Set 2 config settings for poetry once you have it setup and recognized as a command
1. Set poetry to use the local version of python, to be used in conjuction with pyenv later

    - `poetry config virtualenvs.prefer-active-python true`

2. Tell poetry to create a local folder copy of python inside .venv directory when it's called to manage a project

    - `poetry config virtualenvs.in-project true` 
## New Folder Setup
To Start from scratch and get a development/QA environemnt setup. This process means you will have a fresh python version with only the dependencies required by darwin-py that is uncorrupted by other packages installed on the system python
- clone darwin py repo
- navigate to downloaded repo
- Set pyenv to use a local `pyenv local <version>` eg `pyenv local 3.10`
- Create local environment with poetry `poetry shell`
- Install dependencies `poetry install`

Pyenv + Poetry here get used in conjuction, with pyenv telling the system whenever `python` is called in a folder that has been set with `pyenv local <version>` that it should use that local version. Poetry is then set to prefer that local version of python, and to create a per project copy of python to use, it will clone `<version>` into a .venv folder locally, and install dependencies there. If new environment is required, run `rm -rf .venv` while inside the project folder, set a new pyenv version if needed and re-run poetry commands 

## Subsequent Uses
Once a folder is setup, it can easily be reused
- navigate to folder
- run `poetry shell`
- execute any commands as normal eg `python -m darwin.cli ...`
- once complete, close terminal or manually exit shell via `exit` in terminal

Can also force poetry commands without being in a shell environment by prepending the command with `poetry run ...` for example

`poetry run python -m darwin.cli`

## Useful Aliases
Aliases can be helpful for testing and development. Add them to your shell configuration file .bashrc .zshrc etc for ease of use and development
```
DARWIN_PY_DEV="$HOME/Development/darwin-py"
alias dpy="poetry run python -m darwin.cli"
alias dpyt="poetry run python -m pytest -W ignore::DeprecationWarning"
alias dpydb="poetry run python -m debugpy --listen 5678 --wait-for-client $DARWIN_PY_DEV/darwin/cli.py"
```

- dpy -> quick way to run darwin
- dpyt -> calls pytest
- dpydb -> creates a remote attach debugging instance for vscode to attach to